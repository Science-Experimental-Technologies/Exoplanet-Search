"""Download, preprocess, and search the official Kepler false-positive sample."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import pandas as pd
import yaml
from src.config import artifact_path

from src.detect.bls_search import _write_parquet, search_light_curve
from src.ingest.mast_client import DownloadError, MastLightCurveClient, TargetNotFoundError
from src.preprocess.build_processed import _write_processed_parquet
from src.preprocess.clean import clean_light_curve_files
from src.preprocess.detrend import detrend_light_curve

LOGGER = logging.getLogger("sxs.negative_dataset")


def build_negative_dataset(config_path: str | Path = "configs/base.yaml") -> pd.DataFrame:
    """Run the same acquisition, preprocessing, and BLS steps used for positives."""

    config_file = Path(config_path)
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    ml = config["machine_learning"]
    settings = ml["negative_sample"]
    catalog = pd.read_parquet(settings["catalog_output"])
    raw_dir = Path(settings["raw_subdirectory"])
    processed_dir = Path(settings["processed_subdirectory"])
    processed_dir.mkdir(parents=True, exist_ok=True)
    client = MastLightCurveClient(raw_dir)
    preprocessing = config["preprocess"]
    bls = config["bls"]
    candidate_frames: list[pd.DataFrame] = []
    status_rows: list[dict[str, Any]] = []

    for index, row in catalog.iterrows():
        target_id = str(row["target_id"])
        name = str(row["koi_name"])
        LOGGER.info("[%d/%d] Negative target %s (KIC %s)", index + 1, len(catalog), name, target_id)
        try:
            download = client.fetch(
                target_id,
                id_type="KIC",
                mission=config["ingest"]["mission"],
                author=config["ingest"]["author"],
                cadence=config["ingest"]["cadence"],
                max_products=settings.get("max_products"),
            )
            cleaned, stats = clean_light_curve_files(
                download.files,
                quality_bitmask=int(preprocessing["quality_bitmask"]),
                sigma_lower=float(preprocessing["sigma_lower"]),
                sigma_upper=float(preprocessing["sigma_upper"]),
                sigma_maxiters=int(preprocessing["sigma_maxiters"]),
                max_gap_cadences=int(preprocessing["max_gap_cadences"]),
            )
            processed = detrend_light_curve(
                cleaned,
                window_length=int(preprocessing["flatten_window_length"]),
                polyorder=int(preprocessing["flatten_polyorder"]),
                break_tolerance=int(preprocessing["flatten_break_tolerance"]),
                niters=int(preprocessing["flatten_niters"]),
                sigma=float(preprocessing["flatten_sigma"]),
            )
            output = processed_dir / f"{target_id}_clean.parquet"
            _write_processed_parquet(
                processed,
                output,
                metadata={
                    "target_id": target_id,
                    "host_name": name,
                    "mission": "Kepler",
                    "time_system": "BKJD",
                    "catalog_retrieved_at_utc": str(row["catalog_retrieved_at_utc"]),
                    "preprocessing_parameters": json.dumps(preprocessing, sort_keys=True),
                    "label_source": "official Kepler cumulative KOI false positive",
                },
            )
            candidates, detail = search_light_curve(
                processed,
                minimum_period_days=float(bls["minimum_period_days"]),
                maximum_period_days=float(bls["maximum_period_days"]),
                durations_hours=bls["durations_hours"],
                top_k=int(bls["top_k"]),
                frequency_oversampling=float(bls["frequency_oversampling"]),
                duration_oversampling=int(bls["duration_oversampling"]),
                minimum_peak_separation_fraction=float(bls["minimum_peak_separation_fraction"]),
                include_interpolated=bool(bls["include_interpolated"]),
                objective=str(bls["objective"]),
                method=str(bls["method"]),
            )
            candidates.insert(0, "negative_category", row["negative_category"])
            candidates.insert(0, "host_name", name)
            candidates.insert(0, "target_id", target_id)
            candidate_frames.append(candidates)
            status_rows.append(
                {
                    "target_id": target_id,
                    "koi_name": name,
                    "negative_category": row["negative_category"],
                    "status": "available",
                    "product_count": download.product_count,
                    "output_points": len(processed),
                    "outliers_removed": stats.outliers_removed,
                    **detail,
                }
            )
        except (ValueError, TargetNotFoundError, DownloadError, OSError) as exc:
            LOGGER.error("Skipping %s: %s", name, exc)
            status_rows.append(
                {
                    "target_id": target_id,
                    "koi_name": name,
                    "negative_category": row["negative_category"],
                    "status": "skipped",
                    "reason": str(exc),
                }
            )

    if not candidate_frames:
        raise RuntimeError("No negative target produced BLS candidates")
    candidates = pd.concat(candidate_frames, ignore_index=True)
    candidate_output = artifact_path(
        config, "negative_candidates", "data/processed/negative_bls_candidates.parquet"
    )
    candidate_output.parent.mkdir(parents=True, exist_ok=True)
    _write_parquet(candidates, candidate_output, config_file, bls)
    status = pd.DataFrame(status_rows)
    summary_output = artifact_path(
        config, "negative_summary", "data/processed/negative_dataset_summary.json"
    )
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(
        json.dumps(
            {
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "configured_targets": len(catalog),
                "available_targets": int((status["status"] == "available").sum()),
                "skipped_targets": int((status["status"] != "available").sum()),
                "candidate_rows": len(candidates),
                "targets": status.where(pd.notna(status), None).to_dict(orient="records"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return candidates


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    try:
        candidates = build_negative_dataset(args.config)
    except Exception as exc:
        LOGGER.exception("Negative dataset build failed: %s", exc)
        return 2
    print(json.dumps({"candidate_rows": len(candidates), "targets": candidates["target_id"].nunique()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
