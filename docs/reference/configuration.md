# Configuration Reference

## Shared sections

### `project`

Metadata used for run identity and deterministic seeds.

| Key | Meaning |
|---|---|
| `name` | Human-readable project name |
| `version` | Workflow/config schema identity, not necessarily package version |
| `random_seed` | Base seed for deterministic selection or simulation |

### `paths`

Roots for raw products, processed data, catalog snapshots, and reports. Paths
are interpreted relative to the repository working directory unless absolute.

### `ingest`

| Key | Meaning |
|---|---|
| `mission` | Mission queried; supplied configs use Kepler |
| `cadence` | Cadence class; supplied configs use long cadence |
| `author` | MAST product author filter |
| `max_products` | Maximum products per target; `null` means all matches |
| `cache` | Reuse local raw products where present |

### `preprocess`

Quality bitmask, asymmetric sigma thresholds, maximum interpolation gap,
Savitzky-Golay window/polynomial, break tolerance, iterations, and masking
sigma. `visualization_targets` selects baseline examples only.

### `bls`

| Key | Supplied value |
|---|---:|
| `minimum_period_days` | 0.5 |
| `maximum_period_days` | 50.0 |
| `durations_hours` | 1, 2, 4, 8, 12 |
| `top_k` | 5 where proposals are constructed |
| `frequency_oversampling` | 5.0 |
| `duration_oversampling` | 10 |
| `minimum_peak_separation_fraction` | 0.01 |
| `objective` | `snr` |
| `method` | `fast` |

Durations must be strictly shorter than the minimum period. At the supplied
0.5-day bound, the configured 12-hour duration is excluded; consult BLS
diagnostics for `durations_hours_used` and `durations_hours_excluded`.

## Baseline-only sections

### `catalog` and `dataset`

Define the NASA Exoplanet Archive table/output and the mission-product manifest.
`dataset.verify_fits` controls structural validation of downloaded products.

### `targets`

The fixed baseline list uses KIC identifiers, display names, optional archive
aliases, and documented selection reasons.

### `machine_learning`

Defines grouped folds, folded-view bins, negative target construction, and RF /
CNN hyperparameters. The baseline RF uses 400 trees; the scale-up RF uses 600.

## `scaleup`

- `workers`: acquisition concurrency;
- `target_file`: dynamically generated positive target list;
- `selection`: period, S/N, magnitude, quarter, class-balance, and query limits;
- `artifacts`: accepted output paths for data, models, experiments, and report.

The supplied configuration uses serial MAST acquisition because concurrent
requests previously produced partial responses.

## `candidate_search`

| Key | Supplied value / role |
|---|---|
| `sample_size` | 250 deterministic targets |
| `minimum_available_quarters` | 8 |
| magnitude bounds | 10.0–15.0 |
| `model_path` | Frozen RF v2 binary |
| `model_selection` | Selection-policy JSON |
| `shortlist_size` | 20 |
| `required_label` | Explicit unconfirmed-candidate label |
| sanity thresholds | Odd/even, secondary ratio, available centroid significance |
| `artifacts` | Pool, selection, candidates, shortlist, figures, report, run record |

## Independent validation

### `inputs`

Paths to the frozen shortlist, eligible pool, and processed target light curves.

### `fap`

The supplied config uses 1,000 permutations per target, eight workers, and
independent segment circular shifts. The worker currently hard-codes the
minimum roll fraction to 5%; editing `minimum_roll_fraction` in YAML alone does
not change that implementation. A different null construction requires a
reviewed code change and fresh null caches.

### `vetting`

Defines formal thresholds for odd/even significance, secondary eclipse,
grazing shape, companion radius, Gaia risk, TESS period/S/N, and ExoFOP match.

### `artifacts`

Defines frozen input, FAP, vetting, Gaia, crossmatch, final ranking, report, and
run-record destinations.

!!! warning
    Configuration values are coupled to the reported evidence. A changed value
    creates a new experiment and must use new artifact paths and interpretation.
