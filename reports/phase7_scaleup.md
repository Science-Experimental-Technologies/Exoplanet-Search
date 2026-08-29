# Phase 7 — Scale-up and retraining

## Acceptance result

Phase 7 uses **371 confirmed hosts / 434 planets** and **400 balanced official false-positive hosts**, versus 20 + 20 systems in v1. The candidate-level ML dataset contains 2227 rows (227 positive, 2000 negative) across 619 target groups.

The production model selected for Phase 8 is **rf_v2** at threshold **0.221107**. Phase 8 is not executed by this report.

## Selection and resource policy

- Confirmed planets: period 0.5–50 d, transit S/N ≥ 50.0, Kp ≤ 15.0, and ≥ 8 available long-cadence quarters.
- False positives: full in-domain population is archived; the processed set requires S/N ≥ 10.0 and the same magnitude/availability limits, then selects 100 unique targets per flag deterministically.
- Four chronological products per target are processed for both classes. This explicit workstation constraint keeps coverage matched and bounded while retaining a >50 d baseline; it is not a silent reduction.
- Prefetch: 771 available and 0 failed after retries.
- Confirmed preprocessing: 371 available and 0 skipped.
- False-positive processing: 400 available and 0 skipped.

### False-positive flag distribution

Official flags can overlap, so full-population counts do not sum to the number of KOIs. Processing is deliberately balanced at 100 target-unique systems (25%) per assigned category.

| Assigned category | Full FP KOIs carrying flag | Processed unique targets | Processed share |
|---|---:|---:|---:|
| centroid_offset | 1751 | 100 | 25.0% |
| ephemeris_contamination | 1096 | 100 | 25.0% |
| not_transit | 762 | 100 | 25.0% |
| stellar_eclipse | 1962 | 100 | 25.0% |

## BLS scale-up result

With matched four-product coverage, BLS recovered **227/434 (52.30%)** eligible planets in the top five, versus **15/36 (41.67%)** in v1.

## v1 versus v2 out-of-fold metrics at threshold 0.5

| Model | Version | Precision | Recall | F1 | ROC-AUC | Average precision |
|---|---|---:|---:|---:|---:|---:|
| Random Forest | v1 | 0.632 | 0.800 | 0.706 | 0.887 | 0.817 |
| Random Forest | v2 | 0.534 | 0.789 | 0.637 | 0.937 | 0.641 |
| CNN 1D | v1 | 0.258 | 0.533 | 0.348 | 0.791 | 0.443 |
| CNN 1D | v2 | 0.227 | 0.736 | 0.347 | 0.819 | 0.352 |

RF v2 is not uniformly better at the fixed 0.5 cutoff: precision and F1 are lower on the much larger, harder candidate set, recall is broadly stable, and ROC-AUC improves. The scale-up therefore supports model-ranking stability rather than an unqualified improvement claim; RF remains clearly stronger than CNN.

## Manual-review threshold

The operating point is selected from grouped out-of-fold precision–recall predictions by maximizing precision subject to recall ≥0.90. This policy intentionally favors not missing real recovered signals because false alarms will receive manual review. It is an exploratory operating-point estimate on the same OOF predictions, not an independently calibrated probability threshold.

- RF: threshold 0.221107, precision 0.412, recall 0.903.
- CNN: threshold 0.394803, precision 0.198, recall 0.912.
- Complete OOF precision–recall operating points are stored in `reports/experiments/phase7/rf_v2_pr_curve.csv` and `cnn_v2_pr_curve.csv`.

## CNN stability and production decision

CNN fold-F1 standard deviation is 0.166 (stability criterion ≤0.100: not passed). At the common recall floor, CNN must also improve precision over RF by at least 0.020 to become primary. The CNN role is **secondary_diagnostic**; the versioned v1 model remains untouched.

## Limitations

The S/N and magnitude filters deliberately emphasize reliable training signals and therefore do not represent the hardest unknown targets. Four-product coverage is consistent across classes but shorter than full Kepler coverage. KOI flags overlap physically, although selection categories are target-unique. A future nested calibration set is required before treating the threshold as a calibrated posterior probability.
