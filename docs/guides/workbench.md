# Isolated experiments and analysis workbench

These commands are **unreleased current-branch features**, not additions to the
published v1.1.0 bundles. Use a current checkout with `requirements-core.txt`.
They do not replace the archived research metrics or confirm planets.

## 1. Safe cache, resume, and workspaces

Baseline, scale-up, and search now require a content-verified checkpoint for
`--resume`. A checkpoint records completed steps, configuration, Python and
scientific package versions, source hashes, and local artifact hashes.
Changed, missing, or legacy checkpoints are rejected rather than trusted.

```bash
python -m src.cli baseline --workspace runs/research-a --dry-run
python -m src.cli baseline --workspace runs/research-a
python -m src.cli baseline --workspace runs/research-a --resume
python -m src.cli scaleup --workspace runs/research-a
python -m src.cli search --workspace runs/research-a
python -m src.cli validate --workspace runs/research-a
```

The complete research sequence needs `requirements.txt` and public archive
access. Workspace creation copies the checkout's `configs/` directory, not
models, observations, or prior results. Later commands reuse those workspace
configs, not updated checkout configs. Edit them deliberately for a new
experiment. Relative `--config` and artifact paths resolve inside the workspace.
Absolute paths in custom configs are not rewritten and can defeat isolation;
keep experiment data/output paths relative. Even a dry-run command creates the
workspace/config copy, but does not execute scientific stages.

The guard conservatively hashes `data/`, `models/`, `reports/`, configured path
directories, and existing configured files. Hashing large downloads costs I/O.
Changing another workflow's outputs can invalidate an earlier checkpoint;
this is intentional fail-closed behavior. Do not run concurrent workflows in
one workspace. Handled failures save completed-step state; an abrupt process
kill may leave no compatible checkpoint. There is no unsafe force-resume flag.
Starting the baseline after acquisition requires a compatible `--resume`.
Combining `--refresh-catalog` with `--resume` is rejected; a refreshed catalog
belongs in a new experiment.

FAP null caches use content-addressed filenames incorporating light-curve
SHA-256, target, BLS settings, shuffle method, seed, draw count, minimum roll
fraction, and runtime. A sidecar verifies the cache checksum and iteration
coverage. Legacy caches remain on disk but are not silently reused. Only
`independent_segment_circular_shift` is supported; the roll fraction must be
between 0 and 0.5. New null runs do not overwrite the archived science unless
you explicitly run the legacy workflow against its original output paths.

## 2. Offline demo

```bash
python -m src.cli demo --output runs/demo
```

The command generates a deterministic 30-day synthetic light curve (seed 42),
with a 3-day box transit, epoch 1 day, duration 4 hours, and 1% depth. It runs
detrending and BLS, then checks top-ranked period recovery within 1%.
`expected.json` records the known truth and pass/fail result. This is a software
demonstration, not a recovered real planet or a performance benchmark.

No downloads or model training are needed. Omit `--output` for a unique folder
under `runs/`. Explicit output folders must not already exist; choose another
folder for a repeat run. A failed operation may leave partial files; never
treat a directory's existence as proof of completion.

## 3. Your CSV, FITS, or Kepler target

```bash
python -m src.cli analyze --input runs/demo/input.csv --time-system relative --output runs/csv-example
python -m src.cli analyze --input your-kepler-lightcurve.fits --output runs/fits-example
python -m src.cli analyze --kic 11904151 --max-products 1 --output runs/kic-example
```

The KIC example contacts MAST through Lightkurve and downloads one Kepler
long-cadence product. Up to four products are supported. It does not scan the
whole mission or perform Gaia/TESS validation. Archive availability is external
state; the automated tests use mocked downloads rather than depending on MAST.

CSV columns default to `time`, `flux`, `flux_err`; override them using
`--time-column`, `--flux-column`, and `--error-column`. `--time-system` is
required for CSV: `relative`, `bkjd`, `btjd`, or `bjd`. Use `--time-unit seconds`
when necessary; all computations then use days. The time-system flag labels
the coordinate, **not** a conversion between UTC/TDB or barycentric frames.
Optional `quality` retains only zero flags. Optional `segment` separates
products for detrending.

FITS input reads binary table extension 1, defaulting to `TIME`,
`PDCSAP_FLUX`, and `PDCSAP_FLUX_ERR`. The time column/header must declare days
or seconds. Kepler's `BJD - 2454833` time-column label is also supported and
checked against the header reference. `TIMEZERO` and `BJDREFI + BJDREFF` are
applied when present, and `TIMESYS` is recorded.
With no BJD reference, the report preserves the native day coordinate without
claiming a barycentric conversion. Other table layouts must be converted to
the documented CSV format first.

At least 100 finite, quality-accepted samples are required. Flux must have a
positive median; magnitudes are unsupported. Retained uncertainties must be
positive, and duplicate timestamps are rejected. Nonfinite/quality removal is
counted. Detrending is segment-aware with an odd sample window (default 401).
Use `--window`, `--min-period`, and `--max-period` deliberately; the observed
time baseline must exceed the maximum searched period. Transit durations are
1, 2, 4, and 8 hours subject to the minimum-period constraint.

