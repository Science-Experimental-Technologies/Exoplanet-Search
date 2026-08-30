"""Offline checks for repository prose, relative file links, and RNAAS length.

Language detection is a targeted Indonesian-language heuristic, not a proof of
English grammar. MkDocs and check_documentation.py validate site navigation and
anchors separately. External URLs and binary artifacts are not checked here.
"""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
VIRTUAL_ASSETS = {
    "docs/assets/sxs-banner.png": "assets/sxs-banner.png",
    "docs/reports/confusion_matrices.png": "reports/confusion_matrices.png",
    "docs/reports/candidate_figures/rank_05_8300900-r1.png": "reports/candidate_figures/rank_05_8300900-r1.png",
}
INDONESIAN = re.compile(
    r"\b(?:adalah|untuk|dengan|tidak|sudah|belum|pengujian|kesimpulan|"
    r"jalankan|berikut|sebagai|dilakukan|menggunakan|dari|yang|dan)\b", re.I
)


def prose(text: str) -> str:
    text = re.sub(r"^(```|~~~).*?^\1[^\n]*$", "", text, flags=re.M | re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def language_findings(text: str) -> list[int]:
    return [number for number, line in enumerate(prose(text).splitlines(), 1)
            if len(set(word.lower() for word in INDONESIAN.findall(line))) >= 3]


class HTMLLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(value for key, value in attrs if key in {"href", "src"} and value)


def local_link_errors(path: Path, text: str, root: Path) -> list[str]:
    clean = prose(text)
    links = re.findall(r"!?\[[^\]\n]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)", clean)
    links += re.findall(r"^\s*\[[^\]]+\]:\s*(\S+)", clean, re.M)
    parser = HTMLLinks()
    parser.feed(clean)
    links += parser.links
    errors = []
    for link in links:
        parsed = urlsplit(link.strip("<>"))
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        destination = (path.parent / unquote(parsed.path)).resolve()
        if not destination.is_relative_to(root.resolve()):
            errors.append(f"local link escapes repository: {link}")
            continue
        relative = destination.relative_to(root.resolve()).as_posix()
        destination = root / VIRTUAL_ASSETS.get(relative, relative)
        if not destination.exists():
            errors.append(f"missing local link: {link}")
    return errors


def rnaas_counts(text: str) -> dict[str, int]:
    abstract = text.split("## Abstract\n", 1)[1].split("\n## ", 1)[0]
    body = text.split("## Data and Methods\n", 1)[1].split("\n## References", 1)[0]
    # Include Markdown table separators and syntax tokens conservatively.
    count = lambda value: len(value.split())
    return {"abstract": count(abstract), "body": count("Data and Methods\n" + body), "total": count(text)}


def inspect_document(path: Path, root: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors = local_link_errors(path, text, root)
    for line in language_findings(text):
        errors.append(f"possible untranslated Indonesian in prose near line {line}")
    ancestry: list[tuple[int, str]] = []
    seen = set()
    for marks, title in re.findall(r"^(#{1,6})\s+(.+)$", prose(text), re.M):
        level = len(marks)
        ancestry = [(depth, name) for depth, name in ancestry if depth < level]
        ancestry.append((level, title))
        key = tuple(ancestry)
        if key in seen:
            errors.append(f"duplicate heading under the same parent: {title}")
        seen.add(key)
    if "environment specification-9" in text or "environment specification–5" in text:
        errors.append("malformed legacy milestone replacement")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extra", type=Path, action="append", default=[], help="Also inspect a specific untracked Markdown file")
    args = parser.parse_args()
    tracked = subprocess.run(["git", "ls-files", "-z", "*.md"], cwd=ROOT,
                             capture_output=True, check=True).stdout
    paths = {ROOT / name.decode("utf-8") for name in tracked.split(b"\0") if name}
    paths.update((ROOT / path).resolve() for path in args.extra)
    errors = []
    for path in sorted(paths):
        if not path.resolve().is_relative_to(ROOT):
            errors.append(f"outside repository: {path.name}")
            continue
        errors.extend(f"{path.relative_to(ROOT)}: {error}" for error in inspect_document(path, ROOT))
    draft = (ROOT / "reports/rnaas_draft.md").read_text(encoding="utf-8")
    counts = rnaas_counts(draft)
    if counts["abstract"] > 150 or counts["total"] > 1500:
        errors.append(f"RNAAS word limits exceeded: {counts}")
    tables = len(re.findall(r"^\|[\s:|-]+\|$", draft, re.M))
    if tables != 1 or re.search(r"!\[", draft):
        errors.append("RNAAS draft must contain exactly one table and no figures")
    print(f"Checked {len(paths)} Markdown documents; {len(errors)} findings.")
    print(f"Conservative RNAAS word counts: {counts}")
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
