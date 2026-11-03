"""Tests for the findings of the adversarial review of 2026-11-02 (R-01 to R-12). No model is loaded,
except in the tests with the mark `models`.

Each test is a case that the old code got wrong.
"""

import re
import unicodedata

import pytest

from legal_anonymizer.config import Settings
from legal_anonymizer.detector import is_common_word, is_named_after_a_marker
from legal_anonymizer.engine import Engine, glued_form
from legal_anonymizer.romanian import same_word
from legal_anonymizer.spans import Span
from legal_anonymizer.vault import Vault


class Stub:
    """Finds only the exact texts in `known`, with their type."""

    def __init__(self, known):
        self.known = known

    def language_of(self, text, language=None):
        return language or "ro"

    def detect(self, text, language, settings=None, context=None):
        return [
            Span(m.start(), m.end(), kind, 0.9, "presidio")
            for needle, kind in self.known.items()
            for m in re.finditer(re.escape(needle), text)
        ]


def engine_for(vault, known):
    return Engine(vault, Settings(), Stub(known))


# --- R-01: a surname that is also a common word ------------------------------------


@pytest.mark.parametrize(
    ("text", "word", "expected"),
    [
        ("Mr Brown signed. The vehicle was brown.", "Brown", False),  # after a title
        ("Pârâtul Negru a semnat. Culoarea negru.", "Negru", False),  # after a role word
        ("Dl. Negru a semnat. Culoarea negru.", "Negru", False),  # after "dl."
        ("Contractul lui Negru. Culoarea negru.", "Negru", False),  # after "lui"
        ("Negru a semnat. Dl. Negru. Culoarea negru.", "Negru", False),  # the same word is a name in another place
        ("Acordul Părților este scris. Părților li se spune părților.", "Părților", True),  # a defined term
        ("The car is old. Brown is a colour. brown", "Brown", True),  # no title anywhere
        ("Acordul Părților. părților", "Părților", True),
    ],
)
def test_a_surname_that_a_title_shows_is_not_a_common_word(text, word, expected):
    start = text.index(word)
    span = Span(start, start + len(word), "PERSON")
    assert is_common_word(text, span, text) is expected


def test_a_name_marker_is_a_title_or_a_role_but_not_an_article():
    assert is_named_after_a_marker("Brown", "Mr Brown and Ms Green")
    assert is_named_after_a_marker("Green", "Mr Brown and Ms. Green")
    assert not is_named_after_a_marker("Parties", "the Parties and a Parties")
    assert not is_named_after_a_marker("Brown", "Brown and brown")


def test_a_common_noun_inside_a_sentence_is_still_dropped_for_an_organization():
    text = "A decis the Court. The court is here."
    start = text.index("Court")
    assert is_common_word(text, Span(start, start + 5, "ORGANIZATION"), text)


def test_a_name_that_is_a_colour_is_hidden_and_the_colour_stays(vault):
    engine = engine_for(vault, {"Brown": "PERSON"})
    text = "Mr Brown signed. The vehicle was brown. Mr Brown paid. The brown wall is old."
    result = engine.anonymize("a.txt", text.encode())
    assert result.data.decode() == "Mr [PERSON_001] signed. The vehicle was brown. Mr [PERSON_001] paid. The brown wall is old."
    assert result.leaks == []  # the leak check agrees with the sweep
    assert engine.restore("a.anon.txt", result.data).data.decode() == text  # the colour was never an id


def test_a_text_in_lower_case_hides_every_form(vault):
    engine = engine_for(vault, {"Brown": "PERSON"})
    engine.anonymize("a.txt", b"Mr Brown signed.")
    out = engine.anonymize("b.txt", b"mesaj: brown a scris, brown a plecat")  # no capital letter anywhere
    assert out.data.decode() == "mesaj: [PERSON_001] a scris, [PERSON_001] a plecat"


def test_a_message_in_lower_case_hides_a_surname_alone_even_if_other_documents_have_capitals(vault):
    engine = engine_for(vault, {"Popescu": "PERSON"})
    out = engine.anonymize_many([("b.txt", b"Contract cu Dl. Popescu."), ("c.txt", b"buna, popescu a zis ca vine")])
    assert out[0].data.decode() == "Contract cu Dl. [PERSON_001]."
    assert out[1].data.decode() == "buna, [PERSON_001] a zis ca vine"
    assert out[1].leaks == []


def test_a_lower_case_form_of_a_known_name_stays_with_a_capital_in_the_vault(vault):
    engine = engine_for(vault, {"Will": "PERSON"})
    engine.anonymize("a.txt", b"Will signed. He will pay. will")
    (entity,) = vault.entities()
    assert entity.canonical == "Will" and list(entity.forms) == ["Will"]


