# Windows verification — 2026-08-31

Tools has work on Windows 11 + Python 3.11.9

- \python -m src.cli baseline --config configs/base.yaml --dry-run\ → dry_run OK
- \python -m pytest -m \"not network\"\ → 65 passed
- \python -m src.cli demo --output runs/demo\ → report.html generated

Verified in D:\rasya\Exoplanet-Search\.venv
