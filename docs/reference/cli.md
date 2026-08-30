# CLI Reference

## Top-level command

```text
python -m src.cli <command> [options]
```

| Command | Purpose |
|---|---|
| `baseline` | Run or inspect the fixed baseline recovery workflow |
| `scaleup` | Build the scaled benchmark and qualify the production model |
| `search` | Screen the deterministic unknown-target sample |
| `validate` | Run independent statistical and astrophysical validation |
| `demo` | Offline synthetic transit demonstration |
| `analyze` | CSV/FITS or single-KIC analysis |
| `report` | Rebuild an offline HTML analysis report |
| `inject` | Conditional flux-level injection recovery |
| `evaluate` | Nested target-grouped RF evaluation and bootstrap intervals |

Passing `--help` after a command prints its current parser reference.

See [Analysis Workbench](../guides/workbench.md) for the five new commands.
They write new output directories and are unreleased current-branch features.
The top-level dispatcher also accepts `--workspace DIR` after a legacy command
to isolate its configuration and relative outputs. Workspace errors and uncaught
workbench errors exit nonzero; there is not yet a universal error-code schema.

## `baseline`

```text
python -m src.cli baseline
  [--config PATH]
  [--from-stage {0,1,2,3,4,5}]
  [--to-stage {0,1,2,3,4,5}]
  [--resume]
  [--refresh-catalog]
  [--dry-run]
  [--log-path PATH]
  [--verbose]
```

| Option | Default | Effect |
|---|---|---|
| `--config` | `configs/base.yaml` | YAML configuration |
| `--from-stage` | `0` | First baseline stage to execute |
| `--to-stage` | `5` | Final baseline stage to execute |
| `--resume` | off | Require matching content checkpoint before skipping recorded completed stages |
| `--refresh-catalog` | off | Refresh official catalog snapshots before use |
| `--dry-run` | off | Emit the execution plan without running stages |
| `--log-path` | generated path | Override detailed run-record destination; the latest run record is still updated |
| `--verbose` | off | Enable debug logging |

Exit code `0` indicates success. Configuration, prerequisite, and pipeline
errors return `2`.

## `scaleup`

```text
python -m src.cli scaleup [--config PATH] [--resume]
```

`--config` defaults to `configs/scaleup.yaml`. `--resume` skips accepted work
where the scale-up orchestrator supports it. A completed record returns `0`;
an incomplete acceptance state returns `3`; an exception returns `2`.

## `search`

```text
python -m src.cli search [--config PATH] [--resume]
```

`--config` defaults to `configs/candidate_search.yaml`. The search expects the
frozen model selection and model binary. Completed status returns `0`; a
non-completed record returns `3`.

Uncaught search exceptions print a traceback and exit nonzero (normally `1`).
There is no shared error-code contract across all four workflows.

## `validate`

```text
python -m src.cli validate
  [--config PATH]
  [--stage {all,fap,vetting,crossmatch,finalize}]
  [--verbose]
```

| Stage | Output responsibility |
|---|---|
| `fap` | Segment-shuffle null rows and candidate FAP results |
| `vetting` | Odd/even, secondary, shape, and radius evidence |
| `crossmatch` | Gaia, TESS, and ExoFOP evidence |
| `finalize` | Reconciled ranking, categories, report, acceptance record |
| `all` | Complete sequence |

The default config is `configs/independent_validation.yaml`; the default stage
is `all`. A caught validation exception returns `2`.
