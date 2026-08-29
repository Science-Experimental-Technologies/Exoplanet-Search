# SXS Phase 10 Release Audit

Release: `v2.0.0`

Audit date: 2026-08-28

Scope: publication preparation only; no journal submission, arXiv upload, repository push, or discovery claim

## Publication artifacts

- Self-contained preprint source: `reports/research_report.md`
- Submission-style PDF: `output/pdf/sxs_preprint_v2.0.0.pdf`
- Project summary: `reports/sxs_project_summary.md`
- Citation metadata: `CITATION.cff`
- License: `LICENSE` (MIT)
- Version history: `CHANGELOG.md`
- Reproducible PDF builder: `scripts/build_preprint_pdf.py`

The eight-page A4 PDF was rasterized page by page and visually inspected. The review found no clipped text, overlap, unreadable table content, or missing figure labels. Programmatic checks confirmed eight readable pages, document metadata, and the absence of encryption, interactive forms, and JavaScript.

## Scientific-claim audit

The release preserves the Phase 9 outcome exactly: 0 `strong_candidate`, 1 `weak_candidate`, and 19 `likely_false_positive`. KIC 8300900-r1 is described only as a weak, unconfirmed signal. Neither the preprint nor the release metadata claims a new or confirmed exoplanet.

## Reproducibility and repository hygiene

- Phase 8 selection and Phase 9 validation inputs are frozen in versioned artifacts.
- Raw light curves, caches, fitted model binaries, virtual environments, and temporary PDF rasters are excluded from version control.
- Documentation dependencies are pinned in `requirements-docs.txt`.
- The release tree was scanned for absolute workstation paths and common credential patterns.
- The complete automated test suite passed: 35 tests passed and the single opt-in live-network smoke test was skipped by default.

## Acceptance result

Phase 10 is accepted for the `v2.0.0` release commit and annotated tag. The release is a reproducible negative/ambiguous-result case study and is ready for human review before any external submission.
