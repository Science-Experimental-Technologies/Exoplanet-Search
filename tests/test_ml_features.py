from __future__ import annotations

import numpy as np
import pandas as pd

from src.model.features import FEATURE_COLUMNS, extract_candidate_features, fold_light_curve
from src.model.train_baselines import _assert_group_isolation, _class_weights


def _synthetic_candidate() -> tuple[pd.DataFrame, pd.Series]:
    time = np.arange(0, 40, 0.02)
    period = 2.0
    epoch = 0.5
    phase = ((time - epoch + period / 2) % period) - period / 2
    transit_number = np.floor((time - epoch) / period + 0.5).astype(int)
    flux = np.ones(len(time))
    primary = np.abs(phase) <= 0.05
    flux[primary & (np.abs(transit_number) % 2 == 0)] -= 0.02
    flux[primary & (np.abs(transit_number) % 2 == 1)] -= 0.01
    flux[np.abs(np.abs(phase) - period / 2) <= 0.05] -= 0.004
    frame = pd.DataFrame(
        {
            "time_bkjd": time,
            "flux_detrended": flux,
            "is_interpolated": False,
        }
    )
    candidate = pd.Series(
        {
            "period_days": period,
            "transit_time_bkjd": epoch,
            "duration_hours": 2.4,
            "depth_fraction": 0.015,
            "depth_error_fraction": 0.001,
            "snr": 15.0,
            "power": 12.0,
        }
    )
    return frame, candidate


def test_feature_extraction_includes_vetting_signals() -> None:
    frame, candidate = _synthetic_candidate()
    features = extract_candidate_features(frame, candidate)
    assert set(features) == set(FEATURE_COLUMNS)
    assert features["odd_even_mismatch"] > 0.4
    assert features["secondary_depth_fraction"] > 0
    assert features["transit_count"] >= 19


def test_folded_view_is_fixed_length_and_centered() -> None:
    frame, candidate = _synthetic_candidate()
    view = fold_light_curve(frame, candidate, bins=128)
    assert view.shape == (128,)
    assert view.dtype == np.float32
    assert np.isfinite(view).all()
    assert abs(float(np.median(view))) < 1e-6


def test_group_isolation_and_balanced_class_weights() -> None:
    groups = np.array(["a", "a", "b", "c"])
    _assert_group_isolation(groups, np.array([0, 1]), np.array([2, 3]))
    weights = _class_weights(np.array([0, 0, 0, 1]))
    assert weights[1] > weights[0]
