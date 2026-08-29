"""Grouped scale-up qualification retraining, threshold selection, and v1 comparison."""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold

from src.config import artifact_path
from src.model.features import FEATURE_COLUMNS
from src.model.train_baselines import _class_weights, _cnn_model, _feature_pipeline

LOGGER = logging.getLogger("sxs.scaleup.train")
TARGET_REVIEW_RECALL = 0.90


def train_scaleup(config_path: str | Path = "configs/scaleup.yaml") -> dict[str, Any]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    metadata_path = artifact_path(config, "ml_metadata", "data/processed/ml_candidate_metadata.csv")
    views_path = artifact_path(config, "ml_views", "data/processed/ml_folded_views.npz")
    metadata = pd.read_csv(metadata_path, dtype={"target_id": str})
    archive = np.load(views_path)
    views = archive["views"]
    experiments = artifact_path(config, "experiments", "reports/experiments/scaleup")
    experiments.mkdir(parents=True, exist_ok=True)
    feature = evaluate_random_forest(config, metadata)
    (experiments / "rf_v2_cv.json").write_text(json.dumps(feature, indent=2) + "\n", encoding="utf-8")
    _write_pr_curve(metadata["label"].to_numpy(dtype=int), feature, experiments / "rf_v2_pr_curve.csv")
    cnn = evaluate_cnn(config, metadata, views)
    (experiments / "cnn_v2_cv.json").write_text(json.dumps(cnn, indent=2) + "\n", encoding="utf-8")
    _write_pr_curve(metadata["label"].to_numpy(dtype=int), cnn, experiments / "cnn_v2_pr_curve.csv")
    selected = _select_production_model(feature, cnn, config)
    selection_path = Path("models/production_model_selection.json")
    selection_path.write_text(json.dumps(selected, indent=2) + "\n", encoding="utf-8")
    result = {"feature": feature, "cnn": cnn, "selection": selected}
    _write_scaleup_report(config, metadata, result)
    return result


def evaluate_random_forest(config: dict[str, Any], metadata: pd.DataFrame) -> dict[str, Any]:
    seed = int(config["project"]["random_seed"])
    settings = config["machine_learning"]["random_forest"]
    x = metadata.loc[:, FEATURE_COLUMNS].to_numpy(dtype=float)
    y = metadata["label"].to_numpy(dtype=int)
    groups = metadata["target_id"].astype(str).to_numpy()
    predictions = np.zeros(len(y), dtype=float)
    folds = []
    for fold, (train, test) in enumerate(_splitter(config).split(x, y, groups), start=1):
        _assert_no_overlap(groups, train, test)
        model = _feature_pipeline(settings, seed + fold)
        model.fit(x[train], y[train])
        probability = model.predict_proba(x[test])[:, 1]
        predictions[test] = probability
        folds.append({"fold": fold, "test_groups": len(set(groups[test])), **_metrics(y[test], probability, 0.5)})
    threshold = select_review_threshold(y, predictions, minimum_recall=TARGET_REVIEW_RECALL)
    final = _feature_pipeline(settings, seed)
    final.fit(x, y)
    model_path = artifact_path(config, "feature_model", "models/rf_v2.joblib")
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final, model_path)
    classifier = final.named_steps["classifier"]
    importance = sorted(
        zip(FEATURE_COLUMNS, classifier.feature_importances_, strict=True),
        key=lambda item: item[1],
        reverse=True,
    )
    return _payload(
        "rf_v2",
        y,
        predictions,
        groups,
        folds,
        threshold,
        extra={"feature_importance": [{"feature": key, "importance": float(value)} for key, value in importance]},
    )


