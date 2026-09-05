# Dependency update review — 2026-09-04

This review covers the first Dependabot batch opened after automated dependency
maintenance was enabled. Updates were evaluated against the declared Python
3.11/3.12 support range, pull-request CI, the full container build, and the
project's reproducibility requirements.

| PR | Proposed update | Decision | Evidence |
|---:|---|---|---|
| 3 | Python container 3.11 → 3.14 | Reject | Outside `requires-python >=3.11,<3.13`; container build failed |
| 4 | `anchore/sbom-action` 0.24.0 → 0.24.2 | Accept | Patch update; container workflow passed |
| 6 | `actions/configure-pages` 5 → 6 | Accept | Node 24 maintenance line; documentation deployment passed |
| 7 | `softprops/action-gh-release` 2 → 3 | Accept | Supported Node 24 line; no release-input change |
| 8 | `actions/upload-pages-artifact` 4 → 5 | Accept | Documentation workflow passed |
| 9 | setuptools 75.8.2 → 84.0.0 | Accept | Python matrix and full container passed |
| 10 | pandas 2.2.3 → 3.0.5 | Reject | Major behavioral update; full container build failed |
| 11 | Astroquery 0.4.10 → 0.4.11 | Accept | Python matrix and full container passed |
| 12 | SciPy 1.14.1 → 1.17.1 | Accept | Python matrix and full container passed |
| 13 | Lightkurve 2.5.1 → 2.6.0 | Accept | Python matrix and full container passed |
| 17 | Python container 3.11 → 3.12 | Accept | Within the declared support range; full container workflow passed |
| 18 | pandas 2.2.3 → 2.3.3 | Accept | All six Python/OS matrix jobs passed |
| 19 | `actions/deploy-pages` 4 → 5 | Accept | Documentation workflow passed; current maintained action line |
| 20 | grouped PyPI updates | Split | Accept `pypdf` 6.10.0 → 6.16.1; defer major `pyarrow` 19 → 23, `pytest` 8 → 9, and `mlflow` 2 → 3 until scientific regression benchmarks are rerun |

Accepted changes were applied together to the default branch and require a new
combined CI, documentation, CodeQL, clean-wheel, and full-container result.
They do not alter the frozen v1.3.0 tag, Zenodo archive, or recorded scientific
metrics. The next numbered software release will carry the updated dependency
set after that combined validation.

Dependabot is configured not to reopen pandas, PyArrow, pytest, or MLflow major
updates, or Python base-image updates at 3.13 and above. Those constraints must
be revisited intentionally when the supported Python matrix expands or the
scientific regression suite is rerun against a new major dependency line.

## Dependency-review workflow prerequisite

The dependency-review job initially failed uniformly while CI, CodeQL,
documentation, and the relevant container jobs passed. The repository dependency
graph and automatic dependency submission were enabled on 2026-09-04, and the
workflow was advanced to `actions/dependency-review-action@v5`. Subsequent pull
requests can now use the dependency graph for vulnerability review.

Dependency-graph availability is a repository setting, not evidence that an
individual dependency update is safe. The accept/reject decisions above use the
actual build outcomes and compatibility contract; vulnerability review must be
rerun after the graph is enabled.
