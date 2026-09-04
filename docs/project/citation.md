# Citation

If SXS materially supports a project, publication, analysis, or output, cite
the release metadata in `CITATION.cff` and provide the attribution required by
the project license.

## Software citation

```text
Andrean, R. (2026). SCIX Exoplanet Search (SXS): Reproducible Kepler
Transit Recovery and Independent Vetting (Version 1.3.0).
Science Experimental Technologies.
https://doi.org/10.5281/zenodo.22294859
```

The version DOI `10.5281/zenodo.22294859` identifies the archived v1.3.0
software release. The concept DOI
[`10.5281/zenodo.22294858`](https://doi.org/10.5281/zenodo.22294858)
represents all SXS versions and resolves to the latest archive.

GitHub's **Cite this repository** control reads `CITATION.cff` and can export
common citation formats.

The top-level CFF entry identifies the software release. The separately listed
research report remains version 1.0.0; it does not replace the software citation.

## Required attribution

> Built with SXS — SCIX Exoplanet Search, created by Rasya Andrean under
> Science Experimental Technologies.

Link the attribution to the
[repository](https://github.com/Science-Experimental-Technologies/Exoplanet-Search)
when the medium supports links.

## Upstream citations

Also cite the data and software actually used, including the relevant:

- NASA Exoplanet Archive table/query;
- Kepler/MAST data products and mission papers;
- Gaia data release;
- TESS products where used;
- ExoFOP records where used;
- Lightkurve and Astroquery; and
- `batman` transit model.

Do not imply that NASA, ESA, MAST, or another provider endorses SXS or its
candidate classifications.

## Version choice

Cite the exact version or commit used. Release 1.3.0 adds verified public
distribution, security attestations, publication tooling, and the permanent
Zenodo archive to the source-available software. The documentation website
follows the default branch.
The scientific preprint artifact remains version 1.0.0 because
the research metrics did not change in the packaging/documentation release.
