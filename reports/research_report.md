# SXS: A Reproducible Kepler Transit-Recovery and Independent Vetting Pipeline

**Rasya Andrean — Science Experimental Technologies**

**Draft date:** 28 August 2026

**Version:** public software release 1.0.0; internal research milestone 2.0.0

**Suggested venue:** arXiv astro-ph.EP or Research Notes of the AAS

**Status:** submission-ready preprint draft; not submitted

## Abstract

We present SCIX Exoplanet Search (SXS), a reproducible computational pipeline for transit recovery, candidate vetting, and explicitly bounded candidate search in public Kepler photometry. SXS combines quality filtering, quarter-wise normalization, Savitzky-Golay detrending, Box Least Squares (BLS), a feature-based Random Forest, a compact one-dimensional convolutional neural network, official catalog cross-checks, and a final validation stage that is methodologically independent of the machine-learning ranker. In the original 20-system benchmark, 36 confirmed planets fall inside the 0.5-50 day search domain. BLS recovers 15/36 (41.67%) in its top five peaks. On the resulting candidate-level vetting set, the Random Forest obtains precision 0.632, recall 0.800, false-positive rate 0.070, and F1 0.706 under five-fold target-grouped out-of-fold evaluation; end-to-end recovery is 12/36 (33.33%). A scale-up to 371 confirmed hosts, 434 eligible planets, and 400 official false-positive targets increases BLS top-five recovery to 227/434 (52.30%). The selected Phase 7 Random Forest uses an exploratory review threshold of 0.221107, at which grouped out-of-fold precision is 0.412 and recall is 0.903. We then apply the frozen model to a deterministic workstation-bounded sample of 250 targets without KOI or confirmed-name history, producing a 20-signal review queue. Independent Phase 9 validation uses 1,000 segment-wise circular-shuffle BLS searches per target, formal odd/even and secondary-eclipse tests, limb-darkened transit fits, stellar-radius plausibility checks, Gaia DR3 scene analysis, TESS photometry, and an ExoFOP-derived TOI lookup. The final outcome is 0 strong candidates, 1 weak candidate, and 19 likely false positives. The sole weak signal, KIC 8300900-r1 at 5.090289 days, has empirical BLS false-alarm probability 0.01998 and is not a confirmed exoplanet. SXS is therefore a reproducible methodology demonstration and negative-result case study, not a planet-discovery claim.

**Keywords:** exoplanets; transit photometry; Kepler; TESS; time-series analysis; machine learning; reproducible research

## 1. Introduction

Transit surveys measure repeated reductions in stellar flux when an orbiting body crosses the apparent stellar disk. The scientific difficulty is not only detecting periodic decreases but also distinguishing planetary transits from instrumental artifacts, stellar variability, grazing binaries, background eclipsing systems, and aliases. Kepler produced photometry of sufficient duration and precision to make this a canonical setting for automated transit-search research, while the NASA Exoplanet Archive and the Mikulski Archive for Space Telescopes (MAST) make the relevant catalogs and light curves publicly accessible.

BLS remains a standard classical detector because it searches directly for periodic box-like decreases in irregularly sampled photometry [1]. Catalog construction requires a second layer of vetting. The Kepler DR25 Robovetter combined multiple diagnostics and was evaluated with injected, inverted, and scrambled populations to characterize catalog completeness and reliability [2]. Machine-learning approaches provide complementary ranking tools. AstroNet showed that global and local folded-light-curve views can support deep classification [3]. ExoMiner later organized diagnostic inputs in a domain-informed architecture and demonstrated high-precision statistical validation under a much larger, purpose-built framework [4]. These systems establish useful methodological context, but their validation claims do not transfer automatically to a smaller independent implementation.

SXS was designed around a narrower question: can a complete transit-recovery workflow be made auditable on a local workstation while keeping detection performance, classifier performance, catalog association, and independent astrophysical evidence conceptually separate? The project therefore developed in stages. The first version benchmarked recovery on known systems. The second version scaled the labeled sample, froze a model-selection policy, searched an explicitly unclassified target sample, and subjected the resulting shortlist to non-circular validation.

