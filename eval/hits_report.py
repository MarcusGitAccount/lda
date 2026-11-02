"""What does the tool hide in a folder of documents that has no gold list?

    python -m eval.hits_report eval/corpora/ro-law --level medium --name ro-law-medium

There is no recall here: without a gold list we cannot say what was missed. The report gives the number of hits for each
1,000 words and the most common hidden strings. Read the list: a string that is not sensitive is a false hit (the tool
hides too much); a person in the text that is not in the list is a probable miss. Use it on public text only: the strings
are written to `<folder>/_review/<name>.json`, and to the screen.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

from eval import tracker
from legal_anonymizer.config import LEVELS, Settings, load_settings
from legal_anonymizer.detector import Detector
from legal_anonymizer.documents import TEXT_SUFFIXES, open_document, scan_text
from legal_anonymizer.engine import Engine
from legal_anonymizer.textnorm import collapse
from legal_anonymizer.vault import Vault

SUFFIXES = {*TEXT_SUFFIXES, ".docx", ".pdf"}
TOP = 40


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--level", choices=sorted(LEVELS), default="low")
    ap.add_argument("--llm-model")
    ap.add_argument("--hide", help="comma list of types, for example PERSON,ORGANIZATION,DATE_TIME,JOB_TITLE")
    ap.add_argument("--public", action="store_true", help="keep_public_bodies=true")
    ap.add_argument("--name", help="name for the result file (default: the level)")
    ap.add_argument("--no-record", action="store_true")
    args = ap.parse_args()

    folder = args.folder.resolve()
    matter = folder / "matter.yaml"
    settings = load_settings(matter, hide=args.hide.split(",") if args.hide else None) if matter.exists() else Settings()
    if args.hide and not matter.exists():
        settings.hide = set(args.hide.split(","))
    settings.level = args.level
    settings.keep_public_bodies = settings.keep_public_bodies or args.public
    if args.llm_model:
        settings.llm_model = args.llm_model
    settings.validate()

    names = sorted(p.name for p in folder.iterdir() if p.suffix.lower() in SUFFIXES)
    files = [(n, (folder / n).read_bytes()) for n in names]
    detector = Detector(settings)
    detector.warm_up()
    started = time.time()
    by_type: Counter = Counter()
    strings: dict[str, Counter] = defaultdict(Counter)
    with tempfile.TemporaryDirectory() as tmp, Vault(Path(tmp) / "hits.db") as vault:
        engine = Engine(vault, settings, detector)
        results = engine.anonymize_many(files)
        for (name, data), result in zip(files, results):
            text = "\n".join(open_document(name, data).units())
            for span in result.spans:
                by_type[span.type] += 1
                strings[span.type][collapse(text[span.start : span.end])] += 1
    elapsed = time.time() - started
    n_words = sum(len(scan_text(n, d).split()) for n, d in files)
    total = sum(by_type.values())

    print(f"folder={folder.name} level={settings.level} documents={len(files)} words={n_words} time={elapsed:.0f}s")
    print(f"hits {total}  = {1000 * total / max(n_words, 1):.1f} for each 1,000 words")
    for kind, n in by_type.most_common():
        print(f"\n{kind}: {n} hits ({1000 * n / max(n_words, 1):.1f} for each 1,000 words), {len(strings[kind])} different strings")
        for text, count in strings[kind].most_common(TOP):
            print(f"  {count:4}  {text}")

    review = folder / "_review"
    review.mkdir(exist_ok=True)
    name = args.name or settings.level
    (review / f"hits-{name}.json").write_text(
        json.dumps({kind: dict(c.most_common(300)) for kind, c in strings.items()}, indent=1, ensure_ascii=False),
        encoding="utf-8",
    )
    metrics = {
        "documents": len(files),
        "words": n_words,
        "hits": total,
        "hits_per_1000_words": round(1000 * total / max(n_words, 1), 2),
        "by_type": dict(by_type),
        "different_strings": {k: len(v) for k, v in strings.items()},
        "words_per_second": round(n_words / elapsed, 1) if elapsed else None,
    }
    if not args.no_record:
        print("saved", tracker.record(f"hits-{folder.name}", name, settings, metrics, elapsed).relative_to(tracker.ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
