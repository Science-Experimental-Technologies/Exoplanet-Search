# Python API Reference

The stable public interface is the CLI. The functions below are useful for
testing and research extensions, but module-level APIs may evolve between
releases.

## Orchestration

```python
from src.pipeline import run_pipeline

record = run_pipeline(
    "configs/base.yaml",
    from_stage=0,
    to_stage=3,
    resume=True,
    dry_run=False,
)
```

`run_pipeline` returns a structured dictionary and raises `PipelineError` when
a stage cannot safely complete. `stage_complete(stage, config)` evaluates the
minimum baseline acceptance contract.

## Preprocessing

```python
from src.preprocess.clean import clean_light_curve_arrays
from src.preprocess.detrend import detrend_light_curve
```

Cleaning functions return tabular light-curve data and statistics. Detrending
expects the configured column/schema contract and preserves interpolation
metadata.

## BLS detection

```python
from src.detect.bls_search import (
    build_period_grid,
    evaluate_recovery,
    search_light_curve,
    select_distinct_peaks,
)
```

- `build_period_grid` constructs the oversampled search grid.
- `search_light_curve` returns `(candidates, diagnostics)` for one processed
  curve; it requires at least 100 observed samples and a time baseline longer
  than the maximum search period.
- `select_distinct_peaks` enforces fractional period separation.
- `evaluate_recovery` compares proposals with eligible catalog planets.

## Candidate features

```python
from src.model.features import extract_candidate_features, fold_light_curve
```

`extract_candidate_features` returns the fixed 13-feature mapping.
`fold_light_curve(..., bins=512)` returns a normalized `float32` view.

## Scale-up and search

```python
from src.scaleup.run_scaleup import run_scaleup
from src.candidate_search.run_search import run_candidate_search_workflow
```

Both consume a config path and support `resume=True`. They write their accepted
artifact sets and return structured run records.

## Independent validation

```python
from src.independent_validation.fap import run_fap
from src.independent_validation.metrics import run_photometric_vetting
from src.independent_validation.crossmatch import run_crossmatches
from src.independent_validation.run_validation import run_independent_validation
```

Use the orchestrator unless you are writing a controlled test or diagnosing an
individual stage. Direct calls still require the same config and input schema.

## Compatibility guidance

- use keyword arguments for optional parameters;
- pin the SXS release/commit in research software;
- do not rely on private names beginning with `_`;
- validate DataFrame columns before calling a stage directly; and
- preserve candidate labels and scientific disclaimers in downstream APIs.
