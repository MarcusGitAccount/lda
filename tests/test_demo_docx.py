"""Tests for the Word demo: demo/docx_layout.py, demo/docx_edit.py and demo/run_docx.py.

The fast tests need no model. The tests with the mark `models` hide the data in the demo
files with the real models. Run only the fast tests with: pytest -m "not models"
"""

import difflib
import io
import json
import re
import zipfile
from pathlib import Path

import pytest
from docx import Document
from docx.oxml.ns import qn

from demo import kit, layout, run_docx
from demo.docx_edit import AUTHOR, Redline
from legal_anonymizer.config import load_settings
from legal_anonymizer.documents import open_document, scan_text
from legal_anonymizer.engine import Engine
from legal_anonymizer.textnorm import collapse, fold
from legal_anonymizer.vault import PLACEHOLDER_RE, Vault

DEMO = Path(__file__).resolve().parent.parent / "data" / "demo"
GOLD = json.loads((DEMO / "gold.json").read_text(encoding="utf-8"))

# Words of names that can change in the restored text: the short form of a name comes back as the full name.
NAME_WORDS = {
    "s.c", "s.r.l", "s.a", "carpatica", "logistic", "solutions", "mureșul", "agro", "trans",
    "northgate", "freight", "forwarding", "ltd", "societatea", "civilă", "de", "avocați", "rusu", "și", "asociații",
}  # fmt: skip


def plain(text: str) -> str:
    return collapse(fold(text))


def units(name: str, data: bytes) -> list[str]:
    return open_document(name, data).units()


@pytest.fixture(scope="module")
def originals(tmp_path_factory) -> dict[str, bytes]:
    return run_docx.build_originals(tmp_path_factory.mktemp("docx") / "original", 5)


def contract(originals) -> tuple[str, bytes]:
    return next((n, d) for n, d in originals.items() if n.startswith("01_"))


# --- the Word files (no model) -----------------------------------------------------------


def test_there_are_five_word_files_and_the_pdf_layout_is_the_default_again(originals):
    assert [n.split("_")[0] for n in originals] == ["01", "02", "03", "04", "05"]
    assert all(n.endswith(".docx") for n in originals)
    assert kit._backend is layout


def test_the_files_have_word_structure_and_not_only_text(originals):
    for name, data in originals.items():
        doc = Document(io.BytesIO(data))
        used = {p.style.name for p in doc.paragraphs}
        assert {"Title", "Normal"} <= used, name
        assert doc.sections[0].different_first_page_header_footer, name  # no running header on page 1
        assert doc.sections[0].header.paragraphs[0].text, name
        footer = zipfile.ZipFile(io.BytesIO(data)).read("word/footer1.xml").decode("utf-8")
        assert "PAGE" in footer and "NUMPAGES" in footer, name  # page numbers are fields, not typed
    doc = Document(io.BytesIO(contract(originals)[1]))
    assert {"Heading 1", "Clause", "Sub-clause", "Letterhead Name"} <= {p.style.name for p in doc.paragraphs}
    assert len(doc.tables) >= 3  # the two annexes and the signatures


def test_the_language_of_each_file_is_set(originals):
    for name, data in originals.items():
        styles = zipfile.ZipFile(io.BytesIO(data)).read("word/styles.xml").decode("utf-8")
        assert ('w:val="en-GB"' if ".en." in name else 'w:val="ro-RO"') in styles, name


def test_the_tool_reads_the_text_of_the_files_including_header_and_footer(originals):
    name, data = contract(originals)
    text = "\n".join(units(name, data))
    assert "CONTRACT DE PRESTĂRI SERVICII DE TRANSPORT RUTIER" in text
    assert "9.2.\tPentru întârzierea livrării" in text  # the number, a tab, the text
    assert "Contract nr. 128/22.03.2024 –" in text  # header
    assert "CUI RO" in text and "Pagina" in text  # footer
    assert "Tarif / cursă" in text  # a table


def test_the_properties_of_the_original_have_the_name_of_the_author(originals):
    _, data = contract(originals)
    core = zipfile.ZipFile(io.BytesIO(data)).read("docProps/core.xml").decode("utf-8")
    assert "Gabriel-Tudor Lazăr" in core  # the tool must remove it (see the test with the models)


