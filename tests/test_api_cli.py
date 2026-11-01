import base64
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import legal_anonymizer.api as api_module
import legal_anonymizer.engine as engine_module
from legal_anonymizer.api import create_app
from legal_anonymizer.cli import main
from legal_anonymizer.documents import scan_text
from samples import build_docx

pytestmark = pytest.mark.models

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"
TXT = ["01_contract_prestari_servicii.ro.txt", "02_notificare_reziliere.ro.txt", "03_settlement_agreement.en.txt"]


@pytest.fixture
def client(tmp_path, detector):
    return TestClient(create_app(tmp_path / "vaults", detector))


def upload(*names):
    return [("files", (n, (SAMPLES / n).read_bytes())) for n in names]


def test_api_anonymize_then_restore_a_batch(client):
    config = ("config", ("matter.yaml", (SAMPLES / "matter.yaml").read_bytes()))
    response = client.post("/matters/case-1/anonymize", files=[*upload(*TXT), ("files", ("w.docx", build_docx())), config])
    assert response.status_code == 200, response.text
    docs = response.json()["documents"]
    assert [d["name"] for d in docs] == [
        "01_contract_prestari_servicii.ro.anon.txt", "02_notificare_reziliere.ro.anon.txt",
        "03_settlement_agreement.en.anon.txt", "w.anon.docx",
    ]
    assert [d["language"] for d in docs[:3]] == ["ro", "ro", "en"]
    assert all(d["leaks"] == [] for d in docs)
    assert "Popescu" not in docs[0]["text"] and "[PERSON_001]" in docs[0]["text"]
    assert docs[0]["hidden"]["PERSON"] >= 2

    entities = client.get("/matters/case-1/entities").json()["entities"]
    ion = next(e for e in entities if e["id"] == "[PERSON_001]")
    assert ion["type"] == "PERSON" and ion["text"] == "Ion Popescu"

    # restore what we got, also the Word file
    back = client.post("/matters/case-1/restore", files=[("files", (d["name"], base64.b64decode(d["content_base64"]))) for d in docs])
    assert back.status_code == 200, back.text
    restored = back.json()["documents"]
    assert restored[0]["name"] == "01_contract_prestari_servicii.ro.restored.txt"
    assert "Ion Popescu" in restored[0]["text"] and "[PERSON_" not in restored[0]["text"]
    assert "Ion Popescu" in scan_text("w.docx", base64.b64decode(restored[3]["content_base64"]))
    assert all(d["unknown_ids"] == [] for d in restored)


def test_api_errors(client, monkeypatch):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.post("/matters/..%2Fx/anonymize", files=upload(TXT[0])).status_code in (400, 404)
    assert client.post("/matters/bad name/anonymize", files=upload(TXT[0])).status_code == 400
    assert client.post("/matters/nope/restore", files=upload(TXT[0])).status_code == 404
    assert client.get("/matters/nope/entities").status_code == 404
    assert client.post("/matters/m1/anonymize", files=[("files", ("a.pdf", b"%PDF-1.4"))]).status_code == 415
    assert client.post("/matters/m1/anonymize", files=[("files", ("a.docx", b"not a zip"))]).status_code == 422
    assert client.post("/matters/m1/anonymize", files=upload(TXT[0]), data={"language": "fr"}).status_code == 422
    bad_config = ("config", ("c.yaml", b"hide: [NOT_A_TYPE]"))
    assert client.post("/matters/m1/anonymize", files=[*upload(TXT[0]), bad_config]).status_code == 422
    monkeypatch.setattr(api_module, "MAX_UPLOAD_BYTES", 10)
    assert client.post("/matters/m1/anonymize", files=upload(TXT[0])).status_code == 413


def test_api_merge(client):
    client.post("/matters/m2/anonymize", files=[("files", ("a.txt", "Ion Popescu și Popescu Vasile au semnat.".encode()))])
    ids = [e["id"] for e in client.get("/matters/m2/entities").json()["entities"] if e["type"] == "PERSON"]
    assert len(ids) == 2
    merged = client.post("/matters/m2/merge", json={"source": ids[1], "target": ids[0]})
    assert merged.status_code == 200 and merged.json()["id"] == ids[0]
    assert client.post("/matters/m2/merge", json={"source": "[PERSON_099]", "target": ids[0]}).status_code == 404


@pytest.fixture
def cli(tmp_path, detector, monkeypatch, capsys):
    monkeypatch.setattr(engine_module, "Detector", lambda settings: detector)
    home = tmp_path / "home"

    def run(*args):
        code = main(["--home", str(home), *map(str, args)])
        return code, capsys.readouterr().out

    return run


def test_cli_full_flow(cli, tmp_path):
    out_dir, back_dir = tmp_path / "anon", tmp_path / "back"
    files = [SAMPLES / n for n in TXT]
    docx = tmp_path / "w.docx"
    docx.write_bytes(build_docx())

    code, out = cli("anonymize", *files, docx, "-m", "demo", "-o", out_dir, "-c", SAMPLES / "matter.yaml")
    assert code == 0, out
    assert (out_dir / "01_contract_prestari_servicii.ro.anon.txt").exists() and (out_dir / "w.anon.docx").exists()
    assert "(ro)" in out and "(en)" in out and "PERSON" in out
    assert "Ion Popescu" not in out  # the summary must not print real data
    assert "Popescu" not in (out_dir / TXT[0].replace(".txt", ".anon.txt")).read_text(encoding="utf-8")

    code, out = cli("verify", *sorted(out_dir.iterdir()), "-m", "demo")
    assert code == 0 and "LEAK" not in out

    code, out = cli("restore", *sorted(out_dir.glob("*.txt")), "-m", "demo", "-o", back_dir)
    assert code == 0, out
    restored = (back_dir / "01_contract_prestari_servicii.ro.restored.txt").read_text(encoding="utf-8")
    assert "Ion Popescu" in restored and "[PERSON_" not in restored

    code, out = cli("entities", "-m", "demo", "--json")
    assert any(e["id"] == "[PERSON_001]" and e["text"] == "Ion Popescu" for e in json.loads(out))

    code, out = cli("alias", "PERSON_002", "dna Ionescu", "-m", "demo")
    assert code == 0 and "another name" in out
    code, out = cli("verify", SAMPLES / TXT[0], "-m", "demo")
    assert code == 1 and "LEAK" in out  # an original file is not clean


def test_cli_errors(cli, tmp_path):
    with pytest.raises(SystemExit, match="File not found"):
        cli("anonymize", tmp_path / "missing.txt", "-m", "x")
    old_format = tmp_path / "a.doc"
    old_format.write_bytes(b"\xd0\xcf\x11\xe0")
    with pytest.raises(SystemExit, match="not supported"):
        cli("anonymize", old_format, "-m", "x")
    broken = tmp_path / "a.pdf"
    broken.write_bytes(b"%PDF")
    with pytest.raises(SystemExit, match="cannot be read"):
        cli("anonymize", broken, "-m", "x")
    with pytest.raises(SystemExit, match="Bad matter name"):
        cli("entities", "-m", "../etc")
    with pytest.raises(SystemExit, match="unknown id"):
        cli("alias", "PERSON_001", "x y", "-m", "x")