### Optional trusted RF model

RF scoring is **off by default**. Existing published metadata alone is not a
compatible workbench model. Do not fabricate a manifest for a model trained
with different preprocessing merely to bypass the compatibility check.

```bash
python -m src.cli analyze --input photometry.csv --time-system bkjd --mission Kepler --model trusted.joblib --model-manifest trusted.json --trust-model
```

The manifest must declare `sha256` of the model, exact ordered `features` from
`src.model.features.FEATURE_COLUMNS`, `mission: "Kepler"`,
`preprocessing: "sxs-workbench-v1"`, matching `window`, and
`period_domain_days` enclosing the search. The model must be a binary fitted
Random Forest (directly or as the final step of a sklearn pipeline) with the
expected feature count. A matching manifest describes
compatibility; it does not prove scientific validity. Joblib/pickle loading can
execute arbitrary code: only use your own or independently trusted files.
The output `rf_review_score` is uncalibrated and not a planetary probability.

## 4. Offline HTML report

Demo and single-target analysis write `report.html` automatically. Open it in
a browser. To rebuild it from that run's saved data:

```bash
python -m src.cli report --run-dir runs/demo
```

It contains before/after light curves, the BLS periodogram, folded photometry,
candidate rows, optional RF scores, odd/even and secondary checks, and input /
runtime provenance. Its SVG graphics are embedded; no CDN or JavaScript is
needed. The report rebuild replaces only the report and screening-check file.
FAP, Gaia, TESS, and physical transit fitting are explicitly marked not run.
These exploratory checks do not reproduce the full independent validation.

Primary artifacts: `input.csv`, `processed.csv`, `candidates.csv`, `run.json`,
`screening_checks.json`, and `report.html`. Input-coordinate epochs are in
`transit_time_input_days`; the internal legacy `transit_time_bkjd` field in this
workbench is relative to the recorded input origin, not an absolute BKJD claim.

## 5. Transit injection–recovery

```bash
python -m src.cli inject --periods 1.5 3 6 --depths 0.001 0.005 --repeats 5 --output runs/injections
python -m src.cli inject --input runs/demo/input.csv --time-system relative --periods 3 --depths 0.005 --repeats 5
```

With no input, the baseline is seeded synthetic noise plus a slow trend.
Injections multiply the raw flux before a fresh detrending pass. `batman`
uses a central circular orbit, solar mass/radius, quadratic limb darkening
`[0.3, 0.2]`, and seven-times supersampling at the median cadence.
Depth values mean `(Rp/Rstar)^2`, not the exact limb-darkened central depth.
Uncertainties are held fixed; irregular exposure durations are not modeled.

Recovery requires a top-five BLS proposal within 1% of the injected period,
epoch agreement within half its fitted duration, and S/N at least 7 (adjustable
with `--minimum-snr`). Harmonics are excluded. Each trial records an uninjected
control's match to the same ephemeris; existing signals can inflate recovery.
The default search domain is 0.5–8 days.

Outputs include `injection_trials.csv`, `completeness.csv`, `completeness.svg`,
`control_candidates.csv`, `experiment.json`, and `report.html`.
Results are conditional on the input curve and randomized epochs—not stellar
population completeness, occurrence rates, RF performance, or independent
noise realizations. This is a new experiment, not a revision to archived recall.
For the methodological context, see [Kepler simulated data products](https://exoplanetarchive.ipac.caltech.edu/docs/KeplerSimulated.html).

## 6. Independent RF evaluation

```bash
python -m src.cli evaluate --demo --trees 20 --bootstrap 100 --output runs/evaluation-demo
python -m src.cli evaluate --input data/scaleup/processed/ml_candidate_metadata.csv --outer-folds 5 --inner-folds 3 --output runs/evaluation
```

The demo uses synthetic **feature vectors**, not physical photometry or a
scientific benchmark. Real input requires unique `sample_id`, nonmissing
`target_id`, binary `label`, and all 13 feature columns. Features must have the
same meaning as the existing metadata. Both classes must be present in every
training/validation split; insufficient groups produce an error.

Nested `StratifiedGroupKFold` holds each target entirely in one outer fold.
Only inner out-of-fold predictions select RF minimum leaf size (1 or 4) and
the threshold maximizing precision while achieving at least 90% inner recall.
Imputation is fitted within training folds. The outer fold never selects the
threshold or hyperparameters, and the chosen operating point is not guaranteed
to achieve 90% outer recall. No new production model is installed.

The report gives pooled outer candidate precision/recall/FPR and 95% percentile
intervals from resampling whole targets with replacement (default 500 draws).
Undefined ratios are omitted from interval draws and valid counts are reported.
These intervals condition on fixed outer predictions; they do **not** include
retraining variability or correct every selection bias. This is RF-only, not a
CNN reevaluation, a new external cohort, or planet-level end-to-end recovery.
See [nested validation guidance](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html).

Outputs: `input_metadata.csv`, `input_provenance.json`, `outer_predictions.csv`,
`evaluation.json` (including all split assignments and choices), `metrics.csv`,
and `report.html`. Never replace archived benchmark files with these outputs.
