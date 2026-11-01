"""Pattern recognizers for data that has a fixed shape.

Presidio has no Romanian recognizers, so we add them here: CNP, CUI/CIF,
trade register number, ID card, court case number and street address.
The same recognizers run for Romanian and English documents, because an
English contract can name a Romanian company.
"""

from __future__ import annotations

import re
from typing import Callable, Optional

from presidio_analyzer import LocalRecognizer, RecognizerResult

LETTER = r"[A-Za-zĂÂÎȘȚăâîșțŞŢşţ]"
CAP = r"[A-ZĂÂÎȘȚŞŢ]"


# --- checksums ------------------------------------------------------------

_CNP_KEY = "279146358279"


def valid_cnp(value: str) -> bool:
    """Check the Romanian personal numeric code (13 digits)."""
    digits = re.sub(r"\D", "", value)
    if len(digits) != 13 or digits[0] == "0":
        return False
    month, day = int(digits[3:5]), int(digits[5:7])
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return False
    total = sum(int(d) * int(k) for d, k in zip(digits[:12], _CNP_KEY))
    control = total % 11
    return int(digits[12]) == (1 if control == 10 else control)


_CUI_KEY = [7, 5, 3, 2, 1, 7, 5, 3, 2]


def valid_cui(value: str) -> bool:
    """Check the Romanian company tax code (2 to 10 digits, with or without RO)."""
    digits = re.sub(r"\D", "", re.sub(r"(?i)^\s*RO", "", value))
    if not (2 <= len(digits) <= 10) or digits[0] == "0":
        return False
    body, control = digits[:-1], int(digits[-1])
    total = sum(int(d) * k for d, k in zip(reversed(body), reversed(_CUI_KEY)))
    result = (total * 10) % 11
    return control == (0 if result == 10 else result)


# --- generic regex recognizer ----------------------------------------------


class RegexRecognizer(LocalRecognizer):
    """One regex, one entity type.

    `group` selects the part of the match that is the entity. A context word
    can be in the regex and still stay outside the entity.
    `score_fn` gives the score from the matched text.
    """

    def __init__(
        self,
        entity: str,
        pattern: str,
        language: str,
        *,
        group: int = 0,
        score: float = 0.85,
        score_fn: Optional[Callable[[str], Optional[float]]] = None,
        flags: int = re.IGNORECASE,
        name: Optional[str] = None,
    ):
        self.pattern = re.compile(pattern, flags)
        self.group = group
        self.score = score
        self.score_fn = score_fn
        super().__init__(
            supported_entities=[entity],
            supported_language=language,
            name=name or f"Regex[{entity}]",
        )

    def load(self) -> None:
        return None

    def analyze(self, text, entities, nlp_artifacts=None) -> list[RecognizerResult]:
        entity = self.supported_entities[0]
        results = []
        for match in self.pattern.finditer(text):
            start, end = match.span(self.group)
            if start < 0 or start == end:
                continue
            value = text[start:end]
            score = self.score_fn(value) if self.score_fn else self.score
            if not score:
                continue
            results.append(
                RecognizerResult(
                    entity_type=entity,
                    start=start,
                    end=end,
                    score=score,
                    recognition_metadata={
                        RecognizerResult.RECOGNIZER_NAME_KEY: self.name,
                        RecognizerResult.RECOGNIZER_IDENTIFIER_KEY: self.id,
                    },
                )
            )
        return results


# --- the Romanian and general patterns ---------------------------------------

EMAIL = r"(?<![\w.+-])[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![\w-])"

CNP = r"(?<![\d.])[1-9]\d{12}(?![\d])"
CNP_CONTEXT = r"\b(?:C\.?N\.?P\.?|cod\s+numeric\s+personal|personal\s+numeric\s+code)\s*(?:nr\.?|no\.?|:|-)?\s*(\d{13})(?!\d)"

# "CUI: RO 1234567" - the context word is outside the entity.
CUI_CONTEXT = (
    r"\b(?:C\.?U\.?I\.?|C\.?I\.?F\.?|cod\s+fiscal|cod\s+unic\s+de\s+[iî]nregistrare|"
    r"VAT(?:\s+(?:no|number|id))?|TVA|tax\s+id)\s*(?:nr\.?|no\.?|:|-|/)?\s*"
    r"((?:RO\s?)?\d{2,10})(?!\d)"
)
CUI_WITH_PREFIX = r"(?<![\w])(RO\s?\d{2,10})(?![\w])"

TRADE_REG = r"(?<![\w/])([JFC]\s?\d{1,2}\s?/\s?\d{1,6}\s?/\s?\d{2,4})(?![\w/])"

ID_CARD = (
    r"\b(?:seria|serie|series|CI|B\.?I\.?)\s+"
    r"((?-i:[A-Z]{2})\s*,?\s*(?:nr\.?|num[aă]rul|num[aă]r|no\.?)?\s*\d{6})(?!\d)"
)
PASSPORT_RO = (
    r"\bpa[sș]aport(?:ul)?\s*(?:nr\.?|no\.?|num[aă]r(?:ul)?)?\s*:?\s*"
    r"((?-i:(?=[A-Z0-9]*\d)[A-Z0-9]{8,9}))\b"
)
PASSPORT_EN = (
    r"\bpassport\s*(?:no\.?|number|nr\.?)?\s*:?\s*"
    r"((?-i:(?=[A-Z0-9]*\d)[A-Z0-9]{8,9}))\b"
)

