from __future__ import annotations

import numpy as np
import pandas as pd

from src.detect.bls_search import evaluate_recovery, search_light_curve


def test_bls_recovers_synthetic_transit_period() -> None:
    rng = np.random.default_rng(7)
    time = np.arange(0, 120, 0.02)
    period = 3.2
    phase = np.mod(time - 0.4 + period / 2, period) - period / 2
    flux = 1.0 + rng.normal(0, 0.0007, len(time))
    flux[np.abs(phase) < 0.08] -= 0.01
    frame = pd.DataFrame(
        {
            "time_bkjd": time,
            "flux_detrended": flux,
            "flux_err_normalized": np.full(len(time), 0.0007),
            "is_interpolated": False,
        }
    )
    candidates, diagnostics = search_light_curve(
        frame,
        minimum_period_days=0.5,
        maximum_period_days=10,
        durations_hours=[1, 2, 4],
        top_k=5,
        frequency_oversampling=5,
    )
    assert ((candidates["period_days"] / period - 1).abs() < 0.01).any()
    assert diagnostics["trial_periods"] > 1000


def test_recovery_excludes_out_of_range_planets() -> None:
    candidates = pd.DataFrame(
        {"target_id": ["1", "1"], "rank": [1, 2], "period_days": [3.01, 6.0]}
    )
    catalog = pd.DataFrame(
        {
            "host_star_id": ["Host", "Host"],
            "pl_name": ["Host b", "Host c"],
            "period_days": [3.0, 100.0],
        }
    )
    recovery = evaluate_recovery(
        candidates,
        catalog,
        [{"id": "1", "name": "Host"}],
        minimum_period_days=0.5,
        maximum_period_days=50,
    )
    assert bool(recovery.loc[recovery.planet_name.eq("Host b"), "matched_top5_exact"].iloc[0])
    assert not bool(recovery.loc[recovery.planet_name.eq("Host c"), "eligible"].iloc[0])

