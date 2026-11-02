"""A text span with a type, and the rules to clean and combine spans."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from .entities import priority
from .romanian import inflections
from .textnorm import fold, generic_key

# Rank of a span from the vault or from the user's seed list. It wins over all.
VAULT_RANK = -1


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    type: str
    score: float = 1.0
    source: str = ""

    @property
    def length(self) -> int:
        return self.end - self.start

    @property
    def rank(self) -> int:
        return VAULT_RANK if self.source == "vault" else priority(self.type)

    def text(self, full: str) -> str:
        return full[self.start : self.end]


# --- role words and titles ------------------------------------------------------

# Words for the role of a party. They are not private, and the reader needs them.
ROLE_WORDS = {
    # Romanian
    "prestator", "prestatorul", "prestatoare", "beneficiar", "beneficiarul",
    "beneficiara", "vanzator", "vanzatorul", "cumparator", "cumparatorul",
    "client", "clientul", "furnizor", "furnizorul", "locator", "locatorul",
    "locatar", "locatarul", "chirias", "chiriasul", "proprietar",
    "proprietarul", "imprumutat", "imprumutator", "creditor", "creditorul",
    "debitor", "debitorul", "reclamant", "reclamantul", "reclamanta", "parat",
    "paratul", "parata", "intimat", "intimatul", "intimata", "apelant",
    "apelantul", "contestator", "petent", "petentul", "administrator",
    "administratorul", "director", "directorul", "asociat", "asociatul",
    "mandant", "mandatar", "angajator", "angajatorul", "salariat",
    "salariatul", "parte", "parti", "partea", "partile", "societatea",
    "compania", "subsemnatul", "subsemnata", "cedent", "cesionar", "garant",
    "avocat", "avocatul", "notar", "notarul", "expert", "martor", "martorul",
    "martora", "reprezentant", "reprezentantul", "imputernicit", "lichidator",
    "executor", "executorul", "inculpat", "inculpatul", "inculpata",
    # English
    "claimant", "defendant", "plaintiff", "respondent", "applicant",
    "appellant", "petitioner", "seller", "buyer", "purchaser", "vendor",
    "lessor", "lessee", "landlord", "tenant", "borrower", "lender", "licensor",
    "licensee", "employer", "employee", "contractor", "customer", "supplier",
    "provider", "company", "party", "parties", "manager", "officer",
    "shareholder", "guarantor", "assignor", "assignee", "trustee", "witness",
    "attorney", "lawyer", "counsel", "agent", "representative", "owner",
    "debtor", "principal", "consultant", "partner", "advocate",
    "judge", "justice", "president", "registrar", "rapporteur", "secretary",
    "general",
    "exporter", "importer", "carrier", "consignee", "consignor", "shipper",
    "forwarder", "mediator", "interpreter", "solicitor", "insurer", "bank",
    "bidder", "tenderer", "subcontractor", "sub-contractor",
    # Romanian court roles
    "judecator", "judecatorul", "magistrat", "procuror", "procurorul",
    "presedinte", "presedintele", "grefier", "grefierul", "raportor",
}  # fmt: skip

# Romanian nouns change their end for the case and the number: "beneficiarul",
# "beneficiarului", "beneficiarii". We make these forms from the base form.
_RO_ROLE_STEMS = [
    "prestator", "beneficiar", "vanzator", "cumparator", "client", "furnizor",
    "locator", "locatar", "chirias", "proprietar", "imprumutat", "imprumutator",
    "creditor", "debitor", "reclamant", "parat", "intimat", "apelant",
    "contestator", "petent", "administrator", "director", "asociat", "mandant",
    "mandatar", "angajator", "salariat", "cedent", "cesionar", "garant",
    "avocat", "notar", "expert", "martor", "reprezentant", "imputernicit",
    "lichidator", "executor", "inculpat", "judecator", "magistrat", "procuror",
    "presedinte", "grefier", "raportor", "sofer", "dispecer", "transportator",
    "destinatar", "expeditor", "exportator", "importator", "emitent", "platitor",
    "mediator", "traducator", "interpret", "subcontractor", "ofertant", "cabinet",
]  # fmt: skip
_RO_SUFFIXES = ["", "ul", "ului", "i", "ii", "ilor", "lor", "a", "ei", "e", "ele", "elor"]


def _romanian_role_forms() -> set[str]:
    forms = set()
    for stem in _RO_ROLE_STEMS:
        forms.update(stem + suffix for suffix in _RO_SUFFIXES)
        if stem.endswith("tor"):  # the feminine form: prestator -> prestatoare
            base = stem[:-2] + "oare"
            forms.update({base, base + "a", base + "i", base + "ei", base + "lor"})
    return forms


ROLE_WORDS |= _romanian_role_forms()


def is_role(word: str) -> bool:
    """`word` is folded. English plural and possessive forms count as the role."""
    return word in ROLE_WORDS or word.removesuffix("'s") in ROLE_WORDS or word.removesuffix("s") in ROLE_WORDS


TITLES = {
    "dl", "dna", "d-na", "dnei", "domnul", "domnului", "doamna", "doamnei",
    "domnisoara", "mr", "mrs", "ms", "miss", "mx", "dr", "prof", "ing", "av",
    "sir", "madam", "the", "a", "an", "lui", "al", "ai", "ale",
    "domnule", "domnilor", "doamnelor", "dna.", "stimate", "stimata",
}  # fmt: skip

# These need no hiding in most cases. Add more with the `keep` option.
DEFAULT_KEEP = [
    "Romania", "România", "Republica Moldova", "Moldova", "Uniunea Europeană",
    "Uniunea Europeana", "European Union", "UE", "EU", "Europa", "Europe",
    "Statele Unite ale Americii", "Statele Unite", "SUA", "USA", "United States",
    "United States of America", "Regatul Unit", "United Kingdom", "UK",
    "Marea Britanie", "Great Britain", "England", "Anglia", "Wales", "England and Wales",
    "Scotland", "Northern Ireland", "Germania", "Germany",
    "Franța", "Franta", "France", "Italia", "Italy", "Spania", "Spain", "Ungaria",
    "Hungary", "Bulgaria", "Ucraina", "Ukraine", "Polonia", "Poland", "Austria",
    "Olanda", "Țările de Jos", "Netherlands", "Belgia", "Belgium", "Grecia",
    "Greece", "Turcia", "Turkey", "Elveția", "Elvetia", "Switzerland", "China",
    "Rusia", "Russia", "Canada", "Irlanda", "Ireland", "Cipru", "Cyprus",
    "Luxemburg", "Luxembourg", "Portugalia", "Portugal", "Suedia", "Sweden",
    "Danemarca", "Denmark", "Norvegia", "Norway", "Finlanda", "Finland",
    "Cehia", "Czechia", "Slovacia", "Slovakia", "Croația", "Croatia", "Serbia",
    # The genitive of the names that are not made by a rule (see `keep_set`).
    "Uniunii Europene", "Republicii Moldova", "Regatului Unit", "Marii Britanii",
    "Statelor Unite ale Americii", "Statelor Unite", "Țărilor de Jos",
    # Labels of fields. They are not private. The value that follows is.
    "IBAN", "CNP", "CUI", "CIF", "VAT", "TVA", "SWIFT", "BIC", "SWIFT/BIC", "ORC", "CI", "BI",
    # Names of laws and treaties. They are not private.
    "CMR", "GDPR", "UK GDPR",
]  # fmt: skip


# A body that starts with one of these words is a public body, if it has no
# company form (SRL, Ltd ...). Public bodies are often not secret.
PUBLIC_BODY_WORDS = {
    "tribunalul", "tribunal", "curtea", "judecatoria", "inalta", "parchetul",
    "ministerul", "guvernul", "parlamentul", "senatul", "camera", "comisia",
    "consiliul", "agentia", "autoritatea", "primaria", "prefectura",
    "directia", "inspectoratul", "oficiul", "uniunea", "registrul",
    "administratia", "casa", "serviciul", "baroul", "court",
    # forms with another case ("Tribunalului", "Curții")
    "tribunalului", "curtii", "judecatoriei", "parchetului", "ministerului", "guvernului",
    "parlamentului", "consiliului", "autoritatii", "primariei", "prefecturii", "directiei",
    "inspectoratului", "oficiului", "uniunii", "registrului", "administratiei", "casei",
    "serviciului", "comisiei", "camerei", "agentiei", "baroului", "ministry",
    "commission", "council", "parliament", "government", "authority", "agency",
    "department", "senate", "european", "supreme", "high",
}  # fmt: skip
_COMPANY_FORMS = {
    "srl", "sa", "snc", "scs", "sca", "pfa", "ltd", "limited", "llc", "llp",
    "inc", "plc", "gmbh", "ag", "bv", "nv", "sarl", "sas", "spa", "corp",
}  # fmt: skip


def is_public_body(surface: str) -> bool:
    words = [w for w in (_word(t) for t in surface.split()) if w]
    words = [w for w in words if w not in {"the", "al", "a"}]
    if not words or any(w in _COMPANY_FORMS for w in words):
        return False
    return words[0] in PUBLIC_BODY_WORDS


def _word(token: str) -> str:
    return fold(token).strip(".,;:()[]\"'„”“«»‘’")


_TOKEN = re.compile(r"\S+")
_EDGE = " \t\r\n.,;:!?()[]{}<>\"'`„”“«»‘’/\\|-–—"  # a separator between two names is not a part of a name
_LIST_MARKER = re.compile(r"\d+[.)]\s+")
# "S.R.L." ends with a dot that belongs to the name.
_ABBREVIATION = re.compile(r"(?:(?<!\w)[^\W\d_]\.)+[^\W\d_]$")
NAME_TYPES = {"PERSON", "ORGANIZATION", "LOCATION"}
_LEADING_PREPOSITIONS = {"de", "din", "la", "pe", "cu", "pentru", "către", "catre", "prin", "of", "for", "to", "the"}
# Words that are never a name alone. A rest of a cut span can be only such words: the "of" and the "and"
# in "United Kingdom of Great Britain and Northern Ireland", after the KEEP spans cut the three names out.
_FUNCTION_WORDS = _LEADING_PREPOSITIONS | {
    "and", "or", "in", "on", "at", "by", "with", "a", "an", "și", "si", "sau", "ori", "al", "ai", "ale", "lui",
}  # fmt: skip
# A heading in capital letters ("DE TRANSPORT RUTIER ...") is not the name of a company.
_HEADING_START = {"DE", "DIN", "LA", "SI", "ȘI", "CU", "PENTRU", "PRIN", "SAU", "OF", "FOR", "AND", "TO", "ON", "IN"}
# Words of an address that are not private alone ("nr.", "jud.", "et. 2").
_SCAFFOLD = {
    "nr", "str", "strada", "bl", "bloc", "sc", "scara", "et", "etaj", "ap", "apartament", "jud",
    "judetul", "sector", "sectorul", "cod", "postal", "bd", "bulevardul", "calea", "aleea",
    "soseaua", "piata", "com", "comuna", "sat", "mun", "municipiul", "orasul", "oras",
}  # fmt: skip


def _trim_end(text: str, start: int, end: int) -> int:
    """Remove punctuation at the end. Keep the last dot of an abbreviation (S.R.L.)."""
    while end > start and text[end - 1] in _EDGE:
        if text[end - 1] == "." and _ABBREVIATION.search(text[start : end - 1]):
            break
        end -= 1
    return end


def _only_function_words(piece: str) -> bool:
    words = [w for w in (_word(t) for t in piece.split()) if w]
    return bool(words) and all(w in _FUNCTION_WORDS for w in words)


def _is_scaffold(piece: str) -> bool:
    words = [w for w in (_word(t) for t in piece.split()) if w]
    return bool(words) and all(w in _SCAFFOLD or re.fullmatch(r"\d{1,3}[a-z]?", w) for w in words)


def refine(text: str, span: Span, keep: set[str], public_bodies: bool = False) -> Span | None:
    """Clean a span from NER.

    Return None if the span is not a private name (a role word, a common noun).
    Return a span of type "KEEP" if the policy keeps the text visible. Such a span
    also protects its text against the known names of the vault.
    """
    start, end = span.start, span.end
    # 1. Remove punctuation and spaces at the edges.
    while start < end and text[start] in _EDGE:
        start += 1
    end = _trim_end(text, start, end)
    if start >= end:
        return None

    if span.type in NAME_TYPES:
        # The number of a list item ("2. S.C. Alfa S.R.L.") is not a part of the name.
        marker = _LIST_MARKER.match(text, start, end)
        if marker:
            start = marker.end()
        tokens = [(m.start() + start, m.end() + start) for m in _TOKEN.finditer(text[start:end])]
        words = [_word(text[a:b]) for a, b in tokens]
        # 2. Remove titles and role words at the start (for example "dl.", "Reclamanta").
        first = 0
        while first < len(words) and (is_role(words[first]) or (span.type == "PERSON" and words[first] in TITLES)):
            first += 1
        # 3. Remove role words at the end (for example ", administrator").
        last = len(words)
        while last > first and is_role(words[last - 1]):
            last -= 1
        # 4. If only role words are left, there is nothing private.
        if first >= last:
            return None
        start, end = tokens[first][0], tokens[last - 1][1]
        # 5. A name has a capital letter somewhere. The model also marks common words
        #    ("personal calificat"). Lowercase particles in the middle are fine ("van der Weerd").
        if not any(word[:1].isupper() for word in text[start:end].split()):
            return None
        head = text[start:end].split(None, 1)[0]
        if span.type != "PERSON" and head in _HEADING_START:
            return None
        # 5b. A preposition at the start is not a part of the name ("de Alfa SRL").
        if span.type != "PERSON":
            while head in _LEADING_PREPOSITIONS and " " in text[start:end].strip():
                start += len(head) + len(text[start + len(head) :]) - len(text[start + len(head) :].lstrip())
                head = text[start:end].split(None, 1)[0]
        # 6. A person is not followed by a comma and a lowercase word: "Ion Popescu, dispecer".
        if span.type == "PERSON":
            comma = re.search(r",\s+(?=[a-zăâîșț])", text[start:end])
            if comma:
                end = start + comma.start()
        end = _trim_end(text, start, end)

    surface = text[start:end]
    letters = len(re.sub(r"\W", "", surface))
    # One letter is junk ("L." from "S.R.L."), but not for a person: it can be the initial of a name.
    if letters == 0 or (letters < 2 and span.type != "PERSON"):
        return None
    if generic_key(surface) in keep or (public_bodies and span.type == "ORGANIZATION" and is_public_body(surface)):
        return replace(span, start=start, end=end, type="KEEP")
    return replace(span, start=start, end=end)


def keep_set(extra: list[str] | None = None) -> set[str]:
    """The folded texts that stay visible. A one-word name also stays in its Romanian forms:
    `România` keeps `României` ("Constituția României"), `Germania` keeps `Germaniei`."""
    keep = {generic_key(item) for item in [*DEFAULT_KEEP, *(extra or [])]}
    for item in [*DEFAULT_KEEP, *(extra or [])]:
        if item.isalpha() and item[:1].isupper() and not item.isupper() and len(item) >= 5:
            keep |= inflections(generic_key(item))
    return keep


# --- combine spans ----------------------------------------------------------------


def _merge_same_type(spans: list[Span]) -> list[Span]:
    merged: list[Span] = []
    for span in sorted(spans, key=lambda s: (s.type, s.start, s.end)):
        last = merged[-1] if merged else None
        if last and last.type == span.type and span.start < last.end:
            if "vault" in (last.source, span.source):
                source = "vault"
            else:
                source = max(last, span, key=lambda s: s.length).source
            merged[-1] = Span(
                last.start, max(last.end, span.end), last.type, max(last.score, span.score), source
            )
        else:
            merged.append(span)
    return merged


def _subtract(span: Span, others: list[Span]) -> list[tuple[int, int]]:
    """The parts of `span` that no span in `others` covers."""
    pieces = [(span.start, span.end)]
    for other in others:
        next_pieces = []
        for a, b in pieces:
            if other.end <= a or other.start >= b:
                next_pieces.append((a, b))
                continue
            if a < other.start:
                next_pieces.append((a, other.start))
            if other.end < b:
                next_pieces.append((other.end, b))
        pieces = next_pieces
    return pieces


def _pieces(span: Span, others: list[Span], text: str) -> list[Span]:
    result = []
    for a, b in _subtract(span, others):
        while a < b and text[a] in _EDGE:
            a += 1
        b = _trim_end(text, a, b)
        if b - a < 2 or not re.search(r"\w", text[a:b]):
            continue
        if span.type == "ADDRESS" and _is_scaffold(text[a:b]):
            continue  # what is left of an address after we cut a name from it: "jud."
        if span.type in NAME_TYPES and _only_function_words(text[a:b]):
            continue  # what is left of a name between two parts that we cut out: "of", "and", "și"
        result.append(replace(span, start=a, end=b))
    return result


def resolve_overlaps(spans: list[Span], text: str) -> list[Span]:
    """Return spans that do not overlap.

    Rules:
    * A span of type "KEEP" is text that the policy keeps visible. A name span (known or
      from the model) loses the part that it shares with a KEEP span, so the "Mureș" of
      "Tribunalul Mureș" stays visible when "Mureș" is a known place.
    * A known entity (source "vault") must not cut a value with a fixed shape,
      for example the "popescu" inside "ion.popescu@alfa.ro". Such a span is dropped.
    * Otherwise a known entity wins over a model span of another type. The model span
      keeps the part that is not covered, so no part of a name stays visible.
    * Spans of the same type that overlap are joined.
    * For the other conflicts, the span with the better rank and then the longer span wins.
    """
    protected = [s for s in spans if s.type == "KEEP"]
    spans = [s for s in spans if s.type != "KEEP"]
    known = [s for s in spans if s.source == "vault"]
    others = [s for s in spans if s.source != "vault"]
    fixed_shape = [s for s in others if s.rank == 0]
    known = [
        k for k in known
        if not any(f.start <= k.start and k.end <= f.end and f.length > k.length for f in fixed_shape)
    ]
    known = _merge_same_type(known)
    rest = []
    for span in others:
        rest.extend(_pieces(span, [k for k in known if k.type != span.type], text))

    order = sorted(_merge_same_type(known + rest), key=lambda s: (s.rank, -s.length, -s.score, s.start))
    chosen: list[Span] = []
    for span in order:
        chosen.extend(_pieces(span, chosen, text))
    final: list[Span] = []
    for span in chosen:
        final.extend(_pieces(span, protected, text) if span.type in NAME_TYPES else [span])
    return sorted(final, key=lambda s: s.start)
