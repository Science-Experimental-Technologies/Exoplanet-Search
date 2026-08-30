"""Guard report generation and frozen validation inputs without network access."""

import numpy as np
import pandas as pd
import pytest

from src.independent_validation.run_validation import _freeze_inputs
from src.validate.catalog_check import _benchmark_row, _write_benchmark_report


def test_benchmark_prose_uses_supplied_metrics(tmp_path):
    labels = np.array([1, 1, 0, 0])
    rows = [
        _benchmark_row("bls_only", labels, np.ones(4), 10),
        _benchmark_row("feature_model", labels, np.array([1, 0, 0, 0]), 10),
        _benchmark_row("cnn_1d", labels, np.zeros(4), 10),
    ]
    result = {"evaluation": {
        "eligible_confirmed_planets": 10, "bls_detected_planets": 2,
        "period_domain_days": [1, 25], "period_match_tolerance_fraction": 0.02,
        "positive_vetting_candidates": 2, "official_false_positive_candidates": 2,
        "model_predictions": "synthetic grouped predictions",
    }, "models": rows}
    destination = tmp_path / "benchmark.md"
    _write_benchmark_report(result, destination)
    report = destination.read_text(encoding="utf-8")
    assert "2 of 10 eligible confirmed planets (20.00%)" in report
    assert "retained 1 planets (10.00%" in report
    assert "CNN retained 0 planets (0.00%)" in report
    assert "1–25 day domain" in report
    assert "±2%" in report
    assert "36" not in report and "41.67%" not in report


def test_frozen_inputs_reject_changed_values_even_with_same_ids(tmp_path):
    shortlist = pd.DataFrame({
        "candidate_id": [f"{index}-r1" for index in range(20)],
        "target_id": [str(index) for index in range(20)],
        "period_days": np.linspace(1, 20, 20),
        "power": np.linspace(2, 21, 20),
        "score_provenance": "rf_v2_phase7_full_training_model_probability_not_independently_calibrated",
        "figure_path": [f"reports/phase8_candidates/{index}.png" for index in range(20)],
    })
    source = tmp_path / "shortlist.csv"
    frozen = tmp_path / "frozen.parquet"
    config = {"inputs": {"shortlist": str(source)},
              "artifacts": {"frozen_shortlist": str(frozen)}}
    shortlist.to_csv(source, index=False)
    _freeze_inputs(config)
    original = frozen.read_bytes()
    assert len(_freeze_inputs(config)) == 20
    shortlist["score_provenance"] = "rf_v2_scaleup_full_training_model_probability_not_independently_calibrated"
    shortlist["figure_path"] = shortlist.figure_path.str.replace(
        "reports/phase8_candidates/", "reports/candidate_figures/", regex=False,
    )
    shortlist.to_csv(source, index=False)
    assert len(_freeze_inputs(config)) == 20
    shortlist.loc[0, "power"] += 0.1
    shortlist.to_csv(source, index=False)
    with pytest.raises(RuntimeError, match="differs"):
        _freeze_inputs(config)
    assert frozen.read_bytes() == original
