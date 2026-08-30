# Workbench implementation and verification

This records the six requested additions implemented after commit `131bfeb`.
They are current working-tree features, not a published release. The complete
[usage guide](../docs/guides/workbench.md) documents commands and limitations.

## Delivered capabilities

| Addition | Implementation | Verification |
|---|---|---|
| Compatible cache/resume | Content-addressed FAP cache; checksum sidecars; config/runtime/artifact checkpoints; isolated workspaces | Changed seed creates a new null cache; old cache bytes remain intact; stale resume is rejected |
| Offline demo | Seeded synthetic photometry generated locally; known truth and recovery check | A 3-day injected box signal is recovered within the declared 1% tolerance |
| Single-target/file analysis | CSV units/time labels, Kepler FITS reference handling, KIC acquisition, optional explicitly trusted RF | Synthetic CSV and a real local Kepler FITS completed; KIC acquisition contract is mocked in tests |
| HTML reports | Embedded SVG light curves, periodogram, folded signal, checks, and provenance | Browser-rendered report visually inspected; altered report inputs rejected |
| Injection–recovery | Flux-level batman injection before detrending; random epochs; uninjected control | 30 trials completed; exact-period/epoch/SNR rules and harmonic rejection tested |
| Independent model evaluation | Nested target-grouped RF selection and group-bootstrap intervals | Outer/inner group separation and predictions verified; evaluation completed on existing scaled feature metadata |

## Representative command runs

Local verification used fresh folders under `runs/`, which are intentionally
ignored by Git. Repeating these commands requires new output folder names.

```bash
python -m src.cli demo --output runs/verification-demo
python -m src.cli analyze --input runs/verification-demo/input.csv --time-system relative --output runs/verification-csv
python -m src.cli inject --periods 1.5 3 6 --depths 0.001 0.005 --repeats 5 --output runs/verification-injection
python -m src.cli evaluate --input data/scaleup/processed/ml_candidate_metadata.csv --outer-folds 5 --inner-folds 3 --trees 100 --bootstrap 500 --output runs/verification-evaluation
```

A real local Kepler FITS for KIC 10019643 was analyzed separately using
`analyze --input ... --output runs/verification-fits`. This tested the real
`BJD - 2454833` column-unit convention; no new mission download was needed.
That single-product smoke test is not an independent candidate-validation result.

## New RF evaluation: separate from archived benchmarks

The input contains 2,227 candidate rows: 227 positive and 2,000 negative.
RF evaluation used five outer folds, three inner folds, 100 trees, minimum
leaf sizes 1/4, target inner recall 0.90, seed 42, and 500 target-bootstrap draws.
Hyperparameters and thresholds were chosen only from inner out-of-fold scores.

| Candidate metric | New estimate | Conditional 95% interval |
|---|---:|---:|
| Precision | 0.401980 | 0.347461–0.455926 |
| Recall | 0.894273 | 0.853929–0.930130 |
| False-positive rate | 0.151000 | 0.128724–0.173989 |

The confusion counts are TP 203, FP 302, FN 24, TN 1,698. Intervals resample
whole targets with fixed outer-fold predictions; they do not include model
retraining uncertainty. This is an RF candidate-vetting estimate, not
end-to-end planet recovery, a new external population, or a CNN result.

The original RF v2 operating-point metrics and the 0-strong/1-weak/19-likely-FP
outcome are unchanged. Do not replace their values with this distinct protocol.
The local evaluation directory records input hashes, source/runtime identity,
outer predictions, every fold's target membership, and threshold decisions.

## Injection experiment interpretation

With synthetic noise, the tested 1.5- and 3-day cells recovered 5/5 trials at
each nominal depth (0.001 and 0.005). The 6-day cells each recovered 2/5.
There were no control matches at the injected ephemerides in this run.
These small conditional samples are software/method demonstrations, not a
population completeness claim. Timing, period-grid resolution, noise, and
the recovery rule all affect these fractions; no tuning to force full recovery
was performed.

## Boundaries and release status

Final local checks: **65 non-network tests passed, 1 network test deselected**;
the strict MkDocs build passed; **31 generated pages / 2,444 local references**
had no broken references; **59 Markdown documents** passed the offline prose /
link checks. Recorded CLI previews match the command output and `pip check`
reported no broken dependencies. A clean-built wheel passed isolated CLI help.
Third-party deprecation and optional-module warnings remain; they are not
scientific validation failures. These are local checks, not a claim that the
uncommitted revision has passed hosted CI.

- Full legacy acquisition, RF/CNN retraining, the 250-target search, and the
  archived 14,000-realization null experiment were not rerun.
- Tests do not certify every MAST response or every FITS layout. Live KIC
  acquisition remains dependent on the remote archive.
- Model compatibility requires a truthful manifest and explicit trust; no
  bundled or newly installed production model is claimed.
- New generated results stay in isolated local folders. Existing tracked
  scientific data, archived metric files, and PDF assets were not overwritten.
- No license changes, DOI registration, PDF replacement, release, or push is
  performed as part of this implementation.
