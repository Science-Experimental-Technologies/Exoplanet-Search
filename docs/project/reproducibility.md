# Reproducibility

## Two reproducibility targets

### Reproduce the published evidence

Audit the versioned tables, reports, figures, configs, hashes, and run records
attached to the release. This is the correct route when checking the exact
reported metrics.

### Re-execute the process

Run the software against public services. This tests computational
repeatability, but current remote catalogs and product availability may differ
from the frozen acquisition time.

## Minimum record for a rerun

- repository commit and release;
- operating system and Python version;
- exact dependency files or environment lock;
- configuration file and hash;
- upstream query and retrieval metadata;
- random seeds;
- input/output artifact hashes;
- workflow command and options;
- start/finish time and status; and
- documented differences from the accepted run.

## Determinism controls

SXS uses fixed random seeds, SHA-256 target sampling, grouped folds, pinned
direct dependencies, versioned configs, and acceptance contracts. External
downloads and some numerical/ML operations can still vary across platforms or
dependency stacks.

## Validation commands

Install `requirements-docs.txt` in addition to the selected scientific profile
before running the MkDocs command below.

```bash
python -m pip check
python -m pytest -m "not network"
python -m src.cli baseline --config configs/base.yaml --dry-run
python -m mkdocs build --strict
```

The live MAST test is separate because it depends on external state.

## Protect the accepted record

A fresh Git clone includes archived reports and compact tables, but not fitted
models, raw light curves, or folded training tensors. Existence-based resume
checks in older releases could skip archived stages when those inputs were missing.
Current-branch resume requires matching content fingerprints and recorded steps;
it rejects legacy checkpoints. Use `--workspace DIR` to isolate a new run as
described in the [workbench guide](../guides/workbench.md).
For a new computation, use a separate checkout and run `baseline`, `scaleup`,
and `search` without `--resume` initially. Full baseline execution creates the
benchmark required by scaled training in an empty container workspace. Reserve
`--resume` for an interrupted, artifact-compatible run in that same workspace.

- never edit machine-readable results merely to make a report agree;
- regenerate related artifacts together after an authorized method change;
- use forward commits rather than rewriting published release tags;
- label exploratory thresholds and post-hoc analyses explicitly; and
- keep null/negative results rather than filtering them from the public record.

## Scientific metric consistency

The README, documentation site, RNAAS draft, and reports must agree on at least:

- 15/36 baseline BLS recovery;
- 12/36 baseline RF end-to-end recovery;
- 227/434 scaled BLS recovery;
- RF v2 precision 0.412, recall 0.903, threshold 0.221107;
- 250 searched targets and a 20-signal queue;
- 0 strong, 1 weak, and 19 likely false positives; and
- KIC 8300900-r1 FAP 0.01998.
