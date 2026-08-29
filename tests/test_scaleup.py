from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.config import load_targets
from src.scaleup.catalog_builder import FLAGS, select_balanced_false_positive_targets
from src.scaleup.train_phase7 import _select_production_model, select_review_threshold


def test_external_target_file_preserves_v1_inline_behavior(tmp_path: Path) -> None:
    inline = {"targets": [{"id": "1", "name": "Inline"}]}
    assert load_targets(inline)[0]["name"] == "Inline"
    target_file = tmp_path / "targets.yaml"
    target_file.write_text(
        yaml.safe_dump({"targets": [{"id": "2", "name": "External"}]}),
        encoding="utf-8",
    )
    external = {"targets": [], "scaleup": {"target_file": str(target_file)}}
    assert load_targets(external)[0]["id"] == "2"


def test_false_positive_selection_is_balanced_unique_and_deterministic() -> None:
    rows = []
    for category_index, flag in enumerate(FLAGS.values()):
        for index in range(10):
            row = {
                "kepid": category_index * 100 + index,
                "kepoi_name": f"K{category_index:02d}{index:03d}.01",
                **{candidate: 0 for candidate in FLAGS.values()},
            }
            row[flag] = 1
            rows.append(row)
    frame = pd.DataFrame(rows)
    first = select_balanced_false_positive_targets(
        frame, per_category=5, seed=42, excluded_ids={"0"}
    )
    second = select_balanced_false_positive_targets(
        frame, per_category=5, seed=42, excluded_ids={"0"}
    )
    assert first["negative_category"].value_counts().to_dict() == {
        category: 5 for category in FLAGS
    }
    assert first["kepid"].nunique() == 20
    assert first["kepid"].tolist() == second["kepid"].tolist()
    assert 0 not in set(first["kepid"])


def test_review_threshold_satisfies_recall_constraint() -> None:
    labels = np.array([1, 1, 1, 1, 0, 0, 0, 0])
    probabilities = np.array([0.95, 0.8, 0.6, 0.4, 0.7, 0.3, 0.2, 0.1])
    selected = select_review_threshold(labels, probabilities, minimum_recall=0.75)
    assert selected["recall"] >= 0.75
    assert selected["threshold"] > 0


def test_scaleup_models_do_not_overwrite_v1() -> None:
    config = yaml.safe_load(Path("configs/scaleup.yaml").read_text(encoding="utf-8"))
    artifacts = config["scaleup"]["artifacts"]
    assert artifacts["feature_model"] == "models/rf_v2.joblib"
    assert artifacts["cnn_model"] == "models/cnn_v2.keras"
    assert artifacts["feature_model"] != "models/feature_model.joblib"


def test_unstable_cnn_remains_secondary_even_with_small_precision_gain() -> None:
    config = yaml.safe_load(Path("configs/scaleup.yaml").read_text(encoding="utf-8"))
    rf = {
        "model": "rf_v2",
        "review_threshold_selection": {"precision": 0.70, "threshold": 0.30},
    }
    cnn = {
        "model": "cnn_v2",
        "review_threshold_selection": {"precision": 0.71, "threshold": 0.25},
        "fold_f1_standard_deviation": 0.20,
    }
    selected = _select_production_model(rf, cnn, config)
    assert selected["selected_model"] == "rf_v2"
    assert selected["cnn_role"] == "secondary_diagnostic"
