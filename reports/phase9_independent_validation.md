# Phase 9 — Independent validation and statistical vetting

## Scientific boundary and result

The frozen Phase 8 shortlist contains 20 signals on 14 unique Kepler targets. Independent vetting assigns **0 strong**, **1 weak**, and **19 likely false-positive** labels.

None of these labels means a confirmed exoplanet. Every row remains an unconfirmed photometric signal; confirmation requires evidence and/or follow-up outside SXS.

## Why the validation is non-circular

The Phase 7 RF score is retained only as provenance and is not included in the Phase 9 evidence score or decision rules. FAP is computed from BLS peak statistics under shuffled light curves; odd/even and secondary tests use event-level flux measurements; transit morphology comes from a physical limb-darkened model; Gaia tests the sky scene; TESS uses another spacecraft and reduction; and the TOI lookup is a public community-vetting record. None consumes RF probabilities, RF features, CNN output, or training labels.

## Methods

### Empirical BLS FAP

For every candidate, 1,000 null realizations were evaluated over the same 0.5–50 day period grid and duration grid as Phase 8. Each Kepler source-file segment was circularly shifted by an independent random offset, preserving cadence sampling and within-segment correlated structure while breaking a common ephemeris. The test statistic is the maximum BLS power over the full grid, so it includes the period-search look-elsewhere effect. We use the add-one estimator `(exceedances + 1)/(N + 1)`; resolution is 0.000999.

### Formal light-curve tests

Odd and even event depths are measured separately with local baselines and compared with a two-sided Welch t-test (fail at p < 0.01). The phase-0.5 secondary depth is compared with a robust out-of-eclipse scatter estimate; a 3-sigma upper limit is always reported. A secondary is a red flag when it is at least 3 sigma and at least 10% of the primary depth.

A circular-orbit, quadratic-limb-darkened `batman` transit is fitted to the binned folded photometry with period fixed to BLS. The fitted radius ratio, scaled semimajor axis, and impact parameter yield the grazing statistic `b + Rp/R*`; values >= 1 are treated as V-shaped/grazing red flags. Stellar radii from the frozen Phase 8 catalog convert the radius ratio to Earth radii, with >22 R_earth treated as a stellar/substellar-size red flag rather than a planet-like size.

### External cross-matches

Gaia DR3 sources within 30 arcsec are retained. A non-primary Gaia source within 4 arcsec (approximately one Kepler pixel) and no more than 5 G magnitudes fainter is a high-risk contamination flag. TESS light curves are searched by a TIC entry explicitly matching the KIC; up to four products from the highest-priority available pipeline are analyzed with a targeted ±10% BLS search, requiring a best period within 1% and S/N >= 5. The NASA Exoplanet Archive TOI table, which is updated from ExoFOP-TESS, is position-matched within 10 arcsec and its disposition and period match are recorded.

## Transparent evidence score

The score is an audit aid, not a probability: FAP pass/borderline/fail = +3/+1/-3; odd-even = +1/-3; secondary = +1/-3; U/V shape = +2/-3; physical size = +1/-3; clean/high-risk Gaia scene = +1/-3; TESS confirmation/available non-confirmation = +2/-1; ExoFOP period match/FP flag = +1/-3. Unavailable evidence contributes zero. A key failure forces `likely_false_positive`; `strong_candidate` additionally requires all internal tests, clean Gaia, and TESS period confirmation. Other no-key-failure rows are `weak_candidate`.

## Candidate results

