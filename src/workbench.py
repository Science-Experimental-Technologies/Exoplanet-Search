"""Isolated single-light-curve experiments; never writes archived research paths."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid
import re

import numpy as np
import pandas as pd

from src.detect.bls_search import search_light_curve
from src.preprocess.detrend import detrend_light_curve
from src.provenance import atomic_json, file_hash, runtime_identity


DEFAULT_SEARCH = dict(minimum_period_days=0.5, maximum_period_days=8.,
                      durations_hours=[1., 2., 4., 8.], frequency_oversampling=10., top_k=5)


def new_run(output: str | Path | None, kind: str) -> Path:
    path = Path(output) if output else Path("runs") / f"{kind}-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=False)
    from src.execution import register_output
    register_output(path)
    return path


def synthetic_curve(seed: int = 42, *, transit: bool = True) -> tuple[pd.DataFrame, dict]:
    time = np.arange(0., 30., 1. / 48)
    truth = {"period_days": 3., "epoch_days": 1., "duration_hours": 4., "depth_fraction": 0.01}
    flux = 1 + 0.001 * np.sin(2 * np.pi * time / 15) + np.random.default_rng(seed).normal(0, 0.0003, len(time))
    if transit:
        phase = (time - truth["epoch_days"] + 1.5) % 3 - 1.5
        flux[np.abs(phase) < truth["duration_hours"] / 48] -= truth["depth_fraction"]
    return pd.DataFrame({"time": time, "flux": flux, "flux_err": np.full(len(time), 0.0003)}), truth


def prepare(frame: pd.DataFrame, *, window: int = 401) -> tuple[pd.DataFrame, dict]:
    required = ["time", "flux", "flux_err"]
    if not set(required) <= set(frame):
        raise ValueError("Require numeric time, flux and flux_err columns")
    if window < 5 or window % 2 == 0:
        raise ValueError("Detrending window must be an odd number >= 5")
    frame = frame.copy()
    for column in required:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    valid = np.isfinite(frame[required]).all(axis=1)
    if "quality" in frame:
        valid &= pd.to_numeric(frame["quality"], errors="raise").eq(0)
    clean = frame.loc[valid].sort_values("time").copy()
    if len(clean) < 100:
        raise ValueError("At least 100 finite quality-zero samples required")
    if (clean.flux_err <= 0).any():
        raise ValueError("All retained flux uncertainties must be positive")
    if clean.time.duplicated().any():
        raise ValueError("Duplicate timestamps require explicit upstream resolution")
    if clean.flux.median() <= 0:
        raise ValueError("Flux must have a positive median; magnitudes are unsupported")
    origin = float(clean.time.min())
    clean["time_bkjd"] = clean.time - origin  # internal legacy column; not an absolute BKJD claim
    clean["flux_raw"] = clean.flux
    clean["flux_err_raw"] = clean.flux_err
    clean["source_file"] = clean.get("segment", pd.Series("input", index=clean.index)).astype(str)
    clean["is_interpolated"] = False
    processed = detrend_light_curve(clean, window_length=window)
    return processed, {"input_rows": len(frame), "retained_rows": len(clean),
                       "removed_rows": len(frame) - len(clean), "time_origin_input_days": origin,
                       "detrending_window_samples": window, "quality_policy": "keep quality == 0 when present",
                       "outlier_policy": "no extra clipping; finite values and positive uncertainties required"}


def analyze_frame(frame: pd.DataFrame, output: Path, *, settings: dict | None = None,
                  window: int = 401, provenance: dict | None = None) -> dict:
    settings = dict(DEFAULT_SEARCH if settings is None else settings)
    processed, cleaning = prepare(frame, window=window)
    candidates, diagnostics = search_light_curve(processed, **settings)
    candidates["transit_time_input_days"] = candidates.transit_time_bkjd + cleaning["time_origin_input_days"]
    candidates["interpretation"] = "unconfirmed_periodic_signal"
    processed.to_csv(output / "processed.csv", index=False)
    candidates.to_csv(output / "candidates.csv", index=False)
    record = {"schema_version": 1, "status": "analysis_complete_report_pending", "kind": "single_light_curve",
              "claim": "No planet confirmation; BLS proposal scores are not probabilities",
              "cleaning": cleaning, "search": settings, "diagnostics": diagnostics,
              "provenance": provenance or {}, "runtime": runtime_identity(),
              "rf_status": "not_run_no_compatible_model_supplied",
              "best_candidate": candidates.iloc[0].to_dict(),
              "artifact_hashes": {name: file_hash(output / name) for name in ("processed.csv", "candidates.csv")},
              "output": str(output.resolve())}
    atomic_json(output / "run.json", record)
    from src.analysis_report import write_report
    write_report(output)
    record["status"] = "completed"
    atomic_json(output / "run.json", record)
    return record


def demo_main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Offline synthetic transit demo; not an astronomical discovery")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    output = new_run(args.output, "demo")
    frame, truth = synthetic_curve(args.seed)
    frame.to_csv(output / "input.csv", index=False)
    record = analyze_frame(frame, output, provenance={"source": "synthetic_box_transit", "seed": args.seed,
                            "input_sha256": file_hash(output / "input.csv"), "time_system": "relative_days"})
    period_error = abs(record["best_candidate"]["period_days"] / truth["period_days"] - 1)
    expected = {"truth": truth, "period_tolerance_fraction": 0.01,
                "best_period_recovered": bool(period_error <= 0.01)}
    atomic_json(output / "expected.json", expected)
    print(json.dumps({"output": str(output), **expected}, indent=2))
    return 0 if expected["best_period_recovered"] else 3


def read_input(path: Path, *, time_system: str | None = None, time_unit: str = "days",
               time_column: str | None = None, flux_column: str | None = None,
               error_column: str | None = None) -> tuple[pd.DataFrame, dict]:
    """Read explicit CSV columns or a mission FITS binary light-curve table."""
    provenance = {"source": str(path.resolve()), "input_sha256": file_hash(path)}
    if path.suffix.lower() == ".csv":
        if time_system is None:
            raise ValueError("CSV requires --time-system; timestamps must not be guessed")
        original = pd.read_csv(path)
        columns = [time_column or "time", flux_column or "flux", error_column or "flux_err"]
        frame = original.loc[:, columns].copy()
        frame.columns = ["time", "flux", "flux_err"]
        for optional in ("quality", "segment"):
            if optional in original:
                frame[optional] = original[optional]
        frame["time"] = pd.to_numeric(frame.time, errors="raise") / (86400 if time_unit == "seconds" else 1)
        provenance.update(time_system=time_system, original_time_unit=time_unit, columns=columns)
    elif path.name.lower().endswith((".fits", ".fit", ".fits.gz")):
        from astropy.io import fits
        with fits.open(path, memmap=False) as hdus:
            table = hdus[1]
            columns = [time_column or "TIME", flux_column or "PDCSAP_FLUX", error_column or "PDCSAP_FLUX_ERR"]
            frame = pd.DataFrame({key: np.asarray(table.data[col], dtype=float)
                                  for key, col in zip(("time", "flux", "flux_err"), columns)})
            header = hdus[0].header.copy()
            header.update(table.header)
            column_unit = str(table.columns[columns[0]].unit or "").strip()
            offset_label = re.fullmatch(r"BJD\s*-\s*(\d+(?:\.\d+)?)", column_unit, re.I)
            unit = str(header.get("TIMEUNIT", "d") if offset_label else column_unit or header.get("TIMEUNIT", "")).strip().lower()
            if unit not in {"d", "day", "days", "s", "sec", "second", "seconds"}:
                raise ValueError("FITS time column must declare days or seconds")
            factor = 86400 if unit in {"s", "sec", "second", "seconds"} else 1
            frame["time"] = (frame["time"] + float(header.get("TIMEZERO", 0))) / factor
            reference = float(header.get("BJDREFI", 0)) + float(header.get("BJDREFF", 0))
            if offset_label:
                labelled_reference = float(offset_label.group(1))
                if reference and not np.isclose(reference, labelled_reference, rtol=0, atol=1e-6):
                    raise ValueError("FITS BJD reference conflicts with time-column unit")
                reference = labelled_reference
            frame["time"] += reference
            if "QUALITY" in table.columns.names:
                frame["quality"] = np.asarray(table.data["QUALITY"])
            provenance.update(time_system="BJD" if reference else "FITS native day coordinate",
                              fits_timesys=header.get("TIMESYS", "unspecified"), bjd_reference=reference,
                              original_time_unit=unit, columns=columns)
    else:
        raise ValueError("Supported inputs: CSV, FITS, FITS.GZ")
    return frame, provenance


def fetch_kic(kic: int, output: Path, max_products: int) -> tuple[pd.DataFrame, dict]:
    import lightkurve as lk
    if kic <= 0 or not 1 <= max_products <= 4:
        raise ValueError("Require positive KIC and 1–4 products")
    selection = lk.search_lightcurve(f"KIC {kic}", mission="Kepler", author="Kepler", cadence="long")[:max_products]
    if len(selection) == 0:
        raise ValueError(f"No Kepler long-cadence products found for KIC {kic}")
    curves = selection.download_all(download_dir=str(output / "downloads"), quality_bitmask="default")
    if curves is None or len(curves) != len(selection):
        raise RuntimeError("Incomplete MAST download; refusing partial target analysis")
    frames = [pd.DataFrame({"time": lc.time.jd, "flux": lc.flux.value, "flux_err": lc.flux_err.value,
                            "segment": f"product-{i}"}) for i, lc in enumerate(curves)]
    return pd.concat(frames, ignore_index=True), {"source": f"MAST KIC {kic}", "mission": "Kepler",
            "time_system": "BJD", "time_scale": str(curves[0].time.scale), "products": len(curves),
            "product_selection": str(selection.table), "quality_policy": "Lightkurve default bitmask"}


def score_model(output: Path, model_path: Path, manifest_path: Path, *, trusted: bool, mission: str) -> dict:
    """Only deserialize explicitly trusted, checksum-matched sklearn models."""
    if not trusted:
        raise ValueError("Loading a pickle/joblib can execute code; --trust-model is required")
    from src.model.features import FEATURE_COLUMNS, extract_candidate_features
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run = json.loads((output / "run.json").read_text())
    required = {"sha256": file_hash(model_path), "features": list(FEATURE_COLUMNS), "mission": mission,
                "preprocessing": "sxs-workbench-v1", "window": run["cleaning"]["detrending_window_samples"]}
    if mission != "Kepler" or any(manifest.get(k) != v for k, v in required.items()):
        raise ValueError("Model manifest is incompatible with data, features, checksum or preprocessing")
    bounds = manifest.get("period_domain_days", [])
    if len(bounds) != 2 or not bounds[0] <= run["search"]["minimum_period_days"] < run["search"]["maximum_period_days"] <= bounds[1]:
        raise ValueError("Search period domain is outside the model's declared training domain")
    import joblib
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.pipeline import Pipeline
    model = joblib.load(model_path)
    classifier = model.steps[-1][1] if isinstance(model, Pipeline) else model
    if (not isinstance(classifier, RandomForestClassifier) or model.n_features_in_ != len(FEATURE_COLUMNS)
            or list(model.classes_) != [0, 1]):
        raise ValueError("Require a binary fitted RandomForestClassifier with the exact feature count")
    processed = pd.read_csv(output / "processed.csv")
    candidates = pd.read_csv(output / "candidates.csv")
    features = pd.DataFrame([extract_candidate_features(processed, row) for _, row in candidates.iterrows()])
    candidates["rf_review_score"] = model.predict_proba(features.loc[:, FEATURE_COLUMNS].to_numpy())[:, 1]
    candidates.to_csv(output / "candidates.csv", index=False)
    return {"rf_status": "scored_uncalibrated_not_planet_probability", "model_manifest": manifest,
            "model_manifest_sha256": file_hash(manifest_path)}


def analysis_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze one CSV/FITS light curve or a Kepler KIC; unconfirmed signals only")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path)
    source.add_argument("--kic", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--time-system", choices=["relative", "bkjd", "btjd", "bjd"])
    parser.add_argument("--time-unit", choices=["days", "seconds"], default="days")
    for name in ("time", "flux", "error"):
        parser.add_argument(f"--{name}-column")
    parser.add_argument("--max-products", type=int, default=1)
    parser.add_argument("--min-period", type=float, default=0.5)
    parser.add_argument("--max-period", type=float, default=8.)
    parser.add_argument("--window", type=int, default=401)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--model-manifest", type=Path)
    parser.add_argument("--trust-model", action="store_true")
    parser.add_argument("--mission", choices=["Kepler", "other"], default="other")
    return parser


def analyze_main(argv=None) -> int:
    parser = analysis_parser()
    args = parser.parse_args(argv)
    if bool(args.model) != bool(args.model_manifest):
        parser.error("--model and --model-manifest must be supplied together")
    output = new_run(args.output, "analyze")
    if args.kic is not None:
        frame, provenance = fetch_kic(args.kic, output, args.max_products)
    else:
        frame, provenance = read_input(args.input, time_system=args.time_system, time_unit=args.time_unit,
                                      time_column=args.time_column, flux_column=args.flux_column, error_column=args.error_column)
    frame.to_csv(output / "input.csv", index=False)
    provenance["canonical_input_sha256"] = file_hash(output / "input.csv")
    settings = {**DEFAULT_SEARCH, "minimum_period_days": args.min_period, "maximum_period_days": args.max_period}
    record = analyze_frame(frame, output, settings=settings, window=args.window, provenance=provenance)
    if args.model:
        try:
            record.update(score_model(output, args.model, args.model_manifest, trusted=args.trust_model,
                                      mission="Kepler" if args.kic is not None else args.mission))
        except Exception:
            record["status"] = "failed_model_scoring"
            atomic_json(output / "run.json", record)
            raise
        record["artifact_hashes"]["candidates.csv"] = file_hash(output / "candidates.csv")
        atomic_json(output / "run.json", record)
        from src.analysis_report import write_report
        write_report(output)
    print(json.dumps({"output": str(output), "best_candidate": record["best_candidate"], "rf_status": record["rf_status"]}, indent=2))
    return 0
