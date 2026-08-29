# BLS Transit-Recovery Benchmark

## Primary result

Within the configured 0.5–50.0 day search domain, BLS recovered **15 of 36 eligible confirmed planets (41.67% top-5 exact recall)** using a ±1.0% period tolerance.

Top-1 exact recall is 13/36 (36.11%). For diagnostic purposes, top-5 recall allowing 1/2× and 2× aliases is 17/36 (47.22%). The exact metric is the primary baseline.

The full validation sample has 47 planets; 11 are outside the configured period domain and are excluded from the primary denominator rather than counted as detector failures.

## Search method

- Input: preprocessing detrended flux; interpolated samples excluded.
- Period range: 0.5–50.0 days.
- Trial durations: [1.0, 2.0, 4.0, 8.0, 12.0] hours; values not shorter than the minimum period are rejected.
- Frequency oversampling: 5.0 relative to the Rayleigh resolution `1/baseline`.
- Candidate list: top 5 distinct peaks, separated by at least 1.0% in period.

## Per-planet recovery

| Host | Planet | Catalog period (d) | Eligible | Best rank | Best period (d) | Relative error | Exact match |
|---|---|---:|:---:|---:|---:|---:|:---:|
| Kepler-10 | Kepler-10 b | 0.8374907 | yes | 1 | 0.83748422 | 0.0008% | yes |
| Kepler-10 | Kepler-10 c | 45.294301 | yes | 3 | 15.095718 | 66.6719% | no |
| Kepler-22 | Kepler-22 b | 289.86388 | no | 1 | 38.686964 | 86.6534% | no |
| Kepler-7 | Kepler-7 b | 4.8854892 | yes | 1 | 4.8851068 | 0.0078% | yes |
| Kepler-8 | Kepler-8 b | 3.5224991 | yes | 1 | 3.5228313 | 0.0094% | yes |
| Kepler-9 | Kepler-9 d | 1.592851 | yes | 5 | 3.844911 | 141.3855% | no |
| Kepler-9 | Kepler-9 b | 19.23891 | yes | 1 | 19.257068 | 0.0944% | yes |
| Kepler-9 | Kepler-9 c | 38.9853 | yes | 4 | 38.82675 | 0.4067% | yes |
| Kepler-11 | Kepler-11 b | 10.3039 | yes | 1 | 7.5625194 | 26.6053% | no |
| Kepler-11 | Kepler-11 c | 13.0241 | yes | 1 | 7.5625194 | 41.9344% | no |
| Kepler-11 | Kepler-11 d | 22.6845 | yes | 1 | 7.5625194 | 66.6622% | no |
| Kepler-11 | Kepler-11 e | 31.9996 | yes | 4 | 39.456547 | 23.3033% | no |
| Kepler-11 | Kepler-11 f | 46.6888 | yes | 4 | 39.456547 | 15.4903% | no |
| Kepler-11 | Kepler-11 g | 118.3807 | no | 4 | 39.456547 | 66.6698% | no |
| Kepler-12 | Kepler-12 b | 4.4379629 | yes | 1 | 4.436999 | 0.0217% | yes |
| Kepler-13 | KOI-13 b | 1.763588 | yes | 1 | 1.7635478 | 0.0023% | yes |
| Kepler-14 | Kepler-14 b | 6.790123 | yes | 1 | 6.7885488 | 0.0232% | yes |
| Kepler-15 | Kepler-15 b | 4.942782 | yes | 3 | 4.9442403 | 0.0295% | yes |
| Kepler-16 | Kepler-16 b | 228.776 | no | 1 | 41.063762 | 82.0507% | no |
| Kepler-17 | Kepler-17 b | 1.4857108 | yes | 1 | 1.4856518 | 0.0040% | yes |
| Kepler-18 | Kepler-18 b | 3.504725 | yes | 5 | 3.7150783 | 6.0020% | no |
| Kepler-18 | Kepler-18 c | 7.64159 | yes | 1 | 7.6423684 | 0.0102% | yes |
| Kepler-18 | Kepler-18 d | 14.85888 | yes | 2 | 15.284002 | 2.8611% | no |
| Kepler-19 | Kepler-19 b | 9.28699 | yes | 2 | 4.6444071 | 49.9902% | no |
| Kepler-20 | Kepler-20 b | 3.6961049 | yes | 1 | 3.6180615 | 2.1115% | no |
| Kepler-20 | Kepler-20 e | 6.0984882 | yes | 2 | 5.4258159 | 11.0301% | no |
| Kepler-20 | Kepler-20 c | 10.854077 | yes | 2 | 5.4258159 | 50.0113% | no |
| Kepler-20 | Kepler-20 f | 19.578328 | yes | 2 | 5.4258159 | 72.2866% | no |
| Kepler-20 | Kepler-20 d | 77.611455 | no | 2 | 5.4258159 | 93.0090% | no |
| Kepler-21 | Kepler-21 b | 2.7858212 | yes | 1 | 2.7859729 | 0.0054% | yes |
| Kepler-25 | Kepler-25 b | 6.238297 | yes | 2 | 6.3598766 | 1.9489% | no |
| Kepler-25 | Kepler-25 c | 12.7207 | yes | 1 | 12.719245 | 0.0114% | yes |
| Kepler-36 | Kepler-36 b | 13.86825 | yes | 1 | 16.228613 | 17.0199% | no |
| Kepler-36 | Kepler-36 c | 16.21865 | yes | 1 | 16.228613 | 0.0614% | yes |
| Kepler-62 | Kepler-62 b | 5.714932 | yes | 1 | 5.7147517 | 0.0032% | yes |
| Kepler-62 | Kepler-62 c | 12.4417 | yes | 1 | 5.7147517 | 54.0678% | no |
| Kepler-62 | Kepler-62 d | 18.16406 | yes | 1 | 5.7147517 | 68.5381% | no |
| Kepler-62 | Kepler-62 e | 122.3874 | no | 1 | 5.7147517 | 95.3306% | no |
| Kepler-62 | Kepler-62 f | 267.291 | no | 1 | 5.7147517 | 97.8620% | no |
| Kepler-90 | KOI-351 b | 7.008151 | yes | 3 | 36.135109 | 415.6154% | no |
| Kepler-90 | KOI-351 c | 8.719375 | yes | 3 | 36.135109 | 314.4232% | no |
| Kepler-90 | Kepler-90 i | 14.44912 | yes | 3 | 36.135109 | 150.0852% | no |
| Kepler-90 | KOI-351 d | 59.73667 | no | 5 | 45.623603 | 23.6255% | no |
| Kepler-90 | KOI-351 e | 91.93913 | no | 5 | 45.623603 | 50.3763% | no |
| Kepler-90 | KOI-351 f | 124.9144 | no | 5 | 45.623603 | 63.4761% | no |
| Kepler-90 | KOI-351 g | 210.73514 | no | 5 | 45.623603 | 78.3503% | no |
| Kepler-90 | KOI-351 h | 331.60296 | no | 5 | 45.623603 | 86.2415% | no |

## Reproducibility and limitations

The target searches used 14,449–14,558 trial periods depending on each target baseline. No catalog period or epoch was provided to BLS. Known periods are used only after the search for evaluation.

BLS is expected to favor harmonics in multi-planet or eclipsing systems. This report does not treat harmonic-aware recovery as the primary metric and does not make any novel-candidate claim.
