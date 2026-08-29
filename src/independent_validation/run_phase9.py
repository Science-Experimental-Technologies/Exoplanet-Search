"""Run Phase 9 independent validation and enforce its acceptance contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd
import yaml

from src.independent_validation.crossmatch import run_crossmatches
from src.independent_validation.fap import run_fap
from src.independent_validation.metrics import run_photometric_vetting

LOGGER = logging.getLogger("sxs.phase9")
ALLOWED_CATEGORIES = {"strong_candidate", "weak_candidate", "likely_false_positive"}


def run_phase9(config_path: str | Path = "configs/independent_validation.yaml", stage: str = "all") -> dict[str, Any]:
    config_file = Path(config_path)
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    Path(config["artifacts"]["directory"]).mkdir(parents=True, exist_ok=True)
    shortlist = _freeze_inputs(config)
    target_pool = pd.read_parquet(config["inputs"]["target_pool"])
    if stage in {"all", "fap"}:
        LOGGER.info("Running empirical BLS null distributions")
        run_fap(shortlist, config)
    if stage in {"all", "vetting"}:
        LOGGER.info("Running formal odd/even, secondary, transit-shape, and size tests")
        vetting = run_photometric_vetting(shortlist, target_pool, config)
        vetting.to_parquet(config["artifacts"]["vetting_results"], index=False)
    if stage in {"all", "crossmatch"}:
        LOGGER.info("Running Gaia, TESS, and ExoFOP-derived TOI cross-matches")
        run_crossmatches(shortlist, target_pool, config)
    if stage in {"all", "finalize"}:
        return finalize_phase9(config, shortlist, config_file)
    return {"stage": stage, "shortlist_rows": len(shortlist)}


def finalize_phase9(config: dict[str, Any], shortlist: pd.DataFrame, config_path: Path) -> dict[str, Any]:
    fap_draws = pd.read_parquet(config["artifacts"]["fap_results"])
    fap = (
        fap_draws.sort_values("iteration")
        .groupby("candidate_id", as_index=False)
        .first()[["candidate_id", "observed_power", "exceedance_count", "permutations", "fap", "fap_resolution"]]
    )
    vetting = pd.read_parquet(config["artifacts"]["vetting_results"])
    crossmatch = pd.read_parquet(config["artifacts"]["crossmatch_results"])
    shortlist = shortlist.rename(
        columns={
            "odd_even_status": "phase8_preliminary_odd_even_status",
            "secondary_eclipse_status": "phase8_preliminary_secondary_status",
            "centroid_status": "phase8_centroid_status",
        }
    )
    result = shortlist.merge(fap, on="candidate_id", validate="one_to_one")
    result = result.merge(vetting, on=["candidate_id", "target_id"], validate="one_to_one")
    result = result.merge(crossmatch, on=["candidate_id", "target_id"], validate="one_to_one")
    result = add_independent_ranking(result)
    result.to_csv(config["artifacts"]["final_ranking"], index=False)
    _write_report(result, config)
    checks = {key: bool(value) for key, value in acceptance_checks(result, fap_draws, config).items()}
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase": 9,
        "status": "accepted" if all(checks.values()) else "failed",
        "config_path": config_path.as_posix(),
        "frozen_shortlist_sha256": _sha256(Path(config["artifacts"]["frozen_shortlist"])),
        "candidate_count": len(result),
        "unique_target_count": result["target_id"].astype(str).nunique(),
        "category_counts": result["final_category"].value_counts().to_dict(),
        "strong_candidates": result.loc[result["final_category"] == "strong_candidate", "candidate_id"].tolist(),
        "acceptance_checks": checks,
        "phase10_unlocked": bool(all(checks.values())),
    }
    Path(config["artifacts"]["run_record"]).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if not all(checks.values()):
        raise RuntimeError(f"Phase 9 acceptance failed: {checks}")
    return summary


def add_independent_ranking(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["fap_status"] = np.select(
        [result["fap"] <= 0.01, result["fap"] <= 0.05], ["pass", "borderline"], default="fail"
    )
    result["score_fap"] = np.select([result.fap <= 0.01, result.fap <= 0.05], [3, 1], default=-3)
    result["score_odd_even"] = result.odd_even_status.map({"pass": 1, "fail": -3}).fillna(0)
    result["score_secondary"] = result.secondary_status.map({"pass": 1, "fail": -3}).fillna(0)
    result["score_transit_shape"] = result.transit_shape_status.map({"pass": 2, "fail": -3}).fillna(0)
    result["score_physical_size"] = result.physical_size_status.map({"pass": 1, "fail": -3}).fillna(0)
    result["score_gaia"] = np.where(
        result.gaia_status != "available", 0, np.where(result.gaia_high_risk_contaminant, -3, 1)
    )
    result["score_tess"] = np.where(
        result.tess_period_confirmed,
        2,
        np.where(result.tess_status == "available", -1, 0),
    )
    result["score_exofop"] = np.where(
        result.exofop_false_positive_flag,
        -3,
        np.where(result.exofop_period_match, 1, 0),
    )
    score_columns = [
        "score_fap", "score_odd_even", "score_secondary", "score_transit_shape",
        "score_physical_size", "score_gaia", "score_tess", "score_exofop",
    ]
    result["independent_evidence_score"] = result[score_columns].sum(axis=1)
    key_failure = (
        (result.fap > 0.05)
        | (result.odd_even_status == "fail")
        | (result.secondary_status == "fail")
        | (result.transit_shape_status == "fail")
        | (result.physical_size_status == "fail")
        | result.gaia_high_risk_contaminant.astype(bool)
        | result.exofop_false_positive_flag.astype(bool)
    )
    complete_pass = (
        (result.fap <= 0.01)
        & (result.odd_even_status == "pass")
        & (result.secondary_status == "pass")
        & (result.transit_shape_status == "pass")
        & (result.physical_size_status == "pass")
        & (result.gaia_status == "available")
        & ~result.gaia_high_risk_contaminant.astype(bool)
        & result.tess_period_confirmed.astype(bool)
        & ~result.exofop_false_positive_flag.astype(bool)
    )
    result["final_category"] = np.where(
        key_failure, "likely_false_positive", np.where(complete_pass, "strong_candidate", "weak_candidate")
    )
    result["scientific_claim"] = "unconfirmed_signal_not_a_confirmed_exoplanet"
    category_order = {"strong_candidate": 0, "weak_candidate": 1, "likely_false_positive": 2}
    result["_category_order"] = result.final_category.map(category_order)
    result = result.sort_values(
        ["_category_order", "independent_evidence_score", "fap", "shortlist_rank"],
        ascending=[True, False, True, True],
    ).drop(columns="_category_order").reset_index(drop=True)
    result["phase9_rank"] = np.arange(1, len(result) + 1)
    return result


def acceptance_checks(result: pd.DataFrame, fap: pd.DataFrame, config: dict[str, Any]) -> dict[str, bool]:
    expected_draws = len(result) * int(config["fap"]["permutations_per_target"])
    component_scores = [
        "score_fap", "score_odd_even", "score_secondary", "score_transit_shape",
        "score_physical_size", "score_gaia", "score_tess", "score_exofop",
    ]
    return {
        "exactly_20_candidates": len(result) == 20 and result.candidate_id.nunique() == 20,
        "all_fap_null_draws_saved": len(fap) == expected_draws and fap.null_max_power.notna().all(),
        "formal_odd_even_complete": result.odd_even_p_value.notna().all(),
        "secondary_upper_limits_complete": result.secondary_upper_limit_3sigma.notna().all(),
        "transit_models_attempted": result.transit_fit_status.notna().all(),
        "gaia_queries_recorded": result.gaia_status.notna().all(),
        "tess_queries_recorded": result.tess_status.notna().all(),
        "exofop_queries_recorded": result.exofop_status.notna().all(),
        "categories_exact": set(result.final_category).issubset(ALLOWED_CATEGORIES),
        "no_confirmed_claim": result.scientific_claim.eq("unconfirmed_signal_not_a_confirmed_exoplanet").all(),
        "transparent_score_reconciles": np.allclose(
            result.independent_evidence_score,
            result[component_scores].sum(axis=1),
        ),
    }


def _freeze_inputs(config: dict[str, Any]) -> pd.DataFrame:
    source = Path(config["inputs"]["shortlist"])
    shortlist = pd.read_csv(source, dtype={"target_id": str})
    if len(shortlist) != 20 or shortlist["candidate_id"].nunique() != 20:
        raise ValueError("Phase 9 requires the exact 20-row Phase 8 shortlist")
    destination = Path(config["artifacts"]["frozen_shortlist"])
    if destination.exists():
        frozen = pd.read_parquet(destination)
        frozen["target_id"] = frozen["target_id"].astype(str)
        if not frozen["candidate_id"].equals(shortlist["candidate_id"]):
            raise RuntimeError("Frozen Phase 9 input differs from the current Phase 8 shortlist")
        return frozen
    shortlist.to_parquet(destination, index=False)
    return shortlist


def _write_report(result: pd.DataFrame, config: dict[str, Any]) -> None:
    counts = result.final_category.value_counts()
    strong = result.loc[result.final_category == "strong_candidate", "candidate_id"].tolist()
    lines = [
        "# Phase 9 — Independent validation and statistical vetting",
        "",
        "## Scientific boundary and result",
        "",
        f"The frozen Phase 8 shortlist contains 20 signals on {result.target_id.astype(str).nunique()} unique Kepler targets. Independent vetting assigns **{counts.get('strong_candidate', 0)} strong**, **{counts.get('weak_candidate', 0)} weak**, and **{counts.get('likely_false_positive', 0)} likely false-positive** labels.",
        "",
        "None of these labels means a confirmed exoplanet. Every row remains an unconfirmed photometric signal; confirmation requires evidence and/or follow-up outside SXS.",
        "",
        "## Why the validation is non-circular",
        "",
        "The Phase 7 RF score is retained only as provenance and is not included in the Phase 9 evidence score or decision rules. FAP is computed from BLS peak statistics under shuffled light curves; odd/even and secondary tests use event-level flux measurements; transit morphology comes from a physical limb-darkened model; Gaia tests the sky scene; TESS uses another spacecraft and reduction; and the TOI lookup is a public community-vetting record. None consumes RF probabilities, RF features, CNN output, or training labels.",
        "",
        "## Methods",
        "",
        f"### Empirical BLS FAP\n\nFor every candidate, {config['fap']['permutations_per_target']:,} null realizations were evaluated over the same 0.5–50 day period grid and duration grid as Phase 8. Each Kepler source-file segment was circularly shifted by an independent random offset, preserving cadence sampling and within-segment correlated structure while breaking a common ephemeris. The test statistic is the maximum BLS power over the full grid, so it includes the period-search look-elsewhere effect. We use the add-one estimator `(exceedances + 1)/(N + 1)`; resolution is {1/(config['fap']['permutations_per_target']+1):.6f}.",
        "",
        "### Formal light-curve tests\n\nOdd and even event depths are measured separately with local baselines and compared with a two-sided Welch t-test (fail at p < 0.01). The phase-0.5 secondary depth is compared with a robust out-of-eclipse scatter estimate; a 3-sigma upper limit is always reported. A secondary is a red flag when it is at least 3 sigma and at least 10% of the primary depth.",
        "",
        "A circular-orbit, quadratic-limb-darkened `batman` transit is fitted to the binned folded photometry with period fixed to BLS. The fitted radius ratio, scaled semimajor axis, and impact parameter yield the grazing statistic `b + Rp/R*`; values >= 1 are treated as V-shaped/grazing red flags. Stellar radii from the frozen Phase 8 catalog convert the radius ratio to Earth radii, with >22 R_earth treated as a stellar/substellar-size red flag rather than a planet-like size.",
        "",
        "### External cross-matches\n\nGaia DR3 sources within 30 arcsec are retained. A non-primary Gaia source within 4 arcsec (approximately one Kepler pixel) and no more than 5 G magnitudes fainter is a high-risk contamination flag. TESS light curves are searched by a TIC entry explicitly matching the KIC; up to four products from the highest-priority available pipeline are analyzed with a targeted ±10% BLS search, requiring a best period within 1% and S/N >= 5. The NASA Exoplanet Archive TOI table, which is updated from ExoFOP-TESS, is position-matched within 10 arcsec and its disposition and period match are recorded.",
        "",
        "## Transparent evidence score",
        "",
        "The score is an audit aid, not a probability: FAP pass/borderline/fail = +3/+1/-3; odd-even = +1/-3; secondary = +1/-3; U/V shape = +2/-3; physical size = +1/-3; clean/high-risk Gaia scene = +1/-3; TESS confirmation/available non-confirmation = +2/-1; ExoFOP period match/FP flag = +1/-3. Unavailable evidence contributes zero. A key failure forces `likely_false_positive`; `strong_candidate` additionally requires all internal tests, clean Gaia, and TESS period confirmation. Other no-key-failure rows are `weak_candidate`.",
        "",
        "## Candidate results",
        "",
        "| P9 rank | Candidate | P (d) | FAP | Odd/even p | Secondary sig. | Shape | Rp (R_earth) | Gaia risk | TESS | ExoFOP | Score | Category |",
        "|---:|---|---:|---:|---:|---:|---|---:|:---:|:---:|---|---:|---|",
    ]
    for _, row in result.iterrows():
        radius_text = (
            f"{row.implied_companion_radius_earth:.2f}"
            if pd.notna(row.implied_companion_radius_earth)
            else "—"
        )
        lines.append(
            f"| {int(row.phase9_rank)} | {row.candidate_id} | {row.period_days:.6f} | {row.fap:.4f} | "
            f"{row.odd_even_p_value:.3g} | {row.secondary_significance:.2f} | {row.transit_shape} | "
            f"{radius_text} | {'yes' if row.gaia_high_risk_contaminant else 'no'} | "
            f"{'confirmed' if row.tess_period_confirmed else row.tess_status} | {row.exofop_status} | "
            f"{int(row.independent_evidence_score)} | `{row.final_category}` |"
        )
    lines += [
        "",
        "## Phase 10 priority",
        "",
        (", ".join(strong) if strong else "No signal meets the deliberately strict `strong_candidate` rule; Phase 10 must not imply otherwise."),
        "",
        "## Method references",
        "",
        "- Thompson et al. (2018), [Kepler DR25 Robovetter catalog](https://arxiv.org/abs/1710.06758), for the independent-vetting context including odd/even, secondary, and centroid diagnostics.",
        "- Kreidberg (2015), [`batman`: BAsic Transit Model cAlculatioN in Python](https://arxiv.org/abs/1507.08285), for the limb-darkened transit model.",
        "- [Astropy periodogram false-alarm documentation](https://docs.astropy.org/en/stable/timeseries/lombscargle.html#peak-significance-and-false-alarm-probabilities), for the interpretation and computational cost of bootstrap peak FAP estimates.",
        "- [MAST TESS archive](https://archive.stsci.edu/missions-and-data/tess), for the independent TESS light-curve products.",
        "- [ESA Gaia Archive documentation](https://gea.esac.esa.int/archive/documentation/), for Gaia DR3 source queries.",
        "- [NASA Exoplanet Archive TOI column documentation](https://exoplanetarchive.ipac.caltech.edu/docs/API_TOI_columns.html), which states that the table is updated from the ExoFOP TOI list.",
        "",
        "## Limitations",
        "",
        "- Empirical BLS FAP is conditional on this shuffle scheme, time sampling, detrending, and search grid. It is not the posterior probability that a signal is astrophysical and is not a Bayesian astrophysical false-positive probability such as VESPA.",
        "- Only four cached Kepler products per target were used in Phase 8/9, even when more quarters exist. Segment shifts preserve short-timescale correlation but cannot reproduce every instrumental systematic or long-period stellar process.",
        "- The odd/even and secondary tests use simplified robust depth estimators; multiple-testing corrections beyond the BLS maximum statistic are not claimed.",
        "- The `batman` fit fixes circular orbit and approximate quadratic limb darkening. Grazing geometry, dilution, eccentricity, and stellar-parameter uncertainty are degenerate, so fitted radii and densities are screening quantities, not characterization measurements.",
        "- Gaia proximity indicates contamination risk, not proof that a neighbor caused the signal. Conversely, unresolved binaries can evade Gaia.",
        "- A TESS non-detection is weak evidence because of its larger pixels, different bandpass, finite sector coverage, and noise; a TESS period match is independent photometric support but not confirmation of planetary nature.",
        "- The TOI table may lag live ExoFOP-TESS updates, and absence of a public record carries no positive evidential weight.",
        "",
    ]
    Path(config["artifacts"]["report"]).write_text("\n".join(lines), encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/independent_validation.yaml")
    parser.add_argument("--stage", choices=["all", "fap", "vetting", "crossmatch", "finalize"], default="all")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    try:
        summary = run_phase9(args.config, args.stage)
    except Exception:
        LOGGER.exception("Phase 9 failed")
        return 2
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
