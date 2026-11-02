"""Romanian word forms for names (lexemes).

A Romanian name changes with its role in the sentence:

    Popescu  -> Popescul, Popescului, Popescule   (with the article, genitive or dative, vocative)
    Popescu  -> Popeștii, Popeștilor              (the family)
    Maria    -> Mariei                            (genitive or dative)
    Brașov   -> Brașovului
    București -> Bucureștiului, Iași -> Iașului

The vault knows one written form. The document can have another form of the same word. This module
lists the forms. It does not stem. A stemmer would join `Pop` and `Popa`, two names that can belong
to two people. We only join two words when one of them is a form that a rule below makes from the other.

All words here are folded (lower case, no accents), as `textnorm.fold` writes them. The functions
fold their input, so the caller can pass any written form.
"""

from __future__ import annotations

from functools import lru_cache
from itertools import permutations

from .textnorm import fold

MIN_WORD = 3  # a shorter word gets no forms
_VOWELS = "aeiou"

# Name types that change their form. A company name does not (the legal form follows it).
INFLECTED_TYPES = {"PERSON", "LOCATION"}


@lru_cache(maxsize=8192)
def inflections(word: str) -> frozenset[str]:
    """The other forms of a base word. The word itself is not in the result."""
    w = fold(word)
    if len(w) < MIN_WORD or not w[-1].isalpha():
        return frozenset()
    forms: set[str] = set()
    last = w[-1]
    if last == "u":  # Popescu, Radu
        forms |= {w + s for s in ("l", "lui", "le")}
        if w.endswith("escu"):  # Popescu -> Popești, Popeștii, Popeștilor
            plural = w[:-2] + "ti"
            forms |= {plural, plural + "i", plural + "lor"}
    elif last == "a":  # Maria, Ioana, Timișoara, Cluj-Napoca
        stem = w[:-1]
        forms.add(stem + "ei")
        if stem.endswith(("c", "g")):
            forms.add(stem + "ii")
    elif last == "i":  # București, Iași, Mihai
        forms |= {w + s for s in ("ul", "ului")}
        forms |= {w[:-1] + s for s in ("ul", "ului")}
    elif last not in _VOWELS:  # Ion, Brașov
        forms |= {w + s for s in ("ul", "ului", "ule")}
    forms.discard(w)
    return frozenset(forms)


@lru_cache(maxsize=8192)
def bases(word: str) -> frozenset[str]:
    """The words that can have made this form. The rules go the other way round. It can list a few words
    that are not real; that does no harm, because the caller only looks for a word that the vault knows."""
    w = fold(word)
    found: set[str] = set()
    if w.endswith("ului"):
        found |= {w[:-4], w[:-4] + "i"}  # Brașov-ului, Iaș-ului (Iași)
    if w.endswith("lui"):
        found.add(w[:-3])  # Popescu-lui
    if w.endswith("ule"):
        found.add(w[:-3])  # Ion-ule
    if w.endswith("le"):
        found.add(w[:-2])  # Popescu-le
    if w.endswith("ul"):
        found |= {w[:-2], w[:-1], w[:-2] + "i"}  # Ion-ul, Popescu-l, Iaș-ul
    if w.endswith(("ei", "ii")):
        found.add(w[:-2] + "a")  # Mari-ei -> Maria, Napoc-ii -> Napoca
    for suffix, cut in (("estilor", 5), ("estii", 3), ("esti", 2)):
        if w.endswith(suffix):
            found.add(w[:-cut] + "cu")  # Popeștii -> Popescu
            break
    return frozenset(b for b in found if len(b) >= MIN_WORD)


@lru_cache(maxsize=8192)
def related(word: str) -> frozenset[str]:
    """The word, its other forms, its base, and the forms of the base."""
    w = fold(word)
    found = {w} | inflections(w)
    for base in bases(w):
        found.add(base)
        found |= inflections(base)
    return frozenset(found)


def same_word(a: str, b: str) -> bool:
    return fold(b) in related(a)


def _pairs(a: list[str], b: list[str], ordered: bool):
    if len(a) != len(b):
        return
    if ordered:
        yield list(zip(a, b))
    else:  # a person's name: the order of the words is free
        for order in permutations(b):
            yield list(zip(a, order))


def same_lexeme(a: list[str], b: list[str], *, ordered: bool = True) -> bool:
    """True if the two lists of words are the same name in other forms."""
    return any(all(same_word(x, y) for x, y in pairs) for pairs in _pairs(a, b, ordered))


def derives_from(form: list[str], base: list[str], *, ordered: bool = True) -> bool:
    """True if `form` is made from `base` (at least one word differs, and each differing word is an inflection)."""
    for pairs in _pairs(form, base, ordered):
        if all(x == y or fold(x) in inflections(y) for x, y in pairs) and any(x != y for x, y in pairs):
            return True
    return False
