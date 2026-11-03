"""Anonymize and restore documents. This module joins all other modules."""

from __future__ import annotations

import hashlib
import os
import re
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass, field
from itertools import permutations

from .config import Settings
from .detector import Detector
from .documents import (
    Document,
    Replacement,
    apply_replacements,
    open_document,
    scan_text,
)
from .romanian import INFLECTED_TYPES, inflections, related, same_lexeme
from .spans import NAME_TYPES, Span, resolve_overlaps
from .textnorm import LEGAL_FORMS, collapse, entity_key, fold
from .vault import PLACEHOLDER_RE, Vault, parse_placeholder

MIN_SWEEP_LENGTH = 3
MAX_NAME_ORDERS = 4  # a name of up to 4 words has up to 24 orders


class KnownForms:
    """One regex for the written forms in the vault, and the owner of each match.

    A person or a place also matches in the Romanian forms of its words (`Popescului` for `Popescu`,
    see `romanian.py`). The regex lists the forms of each word. `owner` finds the entity of a match.
    """

    def __init__(self, owners: dict[str, tuple[str, int]]):
        self.owners = owners
        self._found: dict[str, tuple[str, int] | None] = {}
        self._by_size: dict[int, list[tuple[list[str], tuple[str, int]]]] = {}
        for variant, owner in owners.items():
            if owner[0] in INFLECTED_TYPES:
                words = variant.split()
                self._by_size.setdefault(len(words), []).append((words, owner))
        self._by_key: dict[tuple[str, str], tuple[str, int]] = {}
        for variant, owner in owners.items():
            self._by_key.setdefault((owner[0], entity_key(owner[0], variant)), owner)
        self._types = sorted({owner[0] for owner in owners.values()})
        ordered = sorted(owners, key=len, reverse=True)  # the longest form first
        body = "|".join(self._pattern(variant, owners[variant][0]) for variant in ordered)
        self.regex = re.compile(rf"(?<!\w)(?:{body})(?!\w)") if owners else None

    @staticmethod
    def _pattern(variant: str, entity_type: str) -> str:
        """The regex for one written form. It allows the spellings that the vault counts as the same name."""
        if entity_type == "PERSON":  # "Ana-Maria" and "Ana Maria"; the Romanian forms of each word
            parts = [part for part in re.split(r"[\s-]+", variant) if part]
            return r"[ \-]+".join(KnownForms._word(part) for part in parts)
        if entity_type == "LOCATION":
            return " +".join(KnownForms._word(word) for word in variant.split())
        if entity_type == "ORGANIZATION":
            words = variant.split()
            prefix = ""
            if len(words) > 1 and words[0].replace(".", "") == "sc":
                prefix, words = r"(?:s\.?c\.? +)?", words[1:]  # "SC" is optional, as in the key of the vault
            parts = []
            for word in words:
                letters = word.replace(".", "")
                if letters.isalpha() and letters in LEGAL_FORMS:
                    parts.append(r"\.?".join(map(re.escape, letters)) + r"\.?")  # SRL, S.R.L., S.R.L
                else:
                    parts.append(re.escape(word))
            return prefix + " +".join(parts)
        return re.escape(variant).replace(r"\ ", " +")

    @staticmethod
    def _word(word: str) -> str:
        forms = sorted({word} | inflections(word), key=len, reverse=True)
        return "(?:" + "|".join(map(re.escape, forms)) + ")"

    def finditer(self, text: str):
        return self.regex.finditer(text) if self.regex else iter(())

    def matches(
        self, text: str, reference: str | None = None, folded: str | None = None, source: str | None = None
    ):
        """The (start, end, owner) of each known form in `text`.

        A name has a capital letter. A lowercase word that is a form of a known one-word name
        ("brown" for "Brown") is a common word if the text also writes the name with a capital
        letter: "Mr Brown ... the brown car". If no capital letter writes it, the word is hidden:
        the text can be all lower case. `reference` is the text before the change, when `text` is
        the hidden file that has lost the capital letters. `folded` is `fold(text)` if the caller
        has changed it (it must keep the length). `source` is the document before the change. A document
        with no capital letter at all (a quick message) has no such common words: all its forms are hidden.
        """
        folded = fold(text) if folded is None else folded
        lowercase_document = not any(ch.isupper() for ch in (text if source is None else source))
        capitals = None
        for match in self.finditer(folded):
            owner = self.owner(match.group(0))
            if owner is None:
                continue
            written = text[match.start() : match.end()]
            if (
                owner[0] in NAME_TYPES
                and not lowercase_document
                and written == written.lower()
                and not re.search(r"[\s-]", written)
            ):
                if capitals is None:
                    capitals = _capitalized_words(text if reference is None else reference)
                if related(match.group(0)) & capitals:
                    continue
            yield match.start(), match.end(), owner

    def owner(self, matched: str) -> tuple[str, int] | None:
        matched = collapse(matched)
        if matched in self.owners:
            return self.owners[matched]
        if matched not in self._found:
            self._found[matched] = self._same_key(matched) or self._same_lexeme(matched)
        return self._found[matched]

    def _same_key(self, matched: str) -> tuple[str, int] | None:
        """The vault counts `S.R.L.` and `SRL`, or `Ana Maria` and `Ana-Maria`, as one written form."""
        for entity_type in self._types:
            owner = self._by_key.get((entity_type, entity_key(entity_type, matched)))
            if owner:
                return owner
        return None

    def _same_lexeme(self, matched: str) -> tuple[str, int] | None:
        words = matched.split()
        return next(
            (
                owner
                for known, owner in self._by_size.get(len(words), [])
                if same_lexeme(words, known, ordered=owner[0] != "PERSON")
            ),
            None,
        )


