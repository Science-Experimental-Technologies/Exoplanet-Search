"""Create a privacy-conscious SXS diagnostic bundle for support requests."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from src import __version__
from src.config_check import DEFAULT_CONFIGS
from src.doctor import diagnose
from src.workspace_status import inspect_workspace


README = """SXS support bundle

This archive contains bounded installation and workspace metadata only.
It excludes configuration contents, observations, candidates, models, logs,
environment variables, credentials, and absolute workspace paths.

The report does not validate large artifact hashes or contact external services.
Review diagnostics.json before sharing the archive.
"""


def create_support_bundle(
    workspace: str | Path = ".", output: str | Path | None = None
) -> dict[str, Any]:
    """Write diagnostics.json and a disclosure note into a new ZIP archive."""

    root = Path(workspace).resolve()
    destination = Path(output) if output is not None else root / "sxs-support-bundle.zip"
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(f"Support bundle already exists: {destination}")
    status = inspect_workspace(root)
    report = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sxs_version": __version__,
        "workspace": _public_status(status, root),
        "installation": _redact(diagnose(network=False), root),
        "config_sha256": _config_hashes(root),
        "privacy": {
            "included": [
                "SXS/Python/platform versions",
                "direct dependency versions",
                "configuration validity and SHA-256",
                "recorded operation/checkpoint/run statuses",
            ],
            "excluded": [
                "configuration contents",
                "observations and candidate data",
                "models and logs",
                "environment variables and credentials",
                "absolute workspace paths",
            ],
            "network_requests": False,
        },
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        with ZipFile(stream, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("README.txt", README)
            archive.writestr("diagnostics.json", json.dumps(report, indent=2, sort_keys=True) + "\n")
    return {
        "schema_version": 1,
        "output": destination.as_posix(),
        "workspace_valid": status["valid"],
        "files": ["README.txt", "diagnostics.json"],
    }


def _public_status(status: dict[str, Any], root: Path) -> dict[str, Any]:
    def fields(item: dict[str, Any], names: tuple[str, ...]) -> dict[str, Any]:
        return {
            name: _redact(item.get(name), root)
            for name in names
            if name in item
        }

    return {
        "kind": status["kind"],
        "valid": status["valid"],
        "issues": _redact(status["issues"], root),
        "marker": fields(status["marker"], ("exists", "readable", "error")),
        "configs": [fields(item, ("workflow", "valid", "errors")) for item in status["configs"]],
        "operation": fields(
            status["operation"],
            ("exists", "readable", "command", "status", "updated_at_utc", "error"),
        ),
        "checkpoints": [
            fields(item, ("workflow", "exists", "readable", "completed", "error"))
            for item in status["checkpoints"]
        ],
        "runs": [
            fields(
                item,
                ("workflow", "exists", "readable", "status", "acceptance_passed", "error"),
            )
            for item in status["runs"]
        ],
        "scope": status["scope"],
    }


def _redact(value: Any, root: Path) -> Any:
    if isinstance(value, dict):
        return {key: _redact(item, root) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item, root) for item in value]
    if not isinstance(value, str):
        return value
    replacements = (
        (str(root), "<workspace>"),
        (root.as_posix(), "<workspace>"),
        (str(Path.home()), "<home>"),
        (Path.home().as_posix(), "<home>"),
    )
    redacted = value
    for source, replacement in replacements:
        redacted = redacted.replace(source, replacement)
    return redacted


def _config_hashes(root: Path) -> dict[str, str | None]:
    hashes: dict[str, str | None] = {}
    for path in DEFAULT_CONFIGS.values():
        config = root / "configs" / path.name
        hashes[path.name] = _sha256(config) if config.is_file() else None
    return hashes


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, help="New ZIP path; defaults inside the workspace")
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable creation summary")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = create_support_bundle(args.workspace, args.output)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Created SXS support bundle: {result['output']}")
        print("Review diagnostics.json before sharing. No observations, logs, or credentials were included.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
