"""Build the labeled feature matrix and folded tensors for Phase 4."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
import yaml

from src.model.features import FEATURE_COLUMNS, extract_candidate_features, fold_light_curve
from src.config import artifact_path, load_targets

LOGGER = logging.getLogger("sxs.ml_dataset")


def build_ml_dataset(config_path: str | Path = "configs/base.yaml") -> tuple[pd.DataFrame, np.ndarray]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    bins = int(config["machine_learning"]["folded_bins"])
    processed_dir = Path(config["paths"]["processed"])
    positive_candidates = pd.read_parquet(processed_dir / "bls_candidates.parquet")
    negative_candidates = pd.read_parquet(
        artifact_path(config, "negative_candidates", "data/processed/negative_bls_candidates.parquet")
    )
    recovery = pd.read_csv(processed_dir / "bls_recovery.csv", dtype={"target_id": str})
    matched = recovery.loc[recovery["matched_top5_exact"]].copy()
    positive_keys = {
        (str(row.target_id), int(row.best_candidate_rank)): str(row.planet_name)
        for row in matched.itertuples()
    }

    rows: list[dict[str, object]] = []
    views: list[np.ndarray] = []
    for source, candidates, label in (
        ("recovered_confirmed_planet", positive_candidates, 1),
        ("official_kepler_false_positive", negative_candidates, 0),
    ):
        for _, candidate in candidates.iterrows():
            target_id = str(candidate["target_id"])
            rank = int(candidate["rank"])
            if label == 1 and (target_id, rank) not in positive_keys:
                continue
            light_curve_path = (
                processed_dir / f"{target_id}_clean.parquet"
                if label == 1
                else Path(config["machine_learning"]["negative_sample"]["processed_subdirectory"])
                / f"{target_id}_clean.parquet"
            )
            light_curve = pd.read_parquet(light_curve_path)
            features = extract_candidate_features(light_curve, candidate)
            view = fold_light_curve(light_curve, candidate, bins=bins)
            rows.append(
                {
                    "sample_id": f"{target_id}-r{rank}",
                    "target_id": target_id,
                    "host_name": candidate["host_name"],
                    "candidate_rank": rank,
                    "label": label,
                    "label_source": source,
                    "matched_planet": positive_keys.get((target_id, rank)),
                    "negative_category": candidate.get("negative_category"),
                    **features,
                }
            )
            views.append(view)
    metadata = pd.DataFrame(rows)
    tensors = np.stack(views).astype(np.float32)
    if metadata["target_id"].nunique() < int(config["machine_learning"]["folds"]):
        raise RuntimeError("Not enough independent target groups for configured cross-validation")
    metadata_path = artifact_path(config, "ml_metadata", "data/processed/ml_candidate_metadata.csv")
    features_path = artifact_path(config, "ml_features", "data/processed/ml_features.parquet")
    views_path = artifact_path(config, "ml_views", "data/processed/ml_folded_views.npz")
    for output in (metadata_path, features_path, views_path):
        output.parent.mkdir(parents=True, exist_ok=True)
    metadata.to_csv(metadata_path, index=False)
    metadata.loc[:, ["sample_id", "target_id", "label", *FEATURE_COLUMNS]].to_parquet(
        features_path, index=False
    )
    np.savez_compressed(
        views_path,
        views=tensors,
        labels=metadata["label"].to_numpy(dtype=np.int8),
        groups=metadata["target_id"].astype(str).to_numpy(),
        sample_ids=metadata["sample_id"].to_numpy(),
    )
    LOGGER.info(
        "Built %d candidates (%d positive, %d negative) from %d target groups",
        len(metadata),
        int(metadata["label"].sum()),
        int((metadata["label"] == 0).sum()),
        metadata["target_id"].nunique(),
    )
    return metadata, tensors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    metadata, tensors = build_ml_dataset(args.config)
    print(json.dumps({"samples": len(metadata), "shape": list(tensors.shape), "labels": metadata.label.value_counts().to_dict()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
