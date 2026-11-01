"""Language detection for the two supported languages (Romanian and English).

A count of common function words is enough for two languages that differ so
much. It needs no model and gives the same answer each time.
"""

from __future__ import annotations

import re

from .textnorm import fold

SUPPORTED = ("ro", "en")

# Folded words (no accents). We use only words that exist in one language.
_RO = {
    "si", "cu", "pentru", "care", "din", "este", "sunt", "prin", "sa", "nu",
    "sau", "acest", "aceasta", "acesta", "prezentul", "prezenta", "contractul",
    "partile", "partea", "art", "conform", "dupa", "privind", "precum", "catre",
    "fata", "cand", "asupra", "fiecare", "oricare", "daca", "va", "vor",
    "fi", "au", "intre", "domiciliat", "domiciliata", "reprezentat",
    "reprezentata", "avand", "numit", "numita", "cod", "numarul", "nr",
}  # fmt: skip
_EN = {
    "the", "and", "of", "to", "is", "for", "that", "with", "shall", "this",
    "by", "or", "be", "as", "on", "are", "any", "such", "party", "parties",
    "agreement", "which", "under", "between", "hereby", "herein", "will",
    "not", "from", "has", "have", "its", "their", "all", "an", "may",
}  # fmt: skip
_DIACRITICS = re.compile("[ăâîșțşţĂÂÎȘȚŞŢ]")
_WORD = re.compile(r"[^\W\d_]+")


def detect_language(text: str) -> str:
    """Return "ro" or "en". On a tie, return "ro"."""
    words = _WORD.findall(fold(text))
    ro = sum(1 for w in words if w in _RO)
    en = sum(1 for w in words if w in _EN)
    ro += 2 * len(_DIACRITICS.findall(text)) // 3  # diacritics are a strong signal
    return "en" if en > ro else "ro"
