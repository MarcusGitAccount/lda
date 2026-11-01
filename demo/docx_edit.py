"""A simulated AI tool for the Word demo. It edits an anonymized .docx with tracked changes.

A real AI tool (Claude Code, Codex, Copilot) gets the hidden file and changes the text. Here a
script does it, so the demo gives the same result each time. The changes are real Word
tracked changes (`w:ins` and `w:del`) by "AI assistant". The lawyer can accept or reject them
in Word. The new text can hold ids such as [ORG_001]: the tool puts the real names back later.
"""

from __future__ import annotations

import copy
import io

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

AUTHOR = "AI assistant"
DATE = "2025-06-20T10:00:00Z"


def _node(tag: str, **attributes: str | int):
    element = OxmlElement(f"w:{tag}")
    for key, value in attributes.items():
        element.set(qn(f"w:{key}"), str(value))
    return element


def _text(tag: str, value: str):
    element = _node(tag)
    element.set(qn("xml:space"), "preserve")
    element.text = value
    return element


class Redline:
    """Tracked changes in one .docx file (as bytes)."""

    def __init__(self, data: bytes, author: str = AUTHOR):
        self.doc = Document(io.BytesIO(data))
        self.author = author
        self._ids = iter(range(9000, 99000))

    def _mark(self, tag: str):
        return _node(tag, id=next(self._ids), author=self.author, date=DATE)

    def _find(self, snippet: str):
        for paragraph in self.doc.element.body.iter(qn("w:p")):
            if snippet in "".join(t.text or "" for t in paragraph.iter(qn("w:t"))):
                return paragraph
        raise ValueError(f"No paragraph has the text '{snippet}'.")

    def replace(self, old: str, new: str, *, in_paragraph: str | None = None) -> None:
        """Delete `old` and insert `new`, as a tracked change. `old` must be inside one text run."""
        paragraph = self._find(in_paragraph or old)
        for t in paragraph.iter(qn("w:t")):
            tracked = next(t.iterancestors(qn("w:ins"), qn("w:del")), None) is not None
            if old in (t.text or "") and not tracked:
                self._replace_in(t, old, new)
                return
        raise ValueError(f"'{old}' is not inside one text run of the paragraph.")

    def _replace_in(self, t, old: str, new: str) -> None:
        run = t.getparent()
        properties = run.find(qn("w:rPr"))
        parts = [child for child in run if child is not properties]
        index = parts.index(t)
        before, _, after = t.text.partition(old)

        def new_run(children: list):
            result = _node("r")
            if properties is not None:
                result.append(copy.deepcopy(properties))
            for child in children:
                result.append(child)
            return result

        head = [copy.deepcopy(c) for c in parts[:index]] + ([_text("t", before)] if before else [])
        tail = ([_text("t", after)] if after else []) + [copy.deepcopy(c) for c in parts[index + 1 :]]
        deleted, inserted = self._mark("del"), self._mark("ins")
        deleted.append(new_run([_text("delText", old)]))
        inserted.append(new_run([_text("t", new)]))
        nodes = [*([new_run(head)] if head else []), deleted, inserted, *([new_run(tail)] if tail else [])]
        parent = run.getparent()
        position = parent.index(run)
        parent.remove(run)
        for offset, node in enumerate(nodes):
            parent.insert(position + offset, node)

    def insert_paragraph_after(self, anchor: str, text: str, label: str = "") -> None:
        """Add a paragraph after the one that has `anchor`, as a tracked change. It has the same style."""
        after = self._find(anchor)
        properties = copy.deepcopy(after.find(qn("w:pPr"))) if after.find(qn("w:pPr")) is not None else _node("pPr")
        for old in properties.findall(qn("w:rPr")):
            properties.remove(old)
        mark = _node("rPr")  # the mark of the paragraph is new too
        mark.append(self._mark("ins"))
        properties.append(mark)
        run = _node("r")
        if label:
            run.append(_text("t", label))
            run.append(_node("tab"))
        run.append(_text("t", text))
        inserted = self._mark("ins")
        inserted.append(run)
        paragraph = _node("p")
        paragraph.append(properties)
        paragraph.append(inserted)
        after.addnext(paragraph)

    def save(self) -> bytes:
        buffer = io.BytesIO()
        self.doc.save(buffer)
        return buffer.getvalue()
