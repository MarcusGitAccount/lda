"""Make a sample of real Romanian legal acts, to look at what the tool hides in public Romanian legal text.

    python -m eval.ro_law_corpus documents.parquet --per-type 5

Source: the daily export of legislatie.just.ro by https://github.com/scriptogre/romanian-law-data
(`documents.parquet` in a release; the repo states no license; Romanian legislation is, as far as we know, outside
copyright by Law 8/1996 art. 9, but confirm this before you publish anything). We do not put the data in git
(`eval/corpora/ro-law/` is in `.gitignore`), and we do not publish it.

There is no gold list for these acts. Use `python -m eval.hits_report`. Decrees and decisions name real people
(appointments, honours), so the sample has names in real Romanian legal text. Contracts are not in this source.

`pyarrow` is not a dependency of the project. Read the parquet file in a separate environment: the file comes from the
internet, so it is untrusted data. The output is plain text.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "eval" / "corpora" / "ro-law"
MARKER = ".made-by-ro-law-corpus"

# Group the acts so that the sample is not only decrees. Both spellings of "hotărâre" exist in the source.
GROUPS = {
    "LEGE": "lege",
    "ORDONANȚĂ": "ordonanta",
    "HOTĂRÂRE": "hotarare",
    "HOTĂRÎRE": "hotarare",
    "ORDIN": "ordin",
    "DECRET": "decret",
    "DECIZIE": "decizie",
    "DECIZIA": "decizie",
    "REGULAMENT": "regulament",
    "NORME": "norme",
}
MIN_WORDS, MAX_WORDS = 800, 4000
MIN_YEAR = 2000
SEED = 20261101


def words(text: str) -> int:
    return len(text.split())


def ascii_slug(text: str) -> str:
    plain = unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "-", plain).strip("-").lower()


def eligible(row: dict) -> str | None:
    """The group of the act if it fits the sample, else None."""
    group = GROUPS.get(row.get("type") or "")
    when = row.get("adopted_at")
    if group is None or when is None or when.year < MIN_YEAR:
        return None
    return group if MIN_WORDS <= words(row.get("content") or "") <= MAX_WORDS else None


def file_name(row: dict, group: str) -> str:
    return f"{group}-{row['adopted_at'].year}-{ascii_slug(row.get('document_number') or str(row.get('id')))}.ro.txt"


def reservoir(rows, per_type: int, seed: int = SEED) -> dict[str, list[dict]]:
    """Choose `per_type` acts of each group, at random but always the same ones for the same input (reservoir sample)."""
    rng = random.Random(seed)
    seen: dict[str, int] = {}
    chosen: dict[str, list[dict]] = {}
    for row in rows:
        group = eligible(row)
        if group is None:
            continue
        seen[group] = seen.get(group, 0) + 1
        bucket = chosen.setdefault(group, [])
        if len(bucket) < per_type:
            bucket.append(row)
        else:
            slot = rng.randrange(seen[group])
            if slot < per_type:
                bucket[slot] = row
    return chosen


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("parquet", type=Path)
    ap.add_argument("--per-type", type=int, default=5)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    try:
        import pyarrow.parquet as pq
    except ImportError:
        print("pyarrow is needed to read the file. Use a separate environment: python -m venv x; x/bin/pip install pyarrow")
        return 1

    def rows():
        columns = ["id", "type", "document_number", "document_citation", "title", "content", "adopted_at"]
        for batch in pq.ParquetFile(args.parquet).iter_batches(batch_size=1000, columns=columns):
            yield from batch.to_pylist()

    chosen = reservoir(rows(), args.per_type)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / MARKER).write_text("made by eval/ro_law_corpus.py; safe to delete and make again\n")
    sources = []
    for group, acts in sorted(chosen.items()):
        for act in sorted(acts, key=lambda a: a["adopted_at"]):
            name = file_name(act, group)
            (args.out / name).write_text(act["content"].strip() + "\n", encoding="utf-8")
            sources.append({"file": name, "citation": act["document_citation"], "words": words(act["content"])})
    (args.out / "SOURCES.json").write_text(json.dumps(sources, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(sources)} acts in {args.out}: " + ", ".join(f"{g}={len(a)}" for g, a in sorted(chosen.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