# --- the simulated AI tool (no model) -------------------------------------------------------


def test_a_replacement_is_a_tracked_change_by_the_ai_assistant(originals):
    redline = Redline(contract(originals)[1])
    redline.replace("0,5%", "0,7%", in_paragraph="Pentru întârzierea livrării")
    redline.replace("20%", "25%", in_paragraph="Pentru întârzierea livrării")
    body = Document(io.BytesIO(redline.save())).element.body
    assert [t.text for t in body.iter(qn("w:delText"))] == ["0,5%", "20%"]
    assert [t.text for ins in body.iter(qn("w:ins")) for t in ins.iter(qn("w:t"))] == ["0,7%", "25%"]
    assert {e.get(qn("w:author")) for e in (*body.iter(qn("w:ins")), *body.iter(qn("w:del")))} == {AUTHOR}
    assert len({e.get(qn("w:id")) for e in (*body.iter(qn("w:ins")), *body.iter(qn("w:del")))}) == 4  # each id is new


def test_the_text_before_and_after_a_replacement_is_kept(originals):
    name, data = contract(originals)
    redline = Redline(data)
    redline.replace("0,5%", "0,7%", in_paragraph="Pentru întârzierea livrării")
    paragraph = " ".join(next(u for u in units(name, redline.save()) if u.startswith("9.2.")).split())
    assert "penalități de 0,5% 0,7% pe zi de întârziere" in paragraph  # the tool reads the old and the new text


def test_a_new_paragraph_has_the_style_of_the_paragraph_before_it(originals):
    redline = Redline(contract(originals)[1])
    redline.insert_paragraph_after("Prezentul contract s-a încheiat în două exemplare", "Textul nou.", label="15.4.")
    paragraphs = list(Document(io.BytesIO(redline.save())).element.body.iter(qn("w:p")))  # python-docx skips tracked text

    def text(p) -> str:
        return "".join(t.text or "" for t in p.iter(qn("w:t")))

    def style(p) -> str:
        return p.find(f"{qn('w:pPr')}/{qn('w:pStyle')}").get(qn("w:val"))

    new = next(i for i, p in enumerate(paragraphs) if "Textul nou." in text(p))
    assert style(paragraphs[new]) == style(paragraphs[new - 1]) == "Clause"
    assert "Prezentul contract s-a încheiat" in text(paragraphs[new - 1])


def test_a_text_that_is_not_in_the_file_is_an_error(originals):
    with pytest.raises(ValueError, match="No paragraph"):
        Redline(contract(originals)[1]).replace("nu există", "x")


def test_ids_in_a_tracked_insertion_are_restored_and_the_change_stays_tracked(originals, vault):
    name, data = contract(originals)
    client = vault.resolve("ORGANIZATION", "Mureșul Agro Trans S.R.L.", count=0)
    redline = Redline(data)
    redline.insert_paragraph_after("Prezentul contract s-a încheiat în două exemplare", f"{client.placeholder} plătește.", label="15.4.")
    result = Engine(vault).restore(name.replace(".docx", ".anon.docx"), redline.save())
    assert result.unknown == []
    assert "15.4.\tMureșul Agro Trans S.R.L. plătește." in units(name, result.data)
    inserted = Document(io.BytesIO(result.data)).element.body.findall(f".//{qn('w:ins')}")
    assert len(inserted) == 2  # the mark of the paragraph and the text


# --- with the models --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def case(detector, originals, tmp_path_factory):
    settings = load_settings(DEMO / "matter.yaml")
    with Vault(tmp_path_factory.mktemp("vault") / "case.db") as vault:
        engine = Engine(vault, settings, detector)
        engine.load_seeds()
        results = dict(zip(originals, engine.anonymize_many(list(originals.items()))))
        yield engine, vault, results


def hidden_text(results) -> dict[str, str]:
    """The text of each output file, with the courts that the policy keeps visible taken out."""
    out = {}
    for name, result in results.items():
        text = plain(scan_text(name, result.data))
        for phrase in GOLD["visible_ok"]:
            text = text.replace(plain(phrase), " ")
        out[name] = text
    return out


@pytest.mark.models
def test_nothing_from_the_must_hide_list_is_left_in_any_part_of_the_files(case):
    _, _, results = case
    texts = hidden_text(results)
    left = {s: [n[:2] for n, t in texts.items() if plain(s) in t] for s in GOLD["must_hide"]}
    assert {s: where for s, where in left.items() if where} == {}


