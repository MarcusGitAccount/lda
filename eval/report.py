"""Make docs/results.md from the files in eval/results/.

    python -m eval.report

One table for each dataset, one row for each run, the oldest run first. The file is made again
each time, so do not edit it. The notes about the results are in docs/experiments.md.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict

from eval.tracker import RESULTS, ROOT

OUT = ROOT / "docs" / "results.md"


def policy(run: dict) -> str:
    return "kept" if run["settings"]["keep_public_bodies"] else "hidden"


def row_mapa(run: dict) -> tuple[list[str], list[str]]:
    m = run["metrics"]
    c = m["classes"]
    h = m["hidden_or_not"]
    head = ["when", "name", "level", "public bodies", "recall", "persons", "orgs", "addresses", "P", "F1", "F2", "tokens/s", "LLM adds (gold / other)"]
    llm = m.get("llm")
    cells = [
        run["when"][:16].replace("T", " "),
        run["name"],
        run["settings"]["level"],
        policy(run),
        f"{m['recall_any_type']:.1%}",
        f"{c['PERSON']['recall']:.1%}",
        f"{c['ORGANISATION']['recall']:.1%}",
        f"{c['ADDRESS']['recall']:.1%}",
        f"{h['precision']:.2f}",
        f"{h['f1']:.2f}",
        f"{h['f2']:.2f}",
        str(m.get("tokens_per_second", "")),
        "-" if not llm else f"{llm['gold_tokens_only_the_llm_covers']} / {llm['other_tokens_only_the_llm_hides']}",
    ]
    return head, cells


def row_corpus(run: dict) -> tuple[list[str], list[str]]:
    m = run["metrics"]
    d = m["mentions"]
    head = ["when", "name", "level", "public bodies", "recall", "P", "F1", "F2", "split", "merged", "leaked", "restore words", "words/s"]
    cells = [
        run["when"][:16].replace("T", " "),
        run["name"],
        run["settings"]["level"],
        policy(run),
        f"{d['recall']:.1%}",
        f"{d['precision']:.2f}",
        f"{d['f1']:.2f}",
        f"{d['f2']:.2f}",
        "n/a" if m["split_entities"] is None else f"{m['split_entities']}/{m['entities_seen']}",
        "n/a" if m["merged_ids"] is None else str(m["merged_ids"]),
        str(m["leaked_forms"]),
        f"{m['restore_words_equal']:.1%}",
        str(m.get("words_per_second", "")),
    ]
    return head, cells


def row_hits(run: dict) -> tuple[list[str], list[str]]:
    m = run["metrics"]
    head = ["when", "name", "level", "public bodies", "documents", "words", "hits", "hits / 1,000 words", "by type", "words/s"]
    cells = [
        run["when"][:16].replace("T", " "),
        run["name"],
        run["settings"]["level"],
        policy(run),
        str(m["documents"]),
        str(m["words"]),
        str(m["hits"]),
        f"{m['hits_per_1000_words']:.1f}",
        ", ".join(f"{k} {v}" for k, v in sorted(m["by_type"].items(), key=lambda kv: -kv[1])),
        str(m.get("words_per_second", "")),
    ]
    return head, cells


def row_for(dataset: str):
    if dataset.startswith("corpus-"):
        return row_corpus
    return row_hits if dataset.startswith("hits-") else row_mapa


def main() -> int:
    runs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(RESULTS.glob("*.json"))]
    by_dataset: dict[str, list[dict]] = defaultdict(list)
    for run in runs:
        by_dataset[run["dataset"]].append(run)

    lines = ["# Results of the experiments", "", "Made by `python -m eval.report` from `eval/results/`. Do not edit.", ""]
    for dataset, items in sorted(by_dataset.items()):
        lines += [f"## {dataset}", ""]
        rows = [row_for(dataset)(run) for run in items]
        head = rows[0][0]
        lines += ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        lines += ["| " + " | ".join(cells) + " |" for _, cells in rows]
        lines.append("")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(runs)} runs in {OUT.relative_to(ROOT) if OUT.is_relative_to(ROOT) else OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
