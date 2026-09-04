# RNAAS Draft Consistency Check

Checked against:

- `reports/research_report.md`
- `reports/independent_validation.md`
- `reports/experiments/scaleup/rf_v2_cv.json` only for the explicitly identified derived RF v2 FPR

## Editorial checks

- The full research report remains a separate working document; no scientific metrics were changed by condensation or the later editorial audit.
- The draft has a formal abstract, correcting the older no-abstract instruction to match the [official RNAAS guidelines](https://journals.aas.org/research-note-preparation-guidelines/) checked on 2026-08-30.
- It contains one table and no figure.
- The table was selected instead of the KIC 8300900-r1 folded light curve because the manuscript's contribution is pipeline performance and independent-vetting outcome, not a candidate claim.
- Author Rasya Andrean, affiliation Science Experimental Technologies, funding acknowledgment, and repository URL are filled from RA-provided public sources.
- The language states that KIC 8300900-r1 is weak and unconfirmed and makes no discovery claim.

## Numerical cross-check

| Quantity in RNAAS draft | Value in draft | Source and matching value | Result |
|---|---:|---|---|
| v1 eligible planets | 36 | `research_report.md`: 36 | Match |
| v1 BLS recovery | 15/36 (41.67%) | `research_report.md`: 15/36 (41.67%) | Match |
| v1 RF end-to-end recovery | 12/36 (33.33%) | `research_report.md`: 12/36 (33.33%) | Match |
| v1 BLS precision / recall / FPR | 0.130 / 1.000 / 1.000 | `research_report.md`, Results table: same | Match |
| v1 RF precision / recall / FPR | 0.632 / 0.800 / 0.070 | `research_report.md`, Results table: same | Match |
| v2 eligible planets and BLS recovery | 227/434 (52.30%) | `research_report.md`: 227/434 (52.30%) | Match |
| v2 RF review threshold | 0.221107 | `research_report.md`: 0.221107 | Match |
| v2 RF review precision / recall | 0.412 / 0.903 | `research_report.md`: 0.412 / 0.903 | Match |
| v2 RF review FPR | 0.146 | Derived from the frozen out-of-fold artifact: 292 FP / 2,000 negative peaks = 0.146; precision check 205/497 = 0.4124748491 and recall check 205/227 = 0.9030837004 | Derived, exact |
| candidate screening target count | 250 | `research_report.md`: 250 | Match |
| candidate screening BLS peaks / RF passes / sanity passes | 1,250 / 151 / 110 | `research_report.md`: same | Match |
| Frozen shortlist / unique KICs | 20 / 14 | `research_report.md` and `independent_validation.md`: same | Match |
| independent validation null draws | 1,000 per target | Both source reports: 1,000 | Match |
| Strong FAP threshold | 0.01 | Both source reports: 0.01 | Match |
| Final category counts | 0 strong / 1 weak / 19 likely FP | Both source reports: same | Match |
| Weak signal | KIC 8300900-r1 | Both source reports: same | Match |
| Weak-signal period | 5.090289 days | Both source reports: 5.090289 days | Match |
| Weak-signal empirical FAP | 20/1,001 = 0.01998 | `research_report.md`: 20/1,001 = 0.01998; independent validation table rounds to 0.0200 | Match |
| Public TOI matches | 0 among 14 targets | Both source reports: no matched record for 14 targets | Match |
| Kepler products per search target | 4 | Both source reports: four | Match |

## Word-count rule

`python scripts/check_repository_docs.py` counts whitespace-separated tokens conservatively, including Markdown table separators. Abstract count excludes its heading. Body count starts at Data and Methods and includes headings, table cells, acknowledgments, and availability text, but excludes abstract and references. Total count includes the entire file, including title, author/affiliation, abstract, references, and formatting tokens.

Counts after the public software DOI was inserted on 2026-09-04: **116 abstract words; 653 body words; 860 total tokens**. These satisfy the official abstract limit of 150 and total limit of 1,500; the final submission-system count must still be checked. The earlier 741-word count used an older draft and counting convention.

## AASTeX package check

`manuscript/rnaas.tex` was created from this checked Markdown draft on
2026-09-02. Its abstract reproduces the same text counted as 116 words by the
repository's Markdown checker; its single table reproduces every row above;
and the prose retains the same values for the v1
and v2 benchmarks, screening counts, shortlist, FAP threshold, weak signal,
period, FAP, catalog result, and limitations. It adds no candidate or discovery
claim. Its availability statement identifies the public v1.3.0 software DOI;
the bibliography contains only sources named in the manuscript.

The local environment does not provide `texcount` or an AASTeX LaTeX
distribution, so no compiled PDF or publisher-equivalent TeX word count is
claimed. `manuscript/submission-checklist.md` leaves both checks explicitly
open for the submitting author.
