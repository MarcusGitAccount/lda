"""Read the text of a PDF that has a text layer.

A PDF has no paragraphs. It only has lines of text at places on a page. We
find the paragraphs again from the places:

* Lines in one row of a table or of a signature block get a tab between them.
* A line starts a new paragraph if the line before it ends early (the first
  word of the new line would have fit), if there is more space above it, if it
  has another font size, or if it starts a list item.
* Page numbers are removed. A header or footer that repeats on many pages is
  removed. Only a header on the first page stays (it can be the letterhead).

A name must not be cut in two by a line break, because the models and the
vault work on whole names. A scanned PDF has no text layer. OCR is not part of
this version, so we report it.
"""

from __future__ import annotations

import io
import re
import statistics
from collections import Counter
from dataclasses import dataclass

from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTChar, LTTextLine

MAX_PAGES = 500
MARGIN_BAND = 0.09  # top and bottom part of a page where we look for headers and footers
SAME_SIZE = 0.12
NEW_PARAGRAPH_PITCH = 1.3  # times the usual distance between two lines

_LIGATURES = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"}
_SPACES = dict.fromkeys(map(ord, "       "), " ")
_REMOVE = dict.fromkeys(map(ord, "­​‌‍﻿"))
_CLEAN = str.maketrans({**_SPACES, **_REMOVE, **{ord(k): v for k, v in _LIGATURES.items()}})

_MARKER = re.compile(r"^(\d+(\.\d+)*[.)]?|[a-zA-Z][.)]|[ivxIVX]+[.)]|\(\w{1,4}\)|[-•–—▪●○])\s")
_MARKER_ONLY = re.compile(r"^(\d+(\.\d+)*[.)]?|[a-zA-Z][.)]|[ivxIVX]+[.)]|\(\w{1,4}\)|[-•–—▪●○])$")
_PAGE_NUMBER = re.compile(r"^(pagina|page|pag\.?|p\.)?\s*#(\s*(din|of|/)\s*#)?$")
_SENTENCE_END = ".;:!?)\"”"


class PdfError(ValueError):
    pass


