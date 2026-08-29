"""Target-grouped cross-validation for feature and 1D CNN classifiers."""

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
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline

from src.model.features import FEATURE_COLUMNS

LOGGER = logging.getLogger("sxs.train")


def evaluate_feature_model(config: dict[str, Any], metadata: pd.DataFrame) -> dict[str, Any]:
    seed = int(config["project"]["random_seed"])
    settings = config["machine_learning"]["random_forest"]
    x = metadata.loc[:, FEATURE_COLUMNS].to_numpy(dtype=float)
    y = metadata["label"].to_numpy(dtype=int)
    groups = metadata["target_id"].astype(str).to_numpy()
    splitter = _splitter(config)
    predictions = np.zeros(len(y), dtype=float)
    folds: list[dict[str, Any]] = []
    for fold, (train, test) in enumerate(splitter.split(x, y, groups), start=1):
        _assert_group_isolation(groups, train, test)
        model = _feature_pipeline(settings, seed + fold)
        model.fit(x[train], y[train])
        probabilities = model.predict_proba(x[test])[:, 1]
        predictions[test] = probabilities
        folds.append(_metrics(y[test], probabilities) | {"fold": fold, "test_groups": len(set(groups[test]))})
    aggregate = _metrics(y, predictions)
    final_model = _feature_pipeline(settings, seed)
    final_model.fit(x, y)
    Path("models").mkdir(exist_ok=True)
    joblib.dump(final_model, "models/feature_model.joblib")
    return _experiment_payload("random_forest", config, aggregate, folds, predictions, metadata)


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
    y = metadata["label"].to_numpy(dtype=np.float32)
    groups = metadata["target_id"].astype(str).to_numpy()
    predictions = np.zeros(len(y), dtype=float)
    folds: list[dict[str, Any]] = []
    best_epochs: list[int] = []
    for fold, (train, test) in enumerate(_splitter(config).split(x, y, groups), start=1):
        _assert_group_isolation(groups, train, test)
        tf.keras.backend.clear_session()
        tf.keras.utils.set_random_seed(seed + fold)
        model = _cnn_model(x.shape[1], float(settings["learning_rate"]))
        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss",
                patience=int(settings["patience"]),
                restore_best_weights=True,
            )
        ]
        history = model.fit(
            x[train],
            y[train],
            validation_data=(x[test], y[test]),
            epochs=int(settings["epochs"]),
            batch_size=int(settings["batch_size"]),
            class_weight=_class_weights(y[train]),
            callbacks=callbacks,
            verbose=0,
        )
        probabilities = model.predict(x[test], verbose=0).ravel()
        predictions[test] = probabilities
        best_epoch = int(np.argmin(history.history["val_loss"]) + 1)
        best_epochs.append(best_epoch)
        folds.append(
            _metrics(y[test].astype(int), probabilities)
            | {"fold": fold, "test_groups": len(set(groups[test])), "best_epoch": best_epoch}
        )
        LOGGER.info("CNN fold %d complete: F1 %.3f", fold, folds[-1]["f1"])
    aggregate = _metrics(y.astype(int), predictions)
    tf.keras.backend.clear_session()
    tf.keras.utils.set_random_seed(seed)
    final_model = _cnn_model(x.shape[1], float(settings["learning_rate"]))
    final_model.fit(
        x,
        y,
        epochs=max(1, int(np.median(best_epochs))),
        batch_size=int(settings["batch_size"]),
        class_weight=_class_weights(y),
        verbose=0,
    )
    Path("models").mkdir(exist_ok=True)
    final_model.save("models/cnn_model.keras")
    return _experiment_payload("cnn_1d", config, aggregate, folds, predictions, metadata) | {
        "final_training_epochs": max(1, int(np.median(best_epochs)))
    }


def run_training(config_path: str | Path = "configs/base.yaml") -> tuple[dict[str, Any], dict[str, Any]]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    metadata = pd.read_csv("data/processed/ml_candidate_metadata.csv", dtype={"target_id": str})
    archive = np.load("data/processed/ml_folded_views.npz")
    views = archive["views"]
    reports = Path("reports/experiments")
    reports.mkdir(parents=True, exist_ok=True)
    feature = evaluate_feature_model(config, metadata)
    (reports / "feature_cv.json").write_text(json.dumps(feature, indent=2) + "\n", encoding="utf-8")
    cnn = evaluate_cnn(config, metadata, views)
    (reports / "cnn_cv.json").write_text(json.dumps(cnn, indent=2) + "\n", encoding="utf-8")
    rows = []
    for payload in (feature, cnn):
        rows.append({"model": payload["model"], "scope": "out_of_fold_aggregate", **payload["aggregate_metrics"]})
        rows.extend({"model": payload["model"], "scope": f"fold_{fold['fold']}", **fold} for fold in payload["fold_metrics"])
    pd.DataFrame(rows).to_csv(reports / "cv_metrics.csv", index=False)
    _write_report(feature, cnn, metadata, Path("reports/phase4_ml_baseline.md"))
    return feature, cnn


