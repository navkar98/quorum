"""Convert docs/SCREENS.md into a styled Word document (docs/Quorum-Screens.docx).

Handles the Markdown constructs used in SCREENS.md: #/##/### headings, horizontal rules,
bullet lists (- ), ordered lists (1. ), blockquotes (> ), pipe tables, and inline bold
(**...**) and inline code (`...`). Run:  python docs/build_docx.py
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

HERE = Path(__file__).resolve().parent
SRC = HERE / os.environ.get("QUORUM_DOCX_SRC", "SCREENS.md")
OUT = HERE / os.environ.get("QUORUM_DOCX_OUT", "Quorum-Screens.docx")

INLINE = re.compile(r"(\*\*.+?\*\*|`.+?`)")
IMG = re.compile(r"^<!--IMG:(.+?)\|(.*?)-->$")
SHOTS = HERE / "screenshots"


def add_image(doc: Document, filename: str, caption: str) -> None:
    path = SHOTS / filename
    if not path.exists():
        # Missing screenshot: note it rather than failing the whole build.
        p = doc.add_paragraph()
        p.add_run(f"[screenshot missing: {filename}]").italic = True
        return
    doc.add_picture(str(path), width=Inches(6.0))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    if caption:
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = cap.add_run(caption)
        run.italic = True
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0x60, 0x60, 0x60)


def add_inline(paragraph, text: str) -> None:
    """Add text to a paragraph, honoring **bold** and `code` spans."""
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
            run.font.color.rgb = RGBColor(0xB0, 0x30, 0x60)
        else:
            paragraph.add_run(part)


def flush_table(doc: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    table = doc.add_table(rows=0, cols=len(rows[0]))
    table.style = "Light Grid Accent 1"
    for i, row in enumerate(rows):
        cells = table.add_row().cells
        for j, cell_text in enumerate(row):
            if j >= len(cells):
                break
            cells[j].text = ""
            p = cells[j].paragraphs[0]
            add_inline(p, cell_text.strip())
            if i == 0:
                for run in p.runs:
                    run.bold = True
    doc.add_paragraph()


def main() -> None:
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)

    lines = SRC.read_text(encoding="utf-8").splitlines()
    table_buffer: list[list[str]] = []

    def flush():
        nonlocal table_buffer
        if table_buffer:
            flush_table(doc, table_buffer)
            table_buffer = []

    for raw in lines:
        line = raw.rstrip()

        # Table rows (contain pipes). Skip separator rows like |---|---|.
        if line.strip().startswith("|") and line.strip().endswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue  # separator
            table_buffer.append(cells)
            continue
        else:
            flush()

        img_match = IMG.match(line.strip())
        if img_match:
            add_image(doc, img_match.group(1).strip(), img_match.group(2).strip())
            continue

        if not line.strip():
            continue

        if line.startswith("### "):
            doc.add_heading(line[4:], level=3)
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=2)
        elif line.startswith("# "):
            doc.add_heading(line[2:], level=1)
        elif line.strip() == "---":
            doc.add_paragraph().add_run("").add_break()
        elif line.startswith("> "):
            p = doc.add_paragraph(style="Intense Quote")
            add_inline(p, line[2:])
        elif re.match(r"^\d+\.\s", line):
            p = doc.add_paragraph(style="List Number")
            add_inline(p, re.sub(r"^\d+\.\s", "", line))
        elif line.startswith("- "):
            # indentation -> nested bullet
            indent = len(raw) - len(raw.lstrip())
            style = "List Bullet 2" if indent >= 2 else "List Bullet"
            p = doc.add_paragraph(style=style)
            add_inline(p, line.lstrip()[2:])
        else:
            p = doc.add_paragraph()
            add_inline(p, line)

    flush()
    doc.save(str(OUT))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
