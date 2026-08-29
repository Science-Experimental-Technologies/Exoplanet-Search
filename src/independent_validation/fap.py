"""Empirical BLS false-alarm probabilities from segment-wise phase shuffles."""

from __future__ import annotations

import hashlib
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from astropy.timeseries import BoxLeastSquares

from src.detect.bls_search import build_period_grid


def run_fap(shortlist: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Return one row per candidate and null realization, including aggregate FAP."""

    settings = config["fap"]
    artifact = Path(config["artifacts"]["fap_results"])
    cache_dir = artifact.parent / "null_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    targets = sorted(shortlist["target_id"].astype(str).unique())
    tasks: list[tuple[str, str, dict[str, Any], int, int, str]] = []
    for target_id in targets:
        cache = cache_dir / f"{target_id}.parquet"
        if _valid_cache(cache, int(settings["permutations_per_target"]), settings["shuffle_method"]):
            continue
        seed = _stable_seed(int(config["project"]["random_seed"]), target_id)
        source = Path(config["inputs"]["processed_light_curves"]) / f"{target_id}_clean.parquet"
        tasks.append(
            (
                target_id,
                str(source),
                config["bls"],
                int(settings["permutations_per_target"]),
                seed,
                str(cache),
            )
        )
    if tasks:
        with ProcessPoolExecutor(max_workers=int(settings["workers"])) as executor:
            futures = {executor.submit(_target_null_worker, task): task[0] for task in tasks}
            for future in as_completed(futures):
                future.result()

    frames: list[pd.DataFrame] = []
    n_permutations = int(settings["permutations_per_target"])
    for _, candidate in shortlist.iterrows():
        target_id = str(candidate["target_id"])
        null = pd.read_parquet(cache_dir / f"{target_id}.parquet")
        observed_power = float(candidate["power"])
        exceed = null["null_max_power"].to_numpy(dtype=float) >= observed_power
        count = int(exceed.sum())
        fap = (count + 1.0) / (n_permutations + 1.0)
        expanded = null.copy()
        expanded.insert(0, "candidate_id", candidate["candidate_id"])
        expanded["observed_power"] = observed_power
        expanded["null_exceeds_observed"] = exceed
        expanded["exceedance_count"] = count
        expanded["permutations"] = n_permutations
        expanded["fap"] = fap
        expanded["fap_resolution"] = 1.0 / (n_permutations + 1.0)
        expanded["shuffle_method"] = settings["shuffle_method"]
        frames.append(expanded)
    result = pd.concat(frames, ignore_index=True)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(artifact, index=False)
    return result


def _target_null_worker(task: tuple[str, str, dict[str, Any], int, int, str]) -> str:
    target_id, source, bls, permutations, seed, destination = task
    frame = pd.read_parquet(source)
    observed = frame.loc[
        (~frame["is_interpolated"].astype(bool))
        & np.isfinite(frame["time_bkjd"])
        & np.isfinite(frame["flux_detrended"])
    ].sort_values("time_bkjd")
    time = observed["time_bkjd"].to_numpy(dtype=float)
    flux = observed["flux_detrended"].to_numpy(dtype=float)
    error = observed["flux_err_normalized"].to_numpy(dtype=float)
    segments = observed["source_file"].astype(str).to_numpy()
    periods = build_period_grid(
        float(time[-1] - time[0]),
        minimum_period_days=float(bls["minimum_period_days"]),
        maximum_period_days=float(bls["maximum_period_days"]),
        frequency_oversampling=float(bls["frequency_oversampling"]),
    )
    durations = np.asarray(bls["durations_hours"], dtype=float) / 24.0
    durations = durations[durations < float(bls["minimum_period_days"])]
    dy = error if np.all(np.isfinite(error) & (error > 0)) else None
    segment_indices = [np.flatnonzero(segments == value) for value in np.unique(segments)]
    rng = np.random.default_rng(seed)
    rows = []
    for iteration in range(permutations):
        shuffled_flux = flux.copy()
        shuffled_error = error.copy()
        shifts = []
        for indices in segment_indices:
            minimum = max(1, int(np.ceil(0.05 * len(indices))))
            maximum = max(minimum + 1, len(indices) - minimum)
            shift = int(rng.integers(minimum, maximum))
            shuffled_flux[indices] = np.roll(flux[indices], shift)
            shuffled_error[indices] = np.roll(error[indices], shift)
            shifts.append(shift)
        model = BoxLeastSquares(time, shuffled_flux, dy=shuffled_error if dy is not None else None)
        power = model.power(
            periods,
            durations,
            objective=str(bls["objective"]),
            method=str(bls["method"]),
            oversample=int(bls["duration_oversampling"]),
        )
        values = np.asarray(power.power, dtype=float)
        index = int(np.nanargmax(values))
        rows.append(
            {
                "target_id": target_id,
                "iteration": iteration,
                "null_max_power": float(values[index]),
                "null_peak_period_days": float(np.asarray(power.period)[index]),
                "segment_rolls": json.dumps(shifts),
                "seed": seed,
            }
        )
    output = pd.DataFrame(rows)
    path = Path(destination)
    temporary = path.with_suffix(".parquet.tmp")
    output.to_parquet(temporary, index=False)
    temporary.replace(path)
    return target_id


def _valid_cache(path: Path, expected_rows: int, method: str) -> bool:
    if not path.is_file() or method != "independent_segment_circular_shift":
        return False
    try:
        cached = pd.read_parquet(path, columns=["iteration"])
    except (OSError, ValueError):
        return False
    return len(cached) == expected_rows and cached["iteration"].nunique() == expected_rows


def _stable_seed(base: int, target_id: str) -> int:
    digest = hashlib.sha256(f"{base}:{target_id}".encode()).digest()
    return int.from_bytes(digest[:4], "little")
