# Preprocessing and Signal Preservation

## Result

preprocessing completed successfully for all 20 validation systems. The pipeline read
1,333,613 raw FITS table rows and produced 1,263,184 finite, normalized samples
across 20 target-level Parquet files. No target was skipped.

| Operation | Samples |
|---|---:|
| Removed by Kepler quality bitmask `1130799` | 79,926 |
| Removed as non-finite after quality accounting | 4,645 |
| Removed by asymmetric sigma clipping | 768 |
| Added by small-gap interpolation | 14,910 |

Quality and non-finite counts are mutually exclusive in the summary, avoiding
double-counting rows that have both a bad flag and a missing flux.

## Method

Each FITS product is processed independently before target-level concatenation:

1. Read `TIME`, `PDCSAP_FLUX`, `PDCSAP_FLUX_ERR`, `SAP_QUALITY`, and `CADENCENO`
   without an implicit quality mask.
2. Remove rows selected by the configured Kepler bitmask and rows without finite
   time/flux values.
3. Apply asymmetric sigma clipping (`sigma_lower=10`, `sigma_upper=5`) to remove
   large flares and positive excursions while avoiding aggressive removal of
   transit dips.
4. Linearly interpolate gaps of at most three cadences. Synthetic samples are
   explicitly marked by `is_interpolated`, `quality=-1`, and `cadence=-1`.
5. Use `lightkurve.LightCurve.flatten()` separately on every quarter with a
   401-cadence (~8.2 day) Savitzky–Golay window. This is substantially longer
   than the configured maximum transit duration of 12 hours.
6. Normalize each segment and final flattened flux to median one.

Processing quarters separately prevents interpolation or trend fitting across
large spacecraft/quarter gaps. All parameter choices live in `configs/base.yaml`
and are embedded in each Parquet schema as provenance metadata.

## Transit-preservation check

Five deliberately deep-transit systems were folded on their known catalog
period solely for visual QA. The known period is not used by cleaning or
detrending.

| Planet | Catalog depth | Recovered 300-bin depth | Recovered/catalog |
|---|---:|---:|---:|
| Kepler-7 b | 0.75693% | 0.74642% | 98.61% |
| Kepler-8 b | 0.91457% | 0.91324% | 99.85% |
| Kepler-12 b | 1.67211% | 1.64067% | 98.12% |
| Kepler-14 b | 0.22523% | 0.22273% | 98.89% |
| Kepler-17 b | 2.18019% | 2.09678% | 96.17% |

All five transit signatures remain visually unambiguous after detrending,
including the active Kepler-17 host. Diagnostic figures are stored in
`reports/preprocessing_examples/`.

## Limitations

- Interpolation is suitable for short gaps only and synthetic points must remain
  identifiable in downstream model features.
- The window was selected as a fixed reproducible baseline, not optimized per
  star. A later sensitivity analysis should compare several windows.
- Period-folded depth recovery is a preservation diagnostic using known periods;
  it is not an independent transit detection result.
