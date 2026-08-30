# Contributing

SXS welcomes focused bug fixes, reproducibility improvements, tests, and
scientifically justified changes.

## Before opening a pull request

1. Read the repository `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, scientific
   disclaimer, and license.
2. Open or reference an issue for changes that alter algorithms, thresholds,
   schemas, or accepted results.
3. Create a focused branch and avoid unrelated formatting changes.
4. Add deterministic tests for behavior changes.
5. Update configs, artifact documentation, and limitations when applicable.
6. Run the required validation commands.

## Local checks

```bash
python -m pip check
python -m pytest -m "not network"
python -m mkdocs build --strict
```

Changes involving TensorFlow, MLflow, full mission acquisition, model training,
or research artifacts require the complete environment and evidence
regeneration beyond hosted core CI.

## Scientific change checklist

- What scientific assumption changes?
- Was it specified before examining final candidates?
- Which artifacts and hashes become invalid?
- Does the change affect comparison with published metrics?
- Are new limitations introduced?
- Does wording remain below the evidence strength?

## Documentation standard

Write task-oriented pages for procedures, concept pages for explanation, and
reference pages for exact options/schemas. Link to the authoritative evidence
rather than copying large generated tables. `mkdocs build --strict` must pass.

## Contribution licensing

Contributors retain copyright in their original contribution and receive
repository-recorded credit. By intentionally submitting to the official
repository, contributors grant the rights described in section 6 of the SXS
license. A contribution does not remove original creator attribution or change
the project license.
