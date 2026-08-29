# Changelog

All notable changes to this project are documented in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the public release uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- GitHub Actions CI for the core deterministic test suite on Ubuntu with Python 3.11 and 3.12.
- Phase 12 release, repository-metadata, and Zenodo DOI guidance.
- Mermaid overview of the end-to-end SXS methodology.
- Minimal SXS corporate wordmark banner for the repository landing page.

## [1.0.0] - 2026-08-29

### Added

- Reproducible Kepler light-curve acquisition, preprocessing, Box Least Squares transit recovery, candidate-level feature construction, and catalog validation.
- Target-grouped Random Forest and compact one-dimensional CNN benchmark evaluations.
- Phase 7 scale-up to 371 confirmed hosts, 434 eligible planets, and 400 official false-positive targets.
- Frozen RF v2 selection policy and exploratory manual-review threshold.
- Deterministic Phase 8 search of 250 targets without cumulative-KOI or confirmed-Kepler-name history.
- Phase 9 independent validation using empirical shuffle FAP, odd/even and secondary tests, limb-darkened transit fitting, Gaia DR3 scene checks, TESS photometry, and an ExoFOP-derived TOI lookup.
- Full research report, RNAAS-length manuscript draft, verified preprint PDF, citation metadata, contribution guidance, security policy, code of conduct, and scientific disclaimer.

### Scientific result

- The initial benchmark records BLS top-five recovery of 15/36 (41.67%) and RF end-to-end recovery of 12/36 (33.33%).
- The scaled benchmark records BLS top-five recovery of 227/434 (52.30%).
- Independent validation assigns 0 strong candidates, 1 weak candidate, and 19 likely false positives.
- KIC 8300900-r1 is the sole weak signal, with period 5.090289 days and empirical FAP 0.01998. It is not a confirmed exoplanet.
- No discovery claim is made.

### Development history

- **Internal SXS v1, Phases 0–6:** established the 20-system baseline pipeline, target-grouped ML evaluation, and catalog cross-checking.
- **Internal SXS v2, Phases 7–10:** expanded the labeled data, retrained and froze model selection, conducted the bounded candidate search, completed independent validation, and prepared publication artifacts.
- The local `v2.0.0` tag records that internal scale-up milestone. Public version numbering begins with this `1.0.0` release.

[Unreleased]: https://github.com/Science-Experimental-Technologies/Exoplanet-Search/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Science-Experimental-Technologies/Exoplanet-Search/releases/tag/v1.0.0
