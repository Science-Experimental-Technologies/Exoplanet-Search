# Contributing to SXS

Thank you for helping improve SXS. Contributions may address software reliability, documentation, reproducibility, or clearly scoped astronomy-methodology questions. By participating, you agree to follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Development setup

Fork and clone the repository, then create an isolated Python environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Linux or macOS, activate with `source .venv/bin/activate`. Use `requirements-core.txt` when working only on acquisition, preprocessing, or BLS components; use the full requirements for ML and complete test coverage.

GitHub Actions installs only `requirements-core.txt` and runs the deterministic non-network suite on Ubuntu with Python 3.11 and 3.12. Contributors changing Random Forest, CNN, TensorFlow, MLflow, or full-pipeline behavior must additionally install `requirements.txt` and run the relevant full-stack checks locally before opening a pull request. Windows validation remains manual/local rather than a hosted CI claim.

## Tests and style

Run the deterministic suite before opening a pull request:

```powershell
python -m pytest
python -m src.pipeline --config configs/base.yaml --dry-run
```

The live MAST test is opt-in and should be run when changing network acquisition:

```powershell
$env:SXS_RUN_NETWORK_TESTS = "1"
python -m pytest -m network tests/test_mast_client_network.py
```

The repository does not currently enforce a separate formatter or linter in CI. Match the existing Python style: four-space indentation, descriptive names, type hints where they clarify interfaces, small testable functions, and docstrings for public or scientifically non-obvious behavior. Avoid unrelated formatting churn.

## Issues

- Use the bug template for reproducible software or data-processing failures.
- Use the feature/research template for methodology proposals.
- Search existing issues first.
- Do not post credentials, unpublished private data, or sensitive vulnerability details in a public issue; follow [SECURITY.md](SECURITY.md).

## Pull requests

1. Create a focused branch from the current default branch.
2. Add or update tests for behavioral changes.
3. Update configuration, reports, and documentation affected by the change.
4. Run the deterministic test suite and record the result in the PR.
5. Explain scientific assumptions, data provenance, and expected metric changes.

Changes to datasets, labels, thresholds, model selection, validation rules, or reported scientific results require methodological justification. Do not tune against the candidate shortlist merely to improve a headline metric. Such changes must document leakage controls, regenerate the relevant machine-readable artifacts, update the corresponding phase report, and preserve earlier results for comparison.

Raw mission products, credentials, fitted model binaries, and local caches must not be committed. If a new reproducibility artifact is too large for ordinary Git, discuss a durable archive or Git LFS strategy before opening the PR.

## Review expectations

Maintainers may request smaller scope, additional tests, a provenance record, or independent reproduction. A scientifically plausible idea is not automatically suitable for the current release; reproducibility and claim discipline take priority.
