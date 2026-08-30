# Artifact Reference

## Baseline

| Artifact | Role |
|---|---|
| `data/processed/manifest.csv` | Mission-product acquisition record |
| `data/processed/preprocessing_summary.json` | Cleaning/detrending status |
| `data/processed/bls_candidates.parquet` | Top BLS proposals |
| `data/processed/bls_recovery.csv` | Catalog-period recovery evaluation |
| `reports/baseline_transit_recovery.md` | Human-readable recovery table |
| `reports/experiments/feature_cv.json` | Grouped RF predictions and metrics |
| `reports/experiments/cnn_cv.json` | Grouped CNN predictions and metrics |
| `reports/benchmark_metrics.json` | Final baseline confusion matrices/metrics |
| `reports/benchmark_report.md` | Baseline interpretation |
| `reports/pipeline_run_latest.json` | Latest structured baseline run |

## Scale-up qualification

| Artifact | Role |
|---|---|
| `data/scaleup/catalog/confirmed_targets.yaml` | Selected confirmed hosts |
| `data/scaleup/processed/confirmed/bls_recovery.csv` | Scaled recovery rows |
| `data/scaleup/processed/ml_candidate_metadata.csv` | Candidate labels/groups |
| `reports/experiments/scaleup/rf_v2_cv.json` | RF v2 grouped evaluation |
| `reports/experiments/scaleup/cnn_v2_cv.json` | CNN v2 grouped evaluation |
| `models/production_model_selection.json` | Frozen model, threshold, policy |
| `reports/model_qualification.md` | Selection rationale and metrics |
| `reports/scaleup_run_latest.json` | Latest structured scale-up run |

Large model binaries such as `models/rf_v2.joblib` and `models/cnn_v2.keras`
are intentionally not tracked in Git.

## Candidate screening

| Artifact | Role |
|---|---|
| `data/search/catalog/eligible_unknown_pool.parquet` | Catalog-filtered target pool |
| `data/search/catalog/selected_unknown_targets.yaml` | Deterministic 250-target sample |
| `data/search/catalog/selection_summary.json` | Pool counts and selection hashes |
| `data/search/processed/scored_candidates.parquet` | All 1,250 scored BLS peaks |
| `data/search/processed/shortlist_top20.csv` | Frozen independent-review queue |
| `reports/candidate_figures/` | Folded views for the 20 signals |
| `reports/candidate_catalog_recheck.json` | Post-ranking catalog evidence |
| `reports/candidate_screening.md` | Screening report |
| `reports/search_run_latest.json` | Search acceptance record |

## Independent validation

| Artifact | Role |
|---|---|
| `data/validation/frozen_search_shortlist.parquet` | Hash-checked audit input |
| `data/validation/fap_results.parquet` | Observed/null comparison by candidate |
| `data/validation/independent_vetting.parquet` | Photometric/physical evidence |
| `data/validation/gaia_sources.parquet` | Gaia query results |
| `data/validation/crossmatch_results.parquet` | Gaia/TESS/ExoFOP summary |
| `data/validation/final_ranking.csv` | Category and transparent score |
| `reports/independent_validation.md` | Final audit report |
| `reports/validation_run_latest.json` | Acceptance checks and shortlist SHA-256 |

## Publication and release

- `reports/research_report.md`: complete paper-length record;
- `reports/rnaas_draft.md`: condensed RNAAS-format draft;
- `reports/rnaas_draft_consistency_check.md`: draft/source metric check;
- `output/pdf/sxs_preprint_v1.0.0.pdf`: visually verified preprint;
- `CITATION.cff`: software citation metadata; and
- `CHANGELOG.md`: public version history.

Machine-readable artifacts may retain historical numbered identifiers for
schema and hash compatibility. Public documentation uses descriptive workflow
names.
