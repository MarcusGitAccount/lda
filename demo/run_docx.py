"""Make the Word demo. Run it from the project folder:  python -m demo.run_docx

The files go to demo-docx/. There are two cases, and each case has three folders:

    single-file/   one document (the transport contract)
    multi-file/    five documents (four Romanian, one English), hidden together

    1-original/    the Word files as the lawyer has them
    2-anonymized/  what the lawyer gives to the AI tool: the same files, with ids in place of the data
    3-restored/    the files after the AI tool changed them and the tool put the real data back

The AI tool is a simulation (demo/docx_edit.py). It makes tracked changes by "AI assistant" in some of
the anonymized files. The new text has ids, and the restored files have the real names in it.
demo-docx/_work/ has the vault (the real data, it stays on this computer) and the files of the AI step.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from . import case as c
from . import docx_layout, kit, layout
from .build import DOCUMENTS
from .docx_edit import Redline

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "demo"
OUT = ROOT / "demo-docx"
MARKER = OUT / ".made-by-the-demo"  # we delete demo-docx only if the demo made it

CASES = {"single-file": 1, "multi-file": len(DOCUMENTS)}  # the number of documents (the first ones)


def language_of(name: str) -> str:
    return "en" if ".en." in name else "ro"


def build_originals(folder: Path, count: int) -> dict[str, bytes]:
    """Write the first `count` demo documents as .docx files. Return name -> bytes."""
    folder.mkdir(parents=True)
    kit.use(docx_layout)
    try:
        files = {}
        for pdf_name, factory in DOCUMENTS[:count]:
            name = pdf_name.removesuffix(".pdf") + ".docx"
            story, meta = factory()
            docx_layout.build(folder / name, story, meta, language_of(name))
            files[name] = (folder / name).read_bytes()
        return files
    finally:
        kit.use(layout)


def ai_edit(name: str, data: bytes, ids: dict[str, str]) -> bytes | None:
    """The simulated AI tool. It works on the anonymized file, so it only knows the ids."""
    if not name.startswith(("01_", "02_", "05_")):
        return None  # these documents stay as they are
    client, other, uk = ids[c.CLIENT_MIXED], ids[c.DEF_MIXED], ids[c.UK]
    redline = Redline(data)
    if name.startswith("01_"):  # the contract: two figures and a new clause
        redline.replace("0,5%", "0,7%", in_paragraph="Pentru întârzierea livrării")
        redline.replace("20%", "25%", in_paragraph="Pentru întârzierea livrării")
        redline.insert_paragraph_after(
            "Prezentul contract s-a încheiat în două exemplare",
            f"{other} transmite {client}, în termen de 5 zile lucrătoare de la fiecare întârziere, un raport scris cu cauza "
            f"întârzierii. Dacă {other} nu transmite raportul, {client} poate cere o penalitate de 500 lei pentru fiecare raport lipsă.",
            label="15.4.",
        )
    elif name.startswith("02_"):  # the notice: one new paragraph
        redline.insert_paragraph_after(
            "Dacă nu plătiți sumele de mai sus",
            f"Vă atragem atenția că {other} datorează dobânda legală penalizatoare pentru fiecare zi de întârziere la plata sumelor "
            f"de mai sus, iar {client} își rezervă toate drepturile.",
        )
    else:  # the settlement (05_): a shorter time to pay and a new clause
        redline.replace("14 days", "10 days", in_paragraph="shall pay the Settlement Sum to the Exporter within")
        redline.insert_paragraph_after(
            "The Exporter shall send a copy of the invoice",
            f"{uk} shall send {client} written confirmation of the payment on the day on which it makes the payment.",
            label="2.4",
        )
    return redline.save()


def run_case(case: str, count: int, detector, settings) -> str:
    from legal_anonymizer.cli import output_name
    from legal_anonymizer.engine import Engine
    from legal_anonymizer.vault import Vault

    root = OUT / case
    anonymized, restored, edited = root / "2-anonymized", root / "3-restored", OUT / "_work" / case / "ai-edited"
    originals = build_originals(root / "1-original", count)
    for folder in (anonymized, restored, edited):
        folder.mkdir(parents=True)
    (OUT / "_work" / "vault").mkdir(parents=True, exist_ok=True)

    warnings = []
    with Vault(OUT / "_work" / "vault" / f"{case}.db") as vault:
        engine = Engine(vault, settings, detector)
        engine.load_seeds()
        results = engine.anonymize_many(list(originals.items()))
        ids = {e.canonical: e.placeholder for e in vault.entities()}
        for (name, _), result in zip(originals.items(), results):
            hidden_name = output_name(name, "anon")
            (anonymized / hidden_name).write_bytes(result.data)
            if result.leaks:
                warnings.append(f"{hidden_name}: text of {', '.join(result.leaks)} is still in the file")
            data = ai_edit(name, result.data, ids)
            if data is not None:
                (edited / hidden_name).write_bytes(data)
            back = engine.restore(hidden_name, data or result.data)
            if back.unknown:
                warnings.append(f"{hidden_name}: unknown ids {', '.join(back.unknown)}")
            (restored / output_name(hidden_name, "restored")).write_bytes(back.data)
    shown = root.relative_to(ROOT) if root.is_relative_to(ROOT) else root
    line = f"{case}: {len(originals)} file(s) in {shown}/ (1-original, 2-anonymized, 3-restored)"
    return "\n".join([line, *[f"  WARNING {w}" for w in warnings]])


def main() -> int:
    if OUT.exists():
        if not MARKER.exists():
            sys.exit(f"{OUT.relative_to(ROOT)} exists, and the demo did not make it. Move it away and run again.")
        shutil.rmtree(OUT)
    OUT.mkdir()
    MARKER.touch()

    from legal_anonymizer.config import load_settings
    from legal_anonymizer.detector import Detector

    settings = load_settings(DATA / "matter.yaml")
    detector = Detector(settings)  # the models load one time, for both cases
    for case, count in CASES.items():
        print(run_case(case, count, detector, settings), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
