"""Build the data acquisition light-curve/ground-truth dataset manifest."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

import pandas as pd
import yaml
from astropy.io import fits

from src.ingest.catalog_client import fetch_confirmed_transiting_catalog
from src.config import load_targets
from src.ingest.mast_client import (
    DownloadError,
    MastLightCurveClient,
    TargetNotFoundError,
)

LOGGER = logging.getLogger("sxs.dataset")


def build_dataset(
    config_path: str | Path = "configs/base.yaml",
    *,
    refresh_catalog: bool = False,
    max_products: int | None = None,
    client: MastLightCurveClient | None = None,
    catalog_fetch_fn: Callable[..., pd.DataFrame] = fetch_confirmed_transiting_catalog,
) -> pd.DataFrame:
    """Download configured targets and write one manifest row per planet/product."""

    config_file = Path(config_path)
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    targets = load_targets(config)
    if not targets:
        raise ValueError("Configuration contains no targets")

    catalog_path = Path(config["catalog"]["output"])
    if refresh_catalog or not catalog_path.is_file():
        catalog = catalog_fetch_fn(catalog_path)
    else:
        catalog = pd.read_parquet(catalog_path)
    _validate_catalog(catalog)

    ingest = config["ingest"]
    configured_limit = ingest.get("max_products")
    product_limit = max_products if max_products is not None else configured_limit
    mast_client = client or MastLightCurveClient(config["paths"]["raw"])
    verify_fits = bool(config.get("dataset", {}).get("verify_fits", True))

    rows: list[dict[str, Any]] = []
    for index, target in enumerate(targets, start=1):
        identifier = str(target["id"])
        host_name = str(target["name"])
        catalog_host = str(target.get("catalog_host", host_name))
        planets = catalog.loc[catalog["host_star_id"] == catalog_host].copy()
        LOGGER.info("[%d/%d] Processing %s (%s %s)", index, len(targets), host_name, target["id_type"], identifier)

        if planets.empty:
            rows.append(
                _base_row(target, None)
                | {
                    "light_curve_path": None,
                    "light_curve_points": 0,
                    "download_from_cache": None,
                    "status": "skipped_catalog_missing",
                    "skip_reason": f"No transiting planet row for {host_name} in catalog snapshot",
                }
            )
            continue

        try:
            summary = mast_client.fetch(
                identifier,
                id_type=target["id_type"],
                mission=ingest.get("mission"),
                author=ingest.get("author"),
                cadence=ingest.get("cadence"),
                max_products=product_limit,
            )
        except (ValueError, TargetNotFoundError, DownloadError) as exc:
            LOGGER.error("Skipping %s: %s", host_name, exc)
            for _, planet in planets.iterrows():
                rows.append(
                    _base_row(target, planet)
                    | {
                        "light_curve_path": None,
                        "light_curve_points": 0,
                        "download_from_cache": None,
                        "status": "skipped_download_error",
                        "skip_reason": str(exc),
                    }
                )
            continue

        for filename in summary.files:
            path = Path(filename)
            point_count, error = _inspect_fits(path) if verify_fits else (None, None)
            status = "available" if error is None else "skipped_corrupt_file"
            if error:
                LOGGER.warning("Invalid FITS file %s: %s", path, error)
            for _, planet in planets.iterrows():
                rows.append(
                    _base_row(target, planet)
                    | {
                        "light_curve_path": _portable_path(path),
                        "light_curve_points": point_count,
                        "download_from_cache": summary.from_cache,
                        "status": status,
                        "skip_reason": error,
                    }
                )

    manifest = pd.DataFrame(rows)
    expected_ids = {str(target["id"]) for target in targets}
    represented_ids = set(manifest["target_id"].astype(str))
    missing_targets = sorted(expected_ids - represented_ids)
    if missing_targets:
        raise RuntimeError(f"Manifest omitted configured targets: {', '.join(missing_targets)}")

    manifest_path = Path(config["dataset"]["manifest"])
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    manifest.to_csv(temporary, index=False)
    temporary.replace(manifest_path)

    summary_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": _portable_path(config_file),
        "catalog_path": _portable_path(catalog_path),
        "target_count": len(targets),
        "planet_count": int(manifest["planet_name"].nunique(dropna=True)),
        "row_count": len(manifest),
        "available_rows": int((manifest["status"] == "available").sum()),
        "skipped_rows": int((manifest["status"] != "available").sum()),
        "status_counts": manifest["status"].value_counts().to_dict(),
    }
    manifest_path.with_suffix(".metadata.json").write_text(
        json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8"
    )
    LOGGER.info("Saved %d manifest rows to %s", len(manifest), manifest_path)
    return manifest


def _validate_catalog(catalog: pd.DataFrame) -> None:
    required = {
        "host_star_id",
        "pl_name",
        "period_days",
        "transit_depth_percent",
        "transit_duration_hours",
        "planet_radius_earth",
        "catalog_source_table",
        "catalog_retrieved_at_utc",
    }
    missing = sorted(required - set(catalog.columns))
    if missing:
        raise ValueError(f"Catalog is missing required columns: {', '.join(missing)}")


def _base_row(target: dict[str, Any], planet: pd.Series | None) -> dict[str, Any]:
    def value(column: str) -> Any:
        if planet is None:
            return None
        item = planet.get(column)
        return None if pd.isna(item) else item

    ground_truth = {
        "period_days": value("period_days"),
        "transit_depth_percent": value("transit_depth_percent"),
        "transit_duration_hours": value("transit_duration_hours"),
        "planet_radius_earth": value("planet_radius_earth"),
    }
    missing_fields = [name for name, item in ground_truth.items() if item is None]
    return {
        "target_id": str(target["id"]),
        "id_type": target["id_type"],
        "host_name": target["name"],
        "catalog_host_name": target.get("catalog_host", target["name"]),
        "target_selection_reason": target.get("reason"),
        "planet_name": value("pl_name"),
        **ground_truth,
        "ground_truth_missing_fields": ";".join(missing_fields) or None,
        "catalog_source_table": value("catalog_source_table"),
        "catalog_retrieved_at_utc": value("catalog_retrieved_at_utc"),
    }


def _inspect_fits(path: Path) -> tuple[int | None, str | None]:
    if not path.is_file():
        return 0, "file does not exist"
    if path.stat().st_size == 0:
        return 0, "file is empty"
    try:
        with fits.open(path, mode="readonly", memmap=True) as hdus:
            for hdu in hdus:
                if isinstance(hdu, fits.BinTableHDU) and hdu.data is not None:
                    rows = len(hdu.data)
                    if rows > 0:
                        return rows, None
            return 0, "FITS contains no non-empty binary table"
    except (OSError, ValueError, TypeError) as exc:
        return 0, f"unreadable FITS: {exc}"


def _portable_path(path: str | Path) -> str:
    candidate = Path(path).resolve()
    try:
        return candidate.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--refresh-catalog", action="store_true")
    parser.add_argument("--max-products", type=int, help="Override config for smoke tests")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    try:
        manifest = build_dataset(
            args.config,
            refresh_catalog=args.refresh_catalog,
            max_products=args.max_products,
        )
    except Exception as exc:
        LOGGER.error("Dataset build failed: %s", exc)
        return 2
    print(
        json.dumps(
            {
                "rows": len(manifest),
                "targets": int(manifest["target_id"].nunique()),
                "planets": int(manifest["planet_name"].nunique(dropna=True)),
                "status": manifest["status"].value_counts().to_dict(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
