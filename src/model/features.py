"""Transit-candidate features and fixed-length folded light-curve views."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


FEATURE_COLUMNS = (
    "period_days",
    "duration_hours",
    "depth_fraction",
    "depth_error_fraction",
    "snr",
    "power",
    "duty_cycle",
    "odd_even_mismatch",
    "secondary_depth_fraction",
    "secondary_to_primary_ratio",
    "robust_scatter",
    "transit_count",
    "primary_point_count",
)


def extract_candidate_features(light_curve: pd.DataFrame, candidate: pd.Series) -> dict[str, float]:
    """Compute BLS and vetting features at one candidate ephemeris."""

    observed = light_curve.loc[
        (~light_curve["is_interpolated"].astype(bool))
        & np.isfinite(light_curve["time_bkjd"])
        & np.isfinite(light_curve["flux_detrended"])
    ]
    time = observed["time_bkjd"].to_numpy(dtype=float)
    flux = observed["flux_detrended"].to_numpy(dtype=float)
    period = float(candidate["period_days"])
    epoch = float(candidate["transit_time_bkjd"])
    duration_days = float(candidate["duration_hours"]) / 24.0
    phase_days = ((time - epoch + period / 2) % period) - period / 2
    primary = np.abs(phase_days) <= duration_days / 2
    secondary = np.abs(np.abs(phase_days) - period / 2) <= duration_days / 2
    out = ~(primary | secondary)
    baseline = float(np.nanmedian(flux[out])) if np.any(out) else float(np.nanmedian(flux))
    scatter = _robust_scale(flux[out] if np.any(out) else flux)
    primary_depth = baseline - float(np.nanmedian(flux[primary])) if np.any(primary) else np.nan
    secondary_depth = baseline - float(np.nanmedian(flux[secondary])) if np.any(secondary) else 0.0

    transit_number = np.floor((time - epoch) / period + 0.5).astype(int)
    odd = primary & (np.abs(transit_number) % 2 == 1)
    even = primary & (np.abs(transit_number) % 2 == 0)
    odd_depth = baseline - float(np.nanmedian(flux[odd])) if np.any(odd) else primary_depth
    even_depth = baseline - float(np.nanmedian(flux[even])) if np.any(even) else primary_depth
    normalizer = max(abs(primary_depth), scatter, np.finfo(float).eps)
    transit_count = len(np.unique(transit_number[primary])) if np.any(primary) else 0
    return {
        "period_days": period,
        "duration_hours": float(candidate["duration_hours"]),
        "depth_fraction": float(candidate["depth_fraction"]),
        "depth_error_fraction": float(candidate["depth_error_fraction"]),
        "snr": float(candidate["snr"]),
        "power": float(candidate["power"]),
        "duty_cycle": duration_days / period,
        "odd_even_mismatch": abs(odd_depth - even_depth) / normalizer,
        "secondary_depth_fraction": secondary_depth,
        "secondary_to_primary_ratio": secondary_depth / normalizer,
        "robust_scatter": scatter,
        "transit_count": float(transit_count),
        "primary_point_count": float(primary.sum()),
    }


def fold_light_curve(light_curve: pd.DataFrame, candidate: pd.Series, *, bins: int = 512) -> np.ndarray:
    """Return a robustly normalized, phase-binned global view in [-0.5, 0.5)."""

    if bins < 16:
        raise ValueError("bins must be at least 16")
    observed = light_curve.loc[
        (~light_curve["is_interpolated"].astype(bool))
        & np.isfinite(light_curve["time_bkjd"])
        & np.isfinite(light_curve["flux_detrended"])
    ]
    time = observed["time_bkjd"].to_numpy(dtype=float)
    flux = observed["flux_detrended"].to_numpy(dtype=float)
    period = float(candidate["period_days"])
    epoch = float(candidate["transit_time_bkjd"])
    phase = ((time - epoch + period / 2) % period) / period - 0.5
    indices = np.floor((phase + 0.5) * bins).astype(int).clip(0, bins - 1)
    view = np.full(bins, np.nan, dtype=float)
    for index in np.unique(indices):
        view[index] = np.nanmedian(flux[indices == index])
    valid = np.flatnonzero(np.isfinite(view))
    if len(valid) < 2:
        raise ValueError("Folded light curve has fewer than two populated bins")
    missing = np.flatnonzero(~np.isfinite(view))
    view[missing] = np.interp(missing, valid, view[valid])
    center = float(np.nanmedian(view))
    scale = _robust_scale(view)
    return ((view - center) / scale).astype(np.float32)


def _robust_scale(values: Any) -> float:
    array = np.asarray(values, dtype=float)
    median = np.nanmedian(array)
    mad = np.nanmedian(np.abs(array - median))
    scale = 1.4826 * mad
    if not np.isfinite(scale) or scale <= 1e-12:
        scale = float(np.nanstd(array))
    return scale if np.isfinite(scale) and scale > 1e-12 else float(np.finfo(float).eps)
