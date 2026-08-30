"""Tests for static-site link validation; no MkDocs dependency required."""

import pytest

from scripts.check_documentation import check


def test_relative_links_and_pages_base_path(tmp_path):
    (tmp_path / "index.html").write_text(
        '<a href="guide/#result">Guide</a><a href="/Exoplanet-Search/guide/">Root</a>',
        encoding="utf-8",
    )
    (tmp_path / "guide").mkdir()
    (tmp_path / "guide" / "index.html").write_text(
        '<h1 id="result">Result</h1><a href="../">Home</a>', encoding="utf-8"
    )
    count, links, errors = check(tmp_path)
    assert (count, links, errors) == (2, 3, [])


def test_missing_local_file_and_anchor(tmp_path):
    (tmp_path / "index.html").write_text(
        '<a href="#missing">Anchor</a><img src="missing.png">'
        '<a href="https://example.com/">External</a>', encoding="utf-8"
    )
    _, links, errors = check(tmp_path)
    assert links == 2
    assert len(errors) == 2


def test_empty_site_is_not_success(tmp_path):
    with pytest.raises(ValueError, match="No generated HTML"):
        check(tmp_path)
