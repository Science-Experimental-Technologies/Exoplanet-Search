import numpy as np
import pandas as pd
import pytest
from src.independent_evaluation import evaluate, demo_metadata, group_intervals


def test_nested_splits_exclude_outer_targets_from_every_selection(tmp_path):
    record = evaluate(demo_metadata(), tmp_path, outer=3, inner=2, trees=8, bootstrap=30)
    for fold in record["folds"]:
        train, test = set(fold["train_targets"]), set(fold["test_targets"])
        assert train.isdisjoint(test)
        for inner in fold["inner_splits"]:
            a, b = set(inner["train_targets"]), set(inner["validation_targets"])
            assert a.isdisjoint(b) and (a | b) <= train and (a | b).isdisjoint(test)
    predictions = pd.read_csv(tmp_path / "outer_predictions.csv")
    assert len(predictions) == 240 and not predictions.sample_id.duplicated().any()
    assert predictions.groupby("target_id").outer_fold.nunique().eq(1).all()
    assert all(0 <= ci["lower"] <= ci["upper"] <= 1 for ci in record["intervals_95"].values())


def test_bad_labels_and_groups_fail_closed(tmp_path):
    data = demo_metadata()
    data["label"] = 1
    with pytest.raises(ValueError, match="Labels"):
        evaluate(data, tmp_path)


def test_group_bootstrap_is_reproducible():
    y = np.array([0, 0, 1, 1] * 5)
    groups = np.repeat(np.arange(10), 2)
    assert group_intervals(y, y, groups, repeats=30, seed=5) == group_intervals(y, y, groups, repeats=30, seed=5)
