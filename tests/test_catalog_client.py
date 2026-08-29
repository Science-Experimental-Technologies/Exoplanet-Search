from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest

from src.ingest.catalog_client import fetch_confirmed_transiting_catalog


def _catalog_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "pl_name": ["Kepler-10 b"],
            "hostname": ["Kepler-10"],
            "pl_orbper": [0.83749],
            "pl_trandep": [0.0152],
            "pl_trandur": [1.81],
            "pl_rade": [1.47],
            "disc_facility": ["Kepler"],
            "discoverymethod": ["Transit"],
            "tran_flag": [1],
        }
    )


def test_catalog_snapshot_has_required_columns_and_provenance(tmp_path: Path) -> None:
    calls = []

    def query(**criteria):
        calls.append(criteria)
        return _catalog_frame()

    destination = tmp_path / "catalog" / "confirmed.parquet"
    frame = fetch_confirmed_transiting_catalog(destination, query_fn=query)

    assert destination.is_file()
    assert frame.loc[0, "host_star_id"] == "Kepler-10"
    assert frame.loc[0, "period_days"] == pytest.approx(0.83749)
    assert calls[0]["where"] == "tran_flag = 1"
    assert calls[0]["cache"] is False

    metadata = pq.read_metadata(destination).metadata
    assert metadata[b"sxs.source_table"] == b"pscomppars"
    sidecar = json.loads(destination.with_suffix(".metadata.json").read_text(encoding="utf-8"))
    assert sidecar["row_count"] == 1


def test_empty_catalog_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="empty transit catalog"):
        fetch_confirmed_transiting_catalog(
            tmp_path / "empty.parquet",
            query_fn=lambda **_kwargs: _catalog_frame().iloc[0:0],
        )

