"""Self-contained HTML evidence report; no scripts, CDN, or remote resources."""

from __future__ import annotations

import argparse
from html import escape
from io import StringIO
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from astropy.timeseries import BoxLeastSquares

from src.detect.bls_search import build_period_grid
from src.independent_validation.metrics import odd_even_test, secondary_eclipse_test
from src.provenance import file_hash, json_safe


def write_report(directory: Path) -> Path:
    record = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    for name in ("processed.csv", "candidates.csv"):
        if record.get("artifact_hashes", {}).get(name) != file_hash(directory / name):
            raise ValueError(f"Changed or unverified report input: {name}")
    frame = pd.read_csv(directory / "processed.csv")
    candidates = pd.read_csv(directory / "candidates.csv")
    best = candidates.iloc[0]
    time = frame.time_bkjd.to_numpy()
    settings = record["search"]
    periods = build_period_grid(float(np.ptp(time)), minimum_period_days=settings["minimum_period_days"],
                               maximum_period_days=settings["maximum_period_days"],
                               frequency_oversampling=settings["frequency_oversampling"])
    durations = np.array(settings["durations_hours"]) / 24
    durations = durations[(durations > 0) & (durations < settings["minimum_period_days"])]
    periodogram = BoxLeastSquares(time, frame.flux_detrended, dy=frame.flux_err_normalized).power(
        periods, durations, objective=settings.get("objective", "snr"),
        method=settings.get("method", "fast"), oversample=settings.get("duration_oversampling", 10))
    figure, axes = plt.subplots(3, 1, figsize=(10, 9), constrained_layout=True)
    axes[0].plot(time, frame.flux_raw_normalized, ".", ms=2, alpha=.45, label="Before detrending")
    axes[0].plot(time, frame.flux_detrended, ".", ms=2, alpha=.6, label="After detrending")
    axes[0].set(xlabel="Days from recorded input origin", ylabel="Normalized flux")
    axes[0].legend()
    axes[1].plot(periodogram.period, periodogram.power, lw=.9)
    axes[1].axvline(best.period_days, color="#bc5030", linestyle="--")
    axes[1].set(xlabel="Trial period (days)", ylabel="BLS power (S/N objective)")
    phase = (time - best.transit_time_bkjd + best.period_days / 2) % best.period_days - best.period_days / 2
    axes[2].plot(phase, frame.flux_detrended, ".", ms=2, alpha=.6)
    axes[2].set(xlabel="Days from best-candidate mid-transit (folded)", ylabel="Normalized flux")
    buffer = StringIO()
    figure.savefig(buffer, format="svg")
    plt.close(figure)
    svg = buffer.getvalue().split("<svg", 1)[1]
    svg = "<svg" + svg
    checks = {**odd_even_test(frame, best, {"odd_even_p_threshold": .01}),
              **secondary_eclipse_test(frame, best, {"secondary_sigma_threshold": 3., "secondary_depth_ratio_threshold": .1})}
    # Machine-readable checks accompany the report; absent tests are not passes.
    checks.update(fap="not_run", gaia="not_run", tess="not_run", physical_transit_fit="not_run")
    if not np.isfinite(checks.get("odd_even_p_value", np.nan)):
        checks["odd_even_status"] = "unavailable"
    checks = json_safe(checks)
    from src.provenance import atomic_json
    atomic_json(directory / "screening_checks.json", checks)
    details = escape(json.dumps({"cleaning": record["cleaning"], "search": settings,
                                "provenance": record["provenance"], "runtime": record["runtime"]}, indent=2))
    columns = ["rank", "period_days", "transit_time_input_days", "duration_hours", "depth_fraction", "snr"]
    if "rf_review_score" in candidates:
        columns.append("rf_review_score")
    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'">
<title>Exoplanet Search — Analysis report</title><style>
body{{font:16px/1.6 system-ui,sans-serif;color:#182b3a;background:#edf2f5;margin:0}}
main{{max-width:1050px;margin:32px auto;padding:32px;background:white;border-radius:12px}}
h1,h2{{line-height:1.2}}.note{{padding:16px;background:#fff0d5;border-left:4px solid #b26715}}
svg{{width:100%;height:auto}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f5f8;padding:16px}}
table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:8px;border-bottom:1px solid #dae1e6;text-align:right}}
.scroll{{overflow:auto}}@media(max-width:650px){{main{{margin:0;padding:16px}}}}
</style></head><body><main><h1>Exoplanet Search</h1><p>Single-light-curve analysis · offline evidence report</p>
<p class="note">Unconfirmed periodic signals only. A BLS peak or RF score is not a planet probability.
This run does not perform the archived project's complete independent validation.</p>
<h2>Light curve and period search</h2>{svg}
<h2>Candidate proposals</h2><p>Epochs are in the input day coordinate; consult provenance for the time system.</p>
<div class="scroll">{candidates[columns].to_html(index=False, escape=True, border=0, float_format=lambda x: f"{x:.6g}")}</div>
<h2>Screening of the highest-ranked proposal</h2><p>Odd/even uses p &lt; 0.01; a secondary flag requires
at least 3 sigma and 10% of the primary depth. Missing or insufficient evidence is not a pass.
No multiple-testing adjustment is applied to these exploratory checks.</p>
<pre>{escape(json.dumps(checks, indent=2, default=str))}</pre>
<p>RF status: {escape(record['rf_status'])}</p><h2>Provenance and reproducibility</h2>
<details><summary>Input, settings, code hashes, and software versions</summary><pre>{details}</pre></details>
<h2>Limitations</h2><p>Detrending may attenuate transits. Window, sampling, noise, aliases and systematics
affect recovery. Search maxima are proposals, not significance-calibrated detections. No Gaia/TESS
cross-match, empirical FAP, physical characterization, or observational follow-up is included here.</p>
</main></body></html>'''
    destination = directory / "report.html"
    destination.write_text(html, encoding="utf-8")
    return destination


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    print(write_report(args.run_dir).resolve())
    return 0
