"""Resumable scale-up qualification orchestrator; intentionally does not implement candidate screening."""

from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

import yaml

from src.config import artifact_path

LOGGER = logging.getLogger("sxs.scaleup.pipeline")


def run_scaleup(
    config_path: str | Path = "configs/scaleup.yaml",
    *,
    resume: bool = False,
) -> dict[str, Any]:
    config_file = Path(config_path)
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    steps: list[tuple[str, Callable[[], dict[str, Any]], Callable[[], bool]]] = [
        ("catalog_selection", lambda: _catalog(config_file), lambda: _catalog_complete(config)),
        ("prefetch", lambda: _prefetch(config_file), lambda: _prefetch_complete()),
        ("confirmed_pipeline", lambda: _confirmed(config_file), lambda: _confirmed_complete(config)),
        ("false_positive_pipeline", lambda: _negative(config_file), lambda: _negative_complete(config)),
        ("ml_dataset", lambda: _ml_dataset(config_file), lambda: _ml_complete(config)),
        ("retraining", lambda: _train(config_file), lambda: _training_complete(config)),
    ]
    record: dict[str, Any] = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "config": str(config_file),
        "resume": resume,
        "steps": [],
    }
    try:
        for name, runner, complete in steps:
            if resume and complete():
                record["steps"].append({"name": name, "status": "skipped_complete"})
                LOGGER.info("%s: skipped", name)
                continue
            LOGGER.info("%s: starting", name)
            clock = time.perf_counter()
            summary = runner()
            record["steps"].append(
                {
                    "name": name,
                    "status": "completed",
                    "duration_seconds": round(time.perf_counter() - clock, 3),
                    "summary": summary,
                }
            )
        acceptance = evaluate_acceptance(config)
        record["acceptance"] = acceptance
        record["status"] = "completed" if acceptance["passed"] else "acceptance_failed"
    except Exception as exc:
        record["status"] = "failed"
        record["error_type"] = type(exc).__name__
        record["error"] = str(exc)
        raise
    finally:
        record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        Path("reports/scaleup_run_latest.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8"
        )
    return record


def evaluate_acceptance(config: dict[str, Any]) -> dict[str, Any]:
    catalog_summary_path = Path(config["paths"]["catalog"]) / "selection_summary.json"
    selection_path = Path("models/production_model_selection.json")
    report_path = artifact_path(config, "report", "reports/model_qualification.md")
    reasons = []
    if not catalog_summary_path.is_file():
        reasons.append("selection summary missing")
        catalog_summary = {}
    else:
        catalog_summary = json.loads(catalog_summary_path.read_text(encoding="utf-8"))
        if catalog_summary.get("positive_targets_after_quality", 0) <= 20:
            reasons.append("positive population did not exceed v1")
        counts = catalog_summary.get("negative_category_counts", {})
        if len(set(counts.values())) != 1 or len(counts) != 4:
            reasons.append("negative flags are not balanced across four categories")
    if not selection_path.is_file():
        reasons.append("versioned production-model selection missing")
        model = None
    else:
        model = json.loads(selection_path.read_text(encoding="utf-8"))
        if not Path(model["model_path"]).is_file():
            reasons.append("selected model artifact missing")
    if not report_path.is_file():
        reasons.append("scale-up qualification report missing")
    return {
        "passed": not reasons,
        "reasons": reasons,
        "selected_model": model,
        "search_authorized_by_artifacts": not reasons,
    }


def _catalog(config: Path) -> dict[str, Any]:
    from src.scaleup.catalog_builder import build_scaleup_catalogs

    return build_scaleup_catalogs(config)


def _prefetch(config: Path) -> dict[str, Any]:
    from src.scaleup.prefetch import prefetch_scaleup

    result = prefetch_scaleup(config)
    return {key: value for key, value in result.items() if key != "targets"}


def _confirmed(config: Path) -> dict[str, Any]:
    from src.detect.bls_search import run_bls
    from src.ingest.build_dataset import build_dataset
    from src.preprocess.build_processed import build_processed_dataset

    manifest = build_dataset(config)
    preprocessing = build_processed_dataset(config)
    candidates, recovery = run_bls(config)
    eligible = recovery.loc[recovery["eligible"]]
    return {
        "manifest_targets": int(manifest["target_id"].nunique()),
        "processed_targets": int((preprocessing["status"] == "available").sum()),
        "skipped_targets": int((preprocessing["status"] != "available").sum()),
        "candidate_rows": len(candidates),
        "eligible_planets": len(eligible),
        "exact_recoveries": int(eligible["matched_top5_exact"].sum()),
    }


def _negative(config: Path) -> dict[str, Any]:
    from src.ingest.build_negative_dataset import build_negative_dataset

    candidates = build_negative_dataset(config)
    return {"candidate_rows": len(candidates), "targets": int(candidates.target_id.nunique())}


def _ml_dataset(config: Path) -> dict[str, Any]:
    from src.model.build_ml_dataset import build_ml_dataset

    metadata, views = build_ml_dataset(config)
    return {
        "samples": len(metadata),
        "positives": int(metadata.label.sum()),
        "negatives": int((metadata.label == 0).sum()),
        "target_groups": int(metadata.target_id.nunique()),
        "view_shape": list(views.shape),
    }


def _train(config: Path) -> dict[str, Any]:
    from src.scaleup.train import train_scaleup

    result = train_scaleup(config)
    return {"selection": result["selection"]}


def _catalog_complete(config: dict[str, Any]) -> bool:
    return (Path(config["paths"]["catalog"]) / "selection_summary.json").is_file()


def _prefetch_complete() -> bool:
    path = Path("data/scaleup/processed/prefetch_summary.json")
    if not path.is_file():
        return False
    summary = json.loads(path.read_text(encoding="utf-8"))
    # Exhausted, explicitly recorded failures are a valid terminal prefetch
    # outcome; downstream stages keep them as skips instead of retrying forever.
    return summary.get("configured_targets", 0) > 0 and len(summary.get("targets", [])) == summary.get(
        "configured_targets"
    )


def _confirmed_complete(config: dict[str, Any]) -> bool:
    root = Path(config["paths"]["processed"])
    return all((root / name).is_file() for name in ("manifest.csv", "preprocessing_summary.json", "bls_candidates.parquet", "bls_recovery.csv"))


def _negative_complete(config: dict[str, Any]) -> bool:
    return artifact_path(config, "negative_candidates", "data/processed/negative_bls_candidates.parquet").is_file()


def _ml_complete(config: dict[str, Any]) -> bool:
    return artifact_path(config, "ml_views", "data/processed/ml_folded_views.npz").is_file()


def _training_complete(config: dict[str, Any]) -> bool:
    return artifact_path(config, "report", "reports/model_qualification.md").is_file() and Path(
        "models/production_model_selection.json"
    ).is_file()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/scaleup.yaml")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    try:
        record = run_scaleup(args.config, resume=args.resume)
    except Exception as exc:
        LOGGER.exception("scale-up qualification failed: %s", exc)
        return 2
    print(json.dumps(record, indent=2))
    return 0 if record["status"] == "completed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
