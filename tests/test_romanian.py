"""Romanian word forms of names: `Popescu` is also written `Popescului`, `Popeștii`. No model is loaded."""

import re

import pytest

from legal_anonymizer.config import Settings
from legal_anonymizer.engine import Engine
from legal_anonymizer.romanian import bases, derives_from, inflections, same_lexeme, same_word
from legal_anonymizer.spans import Span

# --- the rules -----------------------------------------------------------------

FORMS = [
    # (base, other form)
    ("popescu", "popescul"),  # the article
    ("popescu", "popescului"),  # genitive, dative
    ("popescu", "popescule"),  # vocative
    ("popescu", "popestii"),  # the family
    ("popescu", "popestilor"),
    ("radu", "radului"),
    ("ion", "ionul"),
    ("ion", "ionului"),
    ("maria", "mariei"),
    ("ioana", "ioanei"),
    ("ana", "anei"),
    ("popa", "popei"),
    ("brasov", "brasovului"),
    ("bucuresti", "bucurestiului"),
    ("iasi", "iasului"),
    ("mihai", "mihaiului"),
    ("constanta", "constantei"),
    ("timisoara", "timisoarei"),
    ("cluj-napoca", "cluj-napocii"),
    ("ana-maria", "ana-mariei"),
]


@pytest.mark.parametrize(("base", "form"), FORMS)
def test_a_form_is_made_from_its_base_and_found_back(base, form):
    assert form in inflections(base)
    assert base in bases(form)
    assert same_word(base, form) and same_word(form, base)


@pytest.mark.parametrize(("base", "form"), FORMS)
def test_two_forms_of_the_same_base_are_the_same_word(base, form):
    for other in inflections(base):
        assert same_word(form, other)


def test_the_written_form_does_not_matter():
    assert same_word("Popeștii", "POPESCU")  # diacritics and capitals
    assert same_word("Brasovului", "Brașov")
    assert same_word("Bucureştiului", "București")  # the old cedilla letter


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("pop", "popa"),  # two surnames
        ("radu", "rad"),
        ("ion", "ioan"),
        ("popescu", "popa"),
        ("maria", "mari"),
        ("vlad", "vlada"),
        ("ionescu", "popescu"),
    ],
)
def test_two_names_that_can_belong_to_two_people_are_not_joined(a, b):
    assert not same_word(a, b) and not same_word(b, a)


def test_a_very_short_word_gets_no_forms():
    assert inflections("ei") == frozenset() and inflections("o") == frozenset()


def test_the_order_of_the_words_of_a_person_is_free():
    assert same_lexeme(["zorgblescului", "ion"], ["ion", "zorgblescu"], ordered=False)
    assert not same_lexeme(["zorgblescului", "ion"], ["ion", "zorgblescu"], ordered=True)
    assert not same_lexeme(["ion", "zorgblescu"], ["zorgblescu"], ordered=False)  # not the same number of words


def test_derives_from_needs_a_real_inflection():
    assert derives_from(["ion", "popescului"], ["ion", "popescu"])
    assert not derives_from(["ion", "popescu"], ["ion", "popescu"])  # the same form
    assert not derives_from(["ion", "popescu"], ["ion", "popescului"])  # the other way round


# --- the vault: one id for all forms -----------------------------------------------


def test_a_form_of_a_known_name_gets_the_same_id(vault):
    base = vault.resolve("PERSON", "Ion Popescu")
    assert vault.resolve("PERSON", "Ion Popescului").placeholder == base.placeholder
    assert vault.resolve("PERSON", "POPESTII ION").placeholder == base.placeholder


def test_it_does_not_matter_which_form_comes_first(vault):
    first = vault.resolve("LOCATION", "Brașovului")
    assert vault.resolve("LOCATION", "Brașov").placeholder == first.placeholder
    assert vault.resolve("LOCATION", "Brașovul").placeholder == first.placeholder


def test_two_forms_of_a_name_that_we_never_saw_in_its_base_form_get_one_id(vault):
    first = vault.resolve("PERSON", "Mariei Quuxovici")
    assert vault.resolve("PERSON", "Maria Quuxovici").placeholder == first.placeholder


def test_the_base_form_is_what_the_restore_writes(vault):
    # The inflected form is more common, but the restored text must have the base form.
    vault.resolve("PERSON", "Popescu", count=1)
    entity = vault.resolve("PERSON", "Popescului", count=5)
    assert entity.canonical == "Popescu"


def test_names_that_are_not_forms_of_each_other_stay_apart(vault):
    assert vault.resolve("PERSON", "Ion Pop").placeholder != vault.resolve("PERSON", "Ion Popa").placeholder
    assert vault.resolve("LOCATION", "Cluj").placeholder != vault.resolve("LOCATION", "Cluj-Napoca").placeholder


