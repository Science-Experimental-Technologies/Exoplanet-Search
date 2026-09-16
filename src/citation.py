"""Print the preferred citation for the archived SXS software release."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence


CITATION = {
    "author": "Rasya Andrean",
    "year": 2026,
    "title": "SCIX Exoplanet Search (SXS): Reproducible Kepler Transit Recovery and Independent Vetting",
    "version": "1.4.0",
    "publisher": "Science Experimental Technologies",
    "doi": "10.5281/zenodo.22794079",
    "repository": "https://github.com/Science-Experimental-Technologies/Exoplanet-Search",
}


def render_text() -> str:
    """Return a human-readable citation for the latest archived release."""

    return (
        f"Andrean, R. ({CITATION['year']}). {CITATION['title']} "
        f"(Version {CITATION['version']}) [Computer software]. "
        f"{CITATION['publisher']}. https://doi.org/{CITATION['doi']}"
    )


def render_bibtex() -> str:
    """Return a BibTeX software record without requiring a CFF parser."""

    return "\n".join(
        (
            "@software{sxs_1_4_0,",
            "  author = {Andrean, Rasya},",
            f"  title = {{{CITATION['title']}}},",
            f"  year = {{{CITATION['year']}}},",
            f"  version = {{{CITATION['version']}}},",
            f"  publisher = {{{CITATION['publisher']}}},",
            f"  doi = {{{CITATION['doi']}}},",
            f"  url = {{https://doi.org/{CITATION['doi']}}}",
            "}",
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        choices=("text", "bibtex", "json"),
        default="text",
        help="citation serialization (default: text)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.format == "bibtex":
        print(render_bibtex())
    elif args.format == "json":
        print(json.dumps(CITATION, indent=2, sort_keys=True))
    else:
        print(render_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
