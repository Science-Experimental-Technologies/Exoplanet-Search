# SCIX Exoplanet Search - Project Summary

## Purpose

SCIX Exoplanet Search (SXS) is a reproducible computational astronomy project built from public Kepler, TESS, Gaia, and NASA Exoplanet Archive data. Its objective is to demonstrate an auditable end-to-end transit-search workflow on a local workstation. It is not an observatory program and does not claim a new or confirmed exoplanet.

## Phase 0 - Reproducible foundation

The project fixed Python 3.11, pinned dependencies, deterministic seeds, YAML configuration, repository-relative paths, structured logs, machine-readable run records, and a deterministic default test suite. Live network testing is opt-in.

## Phase 1 - Official data acquisition

Confirmed-planet parameters and Kepler false-positive labels were retrieved from official NASA Exoplanet Archive tables. Kepler long-cadence products were acquired from MAST through Lightkurve. Catalog queries, timestamps, source URLs, and artifact metadata were stored for provenance.

## Phase 2 - Preprocessing

The pipeline removes invalid and quality-flagged cadences, clips extreme outliers, interpolates only short marked gaps, normalizes each source-file segment, and applies iterative Savitzky-Golay detrending. Interpolated points are excluded from transit detection.

## Phase 3 - BLS recovery benchmark

BLS searches periods from 0.5 to 50 days and durations from 1 to 12 hours. On the original benchmark, 36 confirmed planets are inside this domain and 15 are recovered in the top five peaks, giving 41.67% end-to-end BLS recall.

## Phase 4 - Machine-learning vetting

A 13-feature Random Forest and a compact 512-bin folded-view CNN were evaluated with five-fold target-grouped out-of-fold predictions. In v1, RF candidate precision is 0.632, recall 0.800, false-positive rate 0.070, and F1 0.706. The CNN is retained as a research baseline.

## Phases 5-6 - Catalog boundary and research record

Operational candidate scores were separated from benchmark estimates. Catalog matches, official false-positive membership, and unmatched signals were recorded without treating catalog absence as validation. Phase reports, confusion matrices, metrics, and the research draft established the first complete SXS research record.

## Phase 7 - Scale-up and retraining

The labeled sample grew to 371 confirmed hosts with 434 eligible planets and 400 official false-positive targets. BLS recovered 227/434 planets in its top five. The candidate set contains 2,227 rows across 619 target groups. RF v2 was selected at an exploratory review threshold of 0.221107, where grouped out-of-fold precision is 0.412 and recall is 0.903. CNN remained secondary because it had lower precision and unstable fold-level F1.

## Phase 8 - Bounded candidate search

The official unclassified-pool construction yielded 100,347 eligible targets after magnitude, quarter, KOI-history, and confirmed-name exclusions. A deterministic SHA-256 sample of 250 targets was processed under the workstation constraint. The run produced 1,250 BLS peaks, 151 RF review passes, 110 RF-plus-preliminary-sanity passes, and a frozen top-20 review queue across 14 KIC targets. Every signal remained explicitly unvalidated.

## Phase 9 - Independent validation

Validation excluded all RF and CNN outputs from its score and rules. The stage saved 20,000 candidate-level BLS null draws from 1,000 segment-wise circular shuffles per target; formal odd/even tests; secondary-eclipse depths and limits; limb-darkened transit fits; stellar-radius plausibility checks; Gaia DR3 source scenes; TESS period searches; and position-matched TOI records.

The accepted result is:

- 0 `strong_candidate`
- 1 `weak_candidate`
- 19 `likely_false_positive`

KIC 8300900-r1 is the sole weak signal. Its period is 5.090289 days and its empirical BLS FAP is 0.01998, above the 1% strong-candidate threshold. It lacks TESS period support. It is not a confirmed exoplanet.

## Phase 10 - Publication and release preparation

The research report was rewritten as a self-contained submission-style preprint with explicit methodology, benchmark metrics, independent-vetting results, limitations, references, acknowledgments, and data-availability guidance. The repository gained citation metadata, a changelog, this project summary, a rendered and visually checked PDF, public-path and secret audits, and version 2.0.0 release metadata.

## Portfolio interpretation

SXS demonstrates practical skills in scientific Python, time-series processing, public archive integration, reproducible experiment design, grouped machine-learning evaluation, multiprocessing, statistical testing, physical-model fitting, cross-mission analysis, documentation, and honest negative-result reporting.

The defensible claim is methodological: SXS can acquire public data, measure recovery, prioritize signals, and reject most of its own high-scoring outputs when independent evidence is insufficient. It does not demonstrate a new planet discovery.

## Primary outputs

- `reports/research_report.md` - submission-style preprint source
- `output/pdf/sxs_preprint_v2.0.0.pdf` - visually verified preprint PDF
- `reports/phase9_independent_validation.md` - complete independent-vetting record
- `data/phase9/final_ranking.csv` - final transparent candidate ranking
- `data/phase9/fap_results.parquet` - 20,000 saved candidate-level null draws
- `CITATION.cff` - citation metadata
- `CHANGELOG.md` - v1 to v2 release history
