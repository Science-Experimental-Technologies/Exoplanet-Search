# CLI preview

SXS runs in a terminal. These previews render **output recorded from the actual
CLI**, with a styled frame for readability. They are not screenshots of a
graphical application, and no new research run or discovery is implied.

Select a preview image to open it at full size. The expandable transcripts
below each image remain readable and copyable on smaller screens.

## Explore the commands

[![SXS CLI help showing the baseline, scaleup, search, and validate workflows](../assets/cli/help.svg)](../assets/cli/help.svg)

```bash
python -m src.cli --help
```

The four commands cover baseline recovery, scaled model qualification, candidate
screening, and independent validation. Add `--help` after a command to inspect
its options, for example `python -m src.cli validate --help`.

??? note "Copyable help output"

    ```text
    --8<-- "docs/assets/cli/help.txt"
    ```

## Preview a run without executing it

[![Baseline dry-run JSON excerpt showing all six stages marked would_run](../assets/cli/baseline-dry-run.svg)](../assets/cli/baseline-dry-run.svg)

```bash
python -m src.cli baseline --config configs/base.yaml --dry-run
```

`dry_run` means the pipeline was inspected, not executed. Each `would_run`
entry is a planned stage, not a completed stage. This command does not download
mission products, train models, or overwrite research artifacts.

The image is a compact JSON excerpt: it retains the exact `status`, `config_path`,
and all six `stages` values. The expandable transcript includes the remaining
JSON fields, except the two run timestamps, which are omitted to keep the
example reproducible. Dependency warnings on stderr are not shown in these
stdout previews and may differ between environments.

??? note "Copyable dry-run JSON (timestamps omitted)"

    ```json
    --8<-- "docs/assets/cli/baseline-dry-run.json"
    ```

## Try it yourself

Follow [Installation](installation.md) or the [Container guide](container.md),
then work through [Quickstart](quickstart.md). With the container, replace
`python -m src.cli` with:

```bash
docker run --rm ghcr.io/science-experimental-technologies/exoplanet-search:main
```

Append `--help` or `baseline --config configs/base.yaml --dry-run` as above.
Public pulls require the package's visibility to be Public; see the container
guide if registry authorization is denied.

For archived scientific outputs rather than CLI operation, see
[Results](../research/results.md) and [Interpreting results](../guides/interpreting-results.md).

## Refresh the previews

From a checkout with SXS dependencies installed:

```bash
python scripts/build_cli_previews.py
python scripts/build_cli_previews.py --check
```

The generator invokes only help and dry-run commands. It creates local SVGs and
text transcripts under `docs/assets/cli/`; no external image service is used.
CI checks that the committed previews still match the current CLI output.
