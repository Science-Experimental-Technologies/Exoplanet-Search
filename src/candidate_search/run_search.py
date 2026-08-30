"""Resumable candidate screening orchestrator and artifact acceptance audit."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import pandas as pd
import yaml

from src.candidate_search.pool_builder import build_unknown_pool
from src.candidate_search.prefetch import prefetch
from src.candidate_search.search import run_candidate_search
from src.provenance import ResumeGuard

LOGGER = logging.getLogger("sxs.candidate_search.pipeline")


def run_candidate_search_workflow(
    config_path: str | Path = "configs/candidate_search.yaml", *, resume: bool = False
) -> dict[str, Any]:
    config_file = Path(config_path)
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    guard = ResumeGuard("search", config, resume)
    artifacts = config["candidate_search"]["artifacts"]
    record: dict[str, Any] = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "config": str(config_file),
        "steps": [],
    }
    try:
        if resume and guard.allows("unknown_pool") and Path(artifacts["selection_summary"]).is_file():
            record["steps"].append({"name": "unknown_pool", "status": "skipped_complete"})
        else:
            guard.invalidate_from("unknown_pool", ["unknown_pool", "prefetch", "candidate_search"])
            record["steps"].append(
                {"name": "unknown_pool", "status": "completed", "summary": build_unknown_pool(config_file)}
            )
        guard.mark("unknown_pool")
        prefetch_path = Path("data/search/processed/prefetch_summary.json")
        prefetch_complete = False
        if prefetch_path.is_file():
            payload = json.loads(prefetch_path.read_text(encoding="utf-8"))
            prefetch_complete = payload.get("available_targets") == payload.get("configured_targets")
        if resume and guard.allows("prefetch") and prefetch_complete:
            record["steps"].append({"name": "prefetch", "status": "skipped_complete"})
        else:
            guard.invalidate_from("prefetch", ["unknown_pool", "prefetch", "candidate_search"])
            result = prefetch(config_file)
            record["steps"].append(
                {
                    "name": "prefetch",
                    "status": "completed",
                    "summary": {key: value for key, value in result.items() if key != "targets"},
                }
            )
        guard.mark("prefetch")
        if resume and guard.allows("candidate_search") and Path(artifacts["shortlist"]).is_file() and Path(artifacts["report"]).is_file():
            record["steps"].append({"name": "candidate_search", "status": "skipped_complete"})
        else:
            guard.invalidate_from("candidate_search", ["unknown_pool", "prefetch", "candidate_search"])
            result = run_candidate_search(config_file)
            record["steps"].append(
                {"name": "candidate_search", "status": "completed", "summary": result}
            )
        guard.mark("candidate_search")
        record["acceptance"] = evaluate_acceptance(config)
        record["status"] = "completed" if record["acceptance"]["passed"] else "acceptance_failed"
    except Exception as exc:
        record["status"] = "failed"
        record["error_type"] = type(exc).__name__
        record["error"] = str(exc)
        raise
    finally:
        record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        output = Path(artifacts["run_record"])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        guard.save()
    return record


def evaluate_acceptance(config: dict[str, Any]) -> dict[str, Any]:
    settings = config["candidate_search"]
    artifacts = settings["artifacts"]
    reasons: list[str] = []
    scaleup_record = Path("reports/scaleup_run_latest.json")
    scaleup_passed = bool(
        scaleup_record.is_file()
        and json.loads(scaleup_record.read_text(encoding="utf-8"))["acceptance"]["passed"]
    )
    if not scaleup_passed:
        reasons.append("scale-up qualification acceptance is not passed")
    required = [
        "selection_summary",
        "processing_summary",
        "candidates",
        "shortlist",
        "report",
        "catalog_recheck",
    ]
    for key in required:
        if not Path(artifacts[key]).is_file():
            reasons.append(f"missing artifact: {key}")
    label = settings["required_label"]
    selected_path = Path(artifacts["selected_targets"])
    eligible_path = Path(artifacts["eligible_pool"])
    if selected_path.is_file() and eligible_path.is_file():
        selected_ids = {
            str(row["id"])
            for row in yaml.safe_load(selected_path.read_text(encoding="utf-8"))["targets"]
        }
        eligible = pd.read_parquet(eligible_path, columns=["target_id", "catalog_status_at_selection"])
        eligible_ids = set(eligible["target_id"].astype(str))
        if not selected_ids <= eligible_ids:
            reasons.append("selected targets are not a subset of the officially excluded eligible pool")
        if set(eligible["catalog_status_at_selection"]) != {"not_categorized_no_koi_history"}:
            reasons.append("eligible pool contains an unexpected catalog status")
    if Path(artifacts["candidates"]).is_file():
        candidates = pd.read_parquet(artifacts["candidates"])
        if set(candidates["catalog_status"]) != {label}:
            reasons.append("candidate outputs do not all carry the required conservative label")
    if Path(artifacts["shortlist"]).is_file():
        shortlist = pd.read_csv(artifacts["shortlist"], dtype={"target_id": str})
        if len(shortlist) != int(settings["shortlist_size"]):
            reasons.append("shortlist size does not match configuration")
        if set(shortlist["catalog_status"]) != {label}:
            reasons.append("shortlist label mismatch")
        missing_figures = [path for path in shortlist["figure_path"] if not Path(path).is_file()]
        if missing_figures:
            reasons.append(f"{len(missing_figures)} shortlist figures are missing")
        if not shortlist["independent_confirmation_required"].astype(bool).all():
            reasons.append("shortlist does not uniformly require independent confirmation")
    if Path(artifacts["catalog_recheck"]).is_file():
        recheck = json.loads(Path(artifacts["catalog_recheck"]).read_text(encoding="utf-8"))
        if any(
            recheck.get(key, 1) != 0
            for key in (
                "cumulative_koi_matches",
                "kepler_confirmed_name_matches",
                "targets_with_nonzero_object_status",
            )
        ):
            reasons.append("post-ranking official catalog recheck found a classified target")
    return {"passed": not reasons, "reasons": reasons, "scaleup_gate_verified": scaleup_passed}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/candidate_search.yaml")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    record = run_candidate_search_workflow(args.config, resume=args.resume)
    print(json.dumps(record, indent=2))
    return 0 if record["status"] == "completed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
