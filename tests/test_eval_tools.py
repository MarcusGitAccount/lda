"""The evaluation tools: the metrics, the gold projection, the result files, the TAB converter."""

from __future__ import annotations

import json

import pytest

from eval import report, tab_corpus, tracker
from eval.corpus_eval import GoldEntity, covered, project
from eval.metrics import Counts
from legal_anonymizer.config import Settings
from legal_anonymizer.spans import Span, keep_set

# --- metrics ------------------------------------------------------------------------


def test_the_scores_of_a_run():
    c = Counts(tp=8, fp=2, fn=2)
    assert (c.precision, c.recall) == (0.8, 0.8)
    assert round(c.f(1), 4) == 0.8 and round(c.f(2), 4) == 0.8


def test_f2_counts_recall_more_than_precision():
    high_recall = Counts(tp=9, fp=9, fn=1)  # hides too much
    high_precision = Counts(tp=5, fp=0, fn=5)  # leaks half
    assert high_recall.f(2) > high_precision.f(2)
    assert high_recall.f(1) < 0.8 < high_precision.f(1) + 0.2  # F1 is not so clear about it


def test_a_run_with_nothing_found_has_zero_scores_and_no_error():
    c = Counts()
    assert (c.precision, c.recall, c.f(1), c.f(2)) == (0, 0, 0, 0)


# --- gold projection ----------------------------------------------------------------


def test_every_written_form_of_an_entity_is_found():
    entities = [GoldEntity("PERSON", ["Anca-Maria Rusu", "Rusu"])]
    text = "Anca-Maria Rusu a semnat. Apoi doamna Rusu a plecat."
    assert [text[m.start : m.end] for m in project(text, entities)] == ["Anca-Maria Rusu", "Rusu"]


def test_the_longest_form_wins_where_two_forms_overlap():
    entities = [GoldEntity("ORGANIZATION", ["Northgate Freight Forwarding Ltd", "Northgate"])]
    text = "Northgate Freight Forwarding Ltd (Northgate) paid."
    assert [text[m.start : m.end] for m in project(text, entities)] == ["Northgate Freight Forwarding Ltd", "Northgate"]


def test_a_form_is_not_found_inside_a_longer_word():
    assert project("Rusulescu a venit.", [GoldEntity("PERSON", ["Rusu"])]) == []


def test_the_case_of_the_letters_and_the_spaces_do_not_matter():
    entities = [GoldEntity("PERSON", ["Ion Popescu"])]
    assert len(project("ION   POPESCU și ion popescu", entities)) == 2


def test_a_title_is_not_a_part_of_a_gold_mention():
    entities = [GoldEntity("PERSON", ["Mr Abdisamad Adow Sufi", "Ms N. Mole"])]
    text = "Mr Abdisamad Adow Sufi met Ms N. Mole."
    assert [text[m.start : m.end] for m in project(text, entities)] == ["Abdisamad Adow Sufi", "N. Mole"]


def test_a_mention_is_hidden_when_every_letter_and_digit_is_covered():
    text = "Alfa Construct S.R.L. a plătit."
    start = 0
    end = text.index(" a plătit")
    assert covered(text, start, end, [Span(0, end, "ORGANIZATION", 0.9, "x")])
    assert covered(text, start, end, [Span(0, end - 1, "ORGANIZATION", 0.9, "x")])  # the final dot may stay
    assert not covered(text, start, end, [Span(0, 5, "ORGANIZATION", 0.9, "x")])  # "Alfa" only


# --- result files -------------------------------------------------------------------


@pytest.fixture
def results_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(tracker, "RESULTS", tmp_path)
    monkeypatch.setattr(report, "RESULTS", tmp_path)
    monkeypatch.setattr(report, "OUT", tmp_path / "results.md")
    return tmp_path


def test_a_run_is_saved_with_what_is_needed_to_repeat_it(results_dir):
    path = tracker.record("mapa-ro", "bert+gliner", Settings(level="medium"), {"recall_any_type": 0.9}, 12.34)
    run = json.loads(path.read_text(encoding="utf-8"))
    assert run["dataset"] == "mapa-ro" and run["name"] == "bert+gliner" and run["seconds"] == 12.3
    assert run["settings"]["level"] == "medium" and run["settings"]["gliner_model"]
    assert run["settings"]["llm_model"] is None  # the LLM did not run at this level
    assert {"commit", "dirty", "python", "machine", "packages"} <= set(run["environment"])
    assert "presidio-analyzer" in run["environment"]["packages"]


def test_the_file_name_is_safe(results_dir):
    path = tracker.record("corpus-x", "a/b c", Settings(), {}, 1)
    assert "/" not in path.name and " " not in path.name


