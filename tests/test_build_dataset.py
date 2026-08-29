from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml
from astropy.io import fits

from src.ingest.build_dataset import build_dataset
from src.ingest.mast_client import DownloadSummary


class FakeClient:
    def __init__(self, filename: Path) -> None:
        self.filename = filename
        self.calls = []

    def fetch(self, identifier, **kwargs):
        self.calls.append((identifier, kwargs))
        return DownloadSummary(
            target=f"KIC {identifier}",
            mission="Kepler",
            files=(str(self.filename),),
            product_count=1,
            data_points=3,
            time_start=1.0,
            time_end=3.0,
            from_cache=False,
            downloaded_at_utc="2026-01-01T00:00:00+00:00",
        )


def test_build_dataset_maps_files_to_all_planets(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    fits_path = tmp_path / "data" / "raw" / "kepler" / "target.fits"
    fits_path.parent.mkdir(parents=True)
    column = fits.Column(name="TIME", format="D", array=[1.0, 2.0, 3.0])
    fits.HDUList([fits.PrimaryHDU(), fits.BinTableHDU.from_columns([column])]).writeto(fits_path)

    catalog_path = tmp_path / "data" / "catalog" / "confirmed.parquet"
    catalog_path.parent.mkdir(parents=True)
    pd.DataFrame(
        {
            "host_star_id": ["Kepler-X", "Kepler-X"],
            "pl_name": ["Kepler-X b", "Kepler-X c"],
            "period_days": [1.0, 2.0],
            "transit_depth_percent": [0.1, 0.2],
            "transit_duration_hours": [2.0, 3.0],
            "planet_radius_earth": [1.0, 2.0],
            "catalog_source_table": ["pscomppars", "pscomppars"],
            "catalog_retrieved_at_utc": ["now", "now"],
        }
    ).to_parquet(catalog_path, index=False)

    config = {
        "paths": {"raw": "data/raw"},
        "catalog": {"output": "data/catalog/confirmed.parquet"},
        "dataset": {"manifest": "data/processed/manifest.csv", "verify_fits": True},
        "ingest": {"mission": "Kepler", "author": "Kepler", "cadence": "long", "max_products": None},
        "targets": [{"id": "123", "id_type": "KIC", "name": "Kepler-X", "reason": "test"}],
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    client = FakeClient(fits_path)
    manifest = build_dataset(config_path, client=client)

    assert len(manifest) == 2
    assert set(manifest["planet_name"]) == {"Kepler-X b", "Kepler-X c"}
    assert set(manifest["status"]) == {"available"}
    assert set(manifest["light_curve_points"]) == {3}
    assert manifest["light_curve_path"].str.startswith("data/raw/").all()
    metadata = json.loads((tmp_path / "data/processed/manifest.metadata.json").read_text())
    assert metadata["target_count"] == 1