The distinction between ranking and validation is central. A Random Forest score from SXS is not a calibrated posterior probability that a signal is planetary. Reapplying the same features or a closely related classifier would reproduce model preferences rather than provide independent evidence. Phase 9 consequently excludes all RF and CNN outputs from its evidence score and category rules. This paper reports the full Phase 0-9 workflow, including the result that no signal satisfies the strong-candidate definition.

## 2. Data and provenance

### 2.1 Official archives

Confirmed-planet parameters were retrieved from the NASA Exoplanet Archive `pscomppars` table through its Table Access Protocol interface. Official Kepler false-positive labels and vetting flags came from the cumulative KOI table. Kepler long-cadence light curves were downloaded from MAST using Lightkurve [5]. Each stored catalog snapshot records the query, retrieval time, source URL, and artifact metadata. Raw FITS products are treated as immutable cache inputs.

For the independent validation stage, Gaia DR3 sources were queried through the ESA Gaia Archive with `astroquery.gaia`. TESS light curves were located through coordinate-linked TIC identifiers and downloaded from MAST. The NASA Exoplanet Archive TOI table was used as a reproducible position-matched view of public TESS Objects of Interest; the Archive documents that this table is updated from the ExoFOP-TESS list.

### 2.2 Version 1 benchmark sample

The initial positive sample contains 20 confirmed Kepler systems and 47 catalog planets. Thirty-six planets have periods within the fixed 0.5-50 day search domain. The negative sample contains 20 unique targets selected from official false-positive KOIs, balanced across four deterministic assignment categories: not transit-like, stellar eclipse, centroid offset, and ephemeris contamination. Official flags can overlap; the assigned category is a sampling device, not an assertion of mutually exclusive physics.

Candidate-level evaluation uses 15 BLS peaks associated with exactly recovered catalog planets and 100 peaks from the 20 false-positive systems. All cross-validation splits are grouped by target identifier so that signals from the same star cannot occur on both sides of a train/evaluation boundary.

### 2.3 Version 2 scale-up sample

The Phase 7 scale-up applies catalog quality constraints before any search of unknown targets. Positive selection requires a confirmed Kepler planet inside the BLS domain, transit signal-to-noise at least 50, Kepler magnitude no fainter than 15, and at least eight available long-cadence quarters. This yields 371 confirmed hosts and 434 eligible planets. The negative population uses official false-positive KOIs with transit signal-to-noise at least 10, the same magnitude and quarter requirements, and deterministic balancing across the four assigned flag groups. Under the documented workstation constraint, 400 unique false-positive targets are processed, exactly 100 per assigned group.

Both classes use four chronological Kepler products per target in Phase 7. All 771 targets complete acquisition and preprocessing without skips. This matched product cap reduces, but does not eliminate, nuisance differences between positive and negative examples.

### 2.4 Unclassified search pool

Phase 8 uses the official Kepler time-series table to construct a pool with `object_status=0`, Kepler magnitude 10-15, and at least eight available quarters. Every KIC appearing anywhere in the cumulative KOI table or the confirmed Kepler-name table is removed. The resulting eligible pool contains 100,347 targets. Because a full-pool search exceeds the intended workstation budget, 250 targets are selected by ascending SHA-256 of a fixed seed and KIC. The sampling hash is independent of flux morphology, BLS results, and model scores.

## 3. Methods

### 3.1 Environment and reproducibility controls

Phase 0 fixes Python 3.11, pinned direct dependencies, deterministic random seeds, repository-relative paths, and structured YAML configuration. Each major stage writes a machine-readable run record and a human-readable report. The default test suite is deterministic; the real MAST smoke test is opt-in to avoid making routine verification depend on network state.

### 3.2 Light-curve acquisition and preprocessing

The acquisition layer distinguishes missing targets, download failures, corrupt products, and valid cache hits. Preprocessing removes non-finite samples and cadences rejected by the configured Kepler quality bitmask. Extreme positive and negative outliers are clipped asymmetrically. Only short internal gaps, at most three cadences, are interpolated; every interpolated row is marked and later excluded from BLS.

