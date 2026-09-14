from __future__ import annotations

import json
from pathlib import Path

import yaml

from src.citation import CITATION, main, render_bibtex, render_text


def test_text_and_bibtex_include_archived_release_identity() -> None:
    for rendered in (render_text(), render_bibtex()):
        assert CITATION["title"] in rendered
        assert CITATION["version"] in rendered
        assert CITATION["doi"] in rendered


def test_json_output_is_machine_readable(capsys) -> None:
    assert main(["--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out) == CITATION


def test_command_metadata_matches_citation_cff() -> None:
    cff = yaml.safe_load(Path("CITATION.cff").read_text(encoding="utf-8"))
    assert CITATION["title"] == cff["title"]
    assert CITATION["version"] == cff["version"]
    assert CITATION["doi"] == cff["doi"]
    assert CITATION["year"] == cff["date-released"].year


def test_container_tests_mount_citation_source() -> None:
    workflow = Path(".github/workflows/container.yml").read_text(encoding="utf-8")
    assert 'src="$GITHUB_WORKSPACE/CITATION.cff",dst=/opt/sxs/CITATION.cff,readonly' in workflow
