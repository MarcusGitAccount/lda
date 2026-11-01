"""Page layout for the demo PDFs, with reportlab.

The pages look like documents from a law office: a letterhead on the first
page, numbered articles, tables, signature blocks, a running header, and a
footer with page numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

FONT_CANDIDATES = [
    # (regular, bold, italic, bold italic)
    ("/System/Library/Fonts/Supplemental/Times New Roman.ttf", "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
     "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf", "/System/Library/Fonts/Supplemental/Times New Roman Bold Italic.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf", "/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-BoldItalic.ttf"),
]  # fmt: skip
FAMILY = "DemoSerif"


def register_fonts() -> None:
    """We need a font with the Romanian letters (ș, ț, ă, â, î)."""
    for paths in FONT_CANDIDATES:
        if all(Path(p).exists() for p in paths):
            for style, path in zip(("", "-Bold", "-Italic", "-BoldItalic"), paths):
                pdfmetrics.registerFont(TTFont(FAMILY + style, path))
            pdfmetrics.registerFontFamily(
                FAMILY, normal=FAMILY, bold=FAMILY + "-Bold", italic=FAMILY + "-Italic", boldItalic=FAMILY + "-BoldItalic"
            )
            return
    raise SystemExit("No serif TrueType font with Romanian letters found. Install 'Liberation Serif' or 'DejaVu Serif'.")


def _style(name: str, **kw) -> ParagraphStyle:
    base = dict(fontName=FAMILY, fontSize=10.5, leading=13.8, alignment=TA_JUSTIFY, spaceAfter=5)
    base.update(kw)
    return ParagraphStyle(name, **base)


def styles() -> dict[str, ParagraphStyle]:
    return {
        "body": _style("body"),
        "left": _style("left", alignment=TA_LEFT),
        "right": _style("right", alignment=TA_RIGHT),
        "title": _style("title", fontName=FAMILY + "-Bold", fontSize=13.5, leading=17, alignment=TA_CENTER, spaceBefore=8, spaceAfter=3),
        "subtitle": _style("subtitle", alignment=TA_CENTER, spaceAfter=10),
        "article": _style("article", fontName=FAMILY + "-Bold", fontSize=11, alignment=TA_CENTER, spaceBefore=9, spaceAfter=5, keepWithNext=1),
        "heading": _style("heading", fontName=FAMILY + "-Bold", alignment=TA_LEFT, spaceBefore=8, spaceAfter=4, keepWithNext=1),
        "clause": _style("clause", leftIndent=1.15 * cm, bulletIndent=0, bulletFontName=FAMILY),
        "sub": _style("sub", leftIndent=2.0 * cm, bulletIndent=1.15 * cm, bulletFontName=FAMILY, spaceAfter=3),
        "cell": _style("cell", fontSize=9.5, leading=12, alignment=TA_LEFT, spaceAfter=0),
        "cellb": _style("cellb", fontName=FAMILY + "-Bold", fontSize=9.5, leading=12, alignment=TA_LEFT, spaceAfter=0),
        "cellr": _style("cellr", fontSize=9.5, leading=12, alignment=TA_RIGHT, spaceAfter=0),
        "sig": _style("sig", alignment=TA_CENTER, spaceAfter=0),
        "small": _style("small", fontSize=9, leading=11.5, alignment=TA_LEFT, spaceAfter=2),
        "lh_name": _style("lh_name", fontName=FAMILY + "-Bold", fontSize=15, leading=18, alignment=TA_CENTER, spaceAfter=2),
        "lh_line": _style("lh_line", fontSize=8.8, leading=11, alignment=TA_CENTER, spaceAfter=0),
    }


S = None  # filled by `setup`


def setup() -> None:
    global S
    register_fonts()
    S = styles()


# --- building blocks ------------------------------------------------------------


def p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, S[style])


def article(text: str) -> Paragraph:
    return Paragraph(text, S["article"])


def clause(number: str, text: str) -> Paragraph:
    return Paragraph(text, S["clause"], bulletText=number)


def sub(letter: str, text: str) -> Paragraph:
    return Paragraph(text, S["sub"], bulletText=letter)


def space(height_cm: float = 0.4) -> Spacer:
    return Spacer(1, height_cm * cm)


def letterhead(name: str, lines: list[str]) -> list:
    rule = Table([[""]], colWidths=[16 * cm], rowHeights=[2])
    rule.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 1.0, colors.HexColor("#333333"))]))
    return [p(name, "lh_name"), *[p(line, "lh_line") for line in lines], rule, space(0.3)]


def grid(rows: list[list[str]], widths_cm: list[float], *, right_cols: tuple[int, ...] = (), header: bool = True, bold_last: bool = False) -> Table:
    data = []
    for r, row in enumerate(rows):
        cells = []
        for c, value in enumerate(row):
            bold = (header and r == 0) or (bold_last and r == len(rows) - 1)
            style = "cellb" if bold else ("cellr" if c in right_cols else "cell")
            cells.append(Paragraph(value, S[style]))
        data.append(cells)
    table = Table(data, colWidths=[w * cm for w in widths_cm], repeatRows=1 if header else 0)
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#555555")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E8E8")))
    table.setStyle(TableStyle(commands))
    return table


def plain_table(rows: list[list[str]], widths_cm: list[float]) -> Table:
    """A table with no lines: labels and values, or the two sides of a signature block."""
    data = [[Paragraph(v, S["left"]) for v in row] for row in rows]
    table = Table(data, colWidths=[w * cm for w in widths_cm])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    return table


def signatures(left: list[str], right: list[str], *, gap_cm: float = 1.6) -> KeepTogether:
    """Two blocks side by side, with room for the signature."""
    rows = [[Paragraph(a, S["sig"]), Paragraph(b, S["sig"])] for a, b in zip(left, right)]
    rows.insert(2, [Spacer(1, gap_cm * cm), Spacer(1, gap_cm * cm)])
    table = Table(rows, colWidths=[8 * cm, 8 * cm])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    return KeepTogether([space(0.5), table])


# --- the document ----------------------------------------------------------------


@dataclass
class Meta:
    title: str  # PDF properties
    author: str
    subject: str
    header: str  # running header, from page 2
    footer: str  # footer, left side
    page_label: str = "Pagina {n} din {total}"


def _canvas_class(meta: Meta):
    class Numbered(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._states: list[dict] = []

        def showPage(self):
            self._states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._states)
            for state in self._states:
                self.__dict__.update(state)
                self._decorate(total)
                super().showPage()
            super().save()

        def _decorate(self, total: int) -> None:
            width, height = A4
            self.setFont(FAMILY + "-Italic", 8.5)
            self.setFillColor(colors.HexColor("#444444"))
            if self._pageNumber > 1:
                self.drawString(2.5 * cm, height - 1.45 * cm, meta.header)
                self.setStrokeColor(colors.HexColor("#999999"))
                self.setLineWidth(0.4)
                self.line(2.5 * cm, height - 1.6 * cm, width - 2.5 * cm, height - 1.6 * cm)
            self.setStrokeColor(colors.HexColor("#999999"))
            self.setLineWidth(0.4)
            self.line(2.5 * cm, 1.75 * cm, width - 2.5 * cm, 1.75 * cm)
            self.drawString(2.5 * cm, 1.3 * cm, meta.footer)
            self.drawRightString(width - 2.5 * cm, 1.3 * cm, meta.page_label.format(n=self._pageNumber, total=total))

    return Numbered


def build(path: Path, story: list, meta: Meta) -> None:
    width, height = A4
    doc = BaseDocTemplate(
        str(path), pagesize=A4, title=meta.title, author=meta.author, subject=meta.subject,
        leftMargin=2.5 * cm, rightMargin=2.5 * cm, topMargin=2.5 * cm, bottomMargin=2.3 * cm,
    )  # fmt: skip
    frame = Frame(2.5 * cm, 2.3 * cm, width - 5 * cm, height - 4.8 * cm, id="body", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="page", frames=[frame])])
    doc.build(story, canvasmaker=_canvas_class(meta))


__all__ = ["KeepTogether", "Meta", "PageBreak", "article", "build", "clause", "grid", "letterhead", "p", "plain_table", "setup", "signatures", "space", "sub"]
