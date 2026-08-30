"""Catalog cross-checking and leakage-safe end-to-end benchmarking."""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import joblib
import matplotlib
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import confusion_matrix

from src.model.features import FEATURE_COLUMNS, extract_candidate_features, fold_light_curve

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

LOGGER = logging.getLogger("sxs.catalog_check")


def match_catalog_period(
    candidate_period_days: float,
    planets: pd.DataFrame,
    *,
    tolerance_fraction: float = 0.01,
) -> dict[str, Any] | None:
    """Return the closest exact-period planet match, or ``None``."""

    usable = planets.dropna(subset=["period_days"])
    if usable.empty:
        return None
    errors = (usable["period_days"].astype(float) / float(candidate_period_days) - 1.0).abs()
    best_index = errors.idxmin()
    if float(errors.loc[best_index]) > tolerance_fraction:
        return None
    row = usable.loc[best_index]
    return {
        "matched_planet": str(row["pl_name"]),
        "catalog_period_days": float(row["period_days"]),
        "relative_period_error": float(errors.loc[best_index]),
    }


def catalog_check(config_path: str | Path = "configs/base.yaml") -> pd.DataFrame:
    """Score all transit-search candidates and classify their official-catalog status."""

    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    import tensorflow as tf

    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    tolerance = float(config["bls"]["match_tolerance_fraction"])
    bins = int(config["machine_learning"]["folded_bins"])
    confirmed = pd.read_parquet(config["catalog"]["output"])
    false_positive_catalog = pd.read_parquet(
        config["machine_learning"]["negative_sample"]["catalog_output"]
    )
    fp_ids = set(false_positive_catalog["target_id"].astype(str))
    target_hosts = {
        str(target["id"]): str(target.get("catalog_host", target["name"]))
        for target in config["targets"]
    }
    positive = pd.read_parquet("data/processed/bls_candidates.parquet").assign(
        candidate_source="validation_host"
    )
    negative = pd.read_parquet("data/processed/negative_bls_candidates.parquet").assign(
        candidate_source="official_false_positive_host"
    )
    candidates = pd.concat([positive, negative], ignore_index=True)
    features: list[dict[str, float]] = []
    views: list[np.ndarray] = []
    catalog_rows: list[dict[str, Any]] = []
    for _, candidate in candidates.iterrows():
        target_id = str(candidate["target_id"])
        processed = (
            Path("data/processed") / f"{target_id}_clean.parquet"
            if target_id in target_hosts
            else Path(config["machine_learning"]["negative_sample"]["processed_subdirectory"])
            / f"{target_id}_clean.parquet"
        )
        light_curve = pd.read_parquet(processed)
        features.append(extract_candidate_features(light_curve, candidate))
        views.append(fold_light_curve(light_curve, candidate, bins=bins))
        host = target_hosts.get(target_id)
        match = (
            match_catalog_period(
                float(candidate["period_days"]),
                confirmed.loc[confirmed["host_star_id"] == host],
                tolerance_fraction=tolerance,
            )
            if host is not None
            else None
        )
        if match:
            status = "recovered_known"
        elif target_id in fp_ids:
            status = "official_false_positive_system"
        else:
            status = "unvalidated_candidate_requires_independent_confirmation"
        catalog_rows.append(
            {
                "catalog_status": status,
                "matched_planet": match["matched_planet"] if match else None,
                "catalog_period_days": match["catalog_period_days"] if match else None,
                "relative_period_error": match["relative_period_error"] if match else None,
            }
        )

    feature_frame = pd.DataFrame(features)
    feature_model = joblib.load("models/feature_model.joblib")
    feature_probability = feature_model.predict_proba(
        feature_frame.loc[:, FEATURE_COLUMNS].to_numpy(dtype=float)
    )[:, 1]
    cnn_model = tf.keras.models.load_model("models/cnn_model.keras")
    cnn_probability = cnn_model.predict(np.stack(views)[..., np.newaxis], verbose=0).ravel()
    result = pd.concat(
        [
            candidates.reset_index(drop=True),
            pd.DataFrame(catalog_rows),
            feature_frame.add_prefix("feature_"),
        ],
        axis=1,
    )
    result.insert(0, "candidate_id", result.apply(lambda row: f"{row['target_id']}-r{int(row['rank'])}", axis=1))
    result["feature_probability"] = feature_probability
    result["feature_pass"] = feature_probability >= 0.5
    result["cnn_probability"] = cnn_probability
    result["cnn_pass"] = cnn_probability >= 0.5
    result["consensus_pass"] = result["feature_pass"] & result["cnn_pass"]
    result["score_provenance"] = "final_models_fit_on_full_model_benchmark_dataset_operational_not_benchmark"
    output = Path("data/processed/catalog_checked_candidates.parquet")
    result.to_parquet(output, index=False)
    result.loc[
        result["feature_pass"] | result["cnn_pass"],
        [
            "candidate_id",
            "target_id",
            "host_name",
            "rank",
            "period_days",
            "catalog_status",
            "matched_planet",
            "feature_probability",
            "feature_pass",
            "cnn_probability",
            "cnn_pass",
            "consensus_pass",
        ],
    ].to_csv("data/processed/passing_candidates.csv", index=False)
    LOGGER.info("Catalog-checked %d candidates", len(result))
    return result


