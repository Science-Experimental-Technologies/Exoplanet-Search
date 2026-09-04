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

Accepted changes were applied together to the default branch and require a new
combined CI, documentation, CodeQL, clean-wheel, and full-container result.
They do not alter the frozen v1.3.0 tag, Zenodo archive, or recorded scientific
metrics. The next numbered software release will carry the updated dependency
set after that combined validation.

Dependabot is configured not to reopen pandas major updates or Python base-image
updates at 3.13 and above while the declared support range remains below 3.13.
Those constraints must be revisited intentionally when the project expands its
supported Python matrix.

## Dependency-review workflow prerequisite

The dependency-review job failed uniformly while CI, CodeQL, documentation, and
the relevant container jobs passed. GitHub's action reports this pattern when
the repository dependency graph is disabled. Enable **Dependency graph** under
repository security settings, then rerun the affected pull-request checks. The
workflow has also been advanced to `actions/dependency-review-action@v5`.

Dependency-graph availability is a repository setting, not evidence that an
individual dependency update is safe. The accept/reject decisions above use the
actual build outcomes and compatibility contract; vulnerability review must be
rerun after the graph is enabled.
