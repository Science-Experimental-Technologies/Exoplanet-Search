# Configuration Basics

Every SXS workflow is driven by a versioned YAML file in `configs/`. Treat a
configuration as part of the scientific method, not just an application
preference.

## Configuration files

| File | Workflow | Primary responsibility |
|---|---|---|
| `configs/base.yaml` | `baseline` | Fixed 20-host benchmark and six-stage pipeline |
| `configs/scaleup.yaml` | `scaleup` | Catalog-filtered benchmark expansion and model qualification |
| `configs/candidate_search.yaml` | `search` | Deterministic unknown-target selection and shortlist construction |
| `configs/independent_validation.yaml` | `validate` | FAP, photometric vetting, external crossmatch, and final classification |

## Safe editing workflow

1. Use a separate repository checkout for a new experiment: some workflows
   retain fixed model, prefetch, and run-record paths.
2. Copy the relevant YAML file to a new, clearly named configuration.
3. Change one documented assumption at a time.
4. Write outputs to new artifact paths; do not overwrite the accepted record.
5. Run a dry run where supported.
6. Record the config path, Git commit, dependency environment, and generated
   run record.
7. Label the result as a new experiment, not as the published benchmark.

## High-impact settings

- `bls.minimum_period_days`, `maximum_period_days`, and `durations_hours`
  define the search hypothesis space.
- `preprocess.flatten_window_length` changes which long-timescale variability
  is removed.
- `ingest.max_products` controls temporal coverage and resource use.
- `machine_learning.folds` and the RF/CNN blocks define model evaluation.
- `candidate_search.sample_size` and shortlist thresholds control review load.
- `fap.permutations_per_target` sets empirical FAP resolution.
- `vetting.*` defines independent evidence and failure thresholds.

!!! danger "Do not silently tune on the final shortlist"
    Changing thresholds after examining the shortlisted candidates creates a
    different analysis and can bias the result. Preserve the frozen artifacts
    and document any exploratory rerun separately.

See the complete [configuration reference](../reference/configuration.md) for
every section and its accepted role.
