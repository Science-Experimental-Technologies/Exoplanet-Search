"""Check the built wheel's module layout and run its CLI outside the checkout."""

import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
from zipfile import ZipFile


def check(wheel: Path) -> None:
    with ZipFile(wheel) as archive:
        names = archive.namelist()
        if "cli.py" in names:
            raise ValueError("Wheel contains stale flattened modules; rebuild from a clean source tree")
        for required in ("src/__init__.py", "src/cli.py", "src/pipeline.py", "src/default_configs/base.yaml",
                         "src/default_configs/scaleup.yaml", "src/default_configs/independent_validation.yaml"):
            if required not in names:
                raise ValueError(f"Wheel missing runtime module: {required}")
        entry = next(name for name in names if name.endswith(".dist-info/entry_points.txt"))
        if "sxs = src.cli:main" not in archive.read(entry).decode():
            raise ValueError("Wheel CLI entry point does not match src.cli:main")
    with tempfile.TemporaryDirectory(prefix="sxs-wheel-check-") as temporary:
        code = "import sys; sys.path.insert(0, sys.argv[1]); from src.cli import main; raise SystemExit(main(['--help']))"
        result = subprocess.run([sys.executable, "-I", "-c", code, str(wheel.resolve())],
                                cwd=temporary, check=True, capture_output=True, text=True)
        if "SXS | SCIX Exoplanet Search" not in result.stdout:
            raise ValueError("Wheel help output missing expected CLI heading")
    print(f"Wheel layout and isolated CLI help passed: {wheel.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    options = parser.parse_args()
    wheels = list(options.directory.glob("scix_exoplanet_search-*.whl"))
    if len(wheels) != 1:
        parser.error("Expected exactly one SXS wheel in the directory")
    check(wheels[0])