def build_benchmark(config_path: str | Path = "configs/base.yaml") -> dict[str, Any]:
    """Compute out-of-fold vetting metrics and end-to-end catalog recall."""

    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    metadata = pd.read_csv("data/processed/ml_candidate_metadata.csv", dtype={"target_id": str})
    recovery = pd.read_csv("data/processed/bls_recovery.csv", dtype={"target_id": str})
    eligible_planets = int(recovery["eligible"].sum())
    detected_planets = int(recovery["matched_top5_exact"].sum())
    models: list[dict[str, Any]] = []

    bls_probability = np.ones(len(metadata), dtype=float)
    models.append(
        _benchmark_row("bls_only", metadata["label"].to_numpy(dtype=int), bls_probability, eligible_planets)
    )
    experiment_files = {
        "feature_model": Path("reports/experiments/feature_cv.json"),
        "cnn_1d": Path("reports/experiments/cnn_cv.json"),
    }
    for name, path in experiment_files.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        probabilities = {row["sample_id"]: row["probability"] for row in payload["out_of_fold_predictions"]}
        ordered = metadata["sample_id"].map(probabilities)
        if ordered.isna().any():
            raise RuntimeError(f"{name} is missing out-of-fold predictions")
        models.append(
            _benchmark_row(
                name,
                metadata["label"].to_numpy(dtype=int),
                ordered.to_numpy(dtype=float),
                eligible_planets,
            )
        )

    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation": {
            "period_domain_days": [
                float(config["bls"]["minimum_period_days"]),
                float(config["bls"]["maximum_period_days"]),
            ],
            "period_match_tolerance_fraction": float(config["bls"]["match_tolerance_fraction"]),
            "eligible_confirmed_planets": eligible_planets,
            "bls_detected_planets": detected_planets,
            "positive_vetting_candidates": int(metadata["label"].sum()),
            "official_false_positive_candidates": int((metadata["label"] == 0).sum()),
            "target_group_count": int(metadata["target_id"].nunique()),
            "model_predictions": "five-fold out-of-fold grouped by target_id",
        },
        "models": models,
    }
    Path("reports").mkdir(exist_ok=True)
    Path("reports/benchmark_metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    pd.DataFrame(
        [
            {
                "model": row["model"],
                **row["candidate_vetting_metrics"],
                "end_to_end_recovered_planets": row["end_to_end_recovered_planets"],
                "eligible_confirmed_planets": eligible_planets,
                "end_to_end_recall": row["end_to_end_recall"],
            }
            for row in models
        ]
    ).to_csv("reports/benchmark_metrics.csv", index=False)
    _plot_confusion_matrices(models, Path("reports/confusion_matrices.png"))
    _write_benchmark_report(result, Path("reports/benchmark_report.md"))
    return result


def _benchmark_row(
    name: str,
    labels: np.ndarray,
    probabilities: np.ndarray,
    eligible_planets: int,
) -> dict[str, Any]:
    predicted = probabilities >= 0.5
    tn, fp, fn, tp = confusion_matrix(labels, predicted, labels=[0, 1]).ravel()
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "model": name,
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "candidate_vetting_metrics": {
            "precision": precision,
            "recall": recall,
            "false_positive_rate": fpr,
            "f1": f1,
        },
        "end_to_end_recovered_planets": int(tp),
        "end_to_end_recall": float(tp / eligible_planets),
    }


def _plot_confusion_matrices(models: Sequence[dict[str, Any]], destination: Path) -> None:
    figure, axes = plt.subplots(1, len(models), figsize=(12, 3.7), constrained_layout=True)
    for axis, row in zip(axes, models, strict=True):
        counts = row["confusion_matrix"]
        matrix = np.array([[counts["tn"], counts["fp"]], [counts["fn"], counts["tp"]]])
        axis.imshow(matrix, cmap="Blues")
        for (y, x), value in np.ndenumerate(matrix):
            axis.text(x, y, str(value), ha="center", va="center", fontsize=13)
        axis.set(
            title=row["model"].replace("_", " "),
            xticks=[0, 1],
            xticklabels=["reject", "pass"],
            yticks=[0, 1],
            yticklabels=["official FP", "known transit"],
            xlabel="Predicted",
            ylabel="Reference",
        )
    figure.suptitle("Candidate-vetting confusion matrices — grouped out-of-fold predictions")
    figure.savefig(destination, dpi=180)
    plt.close(figure)


