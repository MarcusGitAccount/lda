"""Measure the whole pipeline on a folder of documents.

    python -m eval.corpus_eval data/demo --level medium --name bert+gliner

The folder has the documents (.txt, .md, .docx, .pdf), a `gold.json`, and optionally a
`matter.yaml` (known entities, words to keep). `gold.json` lists the sensitive entities. It does
not list offsets: every written form of an entity is searched in every document, so a lawyer can
write it down without a tool.

    {
      "entities": [
        {"type": "ORGANIZATION", "forms": ["Mureșul Agro Trans S.R.L.", "Mureșul Agro Trans"]},
        {"type": "PERSON", "forms": ["Anca-Maria Rusu", "Rusu Anca-Maria"]}
      ],
      "documents": ["01_contract.docx"],   # optional: the files to use (default: all supported files in the folder)
      "must_hide": ["RO-2025-0417"],       # optional: one entity for each string
      "must_keep": ["PRESTATOR"],          # words that must stay visible
      "visible_ok": ["Tribunalul Mureș"]   # text that the policy keeps. It is not a leak.
    }

The run does the real work: it hides all documents together, and it restores each one. It measures:

  * mention recall    gold mentions that the tool hides completely. A miss is a leak. This is the number that decides.
  * precision, F1, F2 spans that the tool hides and that touch no gold mention are false hits. F2 counts recall twice.
                      The gold list can be incomplete, so the false hits are written to a review file.
  * consistency       one gold entity must have one id in all documents (split), and one id must not belong
                      to two entities (merge). A merge corrupts the restored text.
  * leaked forms      gold forms that the output file still has (the check by text, not by offsets).
  * restore           share of the words that come back as in the original (the short forms of a name come back long).

Review files go to <folder>/_review/. They have real text, so they stay on this computer.
The result file in eval/results/ has only counts.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from eval import tracker
from eval.metrics import Counts
from legal_anonymizer.cli import output_name
from legal_anonymizer.config import LEVELS, Settings, load_settings
from legal_anonymizer.detector import Detector
from legal_anonymizer.documents import TEXT_SUFFIXES, open_document, scan_text
from legal_anonymizer.engine import Engine
from legal_anonymizer.spans import TITLES
from legal_anonymizer.textnorm import collapse, fold
from legal_anonymizer.vault import Vault

SUFFIXES = {*TEXT_SUFFIXES, ".docx", ".pdf"}


@dataclass
class Mention:
    entity: int
    start: int
    end: int


@dataclass
class GoldEntity:
    type: str
    forms: list[str]


def load_gold(folder: Path) -> tuple[list[GoldEntity], dict]:
    raw = json.loads((folder / "gold.json").read_text(encoding="utf-8"))
    entities = [GoldEntity(e.get("type", "ANY"), list(e["forms"])) for e in raw.get("entities", [])]
    entities += [GoldEntity("ANY", [form]) for form in raw.get("must_hide", [])]
    return entities, raw


_TITLE_AT_START = re.compile(r"(\S+)\s+")


def without_title(text: str, start: int, end: int) -> int:
    """The tool leaves a title ("Mr", "dl.") visible on purpose, so it is not a part of the gold mention."""
    while match := _TITLE_AT_START.match(text, start, end):
        if fold(match.group(1)).strip(".") not in TITLES:
            break
        start = match.end()
    return start


def project(text: str, entities: list[GoldEntity]) -> list[Mention]:
    """Find every written form of every entity. The longest form wins where two forms overlap."""
    found = []
    for index, entity in enumerate(entities):
        for form in entity.forms:
            pattern = re.escape(collapse(form)).replace(r"\ ", r"\s+")
            for match in re.finditer(rf"(?<!\w){pattern}(?!\w)", text, re.IGNORECASE):
                start = without_title(text, match.start(), match.end())
                if start < match.end():
                    found.append(Mention(index, start, match.end()))
    found.sort(key=lambda m: (-(m.end - m.start), m.start))
    chosen: list[Mention] = []
    for mention in found:
        if not any(mention.start < c.end and c.start < mention.end for c in chosen):
            chosen.append(mention)
    return sorted(chosen, key=lambda m: m.start)


def covered(text: str, start: int, end: int, spans) -> bool:
    """True if the spans together cover every letter and digit of [start, end). The final dot of "S.R.L." may stay."""
    need = {i for i in range(start, end) if text[i].isalnum()}
    for s in spans:
        need -= set(range(max(s.start, start), min(s.end, end)))
    return not need


def context_of(text: str, start: int, end: int, width: int = 40) -> str:
    return text[max(0, start - width) : end + width].replace("\n", " ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--level", choices=sorted(LEVELS), default="low")
    ap.add_argument("--gliner-model")
    ap.add_argument("--gliner-threshold", type=float)
    ap.add_argument("--llm-model")
    ap.add_argument("--name", help="name of the experiment, for the result file (default: the level)")
    ap.add_argument("--public", action="store_true", help="keep_public_bodies=true: courts and ministries stay visible")
    ap.add_argument("--no-record", action="store_true")
    args = ap.parse_args()

    folder = args.folder.resolve()
    matter = folder / "matter.yaml"
    settings = load_settings(matter) if matter.exists() else Settings()
    settings.level = args.level
    if args.public:
        settings.keep_public_bodies = True
    if args.gliner_model:
        settings.gliner_model = args.gliner_model
    if args.gliner_threshold is not None:
        settings.gliner_threshold = args.gliner_threshold
    if args.llm_model:
        settings.llm_model = args.llm_model
    settings.validate()

    entities, raw = load_gold(folder)
    grouped = bool(raw.get("entities"))  # a flat must_hide list cannot say which forms are one entity
    names = raw.get("documents") or sorted(p.name for p in folder.iterdir() if p.suffix.lower() in SUFFIXES)
    files = [(n, (folder / n).read_bytes()) for n in names]

    detector = Detector(settings)
    detector.warm_up()  # models load before the clock starts
    started = time.time()
    counts = Counts()
    by_type: dict[str, Counts] = defaultdict(Counts)
    split: dict[int, set[str]] = defaultdict(set)  # gold entity -> placeholders
    owners: dict[str, set[int]] = defaultdict(set)  # placeholder -> gold entities
    review: dict[str, dict] = {}
    restore_scores: list[float] = []
    leaked, missing_keep = [], []

    with tempfile.TemporaryDirectory() as tmp, Vault(Path(tmp) / "eval.db") as vault:
        engine = Engine(vault, settings, detector)
        engine.load_seeds()
        results = engine.anonymize_many(files)
        for (name, data), result in zip(files, results):
            units = open_document(name, data).units()
            text = "\n".join(units)
            mentions = project(text, entities)
            misses, false_hits = [], []
            for m in mentions:
                gold_type = entities[m.entity].type
                if covered(text, m.start, m.end, result.spans):
                    counts.tp += 1
                    by_type[gold_type].tp += 1
                    for s in result.spans:
                        if s.start < m.end and m.start < s.end:
                            entity = vault.resolve(s.type, collapse(text[s.start : s.end]), count=0)
                            split[m.entity].add(entity.placeholder)
                            owners[entity.placeholder].add(m.entity)
                else:
                    counts.fn += 1
                    by_type[gold_type].fn += 1
                    misses.append({"gold": text[m.start : m.end], "type": gold_type, "context": context_of(text, m.start, m.end)})
            for s in result.spans:
                if not any(s.start < m.end and m.start < s.end for m in mentions):
                    counts.fp += 1
                    false_hits.append({"hidden": text[s.start : s.end], "type": s.type, "source": s.source, "context": context_of(text, s.start, s.end)})

            # The check by text on the output file, like the tests of the demo.
            output = fold(scan_text(name, result.data))
            for phrase in raw.get("visible_ok", []):
                output = output.replace(fold(phrase), " ")
            leaked += [(name, f) for e in entities for f in e.forms if fold(f) in output and len(f) > 3]
            missing_keep += [(name, k) for k in raw.get("must_keep", []) if fold(k) in fold(text) and fold(k) not in output]

            hidden_name = output_name(name, "anon")
            back = engine.restore(hidden_name, result.data)
            after = "\n".join(open_document(output_name(name, "restored"), back.data).units())
            restore_scores.append(
                difflib.SequenceMatcher(None, text.split(), after.split(), autojunk=False).ratio()
            )
            review[name] = {"misses": misses, "false_hits": false_hits}

    elapsed = time.time() - started
    words = sum(len(scan_text(n, d).split()) for n, d in files)
    merges = sorted(p for p, who in owners.items() if len(who) > 1)
    splits = sorted(i for i, ids in split.items() if len(ids) > 1)
    seen = len(split)

    print(f"folder={folder.name} level={settings.level} public bodies {'kept' if settings.keep_public_bodies else 'hidden'} documents={len(files)} words={words} gold entities={len(entities)} time={elapsed:.0f}s")
    print(f"mention recall   {counts.tp}/{counts.tp + counts.fn} = {counts.recall:.3f}      (leaks: {counts.fn})")
    print(f"precision        {counts.precision:.3f}   ({counts.fp} false hits to review)")
    print(f"F1 {counts.f(1):.3f}   F2 {counts.f(2):.3f}")
    for gold_type, c in sorted(by_type.items()):
        print(f"  {gold_type:14} recall {c.recall:.3f}  ({c.tp}/{c.tp + c.fn})")
    if grouped:
        print(f"consistency      split entities {len(splits)}/{seen}   merged ids {len(merges)}")
    else:
        print("consistency      not measured: the gold list is flat (no groups of forms)")
    print(f"leaked forms     {len(leaked)}   must_keep missing {len(missing_keep)}")
    restore_ok = sum(restore_scores) / max(len(restore_scores), 1)
    print(f"restore          {restore_ok:.1%} of the words come back as in the original (mean of {len(restore_scores)} documents)")

    review_dir = folder / "_review"
    review_dir.mkdir(exist_ok=True)
    name = args.name or settings.level
    (review_dir / f"{name}.json").write_text(
        json.dumps(
            {
                "split": [entities[i].forms for i in splits],
                "merged": {p: [entities[i].forms[0] for i in owners[p]] for p in merges},
                "leaked_forms": leaked,
                "documents": review,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"review file      {review_dir.relative_to(folder.parent)}/{name}.json (real text: keep it on this computer)")

    metrics = {
        "documents": len(files),
        "words": words,
        "gold_entities": len(entities),
        "mentions": counts.as_dict(),
        "by_gold_type": {t: c.as_dict() for t, c in sorted(by_type.items())},
        "split_entities": len(splits) if grouped else None,
        "entities_seen": seen if grouped else None,
        "merged_ids": len(merges) if grouped else None,
        "leaked_forms": len(leaked),
        "must_keep_missing": len(missing_keep),
        "restore_words_equal": round(restore_ok, 4),
        "words_per_second": round(words / elapsed, 1) if elapsed else None,
    }
    if settings.use_llm:
        checker = detector.checker(settings)  # the gain of the LLM is the difference to the run at level medium
        metrics["llm"] = {
            "model": settings.llm_model,
            "requests": checker.requests,
            "invalid_replies": checker.invalid,
            "skipped_pieces": checker.skipped,
            "structured_output": checker.structured,
        }
        print(f"llm {settings.llm_model}: requests={checker.requests} invalid replies={checker.invalid}")
    if not args.no_record:
        path = tracker.record(f"corpus-{folder.name}", name, settings, metrics, elapsed)
        print(f"saved {path.relative_to(tracker.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
