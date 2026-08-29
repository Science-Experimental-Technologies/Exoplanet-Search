from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.candidate_search.search import _apply_sanity_flags, _centroid_check


def test_candidate_search_requires_conservative_catalog_label_and_v2_model() -> None:
    config = yaml.safe_load(Path("configs/candidate_search.yaml").read_text(encoding="utf-8"))
    settings = config["candidate_search"]
    assert settings["required_label"] == "unvalidated_candidate_requires_independent_confirmation"
    assert settings["model_path"] == "models/rf_v2.joblib"
    assert settings["artifacts"]["report"] == "reports/candidate_screening.md"


def test_sanity_flags_treat_missing_centroid_as_unavailable_not_measured_pass() -> None:
    frame = pd.DataFrame(
        {
            "feature_odd_even_mismatch": [0.1, 0.9],
            "feature_secondary_to_primary_ratio": [0.05, 0.05],
            "centroid_available": [False, True],
            "centroid_shift_significance": [np.nan, 1.0],
        }
    )
    settings = {
        "odd_even_mismatch_max": 0.5,
        "secondary_to_primary_ratio_max": 0.2,
        "centroid_significance_max": 3.0,
    }
    result = _apply_sanity_flags(frame, settings)
    assert result.loc[0, "centroid_status"] == "unavailable"
    assert bool(result.loc[0, "sanity_no_fail"])
    assert result.loc[1, "odd_even_status"] == "fail"
    assert not bool(result.loc[1, "sanity_no_fail"])


def test_centroid_check_detects_synthetic_in_transit_shift() -> None:
    time = np.linspace(0, 30, 5000)
    period = 3.0
    epoch = 1.0
    duration_days = 0.2
    phase = ((time - epoch + period / 2) % period) - period / 2
    inside = np.abs(phase) <= duration_days / 2
    rng = np.random.default_rng(42)
    row = rng.normal(0, 0.001, len(time))
    column = rng.normal(0, 0.001, len(time))
    row[inside] += 0.01
    candidate = pd.Series(
        {"period_days": period, "transit_time_bkjd": epoch, "duration_hours": duration_days * 24}
    )
    result = _centroid_check({"time": time, "row": row, "column": column}, candidate)
    assert result["centroid_available"] is True
    assert result["centroid_shift_significance"] > 3
