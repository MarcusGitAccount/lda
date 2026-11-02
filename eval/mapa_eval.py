"""Measure the detector on MAPA (EUR-Lex legal text with anonymization labels).

Data: https://huggingface.co/datasets/joelniklaus/mapa (CC-BY-4.0).
Download test.jsonl and validation.jsonl into eval/mapa_raw/ first (see README).

We measure at token level:
  * recall of sensitive tokens, any type. A missed token is a leak.
  * precision and recall for PERSON and ORGANISATION tokens, with type.
  * ADDRESS recall (the detector may call it LOCATION or ADDRESS).
  * precision, recall, F1 and F2 of "hidden or not", for the tokens of the three classes.

MAPA marks only some things. For example, it does not mark a country or a city
outside of an address. So precision against MAPA is a lower bound. The tool also hides all
organizations by default and MAPA marks only some. Use the precision to compare two runs, not
as an absolute number.

Run:  python -m eval.mapa_eval --lang ro --level medium --name bert+gliner
Every run writes a file to eval/results/ (see eval/tracker.py).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

from eval import tracker
from eval.metrics import Counts
from legal_anonymizer.config import LEVELS, Settings
from legal_anonymizer.detector import Detector
from legal_anonymizer.spans import ROLE_WORDS, TITLES, keep_set
from legal_anonymizer.textnorm import fold

HERE = Path(__file__).parent
NO_SPACE_BEFORE = set(".,;:!?)%]")
NO_SPACE_AFTER = set("([")

# Tokens that the policy keeps on purpose: titles, role words and country names.
KEPT_WORDS = {fold(w).strip(".") for w in TITLES | ROLE_WORDS}
# The same list that the detector keeps, with the Romanian forms (`României` for `România`).
KEPT_PLACES = {w.strip(".") for entry in keep_set() for w in entry.split()}


def kept_on_purpose(label: str, token: str) -> bool:
    word = fold(token).strip(".,;:()")
    if label in {"PERSON", "ORGANISATION"}:
        return word in KEPT_WORDS
    return word in KEPT_PLACES


GOLD_CLASSES = {"PERSON": {"PERSON"}, "ORGANISATION": {"ORGANIZATION"}, "ADDRESS": {"LOCATION", "ADDRESS"}}
NAME_AND_PLACE = {"PERSON", "ORGANIZATION", "LOCATION", "ADDRESS"}  # the types that MAPA can judge


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
    ap.add_argument("--level", choices=sorted(LEVELS), default="low", help="what runs: low = BERT, medium = + GLiNER, high = + LLM")
    ap.add_argument("--gliner-model", help="GLiNER model name to test instead of the default")
    ap.add_argument("--gliner-threshold", type=float, help="minimum GLiNER score (default: from the settings)")
    ap.add_argument("--llm-model", help="Ollama model name to test instead of the default")
    ap.add_argument("--name", help="name of the experiment, for the result file (default: the level)")
    ap.add_argument("--limit", type=int, default=0, help="use only this many documents (0 = all)")
    ap.add_argument("--no-record", action="store_true", help="do not write a result file")
    ap.add_argument("--min-score", type=float, default=0.4)
    ap.add_argument("--public", action="store_true", help="keep_public_bodies=true")
    ap.add_argument("--raw", action="store_true", help="count tokens that the policy keeps on purpose as misses")
    ap.add_argument("--show-misses", type=int, default=0, help="print this many missed spans")
    args = ap.parse_args()

    settings = Settings(min_score=args.min_score, keep_public_bodies=args.public, level=args.level)
    settings.validate()
    if args.model:
        setattr(settings, f"{args.lang}_model", args.model)
    if args.gliner_model:
        settings.gliner_model = args.gliner_model
    if args.gliner_threshold is not None:
        settings.gliner_threshold = args.gliner_threshold
    if args.llm_model:
        settings.llm_model = args.llm_model
    detector = Detector(settings)
    detector.warm_up((args.lang,))  # load the models before the clock starts, and fail early

    hit = defaultdict(int)  # gold class -> tokens covered by any predicted span
    gold = defaultdict(int)
    typed_hit = defaultdict(int)  # gold class -> tokens covered with a right type
    predicted = defaultdict(int)  # predicted type -> tokens
    predicted_right = defaultdict(int)  # predicted type -> tokens that are gold of that class
    misses = []
    llm_gain = 0  # gold tokens that only the LLM covers
    llm_noise = 0  # tokens that only the LLM hides, and that are not gold
    hidden_or_not = Counts()  # tokens of the three classes: is it hidden?
    started = time.time()
    n_tokens = 0
    n_docs = 0

    for (_split, _name), rows in load_documents(args.lang, args.splits):
        if args.limit and n_docs >= args.limit:
            break
        n_docs += 1
        text, tokens, labels = build_text(rows)
        n_tokens += len(tokens)
        spans = [s for s in detector.detect(text, args.lang) if s.type != "KEEP"]  # KEEP text stays visible
        spans = sorted(spans, key=lambda s: s.start)
        for tok, label in zip(tokens, labels):
            over = covered(tok, spans)
            is_gold = label in GOLD_CLASSES and (args.raw or not kept_on_purpose(label, text[tok[0] : tok[1]]))
            is_hidden = any(s.type in NAME_AND_PLACE for s in over)
            hidden_or_not.tp += is_gold and is_hidden
            hidden_or_not.fn += is_gold and not is_hidden
            hidden_or_not.fp += is_hidden and not is_gold
            only_llm = bool(over) and all(s.source == "llm" for s in over)
            llm_gain += is_gold and only_llm
            llm_noise += only_llm and is_hidden and not is_gold
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

    elapsed = time.time() - started
    print(f"language={args.lang} level={settings.level} model={getattr(settings, args.lang + '_model')} documents={n_docs} tokens={n_tokens} time={elapsed:.0f}s")
    total_gold = sum(gold.values())
    total_hit = sum(hit.values())
    print(f"sensitive-token recall (any type): {total_hit}/{total_gold} = {total_hit / max(total_gold, 1):.3f}")
    for label in GOLD_CLASSES:
        g = gold[label]
        print(f"  {label:13} gold={g:4}  covered={hit[label]:4} ({hit[label] / max(g, 1):.3f})  right-type={typed_hit[label]:4} ({typed_hit[label] / max(g, 1):.3f})")
    for etype in ("PERSON", "ORGANIZATION", "LOCATION", "ADDRESS"):
        if predicted[etype]:
            print(f"  predicted {etype:13} tokens={predicted[etype]:4}  also gold of that class={predicted_right[etype]:4} ({predicted_right[etype] / predicted[etype]:.3f})")
    print(
        f"hidden-or-not  P={hidden_or_not.precision:.3f}  R={hidden_or_not.recall:.3f}  "
        f"F1={hidden_or_not.f(1):.3f}  F2={hidden_or_not.f(2):.3f}   (precision is a lower bound, see the top of this file)"
    )
    metrics = {
        "documents": n_docs,
        "tokens": n_tokens,
        "recall_any_type": round(total_hit / max(total_gold, 1), 4),
        "classes": {
            label: {
                "gold": gold[label],
                "covered": hit[label],
                "recall": round(hit[label] / max(gold[label], 1), 4),
                "right_type_recall": round(typed_hit[label] / max(gold[label], 1), 4),
            }
            for label in GOLD_CLASSES
        },
        "hidden_or_not": hidden_or_not.as_dict(),
        "predicted_tokens": dict(predicted),
        "tokens_per_second": round(n_tokens / elapsed, 1) if elapsed else None,
    }
    if settings.use_llm:
        checker = detector.checker(settings)
        metrics["llm"] = {
            "model": settings.llm_model,
            "requests": checker.requests,
            "invalid_replies": checker.invalid,
            "skipped_pieces": checker.skipped,
            "structured_output": checker.structured,
            "gold_tokens_only_the_llm_covers": llm_gain,
            "other_tokens_only_the_llm_hides": llm_noise,
        }
        print(
            f"llm {settings.llm_model}: requests={checker.requests} invalid={checker.invalid} "
            f"gold tokens only the LLM covers={llm_gain}  other tokens only the LLM hides={llm_noise}"
        )
    if not args.no_record:
        name = args.name or settings.level
        path = tracker.record(f"mapa-{args.lang}-{'+'.join(args.splits)}", name, settings, metrics, elapsed)
        print(f"saved {path.relative_to(tracker.ROOT)}")
    for label, tok, context in misses[: args.show_misses]:
        print(f"  MISS {label:12} {tok!r:20} ...{context}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
