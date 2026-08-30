# Interpreting Results

## Detection, ranking, and validation are different

| Layer | Question answered | Does not mean |
|---|---|---|
| BLS peak | Is there a strong periodic box-like signal in this grid? | The signal is planetary |
| RF/CNN score | Does this peak resemble prioritized training examples? | Calibrated planet probability |
| Preliminary pass | Did simple shortlist checks avoid a configured failure? | Independent validation |
| Weak candidate | Did the signal avoid key failures but lack complete strong evidence? | Confirmed planet |
| Strong candidate | Did all configured evidence requirements pass? | Physical confirmation |

## Read empirical FAP correctly

`FAP = 0.01998` means that under the chosen segment-shuffle null and complete
BLS grid, 19 of 1,000 null target maxima met or exceeded the observed power;
the plus-one estimate is 20/1,001. It is conditional on this test and does not
say that the object has a 1.998% probability of being a false positive.

## Understand catalog absence

The search excludes known catalog history before signal analysis. A later
non-match only means no matching row was found in the queried tables at that
time. Catalogs have coverage, naming, timing, and sensitivity limits. Absence
does not establish novelty.

## Understand external evidence

- a clean Gaia scene reduces one contamination concern but does not eliminate
  unresolved blends;
- no TESS match may reflect non-observation, cadence, dilution, or sensitivity;
- an ExoFOP non-match is not a validation result;
- a U-shaped fit is compatible with a transit but not unique to planets; and
- a plausible radius depends on stellar parameters and model assumptions.

## Report SXS outputs responsibly

Use precise labels such as:

> SXS identified an unconfirmed weak transit-like signal requiring independent
> follow-up.

Do not write:

> SXS discovered a planet.

Every shared table or figure should retain target identifier, candidate label,
config/release version, and the unconfirmed-candidate warning. Publications
must also follow the [citation](../project/citation.md) and
[license](../project/license-security.md) requirements.
