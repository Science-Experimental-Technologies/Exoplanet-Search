"""Build a deterministic pool of Kepler targets with no official KOI history."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import pandas as pd
import requests
import yaml

LOGGER = logging.getLogger("sxs.candidate_search.pool")
TAP_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"


def build_unknown_pool(config_path: str | Path = "configs/candidate_search.yaml") -> dict[str, Any]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    settings = config["candidate_search"]
    artifacts = settings["artifacts"]
    retrieved_at = datetime.now(timezone.utc).isoformat()
    minimum_magnitude = float(settings["minimum_kepler_magnitude"])
    maximum_magnitude = float(settings["maximum_kepler_magnitude"])
    minimum_quarters = int(settings["minimum_available_quarters"])

    # The archive stores targettype as a fixed-width lower-case string.
    pool_query = (
        "select star_id,max(kepmag) as kepmag,count(quarter) as available_quarters,"
        "min(ra) as ra,min(dec) as dec,min(eff_temp) as effective_temperature_k,"
        "min(radius) as stellar_radius_solar "
        "from keplertimeseries where object_status=0 "
        "and targettype='long cadence     ' "
        f"and kepmag between {minimum_magnitude} and {maximum_magnitude} "
        "group by star_id"
    )
    koi_query = "select kepid,kepoi_name,koi_disposition from cumulative where kepid is not null"
    confirmed_query = "select kepid,kepler_name from keplernames where kepid is not null"
    LOGGER.info("Querying full not-categorized long-cadence population")
    pool = _tap_csv(pool_query)
    LOGGER.info("Querying all KOI identifiers for explicit exclusion")
    kois = _tap_csv(koi_query)
    confirmed = _tap_csv(confirmed_query)

    pool["star_id"] = pd.to_numeric(pool["star_id"], errors="coerce").astype("Int64")
    pool["available_quarters"] = pd.to_numeric(
        pool["available_quarters"], errors="coerce"
    ).astype("Int64")
    before_quarters = len(pool)
    pool = pool.loc[pool["available_quarters"] >= minimum_quarters].copy()
    koi_ids = set(pd.to_numeric(kois["kepid"], errors="coerce").dropna().astype(int))
    confirmed_ids = set(
        pd.to_numeric(confirmed["kepid"], errors="coerce").dropna().astype(int)
    )
    excluded_ids = koi_ids | confirmed_ids
    before_exclusion = len(pool)
    pool = pool.loc[~pool["star_id"].astype(int).isin(excluded_ids)].copy()
    pool["target_id"] = pool["star_id"].astype(int).astype(str)
    pool["selection_hash"] = pool["target_id"].map(
        lambda value: hashlib.sha256(
            f"{config['project']['random_seed']}:{value}".encode("utf-8")
        ).hexdigest()
    )
    pool = pool.sort_values(["selection_hash", "target_id"]).reset_index(drop=True)
    pool["catalog_status_at_selection"] = "not_categorized_no_koi_history"
    pool["required_output_label"] = settings["required_label"]
    pool["catalog_retrieved_at_utc"] = retrieved_at

    sample_size = int(settings["sample_size"])
    if len(pool) < sample_size:
        raise RuntimeError(f"Only {len(pool)} eligible unknown targets for sample size {sample_size}")
    selected = pool.head(sample_size).copy()
    selected["sample_rank"] = range(1, len(selected) + 1)

    eligible_path = Path(artifacts["eligible_pool"])
    selected_path = Path(artifacts["selected_targets"])
    summary_path = Path(artifacts["selection_summary"])
    eligible_path.parent.mkdir(parents=True, exist_ok=True)
    pool.to_parquet(eligible_path, index=False)
    targets = [
        {
            "id": row.target_id,
            "id_type": "KIC",
            "name": f"KIC {row.target_id}",
            "reason": (
                f"candidate screening deterministic unknown-pool sample; object_status=0, "
                f"no cumulative KOI or Kepler confirmed-name row, Kp={row.kepmag:.3f}, "
                f"available_quarters={int(row.available_quarters)}"
            ),
            "kepmag": float(row.kepmag),
            "available_quarters": int(row.available_quarters),
        }
        for row in selected.itertuples()
    ]
    selected_path.write_text(yaml.safe_dump({"targets": targets}, sort_keys=False), encoding="utf-8")
    summary = {
        "generated_at_utc": retrieved_at,
        "source": TAP_URL,
        "queries": {
            "not_categorized_pool": pool_query,
            "all_koi_ids": koi_query,
            "confirmed_kepler_ids": confirmed_query,
        },
        "raw_not_categorized_magnitude_limited_targets": before_quarters,
        "targets_after_quarter_filter": before_exclusion,
        "excluded_unique_official_ids": len(excluded_ids),
        "eligible_unknown_targets": len(pool),
        "selected_targets": len(selected),
        "selection_method": "ascending SHA-256 of '<seed>:<KIC>'; independent of light-curve signal",
        "criteria": {
            "object_status": 0,
            "targettype": "long cadence",
            "minimum_available_quarters": minimum_quarters,
            "kepler_magnitude_range": [minimum_magnitude, maximum_magnitude],
            "exclude_every_cumulative_koi_disposition": True,
            "exclude_every_kepler_confirmed_name": True,
        },
        "required_output_label": settings["required_label"],
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def _tap_csv(query: str) -> pd.DataFrame:
    response = requests.get(
        TAP_URL,
        params={"query": query, "format": "csv"},
        timeout=300,
    )
    response.raise_for_status()
    if response.text.lstrip().startswith("<?xml"):
        raise RuntimeError(f"TAP query failed: {response.text[:500]}")
    return pd.read_csv(io.StringIO(response.text))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/candidate_search.yaml")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    print(json.dumps(build_unknown_pool(args.config), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
