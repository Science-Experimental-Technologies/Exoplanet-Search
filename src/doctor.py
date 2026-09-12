"""Read-only installation and connectivity diagnostics for SXS."""

from __future__ import annotations

import argparse
import json
from importlib import metadata
from pathlib import Path
import platform
import re
import sys
from urllib.request import Request, urlopen

from src import __version__
from src.provenance import default_config_source


PROJECT_NAME = "scix-exoplanet-search"
SUPPORTED_PYTHON = ((3, 11), (3, 13))
REQUIRED_CONFIGS = (
    "base.yaml",
    "candidate_search.yaml",
    "independent_validation.yaml",
    "scaleup.yaml",
)
NETWORK_ENDPOINTS = {
    "mast": "https://mast.stsci.edu/",
    "nasa_exoplanet_archive": "https://exoplanetarchive.ipac.caltech.edu/",
}


def _declared_requirements() -> list[tuple[str, str]]:
    """Return direct exact pins from installed metadata or the source checkout."""

    source = Path(__file__).resolve().parent.parent / "requirements-core.txt"
    try:
        installed_version = metadata.version(PROJECT_NAME)
    except metadata.PackageNotFoundError:
        installed_version = None
    if source.is_file() and installed_version != __version__:
        raw_requirements = source.read_text(encoding="utf-8").splitlines()
    else:
        try:
            raw_requirements = metadata.requires(PROJECT_NAME) or []
        except metadata.PackageNotFoundError:
            raw_requirements = []

    pins: list[tuple[str, str]] = []
    for raw in raw_requirements:
        requirement = raw.split(";", 1)[0].strip()
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s]+)", requirement)
        if match:
            pins.append((match.group(1), match.group(2)))
    return pins


def _dependency_checks() -> list[dict[str, object]]:
    checks = []
    for name, expected in _declared_requirements():
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            installed = None
        checks.append(
            {
                "name": name,
                "expected": expected,
                "installed": installed,
                "ok": installed == expected,
            }
        )
    return checks


def _config_checks() -> list[dict[str, object]]:
    source = default_config_source()
    return [
        {"name": name, "available": source.joinpath(name).is_file()}
        for name in REQUIRED_CONFIGS
    ]


def _network_checks(timeout: float) -> list[dict[str, object]]:
    checks = []
    for name, url in NETWORK_ENDPOINTS.items():
        try:
            request = Request(url, headers={"User-Agent": f"SXS/{__version__} doctor"})
            with urlopen(request, timeout=timeout) as response:  # nosec B310: fixed HTTPS endpoints
                status = getattr(response, "status", None)
            checks.append({"name": name, "url": url, "ok": status is None or status < 500, "status": status})
        except Exception as exc:  # network failures must be reported, not hidden
            checks.append({"name": name, "url": url, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
    return checks


def diagnose(*, network: bool = False, timeout: float = 5.0) -> dict[str, object]:
    python_ok = SUPPORTED_PYTHON[0] <= sys.version_info[:2] < SUPPORTED_PYTHON[1]
    dependencies = _dependency_checks()
    configs = _config_checks()
    network_checks = _network_checks(timeout) if network else []
    checks_ok = python_ok and all(item["ok"] for item in dependencies) and all(
        item["available"] for item in configs
    )
    if network:
        checks_ok = checks_ok and all(item["ok"] for item in network_checks)
    try:
        distribution_version = metadata.version(PROJECT_NAME)
    except metadata.PackageNotFoundError:
        distribution_version = None
    return {
        "schema_version": 1,
        "status": "ok" if checks_ok else "failed",
        "sxs": {"code_version": __version__, "distribution_version": distribution_version},
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "supported": python_ok,
            "required": ">=3.11,<3.13",
        },
        "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "dependencies": dependencies,
        "default_configs": configs,
        "network": {"requested": network, "checks": network_checks},
    }


def _print_human(result: dict[str, object]) -> None:
    dependencies = result["dependencies"]
    configs = result["default_configs"]
    network = result["network"]
    print(f"SXS doctor {result['sxs']['code_version']}")
    print(f"Status: {str(result['status']).upper()}")
    print(
        f"Python: {result['python']['version']} ({result['python']['implementation']}) "
        f"[{'ok' if result['python']['supported'] else 'unsupported'}]"
    )
    print(f"Dependencies: {sum(bool(item['ok']) for item in dependencies)}/{len(dependencies)} exact pins installed")
    for item in dependencies:
        if not item["ok"]:
            print(f"  - {item['name']}: expected {item['expected']}, found {item['installed'] or 'missing'}")
    print(f"Default configs: {sum(bool(item['available']) for item in configs)}/{len(configs)} available")
    if network["requested"]:
        for item in network["checks"]:
            detail = item.get("status", item.get("error", "unavailable"))
            print(f"Network {item['name']}: {'ok' if item['ok'] else 'failed'} ({detail})")
    else:
        print("Network: skipped (use --network to test public astronomy services)")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check the SXS installation without modifying project data")
    parser.add_argument("--json", action="store_true", help="emit machine-readable diagnostics")
    parser.add_argument("--network", action="store_true", help="also test fixed public MAST and archive endpoints")
    parser.add_argument("--timeout", type=float, default=5.0, help="per-endpoint network timeout in seconds")
    args = parser.parse_args(argv)
    if not 0 < args.timeout <= 60:
        parser.error("--timeout must be greater than 0 and at most 60 seconds")
    result = diagnose(network=args.network, timeout=args.timeout)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        _print_human(result)
    return 0 if result["status"] == "ok" else 3


if __name__ == "__main__":
    raise SystemExit(main())