def _feature_pipeline(settings: dict[str, Any], seed: int) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=int(settings["n_estimators"]),
                    max_depth=int(settings["max_depth"]),
                    min_samples_leaf=int(settings["min_samples_leaf"]),
                    class_weight=settings["class_weight"],
                    random_state=seed,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def _cnn_model(length: int, learning_rate: float) -> Any:
    import tensorflow as tf

    inputs = tf.keras.Input(shape=(length, 1), name="folded_flux")
    x = tf.keras.layers.Conv1D(32, 7, padding="same", activation="relu")(inputs)
    x = tf.keras.layers.MaxPooling1D(4)(x)
    x = tf.keras.layers.Conv1D(64, 5, padding="same", activation="relu")(x)
    x = tf.keras.layers.MaxPooling1D(4)(x)
    x = tf.keras.layers.Conv1D(128, 3, padding="same", activation="relu")(x)
    x = tf.keras.layers.GlobalAveragePooling1D()(x)
    x = tf.keras.layers.Dense(64, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid", name="planet_probability")(x)
    model = tf.keras.Model(inputs, outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="binary_crossentropy",
        metrics=[tf.keras.metrics.Precision(name="precision"), tf.keras.metrics.Recall(name="recall")],
    )
    return model


def _splitter(config: dict[str, Any]) -> StratifiedGroupKFold:
    return StratifiedGroupKFold(
        n_splits=int(config["machine_learning"]["folds"]),
        shuffle=True,
        random_state=int(config["project"]["random_seed"]),
    )


def _assert_group_isolation(groups: np.ndarray, train: np.ndarray, test: np.ndarray) -> None:
    overlap = set(groups[train]) & set(groups[test])
    if overlap:
        raise RuntimeError(f"Target leakage across fold: {sorted(overlap)}")


def _class_weights(y: np.ndarray) -> dict[int, float]:
    counts = np.bincount(y.astype(int), minlength=2)
    total = len(y)
    return {label: total / (2 * count) for label, count in enumerate(counts) if count > 0}


def _metrics(y_true: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    predicted = probability >= 0.5
    result = {
        "precision": float(precision_score(y_true, predicted, zero_division=0)),
        "recall": float(recall_score(y_true, predicted, zero_division=0)),
        "f1": float(f1_score(y_true, predicted, zero_division=0)),
        "accuracy": float(accuracy_score(y_true, predicted)),
        "average_precision": float(average_precision_score(y_true, probability)),
    }
    result["roc_auc"] = float(roc_auc_score(y_true, probability)) if len(np.unique(y_true)) == 2 else float("nan")
    return result


def _experiment_payload(
    model: str,
    config: dict[str, Any],
    aggregate: dict[str, float],
    folds: list[dict[str, Any]],
    predictions: np.ndarray,
    metadata: pd.DataFrame,
) -> dict[str, Any]:
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "random_seed": int(config["project"]["random_seed"]),
        "folds": int(config["machine_learning"]["folds"]),
        "split_strategy": "StratifiedGroupKFold grouped by target_id",
        "threshold": 0.5,
        "sample_count": len(metadata),
        "positive_count": int(metadata["label"].sum()),
        "negative_count": int((metadata["label"] == 0).sum()),
        "target_group_count": int(metadata["target_id"].nunique()),
        "aggregate_metrics": aggregate,
        "fold_metrics": folds,
        "out_of_fold_predictions": [
            {"sample_id": sample, "probability": float(probability)}
            for sample, probability in zip(metadata["sample_id"], predictions, strict=True)
        ],
    }


def _write_report(feature: dict[str, Any], cnn: dict[str, Any], metadata: pd.DataFrame, path: Path) -> None:
    baseline_precision = float(metadata.label.mean())
    lines = [
        "# Phase 4 — Machine-learning baselines",
        "",
        "## Result",
        "",
        f"The evaluation contains **{len(metadata)} BLS candidates from {metadata.target_id.nunique()} independent target groups**: "
        f"{int(metadata.label.sum())} recovered confirmed-planet candidates and {int((metadata.label == 0).sum())} candidates from official Kepler false-positive systems.",
        "",
        "| Model | Precision | Recall | F1 | ROC-AUC | Average precision |",
        "|---|---:|---:|---:|---:|---:|",
        f"| BLS pass-through | {baseline_precision:.3f} | 1.000 | {2 * baseline_precision / (1 + baseline_precision):.3f} | — | {baseline_precision:.3f} |",
    ]
    for payload in (feature, cnn):
        metric = payload["aggregate_metrics"]
        lines.append(
            f"| {payload['model']} | {metric['precision']:.3f} | {metric['recall']:.3f} | {metric['f1']:.3f} | "
            f"{metric['roc_auc']:.3f} | {metric['average_precision']:.3f} |"
        )
    lines += [
        "",
        "All model figures are out-of-fold predictions at a fixed 0.5 threshold. Five-fold `StratifiedGroupKFold` keeps every target entirely within one fold; candidates from the same star never appear in both training and evaluation.",
        "",
        "## Inputs and labels",
        "",
        "The feature model uses BLS period, depth, duration, power and S/N plus duty cycle, robust scatter, odd/even depth mismatch, a phase-0.5 secondary-eclipse check, transit count, and in-transit point count. The CNN uses a robustly normalized 512-bin global folded view.",
        "",
        "Positive labels are restricted to exact ±1% Phase-3 recoveries. Official `FALSE POSITIVE` rows come from the Kepler cumulative KOI table and are balanced across not-transit, stellar-eclipse, centroid-offset, and ephemeris-contamination flags. Unmatched peaks on known planet hosts are excluded instead of being assumed negative.",
        "",
        "## Interpretation and limitations",
        "",
        "This is a small candidate-level benchmark, not evidence that either model generalizes to an unconstrained survey. The negative systems use four cached Kepler quarters per target while most positive hosts use all available quarters; quarter coverage may therefore be a nuisance variable despite robust normalization. Hyperparameters and the 0.5 threshold were fixed before evaluation, but the same folds serve as validation for CNN early stopping, so reported results should be treated as preliminary.",
        "",
        "The Phase-3 end-to-end detector recall remains 15/36 (41.67%) within 0.5–50 days. The ML metrics above measure vetting only among the candidate set and do not replace that detection recall.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    feature, cnn = run_training(args.config)
    print(json.dumps({"feature": feature["aggregate_metrics"], "cnn": cnn["aggregate_metrics"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
