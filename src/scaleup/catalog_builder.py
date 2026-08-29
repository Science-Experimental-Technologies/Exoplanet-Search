"""Build deterministic Phase 7 confirmed and false-positive populations."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

LOGGER = logging.getLogger("sxs.scaleup.catalog")
SOURCE_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
FLAGS = {
    "not_transit": "koi_fpflag_nt",
    "stellar_eclipse": "koi_fpflag_ss",
    "centroid_offset": "koi_fpflag_co",
    "ephemeris_contamination": "koi_fpflag_ec",
}


def _query(**criteria: Any) -> Any:
    from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive

    return NasaExoplanetArchive.query_criteria(**criteria)


def build_scaleup_catalogs(
    config_path: str | Path = "configs/scaleup.yaml",
    *,
    query_fn: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    config_file = Path(config_path)
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    criteria = config["scaleup"]["selection"]
    query = query_fn or _query
    catalog_dir = Path(config["paths"]["catalog"])
    catalog_dir.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    minimum = float(criteria["minimum_period_days"])
    maximum = float(criteria["maximum_period_days"])

    LOGGER.info("Querying PSCompPars Kepler population")
    planets = _frame(
        query(
            table="pscomppars",
            select=(
                "pl_name,hostname,pl_orbper,pl_trandep,pl_trandur,pl_rade,"
                "disc_facility,discoverymethod,tran_flag,sy_kepmag"
            ),
            where=(
                "disc_facility = 'Kepler' and tran_flag = 1 and "
                f"pl_orbper between {minimum} and {maximum}"
            ),
            order="hostname,pl_orbper",
            cache=False,
        )
    )
    LOGGER.info("Querying Kepler confirmed-name mapping")
    names = _frame(
        query(
            table="keplernames",
            select="kepid,koi_name,kepler_name,pl_name",
            cache=False,
        )
    )
    LOGGER.info("Querying confirmed cumulative KOI quality fields")
    confirmed_koi = _frame(
        query(
            table="cumulative",
            select=(
                "kepid,kepoi_name,kepler_name,koi_disposition,koi_period,koi_model_snr,"
                "koi_duration,koi_depth,koi_kepmag"
            ),
            where=(
                "koi_disposition = 'CONFIRMED' and "
                f"koi_period between {minimum} and {maximum}"
            ),
            cache=False,
        )
    )
    LOGGER.info("Querying full in-domain cumulative false-positive population")
    false_positives = _frame(
        query(
            table="cumulative",
            select=(
                "kepid,kepoi_name,koi_disposition,koi_period,koi_time0bk,koi_duration,"
                "koi_depth,koi_model_snr,koi_kepmag,koi_fpflag_nt,koi_fpflag_ss,"
                "koi_fpflag_co,koi_fpflag_ec"
            ),
            where=(
                "koi_disposition = 'FALSE POSITIVE' and "
                f"koi_period between {minimum} and {maximum}"
            ),
            cache=False,
        )
    )

    name_map = names.dropna(subset=["pl_name", "kepid"]).drop_duplicates("pl_name")
    joined = planets.merge(
        name_map[["pl_name", "kepid", "koi_name", "kepler_name"]], on="pl_name", how="left"
    )
    koi_quality = confirmed_koi.drop_duplicates("kepoi_name")
    joined = joined.merge(
        koi_quality[["kepoi_name", "koi_model_snr", "koi_kepmag"]],
        left_on="koi_name",
        right_on="kepoi_name",
        how="left",
    )
    joined["kepid"] = pd.to_numeric(joined["kepid"], errors="coerce").astype("Int64")
    positive_quality = joined.loc[
        joined["kepid"].notna()
        & (pd.to_numeric(joined["koi_model_snr"], errors="coerce") >= float(criteria["positive_minimum_transit_snr"]))
        & (pd.to_numeric(joined["koi_kepmag"], errors="coerce") <= float(criteria["maximum_kepler_magnitude"]))
    ].copy()

    false_positives["kepid"] = pd.to_numeric(false_positives["kepid"], errors="coerce").astype("Int64")
    negative_quality = false_positives.loc[
        false_positives["kepid"].notna()
        & (pd.to_numeric(false_positives["koi_model_snr"], errors="coerce") >= float(criteria["negative_minimum_transit_snr"]))
        & (pd.to_numeric(false_positives["koi_kepmag"], errors="coerce") <= float(criteria["maximum_kepler_magnitude"]))
    ].copy()
    availability_ids = sorted(
        set(positive_quality["kepid"].astype(int)) | set(negative_quality["kepid"].astype(int))
    )
    availability = query_quarter_availability(
        availability_ids,
        query_fn=query,
        batch_size=int(criteria["availability_query_batch_size"]),
    )
    minimum_quarters = int(criteria["minimum_available_quarters"])
    positive_quality = positive_quality.merge(availability, on="kepid", how="left")
    negative_quality = negative_quality.merge(availability, on="kepid", how="left")
    positive_selected = positive_quality.loc[
        positive_quality["available_quarters"].fillna(0) >= minimum_quarters
    ].copy()
    negative_eligible = negative_quality.loc[
        negative_quality["available_quarters"].fillna(0) >= minimum_quarters
    ].copy()

    positive_selected = positive_selected.rename(
        columns={
            "hostname": "host_star_id",
            "pl_orbper": "period_days",
            "pl_trandep": "transit_depth_percent",
            "pl_trandur": "transit_duration_hours",
            "pl_rade": "planet_radius_earth",
        }
    )
    positive_selected["target_id"] = positive_selected["kepid"].astype(int).astype(str)
    positive_selected["catalog_source_table"] = "pscomppars joined keplernames and cumulative"
    positive_selected["catalog_source_url"] = SOURCE_URL
    positive_selected["catalog_retrieved_at_utc"] = retrieved_at
    positive_selected = positive_selected.sort_values(["target_id", "period_days", "pl_name"])
    _write_parquet(
        positive_selected,
        Path(config["catalog"]["output"]),
        {"retrieved_at_utc": retrieved_at, "selection": criteria},
    )

    target_rows = []
    for target_id, group in positive_selected.groupby("target_id", sort=True):
        host = str(group.iloc[0]["host_star_id"])
        target_rows.append(
            {
                "id": target_id,
                "id_type": "KIC",
                "name": host,
                "catalog_host": host,
                "reason": (
                    "Phase 7 full quality-filtered Kepler population: "
                    f"SNR>={criteria['positive_minimum_transit_snr']}, "
                    f"Kp<={criteria['maximum_kepler_magnitude']}, "
                    f"quarters>={criteria['minimum_available_quarters']}"
                ),
            }
        )
    target_path = Path(config["scaleup"]["target_file"])
    target_path.write_text(yaml.safe_dump({"targets": target_rows}, sort_keys=False), encoding="utf-8")

    full_fp = false_positives.copy()
    full_fp["catalog_source_table"] = "cumulative"
    full_fp["catalog_source_url"] = SOURCE_URL
    full_fp["catalog_retrieved_at_utc"] = retrieved_at
    _write_parquet(
        full_fp,
        catalog_dir / "false_positive_population.parquet",
        {"retrieved_at_utc": retrieved_at, "population": "all in-domain FALSE POSITIVE KOIs"},
    )
    balanced = select_balanced_false_positive_targets(
        negative_eligible,
        per_category=int(criteria["negative_targets_per_category"]),
        seed=int(config["project"]["random_seed"]),
        excluded_ids=set(positive_selected["target_id"]),
    )
    balanced = balanced.rename(
        columns={
            "kepid": "target_id",
            "kepoi_name": "koi_name",
            "koi_period": "catalog_period_days",
            "koi_time0bk": "catalog_epoch_bkjd",
            "koi_duration": "catalog_duration_hours",
            "koi_depth": "catalog_depth_ppm",
        }
    )
    balanced["target_id"] = balanced["target_id"].astype(int).astype(str)
    balanced["catalog_source_table"] = "cumulative"
    balanced["catalog_source_url"] = SOURCE_URL
    balanced["catalog_retrieved_at_utc"] = retrieved_at
    _write_parquet(
        balanced,
        Path(config["machine_learning"]["negative_sample"]["catalog_output"]),
        {"retrieved_at_utc": retrieved_at, "selection": criteria},
    )
    summary = {
        "generated_at_utc": retrieved_at,
        "selection": criteria,
        "raw_pscomppars_planets": len(planets),
        "raw_confirmed_koi": len(confirmed_koi),
        "raw_false_positive_koi": len(false_positives),
        "raw_false_positive_flag_counts": {
            category: int(false_positives[column].fillna(0).astype(int).sum())
            for category, column in FLAGS.items()
        },
        "positive_planets_after_quality": len(positive_selected),
        "positive_targets_after_quality": len(target_rows),
        "negative_koi_after_quality": len(negative_eligible),
        "negative_targets_selected": int(balanced["target_id"].nunique()),
        "negative_category_counts": balanced["negative_category"].value_counts().sort_index().to_dict(),
        "unmapped_pscomppars_planets": sorted(joined.loc[joined["kepid"].isna(), "pl_name"].astype(str).tolist()),
    }
    (catalog_dir / "selection_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def query_quarter_availability(
    target_ids: Sequence[int],
    *,
    query_fn: Callable[..., Any],
    batch_size: int = 150,
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for start in range(0, len(target_ids), batch_size):
        batch = target_ids[start : start + batch_size]
        LOGGER.info("Quarter availability %d-%d/%d", start + 1, min(start + len(batch), len(target_ids)), len(target_ids))
        where = f"targettype = 'long cadence' and star_id in ({','.join(map(str, batch))})"
        frame = _frame(
            query_fn(
                table="keplertimeseries",
                select="star_id,quarter,targettype",
                where=where,
                cache=False,
            )
        )
        if not frame.empty:
            rows.append(frame)
    if not rows:
        return pd.DataFrame(columns=["kepid", "available_quarters"])
    combined = pd.concat(rows, ignore_index=True)
    combined["star_id"] = pd.to_numeric(combined["star_id"], errors="coerce").astype("Int64")
    counts = combined.dropna(subset=["star_id", "quarter"]).groupby("star_id")["quarter"].nunique()
    return counts.rename("available_quarters").rename_axis("kepid").reset_index()


def select_balanced_false_positive_targets(
    frame: pd.DataFrame,
    *,
    per_category: int,
    seed: int,
    excluded_ids: set[str],
) -> pd.DataFrame:
    selected: list[pd.DataFrame] = []
    used = set(map(str, excluded_ids))
    for category, flag in FLAGS.items():
        pool = frame.loc[pd.to_numeric(frame[flag], errors="coerce").fillna(0).astype(int) == 1].copy()
        pool["selection_key"] = pool.apply(
            lambda row: hashlib.sha256(
                f"{seed}:{category}:{int(row['kepid'])}:{row['kepoi_name']}".encode()
            ).hexdigest(),
            axis=1,
        )
        pool = pool.sort_values(["selection_key", "kepoi_name"])
        pool = pool.loc[~pool["kepid"].astype(int).astype(str).isin(used)]
        pool = pool.drop_duplicates("kepid").head(per_category).copy()
        if len(pool) < per_category:
            raise RuntimeError(f"Only {len(pool)} eligible unique targets for {category}")
        pool["negative_category"] = category
        selected.append(pool)
        used.update(pool["kepid"].astype(int).astype(str))
    return pd.concat(selected, ignore_index=True).drop(columns="selection_key")


def _frame(result: Any) -> pd.DataFrame:
    return result.to_pandas() if hasattr(result, "to_pandas") else pd.DataFrame(result)


def _write_parquet(frame: pd.DataFrame, path: Path, metadata: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    encoded = {f"sxs.{key}".encode(): json.dumps(value, sort_keys=True).encode() for key, value in metadata.items()}
    table = table.replace_schema_metadata({**(table.schema.metadata or {}), **encoded})
    temporary = path.with_suffix(path.suffix + ".tmp")
    pq.write_table(table, temporary, compression="snappy")
    temporary.replace(path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/scaleup.yaml")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    summary = build_scaleup_catalogs(args.config)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
