# Quickstart

This path verifies the installation without downloading mission products or
overwriting research artifacts.

Want to see the tool first? Open the [CLI preview gallery](cli-preview.md) for
recorded help output and a baseline dry-run preview with copyable transcripts.

## 1. Inspect the command surface

```bash
python -m src.cli --help
```

SXS exposes the research workflows `baseline`, `scaleup`, `search`, and
`validate`, plus `demo`, `analyze`, `report`, `inject`, and `evaluate` in the
[analysis workbench](../guides/workbench.md).

## 2. Preview the baseline workflow

```bash
python -m src.cli baseline --config configs/base.yaml --dry-run
```

The JSON plan should list the six baseline stages from environment validation
through catalog validation. A dry run does not execute those stages.

## 3. Run deterministic tests

```bash
python -m pytest -m "not network"
```

This checks preprocessing, BLS behavior, features, orchestration contracts,
candidate selection, and independent-validation rules using deterministic test
fixtures.

## 4. Choose a reproduction depth

| Goal | Command | Cost profile |
|---|---|---|
| Baseline research | `python -m src.cli baseline --config configs/base.yaml` | Full ML environment; public downloads |
| Scaled qualification | `python -m src.cli scaleup --config configs/scaleup.yaml` | Larger catalog/sample and model training |
| Bounded candidate screen | `python -m src.cli search --config configs/candidate_search.yaml` | 250 targets, four products each |
| Independent audit | `python -m src.cli validate --config configs/independent_validation.yaml --stage all` | 1,000 shuffles per target plus external queries |

!!! warning
    These execution commands write research artifacts. Use a separate checkout
    for a fresh computation. Add `--resume` only for an interrupted run with
    compatible artifacts; archived reports alone do not establish compatibility.
    `search` expects the accepted RF v2 model and its selection metadata.
    `validate` expects the frozen 20-signal shortlist and processed light curves.
    Run workflows in order unless you are deliberately inspecting an existing
    evidence record.

## 5. Inspect results before interpreting them

Start with these versioned records:

- [complete research report](https://github.com/Science-Experimental-Technologies/Exoplanet-Search/blob/main/reports/research_report.md);
- [model qualification](https://github.com/Science-Experimental-Technologies/Exoplanet-Search/blob/main/reports/model_qualification.md);
- [candidate screening](https://github.com/Science-Experimental-Technologies/Exoplanet-Search/blob/main/reports/candidate_screening.md); and
- [independent validation](https://github.com/Science-Experimental-Technologies/Exoplanet-Search/blob/main/reports/independent_validation.md).

Then read [Interpreting results](../guides/interpreting-results.md). A high RF
score or catalog absence is not a discovery claim.
