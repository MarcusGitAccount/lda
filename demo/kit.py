"""The building blocks that the demo documents use: `p`, `article`, `clause`, `grid` and so on.

The text of the documents is written one time (docs_ro.py, docs_firm.py, docs_en.py). The
blocks go to the PDF layout (layout.py) or to the Word layout (docx_layout.py). Choose with
`use()` before you call a document function. The PDF layout is the default.
"""

from __future__ import annotations

from . import layout

Meta = layout.Meta
_backend = layout


def use(backend) -> None:
    global _backend
    _backend = backend


def p(*args, **kwargs):
    return _backend.p(*args, **kwargs)


def article(*args, **kwargs):
    return _backend.article(*args, **kwargs)


def clause(*args, **kwargs):
    return _backend.clause(*args, **kwargs)


def sub(*args, **kwargs):
    return _backend.sub(*args, **kwargs)


def space(*args, **kwargs):
    return _backend.space(*args, **kwargs)


def letterhead(*args, **kwargs):
    return _backend.letterhead(*args, **kwargs)


def grid(*args, **kwargs):
    return _backend.grid(*args, **kwargs)


def plain_table(*args, **kwargs):
    return _backend.plain_table(*args, **kwargs)


def signatures(*args, **kwargs):
    return _backend.signatures(*args, **kwargs)


def PageBreak():  # the name is the one of the reportlab class
    return _backend.PageBreak()
