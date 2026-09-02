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

On Linux or macOS, create the environment with `python3.11 -m venv .venv` and activate with `source .venv/bin/activate`. The non-network test suite runs with `requirements-core.txt`; full training and TensorFlow/MLflow checks require `requirements.txt`. Install `requirements-docs.txt` as well for documentation builds.

The CI workflow installs `requirements-core.txt` and runs the non-network suite
and installed-wheel checks on Ubuntu, Windows, and macOS with Python 3.11 and
3.12. A separate Linux-container workflow checks the full environment, imports
TensorFlow/MLflow, and runs the non-network tests; it does not rerun the full
research experiment. Contributors changing training or full-pipeline behavior
must also run the relevant full-stack checks. The complete workstation research
run was validated on Windows; hosted Windows CI covers the deterministic core,
not the full research reproduction.

## Tests and style

Run the deterministic suite before opening a pull request:

```powershell
python -m pytest -m "not network"
python -m src.cli baseline --config configs/base.yaml --dry-run
python scripts/check_repository_docs.py
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

Changes to datasets, labels, thresholds, model selection, validation rules, or reported scientific results require methodological justification. Do not tune against the candidate shortlist merely to improve a headline metric. Such changes must document leakage controls, regenerate the relevant machine-readable artifacts, update the corresponding scientific report, and preserve earlier results for comparison.

Raw mission products, credentials, fitted model binaries, and local caches must not be committed. If a new reproducibility artifact is too large for ordinary Git, discuss a durable archive or Git LFS strategy before opening the PR.

## Review expectations

Maintainers may request smaller scope, additional tests, a provenance record, or independent reproduction. A scientifically plausible idea is not automatically suitable for the current release; reproducibility and claim discipline take priority.

## Contribution and licensing terms

SXS is source-available, not open source. By intentionally submitting a patch, pull request, or other contribution to an official SXS repository, you confirm that you have the right to submit it and agree to the contribution grant in section 6 of [LICENSE](LICENSE). You retain copyright in your original contribution and receive credit through repository history and release records.

Contributions do not remove or replace the required attribution to Rasya Andrean and Science Experimental Technologies. Commercial use of SXS, modified versions, or materially enabled outputs remains subject to the commercial terms and 10% royalty unless a separately signed agreement applies. Review [COMMERCIAL_USE.md](COMMERCIAL_USE.md) before building a commercial product or service.
