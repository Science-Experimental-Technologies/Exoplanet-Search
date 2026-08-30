# Experiments

## Baseline benchmark

The fixed initial benchmark contains 20 confirmed Kepler hosts and 47 catalog
planets. Thirty-six planets fall inside the 0.5–50 day search domain. The
negative sample contains 20 unique official false-positive targets, balanced
across four deterministic assignment categories:

- not transit-like;
- stellar eclipse;
- centroid offset; and
- ephemeris contamination.

Official flags can overlap; the assignment is a sampling device rather than a
claim that the physical causes are mutually exclusive.

Candidate-level ML evaluation uses 15 exactly recovered positive peaks and 100
peaks from the 20 false-positive systems. All out-of-fold predictions are
grouped by target.

## Scaled qualification

Positive selection requires:

- a confirmed Kepler planet inside the BLS domain;
- transit S/N at least 50;
- Kepler magnitude no fainter than 15; and
- at least eight available long-cadence quarters.

This produces 371 confirmed hosts and 434 eligible planets. Negative selection
uses official false-positive KOIs with S/N at least 10 and the same magnitude
and quarter requirements. The workstation-bounded negative sample contains 400
unique targets—100 per assignment category.

Matched four-product coverage is used for both classes. Candidate construction
produces 227 recovered-planet peaks and 2,000 false-positive-system peaks across
619 target groups.

## Frozen model decision

RF v2 and a compact 1D CNN are evaluated under the prespecified review policy.
The RF operating point is `0.2211073884029602` (reported as 0.221107). The CNN
does not meet the replacement conditions because its precision is lower and
fold-level F1 is unstable. RF v2 is trained on the complete qualification set
for candidate screening; CNN remains a diagnostic baseline.

## Bounded candidate search

The deterministic sample contains 250 targets. Every target completes
four-product acquisition, preprocessing, and BLS search, producing 1,250 peaks.
RF v2 flags 151 peaks at the frozen review threshold. Of those, 110 have no
failed preliminary check. The highest-scoring 20 signals, spanning 14 unique
KICs, form the frozen queue.

## Independent audit

The audit stores 20 candidate-level views of target null distributions, each
based on 1,000 shuffles. It attempts formal photometric tests and a physical
transit fit for every candidate, records Gaia/TESS/ExoFOP availability and
errors, and reconciles the final transparent score with the category rules.

The accepted run record asserts:

- exactly 20 candidates;
- all null draws saved;
- formal photometric checks complete;
- transit models attempted;
- external queries recorded;
- categories exact;
- no confirmed claim; and
- transparent score reconciliation.

Machine-readable details are cataloged in the
[artifact reference](../reference/artifacts.md).
