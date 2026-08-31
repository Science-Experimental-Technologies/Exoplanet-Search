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
from src.provenance import atomic_json, file_hash, fingerprint, runtime_identity


def run_fap(shortlist: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Return one row per candidate and null realization, including aggregate FAP."""

    settings = config["fap"]
    if settings["shuffle_method"] != "independent_segment_circular_shift":
        raise ValueError("Unsupported FAP shuffle_method")
    roll_fraction = float(settings.get("minimum_roll_fraction", 0.05))
    if not 0 < roll_fraction < 0.5 or int(settings["permutations_per_target"]) < 1:
        raise ValueError("FAP requires permutations >= 1 and 0 < minimum_roll_fraction < 0.5")
    runtime = runtime_identity()
    artifact = Path(config["artifacts"]["fap_results"])
    cache_dir = artifact.parent / "null_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    targets = sorted(shortlist["target_id"].astype(str).unique())
    tasks = []
    caches = {}
    for target_id in targets:
        seed = _stable_seed(int(config["project"]["random_seed"]), target_id)
        source = Path(config["inputs"]["processed_light_curves"]) / f"{target_id}_clean.parquet"
        key = fingerprint({"target": target_id, "source": file_hash(source), "bls": config["bls"],
                           "seed": seed, "roll_fraction": roll_fraction, "runtime": runtime,
                           "method": settings["shuffle_method"], "draws": int(settings["permutations_per_target"])})
        cache = cache_dir / f"{key}.parquet"
        caches[target_id] = cache
        if _valid_cache(cache, int(settings["permutations_per_target"]), key):
            continue
        tasks.append(
            (
                target_id,
                str(source),
                config["bls"],
                int(settings["permutations_per_target"]),
                seed,
                str(cache),
                roll_fraction,
                key,
            )
        )
    if tasks:
        with ProcessPoolExecutor(max_workers=int(settings["workers"])) as executor:
            futures = {executor.submit(_target_null_worker, task): task[0] for task in tasks}
            for future in as_completed(futures):
                future.result()
                from src.execution import progress
                progress("fap_targets", sum(item.done() for item in futures), len(futures))

    frames: list[pd.DataFrame] = []
    n_permutations = int(settings["permutations_per_target"])
    for _, candidate in shortlist.iterrows():
        target_id = str(candidate["target_id"])
        null = pd.read_parquet(caches[target_id])
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


def _target_null_worker(task: tuple) -> str:
    target_id, source, bls, permutations, seed, destination, roll_fraction, key = task
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
    partial_path = Path(destination).with_suffix(".partial.parquet")
    partial_metadata = partial_path.with_suffix(".json")
    rows = []
    try:
        metadata = json.loads(partial_metadata.read_text(encoding="utf-8"))
        partial = pd.read_parquet(partial_path)
        if (metadata["fingerprint"] == key and metadata["sha256"] == file_hash(partial_path)
                and len(partial) <= permutations and list(partial.iteration) == list(range(len(partial)))
                and np.isfinite(partial.null_max_power).all()):
            rng.bit_generator.state = metadata["rng_state"]
            rows = partial.to_dict("records")
    except (OSError, ValueError, KeyError, AttributeError):
        pass  # Invalid partial checkpoints are never trusted.
    for iteration in range(len(rows), permutations):
        shuffled_flux = flux.copy()
        shuffled_error = error.copy()
        shifts = []
        for indices in segment_indices:
            minimum = max(1, int(np.ceil(roll_fraction * len(indices))))
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
        if len(rows) % 25 == 0 or len(rows) == permutations:
            partial_path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(rows).to_parquet(partial_path, index=False)
            atomic_json(partial_metadata, {"fingerprint": key, "sha256": file_hash(partial_path),
                                          "rng_state": rng.bit_generator.state})
    output = pd.DataFrame(rows)
    path = Path(destination)
    temporary = path.with_suffix(".parquet.tmp")
    output.to_parquet(temporary, index=False)
    temporary.replace(path)
    atomic_json(path.with_suffix(".json"), {"fingerprint": key, "sha256": file_hash(path)})
    return target_id


def _valid_cache(path: Path, expected_rows: int, key: str) -> bool:
    if not path.is_file():
        return False
    try:
        metadata = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        if metadata.get("fingerprint") != key or metadata.get("sha256") != file_hash(path):
            return False
        cached = pd.read_parquet(path, columns=["iteration", "null_max_power"])
    except (OSError, ValueError, KeyError):
        return False
    return (len(cached) == expected_rows and set(cached["iteration"]) == set(range(expected_rows))
            and np.isfinite(cached["null_max_power"]).all())


def _stable_seed(base: int, target_id: str) -> int:
    digest = hashlib.sha256(f"{base}:{target_id}".encode()).digest()
    return int.from_bytes(digest[:4], "little")
