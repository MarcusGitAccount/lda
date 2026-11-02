"""Text normalization.

Two jobs:

1. `fold` makes a copy of a text that is easy to compare. The copy has the
   same length as the original, so a match position in the copy is also a
   valid position in the original.
2. `entity_key` makes the stable key that the vault uses to decide that two
   written forms are the same entity ("Ion Popescu" and "POPESCU ION").
"""

from __future__ import annotations

import re
import unicodedata

# Romanian text often uses the old cedilla letters. The NER model needs the
# comma letters. Each pair has the same length, so offsets do not change.
CEDILLA_TO_COMMA = str.maketrans("şţŞŢ", "șțȘȚ")

_PUNCT_MAP = str.maketrans(
    {
        " ": " ",
        " ": " ",
        " ": " ",
        "‐": "-",
        "‑": "-",
        "‒": "-",
        "–": "-",
        "—": "-",
        "―": "-",
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
    }
)

_WS = re.compile(r"\s+")
_EDGE_PUNCT = " \t\r\n.,;:!?()[]{}<>\"'`-–—/\\|"


def fix_cedilla(text: str) -> str:
    return text.translate(CEDILLA_TO_COMMA)


def _fold_char(ch: str) -> str:
    ch = ch.translate(_PUNCT_MAP).translate(CEDILLA_TO_COMMA)
    base = unicodedata.normalize("NFD", ch)[:1] or ch
    low = base.lower()
    return low if len(low) == 1 else base


def fold(text: str) -> str:
    """Lower-case, remove accents, unify dashes and quotes. Same length as `text`."""
    return "".join(_fold_char(ch) for ch in text)


def collapse(text: str) -> str:
    return _WS.sub(" ", text).strip()


def strip_edges(text: str) -> str:
    return text.strip(_EDGE_PUNCT)


# --- keys ---------------------------------------------------------------

_PERSON_TITLES = {
    "dl", "dna", "d-na", "dnei", "domnul", "domnului", "doamna", "doamnei",
    "dumneaei", "dumnealui", "mr", "mrs", "ms", "miss", "mx", "dr", "av",
    "avocat", "prof", "ing", "jud", "judecator", "sir", "madam",
}

# The legal form is part of the identity: "Alfa SRL" and "Alfa SA" can be two
# companies. If we join them by mistake, the wrong company name goes into the
# restored document. A missed join only gives one more id, so we do not join.
_ORG_FORMS = {
    "srl", "sa", "snc", "scs", "sca", "pfa", "ii", "if", "ong", "ra", "ltd",
    "limited", "llc", "llp", "lp", "inc", "incorporated", "corp", "corporation",
    "co", "plc", "gmbh", "ag", "bv", "nv", "sarl", "sas", "spa", "srl-d",
}  # fmt: skip
_ORG_NOISE = {"sc", "the"}  # "SC" means "commercial company". It adds no identity.
LEGAL_FORMS = _ORG_FORMS  # for the sweep: "SRL" and "S.R.L." are one form


def _tokens(folded: str) -> list[str]:
    return [t for t in re.split(r"[\s,]+", folded) if t]


def _clean_token(token: str) -> str:
    return token.strip(_EDGE_PUNCT)


def person_key(surface: str) -> str:
    tokens = [_clean_token(t) for t in _tokens(fold(surface))]
    tokens = [t for t in tokens if t]
    while len(tokens) > 1 and tokens[0].replace(".", "") in _PERSON_TITLES:
        tokens.pop(0)
    # "Ana-Maria Popescu" and "Ana Maria Popescu" are the same name.
    parts = [part for token in tokens for part in token.split("-") if part]
    # Romanian documents write the family name first or last. Sorting makes
    # both orders give the same key.
    return " ".join(sorted(parts))


def org_key(surface: str) -> str:
    tokens = [_clean_token(t).replace(".", "") for t in _tokens(fold(surface))]
    tokens = [t for t in tokens if t and t not in _ORG_NOISE]
    name = [t for t in tokens if t not in _ORG_FORMS]
    forms = sorted({t for t in tokens if t in _ORG_FORMS})
    if not name:
        return " ".join(tokens)
    return " ".join(name) + (" |" + " ".join(forms) if forms else "")


def phone_key(surface: str) -> str:
    digits = re.sub(r"\D", "", surface)
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("40") and len(digits) == 11:
        digits = digits[2:]
    elif digits.startswith("0"):
        digits = digits[1:]
    return digits


def digits_key(surface: str) -> str:
    return re.sub(r"\D", "", surface)


def cui_key(surface: str) -> str:
    return re.sub(r"\D", "", re.sub(r"(?i)^\s*RO", "", surface))


def generic_key(surface: str) -> str:
    return collapse(strip_edges(fold(surface)))


def entity_key(entity_type: str, surface: str) -> str:
    """Return the stable key for a written form of an entity."""
    if entity_type == "PERSON":
        key = person_key(surface)
    elif entity_type == "ORGANIZATION":
        key = org_key(surface)
    elif entity_type == "PHONE_NUMBER":
        key = phone_key(surface)
    elif entity_type in {"RO_CNP", "CREDIT_CARD"}:
        key = digits_key(surface)
    elif entity_type == "RO_CUI":
        key = cui_key(surface)
    elif entity_type == "IBAN_CODE":
        key = re.sub(r"\s+", "", surface).upper()
    elif entity_type == "EMAIL_ADDRESS":
        key = surface.strip().lower()
    else:
        key = generic_key(surface)
    return key or generic_key(surface) or surface.strip().lower()
