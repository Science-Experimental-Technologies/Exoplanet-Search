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
They write new output directories and are included in v1.2.0.
The top-level dispatcher also accepts `--workspace DIR` after a legacy command
to isolate its configuration and relative outputs.

## Exit codes and status

The unified `sxs` / `python -m src.cli` dispatcher uses:

| Code | Meaning |
|---|---|
| 0 | Completed, help, or successful dry run |
| 1 | Execution failure, including pipeline/runtime exceptions |
| 2 | Argument error, missing file, invalid value, or missing configuration key |
| 3 | Workflow completed without satisfying its acceptance checks |
| 4 | Workspace locked by another process |
| 130 | Handled keyboard interruption |

Errors are summarized on stderr without an uncaught traceback. Once the output
destination is known, `operation.json` (workbench) or
`.sxs-state/operation_latest.json` (legacy workflows/report rebuilds) records
status, timestamps, progress where available, exit code, and error text.
Detailed workflow records remain available. Wrapped pipeline errors use code 1
even if their underlying cause was an invalid value. A hard process kill or
failure to write to disk cannot guarantee a final status record.

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

The shared exit-code contract above applies.

## `scaleup`

```text
python -m src.cli scaleup [--config PATH] [--resume]
```

`--config` defaults to `configs/scaleup.yaml`. `--resume` skips accepted work
where the scale-up orchestrator supports it. A completed record returns `0`;
an incomplete acceptance state returns `3`; exceptions use the shared contract.

## `search`

```text
python -m src.cli search [--config PATH] [--resume]
```

`--config` defaults to `configs/candidate_search.yaml`. The search expects the
frozen model selection and model binary. Completed status returns `0`; a
non-completed record returns `3`.

Search exceptions use the shared contract.

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
is `all`. Validation exceptions use the shared contract.
