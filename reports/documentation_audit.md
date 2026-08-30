# Documentation and Consistency Audit

Date: 2026-08-30. Scope: the current working tree based on commit `4b7e969`.
This report records an editorial and software audit, not a new scientific run.

## Scope and language inventory

The review covered repository Markdown, README and contributor instructions,
the MkDocs website, citation and package metadata, workflow definitions, report
generators, and the archived research PDF. The local `walkthrough.md` was
already present but untracked when the audit began; it is included in the review.

- `walkthrough.md` was the non-English prose document found. It is now in English.
- Tracked Markdown prose was already predominantly English; misleading terms,
  grammar, stale operational claims, and conflicting instructions were corrected.
- The eight-page archived PDF is in English. It remains unchanged, with known
  corrections listed in [Publication status](../docs/project/publication.md).
- Indonesian words remain intentionally in the language-checker's vocabulary
  and regression fixtures. They are not untranslated user documentation.

The automated language check is a targeted Indonesian heuristic, not a complete
language detector or proof of grammatical correctness. Scientific identifiers,
proper names, historical schema keys, and publication titles are preserved.

## Findings and corrections

| Finding | Correction |
|---|---|
| Historical milestones, research generations, and release numbers were conflated | Distinguished baseline/scaled research from software v1.0.0/v1.1.0 and labelled historical audits |
| Reports said BLS searched through 12 hours | Documented the effective 1, 2, 4, 8-hour grid; configured 12 hours is filtered out |
| 20,000 candidate FAP rows could imply independent simulations | Explained reuse of 14 target-level distributions with 1,000 realizations each |
| Broad confirmation wording could include known benchmark planets | Restricted the no-discovery statement to the new-search shortlist; labelled TESS period support |
| Old RNAAS preparation instructions omitted an abstract | Corrected the draft using the current official instructions; retained one table |
| Archived PDF and validation flag suggested submission readiness | Added archival corrections and explained that artifact checks do not establish journal readiness |
| CFF custom license value failed the schema's SPDX enum | Used `license-url`; separated the software citation from the archived report reference |
| Wheel omitted `src.cli` despite its console entry point | Fixed explicit package discovery and added an isolated wheel CLI check |
| Benchmark generator embedded historical percentages | Generated counts, denominators, percentages, period domain, and tolerance from supplied metrics |
| Frozen input check compared candidate IDs only | Compare all fields, allowing numerical serialization tolerance and two documented editorial aliases |
| First-run instructions used existence-based resume | Changed first-run examples and explained artifact compatibility and separate checkouts |
| Custom log path appeared to isolate a run | Documented fixed shared outputs and latest-run records |
| Download instructions implied bundled fitted models | Clarified that current release bundles and container omit fitted model binaries |
| Container publication implied anonymous availability | Recorded that package visibility still requires owner attention |

## Verification

- Non-network tests: **48 passed, 1 network test deselected** on Windows,
  Python 3.11.9. Third-party deprecation/optional-module warnings remain.
- MkDocs strict build passed; generated-site checker found **0 broken references**
  across **30 HTML pages and 2,312 local references**.
- Repository Markdown checker passed **57 documents with 0 findings** and
  includes local file links, repeated headings,
  a language heuristic, and draft length. External URLs are not exhaustively checked.
- Recorded CLI previews match current help/dry-run output. `pip check` passed.
- A wheel built from a clean temporary source tree passed layout validation and
  CLI help execution outside the checkout. No wheel was published.
- `CITATION.cff` passed the official CFF 1.2.0 JSON Schema, including formats.
  The YAML date was serialized to its ISO string for JSON validation.
- The existing 20-row frozen shortlist passed the strengthened input comparison
  without modifying its bytes; changed scientific values are regression-tested.
- RNAAS conservative counts: **116 abstract words, 650 body words, 857 total
  whitespace tokens**, including table syntax in the total. See the
  [numerical consistency record](rnaas_draft_consistency_check.md).

Primary format references: [RNAAS preparation guidelines](https://journals.aas.org/research-note-preparation-guidelines/),
[CFF 1.2.0 schema](https://raw.githubusercontent.com/citation-file-format/citation-file-format/1.2.0/schema.json),
and [Zenodo release archiving](https://help.zenodo.org/docs/github/archive-software/github-upload/).

## Scientific and archival integrity

No tracked data, model artifacts, configuration values, figures, numeric result
files, or archived PDF changed relative to the starting commit. The result
remains 0 strong candidates, 1 weak candidate, and 19 likely false positives.
KIC 8300900-r1 remains unconfirmed, with empirical FAP 0.01998.

SHA-256 checkpoints:

| Artifact | SHA-256 |
|---|---|
| `data/validation/frozen_search_shortlist.parquet` | `68a736fed9172d1c104689d87b9b11d57731371b3a48080700d919e59f97033b` |
| `output/pdf/sxs_preprint_v1.0.0.pdf` | `d8145e015d2de602e279863248cf1b1052141b21ff2bb6c9b3ea5279d8bc9db4` |
| `reports/benchmark_metrics.json` | `e249e86cbc9ea5b40f1e982ef0f595abbe2ca071c583d70f05d99923243dca72` |

## Remaining boundaries

- Full mission downloads, RF/CNN retraining, candidate search, and null
  simulations were not rerun. Local tests do not establish cross-platform
  scientific equivalence or replace independent astronomical validation.
- Resume checks and null caches still require compatible inputs/configuration;
  this audit does not redesign cache invalidation. See the configuration guide.
- The archived PDF requires a separately reviewed replacement before reuse as
  a current manuscript. No PDF, DOI, journal submission, or release was created.
- GHCR public visibility and Zenodo integration require an authorized owner.
- The custom license was not substantively altered or legally certified.
- The checks reduce specific documented errors; they are not a guarantee that
  every sentence, external service, or scientific assumption is error-free.

## Repeat the local checks

Install the appropriate scientific and documentation requirements first.

```bash
python -m pytest -m "not network"
python scripts/check_repository_docs.py --extra walkthrough.md --extra docs/project/publication.md --extra reports/documentation_audit.md
python scripts/build_cli_previews.py --check
python -m mkdocs build --strict
python scripts/check_documentation.py --site-dir site
python -m pip check
```

For wheel verification, build in a clean source tree, then run
`python scripts/check_wheel.py dist/wheels`. Stale `build/` contents from an older
package layout can contaminate a local wheel; the checker rejects that layout.
