# Algorithms

## Segment-aware preprocessing

Kepler products are cleaned independently before concatenation. Quality masks
remove flagged cadences, asymmetric sigma clipping removes large excursions,
and small gaps may be linearly interpolated. Interpolated rows remain marked so
they can be excluded from scientific statistics. Segment normalization avoids
treating quarter-to-quarter offsets as astrophysical variability.

The iterative Savitzky-Golay trend uses an odd window and polynomial order 2.
Transit-like negative excursions are masked during iterations so the trend is
less likely to fit through them.

## Box Least Squares

BLS evaluates a periodic box model over period and duration grids. SXS records
period, epoch, duration, depth, depth uncertainty, S/N, power, and supporting
counts. Distinct-peak selection prevents densely neighboring grid points from
occupying all five proposal slots.

Exact recovery uses fractional period error:

```text
abs(P_BLS - P_catalog) / P_catalog <= 0.01
```

Harmonic matches are useful diagnostics but do not replace the reported exact
recovery metric.

## Feature Random Forest

The feature model uses 13 values derived from BLS and the phase-folded light
curve. A Random Forest captures nonlinear interactions such as short duty cycle
with high S/N or secondary evidence with odd/even mismatch. Class balancing and
fixed hyperparameters are set in YAML.

The scale-up RF uses 600 trees, maximum depth 10, minimum leaf size 2, and
balanced class weights. Its output is a ranking score. The selected threshold
`0.221107` satisfies the review-recall constraint in grouped out-of-fold data.

## Compact 1D CNN

The CNN receives a 512-bin phase-folded global view. Missing bins are filled by
interpolation after requiring at least two populated bins; the view is centered
by its median and scaled by robust scatter. It remains a benchmark/diagnostic
because it did not pass the replacement policy.

## Empirical false-alarm probability

Within each observed segment, flux is circularly shifted by a random nontrivial
offset while time sampling and gaps are preserved. A complete BLS search is run
for each shuffled target, and the maximum null power is saved. The plus-one
estimator avoids reporting zero probability from a finite simulation:

```text
estimated FAP = (1 + count(null_max_power >= observed_power)) / (N + 1)
```

This quantifies how unusual the observed power is under the chosen null. It
does not model every astrophysical false-positive scenario.

## Photometric and physical checks

- **Odd/even:** compares alternating transit depths for binary-like behavior.
- **Secondary:** tests phase 0.5 for a significant companion eclipse.
- **Transit shape:** fits a limb-darkened `batman` model and distinguishes
  U-shaped from V/grazing solutions.
- **Physical radius:** combines fitted radius ratio with stellar radius and
  rejects companions above the configured plausibility limit.
- **Scene/external checks:** look for nearby Gaia sources, matching TESS
  periodicity, and public TOI history.

Final categories are rule-based and transparent rather than learned.