Each source-file segment is median-normalized separately. A Savitzky-Golay trend with a 401-cadence window and polynomial order 2 is estimated iteratively. The window is longer than the trial transit durations, reducing the risk that the detrending model absorbs short transit-like events. Phase 2 transit-preservation checks compare representative known systems before and after detrending. This operation is not a guarantee of unbiased depth recovery for all periods, stellar variability regimes, or transit durations.

### 3.3 Box Least Squares search

SXS uses `astropy.timeseries.BoxLeastSquares` [6]. The search spans 0.5-50 days with trial durations of 1, 2, 4, 8, and 12 hours. Frequency sampling is five points per Rayleigh resolution element, based on each light curve's time baseline. The BLS objective is signal-to-noise. The five highest distinct peaks are retained, subject to at least 1% relative period separation. Catalog periods and epochs are never supplied to detection.

An exact recovery requires a candidate period within 1% of the catalog period. Half-period and double-period aliases are retained only as diagnostics. End-to-end recall uses all 36 eligible v1 planets, including those for which BLS proposes no matching peak.

### 3.4 Feature-based and convolutional vetters

The Random Forest uses 13 numerical features derived from BLS and folded photometry, including period, duration, depth, signal-to-noise, event counts, odd/even mismatch, a phase-0.5 secondary diagnostic, and local scatter summaries. The compact one-dimensional CNN consumes a robustly normalized 512-bin global folded view. It is a research baseline, not an attempted reproduction of the larger AstroNet or ExoMiner architectures.

Both models are evaluated with five-fold `StratifiedGroupKFold`, grouped by target identifier. Saved out-of-fold predictions are the only source of reported candidate-level generalization metrics. Models subsequently fitted on the complete labeled set are operational artifacts and are not evaluated on their own training predictions.

Phase 7 defines a manual-review threshold by maximizing precision subject to grouped out-of-fold recall of at least 0.90. CNN replaces RF only if it improves precision by at least 0.02 and has fold-to-fold F1 standard deviation at most 0.10. This policy selects RF v2 at threshold 0.221107. The threshold is an exploratory operating point, not a probability calibration.

### 3.5 Phase 8 candidate search

All 250 deterministic unknown-pool targets use the same preprocessing and blind BLS configuration. The accepted RF v2 artifact scores every BLS peak. A preliminary sanity layer checks simple odd/even mismatch, phase-0.5 depth ratio, and available moment-centroid columns. The top 20 signals among rows passing the RF review threshold and without a failed preliminary sanity check form the frozen Phase 9 queue. This procedure is selection, not validation.

### 3.6 Independent empirical BLS false-alarm probability

For each of the 14 unique shortlisted targets, Phase 9 generates 1,000 null light curves. Flux and uncertainty arrays within each of the four cached source-file segments are circularly shifted by an independently sampled offset. This preserves cadence sampling and within-segment short-timescale correlation while disrupting a common phase across segments. Every null light curve is searched over the complete Phase 8 period and duration grid. The null statistic is the maximum BLS power across that grid, incorporating the period-search look-elsewhere effect.

For candidate power z, empirical FAP is:

`FAP = (N(null maximum >= z) + 1) / (N(null) + 1)`.

With 1,000 shuffles, the minimum reportable value is 1/1,001 = 0.000999. Because multiple shortlisted periods can belong to one target, the same target-level null distribution is compared with each candidate's observed power and expanded into candidate-level audit rows. The final artifact contains 20,000 rows. This FAP is conditional on the chosen shuffle, detrending, sampling, and search grid; it is not an astrophysical false-positive probability.

### 3.7 Independent photometric vetting

Odd and even transit depths are measured event by event using local baselines. A two-sided Welch t-test compares the two event populations, with p < 0.01 treated as a red flag. The phase-0.5 secondary depth is compared with robust out-of-eclipse scatter. A secondary red flag requires at least 3-sigma significance and depth at least 10% of the primary. A three-sigma upper limit is saved when no significant secondary is found.

A circular-orbit, quadratic-limb-darkened transit model is fitted with `batman` [7]. Period is fixed to the BLS value; radius ratio, scaled semimajor axis, impact parameter, center offset, and baseline are fitted to binned folded photometry. The diagnostic `b + Rp/Rstar >= 1` marks a V-shaped or grazing geometry. Stellar radii from the frozen target pool convert fitted radius ratio to an implied companion radius; values above 22 Earth radii are treated as non-planet-like screening failures. A failed numerical fit is labeled unavailable rather than forced into either morphology class.

