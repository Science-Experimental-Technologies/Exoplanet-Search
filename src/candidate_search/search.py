"""Run the Phase 8 unknown-target search with the accepted Phase 7 RF model."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import joblib
import matplotlib
import numpy as np
import pandas as pd
import yaml
from astropy.io import fits

from src.detect.bls_search import search_light_curve
from src.ingest.mast_client import DownloadError, MastLightCurveClient, TargetNotFoundError
from src.model.features import FEATURE_COLUMNS, extract_candidate_features
from src.preprocess.build_processed import _write_processed_parquet
from src.preprocess.clean import clean_light_curve_files
from src.preprocess.detrend import detrend_light_curve

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

LOGGER = logging.getLogger("sxs.phase8.search")


def run_candidate_search(config_path: str | Path = "configs/candidate_search.yaml") -> dict[str, Any]:
    config_file = Path(config_path)
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    settings = config["candidate_search"]
    artifacts = settings["artifacts"]
    targets = yaml.safe_load(Path(artifacts["selected_targets"]).read_text(encoding="utf-8"))["targets"]
    model_selection = json.loads(Path(settings["model_selection"]).read_text(encoding="utf-8"))
    if model_selection["selected_model"] != "rf_v2":
        raise RuntimeError("Phase 8 config requires the accepted rf_v2 production model")
    threshold = float(model_selection["decision_threshold"])
    model = joblib.load(settings["model_path"])
    client = MastLightCurveClient(config["paths"]["raw"])
    processed_dir = Path(config["paths"]["processed"])
    processed_dir.mkdir(parents=True, exist_ok=True)

    candidate_frames: list[pd.DataFrame] = []
    status_rows: list[dict[str, Any]] = []
    for index, target in enumerate(targets, start=1):
        target_id = str(target["id"])
        LOGGER.info("[%d/%d] Unknown target KIC %s", index, len(targets), target_id)
        try:
            download = _fetch_with_retries(client, target_id, config)
            cleaned, stats = clean_light_curve_files(
                download.files,
                quality_bitmask=int(config["preprocess"]["quality_bitmask"]),
                sigma_lower=float(config["preprocess"]["sigma_lower"]),
                sigma_upper=float(config["preprocess"]["sigma_upper"]),
                sigma_maxiters=int(config["preprocess"]["sigma_maxiters"]),
                max_gap_cadences=int(config["preprocess"]["max_gap_cadences"]),
            )
            processed = detrend_light_curve(
                cleaned,
                window_length=int(config["preprocess"]["flatten_window_length"]),
                polyorder=int(config["preprocess"]["flatten_polyorder"]),
                break_tolerance=int(config["preprocess"]["flatten_break_tolerance"]),
                niters=int(config["preprocess"]["flatten_niters"]),
                sigma=float(config["preprocess"]["flatten_sigma"]),
            )
            destination = processed_dir / f"{target_id}_clean.parquet"
            _write_processed_parquet(
                processed,
                destination,
                metadata={
                    "target_id": target_id,
                    "host_name": f"KIC {target_id}",
                    "mission": "Kepler",
                    "time_system": "BKJD",
                    "catalog_retrieved_at_utc": _pool_retrieval_time(artifacts),
                    "preprocessing_parameters": json.dumps(config["preprocess"], sort_keys=True),
                    "catalog_status": "not_categorized_no_koi_history",
                },
            )
            found, detail = search_light_curve(
                processed,
                minimum_period_days=float(config["bls"]["minimum_period_days"]),
                maximum_period_days=float(config["bls"]["maximum_period_days"]),
                durations_hours=config["bls"]["durations_hours"],
                top_k=int(config["bls"]["top_k"]),
                frequency_oversampling=float(config["bls"]["frequency_oversampling"]),
                duration_oversampling=int(config["bls"]["duration_oversampling"]),
                minimum_peak_separation_fraction=float(
                    config["bls"]["minimum_peak_separation_fraction"]
                ),
                include_interpolated=bool(config["bls"]["include_interpolated"]),
                objective=str(config["bls"]["objective"]),
                method=str(config["bls"]["method"]),
            )
            centroids = _read_centroid_arrays(
                download.files, int(config["preprocess"]["quality_bitmask"])
            )
            features = pd.DataFrame(
                [extract_candidate_features(processed, row) for _, row in found.iterrows()]
            )
            probabilities = model.predict_proba(
                features.loc[:, FEATURE_COLUMNS].to_numpy(dtype=float)
            )[:, 1]
            found.insert(0, "host_name", f"KIC {target_id}")
            found.insert(0, "target_id", target_id)
            found.insert(0, "candidate_id", [f"{target_id}-r{rank}" for rank in found["rank"]])
            for column in FEATURE_COLUMNS:
                found[f"feature_{column}"] = features[column].to_numpy()
            found["rf_v2_probability"] = probabilities
            found["decision_threshold"] = threshold
            found["model_pass"] = probabilities >= threshold
            found["catalog_status"] = settings["required_label"]
            found["score_provenance"] = (
                "rf_v2_phase7_full_training_model_probability_not_independently_calibrated"
            )
            centroid_results = [
                _centroid_check(centroids, row) for _, row in found.iterrows()
            ]
            found = pd.concat([found.reset_index(drop=True), pd.DataFrame(centroid_results)], axis=1)
            found = _apply_sanity_flags(found, settings)
            candidate_frames.append(found)
            status_rows.append(
                {
                    "target_id": target_id,
                    "status": "available",
                    "product_count": download.product_count,
                    "from_cache": download.from_cache,
                    "output_points": len(processed),
                    "outliers_removed": stats.outliers_removed,
                    **detail,
                }
            )
        except (ValueError, OSError, TargetNotFoundError, DownloadError) as exc:
            LOGGER.error("Skipping KIC %s: %s", target_id, exc)
            status_rows.append({"target_id": target_id, "status": "skipped", "reason": str(exc)})

    if not candidate_frames:
        raise RuntimeError("No unknown target produced candidates")
    candidates = pd.concat(candidate_frames, ignore_index=True)
    candidates = candidates.sort_values(
        ["rf_v2_probability", "snr", "candidate_id"], ascending=[False, False, True]
    ).reset_index(drop=True)
    candidates["global_rank"] = np.arange(1, len(candidates) + 1)
    candidate_path = Path(artifacts["candidates"])
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidates.to_parquet(candidate_path, index=False)

    shortlist_size = int(settings["shortlist_size"])
    reviewable = candidates.loc[candidates["model_pass"] & candidates["sanity_no_fail"]].copy()
    shortlist = reviewable.head(shortlist_size).copy()
    if len(shortlist) < shortlist_size:
        raise RuntimeError(
            f"Only {len(shortlist)} candidates passed model and preliminary sanity filters"
        )
    shortlist["shortlist_rank"] = np.arange(1, len(shortlist) + 1)
    shortlist["independent_confirmation_required"] = True
    figure_dir = Path(artifacts["figures"])
    figure_dir.mkdir(parents=True, exist_ok=True)
    figure_paths = []
    for _, row in shortlist.iterrows():
        light_curve = pd.read_parquet(processed_dir / f"{row.target_id}_clean.parquet")
        figure = figure_dir / f"rank_{int(row.shortlist_rank):02d}_{row.candidate_id}.png"
        _plot_folded_candidate(light_curve, row, figure)
        figure_paths.append(figure.as_posix())
    shortlist["figure_path"] = figure_paths
    shortlist.to_csv(artifacts["shortlist"], index=False)

    status = pd.DataFrame(status_rows)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "configured_targets": len(targets),
        "available_targets": int((status["status"] == "available").sum()),
        "skipped_targets": int((status["status"] != "available").sum()),
        "candidate_rows": len(candidates),
        "model_pass_candidates": int(candidates["model_pass"].sum()),
        "sanity_no_fail_candidates": int(candidates["sanity_no_fail"].sum()),
        "model_and_sanity_candidates": len(reviewable),
        "shortlist_size": len(shortlist),
        "required_label": settings["required_label"],
        "targets": status.where(pd.notna(status), None).to_dict(orient="records"),
    }
    Path(artifacts["processing_summary"]).write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    _write_report(config, candidates, shortlist, summary)
    return summary


def _fetch_with_retries(
    client: MastLightCurveClient, target_id: str, config: dict[str, Any]
):
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            return client.fetch(
                target_id,
                id_type="KIC",
                mission=config["ingest"]["mission"],
                author=config["ingest"]["author"],
                cadence=config["ingest"]["cadence"],
                max_products=int(config["ingest"]["max_products"]),
            )
        except (DownloadError, OSError) as exc:
            last_error = exc
            LOGGER.warning("KIC %s download attempt %d failed: %s", target_id, attempt, exc)
    assert last_error is not None
    raise DownloadError(f"Three acquisition attempts failed for KIC {target_id}: {last_error}")


def _apply_sanity_flags(frame: pd.DataFrame, settings: dict[str, Any]) -> pd.DataFrame:
    frame["odd_even_status"] = np.where(
        frame["feature_odd_even_mismatch"] <= float(settings["odd_even_mismatch_max"]),
        "pass",
        "fail",
    )
    frame["secondary_eclipse_status"] = np.where(
        frame["feature_secondary_to_primary_ratio"].abs()
        <= float(settings["secondary_to_primary_ratio_max"]),
        "pass",
        "fail",
    )
    frame["centroid_status"] = np.where(
        frame["centroid_available"],
        np.where(
            frame["centroid_shift_significance"]
            < float(settings["centroid_significance_max"]),
            "pass",
            "fail",
        ),
        "unavailable",
    )
    frame["sanity_no_fail"] = (
        (frame["odd_even_status"] == "pass")
        & (frame["secondary_eclipse_status"] == "pass")
        & (frame["centroid_status"] != "fail")
    )
    return frame


def _read_centroid_arrays(files: Sequence[str], quality_bitmask: int) -> dict[str, np.ndarray] | None:
    arrays: dict[str, list[np.ndarray]] = {"time": [], "row": [], "column": []}
    for filename in files:
        with fits.open(filename, mode="readonly", memmap=True) as hdus:
            data = hdus[1].data
            names = set(data.names or [])
            if not {"TIME", "MOM_CENTR1", "MOM_CENTR2"}.issubset(names):
                return None
            quality_name = "SAP_QUALITY" if "SAP_QUALITY" in names else "QUALITY"
            quality = np.asarray(data[quality_name], dtype=np.int64)
            valid = (quality & quality_bitmask) == 0
            arrays["time"].append(np.asarray(data["TIME"], dtype=float)[valid])
            arrays["column"].append(np.asarray(data["MOM_CENTR1"], dtype=float)[valid])
            arrays["row"].append(np.asarray(data["MOM_CENTR2"], dtype=float)[valid])
    return {key: np.concatenate(value) for key, value in arrays.items()}


def _centroid_check(arrays: dict[str, np.ndarray] | None, candidate: pd.Series) -> dict[str, Any]:
    empty = {
        "centroid_available": False,
        "centroid_shift_pixels": np.nan,
        "centroid_shift_significance": np.nan,
        "centroid_in_transit_points": 0,
    }
    if arrays is None:
        return empty
    time, row, column = arrays["time"], arrays["row"], arrays["column"]
    finite = np.isfinite(time) & np.isfinite(row) & np.isfinite(column)
    time, row, column = time[finite], row[finite], column[finite]
    period = float(candidate["period_days"])
    epoch = float(candidate["transit_time_bkjd"])
    duration = float(candidate["duration_hours"]) / 24.0
    phase_days = ((time - epoch + period / 2) % period) - period / 2
    inside = np.abs(phase_days) <= duration / 2
    outside = np.abs(phase_days) >= duration * 1.5
    if inside.sum() < 5 or outside.sum() < 20:
        return empty
    delta_row = float(np.nanmedian(row[outside]) - np.nanmedian(row[inside]))
    delta_column = float(np.nanmedian(column[outside]) - np.nanmedian(column[inside]))
    row_error = _median_standard_error(row[inside], row[outside])
    column_error = _median_standard_error(column[inside], column[outside])
    significance = float(
        np.hypot(delta_row / row_error, delta_column / column_error)
    ) if row_error > 0 and column_error > 0 else np.nan
    return {
        "centroid_available": bool(np.isfinite(significance)),
        "centroid_shift_pixels": float(np.hypot(delta_row, delta_column)),
        "centroid_shift_significance": significance,
        "centroid_in_transit_points": int(inside.sum()),
    }


def _median_standard_error(inside: np.ndarray, outside: np.ndarray) -> float:
    def scale(values: np.ndarray) -> float:
        median = np.nanmedian(values)
        return float(1.4826 * np.nanmedian(np.abs(values - median)))

    return float(
        np.hypot(scale(inside) / np.sqrt(len(inside)), scale(outside) / np.sqrt(len(outside)))
    )


def _plot_folded_candidate(frame: pd.DataFrame, candidate: pd.Series, destination: Path) -> None:
    observed = frame.loc[~frame["is_interpolated"].astype(bool)]
    time = observed["time_bkjd"].to_numpy(dtype=float)
    flux = observed["flux_detrended"].to_numpy(dtype=float)
    period = float(candidate["period_days"])
    epoch = float(candidate["transit_time_bkjd"])
    phase_days = ((time - epoch + period / 2) % period) - period / 2
    phase = phase_days / period
    figure, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    axes[0].scatter(phase, flux, s=1, alpha=0.08, color="#64748b", rasterized=True)
    _binned_line(axes[0], phase, flux, -0.5, 0.5, 256)
    axes[0].set(xlabel="Orbital phase", ylabel="Detrended flux", title="Global folded view")
    half_window = max(3 * float(candidate["duration_hours"]) / 24.0, period * 0.015)
    local = np.abs(phase_days) <= half_window
    axes[1].scatter(
        phase_days[local] * 24, flux[local], s=3, alpha=0.12, color="#64748b", rasterized=True
    )
    _binned_line(axes[1], phase_days[local] * 24, flux[local], -half_window * 24, half_window * 24, 80)
    axes[1].set(xlabel="Hours from transit center", ylabel="Detrended flux", title="Local transit view")
    figure.suptitle(
        f"{candidate.candidate_id} | P={period:.6f} d | RF={candidate.rf_v2_probability:.3f} | "
        f"status={candidate.catalog_status}"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=180)
    plt.close(figure)


def _binned_line(axis: Any, x: np.ndarray, y: np.ndarray, low: float, high: float, bins: int) -> None:
    edges = np.linspace(low, high, bins + 1)
    index = np.digitize(x, edges) - 1
    centers = (edges[:-1] + edges[1:]) / 2
    values = np.array(
        [np.nanmedian(y[index == item]) if np.any(index == item) else np.nan for item in range(bins)]
    )
    axis.plot(centers, values, color="#dc2626", linewidth=1.4)


def _pool_retrieval_time(artifacts: dict[str, str]) -> str:
    return json.loads(Path(artifacts["selection_summary"]).read_text(encoding="utf-8"))[
        "generated_at_utc"
    ]


def _write_report(
    config: dict[str, Any], candidates: pd.DataFrame, shortlist: pd.DataFrame, summary: dict[str, Any]
) -> None:
    settings = config["candidate_search"]
    artifacts = settings["artifacts"]
    selection = json.loads(Path(artifacts["selection_summary"]).read_text(encoding="utf-8"))
    lines = [
        "# Phase 8 — Candidate search on unclassified Kepler targets",
        "",
        "## Status and interpretation boundary",
        "",
        f"Every output is labeled **`{settings['required_label']}`**. RF scores rank targets for manual review; they are not calibrated posterior probabilities or independent astrophysical confirmation.",
        "",
        "## Target pool",
        "",
        f"The official not-categorized, magnitude-limited population contained {selection['raw_not_categorized_magnitude_limited_targets']:,} targets before the quarter requirement and {selection['eligible_unknown_targets']:,} after requiring at least {settings['minimum_available_quarters']} quarters and excluding every KIC present in cumulative KOI or confirmed Kepler-name tables.",
        f"A deterministic SHA-256 sample of {selection['selected_targets']} targets was processed as an explicit workstation constraint. Selection used only seed and KIC, never light-curve signal or model score.",
        "",
        "## Pipeline counts",
        "",
        f"- Configured targets: {summary['configured_targets']}",
        f"- Available / skipped: {summary['available_targets']} / {summary['skipped_targets']}",
        f"- Top-five BLS candidates: {summary['candidate_rows']}",
        f"- RF threshold passes: {summary['model_pass_candidates']}",
        f"- RF plus no failed preliminary sanity check: {summary['model_and_sanity_candidates']}",
        f"- Final manual-review shortlist: {summary['shortlist_size']}",
        "",
        "The accepted Phase 7 RF threshold is used unchanged. Odd/even mismatch, phase-0.5 secondary depth, and moment-centroid shifts are preliminary filters. A centroid marked `unavailable` is retained with that caveat; it is not treated as a pass measurement.",
        "",
        "A post-ranking TAP recheck of the unique shortlist KIC targets is stored in `reports/phase8_catalog_recheck.json`. It verifies current catalog status only and is not independent astrophysical confirmation.",
        "",
        "## Ranked shortlist",
        "",
        "| Rank | Candidate | Period (d) | RF score | Odd/even | Secondary | Centroid | Shift significance | Figure | Status |",
        "|---:|---|---:|---:|---|---|---|---:|---|---|",
    ]
    for row in shortlist.itertuples():
        significance = "—" if pd.isna(row.centroid_shift_significance) else f"{row.centroid_shift_significance:.2f}σ"
        figure_path = Path(row.figure_path)
        try:
            figure = figure_path.relative_to(Path(artifacts["report"]).parent).as_posix()
        except ValueError:
            figure = figure_path.as_posix()
        lines.append(
            f"| {int(row.shortlist_rank)} | {row.candidate_id} | {row.period_days:.6f} | {row.rf_v2_probability:.3f} | "
            f"{row.odd_even_status} | {row.secondary_eclipse_status} | {row.centroid_status} | {significance} | "
            f"[folded view]({figure}) | `{row.catalog_status}` |"
        )
    lines += [
        "",
        "## Sanity-check definitions",
        "",
        f"- Odd/even: normalized depth mismatch ≤ {settings['odd_even_mismatch_max']}.",
        f"- Secondary eclipse: absolute secondary/primary depth ratio ≤ {settings['secondary_to_primary_ratio_max']}.",
        f"- Centroid: robust in/out-of-transit two-axis moment-centroid shift < {settings['centroid_significance_max']}σ when FITS centroid columns are available.",
        "",
        "These checks do not replace Kepler difference-image analysis, crowding assessment, stellar characterization, ephemeris matching against nearby variables, or external follow-up. The shortlist is solely a prioritized queue requiring independent confirmation.",
        "",
        "## Reproducibility",
        "",
        "Pool queries, exclusion counts, hashes, processing skips, all 1,250 candidate rows, scores, thresholds, sanity values, and figure paths are stored as versioned Phase 8 artifacts. Phase 7 models were read-only inputs and were not retrained.",
        "",
    ]
    Path(artifacts["report"]).write_text("\n".join(lines), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/candidate_search.yaml")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    print(json.dumps(run_candidate_search(args.config), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
