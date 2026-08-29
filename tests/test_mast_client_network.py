"""Opt-in integration smoke test; excluded unless explicitly enabled."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.ingest.mast_client import MastLightCurveClient


@pytest.mark.network
@pytest.mark.skipif(
    os.getenv("SXS_RUN_NETWORK_TESTS") != "1",
    reason="set SXS_RUN_NETWORK_TESTS=1 to query MAST",
)
def test_download_one_real_kepler_product(tmp_path: Path) -> None:
    summary = MastLightCurveClient(tmp_path / "raw").fetch(
        "11904151",
        id_type="KIC",
        mission="Kepler",
        author="Kepler",
        cadence="long",
        max_products=1,
    )
    assert summary.product_count == 1
    assert summary.data_points is not None and summary.data_points > 0
    assert Path(summary.files[0]).is_file()

