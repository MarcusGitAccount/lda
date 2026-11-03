"""Entity types, placeholder tags and the default hiding policy."""

from __future__ import annotations

# Presidio entity type -> short tag in the placeholder, for example [PERSON_001].
TAGS = {
    "PERSON": "PERSON",
    "ORGANIZATION": "ORG",
    "LOCATION": "LOCATION",
    "ADDRESS": "ADDRESS",
    "EMAIL_ADDRESS": "EMAIL",
    "PHONE_NUMBER": "PHONE",
    "IBAN_CODE": "IBAN",
    "CREDIT_CARD": "CARD",
    "URL": "URL",
    "IP_ADDRESS": "IP",
    "RO_CNP": "CNP",
    "RO_CUI": "CUI",
    "RO_TRADE_REG": "TRADE_REG",
    "COMPANY_NUMBER": "COMPANY_NO",
    "ID_DOCUMENT": "ID_DOC",
    "CASE_NUMBER": "CASE_NO",
    "NRP": "NRP",
    "DATE_TIME": "DATE",
    "JOB_TITLE": "JOB",
    "MONEY": "MONEY",
}
TYPE_BY_TAG = {tag: entity for entity, tag in TAGS.items()}

# Other words that an AI tool can write in place of a tag (the long type name, or a Romanian word).
# The restore step reads them as the tag, but only with "_" and a number. The keys have no accents and
# no lower case. A common word ("name", "data", "company") is not in the list: a document can use it.
TAG_ALIASES = {
    "ORGANIZATION": "ORG", "ORGANIZATIE": "ORG", "ORGANISATION": "ORG",
    "PERSOANA": "PERSON", "PERSONA": "PERSON",
    "LOCATIE": "LOCATION", "LOCALITATE": "LOCATION",
    "ADRESA": "ADDRESS", "TELEFON": "PHONE", "TELEPHONE": "PHONE", "FUNCTIE": "JOB",
    "EMAIL_ADDRESS": "EMAIL", "IBAN_CODE": "IBAN", "PHONE_NUMBER": "PHONE", "CREDIT_CARD": "CARD",
}  # fmt: skip
# The same words with the Romanian letters, for the pattern of the restore step.
TAG_ALIAS_SPELLINGS = [*TAG_ALIASES, "PERSOANĂ", "ORGANIZAȚIE", "LOCAȚIE", "ADRESĂ", "FUNCȚIE"]


def type_of_tag(word: str) -> str | None:
    """The entity type for a tag as the text writes it: `ORG`, `org`, `Organization`, `ORGANIZAȚIE`."""
    folded = word.upper().translate(str.maketrans("ĂÂÎȘȚŞŢ", "AAISTST"))
    return TYPE_BY_TAG.get(folded) or TYPE_BY_TAG.get(TAG_ALIASES.get(folded, ""))

# These types come from patterns, often with a checksum. They win over NER.
STRUCTURED = {
    "EMAIL_ADDRESS", "PHONE_NUMBER", "IBAN_CODE", "CREDIT_CARD", "URL",
    "IP_ADDRESS", "RO_CNP", "RO_CUI", "RO_TRADE_REG", "COMPANY_NUMBER",
    "ID_DOCUMENT", "CASE_NUMBER",
}  # fmt: skip

# What we hide if the user gives no other list. DATE_TIME, JOB_TITLE and MONEY are
# optional: they are often needed to understand a contract. A deadline such as
# "30 days after [DATE_001]" cannot be worked out by an AI tool when the date is hidden.
# DATE_TIME means a calendar date (12.03.2024, 12 martie 2025, March 2025). A duration
# ("30 de zile") and a bare year stay visible. JOB_TITLE comes from a list of titles
# (director, administrator, avocat, chief executive officer). NRP (nationality,
# religion, political group) is optional too. In legal text the model finds mostly
# words like "român" in "societate de drept român". Add NRP if your documents
# describe people in this way.
DEFAULT_HIDE = {
    "PERSON", "ORGANIZATION", "LOCATION", "ADDRESS",
    *STRUCTURED,
}  # fmt: skip

ALL_TYPES = set(TAGS)


def priority(entity_type: str) -> int:
    """Lower number wins when two spans overlap and have the same length."""
    if entity_type in STRUCTURED:
        return 0
    if entity_type == "ADDRESS":
        return 1
    return 2
