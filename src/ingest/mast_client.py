"""Download Kepler or TESS light curves from MAST with a local file cache.

Examples
--------
python -m src.ingest.mast_client --id 11904151 --id-type KIC
python -m src.ingest.mast_client --id 261136679 --id-type TIC --max-products 1
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

LOGGER = logging.getLogger("sxs.ingest")


class TargetNotFoundError(RuntimeError):
    """Raised when MAST returns no light curves for a target."""


class DownloadError(RuntimeError):
    """Raised when a search succeeds but no usable file is downloaded."""


@dataclass(frozen=True)
class DownloadSummary:
    target: str
    mission: str
    files: tuple[str, ...]
    product_count: int
    data_points: int | None
    time_start: float | None
    time_end: float | None
    from_cache: bool
    downloaded_at_utc: str


def _default_search(target: str, **kwargs: Any) -> Any:
    # Import lazily so unit tests and --help do not require the astronomy stack.
    from lightkurve import search_lightcurve

    return search_lightcurve(target, **kwargs)


class MastLightCurveClient:
    """Small, testable wrapper around ``lightkurve.search_lightcurve``."""

    def __init__(
        self,
        raw_dir: str | Path = "data/raw",
        search_fn: Callable[..., Any] | None = None,
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.search_fn = search_fn or _default_search

    def fetch(
        self,
        identifier: str | int,
        *,
        id_type: str = "KIC",
        mission: str | None = None,
        author: str | None = None,
        cadence: str | None = None,
        max_products: int | None = None,
        force: bool = False,
    ) -> DownloadSummary:
        """Fetch matching light curves, returning cached files when available."""

        normalized_type = id_type.strip().upper()
        if normalized_type not in {"KIC", "TIC"}:
            raise ValueError("id_type must be either 'KIC' or 'TIC'")
        identifier_text = str(identifier).strip()
        if not identifier_text:
            raise ValueError("identifier cannot be empty")
        if max_products is not None and max_products < 1:
            raise ValueError("max_products must be at least 1")

        resolved_mission = mission or ("Kepler" if normalized_type == "KIC" else "TESS")
        target = f"{normalized_type} {identifier_text}"
        target_dir = self.raw_dir / resolved_mission.lower() / f"{normalized_type.lower()}_{identifier_text}"
        metadata_path = target_dir / "download_summary.json"

        cached_files = self._cached_fits(target_dir)
        if cached_files and not force:
            removed = self._remove_invalid_fits(cached_files)
            if removed:
                LOGGER.warning("Removed %d incomplete/corrupt cached FITS file(s) for %s", removed, target)
                cached_files = self._cached_fits(target_dir)
        if cached_files and not force and self._cache_is_sufficient(
            metadata_path, cached_files, max_products
        ):
            # A scale-up run may deliberately request fewer chronological products
            # than an older cache contains.  Reuse the cache without silently
            # widening that run's observational coverage.
            selected_cached_files = (
                cached_files[:max_products] if max_products is not None else cached_files
            )
            summary = self._cached_summary(
                metadata_path, selected_cached_files, target, resolved_mission
            )
            LOGGER.info(
                "Cache hit for %s: %d file(s), %s data points, time range %s to %s",
                target,
                summary.product_count,
                summary.data_points if summary.data_points is not None else "unknown",
                summary.time_start if summary.time_start is not None else "unknown",
                summary.time_end if summary.time_end is not None else "unknown",
            )
            return summary
        target_dir.mkdir(parents=True, exist_ok=True)
        search_kwargs = {"mission": resolved_mission}
        if author:
            search_kwargs["author"] = author
        if cadence:
            search_kwargs["cadence"] = cadence

        LOGGER.info("Searching MAST for %s (mission=%s)", target, resolved_mission)
        try:
            search_result = self.search_fn(target, **search_kwargs)
        except Exception as exc:  # network/client errors need target context
            raise DownloadError(f"MAST search failed for {target}: {exc}") from exc

        if search_result is None or len(search_result) == 0:
            raise TargetNotFoundError(f"No {resolved_mission} light curves found for {target}")

        selected = search_result[:max_products] if max_products is not None else search_result
        LOGGER.info("Found %d product(s); downloading %d", len(search_result), len(selected))
        try:
            collection = selected.download_all(download_dir=str(target_dir))
        except Exception as exc:
            raise DownloadError(f"Download failed for {target}: {exc}") from exc

        files = self._paths_from_collection(collection)
        if not files:
            files = self._cached_fits(target_dir)
        if not files:
            raise DownloadError(f"MAST returned no readable files for {target}")
        removed = self._remove_invalid_fits(files)
        if removed:
            raise DownloadError(
                f"MAST returned {removed} incomplete/corrupt FITS file(s) for {target}; retry required"
            )

        data_points, time_start, time_end = self._collection_stats(collection)
        summary = DownloadSummary(
            target=target,
            mission=resolved_mission,
            files=tuple(str(path.resolve()) for path in files),
            product_count=len(files),
            data_points=data_points,
            time_start=time_start,
            time_end=time_end,
            from_cache=False,
            downloaded_at_utc=datetime.now(timezone.utc).isoformat(),
        )
        self._write_metadata(
            metadata_path,
            summary,
            available_product_count=len(search_result),
            cache_complete=max_products is None or len(selected) >= len(search_result),
        )
        LOGGER.info(
            "Saved %d file(s) for %s: %s data points, time range %s to %s",
            summary.product_count,
            target,
            data_points if data_points is not None else "unknown",
            time_start if time_start is not None else "unknown",
            time_end if time_end is not None else "unknown",
        )
        return summary

    @staticmethod
    def _cached_fits(target_dir: Path) -> list[Path]:
        if not target_dir.exists():
            return []
        return sorted(path for path in target_dir.rglob("*.fits") if path.is_file())

    @staticmethod
    def _cache_is_sufficient(
        metadata_path: Path,
        files: Sequence[Path],
        max_products: int | None,
    ) -> bool:
        """Avoid treating a one-product smoke-test cache as a full dataset."""

        if not metadata_path.is_file():
            return False
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            if max_products is not None:
                return len(files) >= max_products and int(payload.get("product_count", 0)) >= max_products
            return bool(payload.get("cache_complete", False))
        except (OSError, ValueError, TypeError):
            return False

    @staticmethod
    def _remove_invalid_fits(files: Sequence[Path]) -> int:
        """Delete only unreadable download artifacts so the archive client can retry."""

        from astropy.io import fits

        removed = 0
        for path in files:
            try:
                with fits.open(path, mode="readonly", memmap=True) as hdus:
                    hdus.verify("exception")
                    if not any(
                        getattr(hdu, "data", None) is not None and len(hdu.data) > 0
                        for hdu in hdus
                        if hasattr(hdu, "data")
                    ):
                        raise OSError("FITS has no non-empty data extension")
            except (OSError, ValueError, TypeError):
                path.unlink(missing_ok=True)
                removed += 1
        return removed

    @staticmethod
    def _paths_from_collection(collection: Any) -> list[Path]:
        if collection is None:
            return []
        paths: list[Path] = []
        for light_curve in collection:
            filename = getattr(light_curve, "filename", None)
            if filename and Path(filename).is_file():
                paths.append(Path(filename))
        return sorted(set(paths))

    @staticmethod
    def _collection_stats(collection: Any) -> tuple[int | None, float | None, float | None]:
        if collection is None:
            return None, None, None
        total = 0
        starts: list[float] = []
        ends: list[float] = []
        try:
            for light_curve in collection:
                time_values = light_curve.time.value
                if len(time_values) == 0:
                    continue
                total += len(time_values)
                starts.append(float(time_values[0]))
                ends.append(float(time_values[-1]))
        except (AttributeError, IndexError, TypeError, ValueError):
            return None, None, None
        if not starts:
            return 0, None, None
        return total, min(starts), max(ends)

    @staticmethod
    def _write_metadata(
        path: Path,
        summary: DownloadSummary,
        *,
        available_product_count: int,
        cache_complete: bool,
    ) -> None:
        payload = asdict(summary)
        payload["available_product_count"] = available_product_count
        payload["cache_complete"] = cache_complete
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _cached_summary(
        metadata_path: Path,
        files: Sequence[Path],
        target: str,
        mission: str,
    ) -> DownloadSummary:
        if metadata_path.is_file():
            try:
                payload = json.loads(metadata_path.read_text(encoding="utf-8"))
                cached_product_count = int(payload.get("product_count", len(files)))
                subset = cached_product_count != len(files)
                return DownloadSummary(
                    target=payload.get("target", target),
                    mission=payload.get("mission", mission),
                    files=tuple(str(path.resolve()) for path in files),
                    product_count=len(files),
                    # Aggregate metadata describes the original cache population,
                    # so do not attach it to a requested subset.
                    data_points=None if subset else payload.get("data_points"),
                    time_start=None if subset else payload.get("time_start"),
                    time_end=None if subset else payload.get("time_end"),
                    from_cache=True,
                    downloaded_at_utc=payload.get("downloaded_at_utc", "unknown"),
                )
            except (OSError, ValueError, TypeError):
                LOGGER.warning("Ignoring invalid cache metadata at %s", metadata_path)
        return DownloadSummary(
            target=target,
            mission=mission,
            files=tuple(str(path.resolve()) for path in files),
            product_count=len(files),
            data_points=None,
            time_start=None,
            time_end=None,
            from_cache=True,
            downloaded_at_utc="unknown",
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="Numeric KIC or TIC identifier")
    parser.add_argument("--id-type", choices=("KIC", "TIC"), default="KIC")
    parser.add_argument("--mission", choices=("Kepler", "K2", "TESS"))
    parser.add_argument("--author", help="MAST pipeline author, e.g. Kepler or SPOC")
    parser.add_argument("--cadence", choices=("long", "short", "fast"))
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--max-products", type=int, help="Limit downloads for smoke tests")
    parser.add_argument("--force", action="store_true", help="Bypass an existing cache")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    client = MastLightCurveClient(raw_dir=args.raw_dir)
    try:
        summary = client.fetch(
            args.id,
            id_type=args.id_type,
            mission=args.mission,
            author=args.author,
            cadence=args.cadence,
            max_products=args.max_products,
            force=args.force,
        )
    except (ValueError, TargetNotFoundError, DownloadError) as exc:
        LOGGER.error("%s", exc)
        return 2
    print(json.dumps(asdict(summary), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
