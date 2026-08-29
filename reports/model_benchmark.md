# Machine-Learning Model Benchmark

## Result

The evaluation contains **115 BLS candidates from 34 independent target groups**: 15 recovered confirmed-planet candidates and 100 candidates from official Kepler false-positive systems.

| Model | Precision | Recall | F1 | ROC-AUC | Average precision |
|---|---:|---:|---:|---:|---:|
| BLS pass-through | 0.130 | 1.000 | 0.231 | — | 0.130 |
| random_forest | 0.632 | 0.800 | 0.706 | 0.887 | 0.817 |
| cnn_1d | 0.258 | 0.533 | 0.348 | 0.791 | 0.443 |

All model figures are out-of-fold predictions at a fixed 0.5 threshold. Five-fold `StratifiedGroupKFold` keeps every target entirely within one fold; candidates from the same star never appear in both training and evaluation.

## Inputs and labels

The feature model uses BLS period, depth, duration, power and S/N plus duty cycle, robust scatter, odd/even depth mismatch, a phase-0.5 secondary-eclipse check, transit count, and in-transit point count. The CNN uses a robustly normalized 512-bin global folded view.

Positive labels are restricted to exact ±1% transit-recovery matches. Official `FALSE POSITIVE` rows come from the Kepler cumulative KOI table and are balanced across not-transit, stellar-eclipse, centroid-offset, and ephemeris-contamination flags. Unmatched peaks on known planet hosts are excluded instead of being assumed negative.

## Interpretation and limitations

This is a small candidate-level benchmark, not evidence that either model generalizes to an unconstrained survey. The negative systems use four cached Kepler quarters per target while most positive hosts use all available quarters; quarter coverage may therefore be a nuisance variable despite robust normalization. Hyperparameters and the 0.5 threshold were fixed before evaluation, but the same folds serve as validation for CNN early stopping, so reported results should be treated as preliminary.

The end-to-end detector recall remains 15/36 (41.67%) within 0.5–50 days. The ML metrics above measure vetting only among the candidate set and do not replace that detection recall.