def test_a_lower_case_inflected_form_is_a_common_word(vault):
    engine = engine_for(vault, {"Bunu": "PERSON", "Lungu": "PERSON"})
    text = "Reclamantul Bunu a vândut bunul imobil. Valoarea bunului este mare. Martorul Lungu a descris lungul drum."
    result = engine.anonymize("a.txt", text.encode())
    assert result.data.decode() == (
        "Reclamantul [PERSON_001] a vândut bunul imobil. Valoarea bunului este mare. Martorul [PERSON_002] a descris lungul drum."
    )
    assert result.leaks == []


@pytest.mark.models
def test_real_models_hide_a_surname_that_is_a_colour(detector, tmp_path):
    with Vault(tmp_path / "v.db") as vault:
        engine = Engine(vault, Settings(), detector)
        en = engine.anonymize(
            "en.txt",
            b"Mr Brown signed the agreement on behalf of the Seller. The vehicle was brown. Mr Brown paid the deposit.\n"
            b"Ms White is the witness. The walls are white.",
        ).data.decode()
        assert "Brown" not in en and "White" not in en
        ro = engine.anonymize(
            "ro.txt",
            "Pârâtul Negru a semnat contractul. Autoturismul era de culoare negru. Domnul Negru a plătit avansul.".encode(),
        ).data.decode()
        assert "Negru" not in ro


# --- R-02: restore ----------------------------------------------------------------------


@pytest.fixture
def restorer(vault):
    engine = engine_for(vault, {"Ion Popescu": "PERSON", "Alfa SRL": "ORGANIZATION"})
    engine.anonymize("a.txt", b"Ion Popescu si Alfa SRL.")

    def restore(text):
        return engine.restore("x.txt", text.encode())

    return restore


@pytest.mark.parametrize(
    "written",
    [
        "[PERSON_001]", "[person_001]", "[Person_001]", "[PERSON_1]", "[ PERSON 001 ]", "[PERSON-001]",
        "PERSON_001", "person_001", "(PERSON_001)", "{PERSON_001}", "**[PERSON_001]**", r"\[PERSON\_001\]",
        "[PERSOANA_001]", "[PERSOANĂ_001]", "[Persoana_001]", "［PERSON_001］",
    ],
)  # fmt: skip
def test_restore_reads_a_changed_id(restorer, written):
    result = restorer(f"Contract cu {written}.")
    assert "Ion Popescu" in result.data.decode()
    assert "PERSON" not in result.data.decode().upper().replace("PERSOANA", "")
    assert result.unknown == [] and result.suspect == []


def test_restore_reads_the_long_name_of_the_type(restorer):
    assert restorer("[ORGANIZATION_001] si [ORG_001]").data.decode() == "Alfa SRL si Alfa SRL"
    assert restorer("[ORGANIZAȚIE_001]").data.decode() == "Alfa SRL"


def test_restore_reads_each_id_of_a_list(restorer):
    result = restorer("[PERSON_001 si ORG_001]")
    assert result.data.decode() == "[Ion Popescu si Alfa SRL]"


def test_restore_does_not_read_ordinary_words_as_ids(restorer):
    text = "Person 1 and Data 1 and [Persoana 1] and [Anexa 1] and COVID-19 and Organization 1"
    result = restorer(text)
    assert result.data.decode() == text and result.suspect == []


@pytest.mark.parametrize("written", ["[PERSONNE_001]", "[PERSONNE 001]", "PERS_12", "[PERSON＿001]"])
def test_restore_reports_an_id_that_it_cannot_read(restorer, written):
    result = restorer(f"Contract cu {written}.")
    assert result.suspect, written


def test_restore_reports_an_unknown_number_and_does_not_count_it_twice(restorer):
    result = restorer("[PERSON_042]")
    assert result.unknown == ["[PERSON_042]"] and result.suspect == []


def test_restore_gives_the_romanian_ending_after_a_glued_id(restorer):
    result = restorer("Cererea [PERSON_001]ului si [PERSON_001]-ului.")
    assert result.data.decode() == "Cererea Ion Popescului si Ion Popescului." and result.suspect == []


def test_restore_reports_letters_that_it_cannot_join_to_an_id(restorer):
    result = restorer("Contract [ORG_001]xyz.")
    assert result.suspect == ["[ORG_001]xyz"]


def test_glued_forms():
    assert glued_form("Ion Popescu", "ului") == "Ion Popescului"
    assert glued_form("Maria Ionescu", "ului") == "Maria Ionescului"
    assert glued_form("Brașov", "ului") == "Brașovului"
    assert glued_form("Maria", "ei") == "Mariei"
    assert glued_form("Ion", "zzz") is None


# --- R-04, R-05: the Romanian forms ----------------------------------------------------


