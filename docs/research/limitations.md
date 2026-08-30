# Limitations

## Selection and coverage

- The baseline and scaled benchmarks are quality-filtered validation samples,
  not population-representative surveys.
- The bounded search covers 250 deterministically selected targets from a pool
  of 100,347 and cannot support occurrence-rate inference.
- Scale-up and candidate search use four Kepler products per target even where
  more products exist.
- The fixed BLS domain excludes periods outside 0.5–50 days and durations
  outside the configured grid.

## Detection and preprocessing

- Savitzky-Golay detrending can attenuate or reshape signals when assumptions
  about variability and duration are violated.
- BLS favors periodic box-like events and is less suitable for strong transit
  timing variations or non-box-like signals.
- Gaps, edge effects, residual systematics, stellar activity, dilution, and
  harmonics can create or suppress peaks.

## Machine learning

- RF/CNN metrics describe the constructed candidate-level benchmark, not all
  Kepler light curves.
- The RF threshold was selected for manual-review recall and is not Bayesian
  calibration.
- Model scores reflect similarity to the training construction and must not be
  read as `P(planet | data)`.
- The CNN result is a compact research baseline, not an exhaustive architecture
  or hyperparameter search.

## Independent validation

- Segment circular shifts do not reproduce every instrument systematic,
  stellar process, or contaminating blend.
- Empirical FAP is conditional on preprocessing, sampling, null construction,
  BLS grid, and finite draws. It is not a VESPA-style astrophysical
  false-positive probability.
- At 1,000 shuffles, the minimum reportable plus-one FAP is `1/1,001`.
- Missing external evidence is not positive evidence. A non-match in TESS,
  Gaia, or ExoFOP can reflect coverage, sensitivity, cadence, or catalog timing.
- No new spectroscopy, high-resolution imaging, or pixel-level physical
  follow-up was performed.

## Software and operational constraints

- Public archive availability and schemas can change after the frozen record.
- Full runs are storage-, network-, and compute-intensive.
- Windows has the strongest complete-workstation validation; hosted CI covers
  the deterministic core on Ubuntu rather than full TensorFlow/MLflow training.

These constraints are part of the result. They should remain visible in any
publication, redistribution, competition entry, or downstream project using
SXS outputs.
