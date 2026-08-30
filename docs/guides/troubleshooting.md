# Troubleshooting

## The command imports slowly

The unified CLI loads scientific modules for all workflows. TensorFlow,
Lightkurve, and remote-service helpers can make first import slower than a small
utility command. Wait for the process and use the supported Python versions.

## `No module named pytest` or another missing package

Confirm that the virtual environment is active and install the intended
profile:

```bash
python -m pip install -r requirements.txt
python -m pip check
```

`python --version` should report 3.11 or 3.12.

## Lightkurve warns about `oktopus`

The optional `tpfmodel` warning is not by itself a test failure. Check the final
pytest summary and the code path you intend to use. Do not suppress unrelated
errors merely because this warning also appears.

## MAST download is partial or corrupt

- keep acquisition serial where the provided config sets `workers: 1`;
- remove only the exact corrupt cached product after verifying its path;
- use `--resume` only when its content checkpoint still matches; manual cache
  changes invalidate it, so restart in a new workspace when required; and
- preserve the manifest/error record for provenance.

## A resumed stage is rejected

SXS checks a content fingerprint before its prerequisite artifacts. Config,
runtime/source changes, changed files, and legacy/missing checkpoints are
rejected. Do not create dummy checkpoint files. Start a new isolated workspace
for changed inputs; see [Analysis Workbench](workbench.md).

## The production model binary is missing

Large model binaries are intentionally untracked and are not included in the
current release bundles or container. Reproduce scale-up training in a separate
checkout, without `--resume` on the first run. Never substitute a differently
trained file under the expected name.

## Validation external queries fail

Run stages separately. Complete `fap` and `vetting`, then retry `crossmatch`
when Gaia/TESS/ExoFOP services are available. The output must record unavailable
evidence; do not convert a network failure into a pass.

## Documentation build fails

```bash
python -m pip install -r requirements-docs.txt
python -m mkdocs build --strict
```

Strict mode treats broken navigation, invalid configuration, and documentation
warnings as failures. Fix the source rather than disabling strict validation.

## Still blocked

Open a focused issue with the release, operating system, Python version,
command, configuration path, smallest relevant log excerpt, and whether the
failure is deterministic. Do not attach credentials, tokens, or private data.
