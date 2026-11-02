"""Find sensitive spans in a text, with Presidio."""

from __future__ import annotations

import re

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import (
    CreditCardRecognizer,
    IbanRecognizer,
    IpRecognizer,
    PhoneRecognizer,
    UrlRecognizer,
)

from .config import Settings
from .gliner_ner import GLINER_NAME, gliner_recognizer
from .lang import SUPPORTED, detect_language
from .llm_check import OllamaChecker
from .ner import EnglishNerRecognizer, RomanianNerRecognizer
from .patterns import build_pattern_recognizers, calendar_dates
from .spans import NAME_TYPES, Span, keep_set, refine

NER_NAMES = {"RomanianBertNer", "EnglishBertNer", GLINER_NAME}
PHONE_REGIONS = ("RO", "GB", "US", "DE", "FR", "IT", "ES", "HU", "MD", "BG", "NL", "AT", "PL")


class Detector:
    def __init__(self, settings: Settings | None = None):
        # Settings are the default. `detect` can use other settings for one call,
        # and then the (slow) models are shared.
        self.settings = settings or Settings()
        self._analyzer: AnalyzerEngine | None = None
        self._ner_ready: set[str] = set()
        self._gliner_model: dict[str, str] = {}  # language -> model name of the GLiNER recognizer
        self._checkers: dict[tuple[str, str], OllamaChecker] = {}

    # Presidio needs an NLP engine. The NER models do their own tokenizing, so we
    # use the "no_op" engine and we do not need spaCy models.
    def _build(self) -> AnalyzerEngine:
        nlp_engine = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "no_op",
                "models": [{"lang_code": lang, "model_name": "no_op"} for lang in SUPPORTED],
            }
        ).create_engine()
        registry = RecognizerRegistry(supported_languages=list(SUPPORTED))
        for lang in SUPPORTED:
            for recognizer in (
                UrlRecognizer(supported_language=lang),
                IbanRecognizer(supported_language=lang),
                CreditCardRecognizer(supported_language=lang),
                IpRecognizer(supported_language=lang),
                PhoneRecognizer(supported_language=lang, supported_regions=PHONE_REGIONS),
                *build_pattern_recognizers(lang),
            ):
                registry.add_recognizer(recognizer)
        return AnalyzerEngine(
            nlp_engine=nlp_engine, registry=registry, supported_languages=list(SUPPORTED)
        )

    @property
    def analyzer(self) -> AnalyzerEngine:
        if self._analyzer is None:
            self._analyzer = self._build()
        return self._analyzer

    def warm_up(self, languages: tuple[str, ...] = SUPPORTED) -> None:
        """Load the models now. The first call downloads them. Check the LLM too, if the level needs it."""
        for language in languages:
            self._ensure_ner(language)
            self._ensure_gliner(language, self.settings)
        if self.settings.use_llm:
            self.checker(self.settings)

    def _ensure_ner(self, language: str) -> None:
        if language in self._ner_ready:
            return
        if language == "ro":
            recognizer = RomanianNerRecognizer(self.settings.ro_model)
        else:
            recognizer = EnglishNerRecognizer(self.settings.en_model)
        self.analyzer.registry.add_recognizer(recognizer)
        self._ner_ready.add(language)

    def _ensure_gliner(self, language: str, settings: Settings) -> None:
        if not settings.use_gliner or self._gliner_model.get(language) == settings.gliner_model:
            return
        if language in self._gliner_model:  # another model was asked for
            self.analyzer.registry.remove_recognizer(GLINER_NAME, language)
        self.analyzer.registry.add_recognizer(gliner_recognizer(language, settings.gliner_model))
        self._gliner_model[language] = settings.gliner_model

    def checker(self, settings: Settings) -> OllamaChecker:
        key = (settings.llm_model, settings.llm_host)
        if key not in self._checkers:
            checker = OllamaChecker(settings.llm_model, settings.llm_host)
            checker.check_ready()  # fail now, with a clear message, and not after the first documents
            self._checkers[key] = checker
        return self._checkers[key]

    def language_of(self, text: str, language: str | None = None) -> str:
        language = language or detect_language(text)
        if language not in SUPPORTED:
            raise ValueError(f"Language '{language}' is not supported. Use one of {SUPPORTED}.")
        return language

    def detect(
        self, text: str, language: str, settings: Settings | None = None, context: str | None = None
    ) -> list[Span]:
        """Return cleaned spans for the types that must be hidden.

        `context` is the text of all documents of a batch. A word that the batch also writes in
        lowercase is a common word and not a name (see `is_common_word`).
        """
        settings = settings or self.settings
        keep = keep_set(settings.keep)
        self._ensure_ner(language)
        self._ensure_gliner(language, settings)
        results = self.analyzer.analyze(
            text=text,
            language=language,
            entities=sorted(settings.hide),
        )
        spans = []
        for result in results:
            if result.entity_type not in settings.hide:
                continue
            # The score of a pattern is not on the same scale as the score of a model.
            # So the minimum score is only for the NER models.
            recognizer = result.recognition_metadata.get(RecognizerResult.RECOGNIZER_NAME_KEY)
            if recognizer == GLINER_NAME and not settings.use_gliner:
                continue  # an earlier call, with other settings, added the recognizer
            from_ner = recognizer in NER_NAMES
            floor = settings.gliner_threshold if recognizer == GLINER_NAME else settings.min_score
            if from_ner and result.score < floor:
                continue
            if result.entity_type == "PHONE_NUMBER" and not looks_like_phone(text[result.start : result.end]):
                continue
            raw = Span(result.start, result.end, result.entity_type, result.score, "presidio")
            raws = [raw]
            if from_ner and result.entity_type == "DATE_TIME":
                # The Romanian model also marks durations ("30 de zile") and years. Only a calendar date is hidden.
                raws = [
                    Span(result.start + a, result.start + b, "DATE_TIME", result.score, "presidio")
                    for a, b in calendar_dates(text[result.start : result.end])
                ]
            for raw in raws:
                # The model can mark a span over a line break or a tab. We cut first and clean each piece.
                for piece in split_at_breaks(text, raw):
                    span = refine(text, piece, keep, settings.keep_public_bodies)
                    if span is None:
                        continue
                    if from_ner and span.type in NAME_TYPES and is_common_word(text, span, context):
                        continue
                    spans.append(span)
        if settings.use_llm:
            spans += self._llm_spans(text, spans, settings, keep, context)
        return merge_initials(text, spans)

    def _llm_spans(self, text: str, spans: list[Span], settings: Settings, keep: set[str], context: str | None) -> list[Span]:
        """The LLM reads the hidden text. The spans that it adds get the same clean-up as the model spans."""
        found = []
        for raw in self.checker(settings).missed(text, spans):
            span = refine(text, raw, keep, settings.keep_public_bodies)
            if span is not None and not (span.type in NAME_TYPES and is_common_word(text, span, context)):
                found.append(span)
        return found