def test_a_company_name_is_not_joined_by_form(vault):
    # The legal form is a part of the identity of a company, and a company name does not change.
    assert vault.resolve("ORGANIZATION", "Alfa SRL").placeholder != vault.resolve("ORGANIZATION", "Alfei SRL").placeholder


def test_a_seed_is_never_joined_by_form(vault):
    vault.resolve("PERSON", "Popescu")
    assert vault.resolve("PERSON", "Popescului", seed=True).placeholder == "[PERSON_002]"


# --- the engine: the sweep ----------------------------------------------------------


class WordStub:
    """Finds whole words only, as a real NER span does."""

    def __init__(self, known: dict[str, str]):
        self.known = known

    def language_of(self, text, language=None):
        return language or "ro"

    def detect(self, text, language, settings=None, context=None):
        return [
            Span(m.start(), m.end(), kind, 0.9, "presidio")
            for needle, kind in self.known.items()
            for m in re.finditer(rf"(?<!\w){re.escape(needle)}(?!\w)", text)
        ]


def hide(vault, known, text):
    engine = Engine(vault, Settings(), WordStub(known))
    result = engine.anonymize("doc.txt", text.encode())
    return engine, result, result.data.decode()


# (the name that the model finds, its type, a text with other forms that the model does not find, the forms that must go)
EDGE_CASES = [
    ("Zorgblatt", "PERSON", "Contractul lui Zorgblatt, al Zorgblattului, cu Zorgblattul.", ["Zorgblattului", "Zorgblattul"]),
    ("Ion Zorgblescu", "PERSON", "Dreptul lui Ion Zorgblescului. Domnule Ion Zorgblescule!", ["Zorgblescului", "Zorgblescule"]),
    ("Zorgblescu", "PERSON", "Familia Zorgblescu, adică Zorgbleștii. Zorgbleștilor li se cuvine.", ["Zorgbleștii", "Zorgbleștilor"]),
    ("Zorgblescu", "PERSON", "ZORGBLEȘTII și Zorgbleştilor (cu cedilă).", ["ZORGBLEȘTII", "Zorgbleştilor"]),
    ("Maria Quuxovici", "PERSON", "Cererea Mariei Quuxovici.", ["Mariei"]),
    ("Ioana Blorvescu", "PERSON", "Domiciliul Ioanei Blorvescu.", ["Ioanei"]),
    ("Ion Zorgblescu", "PERSON", "ZORGBLESCULUI ION și Ion zorgblescului.", ["ZORGBLESCULUI", "zorgblescului"]),
    ("Ana-Maria Zorgbla", "PERSON", "Cererea Ana-Mariei Zorgbla.", ["Ana-Mariei"]),
    ("Brașov", "LOCATION", "Instanța Brașovului.", ["Brașovului"]),
    ("Zorgburești", "LOCATION", "Primăria Zorgbureștiului.", ["Zorgbureștiului"]),
    ("Zorgbura", "LOCATION", "Primăria Zorgburei.", ["Zorgburei"]),
    ("Cluj-Napoca", "LOCATION", "Tribunalul Cluj-Napocii.", ["Napocii"]),
]


@pytest.mark.parametrize(("name", "kind", "text", "gone"), EDGE_CASES)
def test_the_sweep_hides_other_forms_of_a_known_name(vault, name, kind, text, gone):
    _, result, out = hide(vault, {name: kind}, f"{name}. {text}")
    assert not [form for form in gone if form.lower() in out.lower()], out
    assert result.leaks == []


# (the name, the same name in another form as a model returns it, the type)
SAME_ENTITY = [
    ("Zorgblatt", "Zorgblattului", "PERSON"),
    ("Ion Zorgblescu", "Ion Zorgblescului", "PERSON"),
    ("Ion Zorgblescu", "ZORGBLESCULUI ION", "PERSON"),
    ("Zorgblescu", "Zorgbleștii", "PERSON"),
    ("Maria Quuxovici", "Mariei Quuxovici", "PERSON"),
    ("Ioana Blorvescu", "Ioanei Blorvescu", "PERSON"),
    ("Ana-Maria Zorgbla", "Ana-Mariei Zorgbla", "PERSON"),
    ("Brașov", "Brașovului", "LOCATION"),
    ("Zorgburești", "Zorgbureștiului", "LOCATION"),
    ("Zorgbura", "Zorgburei", "LOCATION"),
    ("Cluj-Napoca", "Cluj-Napocii", "LOCATION"),
]


