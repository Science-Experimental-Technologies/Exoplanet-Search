"""Formal photometric vetting metrics that do not consume ML features or scores."""

from __future__ import annotations

from typing import Any

import batman
import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.stats import ttest_ind

EARTH_RADII_PER_SOLAR_RADIUS = 109.076
G_SI = 6.67430e-11


def run_photometric_vetting(
    shortlist: pd.DataFrame, target_pool: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    pool = target_pool.copy()
    pool["target_id"] = pool["target_id"].astype(str)
    stellar = pool.set_index("target_id")
    rows = []
    for _, candidate in shortlist.iterrows():
        target_id = str(candidate["target_id"])
        light_curve = pd.read_parquet(
            f"{config['inputs']['processed_light_curves']}/{target_id}_clean.parquet"
        )
        observed = light_curve.loc[~light_curve["is_interpolated"].astype(bool)].copy()
        observed = observed.loc[
            np.isfinite(observed["time_bkjd"]) & np.isfinite(observed["flux_detrended"])
        ]
        row = {
            "candidate_id": candidate["candidate_id"],
            "target_id": target_id,
            **odd_even_test(observed, candidate, config["vetting"]),
            **secondary_eclipse_test(observed, candidate, config["vetting"]),
            **fit_transit_shape(observed, candidate, config["vetting"]),
        }
        radius = float(stellar.loc[target_id, "stellar_radius_solar"])
        row["stellar_radius_solar"] = radius
        row["implied_companion_radius_earth"] = (
            row["radius_ratio"] * radius * EARTH_RADII_PER_SOLAR_RADIUS
            if row["transit_fit_status"] == "success"
            else np.nan
        )
        if row["transit_fit_status"] != "success" or not np.isfinite(
            row["implied_companion_radius_earth"]
        ):
            row["physical_size_status"] = "unavailable"
        else:
            row["physical_size_status"] = (
                "pass"
                if row["implied_companion_radius_earth"]
                <= float(config["vetting"]["maximum_companion_radius_earth"])
                else "fail"
            )
        rows.append(row)
    return pd.DataFrame(rows)


def odd_even_test(frame: pd.DataFrame, candidate: pd.Series, settings: dict[str, Any]) -> dict[str, Any]:
    time = frame["time_bkjd"].to_numpy(dtype=float)
    flux = frame["flux_detrended"].to_numpy(dtype=float)
    period = float(candidate["period_days"])
    epoch = float(candidate["transit_time_bkjd"])
    duration = float(candidate["duration_hours"]) / 24.0
    event_number = np.rint((time - epoch) / period).astype(int)
    depths: list[tuple[int, float]] = []
    for number in np.unique(event_number):
        center = epoch + number * period
        distance = np.abs(time - center)
        inside = distance <= duration / 2
        baseline = (distance >= duration) & (distance <= 3 * duration)
        if inside.sum() >= 3 and baseline.sum() >= 10:
            depths.append((int(number), float(np.nanmedian(flux[baseline]) - np.nanmedian(flux[inside]))))
    odd = np.asarray([value for number, value in depths if number % 2], dtype=float)
    even = np.asarray([value for number, value in depths if not number % 2], dtype=float)
    if len(odd) < 2 or len(even) < 2:
        return {
            "odd_even_status": "unavailable",
            "odd_event_count": len(odd),
            "even_event_count": len(even),
            "odd_depth": np.nan,
            "even_depth": np.nan,
            "odd_even_t_statistic": np.nan,
            "odd_even_p_value": np.nan,
            "odd_even_sigma": np.nan,
        }
    statistic, p_value = ttest_ind(odd, even, equal_var=False, nan_policy="omit")
    odd_se = np.nanstd(odd, ddof=1) / np.sqrt(len(odd))
    even_se = np.nanstd(even, ddof=1) / np.sqrt(len(even))
    denominator = np.hypot(odd_se, even_se)
    sigma = abs(float(np.nanmean(odd) - np.nanmean(even))) / denominator if denominator > 0 else np.inf
    return {
        "odd_even_status": "fail" if p_value < float(settings["odd_even_p_threshold"]) else "pass",
        "odd_event_count": len(odd),
        "even_event_count": len(even),
        "odd_depth": float(np.nanmean(odd)),
        "even_depth": float(np.nanmean(even)),
        "odd_even_t_statistic": float(statistic),
        "odd_even_p_value": float(p_value),
        "odd_even_sigma": float(sigma),
    }


def secondary_eclipse_test(
    frame: pd.DataFrame, candidate: pd.Series, settings: dict[str, Any]
) -> dict[str, Any]:
    time = frame["time_bkjd"].to_numpy(dtype=float)
    flux = frame["flux_detrended"].to_numpy(dtype=float)
    period = float(candidate["period_days"])
    epoch = float(candidate["transit_time_bkjd"])
    duration = float(candidate["duration_hours"]) / 24.0
    primary_phase = ((time - epoch + period / 2) % period) - period / 2
    secondary_phase = ((time - (epoch + period / 2) + period / 2) % period) - period / 2
    primary = np.abs(primary_phase) <= duration / 2
    secondary = np.abs(secondary_phase) <= duration / 2
    outside = (np.abs(primary_phase) >= 1.5 * duration) & (np.abs(secondary_phase) >= 1.5 * duration)
    if primary.sum() < 5 or secondary.sum() < 5 or outside.sum() < 30:
        return {
            "secondary_status": "unavailable",
            "secondary_depth": np.nan,
            "secondary_depth_error": np.nan,
            "secondary_significance": np.nan,
            "secondary_upper_limit_3sigma": np.nan,
            "secondary_to_primary_ratio": np.nan,
        }
    baseline = float(np.nanmedian(flux[outside]))
    primary_depth = baseline - float(np.nanmedian(flux[primary]))
    secondary_depth = baseline - float(np.nanmedian(flux[secondary]))
    scatter = _robust_sigma(flux[outside])
    error = scatter * np.sqrt(np.pi / (2 * secondary.sum()) + np.pi / (2 * outside.sum()))
    significance = secondary_depth / error if error > 0 else np.nan
    ratio = secondary_depth / primary_depth if primary_depth > 0 else np.nan
    detected = significance >= float(settings["secondary_sigma_threshold"])
    fail = detected and ratio >= float(settings["secondary_depth_ratio_threshold"])
    return {
        "secondary_status": "fail" if fail else "pass",
        "secondary_depth": secondary_depth,
        "secondary_depth_error": error,
        "secondary_significance": significance,
        "secondary_upper_limit_3sigma": max(0.0, secondary_depth) + 3 * error,
        "secondary_to_primary_ratio": ratio,
    }


def fit_transit_shape(frame: pd.DataFrame, candidate: pd.Series, settings: dict[str, Any]) -> dict[str, Any]:
    time = frame["time_bkjd"].to_numpy(dtype=float)
    flux = frame["flux_detrended"].to_numpy(dtype=float)
    period = float(candidate["period_days"])
    epoch = float(candidate["transit_time_bkjd"])
    duration = float(candidate["duration_hours"]) / 24.0
    phase_days = ((time - epoch + period / 2) % period) - period / 2
    window = np.abs(phase_days) <= max(3 * duration, 0.03 * period)
    x, y, error = _bin_folded(phase_days[window], flux[window], bins=240)
    if len(x) < 30:
        return _failed_shape("insufficient_folded_bins")
    depth = max(float(candidate["depth_fraction"]), 1e-6)
    rp0 = float(np.clip(np.sqrt(depth), 0.003, 0.5))
    a0 = float(np.clip(period / (np.pi * max(duration, 1e-3)), 2.5, 80.0))

    def model(theta: np.ndarray) -> np.ndarray:
        rp, a_rs, impact, center, baseline = theta
        params = batman.TransitParams()
        params.t0 = center
        params.per = period
        params.rp = rp
        params.a = a_rs
        params.inc = np.degrees(np.arccos(np.clip(impact / a_rs, 0, 0.999999)))
        params.ecc = 0.0
        params.w = 90.0
        params.u = [0.3, 0.2]
        params.limb_dark = "quadratic"
        transit = batman.TransitModel(
            params, x, supersample_factor=7, exp_time=29.4244 / 60 / 24
        ).light_curve(params)
        return transit + (baseline - 1.0)

    scale = np.where(np.isfinite(error) & (error > 0), error, np.nanmedian(error[error > 0]))
    try:
        fit = least_squares(
            lambda theta: (y - model(theta)) / scale,
            x0=[rp0, a0, 0.5, 0.0, 1.0],
            bounds=(
                [0.001, 2.0, 0.0, -duration / 2, 0.98],
                [0.8, 150.0, 1.5, duration / 2, 1.02],
            ),
            max_nfev=2500,
        )
        rp, a_rs, impact, center, baseline = fit.x
        residual = (y - model(fit.x)) / scale
        reduced_chi2 = float(np.sum(residual**2) / max(1, len(y) - len(fit.x)))
        grazing = float(impact + rp)
        density = 3 * np.pi * a_rs**3 / (G_SI * (period * 86400.0) ** 2) / 1000.0
        fit_status = "success" if fit.success else "failed"
        shape_status = (
            "unavailable"
            if not fit.success
            else ("fail" if grazing >= float(settings["grazing_threshold"]) else "pass")
        )
        return {
            "transit_fit_status": fit_status,
            "transit_fit_message": str(fit.message),
            "radius_ratio": float(rp),
            "scaled_semimajor_axis": float(a_rs),
            "impact_parameter": float(impact),
            "grazing_parameter": grazing,
            "transit_shape": (
                "unavailable"
                if not fit.success
                else ("V_or_grazing" if grazing >= float(settings["grazing_threshold"]) else "U_shaped")
            ),
            "transit_shape_status": shape_status,
            "transit_center_offset_days": float(center),
            "transit_baseline": float(baseline),
            "transit_reduced_chi2": reduced_chi2,
            "transit_density_g_cm3": float(density),
            "transit_fit_bins": len(x),
        }
    except (ValueError, RuntimeError, FloatingPointError) as exc:
        return _failed_shape(str(exc))


def _bin_folded(x: np.ndarray, y: np.ndarray, bins: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    edges = np.linspace(float(np.nanmin(x)), float(np.nanmax(x)), bins + 1)
    index = np.digitize(x, edges) - 1
    centers, values, errors = [], [], []
    for item in range(bins):
        selected = y[index == item]
        if len(selected) < 3:
            continue
        centers.append((edges[item] + edges[item + 1]) / 2)
        values.append(float(np.nanmedian(selected)))
        errors.append(max(_robust_sigma(selected) / np.sqrt(len(selected)), 1e-7))
    return np.asarray(centers), np.asarray(values), np.asarray(errors)


def _failed_shape(message: str) -> dict[str, Any]:
    return {
        "transit_fit_status": "failed",
        "transit_fit_message": message,
        "radius_ratio": np.nan,
        "scaled_semimajor_axis": np.nan,
        "impact_parameter": np.nan,
        "grazing_parameter": np.nan,
        "transit_shape": "unavailable",
        "transit_shape_status": "unavailable",
        "transit_center_offset_days": np.nan,
        "transit_baseline": np.nan,
        "transit_reduced_chi2": np.nan,
        "transit_density_g_cm3": np.nan,
        "transit_fit_bins": 0,
    }


def _robust_sigma(values: np.ndarray) -> float:
    median = np.nanmedian(values)
    return float(1.4826 * np.nanmedian(np.abs(values - median)))
