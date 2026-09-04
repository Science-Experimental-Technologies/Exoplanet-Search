# Zenodo archive and DOI

SXS v1.3.0 is preserved as a public Zenodo software record. Use the version
DOI when citing that exact release and the concept DOI when referring to the
evolving software across versions.

| Identifier | Value |
|---|---|
| Version DOI | [`10.5281/zenodo.22294859`](https://doi.org/10.5281/zenodo.22294859) |
| Concept DOI | [`10.5281/zenodo.22294858`](https://doi.org/10.5281/zenodo.22294858) |
| Zenodo record | [`zenodo.org/records/22294859`](https://zenodo.org/records/22294859) |
| GitHub release | [`v1.3.0`](https://github.com/Science-Experimental-Technologies/Exoplanet-Search/releases/tag/v1.3.0) |
| Archived commit | `f2641544c4192bf0bc220e630fc299c9bb50be13` |
| Publication date | 2026-09-04 |

## Archived object

Zenodo's GitHub integration preserved
`Science-Experimental-Technologies/Exoplanet-Search-v1.3.0.zip` (21,249,195
bytes; MD5 `cce95b5e6321cd77c83f6997c090c743`). The archive is the tagged repository
source. Platform bundles, the standalone wheel, checksums, and the preprint are
distributed separately on the GitHub release page.

The record identifies Rasya Andrean as creator, Science Experimental
Technologies as affiliation, software version v1.3.0, the tagged repository as
a related work, and the project repository as the code repository. Its notes
record independent funding by Rasya Andrean and Urus Foundation.

The archived software is governed by the custom
[SXS Source-Available Commercial License 1.0](https://github.com/Science-Experimental-Technologies/Exoplanet-Search/blob/v1.3.0/LICENSE),
not a Creative Commons software license. Zenodo record metadata are CC0 under
Zenodo policy; that separate metadata rule does not replace the license attached
to the archived files.

## Release procedure

For a future numbered release:

1. update and validate `CITATION.cff`, version metadata, and the changelog;
2. pass CI, documentation, CodeQL, container, and release checks before tagging;
3. create a new immutable semantic-version tag rather than moving an old tag;
4. verify the automatically archived creator, version, date, file, related
   repository, funding note, copyright, and custom software license; and
5. add the new version DOI to release-specific citation material while keeping
   the concept DOI stable.

Zenodo defaults non-dataset deposits to CC BY when it cannot map a custom
software license. Therefore, every automatically created SXS record must be
checked and, when necessary, changed to the custom SXS license before the
archive is treated as fully verified.

Official references: [GitHub integration](https://help.zenodo.org/docs/github/),
[software metadata](https://help.zenodo.org/docs/github/describe-software/), and
[custom licenses](https://help.zenodo.org/docs/deposit/describe-records/licenses/).
