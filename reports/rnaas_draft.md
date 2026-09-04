# SXS: A Reproducible Pipeline for Kepler Transit Recovery and Candidate Vetting

**Author:** Rasya Andrean

**Affiliation:** Science Experimental Technologies

## Abstract

SCIX Exoplanet Search (SXS) is a reproducible pipeline combining Box Least Squares (BLS) transit detection with machine-learning ranking and independent candidate vetting in public Kepler photometry. In the version 1 benchmark, BLS recovered 15 of 36 eligible confirmed planets in its five highest peaks, while the Random Forest (RF) retained 12 of 36 end to end (33.33%) with a candidate-level false-positive rate (FPR) of 0.070. The scaled version 2 search recovered 227 of 434 eligible planets with BLS (52.30%) and then examined a deterministic sample of 250 targets without cumulative-KOI or confirmed-Kepler-name history. Independent review of the resulting shortlist found no strong candidate, one weak candidate, and 19 likely false positives; SXS makes no planet-discovery claim.

## Data and Methods

Confirmed-planet parameters came from the NASA Exoplanet Archive `pscomppars` table, and official false-positive labels came from the cumulative KOI table [1]. Kepler long-cadence light curves were obtained from MAST with Lightkurve [2]. After quality filtering, segment normalization, and Savitzky-Golay detrending, Box Least Squares (BLS) searched periods of 0.5–50 days and retained five distinct peaks per target. A 13-feature Random Forest (RF) ranked peaks using BLS and folded-light-curve diagnostics. Five-fold `StratifiedGroupKFold` evaluation grouped all signals by target to prevent cross-target leakage. The RF threshold of 0.221107 maximized precision subject to out-of-fold recall of at least 0.90. Independent validation excluded RF scores from its evidence rules and used 1,000 segment-wise circular-shuffle BLS searches per target, odd/even and secondary-eclipse tests following DR25-style diagnostics [3], limb-darkened `batman` fits [4], Gaia DR3 scene checks [5], TESS photometry, and an ExoFOP-derived TOI lookup [6,7].

## Results

The original benchmark contained 36 planets inside the fixed search range. BLS recovered 15/36 (41.67%); RF classification retained 12/15 recovered signals, giving end-to-end recovery of 12/36 (33.33%). Candidate-level RF precision was 0.632, recall was 0.800, and FPR was 0.070. In the scaled benchmark, BLS recovered 227/434 planets (52.30%). At the exploratory manual-review threshold, RF v2 achieved precision 0.412, recall 0.903, and FPR 0.146 from target-grouped out-of-fold predictions. The FPR is derived from 292 false passes among 2,000 negative peaks.

| Stage and operating point | Precision | Recall | FPR | Recovery or outcome |
|---|---:|---:|---:|---|
| v1 BLS proposal set | 0.130 | 1.000 | 1.000 | 15/36 (41.67%) |
| v1 RF, threshold 0.5 | 0.632 | 0.800 | 0.070 | 12/36 end to end (33.33%) |
| v2 BLS proposal set | — | — | — | 227/434 (52.30%) |
| v2 RF, review threshold 0.221107 | 0.412 | 0.903 | 0.146 | 205 TP; 292 FP |
| Independent vetting | — | — | — | 0 strong; 1 weak; 19 likely FP |

All 250 candidate screening targets completed acquisition, preprocessing, and blind BLS search, producing 1,250 peaks. RF v2 flagged 151 peaks; 110 also passed the available preliminary odd/even, phase-0.5 secondary, and moment-centroid checks. The 20 highest-ranked signals, spanning 14 KIC targets, were frozen before independent validation.

No shortlisted signal met the strong empirical-FAP threshold of 0.01. The sole weak signal, KIC 8300900-r1, has period 5.090289 days and empirical BLS FAP 20/1,001 = 0.01998. It passed the configured odd/even, secondary, morphology, physical-size, and Gaia checks, but lacked TESS period support and is not a confirmed exoplanet. Nineteen signals were classified as likely false positives under prespecified key-failure rules. No position-matched public TOI record was found for the 14 targets, but catalog absence was assigned no positive evidential weight.

SXS demonstrates the separation between ranking performance and independent evidence: an RF can efficiently prioritize transit-like morphology while most high-ranked signals fail a target-specific null test or another independent check. The result is therefore a reproducible methodology and negative-result case study rather than a validation catalog.

## Limitations

The benchmark and bounded 250-target search are too small and selected to support occurrence-rate inference. The RF threshold is an exploratory review threshold, not a calibrated planetary probability, and the empirical FAP is conditional on the shuffle scheme, detrending, sampling, and search grid rather than a VESPA-style Bayesian false-positive probability. Only four Kepler products per search target were analyzed, and no pixel-level analysis, spectroscopy, or new physical follow-up was performed.

## Acknowledgments

This work was independently funded by Rasya Andrean and Urus Foundation. It made use of public services and data from the NASA Exoplanet Archive, MAST, Gaia, TESS, and ExoFOP.

## Data and Software Availability

Repository: `https://github.com/Science-Experimental-Technologies/Exoplanet-Search`; software release `v1.3.0`: `https://doi.org/10.5281/zenodo.22294859`; archived research artifact: `v1.0.0`. Current revisions use the SXS Source-Available Commercial License 1.0; the archived `v1.0.0` copy retains its original license. Versioned configuration, catalog snapshots, metrics, shortlisted-candidate products, independent-vetting tables, and manuscript sources are included. Raw mission products remain available from their source archives.

## References

1. NASA Exoplanet Archive, *Programmatic Interfaces and Kepler/TESS Documentation*, https://exoplanetarchive.ipac.caltech.edu/docs/
2. Lightkurve Collaboration et al. 2018, *Astrophysics Source Code Library*, ascl:1812.013
3. Thompson, S. E. et al. 2018, *ApJS*, 235, 38
4. Kreidberg, L. 2015, *PASP*, 127, 1161
5. European Space Agency, *Gaia Archive Documentation*, https://gea.esac.esa.int/archive/documentation/
6. Mikulski Archive for Space Telescopes, *TESS Mission Archive*, https://archive.stsci.edu/missions-and-data/tess
7. NASA Exoplanet Archive, *TESS Objects of Interest Column Documentation*, https://exoplanetarchive.ipac.caltech.edu/docs/API_TOI_columns.html
