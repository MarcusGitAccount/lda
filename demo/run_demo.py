"""Run the whole demo on the five PDFs in data/demo/.

    python -m demo.run_demo                      # all steps, no wait
    python -m demo.run_demo --pause              # wait for Enter before each step (live demo)
    python -m demo.run_demo --revised FILE.txt   # use the text from a real AI tool in step 5

The steps: hide the data, show what the AI tool gets, check the output, let an AI tool (or a
simulation) change the contract, and put the real data back. Everything goes to demo-output/.
The vault in demo-output/vault has the real data. It stays on this computer.
"""

from __future__ import annotations

import argparse
import contextlib
import difflib
import io
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "demo"
OUT = ROOT / "demo-output"
MARKER = OUT / ".made-by-the-demo"  # we delete demo-output only if the demo made it

CLIENT = "Mureșul Agro Trans S.R.L."
OTHER_SIDE = "Carpatica Logistic Solutions S.A."
CONTRACT = "01_contract_transport.ro"


def say(text: str = "") -> None:
    print(text, flush=True)


def step(number: int, title: str, pause: bool) -> None:
    if pause:
        input("\n[Enter] to go on ")
    say(f"\n{'=' * 78}\nSTEP {number}: {title}\n{'=' * 78}")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def lda(*args: str, quiet: bool = False) -> str:
    """Run one `lda` command in this process. Show it like a user would type it."""
    from legal_anonymizer.cli import main

    say("\n$ lda " + " ".join(args))
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = main(list(args))
    output = buffer.getvalue()
    if not quiet:
        say(output.rstrip())
    if code:
        say(f"(exit code {code})")
    return output


