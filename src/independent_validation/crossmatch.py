"""Independent Gaia, TESS, and ExoFOP-derived TOI cross-matches."""

from __future__ import annotations

import warnings
import ast
from pathlib import Path
from typing import Any

import astropy.units as u
import numpy as np
import pandas as pd
import requests
from astropy.coordinates import SkyCoord
from astropy.timeseries import BoxLeastSquares
from astroquery.gaia import Gaia
from astroquery.mast import Catalogs
from lightkurve import search_lightcurve


def run_crossmatches(
    shortlist: pd.DataFrame, target_pool: pd.DataFrame, config: dict[str, Any]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    pool = target_pool.copy()
    pool["target_id"] = pool["target_id"].astype(str)
    pool = pool.set_index("target_id")
    previous = None
    previous_gaia = None
    crossmatch_path = Path(config["artifacts"]["crossmatch_results"])
    gaia_path = Path(config["artifacts"]["gaia_sources"])
    if crossmatch_path.exists() and gaia_path.exists():
        previous = pd.read_parquet(crossmatch_path)
        previous["target_id"] = previous["target_id"].astype(str)
        previous_gaia = pd.read_parquet(gaia_path)
        previous_gaia["target_id"] = previous_gaia["target_id"].astype(str)
    target_rows: dict[str, dict[str, Any]] = {}
    gaia_frames = []
    for target_id in sorted(shortlist["target_id"].astype(str).unique()):
        if previous is not None:
            old = previous.loc[previous["target_id"] == target_id]
            reusable = (
                len(old)
                and old.iloc[0]["gaia_status"] == "available"
                and old.iloc[0]["tess_status"] == "available"
                and old.iloc[0]["exofop_status"] != "query_failed"
            )
            if reusable:
                candidate_only = {"candidate_id", "tess_best_period_days", "tess_bls_snr", "tess_period_confirmed"}
                target_rows[target_id] = {
                    key: value for key, value in old.iloc[0].to_dict().items() if key not in candidate_only
                }
                gaia_frames.append(previous_gaia.loc[previous_gaia["target_id"] == target_id].copy())
                continue
        star = pool.loc[target_id]
        gaia_summary, gaia_sources = gaia_crossmatch(target_id, star, config["vetting"])
        gaia_frames.append(gaia_sources)
        tess = tess_crossmatch(target_id, star, shortlist, config)
        exofop = exofop_crossmatch(target_id, star, shortlist, config["vetting"])
        target_rows[target_id] = {"target_id": target_id, **gaia_summary, **tess, **exofop}
    targets = pd.DataFrame(target_rows.values())
    candidate_results = shortlist[["candidate_id", "target_id"]].copy()
    candidate_results["target_id"] = candidate_results["target_id"].astype(str)
    candidate_results = candidate_results.merge(targets, on="target_id", how="left")
    tess_by_candidate: dict[str, tuple[float, float, bool]] = {}
    for value in targets["tess_candidate_details"]:
        for candidate_id, best_period, snr, confirmed in ast.literal_eval(value):
            tess_by_candidate[str(candidate_id)] = (float(best_period), float(snr), bool(confirmed))
    candidate_results["tess_best_period_days"] = candidate_results["candidate_id"].map(
        lambda value: tess_by_candidate.get(str(value), (np.nan, np.nan, False))[0]
    )
    candidate_results["tess_bls_snr"] = candidate_results["candidate_id"].map(
        lambda value: tess_by_candidate.get(str(value), (np.nan, np.nan, False))[1]
    )
    candidate_results["tess_period_confirmed"] = candidate_results["candidate_id"].map(
        lambda value: tess_by_candidate.get(str(value), (np.nan, np.nan, False))[2]
    )
    gaia_all = pd.concat(gaia_frames, ignore_index=True) if gaia_frames else pd.DataFrame()
    gaia_all.to_parquet(config["artifacts"]["gaia_sources"], index=False)
    candidate_results.to_parquet(config["artifacts"]["crossmatch_results"], index=False)
    return candidate_results, gaia_all


def gaia_crossmatch(
    target_id: str, star: pd.Series, settings: dict[str, Any]
) -> tuple[dict[str, Any], pd.DataFrame]:
    ra, dec = float(star["ra"]), float(star["dec"])
    radius = float(settings["gaia_cone_arcsec"])
    query = f"""
        SELECT TOP 100 source_id,ra,dec,phot_g_mean_mag,ruwe,duplicated_source,
        DISTANCE(POINT('ICRS',ra,dec),POINT('ICRS',{ra},{dec}))*3600 AS sep_arcsec
        FROM gaiadr3.gaia_source
        WHERE 1=CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{ra},{dec},{radius / 3600.0}))
        ORDER BY sep_arcsec
    """
    try:
        sources = Gaia.launch_job_async(query, dump_to_file=False).get_results().to_pandas()
    except Exception as exc:  # remote-service failures must remain explicit in artifacts
        empty = pd.DataFrame(columns=["target_id", "source_id", "sep_arcsec", "phot_g_mean_mag"])
        return {
            "gaia_status": "query_failed",
            "gaia_error": str(exc),
            "gaia_source_count_30arcsec": 0,
            "gaia_target_ruwe": np.nan,
            "gaia_nearest_contaminant_arcsec": np.nan,
            "gaia_nearest_contaminant_delta_g": np.nan,
            "gaia_high_risk_contaminant": False,
        }, empty
    sources.insert(0, "target_id", target_id)
    if sources.empty:
        return {
            "gaia_status": "no_source",
            "gaia_error": "",
            "gaia_source_count_30arcsec": 0,
            "gaia_target_ruwe": np.nan,
            "gaia_nearest_contaminant_arcsec": np.nan,
            "gaia_nearest_contaminant_delta_g": np.nan,
            "gaia_high_risk_contaminant": False,
        }, sources
    primary = sources.iloc[0]
    contaminants = sources.iloc[1:].copy()
    contaminants["delta_g"] = contaminants["phot_g_mean_mag"] - float(primary["phot_g_mean_mag"])
    risk = contaminants.loc[
        (contaminants["sep_arcsec"] <= float(settings["gaia_high_risk_separation_arcsec"]))
        & (contaminants["delta_g"] <= float(settings["gaia_high_risk_delta_g"]))
    ]
    nearest = contaminants.iloc[0] if len(contaminants) else None
    return {
        "gaia_status": "available",
        "gaia_error": "",
        "gaia_source_count_30arcsec": len(sources),
        "gaia_target_source_id": str(primary["source_id"]),
        "gaia_target_g_mag": float(primary["phot_g_mean_mag"]),
        "gaia_target_ruwe": float(primary["ruwe"]) if pd.notna(primary["ruwe"]) else np.nan,
        "gaia_nearest_contaminant_arcsec": float(nearest["sep_arcsec"]) if nearest is not None else np.nan,
        "gaia_nearest_contaminant_delta_g": (
            float(nearest["phot_g_mean_mag"] - primary["phot_g_mean_mag"])
            if nearest is not None
            else np.nan
        ),
        "gaia_high_risk_contaminant": bool(len(risk)),
    }, sources


def tess_crossmatch(
    target_id: str, star: pd.Series, shortlist: pd.DataFrame, config: dict[str, Any]
) -> dict[str, Any]:
    settings = config["vetting"]
    coordinate = SkyCoord(float(star["ra"]) * u.deg, float(star["dec"]) * u.deg)
    last_error: Exception | None = None
    for attempt in range(3):
      try:
        tic = Catalogs.query_region(coordinate, radius=10 * u.arcsec, catalog="TIC").to_pandas()
        exact = tic.loc[pd.to_numeric(tic.get("KIC"), errors="coerce") == int(target_id)]
        selected_tic = exact.iloc[0] if len(exact) else tic.sort_values("dstArcSec").iloc[0]
        tic_id = str(int(selected_tic["ID"]))
        result = search_lightcurve(
            f"TIC {tic_id}",
            mission="TESS",
            radius=float(settings["tess_search_radius_arcsec"]) * u.arcsec,
        )
        if len(result) == 0:
            return _empty_tess("no_tess_light_curve", tic_id=tic_id)
        table = result.table.to_pandas()
        priority = {"SPOC": 0, "TESS-SPOC": 1, "QLP": 2}
        table["author_priority"] = table["author"].map(priority).fillna(9)
        table = table.sort_values(["author_priority", "exptime"])
        best_priority = table["author_priority"].min()
        indices = table.index[table["author_priority"] == best_priority].to_numpy()
        if len(indices) > 4:
            indices = indices[np.unique(np.linspace(0, len(indices) - 1, 4).astype(int))]
        chosen = result[np.asarray(indices, dtype=int)]
        cache = Path(config["artifacts"]["directory"]) / "tess_cache"
        cache.mkdir(parents=True, exist_ok=True)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            collection = chosen.download_all(download_dir=str(cache))
        if collection is None or len(collection) == 0:
            return _empty_tess("download_failed", tic_id=tic_id, products=len(chosen))
        times, fluxes, errors = [], [], []
        for lc in collection:
            normalized = lc.remove_nans().normalize()
            time_values = np.asarray(normalized.time.value, dtype=float)
            flux_values = np.asarray(normalized.flux.value, dtype=float)
            error_values = np.asarray(normalized.flux_err.value, dtype=float)
            finite = np.isfinite(time_values) & np.isfinite(flux_values)
            times.append(time_values[finite])
            fluxes.append(flux_values[finite])
            errors.append(error_values[finite])
        time = np.concatenate(times)
        flux = np.concatenate(fluxes)
        error = np.concatenate(errors)
        order = np.argsort(time)
        time, flux, error = time[order], flux[order], error[order]
        valid_error = np.isfinite(error) & (error > 0)
        dy = error if valid_error.all() else None
        candidate_rows = shortlist.loc[shortlist["target_id"].astype(str) == target_id]
        confirmations = []
        details = []
        for _, candidate in candidate_rows.iterrows():
            period = float(candidate["period_days"])
            local_periods = np.linspace(period * 0.9, period * 1.1, 1000)
            durations = np.asarray(config["bls"]["durations_hours"], dtype=float) / 24.0
            durations = durations[durations < local_periods.min()]
            result_bls = BoxLeastSquares(time, flux, dy=dy).power(
                local_periods, durations, objective="snr", method="fast", oversample=10
            )
            power = np.asarray(result_bls.power, dtype=float)
            best = int(np.nanargmax(power))
            best_period = float(np.asarray(result_bls.period)[best])
            snr = float(np.asarray(result_bls.depth)[best] / np.asarray(result_bls.depth_err)[best])
            period_match = abs(best_period / period - 1) <= float(
                settings["tess_period_tolerance_fraction"]
            )
            confirmed = bool(period_match and snr >= float(settings["tess_minimum_snr"]))
            confirmations.append(confirmed)
            details.append((candidate["candidate_id"], best_period, snr, confirmed))
        return {
            "tess_status": "available",
            "tess_error": "",
            "tess_tic_id": tic_id,
            "tess_products_found": len(result),
            "tess_products_used": len(collection),
            "tess_authors_used": ",".join(sorted(set(str(lc.meta.get("AUTHOR", "unknown")) for lc in collection))),
            "tess_baseline_days": float(time.max() - time.min()),
            "tess_points": len(time),
            "tess_candidate_details": repr(details),
            "tess_any_period_confirmed": bool(any(confirmations)),
        }
      except Exception as exc:
        last_error = exc
    assert last_error is not None
    return _empty_tess("query_or_analysis_failed", error=str(last_error))


def exofop_crossmatch(
    target_id: str, star: pd.Series, shortlist: pd.DataFrame, settings: dict[str, Any]
) -> dict[str, Any]:
    ra, dec = float(star["ra"]), float(star["dec"])
    radius = float(settings["exofop_match_radius_arcsec"])
    ra_half_width = radius / 3600.0 / np.cos(np.deg2rad(dec))
    dec_half_width = radius / 3600.0
    query = f"""
        SELECT toi,tid,ra,dec,pl_orbper,tfopwg_disp
        FROM toi
        WHERE ra BETWEEN {ra - ra_half_width} AND {ra + ra_half_width}
        AND dec BETWEEN {dec - dec_half_width} AND {dec + dec_half_width}
    """
    try:
        response = requests.get(
            "https://exoplanetarchive.ipac.caltech.edu/TAP/sync",
            params={"query": query, "format": "json"},
            timeout=60,
        )
        response.raise_for_status()
        matches = pd.DataFrame(response.json())
        if len(matches):
            center = SkyCoord(ra * u.deg, dec * u.deg)
            positions = SkyCoord(matches["ra"].to_numpy(float) * u.deg, matches["dec"].to_numpy(float) * u.deg)
            matches = matches.loc[center.separation(positions).arcsec <= radius].copy()
    except Exception as exc:
        return {
            "exofop_status": "query_failed",
            "exofop_error": str(exc),
            "exofop_toi_count": 0,
            "exofop_toi_records": "[]",
            "exofop_period_match": False,
            "exofop_false_positive_flag": False,
        }
    periods = shortlist.loc[shortlist["target_id"].astype(str) == target_id, "period_days"].to_numpy(float)
    period_match = False
    false_positive = False
    records = []
    for _, match in matches.iterrows():
        toi_period = float(match["pl_orbper"]) if pd.notna(match.get("pl_orbper")) else np.nan
        matched = bool(np.isfinite(toi_period) and np.any(np.abs(periods / toi_period - 1) <= 0.01))
        disposition = str(match.get("tfopwg_disp", ""))
        period_match |= matched
        false_positive |= disposition.upper() == "FP"
        records.append(
            {"toi": str(match.get("toi")), "tid": str(match.get("tid")), "period": toi_period,
             "disposition": disposition, "candidate_period_match": matched}
        )
    return {
        "exofop_status": "public_record" if len(matches) else "no_public_record",
        "exofop_error": "",
        "exofop_toi_count": len(matches),
        "exofop_toi_records": repr(records),
        "exofop_period_match": bool(period_match),
        "exofop_false_positive_flag": bool(false_positive),
    }


def _empty_tess(status: str, *, error: str = "", tic_id: str = "", products: int = 0) -> dict[str, Any]:
    return {
        "tess_status": status,
        "tess_error": error,
        "tess_tic_id": tic_id,
        "tess_products_found": products,
        "tess_products_used": 0,
        "tess_authors_used": "",
        "tess_baseline_days": np.nan,
        "tess_points": 0,
        "tess_candidate_details": "[]",
        "tess_any_period_confirmed": False,
    }
