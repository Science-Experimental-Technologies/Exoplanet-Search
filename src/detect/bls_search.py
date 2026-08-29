"""Box Least Squares transit search and catalog-recovery evaluation."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from astropy.timeseries import BoxLeastSquares
from src.config import artifact_path, load_targets

LOGGER = logging.getLogger("sxs.bls")


def search_light_curve(
    frame: pd.DataFrame,
    *,
    minimum_period_days: float,
    maximum_period_days: float,
    durations_hours: Sequence[float],
    top_k: int = 5,
    frequency_oversampling: float = 5.0,
    duration_oversampling: int = 10,
    minimum_peak_separation_fraction: float = 0.01,
    include_interpolated: bool = False,
    objective: str = "snr",
    method: str = "fast",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Search one processed target and return distinct high-power candidates."""

    required = {"time_bkjd", "flux_detrended", "flux_err_normalized", "is_interpolated"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Processed light curve is missing: {', '.join(missing)}")
    selection = np.isfinite(frame["time_bkjd"]) & np.isfinite(frame["flux_detrended"])
    if not include_interpolated:
        selection &= ~frame["is_interpolated"].astype(bool)
    selected = frame.loc[selection].sort_values("time_bkjd")
    if len(selected) < 100:
        raise ValueError("At least 100 observed samples are required for BLS")

    time = selected["time_bkjd"].to_numpy(dtype=float)
    flux = selected["flux_detrended"].to_numpy(dtype=float)
    error = selected["flux_err_normalized"].to_numpy(dtype=float)
    valid_error = np.isfinite(error) & (error > 0)
    dy = error if valid_error.all() else None
    baseline = float(time[-1] - time[0])
    if baseline <= maximum_period_days:
        raise ValueError("Light-curve baseline must exceed maximum_period_days")

    periods = build_period_grid(
        baseline,
        minimum_period_days=minimum_period_days,
        maximum_period_days=maximum_period_days,
        frequency_oversampling=frequency_oversampling,
    )
    duration_days = np.asarray(durations_hours, dtype=float) / 24.0
    usable_durations = duration_days[(duration_days > 0) & (duration_days < minimum_period_days)]
    if len(usable_durations) == 0:
        raise ValueError("No duration is shorter than the minimum search period")
    excluded_durations = sorted(set(duration_days) - set(usable_durations))

    model = BoxLeastSquares(time, flux, dy=dy)
    result = model.power(
        periods,
        usable_durations,
        objective=objective,
        method=method,
        oversample=duration_oversampling,
    )
    indices = select_distinct_peaks(
        np.asarray(result.period, dtype=float),
        np.asarray(result.power, dtype=float),
        top_k=top_k,
        minimum_separation_fraction=minimum_peak_separation_fraction,
    )
    candidates = pd.DataFrame(
        {
            "rank": np.arange(1, len(indices) + 1),
            "period_days": np.asarray(result.period, dtype=float)[indices],
            "transit_time_bkjd": np.asarray(result.transit_time, dtype=float)[indices],
            "duration_hours": np.asarray(result.duration, dtype=float)[indices] * 24.0,
            "depth_fraction": np.asarray(result.depth, dtype=float)[indices],
            "depth_error_fraction": np.asarray(result.depth_err, dtype=float)[indices],
            "power": np.asarray(result.power, dtype=float)[indices],
        }
    )
    candidates["snr"] = candidates["depth_fraction"] / candidates["depth_error_fraction"]
    diagnostics = {
        "observed_points": len(selected),
        "excluded_interpolated_points": int((~selection & frame["is_interpolated"].astype(bool)).sum()),
        "baseline_days": baseline,
        "trial_periods": len(periods),
        "frequency_step_per_day": 1.0 / (baseline * frequency_oversampling),
        "durations_hours_used": (usable_durations * 24.0).tolist(),
        "durations_hours_excluded": (np.asarray(excluded_durations) * 24.0).tolist(),
        "weighted": dy is not None,
    }
    return candidates, diagnostics


def build_period_grid(
    baseline_days: float,
    *,
    minimum_period_days: float,
    maximum_period_days: float,
    frequency_oversampling: float,
) -> np.ndarray:
    if not 0 < minimum_period_days < maximum_period_days:
        raise ValueError("Require 0 < minimum_period_days < maximum_period_days")
    if baseline_days <= 0 or frequency_oversampling <= 0:
        raise ValueError("baseline_days and frequency_oversampling must be positive")
    step = 1.0 / (baseline_days * frequency_oversampling)
    frequencies = np.arange(
        1.0 / maximum_period_days,
        1.0 / minimum_period_days + step / 2,
        step,
    )
    periods = np.sort(1.0 / frequencies)
    return periods[(periods >= minimum_period_days) & (periods <= maximum_period_days)]


def select_distinct_peaks(
    periods: np.ndarray,
    power: np.ndarray,
    *,
    top_k: int,
    minimum_separation_fraction: float,
) -> np.ndarray:
    """Rank finite local maxima while suppressing near-duplicate peak samples."""

    if top_k < 1:
        raise ValueError("top_k must be positive")
    finite = np.isfinite(power)
    local = np.zeros(len(power), dtype=bool)
    if len(power) >= 3:
        local[1:-1] = (power[1:-1] >= power[:-2]) & (power[1:-1] >= power[2:])
    pool = np.flatnonzero(finite & local)
    if len(pool) < top_k:
        pool = np.flatnonzero(finite)
    ordered = pool[np.argsort(power[pool])[::-1]]
    selected: list[int] = []
    for index in ordered:
        period = periods[index]
        if all(abs(period / periods[other] - 1.0) >= minimum_separation_fraction for other in selected):
            selected.append(int(index))
            if len(selected) == top_k:
                break
    return np.asarray(selected, dtype=int)


def evaluate_recovery(
    candidates: pd.DataFrame,
    catalog: pd.DataFrame,
    targets: Sequence[dict[str, Any]],
    *,
    minimum_period_days: float,
    maximum_period_days: float,
    tolerance_fraction: float = 0.01,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for target in targets:
        target_id = str(target["id"])
        catalog_host = target.get("catalog_host", target["name"])
        planets = catalog.loc[catalog["host_star_id"] == catalog_host]
        target_candidates = candidates.loc[candidates["target_id"].astype(str) == target_id]
        for _, planet in planets.iterrows():
            true_period = float(planet["period_days"])
            eligible = minimum_period_days <= true_period <= maximum_period_days
            comparisons = target_candidates.copy()
            if comparisons.empty:
                best_rank = None
                best_period = None
                relative_error = None
                matched = False
            else:
                errors = (comparisons["period_days"] / true_period - 1.0).abs()
                best_index = errors.idxmin()
                best = comparisons.loc[best_index]
                best_rank = int(best["rank"])
                best_period = float(best["period_days"])
                relative_error = float(errors.loc[best_index])
                matched = bool(eligible and relative_error <= tolerance_fraction)
            harmonic_match = _has_harmonic_match(
                comparisons["period_days"].to_numpy(dtype=float),
                true_period,
                tolerance_fraction,
            ) if eligible else False
            rows.append(
                {
                    "target_id": target_id,
                    "host_name": target["name"],
                    "planet_name": planet["pl_name"],
                    "catalog_period_days": true_period,
                    "eligible": eligible,
                    "matched_top5_exact": matched,
                    "matched_top1_exact": matched and best_rank == 1,
                    "matched_top5_harmonic_aware": harmonic_match,
                    "best_candidate_rank": best_rank,
                    "best_candidate_period_days": best_period,
                    "relative_period_error": relative_error,
                }
            )
    return pd.DataFrame(rows)


def _has_harmonic_match(
    candidate_periods: np.ndarray,
    true_period: float,
    tolerance: float,
) -> bool:
    for factor in (0.5, 1.0, 2.0):
        expected = true_period * factor
        if np.any(np.abs(candidate_periods / expected - 1.0) <= tolerance):
            return True
    return False


def run_bls(config_path: str | Path = "configs/base.yaml") -> tuple[pd.DataFrame, pd.DataFrame]:
    config_file = Path(config_path)
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    parameters = config["bls"]
    processed_dir = Path(config["paths"]["processed"])
    all_candidates: list[pd.DataFrame] = []
    diagnostics: list[dict[str, Any]] = []
    targets = load_targets(config)
    for index, target in enumerate(targets, start=1):
        target_id = str(target["id"])
        source = processed_dir / f"{target_id}_clean.parquet"
        LOGGER.info("[%d/%d] BLS search for %s", index, len(targets), target["name"])
        if not source.is_file():
            LOGGER.warning("Skipping BLS for %s: processed file is missing", target["name"])
            diagnostics.append(
                {
                    "target_id": target_id,
                    "host_name": target["name"],
                    "status": "skipped_missing_processed_file",
                }
            )
            continue
        frame = pd.read_parquet(source)
        found, detail = search_light_curve(
            frame,
            minimum_period_days=float(parameters["minimum_period_days"]),
            maximum_period_days=float(parameters["maximum_period_days"]),
            durations_hours=parameters["durations_hours"],
            top_k=int(parameters["top_k"]),
            frequency_oversampling=float(parameters["frequency_oversampling"]),
            duration_oversampling=int(parameters["duration_oversampling"]),
            minimum_peak_separation_fraction=float(parameters["minimum_peak_separation_fraction"]),
            include_interpolated=bool(parameters["include_interpolated"]),
            objective=str(parameters["objective"]),
            method=str(parameters["method"]),
        )
        found.insert(0, "host_name", target["name"])
        found.insert(0, "target_id", target_id)
        all_candidates.append(found)
        diagnostics.append({"target_id": target_id, "host_name": target["name"], **detail})
        LOGGER.info("Top period for %s: %.8g d (power %.3f)", target["name"], found.iloc[0].period_days, found.iloc[0].power)

    if not all_candidates:
        raise RuntimeError("No configured target produced BLS candidates")
    candidates = pd.concat(all_candidates, ignore_index=True)
    output_path = processed_dir / "bls_candidates.parquet"
    _write_parquet(candidates, output_path, config_file, parameters)
    catalog = pd.read_parquet(config["catalog"]["output"])
    recovery = evaluate_recovery(
        candidates,
        catalog,
        targets,
        minimum_period_days=float(parameters["minimum_period_days"]),
        maximum_period_days=float(parameters["maximum_period_days"]),
        tolerance_fraction=float(parameters["match_tolerance_fraction"]),
    )
    recovery.to_csv(processed_dir / "bls_recovery.csv", index=False)
    (processed_dir / "bls_diagnostics.json").write_text(
        json.dumps(
            {
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "config_path": _portable_path(config_file),
                "parameters": parameters,
                "targets": diagnostics,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    _write_report(
        recovery,
        diagnostics,
        artifact_path(
            config,
            "bls_report",
            Path(config["paths"]["reports"]) / "baseline_transit_recovery.md",
        ),
        parameters,
    )
    return candidates, recovery


def _write_parquet(frame: pd.DataFrame, destination: Path, config_path: Path, parameters: dict[str, Any]) -> None:
    metadata = {
        b"sxs.generated_at_utc": datetime.now(timezone.utc).isoformat().encode(),
        b"sxs.config_path": _portable_path(config_path).encode(),
        b"sxs.bls_parameters": json.dumps(parameters, sort_keys=True).encode(),
    }
    table = pa.Table.from_pandas(frame, preserve_index=False)
    table = table.replace_schema_metadata({**(table.schema.metadata or {}), **metadata})
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    pq.write_table(table, temporary, compression="snappy")
    temporary.replace(destination)


def _write_report(
    recovery: pd.DataFrame,
    diagnostics: Sequence[dict[str, Any]],
    destination: Path,
    parameters: dict[str, Any],
) -> None:
    eligible = recovery.loc[recovery["eligible"]]
    exact_top5 = int(eligible["matched_top5_exact"].sum())
    exact_top1 = int(eligible["matched_top1_exact"].sum())
    harmonic = int(eligible["matched_top5_harmonic_aware"].sum())
    denominator = len(eligible)
    successful = [item for item in diagnostics if "trial_periods" in item]
    lines = [
        "# BLS Transit-Recovery Benchmark",
        "",
        "## Primary result",
        "",
        f"Within the configured {parameters['minimum_period_days']}–{parameters['maximum_period_days']} day search domain, "
        f"BLS recovered **{exact_top5} of {denominator} eligible confirmed planets "
        f"({100 * exact_top5 / denominator:.2f}% top-5 exact recall)** using a ±{100 * parameters['match_tolerance_fraction']:.1f}% period tolerance.",
        "",
        f"Top-1 exact recall is {exact_top1}/{denominator} ({100 * exact_top1 / denominator:.2f}%). "
        f"For diagnostic purposes, top-5 recall allowing 1/2× and 2× aliases is {harmonic}/{denominator} "
        f"({100 * harmonic / denominator:.2f}%). The exact metric is the primary baseline.",
        "",
        f"The full validation sample has {len(recovery)} planets; {len(recovery) - denominator} are outside the configured period domain and are excluded from the primary denominator rather than counted as detector failures.",
        "",
        "## Search method",
        "",
        "- Input: preprocessing detrended flux; interpolated samples excluded.",
        f"- Period range: {parameters['minimum_period_days']}–{parameters['maximum_period_days']} days.",
        f"- Trial durations: {parameters['durations_hours']} hours; values not shorter than the minimum period are rejected.",
        f"- Frequency oversampling: {parameters['frequency_oversampling']} relative to the Rayleigh resolution `1/baseline`.",
        f"- Candidate list: top {parameters['top_k']} distinct peaks, separated by at least {100 * parameters['minimum_peak_separation_fraction']:.1f}% in period.",
        "",
        "## Per-planet recovery",
        "",
        "| Host | Planet | Catalog period (d) | Eligible | Best rank | Best period (d) | Relative error | Exact match |",
        "|---|---|---:|:---:|---:|---:|---:|:---:|",
    ]
    for _, row in recovery.iterrows():
        rank = "—" if pd.isna(row.best_candidate_rank) else str(int(row.best_candidate_rank))
        period = "—" if pd.isna(row.best_candidate_period_days) else f"{row.best_candidate_period_days:.8g}"
        error = "—" if pd.isna(row.relative_period_error) else f"{100 * row.relative_period_error:.4f}%"
        lines.append(
            f"| {row.host_name} | {row.planet_name} | {row.catalog_period_days:.8g} | "
            f"{'yes' if row.eligible else 'no'} | {rank} | {period} | {error} | "
            f"{'yes' if row.matched_top5_exact else 'no'} |"
        )
    lines += [
        "",
        "## Reproducibility and limitations",
        "",
        f"The successful target searches used {min(item['trial_periods'] for item in successful):,}–{max(item['trial_periods'] for item in successful):,} trial periods depending on each target baseline. "
        "No catalog period or epoch was provided to BLS. Known periods are used only after the search for evaluation.",
        "",
        f"{len(diagnostics) - len(successful)} configured targets were skipped because no processed light curve was available; their planets remain in the recovery table as misses.",
        "",
        "BLS is expected to favor harmonics in multi-planet or eclipsing systems. This report does not treat harmonic-aware recovery as the primary metric and does not make any novel-candidate claim.",
        "",
    ]
    destination.write_text("\n".join(lines), encoding="utf-8")


def _portable_path(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    try:
        candidates, recovery = run_bls(args.config)
    except Exception as exc:
        LOGGER.exception("BLS phase failed: %s", exc)
        return 2
    eligible = recovery.loc[recovery["eligible"]]
    print(
        json.dumps(
            {
                "candidate_rows": len(candidates),
                "eligible_planets": len(eligible),
                "recovered_top5_exact": int(eligible["matched_top5_exact"].sum()),
                "recall_top5_exact": float(eligible["matched_top5_exact"].mean()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