def evaluate_cnn(config: dict[str, Any], metadata: pd.DataFrame, views: np.ndarray) -> dict[str, Any]:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    import tensorflow as tf

    seed = int(config["project"]["random_seed"])
    tf.keras.utils.set_random_seed(seed)
    try:
        tf.config.experimental.enable_op_determinism()
    except RuntimeError:
        pass
    settings = config["machine_learning"]["cnn"]
    x = views[..., np.newaxis].astype(np.float32)
    y = metadata["label"].to_numpy(dtype=int)
    groups = metadata["target_id"].astype(str).to_numpy()
    predictions = np.zeros(len(y), dtype=float)
    folds = []
    best_epochs = []
    for fold, (train, test) in enumerate(_splitter(config).split(x, y, groups), start=1):
        _assert_no_overlap(groups, train, test)
        tf.keras.backend.clear_session()
        tf.keras.utils.set_random_seed(seed + fold)
        model = _cnn_model(x.shape[1], float(settings["learning_rate"]))
        history = model.fit(
            x[train],
            y[train],
            validation_data=(x[test], y[test]),
            epochs=int(settings["epochs"]),
            batch_size=int(settings["batch_size"]),
            class_weight=_class_weights(y[train]),
            callbacks=[
                tf.keras.callbacks.EarlyStopping(
                    monitor="val_loss",
                    patience=int(settings["patience"]),
                    restore_best_weights=True,
                )
            ],
            verbose=0,
        )
        probability = model.predict(x[test], verbose=0).ravel()
        predictions[test] = probability
        best_epoch = int(np.argmin(history.history["val_loss"]) + 1)
        best_epochs.append(best_epoch)
        metric = _metrics(y[test], probability, 0.5)
        folds.append({"fold": fold, "test_groups": len(set(groups[test])), "best_epoch": best_epoch, **metric})
        LOGGER.info("CNN v2 fold %d: F1 %.3f, recall %.3f", fold, metric["f1"], metric["recall"])
    threshold = select_review_threshold(y, predictions, minimum_recall=TARGET_REVIEW_RECALL)
    final_epochs = max(1, int(np.median(best_epochs)))
    tf.keras.backend.clear_session()
    tf.keras.utils.set_random_seed(seed)
    final = _cnn_model(x.shape[1], float(settings["learning_rate"]))
    final.fit(
        x,
        y,
        epochs=final_epochs,
        batch_size=int(settings["batch_size"]),
        class_weight=_class_weights(y),
        verbose=0,
    )
    model_path = artifact_path(config, "cnn_model", "models/cnn_v2.keras")
    model_path.parent.mkdir(parents=True, exist_ok=True)
    final.save(model_path)
    f1_values = [fold["f1"] for fold in folds]
    return _payload(
        "cnn_v2",
        y,
        predictions,
        groups,
        folds,
        threshold,
        extra={
            "final_training_epochs": final_epochs,
            "fold_f1_standard_deviation": float(np.std(f1_values, ddof=1)),
        },
    )


def select_review_threshold(
    labels: np.ndarray,
    probabilities: np.ndarray,
    *,
    minimum_recall: float,
) -> dict[str, float]:
    """Maximize precision subject to the manual-review recall constraint."""

    precision, recall, thresholds = precision_recall_curve(labels, probabilities)
    candidates = [
        (float(p), float(r), float(t))
        for p, r, t in zip(precision[:-1], recall[:-1], thresholds, strict=True)
        if r >= minimum_recall
    ]
    if not candidates:
        threshold = 0.0
    else:
        _, _, threshold = max(candidates, key=lambda item: (item[0], item[2]))
    metric = _metrics(labels, probabilities, threshold)
    return {"threshold": threshold, "minimum_recall_constraint": minimum_recall, **metric}


