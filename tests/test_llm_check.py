"""The local LLM checker, tested against a fake Ollama server. No model is needed."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from legal_anonymizer.config import Settings
from legal_anonymizer.detector import Detector
from legal_anonymizer.llm_check import LLM_MODEL, LlmUnavailable, OllamaChecker, mask
from legal_anonymizer.spans import Span

TEXT = "Contractul este semnat de Ion Popescu cu Xyzzy Quuxington, la Brașov."


class FakeOllama:
    """Answers /api/tags and /api/chat. `items` is the list that the "LLM" returns."""

    def __init__(self, items=None, content=None, models=(LLM_MODEL,)):
        self.items = items or []
        self.content = content
        self.models = list(models)
        self.requests: list[dict] = []
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
