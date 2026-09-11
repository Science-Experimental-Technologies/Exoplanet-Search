# PyPI publication

Version 1.3.0 is published on both package indexes:

- [PyPI production package](https://pypi.org/project/scix-exoplanet-search/1.3.0/)
- [TestPyPI verification package](https://test.pypi.org/project/scix-exoplanet-search/1.3.0/)

The production page, anonymous wheel download, complete dependency installation,
installed `sxs --help`, core scientific imports, and `pip check` were verified on
2026-09-11 with Python 3.11. `pip check` reported no broken requirements.

## Trusted publisher configuration

Both indexes use GitHub Actions trusted publishing with these values:

| Field | Value |
|---|---|
| PyPI project | `scix-exoplanet-search` |
| GitHub owner | `Science-Experimental-Technologies` |
| Repository | `Exoplanet-Search` |
| Workflow | `publish-pypi.yml` |
| PyPI environment | `pypi` |
| TestPyPI environment | `testpypi` |

The matching GitHub environments exist, and the production `pypi` environment
requires deployment approval. Trusted publishing uses short-lived OpenID Connect
credentials; no long-lived PyPI token is stored in repository secrets.

## Verified publication sequence

1. The TestPyPI trusted publisher uploaded the release in
   [workflow run 2](https://github.com/Science-Experimental-Technologies/Exoplanet-Search/actions/runs/34487604382).
2. The TestPyPI wheel was installed anonymously and its package version and
   `sxs` console entry point were verified.
3. The production trusted publisher uploaded the identical release wheel after
   environment approval in
   [workflow run 3](https://github.com/Science-Experimental-Technologies/Exoplanet-Search/actions/runs/34489363948).
4. A clean production installation resolved the full dependency set, ran
   `sxs --help`, imported NumPy, SciPy, pandas, Astropy, Lightkurve,
   scikit-learn, and batman, and passed `pip check`.

The workflow downloads the already published GitHub release wheel, verifies it
against `SHA256SUMS.txt`, checks its layout and CLI, and passes that same file to
the package index. It does not rebuild a different artifact under the same
version. Package-index versions cannot be overwritten; publish a new semantic
version to correct a released distribution.

Official guidance: [PyPA trusted publishing with GitHub Actions](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/).
