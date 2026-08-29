"""Run Phase 2 preprocessing for every target in the Phase 1 manifest."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import matplotlib
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from src.preprocess.clean import clean_light_curve_files
from src.preprocess.detrend import detrend_light_curve
from src.config import load_targets

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

LOGGER = logging.getLogger("sxs.preprocess")


def build_processed_dataset(config_path: str | Path = "configs/base.yaml") -> pd.DataFrame:
    config_file = Path(config_path)
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    manifest_path = Path(config["dataset"]["manifest"])
    catalog_path = Path(config["catalog"]["output"])
    manifest = pd.read_csv(manifest_path, dtype={"target_id": str})
    catalog = pd.read_parquet(catalog_path)
    available = manifest.loc[manifest["status"] == "available"].copy()
    if available.empty:
        raise RuntimeError("Manifest contains no available light curves")

    parameters = config["preprocess"]
    processed_dir = Path(config["paths"]["processed"])
    processed_dir.mkdir(parents=True, exist_ok=True)
    plot_dir = Path(config["paths"]["reports"]) / "preprocessing_examples"
    plot_dir.mkdir(parents=True, exist_ok=True)
    visualization_targets = set(parameters.get("visualization_targets", []))
    summary_rows: list[dict[str, Any]] = []

    targets = load_targets(config)
    for index, target in enumerate(targets, start=1):
        target_id = str(target["id"])
        name = str(target["name"])
        target_manifest = available.loc[available["target_id"] == target_id]
        files = sorted(target_manifest["light_curve_path"].dropna().unique())
        if not files:
            summary_rows.append(
                {"target_id": target_id, "host_name": name, "status": "skipped_no_available_files"}
            )
            continue
        LOGGER.info("[%d/%d] Cleaning %s from %d products", index, len(targets), name, len(files))
        try:
            cleaned, stats = clean_light_curve_files(
                files,
                quality_bitmask=int(parameters["quality_bitmask"]),
                sigma_lower=float(parameters["sigma_lower"]),
                sigma_upper=float(parameters["sigma_upper"]),
                sigma_maxiters=int(parameters["sigma_maxiters"]),
                max_gap_cadences=int(parameters["max_gap_cadences"]),
            )
            processed = detrend_light_curve(
                cleaned,
                window_length=int(parameters["flatten_window_length"]),
                polyorder=int(parameters["flatten_polyorder"]),
                break_tolerance=int(parameters["flatten_break_tolerance"]),
                niters=int(parameters["flatten_niters"]),
                sigma=float(parameters["flatten_sigma"]),
            )
        except Exception as exc:
            LOGGER.exception("Preprocessing failed for %s", name)
            summary_rows.append(
                {"target_id": target_id, "host_name": name, "status": "skipped_processing_error", "reason": str(exc)}
            )
            continue

        destination = processed_dir / f"{target_id}_clean.parquet"
        retrieved_at = target_manifest["catalog_retrieved_at_utc"].dropna().iloc[0]
        _write_processed_parquet(
            processed,
            destination,
            metadata={
                "target_id": target_id,
                "host_name": name,
                "mission": config["ingest"]["mission"],
                "time_system": "BKJD",
                "catalog_retrieved_at_utc": str(retrieved_at),
                "preprocessing_parameters": json.dumps(parameters, sort_keys=True),
            },
        )
        if name in visualization_targets:
            catalog_host = target.get("catalog_host", name)
            ground_truth = catalog.loc[catalog["host_star_id"] == catalog_host]
            _plot_diagnostic(processed, name, ground_truth, plot_dir / f"{target_id}_{name.lower()}_before_after.png")

        summary_rows.append(
            {
                "target_id": target_id,
                "host_name": name,
                "status": "available",
                "product_count": len(files),
                "input_points": stats.input_points,
                "quality_removed": stats.quality_removed,
                "nonfinite_removed": stats.nonfinite_removed,
                "outliers_removed": stats.outliers_removed,
                "interpolated_points": stats.interpolated_points,
                "output_points": len(processed),
                "detrended_median": float(np.nanmedian(processed["flux_detrended"])),
                "output_path": _portable_path(destination),
            }
        )
        LOGGER.info(
            "Saved %s: %d points (%d quality, %d nonfinite, %d outliers removed; %d interpolated)",
            destination,
            len(processed),
            stats.quality_removed,
            stats.nonfinite_removed,
            stats.outliers_removed,
            stats.interpolated_points,
        )

    summary = pd.DataFrame(summary_rows)
    generated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "generated_at_utc": generated_at,
        "config_path": _portable_path(config_file),
        "target_count": len(targets),
        "available_targets": int((summary["status"] == "available").sum()),
        "skipped_targets": int((summary["status"] != "available").sum()),
        "totals": {
            column: int(summary[column].fillna(0).sum())
            for column in (
                "input_points",
                "quality_removed",
                "nonfinite_removed",
                "outliers_removed",
                "interpolated_points",
                "output_points",
            )
            if column in summary
        },
        "targets": summary.replace({np.nan: None}).to_dict(orient="records"),
    }
    (processed_dir / "preprocessing_summary.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def _write_processed_parquet(frame: pd.DataFrame, destination: Path, *, metadata: dict[str, str]) -> None:
    table = pa.Table.from_pandas(frame, preserve_index=False)
    encoded = {f"sxs.{key}".encode(): value.encode() for key, value in metadata.items()}
    table = table.replace_schema_metadata({**(table.schema.metadata or {}), **encoded})
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    pq.write_table(table, temporary, compression="snappy")
    temporary.replace(destination)


def _plot_diagnostic(
    frame: pd.DataFrame,
    host_name: str,
    ground_truth: pd.DataFrame,
    destination: Path,
) -> None:
    figure, axes = plt.subplots(3, 1, figsize=(12, 9), constrained_layout=True)
    axes[0].scatter(frame["time_bkjd"], frame["flux_raw_normalized"], s=0.35, alpha=0.3, color="#6b7280")
    axes[0].set(title=f"{host_name}: before detrending", ylabel="Normalized raw flux")
    axes[1].scatter(frame["time_bkjd"], frame["flux_detrended"], s=0.35, alpha=0.3, color="#2563eb")
    axes[1].set(title="After per-quarter detrending", xlabel="Time (BKJD)", ylabel="Detrended flux")

    usable = ground_truth.dropna(subset=["period_days"]).copy()
    if not usable.empty:
        ranked = usable.sort_values("transit_depth_percent", ascending=False, na_position="last")
        planet = ranked.iloc[0]
        period = float(planet["period_days"])
        phase = np.mod(frame["time_bkjd"].to_numpy(dtype=float), period) / period
        flux = frame["flux_detrended"].to_numpy(dtype=float)
        axes[2].scatter(phase, flux, s=0.35, alpha=0.035, color="#94a3b8", rasterized=True)
        edges = np.linspace(0, 1, 301)
        indices = np.digitize(phase, edges) - 1
        centers = (edges[:-1] + edges[1:]) / 2
        binned = np.array([np.nanmedian(flux[indices == idx]) if np.any(indices == idx) else np.nan for idx in range(300)])
        axes[2].plot(centers, binned, color="#dc2626", linewidth=1.5, label="300-bin median")
        depth = planet.get("transit_depth_percent")
        depth_label = "unknown" if pd.isna(depth) else f"{float(depth):.4g}%"
        axes[2].set(
            title=f"Folded on {planet['pl_name']} — period {period:.6g} d, catalog depth {depth_label}",
            xlabel="Orbital phase",
            ylabel="Detrended flux",
            xlim=(0, 1),
        )
        lower, upper = np.nanquantile(binned, [0.01, 0.99])
        margin = max((upper - lower) * 0.4, 0.001)
        axes[2].set_ylim(lower - margin, upper + margin)
        axes[2].legend(loc="best")
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=160)
    plt.close(figure)


def _portable_path(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    try:
        summary = build_processed_dataset(args.config)
    except Exception as exc:
        LOGGER.error("Phase 2 preprocessing failed: %s", exc)
        return 2
    print(json.dumps({"targets": len(summary), "status": summary["status"].value_counts().to_dict()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
