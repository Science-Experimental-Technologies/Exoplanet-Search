"""Validated concurrent prefetch for the frozen candidate screening target sample."""

from __future__ import annotations

import argparse
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import yaml

from src.ingest.mast_client import MastLightCurveClient

LOGGER = logging.getLogger("sxs.candidate_search.prefetch")


def prefetch(config_path: str | Path = "configs/candidate_search.yaml") -> dict[str, Any]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    artifacts = config["candidate_search"]["artifacts"]
    targets = yaml.safe_load(Path(artifacts["selected_targets"]).read_text(encoding="utf-8"))["targets"]
    pending = [{"target_id": str(target["id"])} for target in targets]
    results: dict[str, dict[str, Any]] = {}
    for attempt, workers in enumerate((2, 1, 1), start=1):
        if not pending:
            break
        LOGGER.info("Attempt %d: %d targets with %d worker(s)", attempt, len(pending), workers)
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="sxs-search-mast") as executor:
            futures = {executor.submit(_fetch, task["target_id"], config): task for task in pending}
            for completed, future in enumerate(as_completed(futures), start=1):
                task = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = {**task, "status": "failed", "reason": str(exc)}
                results[task["target_id"]] = result
                if completed % 25 == 0:
                    LOGGER.info("Attempt %d progress %d/%d", attempt, completed, len(pending))
        pending = [
            {"target_id": target_id}
            for target_id, result in results.items()
            if result["status"] != "available"
        ]
    ordered = [results[str(target["id"])] for target in targets]
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "configured_targets": len(targets),
        "available_targets": sum(row["status"] == "available" for row in ordered),
        "failed_targets": sum(row["status"] != "available" for row in ordered),
        "targets": ordered,
    }
    output = Path("data/search/processed/prefetch_summary.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def _fetch(target_id: str, config: dict[str, Any]) -> dict[str, Any]:
    summary = MastLightCurveClient(config["paths"]["raw"]).fetch(
        target_id,
        id_type="KIC",
        mission=config["ingest"]["mission"],
        author=config["ingest"]["author"],
        cadence=config["ingest"]["cadence"],
        max_products=int(config["ingest"]["max_products"]),
    )
    return {
        "target_id": target_id,
        "status": "available",
        "product_count": summary.product_count,
        "from_cache": summary.from_cache,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/candidate_search.yaml")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    summary = prefetch(args.config)
    print(json.dumps({key: value for key, value in summary.items() if key != "targets"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
