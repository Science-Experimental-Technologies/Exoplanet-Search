# PyPI publication

Final version 1.4.0 is published on both package indexes:

- [PyPI production package](https://pypi.org/project/scix-exoplanet-search/1.4.0/)
- [TestPyPI verification package](https://test.pypi.org/project/scix-exoplanet-search/1.4.0/)

The production page, anonymous wheel download, complete dependency installation,
installed CLI, packaged configurations, demo, baseline dry-run, and `pip check`
were verified on 2026-09-16 with Python 3.11. `sxs doctor` passed all 13 local
checks and `pip check` reported no broken requirements.

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
   [workflow run 4](https://github.com/Science-Experimental-Technologies/Exoplanet-Search/actions/runs/35088986987).
2. The TestPyPI JSON API reported the expected wheel, version, and Python range.
   Its SHA-256 matched the GitHub Release wheel.
3. The production trusted publisher uploaded the identical release wheel after
   environment approval in
   [workflow run 5](https://github.com/Science-Experimental-Technologies/Exoplanet-Search/actions/runs/35089286710).
4. The production wheel SHA-256 was
   `7bceb7953528f00768ff418bd5c183f4df690cb14df1bbca4d254d03184d7ddc`,
   identical to the GitHub Release and TestPyPI wheels.
5. A clean production installation resolved the complete dependency set, passed
   `pip check`, reported `SXS 1.4.0`, passed `sxs doctor`, generated the demo,
   and completed a baseline dry-run.

The workflow downloads the already published GitHub release wheel, verifies it
against `SHA256SUMS.txt`, checks its layout and CLI, and passes that same file to
the package index. It does not rebuild a different artifact under the same
version. Package-index versions cannot be overwritten; publish a new semantic
version to correct a released distribution.

Official guidance: [PyPA trusted publishing with GitHub Actions](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/).