def _write_benchmark_report(result: dict[str, Any], destination: Path) -> None:
    evaluation = result["evaluation"]
    rows = result["models"]
    by_model = {row["model"]: row for row in rows}
    bls = by_model["bls_only"]
    rf = by_model["feature_model"]
    cnn = by_model["cnn_1d"]
    lower, upper = evaluation["period_domain_days"]
    tolerance = 100 * evaluation["period_match_tolerance_fraction"]
    lines = [
        "# SXS v1 Benchmark Report",
        "",
        "## Executive result",
        "",
        f"BLS recovered **{evaluation['bls_detected_planets']} of {evaluation['eligible_confirmed_planets']} eligible confirmed planets ({bls['end_to_end_recall']:.2%})** in the configured {lower:g}–{upper:g} day domain. "
        f"The target-grouped feature model retained {rf['end_to_end_recovered_planets']} planets ({rf['end_to_end_recall']:.2%} end-to-end recall) with candidate FPR {rf['candidate_vetting_metrics']['false_positive_rate']:.3f}. "
        f"The CNN retained {cnn['end_to_end_recovered_planets']} planets ({cnn['end_to_end_recall']:.2%}) with candidate FPR {cnn['candidate_vetting_metrics']['false_positive_rate']:.3f}.",
        "",
        "| Stage | Candidate precision | Candidate recall | Candidate FPR | Candidate F1 | End-to-end recall |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        metric = row["candidate_vetting_metrics"]
        lines.append(
            f"| {row['model']} | {metric['precision']:.3f} | {metric['recall']:.3f} | "
            f"{metric['false_positive_rate']:.3f} | {metric['f1']:.3f} | {row['end_to_end_recall']:.3f} |"
        )
    lines += [
        "",
        "![Candidate-vetting confusion matrices](confusion_matrices.png)",
        "",
        "## Evaluation contract",
        "",
        f"- Detection recall denominator: {evaluation['eligible_confirmed_planets']} confirmed planets inside the configured BLS domain. Out-of-domain planets are excluded before scoring.",
        f"- BLS recovery requires a proposed period within ±{tolerance:g}% of the official period; harmonic matches do not count in the primary metric.",
        f"- Vetting positives: {evaluation['positive_vetting_candidates']} exact BLS recoveries. Vetting negatives: {evaluation['official_false_positive_candidates']} candidates from official false-positive systems.",
        f"- Prediction provenance: {evaluation['model_predictions']}. No final-model training prediction is used in benchmark metrics.",
        "- Candidate FPR uses negative candidates as units. End-to-end recall uses confirmed planets as units; these denominators are intentionally reported separately.",
        "",
        "## Catalog cross-check",
        "",
        f"Every operational candidate is checked against the local provenance-bearing NASA Exoplanet Archive snapshot by configured host and ±{tolerance:g}% period. Matches are `recovered_known`; targets drawn from the official false-positive sample remain `official_false_positive_system`; other unmatched signals are `unvalidated_candidate_requires_independent_confirmation`.",
        "",
        "Operational probabilities in `catalog_checked_candidates.parquet` come from final models fitted on the complete model-benchmark dataset and are intended for pipeline execution only. They are not used for the benchmark table above.",
        "",
        "## Interpretation",
        "",
        "Candidate precision/FPR and end-to-end recovery measure different populations. A downstream classifier cannot recover a planet absent from the BLS proposal set. Compare the generated metrics above rather than assuming a fixed improvement across datasets.",
        "",
        "Model-selection conclusions require the recorded sample, fold-level evidence, and operating-point policy. The CNN uses held-out folds for early stopping; nested validation would provide a stricter assessment.",
        "",
        "## Limitations",
        "",
        "This benchmark is selected and Kepler-specific. Multiple candidates from a false-positive system create correlated rows; target grouping prevents cross-target leakage, not all model-selection bias. Positive and negative coverage can differ, thresholds are not independently calibrated, and catalog non-matches are not scientific discoveries. Unmatched outputs require independent follow-up.",
        "",
        "## Official data sources",
        "",
        "- NASA Exoplanet Archive TAP service: https://exoplanetarchive.ipac.caltech.edu/TAP/sync",
        "- Kepler KOI cumulative-table column definitions: https://exoplanetarchive.ipac.caltech.edu/docs/API_kepcandidate_columns.html",
        "- MAST Kepler light curves accessed through Lightkurve.",
        "",
    ]
    destination.write_text("\n".join(lines), encoding="utf-8")


def run_catalog_validation(config_path: str | Path = "configs/base.yaml") -> tuple[pd.DataFrame, dict[str, Any]]:
    checked = catalog_check(config_path)
    benchmark = build_benchmark(config_path)
    return checked, benchmark


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    checked, benchmark = run_catalog_validation(args.config)
    print(
        json.dumps(
            {
                "catalog_checked_candidates": len(checked),
                "catalog_status": checked["catalog_status"].value_counts().to_dict(),
                "models": benchmark["models"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
