"""Resumable end-to-end command-line orchestrator for SXS phases 0-5."""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import yaml

LOGGER = logging.getLogger("sxs.pipeline")

PHASE_NAMES = {
    0: "environment",
    1: "acquisition",
    2: "preprocessing",
    3: "bls_detection",
    4: "machine_learning",
    5: "catalog_validation",
}


class PipelineError(RuntimeError):
    """Raised when orchestration cannot safely complete."""


def run_pipeline(
    config_path: str | Path = "configs/base.yaml",
    *,
    from_phase: int = 0,
    to_phase: int = 5,
    resume: bool = False,
    refresh_catalog: bool = False,
    dry_run: bool = False,
    stage_runners: Mapping[int, Callable[[Path, bool], dict[str, Any]]] | None = None,
    log_path: str | Path | None = None,
) -> dict[str, Any]:
    """Execute a contiguous phase range and return its structured run record."""

    if from_phase not in PHASE_NAMES or to_phase not in PHASE_NAMES or from_phase > to_phase:
        raise ValueError("Require 0 <= from_phase <= to_phase <= 5")
    config_file = Path(config_path)
    if not config_file.is_file():
        raise FileNotFoundError(f"Configuration does not exist: {config_file}")
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    _validate_config(config)
    runners = dict(stage_runners or _default_stage_runners())
    missing_runners = sorted(set(range(from_phase, to_phase + 1)) - set(runners))
    if missing_runners:
        raise PipelineError(f"No runner configured for phases: {missing_runners}")

    if from_phase > 1 and not dry_run:
        incomplete = [phase for phase in range(1, from_phase) if not phase_complete(phase, config)]
        if incomplete:
            names = ", ".join(f"{phase}:{PHASE_NAMES[phase]}" for phase in incomplete)
            raise PipelineError(f"Cannot start at phase {from_phase}; prerequisites incomplete: {names}")

    started = datetime.now(timezone.utc)
    record: dict[str, Any] = {
        "schema_version": 1,
        "started_at_utc": started.isoformat(),
        "finished_at_utc": None,
        "status": "running",
        "config_path": _portable_path(config_file),
        "options": {
            "from_phase": from_phase,
            "to_phase": to_phase,
            "resume": resume,
            "refresh_catalog": refresh_catalog,
            "dry_run": dry_run,
        },
        "phases": [],
    }
    for phase in range(from_phase, to_phase + 1):
        name = PHASE_NAMES[phase]
        phase_record: dict[str, Any] = {"phase": phase, "name": name}
        if dry_run:
            phase_record["status"] = "would_skip" if resume and phase_complete(phase, config) else "would_run"
            record["phases"].append(phase_record)
            continue
        if resume and phase > 0 and phase_complete(phase, config):
            phase_record["status"] = "skipped_complete"
            record["phases"].append(phase_record)
            LOGGER.info("Phase %d (%s): skipped; required outputs exist", phase, name)
            continue
        LOGGER.info("Phase %d (%s): starting", phase, name)
        phase_started = datetime.now(timezone.utc)
        clock = time.perf_counter()
        try:
            summary = runners[phase](config_file, refresh_catalog)
        except Exception as exc:
            phase_record.update(
                {
                    "status": "failed",
                    "started_at_utc": phase_started.isoformat(),
                    "duration_seconds": round(time.perf_counter() - clock, 3),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            record["phases"].append(phase_record)
            record["status"] = "failed"
            record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
            _write_run_record(record, config, log_path)
            raise PipelineError(f"Phase {phase} ({name}) failed: {exc}") from exc
        phase_record.update(
            {
                "status": "completed",
                "started_at_utc": phase_started.isoformat(),
                "duration_seconds": round(time.perf_counter() - clock, 3),
                "summary": summary,
            }
        )
        record["phases"].append(phase_record)
        LOGGER.info("Phase %d (%s): completed in %.1f s", phase, name, phase_record["duration_seconds"])

    record["status"] = "dry_run" if dry_run else "completed"
    record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    if not dry_run:
        written = _write_run_record(record, config, log_path)
        record["run_log"] = _portable_path(written)
    return record


def phase_complete(phase: int, config: dict[str, Any]) -> bool:
    """Return whether the phase's minimum acceptance artifacts exist."""

    if phase == 0:
        return False
    processed = Path(config["paths"]["processed"])
    reports = Path(config["paths"]["reports"])
    outputs = {
        1: [Path(config["catalog"]["output"]), Path(config["dataset"]["manifest"])],
        2: [processed / "preprocessing_summary.json"],
        3: [processed / "bls_candidates.parquet", processed / "bls_recovery.csv", reports / "phase3_bls_recall.md"],
        4: [
            Path(config["machine_learning"]["negative_sample"]["catalog_output"]),
            processed / "negative_bls_candidates.parquet",
            processed / "ml_candidate_metadata.csv",
            reports / "experiments" / "feature_cv.json",
            reports / "experiments" / "cnn_cv.json",
            Path("models/feature_model.joblib"),
            Path("models/cnn_model.keras"),
        ],
        5: [processed / "catalog_checked_candidates.parquet", reports / "benchmark_report.md", reports / "benchmark_metrics.json"],
    }
    required = outputs.get(phase)
    if required is None:
        raise ValueError(f"Unknown phase: {phase}")
    if not all(path.is_file() and path.stat().st_size > 0 for path in required):
        return False
    if phase == 2:
        target_files = [processed / f"{target['id']}_clean.parquet" for target in config["targets"]]
        return all(path.is_file() and path.stat().st_size > 0 for path in target_files)
    return True


def _default_stage_runners() -> dict[int, Callable[[Path, bool], dict[str, Any]]]:
    return {
        0: _run_environment,
        1: _run_acquisition,
        2: _run_preprocessing,
        3: _run_detection,
        4: _run_machine_learning,
        5: _run_validation,
    }


def _run_environment(config_path: Path, refresh_catalog: bool) -> dict[str, Any]:
    del refresh_catalog
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    required = [
        "numpy",
        "pandas",
        "pyarrow",
        "astropy",
        "astroquery",
        "lightkurve",
        "sklearn",
        "matplotlib",
        "yaml",
        "tensorflow",
    ]
    missing = [name for name in required if importlib.util.find_spec(name) is None]
    if missing:
        raise RuntimeError(f"Missing required Python packages: {', '.join(missing)}")
    if sys.version_info < (3, 11):
        raise RuntimeError("SXS requires Python 3.11 or newer")
    for key in ("raw", "processed", "catalog", "reports"):
        Path(config["paths"][key]).mkdir(parents=True, exist_ok=True)
    Path("models").mkdir(exist_ok=True)
    return {"python": platform.python_version(), "packages_checked": required, "config_valid": True}


def _run_acquisition(config_path: Path, refresh_catalog: bool) -> dict[str, Any]:
    from src.ingest.build_dataset import build_dataset
    from src.ingest.catalog_client import fetch_confirmed_transiting_catalog

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    catalog_path = Path(config["catalog"]["output"])
    if refresh_catalog or not catalog_path.is_file():
        fetch_confirmed_transiting_catalog(catalog_path)
    manifest = build_dataset(config_path, refresh_catalog=False)
    return {
        "manifest_rows": len(manifest),
        "targets": int(manifest["target_id"].nunique()),
        "available_rows": int((manifest["status"] == "available").sum()),
        "skipped_rows": int((manifest["status"] != "available").sum()),
    }


def _run_preprocessing(config_path: Path, refresh_catalog: bool) -> dict[str, Any]:
    del refresh_catalog
    from src.preprocess.build_processed import build_processed_dataset

    summary = build_processed_dataset(config_path)
    return {
        "targets": len(summary),
        "available_targets": int((summary["status"] == "available").sum()),
        "skipped_targets": int((summary["status"] != "available").sum()),
    }


def _run_detection(config_path: Path, refresh_catalog: bool) -> dict[str, Any]:
    del refresh_catalog
    from src.detect.bls_search import run_bls

    candidates, recovery = run_bls(config_path)
    eligible = recovery.loc[recovery["eligible"]]
    return {
        "candidate_rows": len(candidates),
        "eligible_planets": len(eligible),
        "recovered_top5_exact": int(eligible["matched_top5_exact"].sum()),
        "recall_top5_exact": float(eligible["matched_top5_exact"].mean()),
    }


def _run_machine_learning(config_path: Path, refresh_catalog: bool) -> dict[str, Any]:
    from src.ingest.build_negative_dataset import build_negative_dataset
    from src.ingest.false_positive_catalog import fetch_false_positive_sample
    from src.model.build_ml_dataset import build_ml_dataset
    from src.model.train_baselines import run_training

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    fp_path = Path(config["machine_learning"]["negative_sample"]["catalog_output"])
    if refresh_catalog or not fp_path.is_file():
        fetch_false_positive_sample(config_path)
    negative = build_negative_dataset(config_path)
    metadata, views = build_ml_dataset(config_path)
    feature, cnn = run_training(config_path)
    return {
        "negative_candidate_rows": len(negative),
        "ml_samples": len(metadata),
        "folded_view_shape": list(views.shape),
        "feature_metrics": feature["aggregate_metrics"],
        "cnn_metrics": cnn["aggregate_metrics"],
    }


def _run_validation(config_path: Path, refresh_catalog: bool) -> dict[str, Any]:
    del refresh_catalog
    from src.validate.catalog_check import run_phase5

    checked, benchmark = run_phase5(config_path)
    return {
        "catalog_checked_candidates": len(checked),
        "catalog_status": checked["catalog_status"].value_counts().to_dict(),
        "models": benchmark["models"],
    }


def _validate_config(config: dict[str, Any]) -> None:
    required = {"project", "paths", "ingest", "catalog", "dataset", "preprocess", "bls", "machine_learning", "targets"}
    missing = sorted(required - set(config))
    if missing:
        raise ValueError(f"Configuration is missing sections: {', '.join(missing)}")
    if not config["targets"]:
        raise ValueError("Configuration contains no validation targets")


def _write_run_record(record: dict[str, Any], config: dict[str, Any], log_path: str | Path | None) -> Path:
    reports = Path(config["paths"]["reports"])
    run_dir = reports / "pipeline_runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    stamp = record["started_at_utc"].replace(":", "-").replace("+", "_")
    destination = Path(log_path) if log_path else run_dir / f"pipeline_{stamp}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    latest = reports / "pipeline_run_latest.json"
    latest.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return destination


def _portable_path(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--from-phase", type=int, choices=range(0, 6), default=0)
    parser.add_argument("--to-phase", type=int, choices=range(0, 6), default=5)
    parser.add_argument("--resume", action="store_true", help="Skip phases whose acceptance artifacts already exist")
    parser.add_argument("--refresh-catalog", action="store_true", help="Refresh official catalog snapshots before use")
    parser.add_argument("--dry-run", action="store_true", help="Print the phase plan without changing files")
    parser.add_argument("--log-path", help="Optional JSON run-record destination")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    try:
        record = run_pipeline(
            args.config,
            from_phase=args.from_phase,
            to_phase=args.to_phase,
            resume=args.resume,
            refresh_catalog=args.refresh_catalog,
            dry_run=args.dry_run,
            log_path=args.log_path,
        )
    except (ValueError, FileNotFoundError, PipelineError) as exc:
        LOGGER.error("%s", exc)
        return 2
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