### 3.8 Gaia, TESS, and public TOI evidence

Gaia DR3 sources within 30 arcsec are retained. The closest source is treated as the target counterpart. Another Gaia source is a high-risk contamination flag when it lies within 4 arcsec, approximately one Kepler pixel, and is no more than 5 G magnitudes fainter than the target.

TESS searches use the TIC row explicitly matching each KIC. Up to four products from the highest-priority available light-curve pipeline are combined. For each Kepler signal, a targeted BLS scan covers 90%-110% of the candidate period. Independent period support requires the best TESS period to agree within 1% and to have BLS depth signal-to-noise at least 5. TESS non-recovery is assigned limited negative weight because its bandpass, pixel scale, precision, apertures, and temporal coverage differ from Kepler.

The TOI table is position-matched within 10 arcsec. Public disposition, period, and period agreement are recorded. Absence from the table contributes no positive evidence and is not treated as a rejection.

### 3.9 Transparent evidence score and categories

The Phase 9 score is an audit summary, not a posterior probability. Contributions are: FAP pass/borderline/fail = +3/+1/-3; odd/even pass/fail = +1/-3; secondary pass/fail = +1/-3; U-shaped/V-shaped = +2/-3; physical size pass/fail = +1/-3; clean/high-risk Gaia scene = +1/-3; TESS confirmation/available non-confirmation = +2/-1; and TOI period match/public false-positive flag = +1/-3. Unavailable evidence contributes zero.

A key failure - FAP above 0.05, formal odd/even failure, significant secondary, V/grazing shape, implausible radius, high-risk Gaia contaminant, or public false-positive flag - forces `likely_false_positive`. A `strong_candidate` must have FAP at most 0.01, pass every internal test, have a clean available Gaia scene, and show TESS period support. Rows without a key failure but lacking the complete strong evidence set are `weak_candidate`. No category represents a confirmed exoplanet.

## 4. Results

### 4.1 Version 1 benchmark

| Stage | Precision | Recall | FPR | F1 | End-to-end recall |
|---|---:|---:|---:|---:|---:|
| BLS only | 0.130 | 1.000 | 1.000 | 0.231 | 15/36 = 41.67% |
| Random Forest | 0.632 | 0.800 | 0.070 | 0.706 | 12/36 = 33.33% |
| 1D CNN | 0.258 | 0.533 | 0.230 | 0.348 | 8/36 = 22.22% |

BLS recovers 15 of 36 eligible planets. The Random Forest rejects 93 of 100 false-positive-system peaks while retaining 12 of 15 recovered-planet peaks. Its improved candidate purity comes at the expected cost of lower end-to-end recall because no downstream classifier can recover a planet absent from the BLS proposal set. The small CNN underperforms the feature model on this sample.

![Version 1 confusion matrices](confusion_matrices.png)

### 4.2 Phase 7 scale-up and model selection

The scaled BLS run recovers 227/434 eligible planets (52.30%) in the top five, compared with 15/36 (41.67%) in v1. Candidate construction yields 227 recovered-planet peaks and 2,000 false-positive-system peaks across 619 target groups.

| Model at threshold 0.5 | Precision | Recall | F1 | ROC-AUC | Average precision |
|---|---:|---:|---:|---:|---:|
| RF v2 | 0.534 | 0.789 | 0.637 | 0.937 | 0.641 |
| CNN v2 | 0.227 | 0.736 | 0.347 | 0.819 | 0.352 |

At the Phase 7 review operating point, RF v2 reaches precision 0.412 and recall 0.903 at threshold 0.221107. CNN reaches recall 0.912 at threshold 0.394803 but precision is 0.198 and fold-F1 standard deviation is 0.166. The prespecified policy therefore selects RF v2 and retains CNN only as a secondary diagnostic.

### 4.3 Phase 8 bounded candidate search

