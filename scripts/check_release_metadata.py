"""Fail if the release tag disagrees with current software metadata."""

from pathlib import Path
import sys
import tomllib
import yaml

root = Path(__file__).resolve().parents[1]
expected = sys.argv[1]
project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
citation = yaml.safe_load((root / "CITATION.cff").read_text(encoding="utf-8"))
assert project["project"]["version"] == expected
assert str(citation["version"]) == expected
assert f"## [{expected}]" in (root / "CHANGELOG.md").read_text(encoding="utf-8")
print(f"Release metadata agrees: {expected}")