def _capitalized_words(text: str) -> set[str]:
    return {fold(word) for word in re.findall(r"\w+", text) if word[:1].isupper()}


@dataclass
class AnonymizeResult:
    data: bytes
    language: str
    # placeholder -> number of times in this document
    counts: Counter = field(default_factory=Counter)
    # Words that the document still has after the change. Should be empty.
    leaks: list[str] = field(default_factory=list)
    # The spans that were hidden, as offsets in the text of the units joined with "\n". For the evaluation.
    spans: list[Span] = field(default_factory=list)


@dataclass
class RestoreResult:
    data: bytes
    restored: Counter = field(default_factory=Counter)
    unknown: list[str] = field(default_factory=list)
    # Text that looks like an id and is still in the file: a changed tag, or letters glued to an id.
    suspect: list[str] = field(default_factory=list)


@dataclass
class _Prepared:
    name: str
    data: bytes
    document: Document
    units: list[str]
    text: str
    language: str
    spans: list[Span]  # from the models, before the sweep


class Engine:
    def __init__(self, vault: Vault, settings: Settings | None = None, detector: Detector | None = None):
        self.vault = vault
        self.settings = settings or Settings()
        self.detector = detector or Detector(self.settings)

    # --- seeds -----------------------------------------------------------------

    def load_seeds(self) -> None:
        """Put the entities from the config file into the vault, with their aliases."""
        with self.vault.transaction():
            for seed in self.settings.seeds:
                entity = self.vault.resolve(seed.type, seed.name, seed=True, count=0)
                for alias in seed.aliases:
                    self.vault.add_alias(entity.id, alias)

    # --- anonymize ----------------------------------------------------------------

    def anonymize(self, name: str, data: bytes, *, language: str | None = None) -> AnonymizeResult:
        return self.anonymize_many([(name, data)], language=language)[0]

    def anonymize_many(
        self, files: list[tuple[str, bytes]], *, language: str | None = None
    ) -> list[AnonymizeResult]:
        """Anonymize documents that belong together.

        Pass 1 finds the entities in all documents and puts them in the vault.
        Pass 2 writes each document. It looks again for every entity that the
        vault knows. So a name that the model found in one document is also hidden
        in a document where the model missed it.
        """
        prepared = [self._open(name, data, language) for name, data in files]
        context = "\n".join(item.text for item in prepared)
        for item in prepared:
            if item.text.strip():
                item.spans = self.detector.detect(item.text, item.language, self.settings, context=context)
        with self.vault.transaction():
            for item in prepared:
                self.vault.add_kept(item.text[s.start : s.end] for s in item.spans if s.type == "KEEP")
                for span in self._visible(
                    resolve_overlaps(item.spans + self._sweep(item.text, context), item.text), item.text
                ):
                    self.vault.resolve(span.type, collapse(item.text[span.start : span.end]), count=0)
        return [self._render(item, context) for item in prepared]

    def _open(self, name: str, data: bytes, language: str | None) -> _Prepared:
        document = open_document(name, data)
        units = document.units()
        text = "\n".join(units)
        return _Prepared(name, data, document, units, text, self.detector.language_of(text, language), [])

    def _render(self, item: _Prepared, context: str) -> AnonymizeResult:
        text, units = item.text, item.units
        spans = self._visible(resolve_overlaps(item.spans + self._sweep(text, context), text), text)

        # Give one id to each written form, in the order of first appearance.
        written = Counter((span.type, collapse(text[span.start : span.end])) for span in spans)
        starts = [0]
        for unit in units:
            starts.append(starts[-1] + len(unit) + 1)  # +1 for the "\n" between units
        replacements: list[list[Replacement]] = [[] for _ in units]
        counts: Counter = Counter()
        mentions: Counter = Counter()  # entity id -> count

        with self.vault.transaction():
            entities = {
                key: self.vault.resolve(key[0], key[1], count=n) for key, n in written.items()
            }
            for span in spans:
                entity = entities[(span.type, collapse(text[span.start : span.end]))]
                counts[entity.placeholder] += 1
                mentions[entity.id] += 1
                index = bisect_right(starts, span.start) - 1
                base = starts[index]
                replacements[index].append((span.start - base, span.end - base, entity.placeholder))
            output = item.document.rewrite(replacements, scrub=True)
            self.vault.record_document(item.name, hashlib.sha256(item.data).hexdigest(), item.language, dict(mentions))

        return AnonymizeResult(output, item.language, counts, self.find_leaks(item.name, output, reference=context, source=text), spans)

    def _visible(self, spans: list[Span], text: str) -> list[Span]:
        """Remove the spans of entities that the user told us to forget (`lda forget`)."""
        if not self.vault.any_ignored():
            return spans
        return [s for s in spans if not self.vault.is_ignored(s.type, collapse(text[s.start : s.end]))]

    def _known_forms(self) -> KnownForms:
        """All known written forms in one regex, with the owner of each form."""
        owners: dict[str, tuple[str, int]] = {}
        for folded, entity_type, entity_id in sorted(
            self.vault.known_forms(self.settings.hide), key=lambda f: f[2]
        ):
            variants = {folded}
            words = folded.split()
            if entity_type == "PERSON" and 2 <= len(words) <= MAX_NAME_ORDERS:
                # "Ion Popescu" is also written "POPESCU ION". The entity key
                # ignores the order, so the sweep must look for every order.
                variants.update(" ".join(order) for order in permutations(words))
            for variant in variants:
                if len(re.sub(r"\W", "", variant)) >= MIN_SWEEP_LENGTH:
                    owners.setdefault(variant, (entity_type, entity_id))
        return KnownForms(owners)

    def _sweep(self, text: str, reference: str | None = None) -> list[Span]:
        """Find known entities again. The models can miss a name that they found before.
        `reference` is the text of all documents of the batch: it shows which words are written with a capital letter."""
        known = self._known_forms()
        return [Span(start, end, owner[0], 1.0, "vault") for start, end, owner in known.matches(text, reference)]

    # --- check ----------------------------------------------------------------------

    def find_leaks(
        self, name: str, data: bytes, reference: str | None = None, source: str | None = None
    ) -> list[str]:
        """Look in a file for text of a known entity. Return the placeholders of what is found.

        `reference` is the text of the batch before the change, and `source` the text of this document.
        The hidden file has no capital letters of the names, and the check needs them (see `KnownForms.matches`).
        """
        known = self._known_forms()
        text = scan_text(name, data)
        folded = fold(text)
        kept = self.vault.kept_phrases()
        if kept:  # text that the policy keeps visible is not a leak
            body = "|".join(re.escape(p).replace(r"\ ", r"\s+") for p in sorted(kept, key=len, reverse=True))
            folded = re.sub(rf"(?<!\w)(?:{body})(?!\w)", lambda m: " " * len(m.group(0)), folded)
        leaks = {self.vault.entity(owner[1]).placeholder for _, _, owner in known.matches(text, reference, folded, source)}
        return sorted(leaks)

    # --- restore ---------------------------------------------------------------------

    def restore(self, name: str, data: bytes) -> RestoreResult:
        document = open_document(name, data)
        units = document.units()
        restored: Counter = Counter()
        unknown: list[str] = []
        suspect: set[str] = set()
        replacements: list[list[Replacement]] = []
        for unit in units:
            found = []
            for match in PLACEHOLDER_RE.finditer(unit):
                entity_type, number = parse_placeholder(match)
                entity = self.vault.lookup(entity_type, number) if entity_type else None
                if entity is None:
                    unknown.append(match.group(0))
                    continue
                end, text = match.end(), entity.canonical
                glue = _GLUED.match(unit, end)
                if glue:  # "[PERSON_001]ului": the AI tool wrote a Romanian ending after the id
                    form = glued_form(text, glue.group(1)) if entity.type in INFLECTED_TYPES else None
                    if form is None:
                        suspect.add(unit[match.start() : glue.end()])
                    else:
                        end, text = glue.end(), form
                found.append((match.start(), end, text))
                restored[entity.placeholder] += 1
            replacements.append(found)
            for look in _SUSPECT.finditer(apply_replacements(unit, found)):
                if look.group(0) not in unknown:
                    suspect.add(look.group(0))
        return RestoreResult(document.rewrite(replacements), restored, sorted(set(unknown)), sorted(suspect))


