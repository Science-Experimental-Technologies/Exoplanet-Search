from scripts.check_repository_docs import language_findings, local_link_errors, rnaas_counts
from scripts.check_wheel import check
import pytest
from zipfile import ZipFile


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
