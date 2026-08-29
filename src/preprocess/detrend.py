"""Transit-preserving per-product light-curve detrending."""

from __future__ import annotations

import numpy as np
import pandas as pd


def detrend_light_curve(
    frame: pd.DataFrame,
    *,
    window_length: int = 1001,
    polyorder: int = 2,
    break_tolerance: int = 5,
    niters: int = 3,
    sigma: float = 3.0,
) -> pd.DataFrame:
    """Flatten each source product independently and normalize its median to one."""

    import lightkurve as lk

    if frame.empty:
        raise ValueError("Cannot detrend an empty light curve")
    outputs: list[pd.DataFrame] = []
    for _, segment in frame.groupby("source_file", sort=False):
        segment = segment.sort_values("time_bkjd").copy()
        median_flux = float(np.nanmedian(segment["flux_raw"]))
        if not np.isfinite(median_flux) or median_flux == 0:
            raise ValueError(f"Invalid segment median for {segment['source_file'].iloc[0]}")
        normalized_flux = segment["flux_raw"].to_numpy(dtype=float) / median_flux
        normalized_error = segment["flux_err_raw"].to_numpy(dtype=float) / median_flux
        effective_window = _effective_window(window_length, len(segment), polyorder)
        light_curve = lk.LightCurve(
            time=segment["time_bkjd"].to_numpy(dtype=float),
            flux=normalized_flux,
            flux_err=normalized_error,
        )
        flattened, trend = light_curve.flatten(
            window_length=effective_window,
            polyorder=polyorder,
            return_trend=True,
            break_tolerance=break_tolerance,
            niters=niters,
            sigma=sigma,
        )
        flattened_flux = _filled(flattened.flux.value)
        final_median = float(np.nanmedian(flattened_flux))
        if not np.isfinite(final_median) or final_median == 0:
            raise ValueError(f"Invalid flattened median for {segment['source_file'].iloc[0]}")
        segment["flux_raw_normalized"] = normalized_flux
        segment["trend"] = _filled(trend.flux.value)
        segment["flux_detrended"] = flattened_flux / final_median
        segment["flux_err_normalized"] = normalized_error / final_median
        segment["detrend_window_length"] = effective_window
        outputs.append(segment)
    result = pd.concat(outputs, ignore_index=True).sort_values("time_bkjd").reset_index(drop=True)
    return result


def _effective_window(requested: int, size: int, polyorder: int) -> int:
    if requested < 3:
        raise ValueError("window_length must be at least 3")
    candidate = min(requested, size if size % 2 == 1 else size - 1)
    if candidate % 2 == 0:
        candidate -= 1
    minimum = polyorder + 2
    if minimum % 2 == 0:
        minimum += 1
    if candidate < minimum:
        raise ValueError(f"Segment with {size} points is too short for polyorder {polyorder}")
    return candidate


def _filled(values: object) -> np.ndarray:
    return np.asarray(np.ma.filled(values, np.nan), dtype=float)

