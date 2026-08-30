# Advanced Usage

## Run part of the baseline

The baseline accepts a contiguous stage range:

```bash
python -m src.cli baseline \
  --config configs/base.yaml \
  --from-stage 2 \
  --to-stage 3
```

| Stage | Name | Main responsibility |
|---:|---|---|
| 0 | environment | Validate packages, Python, config, and directories |
| 1 | acquisition | Catalog snapshot and Kepler manifest |
| 2 | preprocessing | Clean/detrended light curves |
| 3 | bls_detection | Candidate peaks and recovery report |
| 4 | machine_learning | Negative set, features, RF/CNN evaluation |
| 5 | catalog_validation | Catalog checks and benchmark report |

Starting after stage 1 requires prerequisite acceptance artifacts unless the
operation is a dry run.

## Force catalog refresh

```bash
python -m src.cli baseline \
  --config configs/base.yaml \
  --refresh-catalog
```

Refreshing can change the input snapshot. Preserve the prior snapshot and
metadata if comparison with the published record matters.

## Write a separate run log

```bash
python -m src.cli baseline \
  --config configs/base.yaml \
  --log-path reports/pipeline_runs/my_experiment.json
```

## Run validation stages separately

```bash
python -m src.cli validate --stage fap
python -m src.cli validate --stage vetting
python -m src.cli validate --stage crossmatch
python -m src.cli validate --stage finalize
```

Use this sequence when diagnosing a failed external service or reviewing an
intermediate artifact. `finalize` should only consume evidence generated for
the same frozen shortlist and configuration.

## Create a new experiment safely

Use a separate checkout and new output locations in a copied YAML file. Some
orchestrators still use fixed prefetch/model/run-record paths, so YAML overrides
alone do not fully isolate a run. A minimal experiment record
should include:

```text
experiment name
Git commit SHA
Python version and dependency lock
configuration path and SHA-256
input snapshot identifiers
start and finish time
generated artifact paths and hashes
deviations from the accepted method
scientific interpretation and limitations
```

Never overwrite the published final ranking when changing the search domain,
thresholds, null construction, or evidence rules.

## Resource controls

- reduce acquisition only for smoke tests by using a separate config;
- use `--resume` after verifying artifact compatibility;
- keep MAST acquisition serial where configured to avoid partial responses;
- retain null caches for interrupted FAP runs; and
- monitor free disk space before scaled or search workflows.

Null cache acceptance checks the realization count, not a hash of every BLS
setting and input curve. Do not reuse a cache after changing those inputs or
the null construction; use a separate validation directory/checkout.