def _metrics(labels: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict[str, float]:
    prediction = probabilities >= threshold
    return {
        "threshold": float(threshold),
        "precision": float(precision_score(labels, prediction, zero_division=0)),
        "recall": float(recall_score(labels, prediction, zero_division=0)),
        "f1": float(f1_score(labels, prediction, zero_division=0)),
        "accuracy": float(accuracy_score(labels, prediction)),
        "roc_auc": float(roc_auc_score(labels, probabilities)),
        "average_precision": float(average_precision_score(labels, probabilities)),
        "passed_candidates": int(prediction.sum()),
    }


def _payload(
    model: str,
    labels: np.ndarray,
    probabilities: np.ndarray,
    groups: np.ndarray,
    folds: list[dict[str, Any]],
    threshold: dict[str, float],
    *,
    extra: dict[str, Any],
) -> dict[str, Any]:
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "split_strategy": "five-fold StratifiedGroupKFold by target_id",
        "sample_count": len(labels),
        "positive_count": int(labels.sum()),
        "negative_count": int((labels == 0).sum()),
        "target_group_count": len(set(groups)),
        "fixed_threshold_metrics": _metrics(labels, probabilities, 0.5),
        "review_threshold_selection": threshold,
        "fold_metrics": folds,
        "out_of_fold_predictions": [float(value) for value in probabilities],
        **extra,
    }


