"""Acquire a deterministic, flag-balanced Kepler DR25 false-positive sample."""

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
from src.config import load_targets

LOGGER = logging.getLogger("sxs.false_positives")

SOURCE_TABLE = "cumulative"
SOURCE_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
SELECT_COLUMNS = (
    "kepid,kepoi_name,koi_disposition,koi_period,koi_time0bk,koi_duration,"
    "koi_depth,koi_fpflag_nt,koi_fpflag_ss,koi_fpflag_co,koi_fpflag_ec"
)
FLAG_CATEGORIES = {
    "not_transit": "koi_fpflag_nt",
    "stellar_eclipse": "koi_fpflag_ss",
    "centroid_offset": "koi_fpflag_co",
    "ephemeris_contamination": "koi_fpflag_ec",
}


def _default_query(**criteria: Any) -> Any:
    from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive

    return NasaExoplanetArchive.query_criteria(**criteria)


def fetch_false_positive_sample(
    config_path: str | Path = "configs/base.yaml",
    *,
    query_fn: Callable[..., Any] | None = None,
) -> pd.DataFrame:
    """Query the official cumulative KOI table and persist a balanced sample."""

    config_file = Path(config_path)
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    settings = config["machine_learning"]["negative_sample"]
    output = Path(settings["catalog_output"])
    per_category = int(settings["per_category"])
    seed = int(config["project"]["random_seed"])
    positive_ids = {str(target["id"]) for target in load_targets(config)}
    where = (
        "koi_disposition = 'FALSE POSITIVE' and "
        f"koi_period between {config['bls']['minimum_period_days']} and "
        f"{config['bls']['maximum_period_days']} and "
        "koi_duration is not null and koi_depth is not null and koi_time0bk is not null"
    )
    result = (query_fn or _default_query)(
        table=SOURCE_TABLE,
        select=SELECT_COLUMNS,
        where=where,
        order="kepid,kepoi_name",
        cache=False,
    )
    frame = result.to_pandas() if hasattr(result, "to_pandas") else pd.DataFrame(result)
    missing = sorted(set(SELECT_COLUMNS.split(",")) - set(frame.columns))
    if missing:
        raise RuntimeError(f"False-positive response is missing: {', '.join(missing)}")
    frame = frame.dropna(subset=["kepid", "koi_period", "koi_time0bk", "koi_duration", "koi_depth"]).copy()
    frame["kepid"] = pd.to_numeric(frame["kepid"], errors="coerce").astype("Int64")
    frame = frame.loc[~frame["kepid"].astype(str).isin(positive_ids)]
    for flag in FLAG_CATEGORIES.values():
        frame[flag] = pd.to_numeric(frame[flag], errors="coerce").fillna(0).astype(int)

    selected: list[pd.DataFrame] = []
    used_ids: set[str] = set()
    for category, flag in FLAG_CATEGORIES.items():
        pool = frame.loc[frame[flag] == 1].copy()
        pool["selection_key"] = pool.apply(
            lambda row: hashlib.sha256(
                f"{seed}:{category}:{int(row['kepid'])}:{row['kepoi_name']}".encode()
            ).hexdigest(),
            axis=1,
        )
        pool = pool.sort_values(["selection_key", "kepoi_name"])
        pool = pool.loc[~pool["kepid"].astype(str).isin(used_ids)]
        pool = pool.drop_duplicates("kepid").head(per_category).copy()
        if len(pool) != per_category:
            raise RuntimeError(f"Only {len(pool)} unique targets available for {category}")
        pool["negative_category"] = category
        selected.append(pool)
        used_ids.update(pool["kepid"].astype(str))

    sample = pd.concat(selected, ignore_index=True).drop(columns="selection_key")
    sample = sample.rename(
        columns={
            "kepid": "target_id",
            "kepoi_name": "koi_name",
            "koi_period": "catalog_period_days",
            "koi_time0bk": "catalog_epoch_bkjd",
            "koi_duration": "catalog_duration_hours",
            "koi_depth": "catalog_depth_ppm",
        }
    )
    sample["target_id"] = sample["target_id"].astype(str)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    sample["catalog_source_table"] = SOURCE_TABLE
    sample["catalog_source_url"] = SOURCE_URL
    sample["catalog_retrieved_at_utc"] = retrieved_at
    sample = sample.sort_values(["negative_category", "target_id"]).reset_index(drop=True)

    output.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        b"sxs.source_table": SOURCE_TABLE.encode(),
        b"sxs.source_url": SOURCE_URL.encode(),
        b"sxs.retrieved_at_utc": retrieved_at.encode(),
        b"sxs.query_where": where.encode(),
        b"sxs.selection_seed": str(seed).encode(),
        b"sxs.per_category": str(per_category).encode(),
    }
    table = pa.Table.from_pandas(sample, preserve_index=False)
    table = table.replace_schema_metadata({**(table.schema.metadata or {}), **metadata})
    temporary = output.with_suffix(output.suffix + ".tmp")
    pq.write_table(table, temporary, compression="snappy")
    temporary.replace(output)
    output.with_suffix(".metadata.json").write_text(
        json.dumps(
            {
                "source_table": SOURCE_TABLE,
                "source_url": SOURCE_URL,
                "retrieved_at_utc": retrieved_at,
                "where": where,
                "selection_seed": seed,
                "per_category": per_category,
                "row_count": len(sample),
                "target_count": sample["target_id"].nunique(),
                "category_counts": sample["negative_category"].value_counts().sort_index().to_dict(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    LOGGER.info("Saved %d official Kepler false positives to %s", len(sample), output)
    return sample


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    try:
        sample = fetch_false_positive_sample(args.config)
    except Exception as exc:
        LOGGER.error("False-positive catalog acquisition failed: %s", exc)
        return 2
    print(json.dumps({"rows": len(sample), "targets": sample["target_id"].nunique()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
