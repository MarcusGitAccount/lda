"""PDF input. These tests need no model."""

import re

import pytest

pytest.importorskip("reportlab")

from legal_anonymizer.cli import output_name  # noqa: E402
from legal_anonymizer.config import Settings  # noqa: E402
from legal_anonymizer.documents import UnsupportedFormat, open_document, scan_text  # noqa: E402
from legal_anonymizer.engine import Engine  # noqa: E402
from legal_anonymizer.pdftext import _join, pdf_text  # noqa: E402
from legal_anonymizer.vault import Vault  # noqa: E402

from pdfmaker import PageBreak, empty_page_pdf, item, make_pdf, paragraph, table  # noqa: E402
from test_engine import StubDetector  # noqa: E402

LONG = (
    "Prestatorul, reprezentat legal prin Ion Popescu, administrator, se obliga sa execute lucrarile de proiectare "
    "pentru imobilul situat in Brasov, in conditiile prevazute de prezentul contract si de anexele sale, "
    "iar Beneficiarul se obliga sa plateasca pretul convenit la termenele stabilite de parti."
)


def test_wrapped_lines_become_one_paragraph_and_names_stay_whole():
    text = pdf_text(make_pdf([paragraph(LONG), paragraph("Al doilea paragraf este scurt.")]))
    assert LONG in text  # no line break inside the paragraph
    assert text.split("\n\n")[-1] == "Al doilea paragraf este scurt."


def test_list_items_are_separate_paragraphs():
    text = pdf_text(
        make_pdf([paragraph("Prestatorul se obliga:"), item("a)", "sa execute lucrarile;"), item("b)", "sa predea lucrarile la termen."), paragraph("Alt text.")])
    )
    blocks = text.split("\n\n")
    assert any(b.startswith("a) sa execute") for b in blocks)
    assert any(b.startswith("b) sa predea") for b in blocks)


def test_table_columns_are_split_by_a_tab():
    text = pdf_text(make_pdf([paragraph("Date de contact."), table([["Nume", "Ion Popescu", "0722 123 456"], ["Firma", "Alfa SRL", "Cluj"]], [3, 6, 5])]))
    rows = [line for line in text.split("\n") if "\t" in line]
    assert any(line.split("\t")[:2] == ["Nume", "Ion Popescu"] for line in rows)


def test_page_numbers_and_repeated_footers_are_removed_but_a_name_in_the_text_stays():
    story = [paragraph(LONG), PageBreak(), paragraph("Pagina doi. " + LONG), PageBreak(), paragraph("Pagina trei. " + LONG)]
    text = pdf_text(make_pdf(story, header="Contract nr. 5", footer="Pagina {n} din 3"))
    assert "Pagina 1 din" not in text and "Pagina 2 din" not in text
    assert text.count("Contract nr. 5") <= 1  # a header stays on the first page only
    assert text.count("Ion Popescu") == 3


def test_a_paragraph_continues_on_the_next_page():
    words = " ".join(f"cuvant{i}" for i in range(400))
    text = pdf_text(make_pdf([paragraph(words)]))
    assert text == words  # one paragraph, although it crosses a page


def test_scanned_pdf_is_reported():
    with pytest.raises(UnsupportedFormat, match="no text layer"):
        open_document("scan.pdf", empty_page_pdf())


def test_a_page_without_text_is_marked_and_the_other_pages_are_read():
    pdf = make_pdf([paragraph("Prima pagina."), PageBreak(), PageBreak(), paragraph("A treia pagina.")], footer="")
    text = pdf_text(pdf)
    assert "Prima pagina." in text and "A treia pagina." in text
    assert "Page 2 has no text layer" in text


def test_broken_file_is_reported():
    with pytest.raises(UnsupportedFormat):
        open_document("x.pdf", b"%PDF-1.4 this is not a PDF")


def test_words_cut_at_the_end_of_a_line_are_joined():
    assert _join(["despre con-", "tract si"]) == "despre contract si"
    assert _join(["din Cluj-", "Napoca si"]) == "din Cluj-Napoca si"
    assert _join(["a doua -", "linie"]) == "a doua - linie"  # a dash is not a cut word


def test_output_of_a_pdf_is_text(tmp_path):
    assert output_name("contract.pdf", "anon") == "contract.anon.txt"
    assert output_name("contract.anon.txt", "restored") == "contract.restored.txt"
    pdf = make_pdf([paragraph(LONG)])
    with Vault(tmp_path / "v.db") as vault:
        engine = Engine(vault, Settings(), StubDetector({"Ion Popescu": "PERSON"}))
        result = engine.anonymize("contract.pdf", pdf)
        text = result.data.decode("utf-8")
        assert "Ion Popescu" not in text and "[PERSON_001]" in text
        assert result.leaks == []
        # The leak check also reads a PDF.
        assert engine.find_leaks("contract.pdf", pdf) == ["[PERSON_001]"]
        assert "Ion Popescu" in scan_text("contract.pdf", pdf)
        restored = engine.restore("contract.anon.txt", result.data)
        assert "Ion Popescu" in restored.data.decode("utf-8")
        assert re.search(r"\[[A-Z_]+\d+\]", restored.data.decode("utf-8")) is None
