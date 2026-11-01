import io
import zipfile

import pytest
from lxml import etree

from legal_anonymizer.documents import (
    UnsupportedFormat,
    open_document,
    scan_text,
)
from samples import build_docx

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def replace_all(data: bytes, mapping: dict[str, str], scrub: bool = False) -> bytes:
    """Replace each text in `mapping` in all units of a .docx."""
    doc = open_document("x.docx", data)
    replacements = []
    for unit in doc.units():
        found = []
        for old, new in mapping.items():
            start = unit.find(old)
            while start != -1:
                found.append((start, start + len(old), new))
                start = unit.find(old, start + len(old))
        replacements.append(found)
    return doc.rewrite(replacements, scrub=scrub)


def part(data: bytes, name: str) -> etree._Element:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return etree.fromstring(z.read(name))


def test_units_cover_body_header_footnote_comment_table_textbox_and_tracked_text():
    units = open_document("x.docx", build_docx(comment="Nota")).units()
    joined = "\n".join(units)
    for text in ["Ion Popescu", "Alfa Construct SRL - confiden", "Vezi dosarul", "Nota", "SC ALFA CONSTRUCT SRL",
                 "Semnat de Maria Ionescu", "Maria Ionescu", "Vasile Georgescu", "ion.popescu@alfaconstruct.ro"]:
        assert text in joined, text


def test_inserted_and_deleted_text_do_not_run_together():
    units = open_document("x.docx", build_docx()).units()
    assert "Prestator: Maria Ionescu Vasile Georgescu" in units


def test_tab_stop_in_paragraph_properties_is_not_text_but_a_tab_in_a_run_is():
    units = open_document("x.docx", build_docx()).units()
    assert "Sediu:\tCluj-Napoca" in units
    assert not any(u.startswith("\t") for u in units)


def test_name_split_in_two_runs_is_replaced_and_format_is_kept():
    out = replace_all(build_docx(), {"Ion Popescu": "[PERSON_001]"})
    root = part(out, "word/document.xml")
    paragraph = [p for p in root.iter(f"{{{W}}}p") if "Beneficiar" in "".join(p.itertext())][0]
    assert "".join(paragraph.itertext()) == "Beneficiar: [PERSON_001], telefon 0722 123 456."
    runs = paragraph.findall(f"{{{W}}}r")
    assert len(runs) == 4  # no run was removed
    assert runs[1].find(f"{{{W}}}rPr/{{{W}}}b") is not None  # the bold run is still bold


def test_replacements_reach_tracked_deleted_text_header_footnote_comment():
    mapping = {"Vasile Georgescu": "[PERSON_009]", "Alfa Construct SRL": "[ORG_001]", "1234/3/2024": "[CASE_NO_001]", "Ion Popescu": "[PERSON_001]"}
    out = replace_all(build_docx(comment="Nota pentru Ion Popescu"), mapping)
    text = scan_text("x.docx", out)
    for secret in mapping:
        assert secret not in text, secret
    assert "[PERSON_009]" in text and "[ORG_001]" in text and "[CASE_NO_001]" in text


def test_scrub_removes_author_and_company_but_without_scrub_they_stay():
    original = build_docx(comment="x")
    plain = replace_all(original, {})
    assert "Andrei Avocat" in scan_text("x.docx", plain) and "Cabinet Avocat Test" in scan_text("x.docx", plain)
    clean = replace_all(original, {}, scrub=True)
    text = scan_text("x.docx", clean)
    assert "Andrei Avocat" not in text and "Cabinet Avocat Test" not in text
    assert part(clean, "word/document.xml").find(f".//{{{W}}}ins").get(f"{{{W}}}author") == "Author"


def test_output_is_a_zip_with_the_same_parts_and_valid_xml():
    original = build_docx(comment="x")
    out = replace_all(original, {"Ion Popescu": "[PERSON_001]"}, scrub=True)
    with zipfile.ZipFile(io.BytesIO(original)) as a, zipfile.ZipFile(io.BytesIO(out)) as b:
        assert a.namelist() == b.namelist()
        assert b.testzip() is None
        for name in b.namelist():
            etree.fromstring(b.read(name))  # must parse
        # Parts that we do not process are the same bytes.
        assert a.read("[Content_Types].xml") == b.read("[Content_Types].xml")


def test_namespace_prefixes_are_kept():
    out = replace_all(build_docx(), {})
    with zipfile.ZipFile(io.BytesIO(out)) as z:
        assert b"<w:document" in z.read("word/document.xml")


def test_scan_text_sees_link_targets_that_are_not_processed():
    data = build_docx(extra_links=(("rId9", "mailto:ion.popescu@alfaconstruct.ro"),))
    assert "ion.popescu@alfaconstruct.ro" in scan_text("x.docx", data)


def test_text_document_round_trip_and_bad_encoding():
    doc = open_document("a.md", "Ion Popescu și ț\n".encode("utf-8"))
    assert doc.units() == ["Ion Popescu și ț\n"]
    assert doc.rewrite([[(0, 11, "[PERSON_001]")]]) == "[PERSON_001] și ț\n".encode()
    with pytest.raises(ValueError, match="UTF-8"):
        open_document("a.txt", "ţară".encode("cp1250"))


def test_bad_inputs_are_refused():
    with pytest.raises(UnsupportedFormat, match="PDF"):
        open_document("a.pdf", b"%PDF")
    with pytest.raises(ValueError, match="not a valid"):
        open_document("a.docx", b"not a zip")
    empty = io.BytesIO()
    with zipfile.ZipFile(empty, "w") as z:
        z.writestr("hello.txt", "x")
    with pytest.raises(ValueError, match="not a Word document"):
        open_document("a.docx", empty.getvalue())


def test_xml_entities_are_not_resolved(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP-SECRET-FILE-CONTENT")
    evil = (
        f'<?xml version="1.0"?><!DOCTYPE d [<!ENTITY x SYSTEM "file://{secret}">]>'
        f'<w:document xmlns:w="{W}"><w:body><w:p><w:r><w:t>&x;</w:t></w:r></w:p></w:body></w:document>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("word/document.xml", evil)
    units = open_document("evil.docx", buffer.getvalue()).units()
    assert "TOP-SECRET-FILE-CONTENT" not in "".join(units)


def test_zip_bomb_is_refused(monkeypatch):
    import legal_anonymizer.documents as documents

    monkeypatch.setattr(documents, "MAX_DOCX_BYTES", 1000)
    with pytest.raises(ValueError, match="too large"):
        open_document("a.docx", build_docx())
