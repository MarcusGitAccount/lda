"""Render a hidden (or restored) text as a PDF. For the demo and for people. Not for the AI tool.

The tool writes text, because an AI tool can edit text but not a PDF. A PDF copy looks better
in a demo: the ids are marked in yellow, and the changes of an AI tool can be marked in green.
The PDF copy has the same words as the text file. It does not have the layout of the original PDF.

    python -m demo.render_pdf demo-output/hidden/*.txt             # PDF copies next to the files
    python -m demo.render_pdf FILE.txt --restored --out some/dir   # a restored text, with no banner
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Table, TableStyle

from . import layout
from .layout import Meta

PLACEHOLDER = re.compile(r"\[[A-Z_]+_\d{3,}\]")
NUMBERED = re.compile(r"^(\d{1,3}(?:\.\d{1,3})*\.|[a-z]\)|\([A-Za-z0-9]{1,4}\))\s+(.*)$", re.S)
HEADING_WORDS = ("ARTICOL", "ANEXA", "BACKGROUND", "AGREED", "SCHEDULE")
LETTERS = re.compile(r"[^A-Za-zĂÂÎȘȚăâîșț]")
COMPANY_NAME = re.compile(r"(?:S\.C\. )?\[[A-Z_]+_\d{3,}\]")

TEXTS = {
    "ro": {
        "hidden": ("COPIE ANONIMIZATĂ – datele sensibile sunt înlocuite cu id-uri", "Copie anonimizată", "Pagina {n} din {total}"),
        "restored": ("", "Document restaurat", "Pagina {n} din {total}"),
    },
    "en": {
        "hidden": ("ANONYMIZED COPY – sensitive data is replaced by ids", "Anonymized copy", "Page {n} of {total}"),
        "restored": ("", "Restored document", "Page {n} of {total}"),
    },
}


def mark(text: str) -> str:
    """Escape the text for reportlab. Show each id on a yellow background."""
    return PLACEHOLDER.sub(
        lambda m: f'<font backColor="#FFE8A3" color="#5A3D00"><b>{m.group(0)}</b></font>', escape(text)
    )


def _style(name: str, changed: bool) -> ParagraphStyle:
    if not changed:
        return layout.S[name]
    return ParagraphStyle(name + "-changed", parent=layout.S[name], backColor=colors.HexColor("#E3F6E3"), borderPadding=3)


def _table(block: str) -> Table:
    rows = [line.split("\t") for line in block.split("\n") if line.strip()]
    columns = max(len(r) for r in rows)
    rows = [[mark(c) for c in r] + [""] * (columns - len(r)) for r in rows]
    header = columns >= 3 and not re.search(r"\d", " ".join(rows[0]))
    if columns == 2 and len(rows) <= 4 and not header:
        return layout.plain_table(rows, [8.0, 8.0])
    return layout.grid(rows, [16.0 / columns] * columns, header=header)


def _flowable(block: str, changed: bool, state: dict):
    if "\t" in block:
        return _table(block)
    if COMPANY_NAME.fullmatch(block.strip()):  # the name of the company in a letterhead
        return Paragraph(mark(block), _style("lh_name", changed))
    letters = LETTERS.sub("", PLACEHOLDER.sub("", block))
    if len(letters) >= 4 and letters.isupper() and len(block) < 130:
        # The first long heading is the title of the document. The other headings are smaller.
        if not state["title"] and len(block) >= 20 and not block.startswith(HEADING_WORDS):
            state["title"] = True
            return Paragraph(mark(block), _style("title", changed))
        return Paragraph(mark(block), _style("article", changed))
    if (" | " in block and len(block) < 170) or block.startswith(("Sediul ", "Nr. Reg.", "Cont IBAN", "Tel.:")):
        return Paragraph(mark(block), _style("lh_line", changed))
    numbered = NUMBERED.match(block)
    if numbered:
        number, rest = numbered.groups()
        style = "clause" if number[0].isdigit() and "." in number else "sub"
        return Paragraph(mark(rest), _style(style, changed), bulletText=number)
    return Paragraph(mark(block), _style("body", changed))


def render(text: str, path: Path, *, restored: bool = False, language: str = "ro", changed: set[str] | frozenset = frozenset()) -> None:
    """Write `text` as a PDF. `changed` is a set of paragraphs to mark in green."""
    if layout.S is None:
        layout.setup()
    banner, footer, page_label = TEXTS[language]["restored" if restored else "hidden"]
    story: list = []
    if banner:
        box = Table([[Paragraph(f"<b>{escape(banner)}</b>", layout.S["small"])]], colWidths=[16 * cm])
        box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF6D6")), ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#C9A227"))]))
        story += [box, layout.space(0.4)]
    state = {"title": False}
    for block in re.split(r"\n\s*\n", text.strip()):
        block = block.strip("\n")
        if block.strip():
            story.append(_flowable(block, block.strip() in changed, state))
    meta = Meta(title=path.stem, author="", subject=footer, header=path.stem, footer=footer, page_label=page_label)
    layout.build(path, story, meta)


def language_of(name: str) -> str:
    return "en" if ".en." in name else "ro"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, help="folder for the PDF files (default: next to each text file)")
    parser.add_argument("--restored", action="store_true", help="the text has the real data: no banner")
    args = parser.parse_args()
    for file in args.files:
        target = (args.out or file.parent) / (file.stem + ".pdf")
        target.parent.mkdir(parents=True, exist_ok=True)
        render(file.read_text(encoding="utf-8"), target, restored=args.restored, language=language_of(file.name))
        print(f"{file} -> {target}")


if __name__ == "__main__":
    main()
