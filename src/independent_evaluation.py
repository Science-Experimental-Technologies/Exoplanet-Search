"""Nested target-grouped RF evaluation and conditional group-bootstrap intervals."""

from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import precision_recall_curve
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline

from src.model.features import FEATURE_COLUMNS
from src.provenance import atomic_json, file_hash, runtime_identity
from src.workbench import new_run


def metrics(y, predicted) -> dict:
    y, predicted = np.asarray(y, dtype=int), np.asarray(predicted, dtype=int)
    tp, fp = int(((y == 1) & (predicted == 1)).sum()), int(((y == 0) & (predicted == 1)).sum())
    fn, tn = int(((y == 1) & (predicted == 0)).sum()), int(((y == 0) & (predicted == 0)).sum())
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "false_positive_rate": fp / (fp + tn) if fp + tn else None}


def choose_threshold(y, probability, target_recall: float) -> tuple[float, float]:
    precision, recall, thresholds = precision_recall_curve(y, probability)
    eligible = np.flatnonzero(recall[:-1] >= target_recall)
    best = max(eligible, key=lambda i: (precision[i], thresholds[i]))
    return float(thresholds[best]), float(precision[best])


def group_intervals(y, predicted, groups, *, repeats: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    unique = np.unique(groups)
    indices = {group: np.flatnonzero(groups == group) for group in unique}
    values = {key: [] for key in ("precision", "recall", "false_positive_rate")}
    for _ in range(repeats):
        selected = np.concatenate([indices[g] for g in rng.choice(unique, size=len(unique), replace=True)])
        result = metrics(y[selected], predicted[selected])
        for key in values:
            if result[key] is not None:
                values[key].append(result[key])
    return {key: {"lower": float(np.quantile(draws, .025)) if draws else None,
                  "upper": float(np.quantile(draws, .975)) if draws else None,
                  "valid_bootstrap_draws": len(draws)} for key, draws in values.items()}


def model(trees: int, leaf: int, seed: int):
    return make_pipeline(SimpleImputer(strategy="median"), RandomForestClassifier(
        n_estimators=trees, min_samples_leaf=leaf, class_weight="balanced", random_state=seed, n_jobs=1))


def splits(x, y, groups, count: int, seed: int):
    if count < 2 or len(np.unique(groups)) < count:
        raise ValueError("At least two folds and sufficient distinct target groups required")
    result = list(StratifiedGroupKFold(count, shuffle=True, random_state=seed).split(x, y, groups))
    for train, test in result:
        if set(groups[train]) & set(groups[test]):
            raise RuntimeError("Target leakage detected")
        if len(np.unique(y[train])) != 2 or len(np.unique(y[test])) != 2:
            raise ValueError("Each fold must contain both labels in training and evaluation; use fewer folds or more targets")
    return result


def evaluate(frame: pd.DataFrame, output: Path, *, outer: int = 5, inner: int = 3, trees: int = 100,
             bootstrap: int = 500, seed: int = 42, target_recall: float = .9) -> dict:
    required = ["sample_id", "target_id", "label", *FEATURE_COLUMNS]
    if not set(required) <= set(frame):
        raise ValueError("Metadata must include sample_id, target_id, binary label and all 13 FEATURE_COLUMNS")
    if frame[["sample_id", "target_id", "label"]].isna().any().any() or frame.sample_id.duplicated().any():
        raise ValueError("Identifiers/labels must be present and sample IDs unique")
    if set(frame.label.unique()) != {0, 1}:
        raise ValueError("Labels must contain exactly 0 and 1")
    if trees < 1 or bootstrap < 20 or not 0 < target_recall <= 1:
        raise ValueError("Require trees >= 1, bootstrap >= 20 and 0 < target recall <= 1")
    x = frame.loc[:, FEATURE_COLUMNS].to_numpy(dtype=float)
    if np.isinf(x).any() or np.isnan(x).all(axis=0).any():
        raise ValueError("Infinite or entirely missing feature columns are unsupported")
    y, groups = frame.label.to_numpy(dtype=int), frame.target_id.astype(str).to_numpy()
    probability, predicted = np.zeros(len(y)), np.zeros(len(y), dtype=int)
    assignment, thresholds = np.full(len(y), -1), np.zeros(len(y))
    folds = []
    for fold, (train, test) in enumerate(splits(x, y, groups, outer, seed)):
        inner_splits = splits(x[train], y[train], groups[train], inner, seed + fold + 1)
        choices, audits = [], []
        for leaf in (1, 4):
            inner_probability = np.zeros(len(train))
            for subfold, (subtrain, valid) in enumerate(inner_splits):
                classifier = model(trees, leaf, seed + fold * 100 + subfold)
                classifier.fit(x[train[subtrain]], y[train[subtrain]])
                inner_probability[valid] = classifier.predict_proba(x[train[valid]])[:, 1]
                if leaf == 1:
                    audits.append({"train_targets": sorted(set(groups[train[subtrain]])),
                                   "validation_targets": sorted(set(groups[train[valid]]))})
            threshold, precision = choose_threshold(y[train], inner_probability, target_recall)
            choices.append({"min_samples_leaf": leaf, "threshold": threshold, "inner_precision": precision})
        selected = max(choices, key=lambda choice: (choice["inner_precision"], choice["threshold"], choice["min_samples_leaf"]))
        classifier = model(trees, selected["min_samples_leaf"], seed + fold)
        classifier.fit(x[train], y[train])
        probability[test] = classifier.predict_proba(x[test])[:, 1]
        predicted[test] = probability[test] >= selected["threshold"]
        assignment[test], thresholds[test] = fold, selected["threshold"]
        folds.append({"fold": fold, "train_targets": sorted(set(groups[train])), "test_targets": sorted(set(groups[test])),
                      "inner_splits": audits, "choices": choices, "selected": selected, "metrics": metrics(y[test], predicted[test])})
        partial = frame.loc[assignment >= 0, ["sample_id", "target_id", "label"]].copy()
        partial["outer_fold"], partial["rf_score"] = assignment[assignment >= 0], probability[assignment >= 0]
        partial["threshold"], partial["predicted"] = thresholds[assignment >= 0], predicted[assignment >= 0]
        partial.to_csv(output / "outer_predictions.partial.csv", index=False)
        atomic_json(output / "folds.partial.json", {"completed_folds": folds})
        from src.execution import progress
        progress("evaluation", fold + 1, outer)
    if (assignment < 0).any():
        raise RuntimeError("Missing outer-fold predictions")
    predictions = frame[["sample_id", "target_id", "label"]].copy()
    predictions["outer_fold"], predictions["rf_score"] = assignment, probability
    predictions["threshold"], predictions["predicted"] = thresholds, predicted
    predictions.to_csv(output / "outer_predictions.csv", index=False)
    record = {"kind": "nested_target_grouped_random_forest", "outer_folds": outer, "inner_folds": inner,
              "trees": trees, "seed": seed, "target_inner_recall": target_recall,
              "features": list(FEATURE_COLUMNS), "candidate_rows": len(frame), "target_groups": len(set(groups)),
              "metrics": metrics(y, predicted), "intervals_95": group_intervals(y, predicted, groups, repeats=bootstrap, seed=seed),
              "bootstrap_repeats": bootstrap, "folds": folds, "runtime": runtime_identity(),
              "selection_policy": "maximize inner OOF precision subject to target recall; ties choose higher threshold then larger leaf",
              "limitations": "RF only, candidate-vetting metrics, not planet end-to-end recall. Outer targets never select hyperparameters or thresholds. No new external cohort. Bootstrap resamples targets with fixed outer predictions; it does not include retraining variability. Scores are uncalibrated. Inner target recall is not a guaranteed outer recall."}
    atomic_json(output / "evaluation.json", record)
    table = pd.DataFrame([{"metric": key, "estimate": record["metrics"][key], **ci} for key, ci in record["intervals_95"].items()])
    table.to_csv(output / "metrics.csv", index=False)
    (output / "report.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Independent RF evaluation</title>'
        '<body><h1>Nested target-grouped RF evaluation</h1><p>' + escape(record["limitations"]) + '</p>'
        + table.to_html(index=False, escape=True) + '<p>Full split assignments and selection decisions: evaluation.json.</p></body></html>', encoding="utf-8")
    return record


def demo_metadata(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    groups = np.repeat(np.arange(80), 3)
    labels = (groups % 2).astype(int)
    x = rng.normal(size=(len(groups), len(FEATURE_COLUMNS))) + labels[:, None] * .5
    frame = pd.DataFrame(x, columns=FEATURE_COLUMNS)
    frame["sample_id"] = [f"demo-{i}" for i in range(len(frame))]
    frame["target_id"], frame["label"] = groups.astype(str), labels
    return frame


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path)
    source.add_argument("--demo", action="store_true", help="Synthetic feature data; not a scientific benchmark")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--outer-folds", type=int, default=5)
    parser.add_argument("--inner-folds", type=int, default=3)
    parser.add_argument("--trees", type=int, default=100)
    parser.add_argument("--bootstrap", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    output = new_run(args.output, "evaluation")
    frame = demo_metadata(args.seed) if args.demo else pd.read_csv(args.input, dtype={"target_id": str, "sample_id": str})
    frame.to_csv(output / "input_metadata.csv", index=False)
    atomic_json(output / "input_provenance.json", {"source": "synthetic_features" if args.demo else str(args.input.resolve()),
                "input_sha256": file_hash(output / "input_metadata.csv"), "scientific_benchmark": not args.demo})
    record = evaluate(frame, output, outer=args.outer_folds, inner=args.inner_folds, trees=args.trees,
                      bootstrap=args.bootstrap, seed=args.seed)
    print(json.dumps({"output": str(output), "metrics": record["metrics"], "intervals_95": record["intervals_95"]}, indent=2))
    return 0
