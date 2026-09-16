"""Check the built wheel's module layout and run its CLI outside the checkout."""

import argparse
from email.parser import BytesParser
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from zipfile import ZipFile


def check_metadata(data: bytes) -> None:
    metadata = BytesParser().parsebytes(data)
    declared = metadata.get_all("Requires-Dist", [])

    def name(value: str) -> str:
        return re.split(r"[\s(<>=!~;\[]", value, maxsplit=1)[0].lower().replace("_", "-")

    runtime_dependencies = {
        name(value)
        for value in declared
        if ";" not in value or "extra ==" not in value.split(";", 1)[1].lower()
    }
    forbidden = runtime_dependencies & {"pytest"}
    if forbidden:
        raise ValueError(
            "Wheel declares test tools as runtime dependencies: "
            + ", ".join(sorted(forbidden))
        )
    extras = {value.lower() for value in metadata.get_all("Provides-Extra", [])}
    missing = {"full", "test"} - extras
    if missing:
        raise ValueError("Wheel is missing optional dependency profiles: " + ", ".join(sorted(missing)))


def check(wheel: Path) -> None:
    with ZipFile(wheel) as archive:
        names = archive.namelist()
        if "cli.py" in names:
            raise ValueError("Wheel contains stale flattened modules; rebuild from a clean source tree")
        for required in ("src/__init__.py", "src/cli.py", "src/citation.py", "src/doctor.py", "src/config_check.py", "src/workspace.py", "src/workspace_status.py", "src/support_bundle.py", "src/verify.py", "src/pipeline.py", "src/default_configs/base.yaml",
                         "src/default_configs/scaleup.yaml", "src/default_configs/candidate_search.yaml",
                         "src/default_configs/independent_validation.yaml"):
            if required not in names:
                raise ValueError(f"Wheel missing runtime module: {required}")
        entry = next(name for name in names if name.endswith(".dist-info/entry_points.txt"))
        if "sxs = src.cli:main" not in archive.read(entry).decode():
            raise ValueError("Wheel CLI entry point does not match src.cli:main")
        metadata_entry = next(name for name in names if name.endswith(".dist-info/METADATA"))
        check_metadata(archive.read(metadata_entry))
    with tempfile.TemporaryDirectory(prefix="sxs-wheel-check-") as temporary:
        code = (
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "from src.cli import main; raise SystemExit(main(sys.argv[2:]))"
        )
        checks = (
            (["--help"], "SXS | SCIX Exoplanet Search"),
            (["citation", "--format", "json"], "10.5281/zenodo.22794079"),
        )
        for arguments, expected in checks:
            result = subprocess.run(
                [sys.executable, "-I", "-c", code, str(wheel.resolve()), *arguments],
                cwd=temporary,
                check=True,
                capture_output=True,
                text=True,
            )
            if expected not in result.stdout:
                raise ValueError(f"Wheel CLI output missing expected value: {expected}")
    print(f"Wheel layout and isolated CLI help/citation passed: {wheel.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    options = parser.parse_args()
    wheels = list(options.directory.glob("scix_exoplanet_search-*.whl"))
    if len(wheels) != 1:
        parser.error("Expected exactly one SXS wheel in the directory")
    check(wheels[0])
