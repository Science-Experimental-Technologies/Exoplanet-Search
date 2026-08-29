"""Quality filtering, outlier removal, and small-gap interpolation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
from astropy.io import fits
from astropy.stats import sigma_clip


@dataclass
class CleaningStats:
    input_points: int = 0
    quality_removed: int = 0
    nonfinite_removed: int = 0
    outliers_removed: int = 0
    interpolated_points: int = 0
    output_points: int = 0

    def add(self, other: "CleaningStats") -> None:
        for field in asdict(self):
            setattr(self, field, getattr(self, field) + getattr(other, field))


def clean_light_curve_files(
    files: Sequence[str | Path],
    *,
    quality_bitmask: int,
    sigma_lower: float = 10.0,
    sigma_upper: float = 5.0,
    sigma_maxiters: int = 5,
    max_gap_cadences: int = 3,
) -> tuple[pd.DataFrame, CleaningStats]:
    """Read and clean multiple FITS products without bridging product gaps."""

    frames: list[pd.DataFrame] = []
    total = CleaningStats()
    for filename in files:
        path = Path(filename)
        arrays = _read_fits_arrays(path)
        frame, stats = clean_light_curve_arrays(
            time=arrays["time"],
            flux=arrays["flux"],
            flux_err=arrays["flux_err"],
            quality=arrays["quality"],
            cadence=arrays["cadence"],
            source_file=_portable_path(path),
            quality_bitmask=quality_bitmask,
            sigma_lower=sigma_lower,
            sigma_upper=sigma_upper,
            sigma_maxiters=sigma_maxiters,
            max_gap_cadences=max_gap_cadences,
        )
        frames.append(frame)
        total.add(stats)
    if not frames:
        return pd.DataFrame(), total
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["time_bkjd", "source_file"]).drop_duplicates(
        subset=["time_bkjd"], keep="first"
    )
    combined = combined.reset_index(drop=True)
    total.output_points = len(combined)
    return combined, total


def clean_light_curve_arrays(
    *,
    time: np.ndarray,
    flux: np.ndarray,
    flux_err: np.ndarray,
    quality: np.ndarray,
    cadence: np.ndarray,
    source_file: str,
    quality_bitmask: int,
    sigma_lower: float = 10.0,
    sigma_upper: float = 5.0,
    sigma_maxiters: int = 5,
    max_gap_cadences: int = 3,
) -> tuple[pd.DataFrame, CleaningStats]:
    """Pure-array cleaning routine used by the FITS adapter and unit tests."""

    time = np.asarray(time, dtype=float)
    flux = np.asarray(flux, dtype=float)
    flux_err = np.asarray(flux_err, dtype=float)
    quality = np.asarray(quality, dtype=np.int64)
    cadence = np.asarray(cadence, dtype=np.int64)
    if not (len(time) == len(flux) == len(flux_err) == len(quality) == len(cadence)):
        raise ValueError("All light-curve arrays must have equal length")

    stats = CleaningStats(input_points=len(time))
    finite = np.isfinite(time) & np.isfinite(flux)
    good_quality = (quality & quality_bitmask) == 0
    stats.quality_removed = int((~good_quality).sum())
    stats.nonfinite_removed = int((good_quality & ~finite).sum())
    keep = finite & good_quality

    time = time[keep]
    flux = flux[keep]
    flux_err = flux_err[keep]
    quality = quality[keep]
    cadence = cadence[keep]
    order = np.argsort(time)
    time, flux, flux_err, quality, cadence = (
        values[order] for values in (time, flux, flux_err, quality, cadence)
    )
    if len(time) == 0:
        stats.output_points = 0
        return _empty_frame(), stats

    median_flux = float(np.nanmedian(flux))
    if not np.isfinite(median_flux) or median_flux == 0:
        raise ValueError(f"Invalid median flux in {source_file}")
    clipped = sigma_clip(
        flux / median_flux,
        sigma_lower=sigma_lower,
        sigma_upper=sigma_upper,
        maxiters=sigma_maxiters,
        masked=True,
    )
    outlier_mask = np.ma.getmaskarray(clipped)
    stats.outliers_removed = int(outlier_mask.sum())
    keep = ~outlier_mask
    time, flux, flux_err, quality, cadence = (
        values[keep] for values in (time, flux, flux_err, quality, cadence)
    )

    frame = pd.DataFrame(
        {
            "time_bkjd": time,
            "flux_raw": flux,
            "flux_err_raw": flux_err,
            "quality": quality,
            "cadence": cadence,
            "is_interpolated": False,
            "source_file": source_file,
        }
    )
    interpolated = _interpolate_small_gaps(frame, max_gap_cadences=max_gap_cadences)
    stats.interpolated_points = len(interpolated) - len(frame)
    stats.output_points = len(interpolated)
    return interpolated, stats


def _interpolate_small_gaps(frame: pd.DataFrame, *, max_gap_cadences: int) -> pd.DataFrame:
    if len(frame) < 3 or max_gap_cadences < 1:
        return frame
    times = frame["time_bkjd"].to_numpy()
    positive_steps = np.diff(times)
    positive_steps = positive_steps[positive_steps > 0]
    if len(positive_steps) == 0:
        return frame
    cadence_days = float(np.nanmedian(positive_steps))
    additions: list[dict[str, object]] = []
    for index, delta in enumerate(np.diff(times)):
        missing = int(round(delta / cadence_days)) - 1
        if missing < 1 or missing > max_gap_cadences:
            continue
        left = frame.iloc[index]
        right = frame.iloc[index + 1]
        for step in range(1, missing + 1):
            fraction = step / (missing + 1)
            additions.append(
                {
                    "time_bkjd": float(left.time_bkjd + fraction * delta),
                    "flux_raw": float(left.flux_raw + fraction * (right.flux_raw - left.flux_raw)),
                    "flux_err_raw": _linear_optional(left.flux_err_raw, right.flux_err_raw, fraction),
                    "quality": -1,
                    "cadence": -1,
                    "is_interpolated": True,
                    "source_file": left.source_file,
                }
            )
    if not additions:
        return frame
    return (
        pd.concat([frame, pd.DataFrame(additions)], ignore_index=True)
        .sort_values("time_bkjd")
        .reset_index(drop=True)
    )


def _linear_optional(left: float, right: float, fraction: float) -> float:
    if np.isfinite(left) and np.isfinite(right):
        return float(left + fraction * (right - left))
    return float("nan")


def _read_fits_arrays(path: Path) -> dict[str, np.ndarray]:
    """Read mission table columns without silently applying a quality mask."""

    with fits.open(path, mode="readonly", memmap=True) as hdus:
        if len(hdus) < 2 or hdus[1].data is None:
            raise ValueError(f"No light-curve table in {path}")
        data = hdus[1].data
        names = set(data.names or [])
        quality_column = "SAP_QUALITY" if "SAP_QUALITY" in names else "QUALITY"
        required = {"TIME", "PDCSAP_FLUX", "PDCSAP_FLUX_ERR", "CADENCENO", quality_column}
        missing = sorted(required - names)
        if missing:
            raise ValueError(f"Missing FITS columns in {path}: {', '.join(missing)}")
        return {
            "time": np.asarray(data["TIME"], dtype=float).copy(),
            "flux": np.asarray(data["PDCSAP_FLUX"], dtype=float).copy(),
            "flux_err": np.asarray(data["PDCSAP_FLUX_ERR"], dtype=float).copy(),
            "quality": np.asarray(data[quality_column], dtype=np.int64).copy(),
            "cadence": np.asarray(data["CADENCENO"], dtype=np.int64).copy(),
        }


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "time_bkjd",
            "flux_raw",
            "flux_err_raw",
            "quality",
            "cadence",
            "is_interpolated",
            "source_file",
        ]
    )


def _portable_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()