@pytest.mark.models
def test_the_words_that_the_reader_needs_stay_and_the_tool_has_no_warning(case):
    _, _, results = case
    everything = " ".join(hidden_text(results).values())
    assert [k for k in GOLD["must_keep"] if plain(k) not in everything] == []
    assert {n: r.leaks for n, r in results.items() if r.leaks} == {}


@pytest.mark.models
def test_the_client_and_the_administrator_have_one_id_in_every_file(case, originals):
    _, _, results = case
    for placeholder in ("[ORG_001]", "[PERSON_001]"):
        found = [n for n, r in results.items() if placeholder in "\n".join(units(n, r.data))]
        assert found == list(originals), placeholder


@pytest.mark.models
def test_the_layout_stays_and_the_name_of_the_author_goes(case, originals):
    _, _, results = case
    for name, result in results.items():
        before, after = Document(io.BytesIO(originals[name])), Document(io.BytesIO(result.data))
        assert [p.style.name for p in before.paragraphs] == [p.style.name for p in after.paragraphs], name
        assert [len(t.rows) for t in before.tables] == [len(t.rows) for t in after.tables], name
        parts = zipfile.ZipFile(io.BytesIO(result.data))
        for part in (n for n in parts.namelist() if re.fullmatch(r"docProps/core\.xml|word/(header|footer)\d*\.xml", n)):
            xml = parts.read(part).decode("utf-8")
            assert not [w for w in ("Lazăr", "Carpatica", "Northgate", "Mureșul", "Rusu") if w in xml], (name, part)


@pytest.mark.models
def test_restore_gives_back_the_text_and_leaves_no_id(case, originals):
    engine, _, results = case
    for name, result in results.items():
        restored = engine.restore(name.replace(".docx", ".anon.docx"), result.data)
        assert restored.unknown == []
        text = "\n".join(units(name, restored.data))
        assert not PLACEHOLDER_RE.search(text)
        a, b = "\n".join(units(name, originals[name])).split(), text.split()
        changed = [
            (" ".join(a[i1:i2]), " ".join(b[j1:j2]))
            for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
            if tag != "equal"
        ]
        words = {w.lower().strip("(),.;–").removesuffix("'s") for x, y in changed for w in f"{x} {y}".split()} - {""}
        assert words <= NAME_WORDS, (name, words - NAME_WORDS)


@pytest.mark.models
def test_the_ai_changes_come_back_with_the_real_names_as_tracked_changes(case):
    engine, vault, results = case
    ids = {e.canonical: e.placeholder for e in vault.entities()}
    name = next(n for n in results if n.startswith("01_"))
    hidden_name = name.replace(".docx", ".anon.docx")
    edited = run_docx.ai_edit(name, results[name].data, ids)
    assert edited is not None and run_docx.ai_edit("03_x.docx", b"", ids) is None  # the claim has no change
    restored = engine.restore(hidden_name, edited)
    assert restored.unknown == []
    text = "\n".join(units(name, restored.data))
    assert re.search(r"15\.4\.\tCarpatica Logistic Solutions S\.A\. transmite Mureșul Agro Trans S\.R\.L\.", text)
    assert "0,5% 0,7%" in text and "20% 25%" in text
    body = Document(io.BytesIO(restored.data)).element.body
    assert {e.get(qn("w:author")) for e in body.iter(qn("w:ins"))} == {AUTHOR}


@pytest.mark.models
def test_the_demo_script_makes_the_three_folders_for_each_case(detector, monkeypatch, tmp_path):
    monkeypatch.setattr(run_docx, "OUT", tmp_path / "demo-docx")
    settings = load_settings(DEMO / "matter.yaml")
    for case_name, count in (("single-file", 1), ("multi-file", 5)):
        summary = run_docx.run_case(case_name, count, detector, settings)
        assert "WARNING" not in summary
        for folder in ("1-original", "2-anonymized", "3-restored"):
            assert len(list((tmp_path / "demo-docx" / case_name / folder).glob("*.docx"))) == count
    assert len(list((tmp_path / "demo-docx" / "_work" / "multi-file" / "ai-edited").glob("*.docx"))) == 3
