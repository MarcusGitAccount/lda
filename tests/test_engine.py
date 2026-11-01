"""Engine logic with a stub detector. No model is loaded."""

import re

from legal_anonymizer.config import SeedEntity, Settings
from legal_anonymizer.engine import Engine
from legal_anonymizer.spans import Span


class StubDetector:
    """Finds only the exact texts in `known`, as the given type."""

    def __init__(self, known: dict[str, str]):
        self.known = known

    def language_of(self, text, language=None):
        return language or "ro"

    def detect(self, text, language, settings=None, context=None):
        spans = []
        for needle, entity_type in self.known.items():
            for m in re.finditer(re.escape(needle), text):
                spans.append(Span(m.start(), m.end(), entity_type, 0.9, "presidio"))
        return spans


def make_engine(vault, known, settings=None):
    return Engine(vault, settings or Settings(), StubDetector(known))


def test_name_found_in_one_document_is_hidden_in_all_documents_of_the_batch(vault):
    # The model finds the name only in doc "late". Doc "early" is first in the list.
    early = b"Nota: sunati-l pe POPESCU ION la birou."
    late = b"Contract cu Ion Popescu."
    engine = Engine(vault, Settings(), StubDetector({"Ion Popescu": "PERSON"}))
    first, second = engine.anonymize_many([("early.txt", early), ("late.txt", late)])
    assert first.data.decode() == "Nota: sunati-l pe [PERSON_001] la birou."
    assert second.data.decode() == "Contract cu [PERSON_001]."
    assert first.leaks == [] and second.leaks == []


def test_entity_keeps_its_id_in_a_later_run_and_new_entities_get_new_ids(vault):
    engine = make_engine(vault, {"Ion Popescu": "PERSON", "Maria Ionescu": "PERSON"})
    engine.anonymize("a.txt", b"Ion Popescu")
    out = engine.anonymize("b.txt", b"Maria Ionescu si Ion Popescu")
    assert out.data.decode() == "[PERSON_002] si [PERSON_001]"


def test_vault_type_wins_if_the_model_changes_its_mind(vault):
    engine = make_engine(vault, {"Alfa": "ORGANIZATION"})
    engine.anonymize("a.txt", b"Alfa a semnat.")
    engine.detector = StubDetector({"Alfa": "LOCATION"})  # another document, another label
    out = engine.anonymize("b.txt", b"In Alfa.")
    assert out.data.decode() == "In [ORG_001]."


def test_seed_entities_and_aliases_are_hidden_without_the_model(vault):
    settings = Settings(seeds=[SeedEntity("PERSON", "Ion Popescu", ["Popescu", "dl. Popescu"])])
    engine = make_engine(vault, {}, settings)  # the stub finds nothing
    engine.load_seeds()
    out = engine.anonymize("a.txt", "Domnul POPESCU a venit. Ion Popescu a plecat.".encode())
    assert out.data.decode() == "Domnul [PERSON_001] a venit. [PERSON_001] a plecat."
    assert vault.entities()[0].canonical == "Ion Popescu"


def test_diacritics_case_and_spacing_do_not_hide_a_known_name(vault):
    engine = make_engine(vault, {"Ștefan Țurcanu": "PERSON"})
    engine.anonymize("a.txt", "Ștefan Țurcanu".encode())
    out = engine.anonymize("b.txt", "STEFAN  TURCANU, Ştefan Ţurcanu și ștefan țurcanu".encode())
    assert out.data.decode() == "[PERSON_001], [PERSON_001] și [PERSON_001]"


def test_a_known_name_is_not_found_inside_another_word(vault):
    engine = make_engine(vault, {"Alfa": "ORGANIZATION"})
    engine.anonymize("a.txt", b"Alfa")
    engine.detector = StubDetector({})  # only the sweep works on the second document
    out = engine.anonymize("b.txt", b"Alfabet, alfanumeric, Alfa.")
    assert out.data.decode() == "Alfabet, alfanumeric, [ORG_001]."


