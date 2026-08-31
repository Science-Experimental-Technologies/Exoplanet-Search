# Frequently Asked Questions

## Did SXS discover an exoplanet?

No. Independent validation found no strong candidate. KIC 8300900-r1 is a weak,
unconfirmed transit-like signal with FAP 0.01998 and no supporting TESS period
match.

## Is an RF score a planet probability?

No. It is a review-prioritization score learned from the constructed benchmark.

## Why use both BLS and machine learning?

BLS proposes periodic box-like signals; machine learning reduces the review
load among those proposals. The model cannot recover planets absent from the
BLS proposal set.

## Why is validation independent of the model?

Reusing the ranking score as validation evidence would blur selection and
confirmation. The final rules use FAP, photometric/physical tests, and external
evidence instead.

## Why is the best signal only weak?

Its FAP is 0.01998, above the 0.01 strong threshold, and it lacks the required
TESS period support. Avoiding other key failures is insufficient for `strong`.

## Can I run SXS on another mission?

The architecture can be extended, but supplied acquisition, configs,
thresholds, and evidence are Kepler-centered. A new mission requires a new
validated data adapter, benchmark, configuration, and scientific report.

## Can I change the period range or thresholds?

Yes for a new experiment. Use a copied config and new artifact paths. Do not
describe changed results as the published SXS benchmark.

## Why are model binaries missing from Git?

Large generated binaries are intentionally untracked. The repository tracks
model-selection metadata and evidence. Reproduce training: the current source
bundles and container do not distribute fitted model binaries. A future model
download must be explicitly versioned and verified against its selection metadata.

## Which platform should I use?

Windows has the complete workstation research validation. The CI matrix checks
the deterministic core and installed wheel on Ubuntu, Windows, and macOS.
This is not full scientific reproduction or CNN validation on every platform.

## Is SXS open source?

Current revisions are source-available, not OSI-approved open source. Read the
[license page](project/license-security.md).

## How do I cite it?

Use the exact release in `CITATION.cff`, add the required creator attribution,
and cite upstream mission data/software. See [Citation](project/citation.md).

## Where is the authoritative complete research narrative?

The versioned
[research report](https://github.com/Science-Experimental-Technologies/Exoplanet-Search/blob/main/reports/research_report.md)
is authoritative for the full methodology, results, and limitations.
