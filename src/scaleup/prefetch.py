"""Concurrent cached MAST prefetch for the scale-up qualification populations."""

from __future__ import annotations

import argparse
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import pandas as pd
import yaml

from src.config import load_targets
from src.ingest.mast_client import MastLightCurveClient

LOGGER = logging.getLogger("sxs.scaleup.prefetch")


def prefetch_scaleup(config_path: str | Path = "configs/scaleup.yaml") -> dict[str, Any]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    positives = [
        {"target_id": str(target["id"]), "population": "confirmed"}
        for target in load_targets(config)
    ]
    negative_catalog = pd.read_parquet(config["machine_learning"]["negative_sample"]["catalog_output"])
    negatives = [
        {"target_id": str(target_id), "population": "false_positive"}
        for target_id in negative_catalog["target_id"].astype(str).drop_duplicates()
    ]
    tasks = positives + negatives
    workers = int(config["scaleup"].get("workers", 4))
    results_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    LOGGER.info("Prefetching %d targets with %d workers", len(tasks), workers)
    pending = tasks
    # Keep three attempts even when every attempt is serial; they are download
    # retries, not merely changes to the concurrency setting.
    worker_attempts = (workers, max(1, workers // 2), 1)
    for attempt, attempt_workers in enumerate(worker_attempts, start=1):
        if not pending:
            break
        LOGGER.info("Prefetch attempt %d for %d target(s) with %d worker(s)", attempt, len(pending), attempt_workers)
        with ThreadPoolExecutor(max_workers=attempt_workers, thread_name_prefix="sxs-mast") as executor:
            futures = {executor.submit(_fetch_one, task, config): task for task in pending}
            for completed, future in enumerate(as_completed(futures), start=1):
                task = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = {**task, "status": "failed", "reason": str(exc)}
                results_by_key[(task["population"], task["target_id"])] = result
                if completed % 25 == 0:
                    LOGGER.info(
                        "Attempt %d progress %d/%d; latest %s %s: %s",
                        attempt,
                        completed,
                        len(pending),
                        task["population"],
                        task["target_id"],
                        result["status"],
                    )
        pending = [
            {"population": population, "target_id": target_id}
            for (population, target_id), result in results_by_key.items()
            if result["status"] != "available"
        ]
        if pending:
            LOGGER.warning("%d target(s) remain failed after attempt %d", len(pending), attempt)
    result_frame = pd.DataFrame(results_by_key.values())
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "workers": workers,
        "configured_targets": len(tasks),
        "available_targets": int((result_frame["status"] == "available").sum()),
        "failed_targets": int((result_frame["status"] != "available").sum()),
        "status_counts": result_frame["status"].value_counts().to_dict(),
        "population_counts": result_frame.groupby(["population", "status"]).size().to_dict(),
        "targets": result_frame.sort_values(["population", "target_id"]).where(pd.notna(result_frame), None).to_dict(orient="records"),
    }
    # Tuple keys are not JSON-compatible.
    summary["population_counts"] = {
        f"{population}:{status}": int(count)
        for (population, status), count in result_frame.groupby(["population", "status"]).size().items()
    }
    output = Path("data/scaleup/processed/prefetch_summary.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def _fetch_one(task: dict[str, str], config: dict[str, Any]) -> dict[str, Any]:
    negative = task["population"] == "false_positive"
    raw_dir = (
        config["machine_learning"]["negative_sample"]["raw_subdirectory"]
        if negative
        else config["paths"]["raw"]
    )
    client = MastLightCurveClient(raw_dir)
    summary = client.fetch(
        task["target_id"],
        id_type="KIC",
        mission=config["ingest"]["mission"],
        author=config["ingest"]["author"],
        cadence=config["ingest"]["cadence"],
        max_products=int(config["ingest"]["max_products"]),
    )
    return {
        **task,
        "status": "available",
        "product_count": summary.product_count,
        "data_points": summary.data_points,
        "time_start": summary.time_start,
        "time_end": summary.time_end,
        "from_cache": summary.from_cache,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/scaleup.yaml")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    summary = prefetch_scaleup(args.config)
    print(json.dumps({key: value for key, value in summary.items() if key != "targets"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