_DATE_LIKE = re.compile(r"\d{1,2}\s?[./-]\s?\d{1,2}\s?[./-]\s?\d{2,4}|\d{4}\s?[./-]\s?\d{1,2}\s?[./-]\s?\d{1,2}")
_DATE_INSIDE = re.compile(
    r"(?<!\d)\d{1,2}\s?[./-]\s?\d{1,2}\s?[./-]\s?(?:19|20)\d{2}(?!\d)|(?<!\d)(?:19|20)\d{2}\s?[./-]\s?\d{1,2}\s?[./-]\s?\d{1,2}(?!\d)"
)


def looks_like_phone(value: str) -> bool:
    """The phone parser also accepts dates (01.06.2024), ranges of dates, and short numbers."""
    return (
        len(re.sub(r"\D", "", value)) >= 9
        and not _DATE_LIKE.fullmatch(value.strip())
        and not _DATE_INSIDE.search(value)
    )


def is_common_word(text: str, span: Span, context: str | None = None) -> bool:
    """A model span of one word is a common noun, if the text also writes it in lowercase.

    The model marks "Șoferul" at the start of a sentence as a person. A real name is not
    written in lowercase somewhere else in the text ("șoferul").
    """
    word = text[span.start : span.end]
    if " " in word or "-" in word or word == word.lower():
        return False
    lower = word.lower()
    return re.search(rf"(?<![\w-]){re.escape(lower)}(?![\w-])", context or text) is not None


_INITIAL_GAP = re.compile(r"\.?\s+")


def merge_initials(text: str, spans: list[Span]) -> list[Span]:
    """Join "James R" and "Whitcombe" into one person, if the name has an initial ("James R. Whitcombe")."""
    result: list[Span] = []
    for span in sorted(spans, key=lambda s: s.start):
        before = result[-1] if result else None
        if (
            before
            and before.type == span.type == "PERSON"
            and re.search(r"(?<!\w)[^\W\d_]$", text[before.start : before.end])
            and _INITIAL_GAP.fullmatch(text[before.end : span.start])
        ):
            result[-1] = Span(before.start, span.end, "PERSON", min(before.score, span.score), before.source)
        else:
            result.append(span)
    return result


_BREAK = re.compile(r"[\n\t\r]+")


def split_at_breaks(text: str, span: Span) -> list[Span]:
    """A span must not contain a line break or a tab. Cut it into pieces."""
    pieces, start = [], span.start
    for match in _BREAK.finditer(text, span.start, span.end):
        pieces.append((start, match.start()))
        start = match.end()
    pieces.append((start, span.end))
    return [
        Span(a, b, span.type, span.score, span.source)
        for a, b in pieces
        if b - a >= 2 and re.search(r"\w", text[a:b])
    ]
