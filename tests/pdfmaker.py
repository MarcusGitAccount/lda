"""Small PDFs for the tests, made with reportlab (a dev dependency)."""

from __future__ import annotations

import io

from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table

BODY = ParagraphStyle("body", fontName="Times-Roman", fontSize=11, leading=14, alignment=TA_JUSTIFY, spaceAfter=6)
LIST = ParagraphStyle("list", parent=BODY, leftIndent=1 * cm, spaceAfter=3)


def make_pdf(story: list, *, header: str = "", footer: str = "{n}") -> bytes:
    """`footer` can use {n} for the page number. `header` is on every page."""
    buffer = io.BytesIO()

    def decorate(c, doc):
        c.setFont("Times-Italic", 8)
        if header:
            c.drawString(2.5 * cm, A4[1] - 1.3 * cm, header)
        if footer:
            c.drawRightString(A4[0] - 2.5 * cm, 1.2 * cm, footer.format(n=doc.page))

    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2.5 * cm, rightMargin=2.5 * cm, topMargin=2.5 * cm, bottomMargin=2.3 * cm)
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return buffer.getvalue()


def paragraph(text: str) -> Paragraph:
    return Paragraph(text, BODY)


def item(marker: str, text: str) -> Paragraph:
    return Paragraph(text, LIST, bulletText=marker)


def table(rows: list[list[str]], widths_cm: list[float]) -> Table:
    return Table(rows, colWidths=[w * cm for w in widths_cm])


def empty_page_pdf(pages: int = 1) -> bytes:
    """A PDF with a drawing and no text, like a scan without OCR."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    for _ in range(pages):
        c.rect(3 * cm, 3 * cm, 10 * cm, 10 * cm, fill=1)
        c.showPage()
    c.save()
    return buffer.getvalue()


__all__ = ["PageBreak", "Spacer", "empty_page_pdf", "item", "make_pdf", "paragraph", "table"]
