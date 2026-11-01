"""Page layout for the demo Word files, with python-docx.

The functions have the same names as the ones in layout.py (the PDF layout), so the text of the
demo documents is written one time. The result is a normal Word file: real styles (Title,
Heading 1, Clause, ...), real tables, a running header from page 2, and a footer with page
fields. A lawyer can edit it in Word. The text uses the same small markup as layout.py: <b>...</b>.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

from .layout import Meta

FONT = "Times New Roman"
CREATED = datetime(2025, 6, 20, 9, 0, tzinfo=timezone.utc)  # a fixed date: the same input gives the same file
TEXT_WIDTH_CM = 16.0
LANGUAGES = {"ro": "ro-RO", "en": "en-GB"}


# --- the blocks of a story ----------------------------------------------------------


@dataclass
class Para:
    text: str
    style: str = "body"
    rule: bool = False  # a line under the paragraph


@dataclass
class Gap:
    cm: float


@dataclass
class Break:
    """A page break. The next paragraph starts on a new page."""


@dataclass
class Grid:
    rows: list[list[str]]
    widths: list[float]
    right_cols: tuple[int, ...] = ()
    header: bool = True
    bold_last: bool = False
    borders: bool = True


@dataclass
class Signature:
    left: list[str]
    right: list[str]
    gap_cm: float = 1.6


def setup() -> None:
    """Nothing to do. The PDF layout loads fonts here. Word has its own fonts."""


def p(text: str, style: str = "body") -> Para:
    return Para(text, style)


def article(text: str) -> Para:
    return Para(text, "article")


def clause(number: str, text: str) -> Para:
    return Para(f"{number}\t{text}", "clause")


def sub(letter: str, text: str) -> Para:
    return Para(f"{letter}\t{text}", "sub")


def space(height_cm: float = 0.4) -> Gap:
    return Gap(height_cm)


def letterhead(name: str, lines: list[str]) -> list:
    return [Para(name, "lh_name"), *[Para(line, "lh_line", rule=i == len(lines) - 1) for i, line in enumerate(lines)], Gap(0.3)]


def grid(rows: list[list[str]], widths_cm: list[float], *, right_cols: tuple[int, ...] = (), header: bool = True, bold_last: bool = False) -> Grid:
    return Grid(rows, widths_cm, right_cols, header, bold_last)


def plain_table(rows: list[list[str]], widths_cm: list[float]) -> Grid:
    """A table with no lines: labels and values, or the two sides of a signature block."""
    return Grid(rows, widths_cm, header=False, borders=False)


def signatures(left: list[str], right: list[str], *, gap_cm: float = 1.6) -> Signature:
    return Signature(left, right, gap_cm)


def PageBreak() -> Break:  # the name is the one of the reportlab class
    return Break()


# --- Word styles --------------------------------------------------------------------


@dataclass
class Look:
    name: str  # the name of the Word style
    align: WD_ALIGN_PARAGRAPH = WD_ALIGN_PARAGRAPH.JUSTIFY
    size: float = 10.5
    bold: bool = False
    before: float = 0
    after: float = 5
    left_cm: float = 0.0
    first_cm: float = 0.0  # negative: hanging indent
    tab_cm: float | None = None
    keep_next: bool = False
    outline: int | None = None  # a level for the navigation pane
    built_in: bool = False  # the template has the style: we remove its old format


LEFT, CENTER, RIGHT = WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.RIGHT

LOOKS = {
    "body": Look("Normal", built_in=True),
    "left": Look("Text Left", LEFT),
    "right": Look("Text Right", RIGHT),
    "title": Look("Title", CENTER, 13.5, True, before=8, after=3, built_in=True),
    "subtitle": Look("Subtitle", CENTER, after=10, built_in=True),
    "article": Look("Heading 1", CENTER, 11, True, before=9, keep_next=True, outline=0, built_in=True),
    "clause": Look("Clause", left_cm=1.15, first_cm=-1.15, tab_cm=1.15),
    "sub": Look("Sub-clause", after=3, left_cm=2.0, first_cm=-0.85, tab_cm=2.0),
    "cell": Look("Table Text", LEFT, 9.5, after=0),
    "sig": Look("Signature", CENTER, after=0),
    "small": Look("Small", LEFT, 9, after=2),
    "lh_name": Look("Letterhead Name", CENTER, 15, True, after=2),
    "lh_line": Look("Letterhead Line", CENTER, 8.8, after=0),
}


def _el(tag: str, **attributes: str | int) -> OxmlElement:
    element = OxmlElement(f"w:{tag}")
    for key, value in attributes.items():
        element.set(qn(f"w:{key}"), str(value))
    return element


def _fonts(rpr, name: str = FONT) -> None:
    """Set the font in a run property element. We remove the theme fonts: they win over the name."""
    for old in rpr.findall(qn("w:rFonts")):
        rpr.remove(old)
    rpr.insert(0, _el("rFonts", ascii=name, hAnsi=name, cs=name, eastAsia=name))


def _define(doc, look: Look):
    styles = doc.styles
    if look.built_in:
        style = styles[look.name]
        for tag in ("w:pPr", "w:rPr"):  # the template has blue headings, borders, and theme fonts
            for old in style.element.findall(qn(tag)):
                style.element.remove(old)
    else:
        style = styles.add_style(look.name, WD_STYLE_TYPE.PARAGRAPH)
        style.base_style = styles["Normal"]
        style.quick_style = True
    style.font.size = Pt(look.size)
    style.font.bold = look.bold or None
    _fonts(style.element.get_or_add_rPr())
    fmt = style.paragraph_format
    fmt.alignment = look.align
    fmt.space_before, fmt.space_after = Pt(look.before), Pt(look.after)
    fmt.line_spacing = 1.15
    fmt.left_indent, fmt.first_line_indent = Cm(look.left_cm), Cm(look.first_cm)
    fmt.keep_with_next = look.keep_next or None
    if look.tab_cm is not None:
        fmt.tab_stops.add_tab_stop(Cm(look.tab_cm))
    if look.outline is not None:
        style.element.get_or_add_pPr().append(_el("outlineLvl", val=look.outline))
    return style


def _running_styles(doc) -> None:
    for name, border in (("Running Header", "bottom"), ("Running Footer", "top")):
        style = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        style.base_style = doc.styles["Normal"]
        style.font.size, style.font.italic = Pt(8.5), True
        _fonts(style.element.get_or_add_rPr())
        fmt = style.paragraph_format
        fmt.alignment, fmt.space_before, fmt.space_after, fmt.line_spacing = LEFT, Pt(0), Pt(0), 1.0
        fmt.tab_stops.add_tab_stop(Cm(TEXT_WIDTH_CM), WD_TAB_ALIGNMENT.RIGHT)
        ppr = style.element.get_or_add_pPr()
        ppr.insert(0, _el_border(border, "999999", size=4, space=2))


def _el_border(side: str, color: str, *, size: int, space: int):
    borders = _el("pBdr")
    borders.append(_el(side, val="single", sz=size, space=space, color=color))
    return borders


def _document_defaults(doc, language: str) -> None:
    """The default font and language. Word checks the spelling with this language."""
    styles = doc.styles.element
    defaults = styles.find(qn("w:docDefaults"))
    rpr = defaults.find(qn("w:rPrDefault")).find(qn("w:rPr"))
    _fonts(rpr)
    lang = rpr.find(qn("w:lang"))
    lang.set(qn("w:val"), LANGUAGES[language])
    lang.set(qn("w:eastAsia"), LANGUAGES[language])
    zoom = doc.settings.element.find(qn("w:zoom"))  # the template has a zoom without a percent
    if zoom is not None:
        zoom.set(qn("w:percent"), "100")
    # The template says "Word 2010". With 15, Word does not show "Compatibility Mode".
    for setting in doc.settings.element.iter(qn("w:compatSetting")):
        if setting.get(qn("w:name")) == "compatibilityMode":
            setting.set(qn("w:val"), "15")


# --- text, fields, tables -----------------------------------------------------------------


def _runs(paragraph, text: str, *, bold: bool = False) -> None:
    """Add the text of a paragraph, in runs. `<b>` and `</b>` switch bold on and off."""
    on = bold
    for token in re.split(r"(</?b>)", text):
        if token == "<b>":
            on = True
        elif token == "</b>":
            on = bold
        elif token:
            paragraph.add_run(unescape(token)).bold = on or None


def _field(paragraph, instruction: str) -> None:
    """A field (page number) with a cached value. Word updates it when it shows the page."""
    for part in ("begin", "instr", "separate", "text", "end"):
        run = paragraph.add_run()
        if part == "instr":
            node = _el("instrText")
            node.set(qn("xml:space"), "preserve")
            node.text = f" {instruction} "
            run._r.append(node)
        elif part == "text":
            run.text = "1"
        else:
            run._r.append(_el("fldChar", fldCharType=part))


def _footer_text(paragraph, left: str, label: str) -> None:
    paragraph.add_run(left + "\t")
    for token in re.split(r"(\{n\}|\{total\})", label):
        if token == "{n}":
            _field(paragraph, "PAGE")
        elif token == "{total}":
            _field(paragraph, "NUMPAGES")
        elif token:
            paragraph.add_run(token)


def _page(doc, meta: Meta) -> None:
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21.0), Cm(29.7)
    section.left_margin = section.right_margin = Cm(2.5)
    section.top_margin, section.bottom_margin = Cm(2.5), Cm(2.3)
    section.header_distance, section.footer_distance = Cm(1.2), Cm(0.9)
    section.different_first_page_header_footer = True  # the first page has the letterhead, not the running header
    section.first_page_header.is_linked_to_previous = False
    section.header.is_linked_to_previous = False
    section.header.paragraphs[0].style = doc.styles["Running Header"]
    section.header.paragraphs[0].add_run(meta.header)
    for footer in (section.first_page_footer, section.footer):
        footer.is_linked_to_previous = False
        footer.paragraphs[0].style = doc.styles["Running Footer"]
        _footer_text(footer.paragraphs[0], meta.footer, meta.page_label)


def _properties(doc, meta: Meta, language: str) -> None:
    props = doc.core_properties
    props.title, props.author, props.last_modified_by, props.subject = meta.title, meta.author, meta.author, meta.subject
    props.comments = props.keywords = props.category = ""
    props.created = props.modified = CREATED
    props.language = LANGUAGES[language]


def _margins(tag: str, top: int, side: int):
    margins = _el(tag)
    for name, value in (("top", top), ("left", side), ("bottom", top), ("right", side)):
        margins.append(_el(name, w=value, type="dxa"))
    return margins


def _table_borders(table, *, on: bool, top: int, side: int) -> None:
    """Lines and cell margins. The margins are in the table and in each cell: Word reads the table,
    other viewers (macOS Quick Look, for example) read only the cells."""
    props = table._tbl.tblPr
    if on:
        borders = _el("tblBorders")
        for name in ("top", "left", "bottom", "right", "insideH", "insideV"):
            borders.append(_el(name, val="single", sz=4, space=0, color="555555"))
        props.insert_element_before(borders, "w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook", "w:tblCaption", "w:tblDescription")
    props.insert_element_before(_margins("tblCellMar", top, side), "w:tblLook", "w:tblCaption", "w:tblDescription")
    for row in table.rows:
        for cell in row.cells:
            cell._tc.get_or_add_tcPr().append(_margins("tcMar", top, side))


def _table_frame(doc, rows: int, widths_cm: list[float]):
    table = doc.add_table(rows=rows, cols=len(widths_cm))
    table.autofit = False
    width = table._tbl.tblPr.find(qn("w:tblW"))
    width.set(qn("w:type"), "dxa")
    width.set(qn("w:w"), str(round(sum(widths_cm) * 567)))
    for column, cm in zip(table.columns, widths_cm):
        column.width = Cm(cm)
    for row in table.rows:
        row._tr.get_or_add_trPr().append(_el("cantSplit"))
        for cell, cm in zip(row.cells, widths_cm):
            cell.width = Cm(cm)
    return table


def _shade(cell, fill: str) -> None:
    cell._tc.get_or_add_tcPr().insert_element_before(
        _el("shd", val="clear", color="auto", fill=fill), "w:noWrap", "w:tcMar", "w:textDirection", "w:tcFitText", "w:vAlign", "w:hideMark"
    )


# --- the build ----------------------------------------------------------------------------------


class _Builder:
    def __init__(self, doc):
        self.doc = doc
        self.gap = 0.0  # space that waits for the next block (cm)
        self.page_break = False
        self.last = None  # the last block: a paragraph or a table

    def add(self, block) -> None:
        if isinstance(block, Gap):
            self.gap += block.cm
        elif isinstance(block, Break):
            self.page_break = True
        elif isinstance(block, Para):
            self.paragraph(block)
        elif isinstance(block, Grid):
            self.grid(block)
        elif isinstance(block, Signature):
            self.signature(block)
        else:
            raise TypeError(f"Unknown block: {block!r}")

    def paragraph(self, block: Para) -> None:
        look = LOOKS[block.style]
        paragraph = self.doc.add_paragraph(style=look.name)
        _runs(paragraph, block.text)
        fmt = paragraph.paragraph_format
        if self.gap:
            fmt.space_before = Pt(look.before + self.gap / 2.54 * 72)
            self.gap = 0.0
        if self.page_break:
            fmt.page_break_before = True
            self.page_break = False
        if block.rule:
            ppr = paragraph._p.get_or_add_pPr()
            ppr.insert_element_before(
                _el_border("bottom", "333333", size=8, space=4),
                "w:shd", "w:tabs", "w:spacing", "w:ind", "w:jc", "w:rPr",
            )  # fmt: skip
            fmt.space_after = Pt(4)
        self.last = block

    def before_table(self) -> None:
        """A table has no space before it. We give the space to the last paragraph, or we add a small one."""
        if self.page_break:  # a table has no `pageBreakBefore` in a style: use a paragraph with a break
            self.doc.add_page_break().paragraph_format.space_after = Pt(0)
            self.page_break = False
            self.last = None
        if self.gap:
            if isinstance(self.last, Para):
                paragraph = self.doc.paragraphs[-1]
                paragraph.paragraph_format.space_after = Pt(LOOKS[self.last.style].after + self.gap / 2.54 * 72)
            else:
                spacer = self.doc.add_paragraph(style="Small")
                spacer.paragraph_format.space_after = Pt(self.gap / 2.54 * 72)
            self.gap = 0.0

    def grid(self, block: Grid) -> None:
        self.before_table()
        table = _table_frame(self.doc, len(block.rows), block.widths)
        _table_borders(table, on=block.borders, top=50 if block.borders else 20, side=80 if block.borders else 0)
        for r, (row, values) in enumerate(zip(table.rows, block.rows)):
            if block.header and r == 0:
                row._tr.get_or_add_trPr().append(_el("tblHeader"))
            for c, (cell, value) in enumerate(zip(row.cells, values)):
                bold = (block.header and r == 0) or (block.bold_last and r == len(block.rows) - 1)
                paragraph = cell.paragraphs[0]
                paragraph.style = self.doc.styles[LOOKS["cell" if block.borders else "left"].name]
                if c in block.right_cols:
                    paragraph.alignment = RIGHT
                _runs(paragraph, value, bold=bold)
                if block.header and r == 0:
                    _shade(cell, "E8E8E8")
        self.last = block

    def signature(self, block: Signature) -> None:
        self.gap += 0.5
        self.before_table()
        pairs = list(zip(block.left, block.right))
        pairs.insert(2, ("", ""))  # the room for the signature
        table = _table_frame(self.doc, len(pairs), [8.0, 8.0])
        _table_borders(table, on=False, top=20, side=100)
        for r, (row, values) in enumerate(zip(table.rows, pairs)):
            for cell, value in zip(row.cells, values):
                paragraph = cell.paragraphs[0]
                paragraph.style = self.doc.styles[LOOKS["sig"].name]
                _runs(paragraph, value)
                paragraph.paragraph_format.keep_with_next = r < len(pairs) - 1 or None  # the block stays on one page
            if r == 2:
                row.height, row.height_rule = Cm(block.gap_cm), WD_ROW_HEIGHT_RULE.EXACTLY
        self.last = block


def build(path: Path, story: list, meta: Meta, language: str = "ro") -> None:
    doc = Document()
    _document_defaults(doc, language)
    for look in LOOKS.values():
        _define(doc, look)
    _running_styles(doc)
    _page(doc, meta)
    _properties(doc, meta, language)
    builder = _Builder(doc)
    for block in story:
        builder.add(block)
    if not isinstance(builder.last, Para):  # a document does not end with a table
        doc.add_paragraph(style="Small")
    doc.save(str(path))


__all__ = [
    "Break", "Gap", "Grid", "Meta", "PageBreak", "Para", "Signature", "article", "build", "clause",
    "grid", "letterhead", "p", "plain_table", "setup", "signatures", "space", "sub",
]  # fmt: skip
