"""Build platform-labelled SXS source bundles for a GitHub Release."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path


PLATFORM_GUIDES = {
    "windows": """# SXS for Windows

Requirements: 64-bit Windows, Python 3.11 or 3.12, and PowerShell.

```powershell
py -3.11 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -m \"not network\"
```
""",
    "macos": """# SXS for macOS

Requirements: macOS with Python 3.11 or 3.12 and a POSIX shell.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -m \"not network\"
```
""",
    "linux": """# SXS for Linux

Requirements: a 64-bit Linux distribution with Python 3.11 or 3.12 and a POSIX shell.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -m \"not network\"
```
""",
}


def tracked_files(repository: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    return [Path(item.decode("utf-8")) for item in result.stdout.split(b"\0") if item]


def stage_repository(repository: Path, destination: Path, platform: str) -> None:
    for relative_path in tracked_files(repository):
        source = repository / relative_path
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    (destination / "PLATFORM_INSTALL.md").write_text(
        PLATFORM_GUIDES[platform], encoding="utf-8", newline="\n"
    )


def write_zip(source: Path, archive: Path) -> None:
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                handle.write(path, path.relative_to(source.parent))


def write_tar(source: Path, archive: Path) -> None:
    with tarfile.open(archive, "w:gz") as handle:
        handle.add(source, arcname=source.name)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, default=Path("dist"))
    args = parser.parse_args()

    repository = Path(__file__).resolve().parents[1]
    output = (repository / args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    root_name = f"sxs-{args.version}"
    archives: list[Path] = []

    with tempfile.TemporaryDirectory(prefix="sxs-release-") as temporary:
        temporary_root = Path(temporary)
        for platform, extension in (
            ("windows", ".zip"),
            ("macos", ".tar.gz"),
            ("linux", ".tar.gz"),
        ):
            staged = temporary_root / platform / root_name
            staged.mkdir(parents=True)
            stage_repository(repository, staged, platform)
            archive = output / f"sxs-v{args.version}-{platform}-python{extension}"
            if extension == ".zip":
                write_zip(staged, archive)
            else:
                write_tar(staged, archive)
            archives.append(archive)

    checksum_file = output / "SHA256SUMS.txt"
    checksum_file.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in archives),
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
