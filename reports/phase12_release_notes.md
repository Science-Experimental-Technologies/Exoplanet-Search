# SXS Phase 12: CI, Release, Metadata, and DOI

Date: 2026-08-29

Repository: https://github.com/Science-Experimental-Technologies/Exoplanet-Search

Scope: infrastructure, release packaging, discoverability metadata, and archival guidance only. Phase 12 does not change any scientific algorithm, metric, candidate classification, or interpretation.

## Status

| Task | Status | Evidence or remaining action |
|---|:---:|---|
| GitHub Actions CI | In progress | `.github/workflows/ci.yml` adds an Ubuntu matrix for Python 3.11 and 3.12, core dependency installation, `pip check`, and non-network tests. A fresh local core-only environment passed 35 tests after `batman-package` was added to the core dependency set. The README badge must wait for the first successful hosted run. |
| GitHub Release `v1.0.0` | Pending execution | The tag is present on the remote. Release creation and PDF upload remain to be completed and verified. |
| Repository About metadata | Pending execution | Final description, topics, and website are specified below. |
| Zenodo DOI | Documented - pending RA account action | GitHub-Zenodo linking requires the repository owner's Zenodo session. No DOI is claimed until Zenodo returns one. |
| README methodology diagram | Done locally | A native Mermaid flowchart complements the existing numbered methodology summary. |

## Continuous integration design

The workflow triggers on pushes to `main` and on pull requests. It uses `ubuntu-latest`, Python 3.11 and 3.12, and `requirements-core.txt`; it deliberately excludes tests marked `network`. The live MAST test remains opt-in through `SXS_RUN_NETWORK_TESTS=1`. `pip check` and any deterministic test failure fail the job.

Local preflight used a new Python 3.11.9 virtual environment containing only `requirements-core.txt`. The first collection exposed that independent-validation tests import `batman`; `batman-package==2.5.3` was therefore moved into the pinned core set rather than skipping scientific tests. The corrected environment reported no broken requirements and passed 35 tests with one network test deselected.

The first hosted matrix run passed on Python 3.11 and exposed a Python 3.12 compatibility requirement: `batman-package==2.5.3` imports `distutils`, which Python 3.12 removed from the standard library. `setuptools==75.8.2` was consequently added to both core and full pinned requirements to provide the compatibility implementation. The CI badge remains withheld until the corrected matrix succeeds.

Hosted CI is not a full-stack ML validation. Changes involving the Random Forest/CNN training paths, TensorFlow, or MLflow must be checked locally using `requirements.txt`. Windows remains manually validated; the workflow makes no Windows CI claim.

## GitHub Release `v1.0.0`

Title:

> SCIX Exoplanet Search (SXS) v1.0.0

Release notes below are reformatted directly from the `[1.0.0]` entry in `CHANGELOG.md`.

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

- **Internal SXS v1, Phases 0-6:** established the 20-system baseline pipeline, target-grouped ML evaluation, and catalog cross-checking.
- **Internal SXS v2, Phases 7-10:** expanded the labeled data, retrained and froze model selection, conducted the bounded candidate search, completed independent validation, and prepared publication artifacts.
- Public version numbering begins with this `1.0.0` release.

Release asset:

- Attach the verified preprint PDF as `sxs_preprint_v1.0.0.pdf`. Its metadata and page header identify public release 1.0.0 while the manuscript explicitly records internal research milestone 2.0.0; all eight rendered pages passed visual inspection.
- For later releases, publish revised PDFs as release assets rather than repeatedly committing generated PDF builds under `output/pdf/`.

## Repository About metadata

Description:

> Reproducible pipeline for Kepler transit detection, ML vetting, and independent validation; zero confirmed discoveries.

Topics, prioritized for discoverability:

`astronomy`, `astrophysics`, `exoplanet`, `exoplanet-detection`, `kepler`, `transit-photometry`, `machine-learning`, `computational-astronomy`, `python`, `open-science`, `reproducible-research`, `nasa-exoplanet-archive`

Website:

https://www.rasyaandrean.my.id/

## Zenodo DOI procedure

Status: **pending RA account action**.

1. Sign in to Zenodo and open https://zenodo.org/account/settings/github/.
2. Connect the GitHub account that administers `Science-Experimental-Technologies/Exoplanet-Search` and enable the repository toggle.
3. If integration is enabled before the GitHub `v1.0.0` release is published, that release can trigger the first archive. If the release already exists first, create a later patch release such as `v1.0.1` after enabling integration; do not delete or retag a published release merely to trigger Zenodo.
4. Wait for Zenodo to finish the deposit, inspect the archived files and metadata, and publish the deposit if Zenodo requires confirmation.
5. Copy the assigned DOI exactly. Add a top-level `doi:` field to `CITATION.cff` and add the Zenodo DOI badge to the README only after the DOI resolves publicly.
6. Commit those two metadata changes in a normal forward commit; do not rewrite release history.

A DOI provides a durable scholarly identifier for the archived release even if the GitHub repository is renamed, transferred, or reorganized. It should be used in the RNAAS/arXiv citation once issued. Until then, the GitHub release and `CITATION.cff` remain the citation sources, and no placeholder DOI or badge should be published.

## Final verification checklist

- Confirm both Python matrix jobs succeed before adding the CI badge.
- Confirm the Release points to tag `v1.0.0` and contains the expected PDF asset.
- Confirm About description, topics, and website are visible publicly.
- Confirm Zenodo integration/DOI status without claiming a DOI prematurely.
- Confirm the final working tree is clean and all Phase 12 changes are forward commits on `main`.