def test_the_report_has_a_table_for_each_dataset(results_dir):
    mapa = {
        "recall_any_type": 0.93,
        "classes": {k: {"recall": 0.9} for k in ("PERSON", "ORGANISATION", "ADDRESS")},
        "hidden_or_not": Counts(tp=9, fp=1, fn=1).as_dict(),
        "tokens_per_second": 100,
    }
    corpus = {
        "mentions": Counts(tp=9, fp=1, fn=1).as_dict(),
        "split_entities": 1,
        "entities_seen": 10,
        "merged_ids": 0,
        "leaked_forms": 2,
        "restore_words_equal": 0.97,
        "words_per_second": 50,
    }
    tracker.record("mapa-ro", "baseline", Settings(), mapa, 1)
    tracker.record("corpus-demo", "baseline", Settings(), corpus, 1)
    assert report.main() == 0
    text = (results_dir / "results.md").read_text(encoding="utf-8")
    assert "## mapa-ro" in text and "## corpus-demo" in text and "93.0%" in text and "1/10" in text


# --- the TAB converter --------------------------------------------------------------


def mention(kind, form, entity, identifier="DIRECT"):
    return {"entity_type": kind, "span_text": form, "entity_id": entity, "identifier_type": identifier}


def test_the_gold_has_only_what_the_tool_hides_by_default():
    document = {
        "annotations": {
            "a1": {
                "entity_mentions": [
                    mention("PERSON", "Galip  Yalman", "e1"),
                    mention("PERSON", "Mr Yalman", "e1", "QUASI"),
                    mention("DATETIME", "5 May 1998", "e2"),  # not hidden by default
                    mention("ORG", "Ankara Court", "e3", "NO_MASK"),  # TAB does not mask it
                    mention("LOC", "Turkey", "e4"),  # the policy keeps countries visible
                    mention("CODE", "36110/97", "e5"),
                ]
            }
        }
    }
    gold = tab_corpus.gold_entities(document, keep_set())
    assert gold == [
        {"type": "PERSON", "forms": ["Galip Yalman", "Mr Yalman"]},
        {"type": "CODE", "forms": ["36110/97"]},
    ]


def test_the_cases_are_picked_at_fixed_steps_and_the_size_is_checked():
    documents = [{"doc_id": f"{i:03}", "text": "word " * (2000 if i % 2 else 100)} for i in range(40)]
    first = tab_corpus.pick(documents, 5)
    assert [d["doc_id"] for d in first] == [d["doc_id"] for d in tab_corpus.pick(documents, 5)]
    assert len(first) == 5 and all(len(d["text"].split()) == 2000 for d in first)


# --- the sample of Romanian legal acts and the hits report ------------------------------


def _act(kind="LEGE", year=2010, text_words=900, number="12", **extra):
    from datetime import date

    return {"id": 1, "type": kind, "document_number": number, "adopted_at": date(year, 5, 1), "content": "cuvant " * text_words, **extra}


def test_an_act_must_have_a_known_type_a_date_and_a_fit_length():
    from eval.ro_law_corpus import eligible

    assert eligible(_act("LEGE")) == "lege"
    assert eligible(_act("HOTĂRÎRE")) == "hotarare" == eligible(_act("HOTĂRÂRE"))  # both spellings
    assert eligible(_act("RAPORT")) is None  # not a kind of act that we want
    assert eligible(_act(text_words=100)) is None and eligible(_act(text_words=9000)) is None
    assert eligible(_act(year=1995)) is None
    assert eligible({**_act(), "adopted_at": None}) is None


def test_the_sample_is_small_fixed_and_has_every_group():
    from eval.ro_law_corpus import reservoir

    rows = [_act(kind, number=f"{kind}{i}") for kind in ("LEGE", "ORDIN", "DECRET") for i in range(40)]
    first = reservoir(iter(rows), 5)
    again = reservoir(iter(rows), 5)
    assert {g: [a["document_number"] for a in acts] for g, acts in first.items()} == {
        g: [a["document_number"] for a in acts] for g, acts in again.items()
    }
    assert sorted(first) == ["decret", "lege", "ordin"] and all(len(acts) == 5 for acts in first.values())


def test_the_file_name_is_plain_ascii():
    from eval.ro_law_corpus import file_name

    assert file_name(_act("LEGE", 2010, number="12/2010 bis"), "lege") == "lege-2010-12-2010-bis.ro.txt"
    assert file_name(_act("ORDONANȚĂ", 2020, number="ȘTEFAN"), "ordonanta") == "ordonanta-2020-stefan.ro.txt"


def test_the_hits_report_has_its_own_table():
    from eval.report import row_for, row_hits

    assert row_for("hits-ro-law") is row_hits
