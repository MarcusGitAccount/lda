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
    "MONEY": "MONEY",
}
TYPE_BY_TAG = {tag: entity for entity, tag in TAGS.items()}

# These types come from patterns, often with a checksum. They win over NER.
STRUCTURED = {
    "EMAIL_ADDRESS", "PHONE_NUMBER", "IBAN_CODE", "CREDIT_CARD", "URL",
    "IP_ADDRESS", "RO_CNP", "RO_CUI", "RO_TRADE_REG", "COMPANY_NUMBER",
    "ID_DOCUMENT", "CASE_NUMBER",
}  # fmt: skip

# What we hide if the user gives no other list. DATE_TIME and MONEY are
# optional: they are often needed to understand a contract. NRP (nationality,
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
