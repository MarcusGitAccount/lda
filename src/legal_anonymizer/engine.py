"""Anonymize and restore documents. This module joins all other modules."""

from __future__ import annotations

import hashlib
import re
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass, field
from itertools import permutations

from .config import Settings
from .detector import Detector
from .documents import Document, Replacement, open_document, scan_text
from .entities import TYPE_BY_TAG
from .spans import Span, resolve_overlaps
from .textnorm import collapse, fold
from .vault import PLACEHOLDER_RE, Vault

MIN_SWEEP_LENGTH = 3
MAX_NAME_ORDERS = 4  # a name of up to 4 words has up to 24 orders


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
                for span in resolve_overlaps(item.spans + self._sweep(item.text), item.text):
                    self.vault.resolve(span.type, collapse(item.text[span.start : span.end]), count=0)
        return [self._render(item) for item in prepared]

    def _open(self, name: str, data: bytes, language: str | None) -> _Prepared:
        document = open_document(name, data)
        units = document.units()
        text = "\n".join(units)
        return _Prepared(name, data, document, units, text, self.detector.language_of(text, language), [])

    def _render(self, item: _Prepared) -> AnonymizeResult:
        text, units = item.text, item.units
        spans = resolve_overlaps(item.spans + self._sweep(text), text)

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

        return AnonymizeResult(output, item.language, counts, self.find_leaks(item.name, output), spans)

    def _known_forms(self) -> tuple[re.Pattern | None, dict[str, tuple[str, int]]]:
        """Return one regex for all known written forms, and the owner of each form."""
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
        if not owners:
            return None, {}
        ordered = sorted(owners, key=len, reverse=True)  # the longest form first
        body = "|".join(re.escape(f).replace(r"\ ", " +") for f in ordered)
        return re.compile(rf"(?<!\w)(?:{body})(?!\w)"), owners

    def _sweep(self, text: str) -> list[Span]:
        """Find known entities again. The models can miss a name that they found before."""
        pattern, owners = self._known_forms()
        if pattern is None:
            return []
        spans = []
        for match in pattern.finditer(fold(text)):  # `fold` keeps the length of the text
            owner = owners.get(collapse(match.group(0)))
            if owner:
                spans.append(Span(match.start(), match.end(), owner[0], 1.0, "vault"))
        return spans

    # --- check ----------------------------------------------------------------------

    def find_leaks(self, name: str, data: bytes) -> list[str]:
        """Look in a file for text of a known entity. Return the placeholders of what is found."""
        pattern, owners = self._known_forms()
        if pattern is None:
            return []
        text = fold(scan_text(name, data))
        kept = self.vault.kept_phrases()
        if kept:  # text that the policy keeps visible is not a leak
            body = "|".join(re.escape(p).replace(r"\ ", r"\s+") for p in sorted(kept, key=len, reverse=True))
            text = re.sub(rf"(?<!\w)(?:{body})(?!\w)", " ", text)
        leaks = set()
        for match in pattern.finditer(text):
            owner = owners.get(collapse(match.group(0)))
            if owner:
                leaks.add(self.vault.entity(owner[1]).placeholder)
        return sorted(leaks)

    # --- restore ---------------------------------------------------------------------

    def restore(self, name: str, data: bytes) -> RestoreResult:
        document = open_document(name, data)
        units = document.units()
        restored: Counter = Counter()
        unknown: list[str] = []
        replacements: list[list[Replacement]] = []
        for unit in units:
            found = []
            for match in PLACEHOLDER_RE.finditer(unit):
                entity = self.vault.lookup(TYPE_BY_TAG[match.group(1)], int(match.group(2)))
                if entity is None:
                    unknown.append(match.group(0))
                    continue
                found.append((match.start(), match.end(), entity.canonical))
                restored[entity.placeholder] += 1
            replacements.append(found)
        return RestoreResult(document.rewrite(replacements), restored, sorted(set(unknown)))
