from __future__ import annotations

import json
from pathlib import Path

from src.cli import main
from src.workspace import initialize


def test_initialize_workspace_copies_and_validates_configs(tmp_path: Path) -> None:
    destination = tmp_path / "experiment"
    report = initialize(destination)
    assert report["status"] == "initialized"
    assert report["valid"] is True
    assert len(report["checks"]) == 4
    assert (destination / ".sxs-workspace.json").is_file()
    assert (destination / "configs/base.yaml").is_file()


def test_initialize_is_idempotent_and_does_not_overwrite_configs(tmp_path: Path) -> None:
    destination = tmp_path / "experiment"
    initialize(destination)
    config = destination / "configs/base.yaml"
    edited = config.read_text(encoding="utf-8").replace(
        "name: SCIX Exoplanet Search", "name: Custom Experiment", 1
    )
    config.write_text(edited, encoding="utf-8")
    report = initialize(destination)
    assert report["status"] == "existing"
    assert "name: Custom Experiment" in config.read_text(encoding="utf-8")


def test_cli_init_records_completion_and_rejects_unmarked_directory(
    tmp_path: Path, capsys
) -> None:
    destination = tmp_path / "workspace"
    assert main(["init", str(destination), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"] == str(destination.resolve())
    operation = json.loads(
        (destination / ".sxs-state/operation_latest.json").read_text(encoding="utf-8")
    )
    assert operation["status"] == "completed"

    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    assert main(["init", str(unrelated)]) == 2
    assert "not an SXS workspace" in capsys.readouterr().err
