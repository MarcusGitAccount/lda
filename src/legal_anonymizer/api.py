"""Local HTTP API (FastAPI).

Run it with `lda serve`. It listens on 127.0.0.1 only. The vault holds real
client data, so do not open this API to a network.
"""

from __future__ import annotations

import base64
import re
import tempfile
import threading
from collections import Counter
from pathlib import Path, PurePosixPath

import yaml
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from .cli import MATTER_RE, default_home, output_name
from .config import Settings, load_settings
from .detector import Detector
from .documents import TEXT_SUFFIXES, UnsupportedFormat
from .engine import Engine
from .vault import Vault

MAX_UPLOAD_BYTES = 25 * 1024 * 1024


class MergeRequest(BaseModel):
    source: str
    target: str


def create_app(home: str | Path | None = None, detector: Detector | None = None) -> FastAPI:
    home = Path(home) if home else default_home()
    app = FastAPI(title="Legal document anonymizer", version="0.1.0")
    # The models are slow to load and not made for parallel calls. We share
    # one detector, and one request at a time uses it.
    detector = detector or Detector(Settings())
    lock = threading.Lock()

    def open_vault(matter: str, *, must_exist: bool = False) -> Vault:
        if not MATTER_RE.match(matter):
            raise HTTPException(400, "Bad matter name. Use letters, digits, '-', '_' and '.'.")
        path = home / f"{matter}.db"
        if must_exist and not path.exists():
            raise HTTPException(404, f"Matter '{matter}' does not exist.")
        return Vault(path)

    async def read_uploads(files: list[UploadFile]) -> list[tuple[str, bytes]]:
        result = []
        for upload in files:
            data = await upload.read(MAX_UPLOAD_BYTES + 1)
            if len(data) > MAX_UPLOAD_BYTES:
                raise HTTPException(413, f"'{upload.filename}' is larger than {MAX_UPLOAD_BYTES // 2**20} MB.")
            name = PurePosixPath((upload.filename or "document").replace("\\", "/")).name
            result.append((name, data))
        return result

    def document_payload(name: str, data: bytes) -> dict:
        payload = {"name": name, "content_base64": base64.b64encode(data).decode("ascii")}
        if PurePosixPath(name).suffix.lower() in TEXT_SUFFIXES:
            payload["text"] = data.decode("utf-8")
        return payload

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/matters/{matter}/anonymize")
    async def anonymize(
        matter: str,
        files: list[UploadFile] = File(...),
        language: str | None = Form(None, description="ro or en. Default: detect for each file."),
        config: UploadFile | None = File(None, description="YAML file with known entities and options."),
    ) -> dict:
        uploads = await read_uploads(files)
        settings = Settings()
        if config is not None:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "config.yaml"
                path.write_bytes(await config.read())
                try:
                    settings = load_settings(path)
                except (ValueError, KeyError, yaml.YAMLError) as error:
                    raise HTTPException(422, f"Bad config file: {error}") from error
        if language not in (None, "", "ro", "en"):
            raise HTTPException(422, "language must be 'ro' or 'en'.")
        with lock, open_vault(matter) as vault:
            engine = Engine(vault, settings, detector)
            try:
                engine.load_seeds()
                results = engine.anonymize_many(uploads, language=language or None)
            except UnsupportedFormat as error:
                raise HTTPException(415, str(error)) from error
            except ValueError as error:
                raise HTTPException(422, str(error)) from error
            except RuntimeError as error:  # no Ollama, no GLiNER: the level in the config file cannot run
                raise HTTPException(503, str(error)) from error
        documents = []
        for (name, _), result in zip(uploads, results):
            kinds = Counter(re.match(r"\[([A-Z_]+?)_\d+\]", p).group(1) for p in result.counts.elements())
            documents.append({
                **document_payload(output_name(name, "anon"), result.data),
                "source": name,
                "language": result.language,
                "hidden": dict(kinds),
                "ids": dict(result.counts),
                "leaks": result.leaks,
            })
        return {"matter": matter, "documents": documents}

    @app.post("/matters/{matter}/restore")
    async def restore(matter: str, files: list[UploadFile] = File(...)) -> dict:
        uploads = await read_uploads(files)
        documents = []
        with lock, open_vault(matter, must_exist=True) as vault:
            engine = Engine(vault, Settings(), detector)
            for name, data in uploads:
                try:
                    result = engine.restore(name, data)
                except UnsupportedFormat as error:
                    raise HTTPException(415, str(error)) from error
                except ValueError as error:
                    raise HTTPException(422, str(error)) from error
                documents.append({
                    **document_payload(output_name(name, "restored"), result.data),
                    "source": name,
                    "restored": dict(result.restored),
                    "unknown_ids": result.unknown,
                })
        return {"matter": matter, "documents": documents}

    @app.get("/matters/{matter}/entities")
    def entities(matter: str) -> dict:
        with open_vault(matter, must_exist=True) as vault:
            return {
                "matter": matter,
                "entities": [
                    {"id": e.placeholder, "type": e.type, "text": e.canonical, "forms": e.forms, "documents": e.documents}
                    for e in vault.entities()
                ],
            }

    @app.post("/matters/{matter}/merge")
    def merge(matter: str, request: MergeRequest) -> dict:
        with lock, open_vault(matter, must_exist=True) as vault:
            try:
                target = vault.merge(request.source, request.target)
            except KeyError as error:
                raise HTTPException(404, str(error)) from error
            except ValueError as error:
                raise HTTPException(422, str(error)) from error
            return {"id": target.placeholder, "text": target.canonical}

    return app
