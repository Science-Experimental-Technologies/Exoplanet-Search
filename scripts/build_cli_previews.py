"""Render real CLI stdout as reproducible, code-native terminal previews."""

from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "docs" / "assets" / "cli"
HELP = ["--help"]
PLAN = ["baseline", "--config", "configs/base.yaml", "--dry-run"]


def capture(arguments: list[str]) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "src.cli", *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        timeout=90,
    )
    return result.stdout.replace("\r\n", "\n").rstrip() + "\n"


def normalize_plan(stdout: str) -> dict:
    plan = json.loads(stdout)
    # Wall-clock timestamps are irrelevant to the plan and would create noisy diffs.
    plan.pop("started_at_utc", None)
    plan.pop("finished_at_utc", None)
    return plan


def compact_plan(plan: dict) -> str:
    """Project exact values into a compact JSON excerpt; never invent status lines."""
    rows = [
        "{",
        f'  "status": {json.dumps(plan["status"])},',
        f'  "config_path": {json.dumps(plan["config_path"])},',
        '  "stages": [',
    ]
    for index, stage in enumerate(plan["stages"]):
        suffix = "," if index < len(plan["stages"]) - 1 else ""
        rows.append("    " + json.dumps(stage) + suffix)
    rows.extend(["  ]", "}"])
    return "\n".join(rows)


def render_terminal(title: str, command: str, stdout: str, note: str) -> str:
    lines = stdout.rstrip().splitlines()
    line_height = 28
    height = 176 + len(lines) * line_height
    longest = max(len(command) + 2, *(len(line) for line in lines))
    width = max(1120, 80 + longest * 12)
    body = []
    for index, line in enumerate(lines):
        color = "#68dacb" if '"status"' in line or line == "Commands:" else "#dce5ed"
        body.append(
            f'<text x="36" y="{150 + index * line_height}" fill="{color}"'
            f' xml:space="preserve">{escape(line)}</text>'
        )
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f"<title id=\"title\">{escape(title)}</title>",
        f"<desc id=\"desc\">{escape(command + '. ' + note)}</desc>",
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="16" fill="#0b121b" stroke="#334254"/>',
        f'<path d="M1 64H{width - 1}" stroke="#334254"/>',
        '<rect x="30" y="23" width="18" height="18" rx="3" fill="#68dacb"/>',
        f'<text x="62" y="40" font-family="Arial, sans-serif" font-size="18" fill="#f3f7fa">SXS / {escape(title)}</text>',
        f'<text x="{width - 30}" y="40" text-anchor="end" font-family="Arial, sans-serif" font-size="13" letter-spacing="1.4" fill="#99aabd">CLI PREVIEW</text>',
        '<g font-family="Consolas, DejaVu Sans Mono, monospace" font-size="18">',
        f'<text x="36" y="108" fill="#68dacb">$ {escape(command)}</text>',
        *body,
        "</g>",
        f'<text x="36" y="{height - 24}" font-family="Arial, sans-serif" font-size="13" fill="#99aabd">{escape(note)}</text>',
        "</svg>",
        "",
    ])


def build_assets() -> dict[str, str]:
    help_text = capture(HELP)
    plan = normalize_plan(capture(PLAN))
    return {
        "help.txt": help_text,
        "baseline-dry-run.json": json.dumps(plan, indent=2) + "\n",
        "help.svg": render_terminal(
            "Command overview", "python -m src.cli --help", help_text,
            "Recorded CLI stdout. Styled terminal rendering; not an application window screenshot.",
        ),
        "baseline-dry-run.svg": render_terminal(
            "Baseline dry run", "python -m src.cli " + " ".join(PLAN), compact_plan(plan),
            "JSON excerpt: exact status, config and stage values. No research stages were executed.",
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if committed previews differ from CLI output")
    options = parser.parse_args()
    assets = build_assets()
    if options.check:
        stale = [name for name, content in assets.items() if not (DESTINATION / name).is_file()
                 or (DESTINATION / name).read_text(encoding="utf-8") != content]
        if stale:
            print("Outdated CLI previews: " + ", ".join(stale), file=sys.stderr)
            return 1
        print("CLI previews match the current command output.")
        return 0
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for name, content in assets.items():
        (DESTINATION / name).write_text(content, encoding="utf-8", newline="\n")
        print((DESTINATION / name).relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
