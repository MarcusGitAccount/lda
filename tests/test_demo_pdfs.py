"""End-to-end tests with the real NER models on the demo case: five PDFs (four Romanian, one English).

The files are in data/demo/. Make them again with `python -m demo.build`.
Run only the fast tests with: pytest -m "not models"
"""

import difflib
import json
import re
from pathlib import Path

import pytest

from legal_anonymizer.config import load_settings
from legal_anonymizer.engine import Engine
from legal_anonymizer.pdftext import pdf_text
from legal_anonymizer.textnorm import collapse, fold
from legal_anonymizer.vault import PLACEHOLDER_RE, Vault

pytestmark = pytest.mark.models

DEMO = Path(__file__).resolve().parent.parent / "data" / "demo"
GOLD = json.loads((DEMO / "gold.json").read_text(encoding="utf-8"))
FILES = sorted(p.name for p in DEMO.glob("*.pdf"))


# Words of the company names. They can change in the restored text (the short name comes back as the full name).
NAME_WORDS = {
    "s.c", "s.r.l", "s.a", "carpatica", "logistic", "solutions", "mureșul", "agro", "trans",
    "northgate", "freight", "forwarding", "ltd",
}  # fmt: skip


def plain(text: str) -> str:
    return collapse(fold(text))


@pytest.fixture(scope="module")
def case(detector, tmp_path_factory):
    settings = load_settings(DEMO / "matter.yaml")
    with Vault(tmp_path_factory.mktemp("vault") / "case.db") as vault:
        engine = Engine(vault, settings, detector)
        engine.load_seeds()
        files = [(name, (DEMO / name).read_bytes()) for name in FILES]
        results = dict(zip(FILES, engine.anonymize_many(files)))
        yield engine, vault, results


def hidden_text(results) -> dict[str, str]:
    """The output of each file, with the courts that the policy keeps visible taken out."""
    out = {}
    for name, result in results.items():
        text = plain(result.data.decode("utf-8"))
        for phrase in GOLD["visible_ok"]:
            text = text.replace(plain(phrase), " ")
        out[name] = text
    return out


def test_there_are_five_documents_and_they_are_long():
    assert len(FILES) == 5
    assert all(len(pdf_text((DEMO / n).read_bytes()).split()) > 600 for n in FILES)


def test_nothing_from_the_must_hide_list_is_left(case):
    _, _, results = case
    texts = hidden_text(results)
    left = {s: [n[:2] for n, t in texts.items() if plain(s) in t] for s in GOLD["must_hide"]}
    assert {s: where for s, where in left.items() if where} == {}


def test_words_that_the_reader_needs_stay_visible(case):
    _, _, results = case
    everything = " ".join(hidden_text(results).values())
    assert [k for k in GOLD["must_keep"] if plain(k) not in everything] == []


def test_no_warning_about_known_text_in_the_output(case):
    _, _, results = case
    assert {n: r.leaks for n, r in results.items() if r.leaks} == {}


def test_the_client_and_the_other_side_have_one_id_in_every_document(case):
    _, vault, results = case
    for placeholder, expected_in in [("[ORG_001]", FILES), ("[PERSON_001]", FILES)]:
        found = [n for n, r in results.items() if placeholder in r.data.decode("utf-8")]
        assert found == expected_in, placeholder
    client = vault.by_placeholder("[ORG_001]")
    assert client.canonical == "Mureșul Agro Trans S.R.L."  # the name of the config file
    assert {"MUREȘUL AGRO TRANS S.R.L.", "Mureșul Agro Trans"} <= set(client.forms)


def test_junk_is_not_hidden(case):
    """The model marks common words. The clean-up must remove them before they spread through the sweep."""
    _, vault, _ = case
    junk = {"personal", "persoana", "persoane", "destinatarul", "poștal", "nr", "jud", "părților", "Șoferul", "Bank", "CMR"}
    forms = {f.lower() for e in vault.entities() for f in e.forms}
    assert forms & {j.lower() for j in junk} == set()
    # No date and no table row is a phone number.
    assert not [e for e in vault.entities() if e.type == "PHONE_NUMBER" and re.search(r"20\d\d", e.canonical)]


def test_restore_gives_the_text_back(case):
    engine, _, results = case
    for name, result in results.items():
        original = pdf_text((DEMO / name).read_bytes())
        restored = engine.restore(name.replace(".pdf", ".anon.txt"), result.data)
        assert restored.unknown == []
        assert not PLACEHOLDER_RE.search(restored.data.decode("utf-8"))
        # The restored text can differ in the form of a name: one written form comes back for each entity.
        a, b = original.split(), restored.data.decode("utf-8").split()
        changed = [
            (" ".join(a[i1:i2]), " ".join(b[j1:j2]))
            for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
            if tag != "equal"
        ]
        words = {w.lower().strip("(),.;").removesuffix("'s") for x, y in changed for w in f"{x} {y}".split()}
        assert words <= NAME_WORDS, words - NAME_WORDS


def test_an_ai_revision_with_ids_is_restored(case):
    engine, vault, results = case
    client, other = vault.by_placeholder("[ORG_001]"), vault.by_placeholder("[ORG_002]")
    revised = (
        f"Art. 16. Penalități. {client.placeholder} poate cere de la {other.placeholder} penalități de 0,7% pe zi.\n"
        f"Notice to \\{client.placeholder[:-1]}\\]: see [ ORG_2 ]."
    )
    restored = engine.restore("revizie.txt", revised.encode("utf-8"))
    text = restored.data.decode("utf-8")
    assert "Mureșul Agro Trans S.R.L. poate cere de la Carpatica Logistic Solutions S.A. penalități" in text
    assert "see Carpatica Logistic Solutions S.A." in text
    assert restored.unknown == []
