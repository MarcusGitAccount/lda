"""Run the whole pipeline on the synthetic Romanian set (eval/synth_ro.py) and report what the public sets do not:

* mention recall and the recall of each hard-case class,
* entity recall: every mention of one entity is hidden,
* document leak rate: documents that have at least one visible mention,
* false joins (two gold entities with one id; the target is 0), and extra ids (one entity, two ids),
* words that must stay visible but were hidden (over-hiding),
* restore: exact text back, text back apart from the form of the word, ids left in the file (silent failures).

    python -m eval.synth_eval --level medium --name medium+my-change

There is no seed list: the tool must find every party by itself. The gold comes from the generator.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

from eval import tracker
from eval.metrics import Counts
from eval.synth_ro import Doc, build_set
from legal_anonymizer.config import LEVELS, Settings
from legal_anonymizer.detector import Detector
from legal_anonymizer.engine import Engine
from legal_anonymizer.textnorm import collapse, fold
from legal_anonymizer.vault import Vault


def covered(doc_length: int, spans) -> list[bool]:
    mask = [False] * doc_length
    for span in spans:
        for i in range(max(0, span.start), min(doc_length, span.end)):
            mask[i] = True
    return mask


def run(settings: Settings, detector: Detector, docs: list[Doc]) -> dict:
    by_case: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # case -> [hidden, total]
    hidden = total = over = over_total = 0
    entities: dict[tuple[str, str], bool] = {}
    leaking_docs: set[str] = set()
    false_joins: list[str] = []
    extra_ids = 0
    restored_exact = restored_loose = silent = 0
    missed: list[tuple[str, str, str]] = []  # (case, entity, surface)
    matters = sorted({d.matter for d in docs})
    for matter in matters:
        group = [d for d in docs if d.matter == matter]
        with tempfile.TemporaryDirectory() as tmp, Vault(Path(tmp) / "v.db") as vault:
            engine = Engine(vault, settings, detector)
            results = engine.anonymize_many([(d.name, d.text.encode()) for d in group])
            placeholder_gold: dict[str, set[str]] = defaultdict(set)
            gold_placeholders: dict[str, set[str]] = defaultdict(set)
            for doc, result in zip(group, results):
                mask = covered(len(doc.text), result.spans)
                for mention in doc.mentions:
                    ok = all(mask[mention.start : mention.end])
                    if mention.kind == "stay":
                        over_total += 1
                        over += any(mask[mention.start : mention.end])
                        continue
                    total += 1
                    hidden += ok
                    by_case[mention.case][0] += ok
                    by_case[mention.case][1] += 1
                    key = (matter, mention.entity)
                    entities[key] = entities.get(key, True) and ok
                    if not ok:
                        leaking_docs.add(doc.name)
                        missed.append((mention.case, mention.entity, doc.text[mention.start : mention.end]))
                        continue
                    span = next(s for s in result.spans if s.start <= mention.start < s.end)
                    entity = vault.resolve(span.type, collapse(doc.text[span.start : span.end]), count=0)
                    placeholder_gold[entity.placeholder].add(mention.entity)
                    gold_placeholders[mention.entity].add(entity.placeholder)
                restored = engine.restore(doc.name.replace(".txt", ".anon.txt"), result.data)
                text = restored.data.decode()
                restored_exact += text == doc.text
                restored_loose += fold(text) == fold(doc.text)
                silent += bool(restored.unknown or getattr(restored, 'suspect', []))
            false_joins += [f"{matter}:{p}={sorted(g)}" for p, g in placeholder_gold.items() if len(g) > 1]
            extra_ids += sum(len(p) - 1 for p in gold_placeholders.values())
    counts = Counts(tp=hidden, fn=total - hidden, fp=over)  # no precision is measured here: only the "stay" words count
    return {
        "mentions": counts.as_dict(),
        "entity_recall": sum(entities.values()) / len(entities),
        "documents": {"total": len(docs), "leaking": len(leaking_docs)},
        "false_joins": len(false_joins),
        "false_join_list": false_joins,
        "extra_ids": extra_ids,
        "over_hidden": {"words": over, "of": over_total},
        "restore": {"exact": restored_exact, "same_apart_from_form": restored_loose, "documents": len(docs), "ids_left_in_file": silent},
        "by_case": {case: {"hidden": h, "total": n, "recall": round(h / n, 3)} for case, (h, n) in sorted(by_case.items())},
        "missed": [list(item) for item in missed],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", choices=sorted(LEVELS), default="low")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--matters", type=int, default=6)
    ap.add_argument("--llm-model")
    ap.add_argument("--name", help="name of the experiment, for the result file (default: the level)")
    ap.add_argument("--no-record", action="store_true")
    args = ap.parse_args()

    settings = Settings()
    settings.level = args.level
    if args.llm_model:
        settings.llm_model = args.llm_model
    settings.validate()
    docs = build_set(args.seed, args.matters)
    detector = Detector(settings)
    detector.warm_up()  # models load before the clock starts
    started = time.time()
    metrics = run(settings, detector, docs)
    elapsed = time.time() - started

    m = metrics
    print(f"synth-ro level={settings.level} documents={len(docs)} seed={args.seed} time={elapsed:.0f}s")
    print(f"mention recall  {m['mentions']['tp']}/{m['mentions']['tp'] + m['mentions']['fn']} = {m['mentions']['recall']:.3f}")
    print(f"entity recall   {m['entity_recall']:.3f}   (every mention of the entity is hidden)")
    print(f"documents with a visible mention: {m['documents']['leaking']} of {m['documents']['total']}")
    print(f"false joins: {m['false_joins']} {m['false_join_list']}   extra ids: {m['extra_ids']}   over-hidden: {m['over_hidden']['words']} of {m['over_hidden']['of']}")
    r = m["restore"]
    print(f"restore: exact {r['exact']}/{r['documents']}, same apart from the form {r['same_apart_from_form']}/{r['documents']}, ids left in file {r['ids_left_in_file']}")
    for case, v in m["by_case"].items():
        print(f"  {case:32} {v['hidden']:3}/{v['total']:<3} {v['recall']:.2f}")
    if not args.no_record:
        path = tracker.record("synth-ro", args.name or settings.level, settings, metrics, elapsed, {"seed": args.seed})
        print(f"saved {path.relative_to(tracker.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
