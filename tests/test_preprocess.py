from __future__ import annotations

import numpy as np
import pytest

from src.preprocess.clean import clean_light_curve_arrays
from src.preprocess.detrend import detrend_light_curve


def test_cleaning_removes_bad_values_preserves_transit_and_marks_interpolation() -> None:
    rng = np.random.default_rng(42)
    time = np.arange(100, dtype=float) * 0.02
    flux = 1.0 + rng.normal(0, 0.0002, size=100)
    flux[40:44] -= 0.01
    flux[50] = 5.0
    quality = np.zeros(100, dtype=np.int64)
    quality[20] = 1

    frame, stats = clean_light_curve_arrays(
        time=time,
        flux=flux,
        flux_err=np.full(100, 0.0002),
        quality=quality,
        cadence=np.arange(100),
        source_file="synthetic.fits",
        quality_bitmask=1,
        max_gap_cadences=3,
    )

    assert stats.quality_removed == 1
    assert stats.outliers_removed >= 1
    assert stats.interpolated_points >= 2
    assert frame["flux_raw"].max() < 2
    assert frame.loc[frame["time_bkjd"].between(0.8, 0.86), "flux_raw"].min() < 0.995
    assert frame["is_interpolated"].any()


def test_detrending_normalizes_and_keeps_transit_depth() -> None:
    time = np.arange(1000, dtype=float) * 0.02
    trend = 1 + 0.01 * np.sin(2 * np.pi * time / 8)
    flux = trend.copy()
    flux[495:505] *= 0.99
    quality = np.zeros(1000, dtype=np.int64)
    frame, _ = clean_light_curve_arrays(
        time=time,
        flux=flux,
        flux_err=np.full(1000, 0.0002),
        quality=quality,
        cadence=np.arange(1000),
        source_file="synthetic.fits",
        quality_bitmask=1,
    )
    result = detrend_light_curve(frame, window_length=301)
    assert np.nanmedian(result["flux_detrended"]) == pytest.approx(1.0, abs=1e-6)
    transit = result.loc[result["time_bkjd"].between(9.9, 10.08), "flux_detrended"]
    assert transit.min() < 0.995