def excerpt(text: str, start: str, lines: int) -> str:
    i = text.index(start)
    return "\n".join(text[i:].splitlines()[:lines])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pause", action="store_true", help="wait for Enter before each step")
    parser.add_argument("--revised", type=Path, help="text from a real AI tool, to use in place of the simulation")
    args = parser.parse_args()

    if OUT.exists():
        if not MARKER.exists():
            sys.exit(f"{rel(OUT)} exists, and the demo did not make it. Move it away and run again.")
        shutil.rmtree(OUT)
    OUT.mkdir()
    MARKER.touch()
    os.environ["LDA_HOME"] = str(OUT / "vault")

    pdfs = sorted(DATA.glob("*.pdf"))
    if not pdfs:
        sys.exit("No PDF in data/demo/. Make them with: python -m demo.build")
    from legal_anonymizer.pdftext import pdf_text

    from .render_pdf import language_of, render

    # --- 1 -----------------------------------------------------------------
    step(1, "The documents of the case (PDF, Romanian and English)", args.pause)
    for pdf in pdfs:
        pages = len(re.findall(rb"/Type\s*/Page\b", pdf.read_bytes()))
        say(f"  {pdf.name:48} {pages} pages, {len(pdf_text(pdf.read_bytes()).split())} words")
    say("\nThe start of the contract, as the tool reads it:\n")
    say("\n".join(pdf_text(pdfs[0].read_bytes()).splitlines()[:14]) + "\n  ...")

    # --- 2 -----------------------------------------------------------------
    step(2, "Hide the sensitive data. One command for all documents of the case", args.pause)
    hidden = OUT / "hidden"
    files = [rel(p) for p in pdfs]
    lda("anonymize", *files, "--matter", "demo", "--config", rel(DATA / "matter.yaml"), "--out", rel(hidden))
    say("\nPDF copies of the hidden files, for people to read (the AI tool gets the .txt files):")
    for txt in sorted(hidden.glob("*.txt")):
        render(txt.read_text(encoding="utf-8"), txt.with_suffix(".pdf"), language=language_of(txt.name))
        say(f"  {rel(txt.with_suffix('.pdf'))}")

    # --- 3 -----------------------------------------------------------------
    step(3, "What the AI tool gets", args.pause)
    hidden_contract = (hidden / f"{CONTRACT}.anon.txt").read_text(encoding="utf-8")
    say(excerpt(hidden_contract, "1. [ORG_", 4))
    say("  ...")
    claim = (hidden / "03_cerere_chemare_in_judecata.ro.anon.txt").read_text(encoding="utf-8")
    say(excerpt(claim, "Reclamantă:", 1)[:700] + " ...")
    say("\nThe court stays visible (keep_public_bodies). Amounts, dates and article numbers stay visible too.")

    # --- 4 -----------------------------------------------------------------
    step(4, "One entity has one id in all documents", args.pause)
    entities = json.loads(lda("entities", "--matter", "demo", "--json", quiet=True))
    say("\nThe main entities (this list has real data. It stays on this computer):")
    for e in entities:
        if e["id"].startswith(("[ORG_", "[PERSON_", "[CUI_")) and len(e["documents"]) >= 4:
            say(f"  {e['id']:15} {e['text'][:44]:44} in {len(e['documents'])} of {len(pdfs)} documents")
    say("\nThe checks of the tool:")
    lda("verify", *[rel(p) for p in sorted(hidden.glob("*.txt"))], "--matter", "demo")

    # --- 5 -----------------------------------------------------------------
    step(5, "An AI tool changes the contract (here: a simulation, with the same rules)", args.pause)
    ids = {e["text"]: e["id"] for e in entities}
    client, other = ids[CLIENT], ids[OTHER_SIDE]
    target = OUT / "ai" / f"{CONTRACT}.anon.txt"
    target.parent.mkdir()
    if args.revised:
        revised = args.revised.read_text(encoding="utf-8")
        say(f"Using the text from {args.revised}.")
    else:
        revised = hidden_contract.replace("0,5% pe zi de întârziere", "0,7% pe zi de întârziere")
        revised = revised.replace("20% din această valoare", "25% din această valoare")
        new_clause = (
            f"15.4. {other} transmite {client}, în termen de 5 zile lucrătoare de la fiecare întârziere, un raport scris "
            f"cu cauza întârzierii. Dacă {other} nu transmite raportul, {client} poate cere o penalitate de 500 lei pentru fiecare raport lipsă."
        )
        revised = re.sub(r"(\n15\.3\. [^\n]+)", lambda m: m.group(1) + "\n\n" + new_clause, revised, count=1)
        say("In real use, you give the hidden file to Claude Code, Codex or Copilot.")
        say(f"The prompt is in {rel(DATA / 'ai_prompt.md')}. This simulation changes two figures and adds a clause.")
    target.write_text(revised, encoding="utf-8")
    old_blocks = {b.strip() for b in re.split(r"\n\s*\n", hidden_contract)}
    changed = {b.strip() for b in re.split(r"\n\s*\n", revised) if b.strip() not in old_blocks}
    render(revised, target.with_suffix(".pdf"), language="ro", changed=changed)
    say(f"PDF copy, with the changed paragraphs in green: {rel(target.with_suffix('.pdf'))}")
    say("\nWhat changed:\n")
    for line in difflib.unified_diff(hidden_contract.splitlines(), revised.splitlines(), "hidden", "revised by the AI tool", lineterm="", n=0):
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
            say(("  " + line)[:400])

    # --- 6 -----------------------------------------------------------------
    step(6, "Put the real data back, then give the document to the client", args.pause)
    final = OUT / "final"
    lda("restore", rel(target), "--matter", "demo", "--out", rel(final))
    restored = (final / f"{CONTRACT}.restored.txt").read_text(encoding="utf-8")
    render(restored, final / f"{CONTRACT}.restored.pdf", restored=True, language="ro")
    say(f"PDF copy for the client: {rel(final / f'{CONTRACT}.restored.pdf')}")
    say("\nThe new clause, with the real names:\n")
    say(excerpt(restored, "15.4.", 1))
    say("\nThe changed figure:\n")
    say("  " + next(line for line in restored.splitlines() if "0,7%" in line)[:400])

    # --- 7 -----------------------------------------------------------------
    step(7, "Two written forms of one company? Join them. Old documents still restore", args.pause)
    by_text = {e["text"]: e["id"] for e in entities}
    full, short = by_text.get("FreshMart Distribuție S.R.L."), by_text.get("FreshMart Distribuție")
    if full and short:
        say(f"'FreshMart Distribuție S.R.L.' is {full} and 'FreshMart Distribuție' is {short}.")
        say("The tool does not guess, because a wrong join puts a wrong name in a legal document.")
        lda("merge", short.strip("[]"), full.strip("[]"), "--matter", "demo")
    else:
        say("(nothing to join in this run)")
    say(f"\nDone. The files are in {rel(OUT)}/ (hidden/, ai/, final/), as text and as PDF. The vault is in {rel(OUT / 'vault')}/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
