"""A local LLM that reads the hidden text and lists the sensitive words that remain.

The LLM never changes the text. It gets the text after hiding (tags such as [PERSON] in place of
the data), and it returns a list of strings. We hide a string only if it is really in the text
that the LLM read. An LLM can invent a word, so the check by code is the rule. So the LLM can add
hits, but it cannot remove one.

The LLM runs in Ollama on this computer. We use the HTTP API of Ollama with the standard library,
so the tool has no new dependency. `Settings.validate` refuses a host that is not on this computer.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
import warnings
from dataclasses import dataclass

from .gliner_ner import chunks
from .spans import Span

LLM_MODEL = "qwen3.5:4b"
LLM_HOST = "http://127.0.0.1:11434"
LLM_TYPES = ["PERSON", "ORGANIZATION", "ADDRESS", "LOCATION"]
LLM_CHUNK = 1500  # characters. A small model reads less well in a long text.
LLM_OVERLAP = 100
LLM_SCORE = 0.5
LLM_MAX_REPLY = 512  # tokens. A small model can repeat itself without end; a list of names is much shorter.

SYSTEM = (
    "You check a legal document that was made anonymous. The tool replaced sensitive data with tags "
    "such as [PERSON] or [ORGANIZATION]. Find the sensitive data that the tool missed: names of "
    "people, names of companies and other organizations, street addresses, and names of places. "
    "Copy each item exactly as it is in the text. Do not list tags. Do not list laws, courts, public "
    "bodies, job titles, or common words. If the tool missed nothing, return an empty list. "
    'Reply with JSON only, in this form: {"items": [{"text": "...", "type": "PERSON"}]}. '
    "The type is PERSON, ORGANIZATION, ADDRESS or LOCATION."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"text": {"type": "string"}, "type": {"type": "string", "enum": LLM_TYPES}},
                "required": ["text", "type"],
            },
        }
    },
    "required": ["items"],
}


class LlmUnavailable(RuntimeError):
    """Ollama does not run, or it does not have the model."""


class LlmTimeout(LlmUnavailable):
    """The server did not answer one request in time (a small model that repeats itself)."""


class NoStructuredOutput(LlmUnavailable):
    """The server cannot force the format of the reply. (Ollama answers 501 for the Qwen3.5 models.)"""


@dataclass
class Candidate:
    text: str
    type: str


_TAG = re.compile(r"\[[A-Z_]+\]")


def mask(text: str, spans: list[Span]) -> str:
    """The text with a tag, such as [PERSON], in place of each span."""
    parts, position = [], 0
    for span in sorted(spans, key=lambda s: (s.start, -s.end)):
        if span.start < position or span.type == "KEEP":
            continue
        parts.append(text[position : span.start])
        parts.append(f"[{span.type}]")
        position = span.end
    parts.append(text[position:])
    return "".join(parts)


def parse_items(content: str) -> list[Candidate] | None:
    """Read the reply of the model. Return None if it has no usable JSON.

    A model that is not forced to the format can add words around the JSON, or a code fence.
    A wrong item does no harm: the caller keeps a string only if it is really in the text.
    """
    text = re.sub(r"```(?:json)?", "", content)
    for opening, closing in (("{", "}"), ("[", "]")):
        start, end = text.find(opening), text.rfind(closing)
        if start < 0 or end <= start:
            continue
        try:
            data = json.loads(text[start : end + 1])
        except ValueError:
            continue
        items = data.get("items") if isinstance(data, dict) else data
        if not isinstance(items, list):
            continue
        return [
            Candidate(item["text"].strip(), item["type"])
            for item in items
            if isinstance(item, dict) and isinstance(item.get("text"), str) and item.get("type") in LLM_TYPES
        ]
    return None


class OllamaChecker:
    def __init__(self, model: str = LLM_MODEL, host: str = LLM_HOST, timeout: float = 300.0):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.requests = 0  # for the experiment log
        self.structured = True  # ask the server to force the JSON format; we stop if it cannot
        self.invalid = 0  # replies that had no usable JSON, for the experiment log
        self.skipped = 0  # pieces of text that the LLM did not check, because the server was too slow

    # --- the server ---------------------------------------------------------------

    def _call(self, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            self.host + path, data=data, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            if error.code == 501:
                raise NoStructuredOutput(f"Ollama cannot force the format for '{self.model}' (HTTP 501).") from error
            raise LlmUnavailable(f"Ollama returned an error at {self.host} ({error}).") from error
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            if isinstance(error, TimeoutError) or isinstance(getattr(error, "reason", None), TimeoutError):
                raise LlmTimeout(f"Ollama did not answer in {self.timeout:.0f} s ({error}).") from error
            raise LlmUnavailable(
                f"Ollama does not answer at {self.host} ({error}). Start it, or use level 'medium' or 'low'."
            ) from error

    def check_ready(self) -> None:
        """Fail now, with a clear message, if the server or the model is missing."""
        names = {m["name"] for m in self._call("/api/tags").get("models", [])}
        if self.model not in names and f"{self.model}:latest" not in names:
            raise LlmUnavailable(f"Ollama does not have the model '{self.model}'. Run: ollama pull {self.model}")

    # --- the check ----------------------------------------------------------------

    def ask(self, hidden_text: str) -> list[Candidate]:
        self.requests += 1
        body = {
            "model": self.model,
            "stream": False,
            "think": False,  # a thinking model is slower and not better on this job
            "options": {"temperature": 0, "num_ctx": 4096, "num_predict": LLM_MAX_REPLY},
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": hidden_text}],
        }
        if self.structured:
            try:
                reply = self._call("/api/chat", {**body, "format": SCHEMA})
            except NoStructuredOutput:
                self.structured = False  # the prompt asks for JSON, and `parse_items` reads what comes back
        if not self.structured:
            reply = self._call("/api/chat", body)
        items = parse_items(str(reply.get("message", {}).get("content", "")))
        if items is None:
            self.invalid += 1  # the model did not follow the format. We lose its hits for this piece.
            return []
        return items

    def missed(self, text: str, spans: list[Span]) -> list[Span]:
        """Spans for the strings that the LLM sees in the hidden text. Each one is in `text`."""
        hidden = mask(text, spans)
        found: dict[str, str] = {}
        for _, piece in chunks(hidden, LLM_CHUNK, LLM_OVERLAP):
            if not re.search(r"\w{3}", _TAG.sub("", piece)):
                continue  # no text to check
            try:
                candidates = self.ask(piece)
            except LlmTimeout as error:
                self.skipped += 1  # do not lose the whole document for one piece, but say so
                warnings.warn(f"The LLM check skipped a piece of text: {error}", stacklevel=2)
                continue
            for candidate in candidates:
                if self._real(candidate.text, piece):
                    found.setdefault(candidate.text, candidate.type)
        result = []
        for surface, type_ in found.items():
            for match in re.finditer(rf"(?<!\w){re.escape(surface)}(?!\w)", text):
                if not any(s.start < match.end() and match.start() < s.end for s in spans if s.type != "KEEP"):
                    result.append(Span(match.start(), match.end(), type_, LLM_SCORE, "llm"))
        return result

    @staticmethod
    def _real(surface: str, piece: str) -> bool:
        """The string must be in the text that the LLM read, and it must not be a tag."""
        return (
            len(surface) >= 3
            and re.search(r"[^\W\d_]", surface) is not None
            and not _TAG.fullmatch(surface)
            and surface in _TAG.sub("\0", piece)
        )
