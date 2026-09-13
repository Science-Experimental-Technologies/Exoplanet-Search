# CLI Reference

## Top-level command

```text
sxs <command> [options]
python -m src.cli <command> [options]
```

The installed `sxs` command and module form are equivalent.

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
| `doctor` | Read-only installation and optional service-connectivity diagnostics |
| `config-check` | Read-only structural and semantic workflow-YAML validation |
| `init` | Create or inspect an isolated, marked workflow workspace |
| `status` | Inspect configuration and recorded workspace state without mutation |
| `support-bundle` | Create a bounded, privacy-conscious diagnostic ZIP |
| `verify` | Verify checkpoint identity and recorded file hashes |

Passing `--help` after a command prints its current parser reference. Use
`sxs --version` to print the code version.

See [Analysis Workbench](../guides/workbench.md) for the five new commands.
They write new output directories and are included in v1.2.0.
The top-level dispatcher also accepts `--workspace DIR` after a legacy command
to isolate its configuration and relative outputs.

## `doctor`

!!! note
    `doctor` is part of the upcoming 1.4.0 release and is currently available
    from the main branch.

```text
sxs doctor [--json] [--network] [--timeout SECONDS]
```

Without `--network`, the command performs no external requests and checks the
supported Python range, exact direct dependency pins, and structural/semantic
validity of packaged default YAML configurations. `--json` emits a stable
machine-readable record suitable for a support ticket. `--network` additionally
checks the fixed HTTPS endpoints for MAST and the NASA Exoplanet Archive; it
does not download mission products.

The command returns `0` when all requested checks pass and `3` when a check
fails. Invalid arguments use exit code `2`.

## `config-check`

!!! info
    `config-check` is part of the upcoming 1.4.0 release and is currently
    available from the main branch.

```text
sxs config-check [CONFIG ...]
  [--workflow {auto,baseline,scaleup,search,validate}]
  [--json]
```

With no file arguments, the command validates all four packaged workflow
configurations against their expected workflows. For explicit files, `auto`
uses distinctive top-level sections to infer the workflow. An explicit
`--workflow` also detects accidentally using a configuration for the wrong
command. The check makes no network requests and does not require result
artifacts. It returns `0` when every file passes and `3` when any file fails.

## `init`

!!! tip
    `init` is part of the upcoming 1.4.0 release and is currently available
    from the main branch.

```text
sxs init WORKSPACE [--json]
```

The command creates a new marked workspace and copies the four packaged YAML
configurations into `WORKSPACE/configs/`. It validates the copies and records
the operation under `WORKSPACE/.sxs-state/`. Repeating the command on the same
marked workspace is safe and does not overwrite user edits. An existing
unmarked directory is rejected. It performs no scientific computation,
network request, or observation download.

## `status`

!!! example
    `status` is part of the upcoming 1.4.0 release and is currently available
    from the main branch.

```text
sxs status [WORKSPACE] [--json]
```

`WORKSPACE` defaults to the current directory. The command recognizes marked
SXS workspaces and the source checkout, validates all four workflow configs,
and summarizes the last operation, readable resume checkpoints, and latest
workflow run records. Corrupt metadata or configurations produce exit code 3;
missing checkpoints and run records are valid for a new workspace. This is a
bounded metadata check: it does not recompute artifact hashes, contact external
services, or prove that a recorded `running` process remains active.

## `support-bundle`

```text
sxs support-bundle [WORKSPACE] [--output ZIP] [--json]
```

The default workspace is the current directory and the default output is
`WORKSPACE/sxs-support-bundle.zip`. The command never overwrites an existing
archive. It writes only `README.txt` and `diagnostics.json`, containing runtime
versions, dependency checks, config validity and SHA-256 values, plus bounded
operation/checkpoint/run status. It excludes configuration contents,
observations, candidate tables, models, logs, environment variables,
credentials, and absolute workspace paths. No network request is made. Always
review `diagnostics.json` before sharing the archive.

## `verify`

```text
sxs verify [WORKSPACE]
  [--workflow {baseline,scaleup,search}]
  [--json]
```

The default workspace is the current directory and the default selection is all
three resume-capable workflows. Repeat `--workflow` to verify more than one
explicit checkpoint. The command recomputes the current config/runtime/source
identity and SHA-256 for every file recorded by each checkpoint. A recorded path
outside the workspace is rejected before opening it. Missing checkpoints,
identity mismatches, changed/missing files, malformed hashes, and unreadable
records return code 3. This can perform substantial disk I/O. It does not check
unrecorded files, external services, or scientific validity.

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
