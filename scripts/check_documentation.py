"""Check local files and anchors in an already-built documentation site."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Page(HTMLParser):
    def __init__(self, path: Path):
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.feed(path.read_text(encoding="utf-8"))

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(attributes["id"])
        for key in ("href", "src"):
            if attributes.get(key):
                self.links.append(attributes[key])


def check(site: Path, base_path: str = "/Exoplanet-Search/") -> tuple[int, int, list[str]]:
    site = site.resolve()
    pages = {path.resolve(): Page(path) for path in site.rglob("*.html")}
    if not pages:
        raise ValueError(f"No generated HTML found in {site}; build the site first")
    checked = 0
    errors = []
    for source, page in pages.items():
        for link in page.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            path = unquote(url.path)
            if path.startswith("/"):
                if not path.startswith(base_path):
                    errors.append(f"{source.relative_to(site)}: outside site base {link}")
                    continue
                target = (site / path[len(base_path):]).resolve()
            else:
                target = (source.parent / path).resolve() if path else source
            if target.is_dir():
                target = target / "index.html"
            checked += 1
            if not target.is_file():
                errors.append(f"{source.relative_to(site)}: missing {link}")
            elif url.fragment and target in pages:
                if unquote(url.fragment) not in pages[target].ids:
                    errors.append(f"{source.relative_to(site)}: missing anchor {link}")
    return len(pages), checked, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, default=Path("site"))
    parser.add_argument("--base-path", default="/Exoplanet-Search/")
    args = parser.parse_args()
    count, links, errors = check(args.site_dir, args.base_path)
    print(f"Checked {count} HTML pages and {links} local references.")
    for error in errors:
        print(error)
    print(f"Broken references: {len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
