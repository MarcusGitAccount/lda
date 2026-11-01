"""Measure the detector on MAPA (EUR-Lex legal text with anonymization labels).

Data: https://huggingface.co/datasets/joelniklaus/mapa (CC-BY-4.0).
Download test.jsonl and validation.jsonl into eval/mapa_raw/ first (see README).

We measure at token level:
  * recall of sensitive tokens, any type. A missed token is a leak.
  * precision and recall for PERSON and ORGANISATION tokens, with type.
  * ADDRESS recall (the detector may call it LOCATION or ADDRESS).

MAPA marks only some things. For example, it does not mark a country or a city
outside of an address. So precision against MAPA is a lower bound.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

from legal_anonymizer.config import Settings
from legal_anonymizer.detector import Detector
from legal_anonymizer.spans import DEFAULT_KEEP, ROLE_WORDS, TITLES
from legal_anonymizer.textnorm import fold

HERE = Path(__file__).parent
NO_SPACE_BEFORE = set(".,;:!?)%]")
NO_SPACE_AFTER = set("([")

# Tokens that the policy keeps on purpose: titles, role words and country names.
KEPT_WORDS = {fold(w).strip(".") for w in TITLES | ROLE_WORDS}
KEPT_PLACES = {fold(w).strip(".") for entry in DEFAULT_KEEP for w in entry.split()}


def kept_on_purpose(label: str, token: str) -> bool:
    word = fold(token).strip(".,;:()")
    if label in {"PERSON", "ORGANISATION"}:
        return word in KEPT_WORDS
    return word in KEPT_PLACES


GOLD_CLASSES = {"PERSON": {"PERSON"}, "ORGANISATION": {"ORGANIZATION"}, "ADDRESS": {"LOCATION", "ADDRESS"}}


def load_documents(language: str, splits: list[str]):
    docs = defaultdict(list)
    for split in splits:
        for line in (HERE / "mapa_raw" / f"{split}.jsonl").read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row["language"] == language:
                docs[(split, row["file_name"])].append(row)
    for key, rows in docs.items():
        rows.sort(key=lambda r: r["sentence_number"])
        yield key, rows


def build_text(rows):
    """Join the tokens like normal text. Return the text, the token offsets, the gold labels."""
    parts, tokens, labels = [], [], []
    pos = 0
    for row in rows:
        previous = None
        for token, tag in zip(row["tokens"], row["coarse_grained"]):
            if previous is not None and token not in NO_SPACE_BEFORE and previous not in NO_SPACE_AFTER:
                parts.append(" ")
                pos += 1
            tokens.append((pos, pos + len(token)))
            labels.append(tag.split("-", 1)[-1] if tag != "O" else "O")
            parts.append(token)
            pos += len(token)
            previous = token
        parts.append("\n")
        pos += 1
    return "".join(parts), tokens, labels


def covered(token, spans):
    return [s for s in spans if token[0] < s.end and s.start < token[1]]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=["ro", "en"], required=True)
    ap.add_argument("--splits", nargs="+", default=["test", "validation"])
    ap.add_argument("--model", help="NER model name to test instead of the default")
    ap.add_argument("--min-score", type=float, default=0.4)
    ap.add_argument("--public", action="store_true", help="keep_public_bodies=true")
    ap.add_argument("--raw", action="store_true", help="count tokens that the policy keeps on purpose as misses")
    ap.add_argument("--show-misses", type=int, default=0, help="print this many missed spans")
    args = ap.parse_args()

    settings = Settings(min_score=args.min_score, keep_public_bodies=args.public)
    if args.model:
        setattr(settings, f"{args.lang}_model", args.model)
    detector = Detector(settings)

    hit = defaultdict(int)  # gold class -> tokens covered by any predicted span
    gold = defaultdict(int)
    typed_hit = defaultdict(int)  # gold class -> tokens covered with a right type
    predicted = defaultdict(int)  # predicted type -> tokens
    predicted_right = defaultdict(int)  # predicted type -> tokens that are gold of that class
    misses = []
    started = time.time()
    n_tokens = 0

    for (_split, _name), rows in load_documents(args.lang, args.splits):
        text, tokens, labels = build_text(rows)
        n_tokens += len(tokens)
        spans = [s for s in detector.detect(text, args.lang) if s.type != "KEEP"]  # KEEP text stays visible
        spans = sorted(spans, key=lambda s: s.start)
        for tok, label in zip(tokens, labels):
            over = covered(tok, spans)
            if label in GOLD_CLASSES and (args.raw or not kept_on_purpose(label, text[tok[0] : tok[1]])):
                gold[label] += 1
                if over:
                    hit[label] += 1
                if any(s.type in GOLD_CLASSES[label] for s in over):
                    typed_hit[label] += 1
                elif not over:
                    misses.append((label, text[tok[0] : tok[1]], text[max(0, tok[0] - 30) : tok[1] + 30].replace("\n", " ")))
            for s in over:
                predicted[s.type] += 1
                gold_class = next((g for g, types in GOLD_CLASSES.items() if s.type in types), None)
                if gold_class and label == gold_class and (args.raw or not kept_on_purpose(label, text[tok[0] : tok[1]])):
                    predicted_right[s.type] += 1

    print(f"language={args.lang} model={getattr(settings, args.lang + '_model')} tokens={n_tokens} time={time.time()-started:.0f}s")
    total_gold = sum(gold.values())
    total_hit = sum(hit.values())
    print(f"sensitive-token recall (any type): {total_hit}/{total_gold} = {total_hit / max(total_gold, 1):.3f}")
    for label in GOLD_CLASSES:
        g = gold[label]
        print(f"  {label:13} gold={g:4}  covered={hit[label]:4} ({hit[label] / max(g, 1):.3f})  right-type={typed_hit[label]:4} ({typed_hit[label] / max(g, 1):.3f})")
    for etype in ("PERSON", "ORGANIZATION", "LOCATION", "ADDRESS"):
        if predicted[etype]:
            print(f"  predicted {etype:13} tokens={predicted[etype]:4}  also gold of that class={predicted_right[etype]:4} ({predicted_right[etype] / predicted[etype]:.3f})")
    for label, tok, context in misses[: args.show_misses]:
        print(f"  MISS {label:12} {tok!r:20} ...{context}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
