"""The GLiNER recognizer. The chunking is tested without the model. One test loads the model."""

from __future__ import annotations

import pytest

from legal_anonymizer.gliner_ner import chunks


def test_a_short_text_is_one_chunk():
    assert list(chunks("Ion Popescu", 800, 80)) == [(0, "Ion Popescu")]


def test_the_chunks_cover_the_text_and_the_offsets_are_right():
    text = " ".join(f"cuvânt{i}" for i in range(400))
    pieces = list(chunks(text, 200, 40))
    assert len(pieces) > 1
    for offset, piece in pieces:
        assert text[offset : offset + len(piece)] == piece
    assert pieces[0][0] == 0 and pieces[-1][0] + len(pieces[-1][1]) == len(text)
    covered = set()
    for offset, piece in pieces:
        covered.update(range(offset, offset + len(piece)))
    assert covered == set(range(len(text)))


def test_a_word_is_not_cut_at_the_end_of_a_chunk():
    text = " ".join(["Mureșul"] * 200)
    for _, piece in chunks(text, 100, 20):
        assert set(piece.split()) == {"Mureșul"}


def test_the_chunks_overlap_so_a_name_at_the_edge_is_seen_whole():
    text = "a" * 90 + " Anca-Maria Rusu " + "b" * 90
    assert any("Anca-Maria Rusu" in piece for _, piece in chunks(text, 100, 40))


@pytest.mark.models
def test_gliner_finds_a_person_and_a_company_in_english():
    pytest.importorskip("gliner")
    from legal_anonymizer.gliner_ner import GlinerRecognizer

    text = "The contract was signed by Margaret Ellison for Northgate Freight Forwarding Ltd in Leeds."
    results = GlinerRecognizer("en").analyze(text, ["PERSON", "ORGANIZATION", "LOCATION", "ADDRESS"])
    found = {(r.entity_type, text[r.start : r.end]) for r in results}
    assert ("PERSON", "Margaret Ellison") in found
    assert any(t == "ORGANIZATION" and "Northgate" in s for t, s in found)


@pytest.mark.models
def test_gliner_does_nothing_for_types_that_are_not_its_job():
    pytest.importorskip("gliner")
    from legal_anonymizer.gliner_ner import GlinerRecognizer

    assert GlinerRecognizer("en").analyze("Write to office@alfa.example", ["EMAIL_ADDRESS", "IBAN_CODE"]) == []
