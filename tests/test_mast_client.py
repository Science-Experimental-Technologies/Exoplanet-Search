from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits

from src.ingest.mast_client import MastLightCurveClient, TargetNotFoundError


class FakeTime:
    def __init__(self, values: list[float]) -> None:
        self.value = np.asarray(values)


class FakeLightCurve:
    def __init__(self, filename: Path, times: list[float]) -> None:
        self.filename = str(filename)
        self.time = FakeTime(times)


class FakeSearchResult:
    def __init__(self, products: list[tuple[str, list[float]]]) -> None:
        self.products = products

    def __len__(self) -> int:
        return len(self.products)

    def __getitem__(self, item):
        if isinstance(item, slice):
            return FakeSearchResult(self.products[item])
        return self.products[item]

    def download_all(self, download_dir: str):
        destination = Path(download_dir) / "mastDownload" / "Kepler"
        destination.mkdir(parents=True, exist_ok=True)
        collection = []
        for filename, times in self.products:
            path = destination / filename
            table = fits.BinTableHDU.from_columns(
                [fits.Column(name="TIME", array=np.asarray(times), format="D")]
            )
            fits.HDUList([fits.PrimaryHDU(), table]).writeto(path, overwrite=True)
            collection.append(FakeLightCurve(path, times))
        return collection


def test_fetch_downloads_and_then_uses_cache(tmp_path: Path) -> None:
    calls = []

    def fake_search(target: str, **kwargs):
        calls.append((target, kwargs))
        return FakeSearchResult(
            [("quarter-1.fits", [100.0, 100.5, 101.0]), ("quarter-2.fits", [200.0, 201.0])]
        )

    client = MastLightCurveClient(tmp_path / "raw", search_fn=fake_search)
    first = client.fetch("11904151", id_type="KIC", cadence="long")

    assert first.from_cache is False
    assert first.product_count == 2
    assert first.data_points == 5
    assert first.time_start == 100.0
    assert first.time_end == 201.0
    assert all(Path(path).is_file() for path in first.files)
    assert calls == [("KIC 11904151", {"mission": "Kepler", "cadence": "long"})]

    second = client.fetch("11904151", id_type="KIC", cadence="long")
    assert second.from_cache is True
    assert second.data_points == 5
    assert len(calls) == 1

    metadata = Path(first.files[0]).parents[2] / "download_summary.json"
    payload = json.loads(metadata.read_text(encoding="utf-8"))
    assert payload["target"] == "KIC 11904151"
    assert payload["cache_complete"] is True


def test_fetch_limits_products(tmp_path: Path) -> None:
    result = FakeSearchResult([("one.fits", [1.0]), ("two.fits", [2.0])])
    client = MastLightCurveClient(tmp_path, search_fn=lambda *_args, **_kwargs: result)
    summary = client.fetch(1, max_products=1)
    assert summary.product_count == 1
    metadata = tmp_path / "kepler" / "kic_1" / "download_summary.json"
    assert json.loads(metadata.read_text(encoding="utf-8"))["cache_complete"] is False


def test_partial_cache_is_expanded_for_full_request(tmp_path: Path) -> None:
    calls = 0
    result = FakeSearchResult([("one.fits", [1.0]), ("two.fits", [2.0])])

    def fake_search(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return result

    client = MastLightCurveClient(tmp_path, search_fn=fake_search)
    client.fetch(1, max_products=1)
    complete = client.fetch(1)
    assert calls == 2
    assert complete.product_count == 2


def test_limited_request_reuses_only_requested_cached_products(tmp_path: Path) -> None:
    result = FakeSearchResult(
        [
            ("quarter-1.fits", [1.0]),
            ("quarter-2.fits", [2.0]),
            ("quarter-3.fits", [3.0]),
        ]
    )
    calls = 0

    def fake_search(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return result

    client = MastLightCurveClient(tmp_path, search_fn=fake_search)
    client.fetch(1)
    limited = client.fetch(1, max_products=2)

    assert calls == 1
    assert limited.from_cache is True
    assert limited.product_count == 2
    assert [Path(path).name for path in limited.files] == ["quarter-1.fits", "quarter-2.fits"]
    assert limited.data_points is None


def test_cache_without_metadata_is_not_trusted(tmp_path: Path) -> None:
    target_dir = tmp_path / "kepler" / "kic_1"
    target_dir.mkdir(parents=True)
    (target_dir / "partial.fits").write_bytes(b"truncated")
    result = FakeSearchResult([("replacement.fits", [1.0, 2.0])])
    calls = 0

    def fake_search(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return result

    summary = MastLightCurveClient(tmp_path, search_fn=fake_search).fetch(1, max_products=1)
    assert calls == 1
    assert summary.from_cache is False
    assert not (target_dir / "partial.fits").exists()



def test_missing_target_has_clear_error(tmp_path: Path) -> None:
    client = MastLightCurveClient(
        tmp_path,
        search_fn=lambda *_args, **_kwargs: FakeSearchResult([]),
    )
    with pytest.raises(TargetNotFoundError, match="No Kepler light curves found for KIC 0"):
        client.fetch(0)


def test_rejects_unknown_identifier_type(tmp_path: Path) -> None:
    client = MastLightCurveClient(tmp_path, search_fn=lambda *_args, **_kwargs: None)
    with pytest.raises(ValueError, match="id_type"):
        client.fetch(1, id_type="Gaia")