@pytest.mark.parametrize(
    ("one", "other"),
    [("Andra Popescu", "Andrei Popescu"), ("Mata Ionescu", "Matei Ionescu"), ("Paul Rusu", "Pau Rusu")],
)
def test_two_different_people_keep_two_ids(vault, one, other):
    engine = engine_for(vault, {one: "PERSON", other: "PERSON"})
    result = engine.anonymize("a.txt", f"{one} si {other}.".encode())
    assert result.data.decode() == "[PERSON_001] si [PERSON_002]."
    assert engine.restore("b.txt", result.data).data.decode() == f"{one} si {other}."


def test_a_real_genitive_still_joins(vault):
    engine = engine_for(vault, {"Maria Ionescu": "PERSON", "Mariei Ionescu": "PERSON"})
    out = engine.anonymize("a.txt", b"Maria Ionescu. Cererea Mariei Ionescu.")
    assert out.data.decode() == "[PERSON_001]. Cererea [PERSON_001]."


def test_the_rules_do_not_make_andrei_from_andra():
    assert not same_word("andra", "andrei") and not same_word("matei", "mata")
    assert not same_word("pau", "paul")
    assert same_word("maria", "mariei") and same_word("popescu", "popescului") and same_word("ion", "ionul")


@pytest.mark.parametrize(
    "text",
    [
        "Pârâtul Popescu locuiește în orașul Popești-Leordeni.",
        "Martorul Popescu a fost în comuna Popești, jud. Ilfov.",
    ],
)
def test_a_surname_does_not_hide_a_place_that_ends_in_esti(vault, text):
    engine = engine_for(vault, {"Popescu": "PERSON"})
    out = engine.anonymize("a.txt", text.encode()).data.decode()
    assert "Popești" in out and "[PERSON_001]" in out
    assert engine.restore("b.txt", out.encode()).data.decode() == text


def test_the_family_plural_with_the_article_is_still_found(vault):
    engine = engine_for(vault, {"Popescu": "PERSON"})
    out = engine.anonymize("a.txt", b"Popescu a venit. Casa Popestilor si Popestii.")
    assert out.data.decode() == "[PERSON_001] a venit. Casa [PERSON_001] si [PERSON_001]."


# --- R-12: letters in another Unicode form -------------------------------------------


def test_a_name_in_decomposed_unicode_is_hidden(vault):
    engine = engine_for(vault, {"Ștefan Țăranu": "PERSON"})
    engine.anonymize("a.txt", "Ștefan Țăranu a semnat.".encode())
    nfd = unicodedata.normalize("NFD", "Contract cu Ștefan Țăranu.")
    assert nfd != unicodedata.normalize("NFC", nfd)
    result = engine.anonymize("b.txt", nfd.encode())
    assert result.data.decode() == "Contract cu [PERSON_001]."
    assert result.leaks == []


def test_the_leak_check_sees_a_name_in_decomposed_unicode(vault):
    engine = engine_for(vault, {"Ștefan Țăranu": "PERSON"})
    engine.anonymize("a.txt", "Ștefan Țăranu a semnat.".encode())
    nfd = unicodedata.normalize("NFD", "Ștefan Țăranu")
    assert engine.find_leaks("c.txt", nfd.encode()) == ["[PERSON_001]"]


# --- R-11: remove a wrong entity, split a wrong join -----------------------------------


def test_forget_stops_the_hiding_of_a_word_that_is_not_a_name(vault):
    engine = engine_for(vault, {"Convention": "PERSON", "Ion Popescu": "PERSON"})
    first = engine.anonymize("a.txt", b"Convention. Ion Popescu.")
    assert first.data.decode() == "[PERSON_001]. [PERSON_002]."
    entity = vault.by_placeholder("[PERSON_001]")
    assert vault.forget(entity.id).ignored
    second = engine.anonymize("b.txt", b"Convention. Ion Popescu.")
    assert second.data.decode() == "Convention. [PERSON_002]."
    assert second.leaks == []
    # An old document that has the id still restores.
    assert engine.restore("a.anon.txt", first.data).data.decode() == "Convention. Ion Popescu."


def test_split_gives_one_name_its_own_id(vault):
    engine = engine_for(vault, {"Maria Ionescu": "PERSON", "Mariei Ionescu": "PERSON"})
    engine.anonymize("a.txt", b"Maria Ionescu. Mariei Ionescu.")
    (entity,) = vault.entities()
    assert set(entity.forms) == {"Maria Ionescu", "Mariei Ionescu"}
    new = vault.split(entity.id, "Mariei Ionescu")
    assert new.placeholder == "[PERSON_002]" and list(new.forms) == ["Mariei Ionescu"]
    out = engine.anonymize("b.txt", b"Maria Ionescu. Mariei Ionescu.")
    assert out.data.decode() == "[PERSON_001]. [PERSON_002]."
    with pytest.raises(ValueError):
        vault.split(new.id, "Mariei Ionescu")  # the only name


