# Release Operations: CI, Metadata, and DOI

Status reviewed: 2026-08-30. This is an operational snapshot, not a claim that
publication, DOI registration, or a new release has been completed.

## Published release and version meaning

The current published release is [v1.1.0](https://github.com/Science-Experimental-Technologies/Exoplanet-Search/releases/tag/v1.1.0).
Public releases started with v1.0.0. Internal research labels “v1” and “v2”
describe benchmark generations, not public software version numbers.

The v1.1.0 release contains:

- `sxs-v1.1.0-windows-python.zip`
- `sxs-v1.1.0-macos-python.tar.gz`
- `sxs-v1.1.0-linux-python.tar.gz`
- `SHA256SUMS.txt`
- `sxs_preprint_v1.0.0.pdf`

The platform bundles contain Python source, not standalone native executables.
Their `PLATFORM_INSTALL.md` files provide platform-specific setup instructions.
They do not include all downloaded light curves or fitted model binaries.
The PDF is a historical research artifact; its filename version is independent
of the software packaging release. See [publication status and corrections](../docs/project/publication.md)
before reusing it as a manuscript. It is not evidence of journal acceptance.

Current-branch corrections do not modify published tags or release assets.
See [CHANGELOG](../CHANGELOG.md) for the distinction between released and
unreleased changes.

## Continuous integration

The [core CI workflow](../.github/workflows/ci.yml) runs on Ubuntu with Python
3.11 and 3.12. It installs `requirements-core.txt`, checks dependencies, runs
non-network tests, checks recorded CLI previews and repository documentation,
and builds a wheel for an isolated CLI smoke check.

The [documentation workflow](../.github/workflows/docs.yml) builds MkDocs in
strict mode, checks generated local links and anchors, and deploys GitHub Pages.
The [container workflow](../.github/workflows/container.yml) separately builds
the full-dependency Linux image and runs smoke tests and deterministic tests.

These checks are not a new full scientific reproduction. They do not rerun the
complete acquisition, training, search, or empirical null simulations.
A workflow definition alone is not proof of a successful hosted run; inspect
the [Actions history](https://github.com/Science-Experimental-Technologies/Exoplanet-Search/actions)
for the revision being used.

Historical infrastructure evidence: [run 33229091278](https://github.com/Science-Experimental-Technologies/Exoplanet-Search/actions/runs/33229091278)
passed the original Python matrix. Its 35-test count describes that revision,
not the current test suite. The original Python 3.12 compatibility fix added
pinned setuptools support for batman's use of `distutils`.

## Repository metadata and container access

The repository About description, topics, and
[documentation website](https://science-experimental-technologies.github.io/Exoplanet-Search/)
are configured. Project contact: **scix.official@gmail.com**.

The workflow has published `ghcr.io/science-experimental-technologies/exoplanet-search:main`.
Anonymous access remained unauthorized at the audit checkpoint. Publication
of an image does not guarantee public pull access: an authorized package owner
must inspect package visibility and grant public access if desired.
See the [container guide](../docs/getting-started/container.md).

## Zenodo DOI: owner action pending

No DOI is recorded in the current citation metadata. Do not display a DOI badge
or claim archival completion until a public record is verified.

1. Follow Zenodo's [repository integration instructions](https://help.zenodo.org/docs/github/).
   Sign in with an account authorized to connect this GitHub repository.
2. Enable the repository before publishing the next intentionally versioned
   release. Do not delete, overwrite, or retag v1.0.0 or v1.1.0 to trigger archiving.
   Alternatively, use Zenodo's documented manual software-upload workflow.
3. Follow the [GitHub release archiving guide](https://help.zenodo.org/docs/github/archive-software/github-upload/),
   wait for processing, and inspect the archived files, authors, version, and license.
4. Add the assigned release DOI to `CITATION.cff` and the appropriate DOI badge
   only after verifying the public record. Keep software-release and manuscript
   identifiers separate.
5. Commit metadata corrections forward without rewriting published history.

Before any future release, verify the version, changelog, citation metadata,
platform bundle contents, license, checksums, and applicable CI results.
