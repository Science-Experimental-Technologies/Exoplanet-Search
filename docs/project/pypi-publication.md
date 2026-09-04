# PyPI publication

The project name `scix-exoplanet-search` was not registered on PyPI when checked
on 2026-09-04. The repository contains a manual, approval-gated trusted
publishing workflow, but no PyPI publication is claimed until the public package
page resolves and an anonymous installation succeeds.

## Trusted publisher configuration

Configure pending publishers in both package indexes before running the
workflow. Use these exact values:

| Field | Value |
|---|---|
| PyPI project | `scix-exoplanet-search` |
| GitHub owner | `Science-Experimental-Technologies` |
| Repository | `Exoplanet-Search` |
| Workflow | `publish-pypi.yml` |
| PyPI environment | `pypi` |
| TestPyPI environment | `testpypi` |

Create matching GitHub environments and require a human deployment approval for
the production `pypi` environment. Trusted publishing uses short-lived OpenID
Connect credentials; do not add a long-lived PyPI token to repository secrets.

## Publication sequence

1. Register the pending trusted publisher on TestPyPI and create the
   `testpypi` GitHub environment.
2. Run **Publish Python package** with tag `v1.3.0`, target `testpypi`, and the
   confirmation checkbox selected.
3. Install the exact version anonymously from TestPyPI in a clean environment
   and run `sxs --help` and `sxs demo`.
4. Register the production pending publisher and create the protected `pypi`
   environment.
5. Run the same workflow with target `pypi`, approve the deployment, then repeat
   the anonymous installation test from PyPI.

The workflow downloads the already published GitHub release wheel, verifies it
against `SHA256SUMS.txt`, checks its layout and CLI, and passes that same file to
the package index. It does not rebuild a different artifact under the same
version. Package-index versions cannot be overwritten; publish a new semantic
version to correct a released distribution.

Official guidance: [PyPA trusted publishing with GitHub Actions](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/).
