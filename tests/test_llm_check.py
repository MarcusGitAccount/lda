"""The local LLM checker, tested against a fake Ollama server. No model is needed."""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from legal_anonymizer.config import Settings
from legal_anonymizer.detector import Detector
from legal_anonymizer.llm_check import LLM_MODEL, LLM_MAX_REPLY, SYSTEM, LlmTimeout, LlmUnavailable, OllamaChecker, mask, parse_items
from legal_anonymizer.spans import Span

TEXT = "Contractul este semnat de Ion Popescu cu Xyzzy Quuxington, la Brașov."


class FakeOllama:
    """Answers /api/tags and /api/chat. `items` is the list that the "LLM" returns."""

    def __init__(self, items=None, content=None, models=(LLM_MODEL,), structured=True, delay=0.0):
        self.items = items or []
        self.content = content
        self.models = list(models)
        self.delay = delay  # seconds to wait before an answer to /api/chat: a model that is too slow
        self.structured = structured  # False: answer 501 to a request with `format`, as Ollama does for Qwen3.5
        self.requests: list[dict] = []  # the requests that were answered
        self.rejected = 0
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, body: dict):
                data = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                self._send({"models": [{"name": m} for m in fake.models]})

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                time.sleep(fake.delay)
                if "format" in body and not fake.structured:
                    fake.rejected += 1
                    data = json.dumps({"error": "structured output is unavailable"}).encode()
                    self.send_response(501)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                fake.requests.append(body)
                content = fake.content if fake.content is not None else json.dumps({"items": fake.items})
                self._send({"message": {"role": "assistant", "content": content}})

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.host = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def fake():
    servers = []

    def make(**kwargs):
        servers.append(FakeOllama(**kwargs))
        return servers[-1]

    yield make
    for server in servers:
        server.close()


def hidden_popescu():
    start = TEXT.index("Ion Popescu")
    return [Span(start, start + len("Ion Popescu"), "PERSON", 0.9, "presidio")]


def test_mask_puts_a_tag_in_place_of_the_data():
    assert mask(TEXT, hidden_popescu()) == "Contractul este semnat de [PERSON] cu Xyzzy Quuxington, la Brașov."


def test_the_llm_adds_a_name_that_the_models_missed(fake):
    server = fake(items=[{"text": "Xyzzy Quuxington", "type": "PERSON"}])
    spans = OllamaChecker(host=server.host).missed(TEXT, hidden_popescu())
    assert [(TEXT[s.start : s.end], s.type, s.source) for s in spans] == [("Xyzzy Quuxington", "PERSON", "llm")]


def test_the_llm_never_sees_the_data_that_is_hidden(fake):
    server = fake(items=[])
    OllamaChecker(host=server.host).missed(TEXT, hidden_popescu())
    sent = json.dumps(server.requests)
    assert "Popescu" not in sent and "[PERSON]" in sent


def test_a_word_that_the_llm_invents_is_dropped(fake):
    server = fake(items=[{"text": "Invented Name", "type": "PERSON"}])
    assert OllamaChecker(host=server.host).missed(TEXT, hidden_popescu()) == []


def test_a_name_that_is_already_hidden_is_not_added_again(fake):
    # The LLM did not see "Ion Popescu" (it is a tag), so a string from the original text is not real.
    server = fake(items=[{"text": "Ion Popescu", "type": "PERSON"}])
    assert OllamaChecker(host=server.host).missed(TEXT, hidden_popescu()) == []


def test_a_tag_is_not_a_hit(fake):
    server = fake(items=[{"text": "[PERSON]", "type": "PERSON"}])
    assert OllamaChecker(host=server.host).missed(TEXT, hidden_popescu()) == []


def test_every_visible_occurrence_is_found(fake):
    text = "Xyzzy Quuxington a venit. Apoi Xyzzy Quuxington a plecat."
    server = fake(items=[{"text": "Xyzzy Quuxington", "type": "PERSON"}])
    assert len(OllamaChecker(host=server.host).missed(text, [])) == 2