All 250 selected targets complete four-product acquisition, preprocessing, and blind BLS search. The run produces 1,250 peaks. RF v2 flags 151 at its frozen review threshold; 110 also have no failed preliminary odd/even, phase-0.5 secondary, or available moment-centroid check. The highest-scoring 20 form the Phase 9 queue. A live post-ranking catalog recheck finds no cumulative KOI row and no confirmed Kepler name for the 14 unique KICs at that time. This catalog absence means only that the targets were not present in those tables; it does not establish astrophysical novelty.

### 4.4 Phase 9 independent validation

The 20 candidate-level null distributions contain 1,000 draws each. No signal reaches the prespecified strong FAP threshold of 0.01. The best result is KIC 8300900-r1: 19 of 1,000 null maxima equal or exceed the observed power, giving FAP 20/1,001 = 0.01998. The second-best signal has FAP 0.05594, already above the key-failure boundary.

All 20 formal odd/even tests are available and none fails at p < 0.01. One signal, KIC 9767793-r3, has a significant phase-0.5 secondary under the configured rule. One signal, KIC 6268872-r5, has a fitted V/grazing geometry. The fit for KIC 10124049-r2 does not converge and is retained as unavailable. KIC 3655287 has a Gaia neighbor within the high-risk separation and magnitude criteria, affecting all three shortlisted periods on that target.

TESS light curves are available for all 14 unique targets. Only KIC 6268872-r5 meets the TESS period-support rule, but its FAP is 0.99600 and its transit fit is V/grazing; cross-mission periodicity therefore does not rescue its planetary interpretation. No position-matched public TOI record is found for the 14 targets.

| Rank | Signal | Period (d) | FAP | Score | Final category | Principal note |
|---:|---|---:|---:|---:|---|---|
| 1 | 8300900-r1 | 5.090289 | 0.01998 | 6 | weak_candidate | Best FAP, above 1%; no TESS support |
| 2 | 8163439-r1 | 14.151354 | 0.05594 | 2 | likely_false_positive | FAP key failure |
| 3 | 11561399-r3 | 9.877735 | 0.22178 | 2 | likely_false_positive | FAP key failure |
| 4 | 1027740-r4 | 12.035808 | 0.39760 | 2 | likely_false_positive | FAP key failure |
| 5 | 7976673-r2 | 4.979590 | 0.52148 | 2 | likely_false_positive | FAP key failure |
| 6 | 4283320-r2 | 11.693914 | 0.62837 | 2 | likely_false_positive | FAP key failure |
| 7 | 2011905-r5 | 11.575636 | 0.63137 | 2 | likely_false_positive | FAP key failure |
| 8 | 8300900-r3 | 30.208825 | 0.95305 | 2 | likely_false_positive | FAP key failure |
| 9 | 6268872-r3 | 7.764579 | 0.95405 | 2 | likely_false_positive | FAP key failure |
| 10 | 8765712-r5 | 21.858360 | 0.97203 | 2 | likely_false_positive | FAP key failure |
| 11 | 8163439-r4 | 24.411279 | 0.97403 | 2 | likely_false_positive | FAP key failure |
| 12 | 8159207-r3 | 15.083637 | 0.98701 | 2 | likely_false_positive | FAP key failure |
| 13 | 8300900-r5 | 5.506531 | 0.99900 | 2 | likely_false_positive | FAP key failure |
| 14 | 9650424-r5 | 3.053610 | 1.00000 | 2 | likely_false_positive | FAP key failure |
| 15 | 6268872-r5 | 24.246530 | 0.99600 | 0 | likely_false_positive | V/grazing; TESS support |
| 16 | 10124049-r2 | 15.285027 | 0.86214 | -1 | likely_false_positive | Transit fit unavailable |
| 17 | 9767793-r3 | 10.283070 | 0.60340 | -2 | likely_false_positive | Significant secondary |
| 18 | 3655287-r1 | 18.478278 | 0.69830 | -2 | likely_false_positive | High-risk Gaia neighbor |
| 19 | 3655287-r2 | 3.724685 | 0.70629 | -2 | likely_false_positive | High-risk Gaia neighbor |
| 20 | 3655287-r5 | 22.170294 | 0.99800 | -2 | likely_false_positive | High-risk Gaia neighbor |

The final category counts are therefore 0 `strong_candidate`, 1 `weak_candidate`, and 19 `likely_false_positive`. There is no strong-candidate priority list for publication or follow-up.

