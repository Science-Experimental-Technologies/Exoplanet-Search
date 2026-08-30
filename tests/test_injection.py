import numpy as np
import pandas as pd
from src.injection import recovered, transit_model, run_injections
from src.workbench import synthetic_curve


def test_physical_injection_and_recovery_contract(tmp_path):
    frame, _ = synthetic_curve(transit=False)
    model = transit_model(frame.time.to_numpy(), 3., .01, 1.)
    assert np.min(model) < .995 and np.max(model) <= 1
    record = run_injections(frame, tmp_path, periods=[3.], depths=[.01], repeats=2)
    trials = pd.read_csv(tmp_path / "injection_trials.csv")
    assert record["total_trials"] == 2
    assert trials.recovered.all()
    assert (tmp_path / "completeness.csv").exists()


def test_harmonics_and_wrong_epochs_do_not_count():
    rows = pd.DataFrame([dict(period_days=6., transit_time_bkjd=1., duration_hours=4., snr=20.)])
    assert not recovered(rows, 3., 1., 7.)
    rows["period_days"] = 3.
    assert recovered(rows, 3., 1., 7.)
    assert not recovered(rows, 3., 2., 7.)