@dataclass
class _Line:
    text: str
    x0: float
    x1: float
    y0: float
    y1: float
    size: float
    bold: bool
    first_word: float  # width of the first word

    @property
    def mid(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class _Row:
    text: str
    x0: float
    x1: float
    mid: float
    size: float
    bold: bool
    is_table: bool
    first_word: float


def _clean(text: str) -> str:
    return re.sub(r"[ ]{2,}", " ", text.translate(_CLEAN).replace("\n", " ")).strip()


def _first_word_width(line: LTTextLine) -> float:
    start = end = None
    for item in line:
        if isinstance(item, LTChar) and not item.get_text().isspace():
            start = item.x0 if start is None else start
            end = item.x1
        elif start is not None:  # a space ends the word
            break
    return 0.0 if start is None else end - start


def _collect(container, out: list[_Line]) -> None:
    for child in container:
        if isinstance(child, LTTextLine):
            text = _clean(child.get_text())
            chars = [c for c in child if isinstance(c, LTChar) and not c.get_text().isspace()]
            if text and chars:
                bold = sum("bold" in c.fontname.lower() or "black" in c.fontname.lower() for c in chars) * 2 > len(chars)
                size = statistics.median(c.size for c in chars)
                out.append(_Line(text, child.x0, child.x1, child.y0, child.y1, size, bold, _first_word_width(child)))
        elif hasattr(child, "__iter__"):  # a text box or a figure
            _collect(child, out)


def _rows(lines: list[_Line]) -> list[_Row]:
    """Put the lines that are at the same height into one row. Rows go from top to bottom."""
    groups: list[list[_Line]] = []
    for line in sorted(lines, key=lambda item: -item.mid):
        if groups:
            first = groups[-1][0]
            overlap = min(first.y1, line.y1) - max(first.y0, line.y0)
            if overlap > 0.5 * min(first.y1 - first.y0, line.y1 - line.y0):
                groups[-1].append(line)
                continue
        groups.append([line])
    rows = []
    for group in groups:
        group.sort(key=lambda item: item.x0)
        text = group[0].text
        gaps = [after.x0 - before.x1 for before, after in zip(group, group[1:])]
        # A justified line has wide spaces, and all of them have the same width. It is text,
        # not a table. (The first gap can be the hanging indent of a clause number.)
        measured = gaps[1:] if _MARKER_ONLY.match(group[0].text) else gaps
        justified = len(measured) >= 3 and min(measured) > 0 and statistics.pstdev(measured) < 0.3 * statistics.mean(measured)
        for (before, after), gap in zip(zip(group, group[1:]), gaps):
            # The PDF reader already joins words that are close. Two pieces in one row are
            # two columns of a table. The exception is the number of a clause or of a list
            # item (a hanging indent).
            wide = gap > 0.5 * before.size and not justified and not _MARKER_ONLY.match(before.text)
            text += ("\t" if wide else " ") + after.text
        biggest = max(group, key=lambda item: item.x1 - item.x0)
        rows.append(
            _Row(
                text, group[0].x0, group[-1].x1, sum(i.mid for i in group) / len(group), biggest.size, biggest.bold,
                "\t" in text, group[0].first_word,
            )
        )
    return rows


def _normal(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\d+", "#", text.lower())).strip()


@dataclass
class _Context:
    left: float  # the left edge of the text
    right: float  # the right edge of the text
    pitch: float  # the usual distance between two lines of one paragraph

    def centered(self, row: _Row) -> bool:
        width = self.right - self.left
        return abs((row.x0 + row.x1) / 2 - (self.left + self.right) / 2) < 0.008 * width

    def narrow(self, row: _Row) -> bool:
        return (row.x1 - row.x0) < 0.97 * (self.right - self.left)


def _context(pages: list[list[_Row]], page_width: float) -> _Context:
    wide = [r for rows in pages for r in rows if not r.is_table and (r.x1 - r.x0) > 0.4 * page_width]
    right = statistics.quantiles([r.x1 for r in wide], n=10)[-1] if len(wide) >= 10 else (max((r.x1 for r in wide), default=page_width - 70))
    left = statistics.quantiles([r.x0 for r in wide], n=10)[0] if len(wide) >= 10 else (min((r.x0 for r in wide), default=70))
    pitches = []
    for rows in pages:
        for before, after in zip(rows, rows[1:]):
            if not before.is_table and not after.is_table and abs(before.size - after.size) < 0.5:
                pitches.append(before.mid - after.mid)
    return _Context(left, right, statistics.median(pitches) if pitches else 14.0)


def _starts_paragraph(before: _Row, after: _Row, ctx: _Context) -> bool:
    if abs(before.size - after.size) > SAME_SIZE * before.size:
        return True
    # A bold word at the start of a line is often a defined term, not a heading. A heading in capitals is.
    if after.bold and not before.bold and after.text.isupper():
        return True
    if before.mid - after.mid > NEW_PARAGRAPH_PITCH * ctx.pitch:
        return True
    # The line before is short: the first word of this line would have fitted.
    needed = after.first_word + 0.3 * before.size  # the word and a space
    if before.x1 + needed <= ctx.right + 0.5 * before.size:
        return True
    if ctx.centered(before) and ctx.centered(after) and (ctx.narrow(before) or ctx.narrow(after)):
        return False  # a title on two lines
    if after.x0 - before.x0 > 1.2 * before.size and not _MARKER.match(before.text):
        return True  # indent of the first line
    return bool(_MARKER.match(after.text)) and before.text[-1:] in _SENTENCE_END


def _join(lines: list[str]) -> str:
    text = lines[0]
    for line in lines[1:]:
        if re.search(r"[^\W\d_]-$", text) and line[:1].islower():
            text = text[:-1] + line  # "con-" + "tract": a word cut at the end of a line
        elif re.search(r"[^\W\d_]-$", text) and line[:1].isupper():
            text += line  # "Cluj-" + "Napoca": the hyphen is part of the name
        else:
            text += " " + line
    return text


def _blocks(rows: list[_Row], ctx: _Context) -> list[str]:
    blocks: list[list[_Row]] = []
    for row in rows:
        if blocks:
            before = blocks[-1][-1]
            if row.is_table and before.is_table and before.mid - row.mid <= NEW_PARAGRAPH_PITCH * ctx.pitch * 1.4:
                blocks[-1].append(row)
                continue
            if not row.is_table and not before.is_table and not _starts_paragraph(before, row, ctx):
                blocks[-1].append(row)
                continue
        blocks.append([row])
    return ["\n".join(r.text for r in b) if b[0].is_table else _join([r.text for r in b]) for b in blocks]


def _read(data: bytes) -> tuple[list[list[_Row]], float, list[float]]:
    pages, heights, width = [], [], 0.0
    try:
        for number, page in enumerate(extract_pages(io.BytesIO(data), laparams=LAParams(detect_vertical=False, char_margin=1.0)), 1):
            if number > MAX_PAGES:
                raise PdfError(f"The PDF has more than {MAX_PAGES} pages.")
            lines: list[_Line] = []
            _collect(page, lines)
            # A page number can be next to the text of a footer. Remove it before we make the rows.
            lines = [
                line for line in lines
                if not (_in_margin(line.mid, page.height) and _PAGE_NUMBER.match(_normal(line.text)))
            ]
            pages.append(_rows(lines))
            heights.append(page.height)
            width = max(width, page.width)
    except PdfError:
        raise
    except Exception as error:
        # pdfminer raises many kinds of errors for a broken or locked file.
        raise PdfError(f"The PDF cannot be read ({type(error).__name__}). Is it locked with a password?") from error
    return pages, width, heights


def _in_margin(mid: float, height: float) -> bool:
    return mid > height * (1 - MARGIN_BAND) or mid < height * MARGIN_BAND


def _drop_running_text(pages: list[list[_Row]], heights: list[float]) -> list[list[_Row]]:
    """Remove the header and footer text that repeats on many pages.

    A footer goes from all pages. A header stays on the first page, because it can be the
    letterhead of the document.
    """
    seen = Counter(
        key
        for rows, height in zip(pages, heights)
        for key in {_normal(r.text) for r in rows if _in_margin(r.mid, height)}
    )
    repeated = {key for key, count in seen.items() if count >= max(2, len(pages) / 2)}

    def keep(row: _Row, index: int, height: float) -> bool:
        if not (_in_margin(row.mid, height) and _normal(row.text) in repeated):
            return True
        return index == 0 and row.mid > height / 2  # a header on the first page

    return [[r for r in rows if keep(r, index, height)] for index, (rows, height) in enumerate(zip(pages, heights))]


def pdf_text(data: bytes) -> str:
    """Return the text of a PDF. Paragraphs are separated by an empty line."""
    pages, width, heights = _read(data)
    if not pages:
        raise PdfError("The PDF has no pages.")
    if not any(pages):
        raise PdfError(
            "The PDF has no text layer. It may be a scan. This version has no OCR. "
            "Make a text version first (for example with OCR in your PDF program)."
        )
    pages = _drop_running_text(pages, heights)
    ctx = _context(pages, width)
    texts: list[str] = []
    for number, rows in enumerate(pages, 1):
        if not rows:
            texts.append(f"[Page {number} has no text layer. It was skipped.]")
            continue
        blocks = _blocks(rows, ctx)
        # A paragraph can go on at the top of the next page.
        if texts and blocks and "\n" not in texts[-1] and texts[-1][-1:] not in _SENTENCE_END and blocks[0][:1].islower():
            texts[-1] = _join([texts[-1], blocks.pop(0)])
        texts.extend(blocks)
    text = "\n\n".join(texts)
    if text.count("(cid:") > 0.05 * max(len(text.split()), 1):
        raise PdfError("The fonts of the PDF have no text map, so the text cannot be read. Make a text version first.")
    return text