def test_a_reply_without_the_format_gives_no_hits(fake):
    server = fake(content="I cannot help with that.")
    assert OllamaChecker(host=server.host).missed(TEXT, []) == []


def test_the_request_asks_for_a_list_and_no_thinking(fake):
    server = fake(items=[])
    OllamaChecker(host=server.host).missed(TEXT, [])
    request = server.requests[0]
    assert request["think"] is False and request["options"]["temperature"] == 0
    assert request["format"]["properties"]["items"]["type"] == "array"


def test_the_prompt_tells_the_model_the_format(fake):
    # The server cannot always force the format, so the prompt must describe it.
    assert "JSON" in SYSTEM and '"items"' in SYSTEM
    server = fake(items=[])
    OllamaChecker(host=server.host).missed(TEXT, [])
    assert "JSON" in server.requests[0]["messages"][0]["content"]


def test_a_server_that_cannot_force_the_format_is_asked_once_and_the_checker_goes_on(fake):
    server = fake(items=[{"text": "Xyzzy Quuxington", "type": "PERSON"}], structured=False)
    checker = OllamaChecker(host=server.host)
    spans = checker.missed(TEXT + " " * 2000 + TEXT, hidden_popescu())  # two chunks
    assert [TEXT[s.start : s.end] for s in spans if s.start < len(TEXT)] == ["Xyzzy Quuxington"]
    assert server.rejected == 1  # it did not try again for the second chunk
    assert all("format" not in request for request in server.requests)
    assert checker.structured is False and len(server.requests) >= 2


@pytest.mark.parametrize(
    "content",
    [
        '{"items": [{"text": "Xyzzy Quuxington", "type": "PERSON"}]}',
        '```json\n{"items": [{"text": "Xyzzy Quuxington", "type": "PERSON"}]}\n```',
        'Here is the list: {"items": [{"text": "Xyzzy Quuxington", "type": "PERSON"}]} Done.',
        '[{"text": "Xyzzy Quuxington", "type": "PERSON"}]',
        '<think>\n\n</think>\n\n{"items": [{"text": "Xyzzy Quuxington", "type": "PERSON"}]}',
    ],
)
def test_the_reply_is_read_even_with_words_around_the_json(content):
    assert parse_items(content) == parse_items('{"items": [{"text": "Xyzzy Quuxington", "type": "PERSON"}]}')
    assert [(i.text, i.type) for i in parse_items(content)] == [("Xyzzy Quuxington", "PERSON")]


@pytest.mark.parametrize("content", ["I cannot help with that.", "", "{broken", '{"other": 1}', '"text"'])
def test_a_reply_with_no_usable_json_is_none(content):
    assert parse_items(content) is None


def test_items_of_an_unknown_type_or_without_text_are_dropped():
    content = '{"items": [{"text": "A", "type": "DATE"}, {"type": "PERSON"}, {"text": "Ion Zorg", "type": "PERSON"}]}'
    assert [i.text for i in parse_items(content)] == ["Ion Zorg"]


def test_the_checker_counts_the_replies_that_it_could_not_read(fake):
    server = fake(content="I cannot help with that.")
    checker = OllamaChecker(host=server.host)
    checker.missed(TEXT, [])
    assert checker.invalid == 1


def test_the_length_of_a_reply_is_limited(fake):
    # A small model can repeat itself without end. Without a limit, one piece can take minutes.
    server = fake(items=[])
    OllamaChecker(host=server.host).missed(TEXT, [])
    assert server.requests[0]["options"]["num_predict"] == LLM_MAX_REPLY


def test_a_piece_that_times_out_is_skipped_with_a_warning_and_the_next_piece_is_checked(fake):
    server = fake(items=[{"text": "Xyzzy Quuxington", "type": "PERSON"}], delay=0.5)
    checker = OllamaChecker(host=server.host, timeout=0.2)
    with pytest.warns(UserWarning, match="skipped a piece"):
        spans = checker.missed(TEXT, hidden_popescu())
    assert spans == [] and checker.skipped == 1
    server.delay = 0.0  # the model is fast again: the checker still works
    assert len(OllamaChecker(host=server.host).missed(TEXT, hidden_popescu())) == 1


