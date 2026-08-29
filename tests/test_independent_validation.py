from __future__ import annotations

import numpy as np
import pandas as pd

from src.independent_validation.fap import _stable_seed
from src.independent_validation.metrics import odd_even_test, secondary_eclipse_test
from src.independent_validation.run_phase9 import ALLOWED_CATEGORIES, add_independent_ranking


def _candidate() -> pd.Series:
    return pd.Series(
        {"candidate_id": "1-r1", "period_days": 2.0, "transit_time_bkjd": 0.0, "duration_hours": 4.0}
    )


def _synthetic_curve(alternating: bool = False, secondary: float = 0.0) -> pd.DataFrame:
    time = np.arange(0, 40, 0.02)
    phase = ((time + 1.0) % 2.0) - 1.0
    event = np.rint(time / 2.0).astype(int)
    depth = np.where(alternating & (event % 2 == 1), 0.02, 0.01)
    flux = np.ones_like(time)
    flux[np.abs(phase) <= 2 / 24] -= depth[np.abs(phase) <= 2 / 24]
    secondary_phase = ((time - 1.0 + 1.0) % 2.0) - 1.0
    flux[np.abs(secondary_phase) <= 2 / 24] -= secondary
    flux += np.random.default_rng(8).normal(0, 2e-4, len(time))
    return pd.DataFrame({"time_bkjd": time, "flux_detrended": flux})


def test_odd_even_welch_test_detects_alternating_depths() -> None:
    settings = {"odd_even_p_threshold": 0.01}
    same = odd_even_test(_synthetic_curve(), _candidate(), settings)
    alternating = odd_even_test(_synthetic_curve(alternating=True), _candidate(), settings)
    assert same["odd_even_status"] == "pass"
    assert alternating["odd_even_status"] == "fail"
    assert alternating["odd_even_p_value"] < 0.01


def test_secondary_test_reports_upper_limit_and_detection() -> None:
    settings = {"secondary_sigma_threshold": 3.0, "secondary_depth_ratio_threshold": 0.1}
    absent = secondary_eclipse_test(_synthetic_curve(), _candidate(), settings)
    present = secondary_eclipse_test(_synthetic_curve(secondary=0.004), _candidate(), settings)
    assert absent["secondary_status"] == "pass"
    assert absent["secondary_upper_limit_3sigma"] > 0
    assert present["secondary_status"] == "fail"
    assert present["secondary_significance"] >= 3


def test_independent_ranking_never_emits_confirmed_category() -> None:
    base = {
        "candidate_id": "1-r1", "shortlist_rank": 1, "fap": 0.005,
        "odd_even_status": "pass", "secondary_status": "pass",
        "transit_shape_status": "pass", "physical_size_status": "pass",
        "gaia_status": "available", "gaia_high_risk_contaminant": False,
        "tess_status": "available", "tess_period_confirmed": True,
        "exofop_period_match": False, "exofop_false_positive_flag": False,
    }
    failure = {**base, "candidate_id": "2-r1", "shortlist_rank": 2, "fap": 0.2}
    result = add_independent_ranking(pd.DataFrame([base, failure]))
    assert set(result.final_category).issubset(ALLOWED_CATEGORIES)
    assert result.set_index("candidate_id").loc["1-r1", "final_category"] == "strong_candidate"
    assert result.set_index("candidate_id").loc["2-r1", "final_category"] == "likely_false_positive"
    assert result.scientific_claim.str.contains("confirmed_exoplanet").all()


def test_fap_seed_is_target_stable() -> None:
    assert _stable_seed(42, "123") == _stable_seed(42, "123")
    assert _stable_seed(42, "123") != _stable_seed(42, "124")
