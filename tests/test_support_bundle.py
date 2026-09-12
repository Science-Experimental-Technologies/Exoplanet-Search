from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from src.cli import main
from src.support_bundle import create_support_bundle


def test_support_bundle_is_bounded_and_redacts_workspace_path(
    tmp_path: Path, capsys
) -> None:
    workspace = tmp_path / "private-user-path" / "experiment"
    assert main(["init", str(workspace), "--json"]) == 0
    capsys.readouterr()
    output = tmp_path / "support.zip"
    result = create_support_bundle(workspace, output)
    assert result["workspace_valid"] is True

    with ZipFile(output) as archive:
        assert set(archive.namelist()) == {"README.txt", "diagnostics.json"}
        diagnostics_bytes = archive.read("diagnostics.json")
        diagnostics = json.loads(diagnostics_bytes)
    assert str(workspace).encode() not in diagnostics_bytes
    assert workspace.as_posix().encode() not in diagnostics_bytes
    assert str(Path.home()).encode() not in diagnostics_bytes
    assert Path.home().as_posix().encode() not in diagnostics_bytes
    assert diagnostics["privacy"]["network_requests"] is False
    assert set(diagnostics["config_sha256"]) == {
        "base.yaml",
        "candidate_search.yaml",
        "independent_validation.yaml",
        "scaleup.yaml",
    }
    assert all(len(value) == 64 for value in diagnostics["config_sha256"].values())
    assert "path" not in diagnostics["workspace"]["operation"]


def test_support_bundle_never_overwrites_existing_archive(tmp_path: Path) -> None:
    workspace = tmp_path / "experiment"
    assert main(["init", str(workspace), "--json"]) == 0
    output = tmp_path / "support.zip"
    output.write_bytes(b"keep")
    with pytest.raises(FileExistsError, match="already exists"):
        create_support_bundle(workspace, output)
    assert output.read_bytes() == b"keep"


def test_support_bundle_cli_json(tmp_path: Path, capsys) -> None:
    workspace = tmp_path / "experiment"
    assert main(["init", str(workspace), "--json"]) == 0
    capsys.readouterr()
    output = tmp_path / "diagnostics.zip"
    assert main(
        ["support-bundle", str(workspace), "--output", str(output), "--json"]
    ) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["files"] == ["README.txt", "diagnostics.json"]
    assert output.is_file()
