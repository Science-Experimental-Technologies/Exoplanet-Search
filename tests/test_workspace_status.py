from __future__ import annotations

import json
from pathlib import Path

from src.cli import main
from src.workspace_status import inspect_workspace


def test_status_reports_initialized_workspace_without_mutation(tmp_path: Path, capsys) -> None:
    workspace = tmp_path / "experiment"
    assert main(["init", str(workspace), "--json"]) == 0
    capsys.readouterr()
    operation_path = workspace / ".sxs-state/operation_latest.json"
    before = operation_path.read_bytes()

    assert main(["status", str(workspace), "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["kind"] == "workspace"
    assert report["valid"] is True
    assert report["operation"]["command"] == "init"
    assert report["operation"]["status"] == "completed"
    assert operation_path.read_bytes() == before


def test_status_summarizes_checkpoints_and_run_records(tmp_path: Path) -> None:
    workspace = tmp_path / "experiment"
    assert main(["init", str(workspace), "--json"]) == 0
    state = workspace / ".sxs-state"
    (state / "baseline.json").write_text(
        json.dumps({"identity": "test", "files": {}, "completed": ["0", "1"]}),
        encoding="utf-8",
    )
    reports = workspace / "reports"
    reports.mkdir()
    (reports / "pipeline_run_latest.json").write_text(
        json.dumps({"status": "completed"}), encoding="utf-8"
    )
    report = inspect_workspace(workspace)
    baseline = next(item for item in report["checkpoints"] if item["workflow"] == "baseline")
    run = next(item for item in report["runs"] if item["workflow"] == "baseline")
    assert baseline["completed"] == ["0", "1"]
    assert run["status"] == "completed"


def test_status_rejects_unrecognized_or_corrupt_workspace(tmp_path: Path) -> None:
    assert inspect_workspace(tmp_path)["valid"] is False
    workspace = tmp_path / "experiment"
    assert main(["init", str(workspace), "--json"]) == 0
    (workspace / ".sxs-state/baseline.json").write_text("not json", encoding="utf-8")
    report = inspect_workspace(workspace)
    assert report["valid"] is False
    assert any("unreadable baseline checkpoint" in issue for issue in report["issues"])