def test_a_server_that_is_down_is_still_an_error_and_a_timeout_is_a_kind_of_it():
    with pytest.raises(LlmUnavailable):
        OllamaChecker(host="http://127.0.0.1:9", timeout=1).check_ready()
    assert issubclass(LlmTimeout, LlmUnavailable)


def test_a_text_without_words_is_not_sent(fake):
    server = fake(items=[])
    spans = [Span(0, 10, "PERSON", 0.9, "presidio")]
    OllamaChecker(host=server.host).missed("0123456789", spans)
    assert server.requests == []


def test_a_server_that_is_down_gives_a_clear_error():
    with pytest.raises(LlmUnavailable, match="does not answer"):
        OllamaChecker(host="http://127.0.0.1:9", timeout=2).check_ready()


def test_a_missing_model_gives_a_clear_error(fake):
    server = fake(models=["other:1b"])
    with pytest.raises(LlmUnavailable, match="ollama pull"):
        OllamaChecker(host=server.host).check_ready()


def test_the_model_is_found_with_the_latest_tag(fake):
    server = fake(models=[f"{LLM_MODEL}:latest"])
    OllamaChecker(host=server.host).check_ready()


# --- the level and the detector ---------------------------------------------------


def test_the_levels_say_what_runs():
    assert (Settings().use_gliner, Settings().use_llm) == (False, False)
    assert (Settings(level="medium").use_gliner, Settings(level="medium").use_llm) == (True, False)
    assert (Settings(level="high").use_gliner, Settings(level="high").use_llm) == (True, True)


def test_an_unknown_level_is_refused():
    with pytest.raises(ValueError, match="Unknown level"):
        Settings(level="extreme").validate()


@pytest.mark.parametrize("host", ["http://192.168.1.20:11434", "https://api.example.com", "http://ollama.lan:11434"])
def test_an_llm_on_another_computer_is_refused(host):
    with pytest.raises(ValueError, match="not on this computer"):
        Settings(level="high", llm_host=host).validate()


@pytest.mark.parametrize("host", ["http://127.0.0.1:11434", "http://localhost:11434"])
def test_an_llm_on_this_computer_is_accepted(host):
    Settings(level="high", llm_host=host).validate()


def test_the_detector_cleans_the_spans_of_the_llm(fake):
    # The LLM lists the name with the title. The clean-up cuts the title, as for a model span.
    text = "Contactați pe domnul Xyzzy Quuxington mâine."
    server = fake(items=[{"text": "domnul Xyzzy Quuxington", "type": "PERSON"}])
    settings = Settings(level="high", llm_host=server.host)
    spans = Detector(settings)._llm_spans(text, [], settings, set(), None)
    assert [text[s.start : s.end] for s in spans] == ["Xyzzy Quuxington"]


@pytest.mark.models
def test_level_high_runs_the_whole_chain_with_the_real_models(fake):
    # BERT and GLiNER find "Ion Popescu". The "LLM" (a fake server) lists a name that nobody else knows.
    text = "Ion Popescu a semnat contractul cu doamna Zorgblatt Quoxx la Brașov."
    server = fake(items=[{"text": "Zorgblatt Quoxx", "type": "PERSON"}])
    settings = Settings(level="high", llm_host=server.host)
    detector = Detector(settings)
    detector.warm_up(("ro",))
    spans = detector.detect(text, "ro")
    hidden = {text[s.start : s.end] for s in spans if s.type != "KEEP"}
    assert "Ion Popescu" in hidden and "Zorgblatt Quoxx" in hidden
    sent = json.dumps(server.requests)
    assert "Popescu" not in sent  # the LLM read the hidden text
