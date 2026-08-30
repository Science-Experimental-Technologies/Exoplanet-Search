# Changelog

All notable changes to this project are documented in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the public release uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Content-verified legacy-workflow resume, content-addressed FAP caches, and
  isolated `--workspace` execution with explicit legacy-cache migration.
- Offline `demo`, single-file/KIC `analyze`, and script-free HTML `report` commands.
- Physical flux-level `inject` experiments with ephemeris recovery criteria and
  uninjected controls; results remain separate from archived benchmarks.
- Nested target-grouped RF `evaluate` command with inner-only model/threshold
  selection, outer predictions, split audits, and target-bootstrap intervals.
- Material for MkDocs documentation covering installation, scientific methods,
  research results, workflows, configuration, artifacts, and project governance.
- Strict documentation builds on pull requests and GitHub Pages deployment from
  the default branch.

### Corrected

- Fixed wheel package discovery so the installed CLI can import `src.cli`.
- Generated baseline benchmark prose now uses the supplied metrics rather than
  hard-coded historical percentages. Frozen validation inputs reject changed
  values even when candidate identifiers are unchanged.
- Translated the project walkthrough into English, clarified archived publication
  status, corrected effective BLS durations, and aligned RNAAS draft structure
  with the current journal instructions.
- Corrected citation metadata and added documentation and wheel regression checks.
- README module paths now match the implementation. Documentation distinguishes
  configured BLS durations from effective search durations and records fixed
  artifact paths and null-cache reuse limitations.

## [1.1.0] - 2026-08-29

### Added

- GitHub Actions CI for the core deterministic test suite on Ubuntu with Python 3.11 and 3.12.
- Release, repository-metadata, and Zenodo DOI guidance.
- Mermaid overview of the end-to-end SXS methodology.
- Minimal SXS corporate wordmark banner for the repository landing page.
- Unified product-oriented command interface for baseline, scale-up, search, and validation workflows.
- Commercial-use guide and formal creator/funding notice.
- Platform-labelled release bundles for Windows, macOS, and Linux, including
  SHA-256 checksums and platform-specific installation instructions.
- Automated GitHub Release publication for version tags.

### Changed

- Reframed public documentation and report names around scientific responsibilities instead of numbered development milestones.
- Replaced the MIT license on the current branch with the SXS Source-Available Commercial License 1.0, including mandatory attribution and a 10% Covered Revenue royalty for commercial use. Previously granted MIT rights for copies of `v1.0.0` remain unaffected.

## [1.0.0] - 2026-08-29

### Added

- Reproducible Kepler light-curve acquisition, preprocessing, Box Least Squares transit recovery, candidate-level feature construction, and catalog validation.
- Target-grouped Random Forest and compact one-dimensional CNN benchmark evaluations.
- Scaled benchmark of 371 confirmed hosts, 434 eligible planets, and 400 official false-positive targets.
- Frozen RF v2 selection policy and exploratory manual-review threshold.
- Deterministic search of 250 targets without cumulative-KOI or confirmed-Kepler-name history.
- Independent validation using empirical shuffle FAP, odd/even and secondary tests, limb-darkened transit fitting, Gaia DR3 scene checks, TESS photometry, and an ExoFOP-derived TOI lookup.
- Full research report, RNAAS-length manuscript draft, verified preprint PDF, citation metadata, contribution guidance, security policy, code of conduct, and scientific disclaimer.

### Scientific result

- The initial benchmark records BLS top-five recovery of 15/36 (41.67%) and RF end-to-end recovery of 12/36 (33.33%).
- The scaled benchmark records BLS top-five recovery of 227/434 (52.30%).
- Independent validation assigns 0 strong candidates, 1 weak candidate, and 19 likely false positives.
- KIC 8300900-r1 is the sole weak signal, with period 5.090289 days and empirical FAP 0.01998. It is not a confirmed exoplanet.
- No discovery claim is made.

### Development history

- The baseline program established the 20-system recovery workflow, target-grouped ML evaluation, and catalog cross-checking.
- The scale-up program expanded the labeled data, froze model selection, conducted the bounded candidate search, completed independent validation, and prepared publication artifacts.
- Public version numbering begins with the `1.0.0` release.

[Unreleased]: https://github.com/Science-Experimental-Technologies/Exoplanet-Search/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/Science-Experimental-Technologies/Exoplanet-Search/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Science-Experimental-Technologies/Exoplanet-Search/releases/tag/v1.0.0