def test_two_companies_with_different_legal_forms_stay_apart(vault):
    engine = make_engine(vault, {"Alfa Construct SRL": "ORGANIZATION", "Alfa Construct SA": "ORGANIZATION"})
    out = engine.anonymize("a.txt", b"Alfa Construct SRL vinde catre Alfa Construct SA.")
    assert out.data.decode() == "[ORG_001] vinde catre [ORG_002]."


def test_roundtrip_is_exact_when_every_entity_has_one_written_form(vault):
    original = "Contract intre Ion Popescu si SC Alfa SRL.\nSemnat: Ion Popescu.\n"
    engine = make_engine(vault, {"Ion Popescu": "PERSON", "SC Alfa SRL": "ORGANIZATION"})
    anon = engine.anonymize("c.txt", original.encode())
    assert "Popescu" not in anon.data.decode()
    assert engine.restore("c.anon.txt", anon.data).data.decode() == original


def test_restoring_after_an_ai_tool_changed_the_text(vault):
    engine = make_engine(vault, {"Ion Popescu": "PERSON", "SC Alfa SRL": "ORGANIZATION"})
    engine.anonymize("c.txt", b"Ion Popescu reprezinta SC Alfa SRL.")  # this fills the vault
    revised = "Revizuit: [ORG_001] este reprezentata de [PERSON_001], iar [PERSON_001] semneaza."
    assert engine.restore("r.txt", revised.encode()).data.decode() == (
        "Revizuit: SC Alfa SRL este reprezentata de Ion Popescu, iar Ion Popescu semneaza."
    )


def test_hide_setting_limits_the_types(vault):
    settings = Settings(hide={"PERSON"})
    engine = make_engine(vault, {"Ion Popescu": "PERSON", "Cluj": "LOCATION"}, settings)
    # The stub ignores `hide`; the sweep must respect it. Cluj is not in the vault as a hidden type.
    out = engine.anonymize("a.txt", b"Ion Popescu din Cluj")
    assert "[PERSON_001]" in out.data.decode()


def test_document_is_recorded_with_counts(vault):
    engine = make_engine(vault, {"Ion Popescu": "PERSON"})
    engine.anonymize("a.txt", b"Ion Popescu si Ion Popescu")
    assert [d["name"] for d in vault.documents()] == ["a.txt"]
    assert vault.entities()[0].documents == ["a.txt"]


def test_kept_text_stays_visible_and_is_not_a_leak(vault):
    # "Tribunalul Mureș" is kept by the policy. "Mureș" is a known place, hidden elsewhere.
    engine = make_engine(vault, {"Tribunalul Mureș": "KEEP", "Mureș": "LOCATION"})
    text = "Tribunalul Mureș a decis. Sediul este în jud. Mureș.".encode()
    result = engine.anonymize("a.txt", text)
    out = result.data.decode()
    assert out.startswith("Tribunalul Mureș a decis.")
    assert "jud. [LOCATION_001]." in out
    assert result.leaks == []
    assert engine.find_leaks("b.txt", "Tribunalul Mureș".encode()) == []
    assert engine.find_leaks("b.txt", "jud. Mureș".encode()) == ["[LOCATION_001]"]


def test_the_seed_name_wins_over_its_aliases_when_the_alias_is_more_common(vault):
    settings = Settings(seeds=[SeedEntity("ORGANIZATION", "Northgate Freight Forwarding Ltd", ["Northgate"])])
    engine = make_engine(vault, {}, settings)
    engine.load_seeds()
    text = "Northgate plateste. Northgate a primit. Northgate Freight Forwarding Ltd semneaza.".encode()
    result = engine.anonymize("a.txt", text)
    restored = engine.restore("a.anon.txt", result.data).data.decode()
    assert vault.lookup("ORGANIZATION", 1).canonical == "Northgate Freight Forwarding Ltd"
    assert restored.count("Northgate Freight Forwarding Ltd") == 3  # a known limit: the short name restores as the full name
