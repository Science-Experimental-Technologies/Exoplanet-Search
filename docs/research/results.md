# Results

## Summary

| Evaluation | Precision | Recall | FPR | Recovery / retained positives |
|---|---:|---:|---:|---:|
| Baseline BLS-only proposals | 0.130 | 1.000 | 1.000 | 15/36 (41.67%) |
| Baseline feature RF | 0.632 | 0.800 | 0.070 | 12/36 (33.33%) |
| Scaled BLS top-five search | — | — | — | 227/434 (52.30%) |
| RF v2 review point | 0.412 | 0.903 | 0.146 | 205/227 candidate positives retained |

The RF v2 FPR is derived from 292 false passes among 2,000 negative peaks.
Its threshold is an exploratory manual-review operating point, not a calibrated
planet probability.

The RF v2 denominator of 227 is the BLS-recovered positive candidate set, not
all 434 eligible planets. Candidate-level recall and end-to-end planet recovery
are different metrics and must not be compared as if their denominators match.

## Baseline interpretation

BLS recovers 15 of 36 eligible planets. The feature RF retains 12 of those 15
positive peaks and rejects 93 of 100 negative-system peaks. The improved
candidate purity costs three recovered positive peaks; no downstream ranker can
recover a planet that BLS did not propose.

![Baseline confusion matrices](../reports/confusion_matrices.png){ loading=lazy }

## Scaled recovery and model selection

With matched four-product coverage, BLS recovers 227 of 434 eligible planets
(52.30%). RF v2 reaches precision 0.412 and recall 0.903 at threshold 0.221107.
The CNN reaches recall 0.912 at threshold 0.394803 but precision 0.198 and
fold-F1 standard deviation 0.166, so it remains secondary under the frozen
selection policy.

## Candidate search

The 250-target search produces 1,250 peaks and a 20-signal queue. A live
post-ranking catalog recheck finds no cumulative KOI row and no confirmed
Kepler name for the 14 unique KICs at that time. That absence is a selection
fact only; it does not demonstrate novelty.

## Independent validation outcome

| Category | Count |
|---|---:|
| Strong candidate | 0 |
| Weak candidate | 1 |
| Likely false positive | 19 |

The best FAP belongs to `KIC 8300900-r1`:

- period: 5.090289 days;
- 19 of 1,000 null maxima equal or exceed observed power;
- plus-one FAP: `20/1,001 = 0.01998`;
- transit fit: U-shaped;
- physical-size plausibility: pass;
- Gaia evidence: available;
- TESS period support: none; and
- public ExoFOP/TOI record: no matching public record at audit time.

Because FAP is above the 1% strong threshold and TESS support is absent, the
signal is `weak_candidate`, not a confirmed exoplanet. The second-best FAP is
0.05594, already above the key-failure boundary.

![Folded view of KIC 8300900-r1](../reports/candidate_figures/rank_05_8300900-r1.png){ loading=lazy }

## Primary conclusion

SXS demonstrates a complete, auditable computational workflow and records a
negative candidate-search result honestly. The scientific contribution is the
reproducible recovery, ranking, and independent-vetting methodology—not a new
planet claim.
