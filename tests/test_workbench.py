import json
import pytest
from src.workbench import demo_main, prepare, synthetic_curve, new_run, read_input, analyze_main


def test_demo_offline_isolated_and_repeatable(tmp_path, monkeypatch):
    import socket
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: pytest.fail("network in demo"))
    output = tmp_path / "demo"
    assert demo_main(["--output", str(output)]) == 0
    assert json.loads((output / "expected.json").read_text())["best_period_recovered"]
    report = (output / "report.html").read_text(encoding="utf-8")
    assert "<svg" in report and "Unconfirmed periodic signals only" in report
    assert "<script" not in report and "Content-Security-Policy" in report
    from src.analysis_report import write_report
    (output / "candidates.csv").write_text("changed")
    with pytest.raises(ValueError, match="Changed"):
        write_report(output)
    with pytest.raises(FileExistsError):
        new_run(output, "demo")


def test_invalid_photometry_is_rejected():
    frame, _ = synthetic_curve()
    frame.loc[0, "flux_err"] = 0
    with pytest.raises(ValueError, match="positive"):
        prepare(frame)


def test_csv_units_and_ambiguity(tmp_path):
    frame, _ = synthetic_curve()
    frame["time"] *= 86400
    path = tmp_path / "lightcurve.csv"
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError, match="time-system"):
        read_input(path)
    loaded, _ = read_input(path, time_system="relative", time_unit="seconds")
    assert loaded.time.max() < 30
    assert analyze_main(["--input", str(path), "--time-system", "relative", "--time-unit", "seconds",
                         "--output", str(tmp_path / "analysis")]) == 0


def test_fits_reference_and_units(tmp_path):
    import numpy as np
    from astropy.io import fits
    cols = [fits.Column(name="TIME", format="D", unit="BJD - 2454833", array=np.arange(100.)),
            fits.Column(name="PDCSAP_FLUX", format="D", array=np.ones(100)),
            fits.Column(name="PDCSAP_FLUX_ERR", format="D", array=np.full(100, 0.001))]
    hdu = fits.BinTableHDU.from_columns(cols)
    hdu.header["BJDREFI"] = 2454833
    path = tmp_path / "test.fits"
    fits.HDUList([fits.PrimaryHDU(), hdu]).writeto(path)
    frame, provenance = read_input(path)
    assert frame.time.iloc[0] == 2454833
    assert provenance["time_system"] == "BJD"


def test_kic_download_contract_without_network(tmp_path, monkeypatch):
    import lightkurve as lk
    from types import SimpleNamespace
    from src.workbench import fetch_kic
    frame, _ = synthetic_curve()
    curve = SimpleNamespace(time=SimpleNamespace(jd=frame.time.to_numpy() + 2454833, scale="tdb"),
                            flux=SimpleNamespace(value=frame.flux.to_numpy()),
                            flux_err=SimpleNamespace(value=frame.flux_err.to_numpy()))
    class Selection:
        table = "mocked Kepler product"
        def __getitem__(self, item):
            return self
        def __len__(self):
            return 1
        def download_all(self, **kwargs):
            assert kwargs["quality_bitmask"] == "default"
            return [curve]
    monkeypatch.setattr(lk, "search_lightcurve", lambda *args, **kwargs: Selection())
    data, provenance = fetch_kic(11904151, tmp_path, 1)
    assert len(data) == len(frame) and provenance["products"] == 1
    assert provenance["time_system"] == "BJD"


def test_optional_model_checks_trust_and_manifest_before_scoring(tmp_path):
    import numpy as np
    import joblib
    from sklearn.ensemble import RandomForestClassifier
    from src.model.features import FEATURE_COLUMNS
    from src.provenance import atomic_json, file_hash
    from src.workbench import analyze_frame, score_model
    frame, _ = synthetic_curve()
    analyze_frame(frame, tmp_path)
    model = RandomForestClassifier(n_estimators=2, random_state=1).fit(
        np.random.default_rng(1).normal(size=(20, len(FEATURE_COLUMNS))), [0, 1] * 10)
    model_path = tmp_path / "model.joblib"
    joblib.dump(model, model_path)
    manifest = {"sha256": file_hash(model_path), "features": list(FEATURE_COLUMNS), "mission": "Kepler",
                "preprocessing": "sxs-workbench-v1", "window": 401, "period_domain_days": [.5, 8.]}
    metadata = tmp_path / "manifest.json"
    atomic_json(metadata, manifest)
    with pytest.raises(ValueError, match="trust-model"):
        score_model(tmp_path, model_path, metadata, trusted=False, mission="Kepler")
    with pytest.raises(ValueError, match="incompatible"):
        score_model(tmp_path, model_path, metadata, trusted=True, mission="other")
    result = score_model(tmp_path, model_path, metadata, trusted=True, mission="Kepler")
    assert result["rf_status"] == "scored_uncalibrated_not_planet_probability"
