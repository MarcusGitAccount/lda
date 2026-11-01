"""End-to-end tests with the real NER models on the synthetic case in data/samples/.

The first run downloads the models. Run only the fast tests with: pytest -m "not models"
"""

import json
import re
from pathlib import Path

import pytest

from legal_anonymizer.config import load_settings
from legal_anonymizer.documents import open_document, scan_text
from legal_anonymizer.engine import Engine
from legal_anonymizer.textnorm import fold
from legal_anonymizer.vault import PLACEHOLDER_RE, Vault
from samples import build_docx

pytestmark = pytest.mark.models

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"
GOLD = json.loads((SAMPLES / "gold.json").read_text(encoding="utf-8"))
TEXT_FILES = [
    "01_contract_prestari_servicii.ro.txt",
    "02_notificare_reziliere.ro.txt",
    "03_settlement_agreement.en.txt",
]


def contains(text: str, needle: str) -> bool:
    return fold(needle) in fold(text)


@pytest.fixture(scope="module")
def case(detector, tmp_path_factory):
    settings = load_settings(SAMPLES / "matter.yaml")
    with Vault(tmp_path_factory.mktemp("vault") / "case.db") as vault:
        engine = Engine(vault, settings, detector)
        engine.load_seeds()
        files = [(name, (SAMPLES / name).read_bytes()) for name in TEXT_FILES]
        results = engine.anonymize_many(files)
        yield engine, vault, dict(files), dict(zip(TEXT_FILES, results))


def test_languages_are_detected(case):
    _, _, _, results = case
    assert [results[n].language for n in TEXT_FILES] == ["ro", "ro", "en"]


def test_nothing_from_the_must_hide_list_is_left(case):
    _, _, _, results = case
    for name, result in results.items():
        text = result.data.decode()
        for phrase in GOLD["visible_ok"]:  # a court stays visible (keep_public_bodies)
            text = text.replace(phrase, " ")
        for secret in GOLD["must_hide"]:
            assert not contains(text, secret), f"{name} still has {secret!r}:\n{text}"
        assert result.leaks == []


def test_words_that_the_reader_needs_stay_visible(case):
    _, _, _, results = case
    everything = "\n".join(r.data.decode() for r in results.values())
    for word in GOLD["must_keep"]:
        assert word in everything, word


def test_same_entity_has_the_same_id_in_every_document(case):
    engine, vault, _, results = case
    ion = vault.resolve("PERSON", "Ion Popescu", count=0).placeholder
    maria = vault.resolve("PERSON", "Maria Ionescu", count=0).placeholder
    alfa = vault.resolve("ORGANIZATION", "Alfa Construct SRL", count=0).placeholder
    out = {n: r.data.decode() for n, r in results.items()}
    # Ion Popescu: "dl. Ion Popescu", "dl. Popescu", "Popescu Ion", "Mr. Ion Popescu"
    for name in TEXT_FILES:
        assert ion in out[name], name
        assert alfa in out[name], name
    assert maria in out[TEXT_FILES[0]] and maria in out[TEXT_FILES[1]]
    assert "Popescu" not in "".join(out.values())
    # one id for each person and company in the case
    people = [e for e in vault.entities() if e.type == "PERSON"]
    assert sorted(e.canonical for e in people) == ["Ion Popescu", "Jane Doe", "Maria Ionescu"]
    orgs = [e for e in vault.entities() if e.type == "ORGANIZATION"]
    assert sorted(e.canonical for e in orgs if "Alfa" in e.canonical or "Beta" in e.canonical or "Northwind" in e.canonical) == [
        "Beta Logistic SA", "Northwind Traders Ltd", "SC Alfa Construct SRL",
    ]
    assert vault.resolve("PERSON", "Ion Popescu", count=0).documents == TEXT_FILES


def test_structured_data_gets_its_own_type(case):
    _, _, _, results = case
    text = results[TEXT_FILES[0]].data.decode()
    for tag in ["CNP", "CUI", "IBAN", "EMAIL", "PHONE", "ID_DOC", "TRADE_REG", "CASE_NO", "ADDRESS"]:
        assert re.search(rf"\[{tag}_\d+\]", text), tag


def test_restore_gives_back_every_secret_and_leaves_no_id(case):
    engine, _, originals, results = case
    for name, result in results.items():
        restored = engine.restore(name, result.data)
        text = restored.data.decode()
        assert not PLACEHOLDER_RE.search(text), name
        assert restored.unknown == []
        original = originals[name].decode()
        # CNP, IBAN and so on come back as they were
        for token in re.findall(r"\b\d{13}\b|\bRO\d{2}[A-Z]{4}\w{16}\b|[\w.]+@[\w.]+", original):
            assert token in text, (name, token)


def test_anonymizing_the_restored_text_gives_the_same_anonymized_text(case):
    engine, _, _, results = case
    for name, result in results.items():
        restored = engine.restore(name, result.data).data
        again = engine.anonymize(name, restored)
        assert again.data == result.data, name


def test_docx_with_tracked_changes_header_footnote_comment_and_metadata(case):
    engine, _, _, _ = case
    source = build_docx(comment="Verificați CNP-ul lui Ion Popescu.")
    result = engine.anonymize("contract.docx", source)
    text = scan_text("contract.docx", result.data)
    for secret in GOLD["docx_must_hide"]:
        assert not contains(text, secret), f"{secret!r} is still in the docx"
    assert result.leaks == []
    units = open_document("contract.docx", result.data).units()
    assert any(re.fullmatch(r"Beneficiar: \[PERSON_\d+\], telefon \[PHONE_\d+\]\.", u) for u in units), units
    assert "Prețul este de 25.000 EUR." in units
    # restore: the names are back in their places
    back = open_document("contract.docx", engine.restore("contract.docx", result.data).data).units()
    assert "Beneficiar: Ion Popescu, telefon 0722 123 456." in back
    assert "Sediu:\tCluj-Napoca" in back


def test_a_leak_in_a_part_that_we_do_not_process_is_reported(case):
    engine, _, _, _ = case
    source = build_docx(extra_links=(("rId9", "mailto:ion.popescu@alfaconstruct.ro"),))
    result = engine.anonymize("link.docx", source)
    assert result.leaks, "the e-mail is in a link target; the check must find it"
    assert any(p.startswith("[EMAIL_") for p in result.leaks)
