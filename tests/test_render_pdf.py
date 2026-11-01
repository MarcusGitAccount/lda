"""The PDF copies of the demo. No model is needed."""

import pytest

pytest.importorskip("reportlab")

from demo.render_pdf import language_of, mark, render  # noqa: E402
from legal_anonymizer.pdftext import pdf_text  # noqa: E402

TEXT = (
    "S.C. [ORG_002]\n\nCONTRACT DE TEST ȘI ALTE LUCRURI\n\nARTICOLUL 1 – OBIECTUL\n\n"
    "1.1. [ORG_002] se obligă față de [ORG_001] să execute lucrarea. Costul este de 1.000,00 lei.\n\n"
    "Ruta\tTarif\tTermen\nBrașov\t3.150,00\tAceeași zi"
)


def test_the_pdf_copy_has_the_same_words_and_the_ids(tmp_path):
    render(TEXT, tmp_path / "a.pdf")
    text = pdf_text((tmp_path / "a.pdf").read_bytes())
    for part in ["[ORG_002]", "[ORG_001]", "CONTRACT DE TEST ȘI ALTE LUCRURI", "ARTICOLUL 1 – OBIECTUL", "1.000,00 lei", "Brașov\t3.150,00\tAceeași zi"]:
        assert part in text, part
    assert text.startswith("COPIE ANONIMIZATĂ")  # the banner: this copy has hidden data


def test_a_restored_copy_has_no_banner_and_an_english_copy_has_an_english_banner(tmp_path):
    render(TEXT, tmp_path / "b.pdf", restored=True)
    assert "ANONIMIZATĂ" not in pdf_text((tmp_path / "b.pdf").read_bytes())
    render("The text has [ORG_001].", tmp_path / "c.pdf", language="en")
    assert pdf_text((tmp_path / "c.pdf").read_bytes()).startswith("ANONYMIZED COPY")
    assert language_of("05_settlement.en.anon.txt") == "en" and language_of("01_contract.ro.anon.txt") == "ro"


def test_special_characters_do_not_break_the_layout(tmp_path):
    render("Alfa & Beta <b> sunt [ORG_001].", tmp_path / "d.pdf")
    assert "Alfa & Beta <b> sunt [ORG_001]." in pdf_text((tmp_path / "d.pdf").read_bytes())
    assert "&amp;" in mark("a & b")