CASE_NUMBER_RO = (
    r"\b(?:dosar(?:ul)?|cauza|cazul)\s*(?:civil\s+|penal\s+)?(?:nr\.?|num[aă]r(?:ul)?)?\s*:?\s*"
    r"(\d{1,6}\s?/\s?\d{1,4}(?:\s?/\s?\d{2,4})?(?:/[A-Za-z]\d*(?:\.\w+)?)?)"
)
# A number of a company in the UK register (8 digits, or 2 letters and 6 digits).
COMPANY_NUMBER = (
    r"\b(?:company|registered)\s+(?:number|no\.?|registration\s+(?:number|no\.?))\s*:?\s*"
    r"((?-i:(?:[A-Z]{2})?\d{6,8}))\b"
)
# UK postcode, for example "LS11 9AQ". It needs real capital letters.
UK_POSTCODE = r"\b([A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2})\b"

CASE_NUMBER_EN = (
    r"\b(?:case|docket|file|claim|consignment\s+note|CMR\s+note|waybill)\s*(?:no\.?|number|nr\.?|#)\s*:?\s*"
    r"((?-i:[A-Z0-9][A-Za-z0-9]*(?:[-/.][A-Za-z0-9]+){1,5}))"
)

POSTAL_CODE = r"\b(?:cod\s+po[sș]tal|postcode|postal\s+code|zip(?:\s+code)?)\s*:?\s*(\d{5,6})\b"

STREET_TYPES = (
    r"(?i:strada|str\.?|bulevardul|b-dul|bd\.?|calea|aleea|[sșş]oseaua|[sșş]os\.?|"
    r"pia[tțţ]a|splaiul|drumul|intrarea|prelungirea)"
)
_NAME_WORD = rf"(?:{CAP}[\wăâîșțşţ'-]*\.?|\d+[A-Za-z]?|de|din|a|al|lui|cel|ale)"
_NR = r"(?i:nr\.?|num[aă]rul)"
_UNIT = (
    r"(?i:bl\.?|bloc|sc\.?|scara|et\.?|etaj|ap\.?|apartament|camera|cam\.?|"
    r"sector|sectorul|jud\.?|jude[tț]ul)"
)
RO_ADDRESS = (
    rf"\b({STREET_TYPES}\s+{_NAME_WORD}(?:\s+{_NAME_WORD}){{0,5}}"
    rf"\s*,?\s*{_NR}\s*\d+\s?[A-Za-z]?"
    rf"(?:\s*,\s*{_UNIT}\s*[\w./-]+)*)"
)
EN_ADDRESS = (
    r"\b(\d{1,5}[A-Za-z]?\s+(?:[A-Z][\w'.-]*\s+){1,4}"
    r"(?:Street|St\.?|Road|Rd\.?|Avenue|Ave\.?|Boulevard|Blvd\.?|Lane|Ln\.?|Drive|Dr\.?|"
    r"Court|Ct\.?|Way|Place|Pl\.?|Square|Terrace|Close|Crescent|Highway|Hwy\.?)"
    r"(?:\s*,?\s*(?:Suite|Ste\.?|Apt\.?|Apartment|Unit|Floor|Flat)\s*[\w-]+)?)\b"
)


def _cnp_score(value: str) -> Optional[float]:
    return 1.0 if valid_cnp(value) else None


def _cnp_context_score(value: str) -> Optional[float]:
    # The context word is the proof. A bad checksum can be a typing error.
    return 1.0 if valid_cnp(value) else 0.8


def _cui_context_score(value: str) -> Optional[float]:
    # The context word is the proof. A bad checksum can be a typing error,
    # so we still hide it (the risk of a leak is higher than a false hit).
    return 0.95 if valid_cui(value) else 0.8


def _cui_prefix_score(value: str) -> Optional[float]:
    return 0.85 if valid_cui(value) else None


def build_pattern_recognizers(language: str) -> list[LocalRecognizer]:
    R = RegexRecognizer
    exact = 0  # no IGNORECASE: the pattern needs real capital letters
    return [
        R("EMAIL_ADDRESS", EMAIL, language, score=0.95, name="Email"),
        R("RO_CNP", CNP, language, score_fn=_cnp_score, flags=exact, name="RoCnp"),
        R("RO_CNP", CNP_CONTEXT, language, group=1, score_fn=_cnp_context_score, name="RoCnpContext"),
        R("RO_CUI", CUI_CONTEXT, language, group=1, score_fn=_cui_context_score, name="RoCuiContext"),
        R("RO_CUI", CUI_WITH_PREFIX, language, group=1, score_fn=_cui_prefix_score, flags=exact, name="RoCuiPrefix"),
        R("RO_TRADE_REG", TRADE_REG, language, group=1, score=0.9, flags=exact, name="RoTradeReg"),
        R("ID_DOCUMENT", ID_CARD, language, group=1, score=0.9, name="IdCard"),
        R("ID_DOCUMENT", PASSPORT_RO, language, group=1, score=0.85, name="PassportRo"),
        R("ID_DOCUMENT", PASSPORT_EN, language, group=1, score=0.85, name="PassportEn"),
        R("CASE_NUMBER", CASE_NUMBER_RO, language, group=1, score=0.9, name="CaseNumberRo"),
        R("CASE_NUMBER", CASE_NUMBER_EN, language, group=1, score=0.85, name="CaseNumberEn"),
        R("ADDRESS", RO_ADDRESS, language, group=1, score=0.85, flags=exact, name="RoAddress"),
        R("ADDRESS", EN_ADDRESS, language, group=1, score=0.8, flags=exact, name="EnAddress"),
        R("ADDRESS", POSTAL_CODE, language, group=1, score=0.8, name="PostalCode"),
        R("ADDRESS", UK_POSTCODE, language, group=1, score=0.8, flags=exact, name="UkPostcode"),
        R("COMPANY_NUMBER", COMPANY_NUMBER, language, group=1, score=0.9, name="CompanyNumber"),
    ]
