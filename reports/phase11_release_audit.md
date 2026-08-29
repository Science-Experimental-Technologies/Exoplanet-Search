# SXS Phase 11 Public-Release Audit

Audit date: 2026-08-29

Target repository: https://github.com/Science-Experimental-Technologies/Exoplanet-Search

Scope: packaging, documentation, repository hygiene, and reproducibility verification only. No scientific algorithm, metric, candidate category, or source-data result was changed in Phase 11.

## Executive status

**Technical release readiness: PASS.** The candidate public tree passes every automated and manual audit item below. No commit, new tag, push, or GitHub Release was created automatically. GitHub metadata, commit, public tag, and push remain deliberate human actions.

## Audit checklist

| Item | Status | Evidence |
|---|:---:|---|
| Local absolute-path scan | PASS | Recursive text scan found 0 occurrences of the workspace root in slash or backslash form and 0 occurrences of the local user-profile root. Binary artifacts and virtual environments were excluded from text interpretation. |
| Credential scan, candidate tree | PASS | Scan found 0 GitHub tokens, OpenAI-style keys, AWS access-key IDs, Google API keys, private-key headers, or quoted secret assignments. |
| Credential scan, Git history | PASS | `git log --all -p --no-ext-diff` produced 0 matches for the same high-confidence secret patterns. |
| `.gitignore` review | PASS | `.venv`, Python caches, `.env*`, private-key files, raw mission products, Phase 9 caches, fitted model binaries, logs, and build outputs are excluded. Required YAML configs, compact catalog Parquet files, reports, and reproducibility artifacts remain visible. |
| Required-file visibility | PASS | All four `configs/*.yaml` files, the two compact `data/catalog/*.parquet` snapshots, `reports/research_report.md`, and `reports/rnaas_draft.md` passed explicit `git check-ignore` visibility checks. |
| Repository size | PASS | Final candidate tree contains 174 files totaling 24.09 MiB. The largest file is `data/phase8/catalog/eligible_unknown_pool.parquet` at 9.99 MiB. No tracked FITS file or fitted `.joblib`/`.keras` model was found. Git LFS is not required for this release. |
| Internal links | PASS | Final automated validation resolved 39 relative Markdown links across 25 Markdown files with 0 broken targets. A new link pass is required after any manual edits. |
| README scientific consistency | PASS | README values match `reports/research_report.md` and `reports/phase9_independent_validation.md`: v1 BLS 15/36 (41.67%), v1 RF end-to-end 12/36 (33.33%), v2 BLS 227/434 (52.30%), RF v2 precision/recall 0.412/0.903, 250 searched targets, and Phase 9 outcome 0 strong/1 weak/19 likely FP. RF v2 FPR 0.146 is explicitly identified as derived from 292/2,000 out-of-fold negative peaks. |
| Fresh-clone full installation | PASS | A separate clone was created in the operating-system temporary directory. Because Phase 11 forbids committing, the final candidate files were overlaid into that fresh clone before testing. A new Python 3.11.9 virtual environment installed `requirements.txt`; an interrupted first pip extraction was retried from cache and completed successfully. `pip check` reported no broken requirements. |
| Fresh-clone package imports | PASS | NumPy, pandas, Astropy, Astroquery, Lightkurve, `batman`, scikit-learn, TensorFlow, and MLflow imported successfully in the new environment. |
| Fresh-clone CLI dry-run | PASS | `python -m src.pipeline --config configs/base.yaml --dry-run` returned status `dry_run` and the expected Phase 0–5 plan. |
| Fresh-clone test suite | PASS | 35 tests passed, 1 opt-in MAST network test was skipped, and 0 tests failed in 19.18 seconds. The 15 warnings were upstream Matplotlib pyparsing deprecations and Lightkurve's optional `oktopus` notice. |
| Discovery-claim review | PASS | README and disclaimer state prominently that SXS reports no confirmed discovery and that KIC 8300900-r1 remains weak and unconfirmed. |
| Public version metadata | PASS | `pyproject.toml` and `CITATION.cff` use public version `1.0.0`. The changelog records internal SXS v1 and v2 as development stages inside the first public release. The existing local `v2.0.0` tag remains an internal milestone. |
| Git remote destination | PASS | Local `origin` is configured as `https://github.com/Science-Experimental-Technologies/Exoplanet-Search.git`. A read-only `git ls-remote origin` check succeeded and returned no refs, consistent with an accessible empty destination repository. No network push was performed. |
| Identity and funding metadata | PASS | Author Rasya Andrean, affiliation Science Experimental Technologies, and independent funding by Rasya Andrean and Urus Foundation were supplied by RA and checked against the provided public profiles. The public portfolio contact is used for repository policies. |

## Large-file decision

The 9.99 MiB eligible-target snapshot is retained in ordinary Git because it is the deterministic Phase 8 sampling frame and materially supports reproducibility. All other public candidate files are below 1 MiB. Raw FITS products and fitted models are reproducible but storage-heavy and remain intentionally excluded. This release does not need Git LFS.

## GitHub metadata recommendation

### About description

> Reproducible Python pipeline for Kepler transit recovery, ML candidate ranking, and independent vetting; no planet-discovery claim.

### Recommended topics

`astronomy`, `astrophysics`, `exoplanet`, `kepler`, `tess`, `machine-learning`, `time-series`, `transit-search`, `computational-astronomy`, `reproducible-research`, `python`, `box-least-squares`

### Release recommendation

After final human review:

1. Review the author, affiliation, funding, and public contact metadata one final time.
2. Commit the Phase 11 candidate tree on the intended public default branch.
3. Create an annotated `v1.0.0` tag on that reviewed commit.
4. Push the branch and **only** the `v1.0.0` public tag to the target repository; do not use a blanket `git push --tags` if the internal `v2.0.0` tag should remain local-only.
5. Create a formal GitHub Release for `v1.0.0` using the matching `CHANGELOG.md` entry as release notes.
6. Fill the About description and topics above, enable private vulnerability reporting, and consider branch protection plus CI in a later documentation-only change.

The existing local `v2.0.0` tag should not be deleted, moved, or advertised as the first public GitHub Release.

## Identity and funding record

- Author: Rasya Andrean — https://www.rasyaandrean.my.id/
- Affiliation: Science Experimental Technologies — https://github.com/Science-Experimental-Technologies
- Independent funding: Rasya Andrean and Urus Foundation.
- Public contact: `rasyaandrean@outlook.co.id`.

No identity or contact field remains unresolved in the public candidate tree.

## Final publication gate

Automated audit: **PASS**

Human identity/contact review: **SUPPLIED BY RA; FINAL VISUAL REVIEW RECOMMENDED**

Commit/tag/push/GitHub Release: **NOT PERFORMED BY PHASE 11**