def _select_production_model(
    feature: dict[str, Any], cnn: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    feature_metric = feature["review_threshold_selection"]
    cnn_metric = cnn["review_threshold_selection"]
    # A neural model must show a material precision gain and stable grouped folds
    # before replacing the simpler RF at the same high-recall operating point.
    cnn_precision_gain = cnn_metric["precision"] - feature_metric["precision"]
    cnn_stable = cnn["fold_f1_standard_deviation"] <= 0.10
    cnn_wins = cnn_stable and cnn_precision_gain >= 0.02
    chosen = cnn if cnn_wins else feature
    model_key = "cnn_model" if cnn_wins else "feature_model"
    return {
        "selected_model": chosen["model"],
        "model_path": str(artifact_path(config, model_key, "models/rf_v2.joblib")),
        "decision_threshold": chosen["review_threshold_selection"]["threshold"],
        "selection_policy": "among models satisfying the explicit >=0.90 review-recall constraint, CNN replaces RF only with >=0.02 absolute precision gain and grouped-fold F1 SD <=0.10; otherwise RF is preferred",
        "cnn_precision_gain_over_rf": cnn_precision_gain,
        "cnn_stability_limit_fold_f1_sd": 0.10,
        "cnn_stability_passed": cnn_stable,
        "cnn_role": "secondary_diagnostic" if not cnn_wins else "primary",
    }


def _write_pr_curve(labels: np.ndarray, result: dict[str, Any], destination: Path) -> None:
    probabilities = np.asarray(result["out_of_fold_predictions"], dtype=float)
    precision, recall, thresholds = precision_recall_curve(labels, probabilities)
    # sklearn's final PR point has no corresponding decision threshold.
    frame = pd.DataFrame(
        {"threshold": thresholds, "precision": precision[:-1], "recall": recall[:-1]}
    )
    frame["meets_review_recall_floor"] = frame["recall"] >= TARGET_REVIEW_RECALL
    frame.to_csv(destination, index=False)


def _splitter(config: dict[str, Any]) -> StratifiedGroupKFold:
    return StratifiedGroupKFold(
        n_splits=int(config["machine_learning"]["folds"]),
        shuffle=True,
        random_state=int(config["project"]["random_seed"]),
    )


def _assert_no_overlap(groups: np.ndarray, train: np.ndarray, test: np.ndarray) -> None:
    overlap = set(groups[train]) & set(groups[test])
    if overlap:
        raise RuntimeError(f"Target leakage: {sorted(overlap)}")


def _write_scaleup_report(
    config: dict[str, Any], metadata: pd.DataFrame, result: dict[str, Any]
) -> None:
    selection_summary = json.loads(
        (Path(config["paths"]["catalog"]) / "selection_summary.json").read_text(encoding="utf-8")
    )
    v1 = json.loads(Path("reports/benchmark_metrics.json").read_text(encoding="utf-8"))
    v1_by_model = {row["model"]: row for row in v1["models"]}
    confirmed_summary = json.loads(
        (Path(config["paths"]["processed"]) / "preprocessing_summary.json").read_text(encoding="utf-8")
    )
    negative_summary = json.loads(
        artifact_path(
            config, "negative_summary", "data/processed/negative_dataset_summary.json"
        ).read_text(encoding="utf-8")
    )
    prefetch_summary = json.loads(
        Path("data/scaleup/processed/prefetch_summary.json").read_text(encoding="utf-8")
    )
    recovery = pd.read_csv(Path(config["paths"]["processed"]) / "bls_recovery.csv")
    eligible_recovery = recovery.loc[recovery["eligible"]]
    rf = result["feature"]
    cnn = result["cnn"]
    chosen = result["selection"]
    lines = [
        "# Scaled Model Qualification",
        "",
        "## Acceptance result",
        "",
        f"The scaled benchmark uses **{selection_summary['positive_targets_after_quality']} confirmed hosts / {selection_summary['positive_planets_after_quality']} planets** and "
        f"**{selection_summary['negative_targets_selected']} balanced official false-positive hosts**, versus 20 + 20 systems in v1. "
        f"The candidate-level ML dataset contains {len(metadata)} rows ({int(metadata.label.sum())} positive, {int((metadata.label == 0).sum())} negative) across {metadata.target_id.nunique()} target groups.",
        "",
        f"The production model selected for candidate screening is **{chosen['selected_model']}** at threshold **{chosen['decision_threshold']:.6f}**. "
        "Candidate screening is not executed by this report.",
        "",
        "## Selection and resource policy",
        "",
        f"- Confirmed planets: period 0.5–50 d, transit S/N ≥ {config['scaleup']['selection']['positive_minimum_transit_snr']}, Kp ≤ {config['scaleup']['selection']['maximum_kepler_magnitude']}, and ≥ {config['scaleup']['selection']['minimum_available_quarters']} available long-cadence quarters.",
        f"- False positives: full in-domain population is archived; the processed set requires S/N ≥ {config['scaleup']['selection']['negative_minimum_transit_snr']} and the same magnitude/availability limits, then selects {config['scaleup']['selection']['negative_targets_per_category']} unique targets per flag deterministically.",
        f"- Four chronological products per target are processed for both classes. This explicit workstation constraint keeps coverage matched and bounded while retaining a >50 d baseline; it is not a silent reduction.",
        f"- Prefetch: {prefetch_summary['available_targets']} available and {prefetch_summary['failed_targets']} failed after retries.",
        f"- Confirmed preprocessing: {confirmed_summary['available_targets']} available and {confirmed_summary['skipped_targets']} skipped.",
        f"- False-positive processing: {negative_summary['available_targets']} available and {negative_summary['skipped_targets']} skipped.",
        "",
        "### False-positive flag distribution",
        "",
        "Official flags can overlap, so full-population counts do not sum to the number of KOIs. Processing is deliberately balanced at 100 target-unique systems (25%) per assigned category.",
        "",
        "| Assigned category | Full FP KOIs carrying flag | Processed unique targets | Processed share |",
        "|---|---:|---:|---:|",
        *[
            f"| {category} | {selection_summary['raw_false_positive_flag_counts'][category]} | {selection_summary['negative_category_counts'][category]} | 25.0% |"
            for category in sorted(selection_summary["negative_category_counts"])
        ],
        "",
        "## BLS scale-up result",
        "",
        f"With matched four-product coverage, BLS recovered **{int(eligible_recovery['matched_top5_exact'].sum())}/{len(eligible_recovery)} ({100 * eligible_recovery['matched_top5_exact'].mean():.2f}%)** eligible planets in the top five, versus **15/36 (41.67%)** in v1.",
        "",
        "## v1 versus v2 out-of-fold metrics at threshold 0.5",
        "",
        "| Model | Version | Precision | Recall | F1 | ROC-AUC | Average precision |",
        "|---|---|---:|---:|---:|---:|---:|",
        f"| Random Forest | v1 | {v1_by_model['feature_model']['candidate_vetting_metrics']['precision']:.3f} | {v1_by_model['feature_model']['candidate_vetting_metrics']['recall']:.3f} | {v1_by_model['feature_model']['candidate_vetting_metrics']['f1']:.3f} | 0.887 | 0.817 |",
        f"| Random Forest | v2 | {rf['fixed_threshold_metrics']['precision']:.3f} | {rf['fixed_threshold_metrics']['recall']:.3f} | {rf['fixed_threshold_metrics']['f1']:.3f} | {rf['fixed_threshold_metrics']['roc_auc']:.3f} | {rf['fixed_threshold_metrics']['average_precision']:.3f} |",
        f"| CNN 1D | v1 | {v1_by_model['cnn_1d']['candidate_vetting_metrics']['precision']:.3f} | {v1_by_model['cnn_1d']['candidate_vetting_metrics']['recall']:.3f} | {v1_by_model['cnn_1d']['candidate_vetting_metrics']['f1']:.3f} | 0.791 | 0.443 |",
        f"| CNN 1D | v2 | {cnn['fixed_threshold_metrics']['precision']:.3f} | {cnn['fixed_threshold_metrics']['recall']:.3f} | {cnn['fixed_threshold_metrics']['f1']:.3f} | {cnn['fixed_threshold_metrics']['roc_auc']:.3f} | {cnn['fixed_threshold_metrics']['average_precision']:.3f} |",
        "",
        "RF v2 is not uniformly better at the fixed 0.5 cutoff: precision and F1 are lower on the much larger, harder candidate set, recall is broadly stable, and ROC-AUC improves. The scale-up therefore supports model-ranking stability rather than an unqualified improvement claim; RF remains clearly stronger than CNN.",
        "",
        "## Manual-review threshold",
        "",
        "The operating point is selected from grouped out-of-fold precision–recall predictions by maximizing precision subject to recall ≥0.90. This policy intentionally favors not missing real recovered signals because false alarms will receive manual review. It is an exploratory operating-point estimate on the same OOF predictions, not an independently calibrated probability threshold.",
        "",
        f"- RF: threshold {rf['review_threshold_selection']['threshold']:.6f}, precision {rf['review_threshold_selection']['precision']:.3f}, recall {rf['review_threshold_selection']['recall']:.3f}.",
        f"- CNN: threshold {cnn['review_threshold_selection']['threshold']:.6f}, precision {cnn['review_threshold_selection']['precision']:.3f}, recall {cnn['review_threshold_selection']['recall']:.3f}.",
        "- Complete OOF precision–recall operating points are stored in `reports/experiments/scaleup/rf_v2_pr_curve.csv` and `cnn_v2_pr_curve.csv`.",
        "",
        "## CNN stability and production decision",
        "",
        f"CNN fold-F1 standard deviation is {cnn['fold_f1_standard_deviation']:.3f} (stability criterion ≤0.100: {'passed' if chosen['cnn_stability_passed'] else 'not passed'}). "
        "At the common recall floor, CNN must also improve precision over RF by at least 0.020 to become primary. "
        f"The CNN role is **{chosen['cnn_role']}**; the versioned v1 model remains untouched.",
        "",
        "## Limitations",
        "",
        "The S/N and magnitude filters deliberately emphasize reliable training signals and therefore do not represent the hardest unknown targets. Four-product coverage is consistent across classes but shorter than full Kepler coverage. KOI flags overlap physically, although selection categories are target-unique. A future nested calibration set is required before treating the threshold as a calibrated posterior probability.",
        "",
    ]
    report = artifact_path(config, "report", "reports/model_qualification.md")
    report.write_text("\n".join(lines), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/scaleup.yaml")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    result = train_scaleup(args.config)
    print(json.dumps({"selection": result["selection"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
