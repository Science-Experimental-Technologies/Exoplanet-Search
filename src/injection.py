"""Conditional flux-level transit injection/recovery, separate from archive metrics."""

from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path

import batman
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.detect.bls_search import search_light_curve
from src.provenance import atomic_json, file_hash, runtime_identity
from src.workbench import DEFAULT_SEARCH, new_run, prepare, read_input, synthetic_curve


def transit_model(time: np.ndarray, period: float, nominal_depth: float, epoch: float) -> np.ndarray:
    if not 0 < nominal_depth < .1 or period <= 0:
        raise ValueError("Require positive period and 0 < nominal depth < 0.1")
    params = batman.TransitParams()
    params.t0, params.per, params.rp = epoch, period, np.sqrt(nominal_depth)
    params.a = 4.2083 * period ** (2 / 3)  # solar mass/radius, circular orbit
    params.inc, params.ecc, params.w = 90., 0., 90.
    params.u, params.limb_dark = [.3, .2], "quadratic"
    exposure = float(np.median(np.diff(np.sort(np.unique(time)))))
    return batman.TransitModel(params, time, supersample_factor=7, exp_time=exposure).light_curve(params)


def recovered(candidates: pd.DataFrame, period: float, epoch: float, minimum_snr: float) -> bool:
    for _, row in candidates.iterrows():
        epoch_error = abs((row.transit_time_bkjd - epoch + period / 2) % period - period / 2)
        if (abs(row.period_days / period - 1) <= .01 and row.snr >= minimum_snr
                and epoch_error <= row.duration_hours / 48):
            return True
    return False


def run_injections(frame: pd.DataFrame, output: Path, *, periods: list[float], depths: list[float],
                   repeats: int = 5, seed: int = 42, minimum_snr: float = 7., settings: dict | None = None) -> dict:
    settings = dict(DEFAULT_SEARCH if settings is None else settings)
    if repeats < 1 or not np.isfinite(minimum_snr) or minimum_snr <= 0:
        raise ValueError("Require positive repeats and minimum S/N")
    if not periods or not depths or any(not np.isfinite(v) for v in periods + depths):
        raise ValueError("Finite nonempty period/depth grids required")
    if any(not settings["minimum_period_days"] <= p <= settings["maximum_period_days"] for p in periods):
        raise ValueError("Injection periods must lie inside the search domain")
    if any(not 0 < d < .1 for d in depths):
        raise ValueError("Require 0 < nominal depths < 0.1")
    base, cleaning = prepare(frame)
    # Retain only accepted rows; injection occurs before a fresh detrending pass.
    raw = base[["time", "flux", "flux_err", "source_file"]].rename(columns={"source_file": "segment"})
    time = raw.time.to_numpy() - cleaning["time_origin_input_days"]
    control, _ = search_light_curve(base, **settings)
    control.to_csv(output / "control_candidates.csv", index=False)
    rng = np.random.default_rng(seed)
    rows = []
    for period in periods:
        for depth in depths:
            for trial in range(repeats):
                epoch = float(rng.uniform(0, period))
                injected = raw.copy()
                injected["flux"] *= transit_model(time, period, depth, epoch)
                processed, _ = prepare(injected)
                candidates, _ = search_light_curve(processed, **settings)
                rows.append({"period_days": period, "nominal_depth_rp_squared": depth, "trial": trial,
                             "epoch_relative_days": epoch, "recovered": recovered(candidates, period, epoch, minimum_snr),
                             "control_matches_same_ephemeris": recovered(control, period, epoch, minimum_snr),
                             "best_period_days": float(candidates.iloc[0].period_days),
                             "best_snr": float(candidates.iloc[0].snr)})
    trials = pd.DataFrame(rows)
    trials.to_csv(output / "injection_trials.csv", index=False)
    summary = trials.groupby(["period_days", "nominal_depth_rp_squared"], as_index=False).agg(
        recovered=("recovered", "sum"), trials=("recovered", "size"), control_matches=("control_matches_same_ephemeris", "sum"))
    summary["recovery_fraction"] = summary.recovered / summary.trials
    summary.to_csv(output / "completeness.csv", index=False)
    record = {"kind": "conditional_flux_level_injection_recovery", "seed": seed, "repeats_per_cell": repeats,
              "search": settings, "minimum_snr": minimum_snr, "runtime": runtime_identity(),
              "recovery_rule": "top-five period within 1%, epoch within half fitted duration, S/N above threshold; harmonics excluded",
              "model": "batman; solar mass/radius, central circular transit, quadratic limb darkening [0.3,0.2]; 7x median-cadence integration",
              "depth_definition": "Rp/Rstar squared, not actual limb-darkened central depth",
              "limitations": "Conditional on one input curve and random epochs; not population completeness, occurrence rates, RF performance, or independent noise realizations. Flux uncertainties remain fixed. Existing signals may inflate recovery; inspect control matches.",
              "total_trials": len(trials), "input_sha256": file_hash(output / "input.csv") if (output / "input.csv").exists() else None}
    atomic_json(output / "experiment.json", record)
    pivot = summary.pivot(index="nominal_depth_rp_squared", columns="period_days", values="recovery_fraction")
    fig, axis = plt.subplots(figsize=(7, 4), constrained_layout=True)
    plot = axis.imshow(pivot.to_numpy(), origin="lower", aspect="auto", vmin=0, vmax=1, cmap="viridis")
    axis.set(xticks=range(len(pivot.columns)), xticklabels=[f"{p:g}" for p in pivot.columns],
             yticks=range(len(pivot.index)), yticklabels=[f"{d:g}" for d in pivot.index],
             xlabel="Injected period (days)", ylabel="Nominal depth (Rp/Rstar squared)")
    fig.colorbar(plot, ax=axis, label="Conditional recovery fraction")
    fig.savefig(output / "completeness.svg")
    plt.close(fig)
    (output / "report.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Injection recovery</title>'
        '<body><h1>Conditional injection–recovery</h1><p>' + escape(record["limitations"]) + '</p>'
        + summary.to_html(index=False, escape=True) + '<img src="completeness.svg" alt="Recovery fraction grid">'
        + '<pre>' + escape(json.dumps(record, indent=2)) + '</pre></body></html>', encoding="utf-8")
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Optional canonical CSV/FITS; omit for seeded synthetic noise")
    parser.add_argument("--time-system", choices=["relative", "bkjd", "btjd", "bjd"])
    parser.add_argument("--periods", type=float, nargs="+", default=[1.5, 3., 6.])
    parser.add_argument("--depths", type=float, nargs="+", default=[.001, .005])
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--minimum-snr", type=float, default=7.)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    output = new_run(args.output, "injection")
    if args.input:
        frame, provenance = read_input(args.input, time_system=args.time_system)
    else:
        frame, _ = synthetic_curve(args.seed, transit=False)
        provenance = {"source": "synthetic_noise_and_slow_trend", "seed": args.seed}
    frame.to_csv(output / "input.csv", index=False)
    atomic_json(output / "input_provenance.json", provenance)
    record = run_injections(frame, output, periods=args.periods, depths=args.depths,
                            repeats=args.repeats, seed=args.seed, minimum_snr=args.minimum_snr)
    print(json.dumps({"output": str(output), "total_trials": record["total_trials"]}, indent=2))
    return 0
