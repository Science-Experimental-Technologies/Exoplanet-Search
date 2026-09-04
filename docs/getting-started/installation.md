# Installation

SXS is Python scientific software. It has no standalone graphical interface and
does not need to be installed system-wide.

To use a prebuilt scientific environment instead of installing Python packages,
see the [GHCR container guide](container.md).

## Requirements

- Python 3.11 or 3.12
- Git for a repository checkout, or one platform bundle from the
  [v1.3.0 release](https://github.com/Science-Experimental-Technologies/Exoplanet-Search/releases/tag/v1.3.0)
- Enough disk space for the chosen public mission products
- Network access for MAST and catalog acquisition

Windows received the full workstation research validation. The CI matrix checks
the deterministic core and installed wheel on Ubuntu, Windows, and macOS with
Python 3.11 and 3.12. This does not imply that the full research/CNN workflow has
been scientifically reproduced on all platforms. See the latest CI results.

## Choose a dependency profile

| File | Intended use |
|---|---|
| `requirements-core.txt` | Acquisition, preprocessing, BLS, independent validation, tests, and CI |
| `requirements.txt` | Complete environment including RF/CNN training, TensorFlow, and MLflow |
| `requirements-ml.txt` | Compatibility alias for the complete environment |
| `requirements-docs.txt` | Documentation website and publication/PDF utilities |

Use the complete environment for an end-to-end research reproduction.

## Install from Git

=== "Windows PowerShell"

    ```powershell
    git clone https://github.com/Science-Experimental-Technologies/Exoplanet-Search.git
    cd Exoplanet-Search
    py -3.11 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    ```

=== "macOS"

    ```bash
    git clone https://github.com/Science-Experimental-Technologies/Exoplanet-Search.git
    cd Exoplanet-Search
    python3.11 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    ```

=== "Linux"

    ```bash
    git clone https://github.com/Science-Experimental-Technologies/Exoplanet-Search.git
    cd Exoplanet-Search
    python3.11 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    ```

## Install from a release bundle

Download the archive for your platform, extract it, and open
`PLATFORM_INSTALL.md` inside the extracted `sxs-1.3.0` directory. All platform
archives contain the same source and scientific record; only the installation
guide differs.

Verify the archive checksum before use:

=== "Windows PowerShell"

    ```powershell
    Get-FileHash .\sxs-v1.3.0-windows-python.zip -Algorithm SHA256
    ```

=== "macOS / Linux"

    ```bash
    shasum -a 256 sxs-v1.3.0-*-python.*
    ```

Compare the result with `SHA256SUMS.txt` on the release page.

## Verify the environment

```bash
python -m pip check
python -m pytest -m "not network"
python -m src.cli baseline --config configs/base.yaml --dry-run
```

The command above uses `-m "not network"` and deselects the opt-in network
test. Test counts are revision-specific. Warnings from optional Lightkurve components do not by
themselves indicate a failed SXS test.

## Optional network test

The MAST smoke test performs a real external query and is deliberately opt-in.

=== "Windows PowerShell"

    ```powershell
    $env:SXS_RUN_NETWORK_TESTS = "1"
    python -m pytest -m network tests/test_mast_client_network.py
    ```

=== "macOS / Linux"

    ```bash
    SXS_RUN_NETWORK_TESTS=1 python -m pytest -m network tests/test_mast_client_network.py
    ```

Continue with the [quickstart](quickstart.md) after these checks pass.

## Standalone wheel and installed command

The release wheel installs the `sxs` command and core dependencies without a
source checkout. In a Python 3.11/3.12 virtual environment, download the wheel
and checksum manifest from the release, verify its checksum, then run:

```bash
python -m pip install scix_exoplanet_search-1.3.0-py3-none-any.whl
sxs demo --output demo
sxs baseline --workspace research-a --dry-run
```

Open `demo/report.html`. YAML defaults are included and copied into the selected
workspace. Observations, catalogs, and trained models are not bundled in the
wheel. Full model training additionally requires `requirements.txt` from the
matching source bundle. From a checkout, `python -m pip install .` provides the
same installed command. The approval-gated [PyPI publication procedure](../project/pypi-publication.md)
is prepared, but use the GitHub release wheel until a public package page and
anonymous installation have been verified.
