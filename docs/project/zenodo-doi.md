# Zenodo archive and DOI

The repository is prepared for Zenodo ingestion through `CITATION.cff`, but no
Zenodo DOI is currently claimed. A DOI must resolve publicly before it is added
to the citation file, README, manuscript, or release notes.

## Publish the first record

1. Sign in to Zenodo with the GitHub account authorized for the organization.
2. Open the Zenodo GitHub integration, synchronize repositories, and enable
   `Science-Experimental-Technologies/Exoplanet-Search`.
3. Review `CITATION.cff` before creating the next GitHub release. Do not add a
   `.zenodo.json` file unless there is a specific metadata need: Zenodo gives it
   precedence over `CITATION.cff`.
4. Create a new numbered GitHub release only after all release checks pass.
   Zenodo should archive that release automatically when the integration is
   enabled.
5. In Zenodo, verify the creator, title, description, license URL, keywords,
   funding statement, related repository, files, and publication date.
6. Publish the record. This is the action that registers the DOI and cannot be
   represented by a local placeholder.
7. Open the DOI in a logged-out browser. Only then add the DOI to
   `CITATION.cff`, the manuscript availability statement, and project pages.

## Evidence to retain

Record the concept DOI, version DOI, Zenodo record URL, archived Git commit and
tag, publication date, file checksums, and a logged-out resolution check. A
reserved or draft DOI is not described as a published archive.

Official instructions: [enable a GitHub repository](https://help.zenodo.org/docs/github/enable-repository/),
[describe software](https://help.zenodo.org/docs/github/describe-software/), and
[reserve or register a DOI](https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/).