## 5. Discussion

SXS demonstrates why selection performance and scientific validation must be separated. The Phase 8 RF scores are high for several signals, but the independent segment-shuffle test shows that comparable or stronger BLS maxima commonly arise after disrupting cross-segment phase alignment. The ranking model successfully identifies transit-like morphology relative to its training set; that result does not imply that the selected peak is rare under a target-specific null.

The single weak signal illustrates the intended interpretation boundary. KIC 8300900-r1 has the smallest empirical FAP and passes the available internal shape, odd/even, secondary, physical-size, and Gaia checks. However, its FAP is approximately 2%, TESS does not independently support the period, and the null model is conditional on only four Kepler products. It merits at most cautious further analysis. Calling it a validated or discovered planet would exceed the evidence.

The TESS-supported signal provides a complementary caution. Periodic behavior can recur across missions while still being non-planetary. KIC 6268872-r5 is supported at a similar period in TESS but fails the empirical FAP and has a grazing morphology. Cross-mission consistency therefore indicates a persistent astrophysical or blended periodic source, not necessarily a planet.

Compared with survey-scale systems, SXS is intentionally small. Robovetter uses a wider diagnostic system and purpose-built simulated populations [2]. AstroNet and ExoMiner train on far larger labeled collections and, in the latter case, combine multiple diagnostic branches [3,4]. SXS contributes neither a higher-performing classifier nor a new validation framework. Its useful contribution is procedural: it records how a workstation-scale project can freeze provenance, avoid target leakage, distinguish operational scores from out-of-fold metrics, bound an unknown-target search, and accept a mostly negative independent-vetting result.

## 6. Limitations

1. **Selection and sample size.** The v1 benchmark is small and curated. Phase 7 is larger but remains selected by catalog signal-to-noise, magnitude, quarter coverage, and dispositions. Neither sample supports occurrence-rate inference.
2. **Candidate correlation.** Multiple BLS peaks can arise from one target. Grouped cross-validation prevents train/evaluation leakage but does not make candidate rows statistically independent.
3. **Four-product cap.** Phases 7-9 use four chronological Kepler products per target. This makes workstation execution feasible but discards available temporal coverage and can change recovery and FAP behavior.
4. **Detection model.** BLS assumes strictly periodic, box-like events. Transit-timing variations, circumbinary dynamics, stellar activity, shallow events, and competing multi-planet peaks can reduce recovery or promote aliases.
5. **Detrending.** Savitzky-Golay filtering can distort signals whose timescales interact with the filter window. Representative preservation checks do not prove unbiased performance over the full parameter space.
6. **Machine-learning calibration.** RF and CNN outputs are not calibrated posterior probabilities. The Phase 7 threshold is intended only for review prioritization.
7. **CNN evaluation.** The CNN sample is modest, and its early stopping uses each held-out fold as validation. Nested validation would provide a stricter estimate.
8. **Empirical FAP.** Segment shifts do not reproduce every instrumental systematic, stellar process, or blend. FAP is not `P(false positive | data)` and is not a VESPA-style Bayesian false-positive probability.
9. **Transit fits.** The fits assume circular orbits and approximate fixed limb darkening. Grazing geometry, dilution, eccentricity, impact parameter, stellar radius, and radius ratio are degenerate.
10. **Gaia scene interpretation.** A nearby source indicates risk but does not show that it caused the event. Unresolved companions can escape Gaia.
11. **TESS interpretation.** Different pixels, apertures, cadence, bandpass, noise, and windows limit both positive and negative inference.
12. **Catalog status.** Absence from KOI, confirmed-name, or TOI tables is not evidence of novelty. Catalogs evolve.
13. **No physical follow-up.** SXS includes no new spectroscopy, radial velocities, adaptive optics, difference imaging, or dedicated photometric follow-up. It cannot confirm a planet.

## 7. Reproducibility and data availability

The release includes pinned dependency files, YAML configurations, deterministic tests, source modules, machine-readable metrics, catalog provenance, the frozen Phase 8 shortlist, 20,000 Phase 9 FAP draws, external cross-match summaries, and phase-specific reports. Large raw FITS products, TESS cache files, intermediate null caches, trained binary models, and generated tensors are excluded from version control and can be regenerated from public services subject to archive availability.

