import os
import stat

import pytest

from legal_anonymizer.engine import Engine
from legal_anonymizer.vault import PLACEHOLDER_RE, Vault


def test_same_entity_gets_same_id_and_new_entity_gets_next_id(vault):
    a = vault.resolve("PERSON", "Ion Popescu")
    b = vault.resolve("PERSON", "POPESCU ION")
    c = vault.resolve("PERSON", "Maria Ionescu")
    assert a.id == b.id and a.placeholder == "[PERSON_001]"
    assert c.placeholder == "[PERSON_002]"
    assert vault.resolve("ORGANIZATION", "Alfa SRL").placeholder == "[ORG_001]"


def test_canonical_form_is_the_seed_then_the_most_common(vault):
    vault.resolve("PERSON", "POPESCU ION", count=1)
    vault.resolve("PERSON", "Ion Popescu", count=5)
    assert vault.resolve("PERSON", "popescu ion", count=0).canonical == "Ion Popescu"
    seeded = vault.resolve("PERSON", "Ionescu Maria", seed=True, count=0)
    vault.resolve("PERSON", "IONESCU MARIA", count=9)
    assert vault.entity(seeded.id).canonical == "Ionescu Maria"


def test_alias_and_conflict(vault):
    ion = vault.resolve("PERSON", "Ion Popescu", seed=True)
    vault.add_alias(ion.id, "dl. Popescu")
    # A title is not part of the key. So the surname alone is now the same entity.
    assert vault.resolve("PERSON", "Popescu").id == ion.id
    maria = vault.resolve("PERSON", "Maria Ionescu")
    with pytest.raises(ValueError, match="already"):
        vault.add_alias(maria.id, "Ion Popescu")


def test_surname_alone_is_a_new_entity_if_nobody_said_it_is_an_alias(vault):
    ion = vault.resolve("PERSON", "Ion Popescu")
    assert vault.resolve("PERSON", "Popescu").id != ion.id


def test_merge_keeps_old_ids_working_and_never_reuses_numbers(vault):
    ion = vault.resolve("PERSON", "Ion Popescu")
    short = vault.resolve("PERSON", "Popescu")
    assert short.placeholder == "[PERSON_002]"
    merged = vault.merge("[PERSON_002]", "[PERSON_001]")
    assert merged.id == ion.id and "Popescu" in merged.forms
    assert vault.lookup("PERSON", 2).placeholder == "[PERSON_001]"  # old id still works
    assert vault.resolve("PERSON", "Popescu").placeholder == "[PERSON_001]"
    assert vault.resolve("PERSON", "Maria Ionescu").placeholder == "[PERSON_003]"  # no reuse
    assert [e.placeholder for e in vault.entities()] == ["[PERSON_001]", "[PERSON_003]"]


def test_merge_refuses_two_types(vault):
    person = vault.resolve("PERSON", "Ion Popescu")
    org = vault.resolve("ORGANIZATION", "Popescu SRL")
    with pytest.raises(ValueError, match="Cannot merge"):
        vault.merge(person.placeholder, org.placeholder)


def test_vault_file_is_private(tmp_path):
    path = tmp_path / "private.db"
    Vault(path).close()
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


@pytest.mark.parametrize(
    "text",
    ["[PERSON_001]", "[PERSON_1]", "[person_001]".upper(), "[ PERSON_001 ]", "[PERSON-001]", "[PERSON 001]", r"\[PERSON\_001\]"],
)
def test_placeholder_regex_accepts_small_changes_by_an_ai_tool(text):
    match = PLACEHOLDER_RE.fullmatch(text)
    assert match and match.group(1) == "PERSON" and int(match.group(2)) == 1


def test_placeholder_regex_does_not_match_normal_text():
    for text in ["[●]", "[Annex 1]", "[PERSON]", "[NOTE_1]", "PERSON_001"]:
        assert not PLACEHOLDER_RE.search(text), text


def test_restore_text_with_tolerant_ids_and_unknown_ids(vault):
    ion = vault.resolve("PERSON", "Ion Popescu")
    org = vault.resolve("ORGANIZATION", "Alfa Construct SRL")
    engine = Engine(vault)  # no model is needed to restore
    text = "[PERSON_001] și [ORG_1] ({}) cu [PERSON_042] și [●].".format(r"\[PERSON\_001\]")
    result = engine.restore("a.txt", text.encode())
    assert result.data.decode() == "Ion Popescu și Alfa Construct SRL (Ion Popescu) cu [PERSON_042] și [●]."
    assert result.unknown == ["[PERSON_042]"]
    assert result.restored[ion.placeholder] == 2 and result.restored[org.placeholder] == 1


def test_restore_is_one_pass_and_does_not_restore_inside_restored_text(vault):
    vault.resolve("PERSON", "[ORG_001]")  # a strange name that looks like an id
    vault.resolve("ORGANIZATION", "Alfa SRL")
    result = Engine(vault).restore("a.txt", b"[PERSON_001]")
    assert result.data == b"[ORG_001]"
