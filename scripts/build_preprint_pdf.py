"""Render the SXS Markdown preprint as a polished, archive-ready PDF."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "reports" / "research_report.md"
DEFAULT_OUTPUT = ROOT / "output" / "pdf" / "sxs_preprint_v1.0.0.pdf"


def styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "SxsTitle", parent=sample["Title"], fontName="Helvetica-Bold", fontSize=20,
            leading=24, textColor=colors.HexColor("#102A43"), alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "meta": ParagraphStyle(
            "SxsMeta", parent=sample["Normal"], fontName="Helvetica", fontSize=8.5,
            leading=11, textColor=colors.HexColor("#486581"), alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "h1": ParagraphStyle(
            "SxsH1", parent=sample["Heading1"], fontName="Helvetica-Bold", fontSize=14,
            leading=17, textColor=colors.HexColor("#102A43"), spaceBefore=13, spaceAfter=6,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "SxsH2", parent=sample["Heading2"], fontName="Helvetica-Bold", fontSize=11,
            leading=14, textColor=colors.HexColor("#243B53"), spaceBefore=10, spaceAfter=4,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "SxsBody", parent=sample["BodyText"], fontName="Times-Roman", fontSize=9.4,
            leading=12.4, alignment=TA_JUSTIFY, textColor=colors.HexColor("#172B4D"),
            spaceAfter=5, allowWidows=0, allowOrphans=0,
        ),
        "abstract": ParagraphStyle(
            "SxsAbstract", parent=sample["BodyText"], fontName="Times-Roman", fontSize=9.2,
            leading=12.2, alignment=TA_JUSTIFY, leftIndent=12 * mm, rightIndent=12 * mm,
            textColor=colors.HexColor("#243B53"), spaceAfter=7,
        ),
        "list": ParagraphStyle(
            "SxsList", parent=sample["BodyText"], fontName="Times-Roman", fontSize=9.2,
            leading=12, leftIndent=6 * mm, firstLineIndent=-4 * mm, alignment=TA_LEFT,
            spaceAfter=3,
        ),
        "reference": ParagraphStyle(
            "SxsReference", parent=sample["BodyText"], fontName="Times-Roman", fontSize=8,
            leading=10.2, leftIndent=5 * mm, firstLineIndent=-5 * mm, alignment=TA_LEFT,
            wordWrap="CJK", spaceAfter=3,
        ),
        "caption": ParagraphStyle(
            "SxsCaption", parent=sample["BodyText"], fontName="Helvetica-Oblique", fontSize=7.8,
            leading=10, alignment=TA_CENTER, textColor=colors.HexColor("#486581"),
            spaceBefore=3, spaceAfter=7,
        ),
        "table": ParagraphStyle(
            "SxsTable", parent=sample["BodyText"], fontName="Helvetica", fontSize=6.6,
            leading=8, alignment=TA_LEFT, wordWrap="CJK",
        ),
        "table_header": ParagraphStyle(
            "SxsTableHeader", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=6.6,
            leading=8, textColor=colors.white, alignment=TA_LEFT, wordWrap="CJK",
        ),
    }


def inline_markup(text: str) -> str:
    value = html.escape(text.strip())
    value = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<link href="\2" color="#1D4ED8">\1</link>', value)
    value = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", value)
    value = re.sub(
        r"(?<!href=&quot;)(https?://[^\s<]+)",
        r'<link href="\1" color="#1D4ED8">\1</link>',
        value,
    )
    return value


def parse_table(lines: list[str], sty: dict[str, ParagraphStyle], width: float) -> Table:
    raw = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    if len(raw) > 1 and all(re.fullmatch(r":?-{3,}:?", cell) for cell in raw[1]):
        raw.pop(1)
    columns = max(len(row) for row in raw)
    data = []
    for row_index, row in enumerate(raw):
        row += [""] * (columns - len(row))
        cell_style = sty["table_header"] if row_index == 0 else sty["table"]
        data.append([Paragraph(inline_markup(cell), cell_style) for cell in row])
    if columns == 7:
        ratios = [0.07, 0.14, 0.10, 0.09, 0.08, 0.19, 0.33]
    elif columns == 6:
        ratios = [0.23, 0.13, 0.13, 0.13, 0.13, 0.25]
    else:
        ratios = [1 / columns] * columns
    table = Table(data, colWidths=[width * item for item in ratios], repeatRows=1, hAlign="LEFT")
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334E68")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#BCCCDC")),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for row in range(1, len(data)):
        if row % 2 == 0:
            commands.append(("BACKGROUND", (0, row), (-1, row), colors.HexColor("#F0F4F8")))
    table.setStyle(TableStyle(commands))
    return table


def build_story(source: Path, sty: dict[str, ParagraphStyle], content_width: float) -> list:
    lines = source.read_text(encoding="utf-8").splitlines()
    story: list = []
    paragraph: list[str] = []
    in_abstract = False
    in_references = False
    figure_number = 0

    def flush() -> None:
        nonlocal paragraph
        if paragraph:
            style = sty["abstract"] if in_abstract else sty["body"]
            story.append(Paragraph(inline_markup(" ".join(item.strip() for item in paragraph)), style))
            paragraph = []

    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("| "):
            flush()
            table_lines = []
            while index < len(lines) and lines[index].lstrip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            story.extend([Spacer(1, 2 * mm), parse_table(table_lines, sty, content_width), Spacer(1, 3 * mm)])
            continue
        image_match = re.fullmatch(r"!\[([^]]+)\]\(([^)]+)\)", line.strip())
        if image_match:
            flush()
            image_path = (source.parent / image_match.group(2)).resolve()
            if image_path.is_file():
                image = Image(str(image_path))
                image._restrictSize(content_width * 0.82, 78 * mm)
                figure_number += 1
                story.append(KeepTogether([
                    image,
                    Paragraph(f"Figure {figure_number}. {html.escape(image_match.group(1))}", sty["caption"]),
                ]))
            index += 1
            continue
        if line.startswith("# "):
            flush()
            story.append(Spacer(1, 5 * mm))
            story.append(Paragraph(inline_markup(line[2:]), sty["title"]))
            story.append(HRFlowable(width="72%", thickness=1.2, color=colors.HexColor("#3B82F6"), spaceAfter=5))
            index += 1
            continue
        if line.startswith("## "):
            flush()
            heading = line[3:]
            if heading == "Abstract":
                in_abstract = True
            elif in_abstract:
                in_abstract = False
            if heading == "References":
                in_references = True
            story.append(Paragraph(inline_markup(heading), sty["h1"]))
            index += 1
            continue
        if line.startswith("### "):
            flush()
            story.append(Paragraph(inline_markup(line[4:]), sty["h2"]))
            index += 1
            continue
        if line.startswith("**") and line.endswith("  ") and len(story) < 12:
            flush()
            story.append(Paragraph(inline_markup(line[:-2]), sty["meta"]))
            index += 1
            continue
        if re.match(r"^\d+\. \*\*", line) or line.startswith("- "):
            flush()
            match = re.match(r"^(\d+\.|-)\s+(.*)$", line)
            assert match
            story.append(Paragraph(f"{html.escape(match.group(1))} {inline_markup(match.group(2))}", sty["list"]))
            index += 1
            continue
        if in_references and re.match(r"^\d+\. ", line):
            flush()
            story.append(Paragraph(inline_markup(line), sty["reference"]))
            index += 1
            continue
        if not line.strip():
            flush()
        else:
            paragraph.append(line)
        index += 1
    flush()
    return story


class PreprintDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str):
        margin_x = 20 * mm
        margin_top = 18 * mm
        margin_bottom = 18 * mm
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=margin_x,
            rightMargin=margin_x,
            topMargin=margin_top,
            bottomMargin=margin_bottom,
            title="SXS: A Reproducible Kepler Transit-Recovery and Independent Vetting Pipeline",
            author="Rasya Andrean",
            subject="SXS public release v1.0.0 preprint",
        )
        frame = Frame(
            self.leftMargin, self.bottomMargin, self.width, self.height,
            leftPadding=0, rightPadding=0, topPadding=2 * mm, bottomPadding=1 * mm,
        )
        self.addPageTemplates(PageTemplate(id="main", frames=[frame], onPage=self._decorate))

    def _decorate(self, canvas, doc) -> None:
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(colors.HexColor("#D9E2EC"))
        canvas.setLineWidth(0.5)
        canvas.line(self.leftMargin, height - 12 * mm, width - self.rightMargin, height - 12 * mm)
        canvas.setFont("Helvetica", 7.2)
        canvas.setFillColor(colors.HexColor("#627D98"))
        canvas.drawString(self.leftMargin, height - 9.5 * mm, "SCIX Exoplanet Search - public release v1.0.0")
        canvas.drawRightString(width - self.rightMargin, height - 9.5 * mm, "Not a planet-discovery claim")
        canvas.line(self.leftMargin, 12 * mm, width - self.rightMargin, 12 * mm)
        canvas.drawString(self.leftMargin, 8.5 * mm, "28 August 2026")
        canvas.drawRightString(width - self.rightMargin, 8.5 * mm, f"Page {doc.page}")
        canvas.restoreState()


def build(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    sty = styles()
    document = PreprintDocTemplate(str(output))
    document.build(build_story(source, sty, document.width))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build(args.source.resolve(), args.output.resolve())
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
