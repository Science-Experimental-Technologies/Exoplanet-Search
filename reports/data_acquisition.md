# Data Acquisition and Ground Truth

## Result

Data acquisition completed successfully on 2026-08-25 (UTC snapshot date). The fixed
validation sample contains 20 Kepler host systems and 47 confirmed transiting
planets. MAST provided 341 unique long-cadence FITS products containing
1,333,613 table rows in total. All downloaded products passed the non-empty FITS
binary-table check; the generated manifest contains 781 available rows and no
skipped rows.

## Catalog provenance

Ground truth was queried from the NASA Exoplanet Archive `pscomppars` table via
its TAP-backed `astroquery` interface with `tran_flag = 1`. The complete snapshot
contains 4,731 confirmed transiting planets across 3,617 host identifiers.
Retrieval time, source URL, query constraint, and schema are embedded in Parquet
metadata and repeated in a JSON sidecar.

The archived catalog snapshot identifies two sample hosts by historical aliases:

- Kepler-13 is matched to `KOI-13`.
- Kepler-90 is matched to `KOI-351`.

These mappings are explicit in `configs/base.yaml`.

## Missing official parameters

No values were imputed during acquisition. The snapshot currently lacks transit
depth for Kepler-16 b and Kepler-90 i, and transit duration for Kepler-16 b.
Their periods and remaining available parameters are retained. Each affected
manifest row names the unavailable fields in `ground_truth_missing_fields`.

## Reproducibility notes

- Raw FITS files are cached below `data/raw/` and excluded from Git.
- The catalog snapshot and manifest are small, versioned artifacts.
- A repeated dataset build used cache hits for all 20 systems.
- Download/product counts vary by target according to public MAST coverage and
  are not forced to a uniform number.