# Letters that follow an id without a space ("[PERSON_001]ului", "[PERSON_001]-ului").
_GLUED = re.compile(r"-?([a-zăâîșț]+)")
# Text that looks like an id but is not one that we restore: "[PERSONNE_001]", "ORG_7", "[ORGANIZATIE 3]".
_SUSPECT = re.compile(
    r"(?<!\w)[^\W\d_]{3,}[_＿]\d{1,6}(?!\d)"
    r"|\[\s*[A-ZĂÂÎȘȚ]{4,}[\s_-]\s*\d{1,6}\s*\]"
    r"|[［\[]\s*[^\W\d_]{3,}[_＿]\s*\d{1,6}\s*[］\]]"
)


def glued_form(canonical: str, ending: str) -> str | None:
    """The canonical name with its last word in the form that has this ending, or None.

    `Popescu` and `ului` give `Popescului`. `Maria` and `ei` give `Mariei`.
    """
    words = canonical.split()
    if not words:
        return None
    last = words[-1]
    base, ending = fold(last), fold(ending)
    forms = sorted((f for f in inflections(base) if f.endswith(ending)), key=len)
    if not forms:
        return None
    keep = len(os.path.commonprefix([base, forms[0]]))
    return " ".join([*words[:-1], last[:keep] + forms[0][keep:]])
