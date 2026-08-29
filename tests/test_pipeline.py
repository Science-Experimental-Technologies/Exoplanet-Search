from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from src.pipeline import PipelineError, run_pipeline


def _temporary_config(tmp_path: Path) -> Path:
    config = yaml.safe_load(Path("configs/base.yaml").read_text(encoding="utf-8"))
    config["paths"] = {
        "raw": str(tmp_path / "raw"),
        "processed": str(tmp_path / "processed"),
        "catalog": str(tmp_path / "catalog"),
        "reports": str(tmp_path / "reports"),
    }
    config["catalog"]["output"] = str(tmp_path / "catalog" / "confirmed.parquet")
    config["dataset"]["manifest"] = str(tmp_path / "processed" / "manifest.csv")
    config["machine_learning"]["negative_sample"]["catalog_output"] = str(
        tmp_path / "catalog" / "false_positives.parquet"
    )
    destination = tmp_path / "config.yaml"
    destination.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return destination


def test_pipeline_runs_selected_phases_in_order(tmp_path: Path) -> None:
    config = _temporary_config(tmp_path)
    called: list[int] = []

    def runner(phase: int):
        def execute(config_path: Path, refresh: bool) -> dict[str, int]:
            assert config_path == config
            assert not refresh
            called.append(phase)
            return {"phase": phase}

        return execute

    record = run_pipeline(
        config,
        from_phase=0,
        to_phase=2,
        stage_runners={phase: runner(phase) for phase in range(3)},
        log_path=tmp_path / "run.json",
    )
    assert called == [0, 1, 2]
    assert record["status"] == "completed"
    assert [row["status"] for row in record["phases"]] == ["completed"] * 3
    assert (tmp_path / "run.json").is_file()


def test_pipeline_dry_run_has_no_side_effects(tmp_path: Path) -> None:
    config = _temporary_config(tmp_path)
    called = False

    def runner(config_path: Path, refresh: bool) -> dict[str, object]:
        nonlocal called
        called = True
        return {}

    record = run_pipeline(
        config,
        from_phase=0,
        to_phase=0,
        dry_run=True,
        stage_runners={0: runner},
    )
    assert not called
    assert record["status"] == "dry_run"
    assert not (tmp_path / "reports").exists()


def test_pipeline_records_failure_before_raising(tmp_path: Path) -> None:
    config = _temporary_config(tmp_path)
    log = tmp_path / "failed.json"

    def fail(config_path: Path, refresh: bool) -> dict[str, object]:
        raise RuntimeError("synthetic failure")

    with pytest.raises(PipelineError, match="synthetic failure"):
        run_pipeline(config, from_phase=0, to_phase=0, stage_runners={0: fail}, log_path=log)
    payload = json.loads(log.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["phases"][0]["error_type"] == "RuntimeError"