def test_a_file_with_a_leak_goes_to_the_folder_needs_review(tmp_path, monkeypatch):
    from legal_anonymizer import cli

    monkeypatch.setattr("legal_anonymizer.engine.Detector", lambda settings: Stub({"Ion Popescu": "PERSON"}))
    monkeypatch.setattr(Engine, "find_leaks", lambda self, name, data, reference=None, source=None: ["[PERSON_001]"])
    source = tmp_path / "a.txt"
    source.write_text("Contract cu Ion Popescu.")
    out = tmp_path / "out"
    code = cli.main(["--home", str(tmp_path / "h"), "anonymize", str(source), "-m", "t", "-o", str(out)])
    assert code == 1
    assert (out / "needs-review" / "a.anon.txt").exists() and not (out / "a.anon.txt").exists()


def test_a_clean_file_goes_to_the_main_folder(tmp_path, monkeypatch):
    from legal_anonymizer import cli

    monkeypatch.setattr("legal_anonymizer.engine.Detector", lambda settings: Stub({"Ion Popescu": "PERSON"}))
    source = tmp_path / "a.txt"
    source.write_text("Contract cu Ion Popescu.")
    out = tmp_path / "out"
    assert cli.main(["--home", str(tmp_path / "h"), "anonymize", str(source), "-m", "t", "-o", str(out)]) == 0
    assert (out / "a.anon.txt").read_text() == "Contract cu [PERSON_001]."


def test_the_restore_command_fails_when_an_id_is_suspect(tmp_path, monkeypatch, capsys):
    from legal_anonymizer import cli

    monkeypatch.setattr("legal_anonymizer.engine.Detector", lambda settings: Stub({"Ion Popescu": "PERSON"}))
    home = str(tmp_path / "h")
    source = tmp_path / "a.txt"
    source.write_text("Contract cu Ion Popescu.")
    cli.main(["--home", home, "anonymize", str(source), "-m", "t", "-o", str(tmp_path / "out")])
    edited = tmp_path / "b.txt"
    edited.write_text("Contract cu [PERSONNE_001].")
    assert cli.main(["--home", home, "restore", str(edited), "-m", "t", "-o", str(tmp_path / "back")]) == 1
    assert "looks like an id" in capsys.readouterr().out


# --- R-07: Romanian identifiers that the patterns missed ----------------------------------


@pytest.fixture(scope="module")
def recognizers():
    from legal_anonymizer.patterns import build_pattern_recognizers

    return build_pattern_recognizers("ro")


def found(recognizers, text):
    return sorted(
        (r.entity_type, text[r.start : r.end]) for rec in recognizers for r in rec.analyze(text, [rec.supported_entities[0]])
    )


@pytest.mark.parametrize(
    ("text", "kind", "value"),
    [
        ("CNP 180 0101 221144", "RO_CNP", "180 0101 221144"),
        ("CNP: 1-800101-221144", "RO_CNP", "1-800101-221144"),
        ("nr. de ordine în Registrul Comerțului J2020001234408", "RO_TRADE_REG", "J2020001234408"),
        ("autoturismul B 123 ABC a fost vândut", "ID_DOCUMENT", "B 123 ABC"),
        ("nr. înmatriculare B-123-ABC", "ID_DOCUMENT", "B-123-ABC"),
        ("auto CJ 12 XYZ", "ID_DOCUMENT", "CJ 12 XYZ"),
        ("carte funciară nr. 123456 a localității Cluj-Napoca", "ID_DOCUMENT", "123456"),
        ("nr. cadastral 234567-C1", "ID_DOCUMENT", "234567-C1"),
        ("polița RCA nr. RO/25/K25/HX 1234567", "ID_DOCUMENT", "RO/25/K25/HX 1234567"),
        ("sat Valea Seacă, com. Bucium, jud. Alba", "ADDRESS", "sat Valea Seacă, com. Bucium, jud. Alba"),
    ],
)
def test_the_pattern_finds_a_romanian_identifier(recognizers, text, kind, value):
    assert (kind, value) in found(recognizers, text)


@pytest.mark.parametrize(
    "text",
    ["EU 27 ABC", "Articolul 12 ABC", "județul Alba", "sat Valea Seacă", "CNP 180 0101 221145 9999"],
)
def test_the_new_patterns_do_not_hide_ordinary_text(recognizers, text):
    kinds = {kind for kind, _ in found(recognizers, text)}
    assert not kinds & {"ID_DOCUMENT", "RO_TRADE_REG", "ADDRESS"}, found(recognizers, text)
