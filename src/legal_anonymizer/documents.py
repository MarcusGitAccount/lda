"""Read and write documents.

The engine works on a list of "units" (paragraphs of text). A document class
gives the units and writes the changed units back into the same file format.
For .docx we change only the text nodes. The styles, tables and images stay.
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field
from html import unescape
from pathlib import PurePosixPath
from typing import Protocol

from lxml import etree

from .pdftext import PdfError, pdf_text

# (start, end, new text), with positions inside one unit
Replacement = tuple[int, int, str]

TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".text"}
MAX_DOCX_BYTES = 200 * 1024 * 1024  # a limit on the unpacked size (zip bombs)
MAX_DOCX_ENTRIES = 5000


class UnsupportedFormat(ValueError):
    pass


class Document(Protocol):
    def units(self) -> list[str]: ...

    def rewrite(self, replacements: list[list[Replacement]], *, scrub: bool = False) -> bytes: ...


def apply_replacements(text: str, replacements: list[Replacement]) -> str:
    for start, end, new in sorted(replacements, reverse=True):
        text = text[:start] + new + text[end:]
    return text


# --- plain text and Markdown ------------------------------------------------------


class TextDocument:
    def __init__(self, data: bytes):
        try:
            self.text = data.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ValueError("The file is not UTF-8 text. Save it as UTF-8 and try again.") from error

    def units(self) -> list[str]:
        return [self.text]

    def rewrite(self, replacements: list[list[Replacement]], *, scrub: bool = False) -> bytes:
        return apply_replacements(self.text, replacements[0]).encode("utf-8")


# --- Word (.docx) ----------------------------------------------------------------

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def _w(tag: str) -> str:
    return f"{{{W}}}{tag}"


P, R = _w("p"), _w("r")
TEXT_TAGS = (_w("t"), _w("delText"))
# Characters that are not in a text node. We show them as a character in the unit
# text, so that two words are not joined. A span never contains \t or \n.
INLINE_TAGS = {_w("tab"): "\t", _w("br"): "\n", _w("cr"): "\n", _w("noBreakHyphen"): "-"}

PROCESSED_PARTS = re.compile(
    r"^word/(document|footnotes|endnotes|comments\w*|header\d*|footer\d*)\.xml$"
)
METADATA_FIELDS = {
    "docProps/core.xml": {"creator", "lastModifiedBy", "title", "subject", "description", "keywords", "category"},
    "docProps/app.xml": {"Company", "Manager"},
}

_PARSER = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)


@dataclass
class _Node:
    el: etree._Element | None  # None for a gap that we add
    start: int
    end: int
    kind: str  # "text", "inline" or "gap"


@dataclass
class _Unit:
    text: str
    nodes: list[_Node] = field(default_factory=list)

    def apply(self, replacements: list[Replacement]) -> None:
        for node in self.nodes:
            if node.kind == "text":
                pieces, pos = [], node.start
                for start, end, new in replacements:
                    if end <= node.start or start >= node.end:
                        continue
                    if start > pos:
                        pieces.append(self.text[pos : min(start, node.end)])
                    if node.start <= start < node.end:
                        pieces.append(new)
                    pos = max(pos, min(end, node.end))
                if pos < node.end:
                    pieces.append(self.text[pos : node.end])
                node.el.text = "".join(pieces)
                node.el.set(XML_SPACE, "preserve")
            elif node.kind == "inline" and node.el.tag == _w("noBreakHyphen"):
                # A hyphen inside a hidden name must go too.
                if any(s <= node.start and node.end <= e for s, e, _ in replacements):
                    node.el.getparent().remove(node.el)


def _collect_units(root: etree._Element) -> list[_Unit]:
    groups: dict[etree._Element, list[etree._Element]] = {}
    for el in root.iter(*TEXT_TAGS, *INLINE_TAGS):
        parent = el.getparent()
        if parent is None or parent.tag != R:  # for example a tab stop in a style
            continue
        paragraph = next(el.iterancestors(P), None)
        if paragraph is not None:
            groups.setdefault(paragraph, []).append(el)
    units = []
    for elements in groups.values():
        unit, parts, pos = _Unit(""), [], 0
        deleted = False
        for el in elements:
            # Deleted text (tracked changes) is next to the new text, with no space.
            # A gap keeps the words apart, so the model can read both.
            if (el.tag == _w("delText")) != deleted and pos:
                unit.nodes.append(_Node(None, pos, pos + 1, "gap"))
                parts.append(" ")
                pos += 1
            deleted = el.tag == _w("delText")
            text = (el.text or "") if el.tag in TEXT_TAGS else INLINE_TAGS[el.tag]
            kind = "text" if el.tag in TEXT_TAGS else "inline"
            unit.nodes.append(_Node(el, pos, pos + len(text), kind))
            parts.append(text)
            pos += len(text)
        unit.text = "".join(parts)
        units.append(unit)
    return units


def _open_zip(data: bytes) -> zipfile.ZipFile:
    try:
        zin = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as error:
        raise ValueError("The file is not a valid .docx file.") from error
    infos = zin.infolist()
    if len(infos) > MAX_DOCX_ENTRIES or sum(i.file_size for i in infos) > MAX_DOCX_BYTES:
        raise ValueError("The .docx file is too large to process safely.")
    return zin


class DocxDocument:
    def __init__(self, data: bytes):
        zin = _open_zip(data)
        infos = zin.infolist()
        self._infos = infos
        self._raw = {i.filename: zin.read(i) for i in infos}
        if "word/document.xml" not in self._raw:
            raise ValueError("The file is not a Word document (word/document.xml is missing).")
        self._trees = {
            name: etree.fromstring(raw, _PARSER)
            for name, raw in sorted(self._raw.items())
            if PROCESSED_PARTS.match(name)
        }
        self._units: list[_Unit] = []
        for root in self._trees.values():
            self._units.extend(_collect_units(root))

    def units(self) -> list[str]:
        return [u.text for u in self._units]

    def rewrite(self, replacements: list[list[Replacement]], *, scrub: bool = False) -> bytes:
        for unit, repls in zip(self._units, replacements):
            if repls:
                unit.apply(sorted(repls))
        out = dict(self._raw)
        if scrub:
            self._scrub(out)
        for name, root in self._trees.items():
            out[name] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in self._infos:
                zout.writestr(info.filename, out[info.filename], zipfile.ZIP_DEFLATED)
        return buffer.getvalue()

    def _scrub(self, out: dict[str, bytes]) -> None:
        """Remove names of authors from the metadata and from the tracked changes."""
        for root in self._trees.values():
            for el in root.iter():
                if _w("author") in el.attrib:
                    el.set(_w("author"), "Author")
                if _w("initials") in el.attrib:
                    el.set(_w("initials"), "A")
        for name, fields in METADATA_FIELDS.items():
            if name in out:
                tree = etree.fromstring(out[name], _PARSER)
                for el in tree.iter():
                    if isinstance(el.tag, str) and etree.QName(el).localname in fields:
                        el.text = ""
                out[name] = etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)


# --- PDF (read only) ------------------------------------------------------------


class PdfDocument(TextDocument):
    """The text of a PDF. The output is UTF-8 text, not a PDF."""

    def __init__(self, data: bytes):
        try:
            self.text = pdf_text(data)
        except PdfError as error:
            raise UnsupportedFormat(str(error)) from error


def scan_text(name: str, data: bytes) -> str:
    """All text of a file, also of the .docx parts that we do not change.

    The leak check uses it on the output file. Tags are removed without a space,
    so a name that is split into runs is in one piece again.
    """
    suffix = PurePosixPath(name).suffix.lower()
    if suffix == ".pdf" and data.startswith(b"%PDF-"):
        return PdfDocument(data).text
    if suffix != ".docx":
        return TextDocument(data).text
    parts = []
    with _open_zip(data) as z:
        for info in z.infolist():
            if info.filename.endswith((".xml", ".rels")):
                raw = z.read(info.filename).decode("utf-8", errors="ignore")
                parts.append(raw if info.filename.endswith(".rels") else unescape(re.sub(r"<[^>]+>", "", raw)))
    return "\n".join(parts)


def open_document(name: str, data: bytes) -> Document:
    suffix = PurePosixPath(name).suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return TextDocument(data)
    if suffix == ".docx":
        return DocxDocument(data)
    if suffix == ".pdf":
        return PdfDocument(data)
    raise UnsupportedFormat(f"'{name}': format '{suffix}' is not supported. Use .txt, .md, .docx or .pdf (with a text layer).")
