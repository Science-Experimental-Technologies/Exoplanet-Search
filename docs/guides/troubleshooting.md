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
- rerun with the same config and `--resume`; and
- preserve the manifest/error record for provenance.

## A resumed stage is rejected

SXS checks required prerequisite artifacts. Confirm that the config points to
the correct dataset and that required files are nonempty. Do not create dummy
files to satisfy the contract.

## The production model binary is missing

Large model binaries are intentionally untracked. Reproduce scale-up training
or obtain the exact authorized release artifact associated with the selection
metadata. Never substitute a differently trained file under the expected name.

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
