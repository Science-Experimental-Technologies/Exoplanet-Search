# Scientific Background

## Transit photometry

A transiting companion blocks a small fraction of its host star's light when
its orbit crosses the line of sight. Repeated, approximately periodic dips can
therefore reveal an orbital period, transit duration, epoch, and depth. The
signal is difficult to recover when stellar variability, instrument systematics,
gaps, dilution, eclipsing binaries, or low signal-to-noise produce similar
structure.

SXS operates on public Kepler long-cadence light curves. It is a computational
recovery and review system; it does not produce spectroscopy, high-resolution
imaging, or new telescope observations.

## Why a pipeline needs multiple layers

No single score is sufficient for a discovery claim:

1. **Preprocessing** can suppress noise but may also distort a transit.
2. **BLS** finds box-like periodic signals but also responds to binaries,
   systematics, and stellar variability.
3. **Machine learning** can prioritize familiar signal patterns but inherits
   the training distribution and decision threshold.
4. **Independent vetting** can reject many failure modes, but missing evidence
   and observational limits remain.

SXS therefore separates detection, ranking, and independent audit. The RF/CNN
scores are excluded from the final validation rules.

## Research questions

The research record addresses four bounded questions:

1. How often does the configured BLS search recover known Kepler planets in its
   five highest distinct peaks?
2. Can a target-grouped feature model reduce candidate-level false passes while
   retaining most BLS-recovered positives?
3. What happens when the frozen model screens a deterministic workstation-scale
   target sample with no selected catalog history?
4. Do the shortlisted signals survive independent statistical, photometric,
   catalog, Gaia, and TESS checks?

It does **not** estimate exoplanet occurrence rates or claim a complete Kepler
search.

## Ground truth and external evidence

- confirmed-planet parameters: NASA Exoplanet Archive `pscomppars`;
- Kepler false-positive labels and flags: cumulative KOI table;
- time-series products: MAST, acquired with Lightkurve;
- scene context: Gaia DR3;
- independent photometric comparison: public TESS products where available;
- public candidate history: ExoFOP-derived TOI lookup.

Each upstream source retains its own terms and citation requirements. The
[citation guide](../project/citation.md) lists the project-level expectation.