| P9 rank | Candidate | P (d) | FAP | Odd/even p | Secondary sig. | Shape | Rp (R_earth) | Gaia risk | TESS | ExoFOP | Score | Category |
|---:|---|---:|---:|---:|---:|---|---:|:---:|:---:|---|---:|---|
| 1 | 8300900-r1 | 5.090289 | 0.0200 | 0.778 | -0.39 | U_shaped | 2.34 | no | available | no_public_record | 6 | `weak_candidate` |
| 2 | 8163439-r1 | 14.151354 | 0.0559 | 0.0937 | 1.29 | U_shaped | 4.91 | no | available | no_public_record | 2 | `likely_false_positive` |
| 3 | 11561399-r3 | 9.877735 | 0.2218 | 0.582 | -0.06 | U_shaped | 1.29 | no | available | no_public_record | 2 | `likely_false_positive` |
| 4 | 1027740-r4 | 12.035808 | 0.3976 | 0.419 | -0.63 | U_shaped | 2.06 | no | available | no_public_record | 2 | `likely_false_positive` |
| 5 | 7976673-r2 | 4.979590 | 0.5215 | 0.132 | 1.13 | U_shaped | 8.51 | no | available | no_public_record | 2 | `likely_false_positive` |
| 6 | 4283320-r2 | 11.693914 | 0.6284 | 0.83 | 2.53 | U_shaped | 0.75 | no | available | no_public_record | 2 | `likely_false_positive` |
| 7 | 2011905-r5 | 11.575636 | 0.6314 | 0.616 | -0.90 | U_shaped | 3.18 | no | available | no_public_record | 2 | `likely_false_positive` |
| 8 | 8300900-r3 | 30.208825 | 0.9530 | 0.613 | -0.79 | U_shaped | 6.03 | no | available | no_public_record | 2 | `likely_false_positive` |
| 9 | 6268872-r3 | 7.764579 | 0.9540 | 0.785 | -0.84 | U_shaped | 0.27 | no | available | no_public_record | 2 | `likely_false_positive` |
| 10 | 8765712-r5 | 21.858360 | 0.9720 | 0.925 | 1.10 | U_shaped | 0.95 | no | available | no_public_record | 2 | `likely_false_positive` |
| 11 | 8163439-r4 | 24.411279 | 0.9740 | 0.765 | -0.89 | U_shaped | 7.68 | no | available | no_public_record | 2 | `likely_false_positive` |
| 12 | 8159207-r3 | 15.083637 | 0.9870 | 0.526 | 0.77 | U_shaped | 2.31 | no | available | no_public_record | 2 | `likely_false_positive` |
| 13 | 8300900-r5 | 5.506531 | 0.9990 | 0.433 | -0.49 | U_shaped | 1.66 | no | available | no_public_record | 2 | `likely_false_positive` |
| 14 | 9650424-r5 | 3.053610 | 1.0000 | 0.658 | -1.10 | U_shaped | 9.23 | no | available | no_public_record | 2 | `likely_false_positive` |
| 15 | 6268872-r5 | 24.246530 | 0.9960 | 0.255 | -0.13 | V_or_grazing | 6.71 | no | confirmed | no_public_record | 0 | `likely_false_positive` |
| 16 | 10124049-r2 | 15.285027 | 0.8621 | 0.654 | 0.58 | unavailable | — | no | available | no_public_record | -1 | `likely_false_positive` |
| 17 | 9767793-r3 | 10.283070 | 0.6034 | 0.419 | 3.05 | U_shaped | 1.14 | no | available | no_public_record | -2 | `likely_false_positive` |
| 18 | 3655287-r1 | 18.478278 | 0.6983 | 0.552 | -0.44 | U_shaped | 1.73 | yes | available | no_public_record | -2 | `likely_false_positive` |
| 19 | 3655287-r2 | 3.724685 | 0.7063 | 0.507 | 0.11 | U_shaped | 0.98 | yes | available | no_public_record | -2 | `likely_false_positive` |
| 20 | 3655287-r5 | 22.170294 | 0.9980 | 0.592 | 0.23 | U_shaped | 1.31 | yes | available | no_public_record | -2 | `likely_false_positive` |

## Phase 10 priority

No signal meets the deliberately strict `strong_candidate` rule; Phase 10 must not imply otherwise.

## Method references

- Thompson et al. (2018), [Kepler DR25 Robovetter catalog](https://arxiv.org/abs/1710.06758), for the independent-vetting context including odd/even, secondary, and centroid diagnostics.
- Kreidberg (2015), [`batman`: BAsic Transit Model cAlculatioN in Python](https://arxiv.org/abs/1507.08285), for the limb-darkened transit model.
- [Astropy periodogram false-alarm documentation](https://docs.astropy.org/en/stable/timeseries/lombscargle.html#peak-significance-and-false-alarm-probabilities), for the interpretation and computational cost of bootstrap peak FAP estimates.
- [MAST TESS archive](https://archive.stsci.edu/missions-and-data/tess), for the independent TESS light-curve products.
- [ESA Gaia Archive documentation](https://gea.esac.esa.int/archive/documentation/), for Gaia DR3 source queries.
- [NASA Exoplanet Archive TOI column documentation](https://exoplanetarchive.ipac.caltech.edu/docs/API_TOI_columns.html), which states that the table is updated from the ExoFOP TOI list.

## Limitations

- Empirical BLS FAP is conditional on this shuffle scheme, time sampling, detrending, and search grid. It is not the posterior probability that a signal is astrophysical and is not a Bayesian astrophysical false-positive probability such as VESPA.
- Only four cached Kepler products per target were used in Phase 8/9, even when more quarters exist. Segment shifts preserve short-timescale correlation but cannot reproduce every instrumental systematic or long-period stellar process.
- The odd/even and secondary tests use simplified robust depth estimators; multiple-testing corrections beyond the BLS maximum statistic are not claimed.
- The `batman` fit fixes circular orbit and approximate quadratic limb darkening. Grazing geometry, dilution, eccentricity, and stellar-parameter uncertainty are degenerate, so fitted radii and densities are screening quantities, not characterization measurements.
- Gaia proximity indicates contamination risk, not proof that a neighbor caused the signal. Conversely, unresolved binaries can evade Gaia.
- A TESS non-detection is weak evidence because of its larger pixels, different bandpass, finite sector coverage, and noise; a TESS period match is independent photometric support but not confirmation of planetary nature.
- The TOI table may lag live ExoFOP-TESS updates, and absence of a public record carries no positive evidential weight.
