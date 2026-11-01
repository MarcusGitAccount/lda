"""Make an English test corpus from TAB (Text Anonymization Benchmark): real ECHR court cases.

TAB: https://github.com/NorskRegnesentral/text-anonymization-benchmark (MIT license).
Download echr_test.json into eval/tab_raw/ (see the README), then run:

    python -m eval.tab_corpus --count 12
    python -m eval.corpus_eval eval/corpora/tab-en --level medium --name bert+gliner

The output has the documents (.txt) and a gold.json in the format of eval/corpus_eval.py.
We take the cases at fixed steps, so two runs give the same documents.

What goes into the gold list:
  * a mention that TAB marks as DIRECT or QUASI identifier (TAB masks these two kinds),
  * of the types that the default policy of the tool hides: PERSON, ORG, LOC and CODE (case numbers,
    application numbers). TAB also has DATETIME, QUANTITY, DEM (nationality, occupation) and MISC.
    The tool does not hide these by default, so they are not in the list,
  * without the words that the policy keeps visible on purpose (for example "Turkey").
TAB masks courts and governments of a country ("High Court of Western Denmark") but not the ECHR itself. The tool
hides all public bodies by default, and that is the policy we measure. With --public the tool keeps them visible,
and then these gold mentions count as misses. Compare precision and recall of two runs only with the same policy.
All mentions of one entity are written as the forms of one entity, so the test can see if the
tool gives the same id to "Mr Yalman" and "Galip Yalman".
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from legal_anonymizer.spans import generic_key, keep_set
from legal_anonymizer.textnorm import collapse

HERE = Path(__file__).parent
RAW = HERE / "tab_raw" / "echr_test.json"
OUT = HERE / "corpora" / "tab-en"
MARKER = OUT / ".made-by-tab-corpus"

TYPE_MAP = {"PERSON": "PERSON", "ORG": "ORGANIZATION", "LOC": "LOCATION", "CODE": "CODE"}
MIN_WORDS, MAX_WORDS = 1500, 4500  # a case of this size is like a long contract


def pick(documents: list[dict], count: int) -> list[dict]:
    fitting = sorted(
        (d for d in documents if MIN_WORDS <= len(d["text"].split()) <= MAX_WORDS), key=lambda d: d["doc_id"]
    )
    if len(fitting) <= count:
        return fitting
    step = len(fitting) / count
    return [fitting[int(i * step)] for i in range(count)]


def gold_entities(document: dict, keep: set[str]) -> list[dict]:
    forms: dict[str, tuple[str, set[str]]] = {}
    for annotation in document["annotations"].values():
        for mention in annotation["entity_mentions"]:
            kind = TYPE_MAP.get(mention["entity_type"])
            if kind is None or mention["identifier_type"] not in {"DIRECT", "QUASI"}:
                continue
            form = collapse(mention["span_text"])
            if len(form) < 3 or generic_key(form) in keep:
                continue
            entity = forms.setdefault(mention["entity_id"], (kind, set()))
            entity[1].add(form)
    return [{"type": kind, "forms": sorted(found, key=len, reverse=True)} for kind, found in forms.values() if found]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=12)
    args = ap.parse_args()
    if not RAW.exists():
        sys.exit(f"{RAW} is missing. Download echr_test.json from the TAB repository into eval/tab_raw/.")
    if OUT.exists():
        if not MARKER.exists():
            sys.exit(f"{OUT} exists, and this script did not make it. Move it away and run again.")
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    MARKER.touch()

    documents = pick(json.loads(RAW.read_text(encoding="utf-8")), args.count)
    keep = keep_set()
    entities: list[dict] = []
    for document in documents:
        (OUT / f"{document['doc_id']}.en.txt").write_text(document["text"], encoding="utf-8")
        for found in gold_entities(document, keep):
            # Two cases can have the same person (for example a judge). One entity has one id in all documents,
            # so the entities of two cases that share a written form are one gold entity.
            same = next((e for e in entities if e["type"] == found["type"] and set(e["forms"]) & set(found["forms"])), None)
            if same:
                same["forms"] = sorted(set(same["forms"]) | set(found["forms"]), key=len, reverse=True)
            else:
                entities.append(found)
    gold = {"entities": entities, "must_keep": [], "visible_ok": []}
    (OUT / "gold.json").write_text(json.dumps(gold, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    words = sum(len(d["text"].split()) for d in documents)
    print(f"{len(documents)} cases, {words} words, {len(entities)} gold entities in {OUT.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
