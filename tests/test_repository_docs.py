from pathlib import Path
import tomllib
from zipfile import ZipFile

import pytest

from scripts.check_repository_docs import language_findings, local_link_errors, rnaas_counts
from scripts.check_wheel import check, check_metadata


def test_language_scan_ignores_code_and_english_names():
    assert language_findings("SXS adalah alat untuk riset yang menggunakan Python.")
    assert not language_findings("Research by Yang and Dan.\n```text\nadalah untuk yang\n```\n")


def test_relative_links_and_html_are_checked(tmp_path):
    (tmp_path / "existing.md").write_text("# Test", encoding="utf-8")
    path = tmp_path / "index.md"
    assert not local_link_errors(path, "[ok](existing.md) [web](https://example.com)", tmp_path)
    assert len(local_link_errors(path, '[missing](absent.md) <img src="absent.png">', tmp_path)) == 2
    assert "escapes" in local_link_errors(path, "[bad](../outside.md)", tmp_path)[0]


def test_rnaas_counts_are_separate():
    counts = rnaas_counts("# Title\n## Abstract\nOne two\n## Data and Methods\nThree four\n## References\nFive")
    assert counts["abstract"] == 2
    assert counts["body"] == 5
    assert counts["total"] > counts["body"] + counts["abstract"]


def test_wheel_check_rejects_flattened_src_layout(tmp_path):
    path = tmp_path / "wrong.whl"
    with ZipFile(path, "w") as archive:
        archive.writestr("cli.py", "")
    with pytest.raises(ValueError, match="stale flattened modules"):
        check(path)


def test_wheel_check_rejects_test_tools_in_runtime_metadata(tmp_path):
    path = tmp_path / "wrong.whl"
    required = (
        "src/__init__.py", "src/cli.py", "src/doctor.py", "src/config_check.py",
        "src/workspace.py", "src/workspace_status.py", "src/support_bundle.py",
        "src/verify.py", "src/pipeline.py", "src/default_configs/base.yaml",
        "src/default_configs/scaleup.yaml", "src/default_configs/candidate_search.yaml",
        "src/default_configs/independent_validation.yaml",
    )
    with ZipFile(path, "w") as archive:
        for name in required:
            archive.writestr(name, "")
        archive.writestr("package.dist-info/entry_points.txt", "sxs = src.cli:main")
        archive.writestr(
            "package.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: package\nVersion: 1\nRequires-Dist: pytest==9.1.1\n",
        )
    with pytest.raises(ValueError, match="runtime dependencies: pytest"):
        check(path)


def test_wheel_metadata_allows_test_extra_but_not_default_test_dependency():
    check_metadata(
        b"Metadata-Version: 2.4\nName: package\nVersion: 1\n"
        b"Provides-Extra: full\nProvides-Extra: test\n"
        b'Requires-Dist: pytest==9.1.1; extra == "test"\n'
    )


def test_container_requirement_files_are_in_build_context():
    root = Path(__file__).resolve().parents[1]
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    ignore_rules = set((root / ".dockerignore").read_text(encoding="utf-8").splitlines())
    copied = {
        token
        for line in dockerfile.splitlines()
        if line.startswith("COPY requirements")
        for token in line.split()[1:-1]
        if token.startswith("requirements")
    }
    assert copied
    assert {f"!{path}" for path in copied} <= ignore_rules


def test_optional_dependency_pins_match_requirement_profiles():
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    def pins(filename: str) -> set[str]:
        return {
            line.strip()
            for line in (root / filename).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith(("#", "-r "))
        }

    assert set(project["optional-dependencies"]["full"]) == pins("requirements.txt")
    assert set(project["optional-dependencies"]["test"]) == pins("requirements-test.txt")
