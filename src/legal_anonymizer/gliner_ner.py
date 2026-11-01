"""GLiNER recognizer for Presidio.

Presidio has `GLiNERRecognizer`. We do not use it, for two reasons:

* It turns every entity type that the caller asks for into a zero-shot label. We call the
  analyzer with a long list of types (e-mail, IBAN, ...), and most of them are not a job for GLiNER.
* It has its own chunking. We use the same chunk size and the same ALL-CAPS handling as the
  BERT recognizers, so the models see the same text.

GLiNER is a zero-shot model: it finds the spans that match a label that we write in plain words.
It adds hits to the BERT models. It does not replace them.

Two model families work here. `GLiNER` models (urchade/gliner_multi_pii-v1) use the `gliner` package.
`GLiNER2` models (fastino/gliner2-privacy-filter-PII-multi) use the `gliner2` package. The name of the
model decides. The GLiNER2 PII model does not cover Romanian, and it has no label for organizations.
"""

from __future__ import annotations

import re
import threading

from presidio_analyzer import EntityRecognizer, RecognizerResult

from .ner import CHUNK_OVERLAP, CHUNK_SIZE, _CapsAwareMixin

GLINER_MODEL = "urchade/gliner_multi_pii-v1"  # Apache-2.0, multilingual
GLINER_NAME = "GlinerPii"

# The label is the prompt for the model, so the words matter. Label -> Presidio entity type.
GLINER_LABELS = {
    "person": "PERSON",
    "organization": "ORGANIZATION",
    "address": "ADDRESS",
    "location": "LOCATION",
}

# The labels of the GLiNER2 PII model are fixed (42 types). We use the ones that name a person or a place.
GLINER2_LABELS = {
    "person": "PERSON",
    "full_name": "PERSON",
    "address": "ADDRESS",
    "street_address": "ADDRESS",
    "city": "LOCATION",
}

_MODELS: dict[str, object] = {}
_LOCK = threading.Lock()


def is_gliner2(name: str) -> bool:
    return "gliner2" in name.lower()


def load_model(name: str):
    """One model object for each name. Both language recognizers use it."""
    with _LOCK:
        if name not in _MODELS:
            try:
                if is_gliner2(name):
                    from gliner2 import GLiNER2

                    _MODELS[name] = GLiNER2.from_pretrained(name)
                else:
                    from gliner import GLiNER

                    _MODELS[name] = GLiNER.from_pretrained(name, map_location="cpu")
            except ImportError as error:  # the packages are an optional extra
                raise RuntimeError("GLiNER is not installed. Run: pip install 'legal-anonymizer[gliner]'") from error
        return _MODELS[name]


def chunks(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    """Yield (offset, piece). A piece ends at a space when it can, so a word is not cut."""
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            space = text.rfind(" ", start + size // 2, end)
            end = space if space > 0 else end
        yield start, text[start:end]
        if end >= len(text):
            return
        start = max(end - overlap, start + 1)
        while start < end and re.match(r"\w", text[start - 1 : start]) and re.match(r"\w", text[start : start + 1]):
            start += 1  # do not start in the middle of a word


class _GlinerBase(EntityRecognizer):
    def __init__(
        self,
        language: str,
        model_name: str = GLINER_MODEL,
        threshold: float = 0.2,
        labels: dict[str, str] | None = None,
    ):
        # Presidio calls `load` inside `__init__`, so the fields must exist first.
        self.model_name = model_name
        self.threshold = threshold
        self.labels = dict(labels or GLINER_LABELS)
        self.model = None
        super().__init__(
            supported_entities=sorted(set(self.labels.values())),
            name=GLINER_NAME,
            supported_language=language,
        )

    def load(self) -> None:
        if self.model is None:
            self.model = load_model(self.model_name)

    def _predict(self, piece: str, labels: list[str]):
        """Yield (label, start, end, score) for one piece of text."""
        for hit in self.model.predict_entities(piece, labels, threshold=self.threshold, flat_ner=True):
            yield hit["label"], hit["start"], hit["end"], float(hit["score"])

    def analyze(self, text, entities, nlp_artifacts=None) -> list[RecognizerResult]:
        self.load()
        wanted = set(entities)
        names = [label for label, entity in self.labels.items() if entity in wanted]
        if not names:
            return []
        results = []
        for offset, piece in chunks(text):
            for label, start, end, score in self._predict(piece, names):
                results.append(
                    RecognizerResult(
                        entity_type=self.labels[label],
                        start=offset + start,
                        end=offset + end,
                        score=score,
                        recognition_metadata={
                            RecognizerResult.RECOGNIZER_NAME_KEY: self.name,
                            RecognizerResult.RECOGNIZER_IDENTIFIER_KEY: self.id,
                        },
                    )
                )
        return results


class _Gliner2Base(_GlinerBase):
    def __init__(self, language: str, model_name: str, threshold: float = 0.2, labels: dict[str, str] | None = None):
        super().__init__(language, model_name, threshold, labels or GLINER2_LABELS)

    def _predict(self, piece: str, labels: list[str]):
        found = self.model.extract_entities(
            piece, labels, threshold=self.threshold, include_confidence=True, include_spans=True
        )
        for label, hits in found.get("entities", {}).items():
            for hit in hits:
                yield label, hit["start"], hit["end"], float(hit["confidence"])


class GlinerRecognizer(_CapsAwareMixin, _GlinerBase):
    """GLiNER on the text and on a Title Case copy of it (see `_CapsAwareMixin`)."""


class Gliner2Recognizer(_CapsAwareMixin, _Gliner2Base):
    """The same, with the GLiNER2 package."""


def gliner_recognizer(language: str, model_name: str = GLINER_MODEL):
    """The recognizer class that fits the model."""
    if is_gliner2(model_name):
        return Gliner2Recognizer(language, model_name)
    return GlinerRecognizer(language, model_name)
