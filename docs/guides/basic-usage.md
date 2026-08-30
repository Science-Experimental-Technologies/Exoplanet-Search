# Basic Usage

## Command pattern

```bash
python -m src.cli <workflow> --config <configuration> [options]
```

Run commands from the repository root with the intended virtual environment
active.

## Baseline workflow

Preview it first:

```bash
python -m src.cli baseline --config configs/base.yaml --dry-run
```

Then execute or resume:

```bash
python -m src.cli baseline --config configs/base.yaml --resume
```

The full baseline needs `requirements.txt`, not only the core CI profile,
because it trains both RF and CNN baselines.

## Scale-up qualification

```bash
python -m src.cli scaleup --config configs/scaleup.yaml --resume
```

This selects benchmark targets, uses matched four-product coverage, builds the
expanded candidate set, evaluates RF v2/CNN v2, and writes the accepted model
selection. It is expensive and depends on remote mission/catalog services.

## Candidate screening

```bash
python -m src.cli search --config configs/candidate_search.yaml --resume
```

Before running, verify that `models/production_model_selection.json` identifies
the intended model and that the referenced model binary is present. The command
creates a frozen shortlist; it does not validate or confirm candidates.

## Independent validation

```bash
python -m src.cli validate --config configs/independent_validation.yaml --stage all
```

This command can run many BLS searches and external queries. It consumes the
frozen shortlist and the processed light curves from candidate screening.

## Monitor outputs

Each workflow prints structured JSON and writes a latest run record in
`reports/`. Inspect status, config path, counts, acceptance checks, and error
messages before relying on a report.

Useful files include:

- `reports/pipeline_run_latest.json`;
- `reports/scaleup_run_latest.json`;
- `reports/search_run_latest.json`; and
- `reports/validation_run_latest.json`.

See [Artifacts](../reference/artifacts.md) for the complete mapping.