The primary commands are documented in `README.md`. The default test command is `python -m pytest`; the accepted release passes 35 tests, with one opt-in live-network test skipped by default. Exact floating-point identity across operating systems or binary builds is not guaranteed. Reproducing stored results requires the committed catalog snapshots and no catalog refresh.

## 8. Conclusion

The internal SXS 2.0.0 research milestone, distributed in public software release 1.0.0, is a complete, auditable computational astronomy workflow spanning official data acquisition, preprocessing, transit recovery, target-grouped model evaluation, bounded candidate search, and independent vetting. Its strongest positive benchmark result is the feature-based vetter's reduction of v1 candidate false-positive rate from 1.00 at the BLS-only stage to 0.07 while retaining 12 of 15 BLS-recovered planets. Its most important search result is negative: among 20 ML-prioritized signals, independent validation identifies no strong candidate, one weak candidate, and 19 likely false positives.

This outcome supports the project's central methodological claim rather than a discovery claim. A reproducible candidate-search pipeline should be able to reject its own highly ranked outputs when independent evidence is insufficient. KIC 8300900-r1 remains an unconfirmed weak signal requiring analysis beyond SXS. No object reported here is a confirmed exoplanet or a claimed new discovery.

## Acknowledgments

This work used public data from the NASA Exoplanet Archive, the Mikulski Archive for Space Telescopes, and the ESA Gaia Archive. It used Astropy, astroquery, Lightkurve, NumPy, SciPy, pandas, scikit-learn, TensorFlow, matplotlib, PyArrow, and `batman`. SCIX acknowledges the teams that produced, calibrated, archived, and documented the Kepler, TESS, and Gaia data products.

## References

1. Kovacs, G., Zucker, S., and Mazeh, T. (2002). "A box-fitting algorithm in the search for periodic transits." *Astronomy & Astrophysics*, 391, 369-377. https://doi.org/10.1051/0004-6361:20020802
2. Thompson, S. E. et al. (2018). "Planetary Candidates Observed by Kepler. VIII. A Fully Automated Catalog with Measured Completeness and Reliability Based on Data Release 25." *The Astrophysical Journal Supplement Series*, 235, 38. https://doi.org/10.3847/1538-4365/aab4f9
3. Shallue, C. J. and Vanderburg, A. (2018). "Identifying Exoplanets with Deep Learning: A Five-planet Resonant Chain around Kepler-80 and an Eighth Planet around Kepler-90." *The Astronomical Journal*, 155, 94. https://doi.org/10.3847/1538-3881/aa9e09
4. Valizadegan, H. et al. (2022). "ExoMiner: A Highly Accurate and Explainable Deep Learning Classifier that Validates 301 New Exoplanets." *The Astrophysical Journal*, 926, 120. https://doi.org/10.3847/1538-4357/ac4399
5. Lightkurve Collaboration et al. (2018). "Lightkurve: Kepler and TESS time series analysis in Python." *Astrophysics Source Code Library*, ascl:1812.013. https://ui.adsabs.harvard.edu/abs/2018ascl.soft12013L
6. Astropy Collaboration et al. (2022). "The Astropy Project: Sustaining and Growing a Community-oriented Open-source Project and the Latest Major Release (v5.0) of the Core Package." *The Astrophysical Journal*, 935, 167. https://doi.org/10.3847/1538-4357/ac7c74
7. Kreidberg, L. (2015). "batman: BAsic Transit Model cAlculatioN in Python." *Publications of the Astronomical Society of the Pacific*, 127, 1161. https://doi.org/10.1086/683602
8. Ginsburg, A. et al. (2019). "astroquery: An Astronomical Web-querying Package in Python." *The Astronomical Journal*, 157, 98. https://doi.org/10.3847/1538-3881/aafc33
9. NASA Exoplanet Archive. Programmatic Interfaces and Kepler/TESS documentation. https://exoplanetarchive.ipac.caltech.edu/docs/
10. Mikulski Archive for Space Telescopes. Kepler and TESS archives. https://archive.stsci.edu/
11. European Space Agency. Gaia Archive documentation. https://gea.esac.esa.int/archive/documentation/