@pytest.mark.parametrize(("name", "other", "kind"), SAME_ENTITY)
def test_a_form_that_the_model_finds_has_the_id_of_the_base_name(vault, name, other, kind):
    # The model finds the name in its other form too. It is one entity, not two.
    hide(vault, {name: kind, other: kind}, f"{name}. Apoi {other} a venit.")
    assert len(vault.entities()) == 1, [(e.placeholder, e.forms) for e in vault.entities()]


def test_a_name_that_only_looks_like_a_form_is_left_alone(vault):
    _, _, out = hide(vault, {"Ion Pop": "PERSON"}, "Ion Pop și Ion Popa. Popoarele.")
    assert "Ion Popa" in out and "Popoarele" in out


def test_the_leak_check_sees_a_form_of_a_known_name(vault):
    engine, _, _ = hide(vault, {"Ion Popescu": "PERSON"}, "Ion Popescu.")
    assert engine.find_leaks("doc.txt", "Contractul lui Ion Popescului.".encode()) == ["[PERSON_001]"]


def test_the_restore_writes_the_base_form(vault):
    # Known limit: the placeholder does not say which form the text had.
    engine, result, out = hide(vault, {"Ion Popescu": "PERSON"}, "Ion Popescu și dreptul lui Ion Popescului.")
    assert out == "[PERSON_001] și dreptul lui [PERSON_001]."
    assert engine.restore("doc.txt", result.data).data.decode() == "Ion Popescu și dreptul lui Ion Popescu."


# --- spelling variants of a known name (LDA-29) -----------------------------------------

VARIANTS = [
    ("Ana-Maria Zorgbla", "PERSON", "Ana Maria Zorgbla și ANA MARIA ZORGBLA.", ["Ana Maria Zorgbla", "ANA MARIA ZORGBLA"]),
    ("Ana Maria Zorgbla", "PERSON", "Ana-Maria Zorgbla.", ["Ana-Maria Zorgbla"]),
    ("Zorgbla Quux", "PERSON", "Zorgbla-Quux a venit.", ["Zorgbla-Quux"]),
    ("Alfa Construct SRL", "ORGANIZATION", "SC ALFA CONSTRUCT S.R.L. și Alfa Construct S.R.L.-ul.", ["ALFA CONSTRUCT S.R.L.", "S.R.L.-ul"]),
    ("Alfa Construct S.R.L.", "ORGANIZATION", "Alfa Construct SRL a semnat.", ["Alfa Construct SRL"]),
    ("S.C. Alfa Construct S.R.L.", "ORGANIZATION", "Alfa Construct SRL și ALFA CONSTRUCT S.R.L.", ["Alfa Construct SRL", "ALFA CONSTRUCT S.R.L."]),
]


@pytest.mark.parametrize(("name", "kind", "text", "gone"), VARIANTS)
def test_the_sweep_hides_other_spellings_of_a_known_name(vault, name, kind, text, gone):
    _, result, out = hide(vault, {name: kind}, f"{name}. {text}")
    assert not [form for form in gone if form.lower() in out.lower()], out
    assert result.leaks == []


def test_a_company_name_with_an_ending_after_the_legal_form_is_hidden_and_restores_exactly(vault):
    # This already works: the hyphen ends the word, so only the ending stays visible.
    engine, result, out = hide(vault, {"Alfa Construct SRL": "ORGANIZATION"}, "Alfa Construct SRL. Cererea Alfa Construct SRL-ului.")
    assert out == "[ORG_001]. Cererea [ORG_001]-ului."
    assert engine.restore("doc.txt", result.data).data.decode() == "Alfa Construct SRL. Cererea Alfa Construct SRL-ului."


def test_another_legal_form_is_another_company(vault):
    # "SRL" and "SA" are two companies, also with dots. The sweep must not join them.
    _, _, out = hide(vault, {"Alfa Construct SRL": "ORGANIZATION"}, "Alfa Construct SRL. Alfa Construct S.A. și Alfa Construct SNC.")
    assert out == "[ORG_001]. Alfa Construct S.A. și Alfa Construct SNC."


def test_a_double_name_with_a_hyphen_or_a_space_is_one_entity(vault):
    first = vault.resolve("PERSON", "Ana-Maria Zorgbla")
    assert vault.resolve("PERSON", "Ana Maria Zorgbla").placeholder == first.placeholder
    assert vault.resolve("PERSON", "ZORGBLA ANA-MARIA").placeholder == first.placeholder
    assert vault.resolve("PERSON", "Ana-Mariei Zorgbla").placeholder == first.placeholder  # and a Romanian form


def test_a_legal_form_with_dots_is_the_same_company_as_without_dots(vault):
    first = vault.resolve("ORGANIZATION", "Alfa Construct SRL")
    assert vault.resolve("ORGANIZATION", "S.C. ALFA CONSTRUCT S.R.L.").placeholder == first.placeholder
