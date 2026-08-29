# Phase 8 — Candidate search on unclassified Kepler targets

## Status and interpretation boundary

Every output is labeled **`unvalidated_candidate_requires_independent_confirmation`**. RF scores rank targets for manual review; they are not calibrated posterior probabilities or independent astrophysical confirmation.

## Target pool

The official not-categorized, magnitude-limited population contained 118,773 targets before the quarter requirement and 100,347 after requiring at least 8 quarters and excluding every KIC present in cumulative KOI or confirmed Kepler-name tables.
A deterministic SHA-256 sample of 250 targets was processed as an explicit workstation constraint. Selection used only seed and KIC, never light-curve signal or model score.

## Pipeline counts

- Configured targets: 250
- Available / skipped: 250 / 0
- Top-five BLS candidates: 1250
- RF threshold passes: 151
- RF plus no failed preliminary sanity check: 110
- Final manual-review shortlist: 20

The accepted Phase 7 RF threshold is used unchanged. Odd/even mismatch, phase-0.5 secondary depth, and moment-centroid shifts are preliminary filters. A centroid marked `unavailable` is retained with that caveat; it is not treated as a pass measurement.

A post-ranking TAP recheck of the 14 unique shortlist KIC targets returned zero cumulative-KOI rows, zero confirmed Kepler-name rows, and `object_status=0` for every target. The structured result is stored in [`phase8_catalog_recheck.json`](phase8_catalog_recheck.json); this confirms catalog status only.

## Ranked shortlist

| Rank | Candidate | Period (d) | RF score | Odd/even | Secondary | Centroid | Shift significance | Figure | Status |
|---:|---|---:|---:|---|---|---|---:|---|---|
| 1 | 3655287-r1 | 18.478278 | 0.909 | pass | pass | pass | 0.14σ | [folded view](phase8_candidates/rank_01_3655287-r1.png) | `unvalidated_candidate_requires_independent_confirmation` |
| 2 | 3655287-r5 | 22.170294 | 0.903 | pass | pass | pass | 0.15σ | [folded view](phase8_candidates/rank_02_3655287-r5.png) | `unvalidated_candidate_requires_independent_confirmation` |
| 3 | 6268872-r3 | 7.764579 | 0.900 | pass | pass | pass | 0.07σ | [folded view](phase8_candidates/rank_03_6268872-r3.png) | `unvalidated_candidate_requires_independent_confirmation` |
| 4 | 1027740-r4 | 12.035808 | 0.900 | pass | pass | pass | 0.04σ | [folded view](phase8_candidates/rank_04_1027740-r4.png) | `unvalidated_candidate_requires_independent_confirmation` |
| 5 | 8300900-r1 | 5.090289 | 0.892 | pass | pass | pass | 0.00σ | [folded view](phase8_candidates/rank_05_8300900-r1.png) | `unvalidated_candidate_requires_independent_confirmation` |
| 6 | 10124049-r2 | 15.285027 | 0.891 | pass | pass | pass | 0.16σ | [folded view](phase8_candidates/rank_06_10124049-r2.png) | `unvalidated_candidate_requires_independent_confirmation` |
| 7 | 8159207-r3 | 15.083637 | 0.890 | pass | pass | pass | 0.01σ | [folded view](phase8_candidates/rank_07_8159207-r3.png) | `unvalidated_candidate_requires_independent_confirmation` |
| 8 | 8300900-r5 | 5.506531 | 0.889 | pass | pass | pass | 0.00σ | [folded view](phase8_candidates/rank_08_8300900-r5.png) | `unvalidated_candidate_requires_independent_confirmation` |
| 9 | 11561399-r3 | 9.877735 | 0.884 | pass | pass | pass | 0.05σ | [folded view](phase8_candidates/rank_09_11561399-r3.png) | `unvalidated_candidate_requires_independent_confirmation` |
| 10 | 8163439-r1 | 14.151354 | 0.881 | pass | pass | pass | 0.00σ | [folded view](phase8_candidates/rank_10_8163439-r1.png) | `unvalidated_candidate_requires_independent_confirmation` |
| 11 | 2011905-r5 | 11.575636 | 0.878 | pass | pass | pass | 0.05σ | [folded view](phase8_candidates/rank_11_2011905-r5.png) | `unvalidated_candidate_requires_independent_confirmation` |
| 12 | 6268872-r5 | 24.246530 | 0.876 | pass | pass | pass | 0.95σ | [folded view](phase8_candidates/rank_12_6268872-r5.png) | `unvalidated_candidate_requires_independent_confirmation` |
| 13 | 8765712-r5 | 21.858360 | 0.859 | pass | pass | pass | 0.05σ | [folded view](phase8_candidates/rank_13_8765712-r5.png) | `unvalidated_candidate_requires_independent_confirmation` |
| 14 | 8163439-r4 | 24.411279 | 0.846 | pass | pass | pass | 0.02σ | [folded view](phase8_candidates/rank_14_8163439-r4.png) | `unvalidated_candidate_requires_independent_confirmation` |
| 15 | 9767793-r3 | 10.283070 | 0.843 | pass | pass | pass | 0.05σ | [folded view](phase8_candidates/rank_15_9767793-r3.png) | `unvalidated_candidate_requires_independent_confirmation` |
| 16 | 9650424-r5 | 3.053610 | 0.832 | pass | pass | pass | 0.01σ | [folded view](phase8_candidates/rank_16_9650424-r5.png) | `unvalidated_candidate_requires_independent_confirmation` |
| 17 | 8300900-r3 | 30.208825 | 0.830 | pass | pass | pass | 0.00σ | [folded view](phase8_candidates/rank_17_8300900-r3.png) | `unvalidated_candidate_requires_independent_confirmation` |
| 18 | 7976673-r2 | 4.979590 | 0.827 | pass | pass | pass | 0.02σ | [folded view](phase8_candidates/rank_18_7976673-r2.png) | `unvalidated_candidate_requires_independent_confirmation` |
| 19 | 4283320-r2 | 11.693914 | 0.804 | pass | pass | pass | 0.20σ | [folded view](phase8_candidates/rank_19_4283320-r2.png) | `unvalidated_candidate_requires_independent_confirmation` |
| 20 | 3655287-r2 | 3.724685 | 0.781 | pass | pass | pass | 0.13σ | [folded view](phase8_candidates/rank_20_3655287-r2.png) | `unvalidated_candidate_requires_independent_confirmation` |

## Sanity-check definitions

- Odd/even: normalized depth mismatch ≤ 0.5.
- Secondary eclipse: absolute secondary/primary depth ratio ≤ 0.2.
- Centroid: robust in/out-of-transit two-axis moment-centroid shift < 3.0σ when FITS centroid columns are available.

These checks do not replace Kepler difference-image analysis, crowding assessment, stellar characterization, ephemeris matching against nearby variables, or external follow-up. The shortlist is solely a prioritized queue requiring independent confirmation.

## Reproducibility

Pool queries, exclusion counts, hashes, processing skips, all 1,250 candidate rows, scores, thresholds, sanity values, and figure paths are stored as versioned Phase 8 artifacts. Phase 7 models were read-only inputs and were not retrained.
