from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.validate.catalog_check import _benchmark_row, match_catalog_period


def test_catalog_period_match_respects_tolerance() -> None:
    planets = pd.DataFrame(
        {
            "pl_name": ["Host b", "Host c"],
            "period_days": [3.0, 12.0],
        }
    )
    match = match_catalog_period(3.015, planets, tolerance_fraction=0.01)
    assert match is not None
    assert match["matched_planet"] == "Host b"
    assert match_catalog_period(3.1, planets, tolerance_fraction=0.01) is None


def test_benchmark_row_separates_vetting_and_end_to_end_recall() -> None:
    labels = np.array([1, 1, 0, 0])
    probabilities = np.array([0.9, 0.2, 0.8, 0.1])
    result = _benchmark_row("test", labels, probabilities, eligible_planets=10)
    assert result["confusion_matrix"] == {"tn": 1, "fp": 1, "fn": 1, "tp": 1}
    assert result["candidate_vetting_metrics"]["recall"] == 0.5
    assert result["candidate_vetting_metrics"]["false_positive_rate"] == 0.5
    assert result["end_to_end_recall"] == 0.1


def test_benchmark_artifact_uses_out_of_fold_predictions() -> None:
    payload = json.loads(open("reports/benchmark_metrics.json", encoding="utf-8").read())
    assert payload["evaluation"]["model_predictions"].startswith("five-fold out-of-fold")
    assert payload["evaluation"]["eligible_confirmed_planets"] == 36
