"""NER recognizers for Presidio.

Presidio already has `HuggingFaceNerRecognizer`. It handles chunking of long
text and the score threshold. We add two things:

* The Romanian model has no label names in its config (it only has LABEL_0
  to LABEL_30). We set the names from the RONEC list in the model card.
* The Romanian model needs comma letters (ș, ț) and not cedilla letters
  (ş, ţ). We change the letters before we call the model. The text keeps its
  length, so all offsets stay valid.
"""

from __future__ import annotations

import re

from presidio_analyzer import RecognizerResult
from presidio_analyzer.predefined_recognizers.ner import HuggingFaceNerRecognizer

from .textnorm import fix_cedilla

RO_MODEL = "dumitrescustefan/bert-base-romanian-ner"
EN_MODEL = "dslim/bert-large-NER"

# Order is from the model card. It is the order of the model output ids.
RONEC_LABELS = [
    "O",
    "B-PERSON", "I-PERSON",
    "B-ORG", "I-ORG",
    "B-GPE", "I-GPE",
    "B-LOC", "I-LOC",
    "B-NAT_REL_POL", "I-NAT_REL_POL",
    "B-EVENT", "I-EVENT",
    "B-LANGUAGE", "I-LANGUAGE",
    "B-WORK_OF_ART", "I-WORK_OF_ART",
    "B-DATETIME", "I-DATETIME",
    "B-PERIOD", "I-PERIOD",
    "B-MONEY", "I-MONEY",
    "B-QUANTITY", "I-QUANTITY",
    "B-NUMERIC", "I-NUMERIC",
    "B-ORDINAL", "I-ORDINAL",
    "B-FACILITY", "I-FACILITY",
]  # fmt: skip

RONEC_TO_PRESIDIO = {
    "PERSON": "PERSON",
    "ORG": "ORGANIZATION",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "FACILITY": "LOCATION",
    "NAT_REL_POL": "NRP",
    "DATETIME": "DATE_TIME",
    "MONEY": "MONEY",
}

CONLL_TO_PRESIDIO = {
    "PER": "PERSON",
    "ORG": "ORGANIZATION",
    "LOC": "LOCATION",
    "MISC": "MISC",
}

# About 800 characters are about 200 to 300 word pieces. This is well below
# the 512 limit of the model, also for text with many numbers.
CHUNK_SIZE = 800
CHUNK_OVERLAP = 80


# Legal documents write party names in capital letters. Cased BERT models are
# weak on such text. We keep short legal forms in capitals, as they help the model.
_KEEP_UPPER = {
    "SRL", "SA", "SC", "SNC", "SCS", "SCA", "PFA", "II", "LLC", "LTD", "LLP",
    "INC", "PLC", "GMBH", "AG", "BV", "NV", "RO", "CNP", "CUI", "CIF", "UE",
    "EU", "UK", "USA",
}  # fmt: skip
_WORD = re.compile(r"[^\W\d_]{2,}")


def titlecase_caps(text: str) -> str:
    """Change ALL-CAPS words to Title Case. The result has the same length."""

    def fix(match: re.Match) -> str:
        word = match.group(0)
        if not word.isupper() or word in _KEEP_UPPER:
            return word
        fixed = word[0] + word[1:].lower()
        return fixed if len(fixed) == len(word) else word

    return _WORD.sub(fix, text)


class _CapsAwareMixin:
    """Run the model on the text and on a Title Case copy. Merge the results.

    Where the two runs overlap, the Title Case result wins. A result of the
    first run is kept only if no Title Case result overlaps it.
    """

    def analyze(self, text, entities, nlp_artifacts=None) -> list[RecognizerResult]:
        text = fix_cedilla(text)
        folded = titlecase_caps(text)
        primary = super().analyze(folded, entities, nlp_artifacts)
        if folded == text:
            return primary
        extra = super().analyze(text, entities, nlp_artifacts)
        merged = list(primary)
        for item in extra:
            if not any(item.start < p.end and p.start < item.end for p in primary):
                merged.append(item)
        return merged


class RomanianNerRecognizer(_CapsAwareMixin, HuggingFaceNerRecognizer):
    """`bert-base-romanian-ner` with correct label names."""

    def __init__(self, model_name: str = RO_MODEL, threshold: float = 0.2, **kwargs):
        super().__init__(
            supported_entities=sorted(set(RONEC_TO_PRESIDIO.values())),
            name="RomanianBertNer",
            supported_language="ro",
            model_name=model_name,
            label_mapping=RONEC_TO_PRESIDIO,
            threshold=threshold,
            aggregation_strategy="first",
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            device="cpu",
            **kwargs,
        )

    def load(self) -> None:
        if self.ner_pipeline is not None:
            return
        from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

        id2label = dict(enumerate(RONEC_LABELS))
        model = AutoModelForTokenClassification.from_pretrained(
            self.model_name,
            id2label=id2label,
            label2id={label: i for i, label in id2label.items()},
        )
        tokenizer = AutoTokenizer.from_pretrained(self.tokenizer_name)
        self.ner_pipeline = pipeline(
            self.DEFAULT_HF_TASK,
            model=model,
            tokenizer=tokenizer,
            aggregation_strategy=self.aggregation_strategy,
            device=self.device,
        )


class EnglishNerRecognizer(_CapsAwareMixin, HuggingFaceNerRecognizer):
    """`dslim/bert-large-NER` (labels PER, ORG, LOC, MISC)."""

    def __init__(self, model_name: str = EN_MODEL, threshold: float = 0.2, **kwargs):
        super().__init__(
            supported_entities=["PERSON", "ORGANIZATION", "LOCATION"],
            name="EnglishBertNer",
            supported_language="en",
            model_name=model_name,
            label_mapping=CONLL_TO_PRESIDIO,
            threshold=threshold,
            aggregation_strategy="first",
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            device="cpu",
            **kwargs,
        )
