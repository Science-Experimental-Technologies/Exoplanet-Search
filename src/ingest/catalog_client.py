"""Create a reproducible confirmed-transiting-planet catalog snapshot."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

LOGGER = logging.getLogger("sxs.catalog")

SOURCE_TABLE = "pscomppars"
SOURCE_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
SELECT_COLUMNS = (
    "pl_name,hostname,pl_orbper,pl_trandep,pl_trandur,pl_rade,"
    "disc_facility,discoverymethod,tran_flag"
)


def _default_query(**criteria: Any) -> Any:
    from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive

    return NasaExoplanetArchive.query_criteria(**criteria)


def fetch_confirmed_transiting_catalog(
    output_path: str | Path = "data/catalog/confirmed_exoplanets.parquet",
    *,
    query_fn: Callable[..., Any] | None = None,
) -> pd.DataFrame:
    """Query PSCompPars and atomically persist a provenance-bearing Parquet file."""

    query = query_fn or _default_query
    retrieved_at = datetime.now(timezone.utc).isoformat()
    LOGGER.info("Querying NASA Exoplanet Archive table %s", SOURCE_TABLE)
    result = query(
        table=SOURCE_TABLE,
        select=SELECT_COLUMNS,
        where="tran_flag = 1",
        order="hostname,pl_orbper",
        cache=False,
    )
    frame = _to_dataframe(result)
    if frame.empty:
        raise RuntimeError("NASA Exoplanet Archive returned an empty transit catalog")

    expected = SELECT_COLUMNS.split(",")
    missing = sorted(set(expected) - set(frame.columns))
    if missing:
        raise RuntimeError(f"Catalog response is missing columns: {', '.join(missing)}")

    frame = frame.loc[:, expected].copy()
    frame = frame.rename(
        columns={
            "hostname": "host_star_id",
            "pl_orbper": "period_days",
            "pl_trandep": "transit_depth_percent",
            "pl_trandur": "transit_duration_hours",
            "pl_rade": "planet_radius_earth",
        }
    )
    for column in (
        "period_days",
        "transit_depth_percent",
        "transit_duration_hours",
        "planet_radius_earth",
    ):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["tran_flag"] = pd.to_numeric(frame["tran_flag"], errors="coerce").astype("Int64")
    frame["catalog_source_table"] = SOURCE_TABLE
    frame["catalog_source_url"] = SOURCE_URL
    frame["catalog_retrieved_at_utc"] = retrieved_at
    frame = frame.sort_values(["host_star_id", "period_days", "pl_name"], na_position="last")
    frame = frame.reset_index(drop=True)

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        b"sxs.source_table": SOURCE_TABLE.encode(),
        b"sxs.source_url": SOURCE_URL.encode(),
        b"sxs.retrieved_at_utc": retrieved_at.encode(),
        b"sxs.query_where": b"tran_flag = 1",
    }
    table = pa.Table.from_pandas(frame, preserve_index=False)
    table = table.replace_schema_metadata({**(table.schema.metadata or {}), **metadata})
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    pq.write_table(table, temporary, compression="snappy")
    temporary.replace(destination)

    sidecar = destination.with_suffix(".metadata.json")
    sidecar.write_text(
        json.dumps(
            {
                "source_table": SOURCE_TABLE,
                "source_url": SOURCE_URL,
                "retrieved_at_utc": retrieved_at,
                "where": "tran_flag = 1",
                "row_count": len(frame),
                "columns": list(frame.columns),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    LOGGER.info("Saved %d confirmed transiting planets to %s", len(frame), destination)
    return frame


def _to_dataframe(result: Any) -> pd.DataFrame:
    if isinstance(result, pd.DataFrame):
        return result.copy()
    if hasattr(result, "to_pandas"):
        return result.to_pandas()
    return pd.DataFrame(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="data/catalog/confirmed_exoplanets.parquet",
        help="Destination Parquet path",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    try:
        frame = fetch_confirmed_transiting_catalog(args.output)
    except Exception as exc:
        LOGGER.error("Catalog acquisition failed: %s", exc)
        return 2
    print(json.dumps({"path": str(Path(args.output).resolve()), "rows": len(frame)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

