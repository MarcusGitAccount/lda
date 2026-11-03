"""The vault: a local SQLite file for one matter (one client case).

The vault is the only place where the real data and the ids are together.
Keep the file on the local disk. Never send it to an AI tool.

One entity has one id. Each entity has:
  * keys: normalized forms. Two written forms with the same key are the same
    entity (see `textnorm.entity_key`),
  * forms: the written forms we saw, with a count,
  * mentions: how many times the entity appears in each document.
"""

from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .entities import TAG_ALIAS_SPELLINGS, TAGS, TYPE_BY_TAG, type_of_tag
from .romanian import INFLECTED_TYPES, derives_from, same_lexeme
from .textnorm import collapse, entity_key, fold

SCHEMA = """
CREATE TABLE IF NOT EXISTS entity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    number INTEGER NOT NULL,
    merged_into INTEGER REFERENCES entity(id),
    ignored INTEGER NOT NULL DEFAULT 0,
    UNIQUE (type, number)
);
CREATE TABLE IF NOT EXISTS entity_key (
    type TEXT NOT NULL,
    key TEXT NOT NULL,
    entity_id INTEGER NOT NULL REFERENCES entity(id),
    PRIMARY KEY (type, key)
);
CREATE TABLE IF NOT EXISTS form (
    entity_id INTEGER NOT NULL REFERENCES entity(id),
    original TEXT NOT NULL,
    folded TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    seed INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (entity_id, original)
);
CREATE TABLE IF NOT EXISTS document (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    language TEXT,
    processed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS kept_phrase (
    folded TEXT PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS mention (
    document_id INTEGER NOT NULL REFERENCES document(id),
    entity_id INTEGER NOT NULL REFERENCES entity(id),
    count INTEGER NOT NULL,
    PRIMARY KEY (document_id, entity_id)
);
"""

_PLACEHOLDER_NUMBER_WIDTH = 3


def placeholder(entity_type: str, number: int) -> str:
    return f"[{TAGS[entity_type]}_{number:0{_PLACEHOLDER_NUMBER_WIDTH}d}]"


# The restore step accepts small changes that an AI tool can make: other spacing, a hyphen in place
# of "_", missing leading zeros, Markdown escapes such as \[PERSON\_001\], lower case, the long
# name of the type, a Romanian word for the type (only with "_"), and other brackets. An id without
# brackets needs the "_" ("PERSON_001"): the text "Person 1" is not an id.
def _words(words) -> str:
    return "|".join(sorted(map(re.escape, words), key=len, reverse=True))


_EXACT, _ALIAS = _words(TYPE_BY_TAG), _words(TAG_ALIAS_SPELLINGS)
PLACEHOLDER_RE = re.compile(
    rf"\\?\[\s*(?:({_EXACT})\s*\\?[_\s-]|({_ALIAS})\s*\\?_)\s*0*(\d+)\s*\\?\]"  # [PERSON_001], [ person 1 ]
    rf"|(?<!\w)({_EXACT}|{_ALIAS})\\?_0*(\d+)(?!\d)",  # PERSON_001, (PERSON_001), [PERSON_001 si PERSON_002]
    re.IGNORECASE,
)


def parse_placeholder(match: re.Match) -> tuple[str | None, int]:
    """(entity type, number) of a match of `PLACEHOLDER_RE`. The type is None for an unknown tag."""
    tag = match.group(1) or match.group(2) or match.group(4)
    return type_of_tag(tag), int(match.group(3) or match.group(5))


@dataclass
class Entity:
    id: int
    type: str
    number: int
    canonical: str
    forms: dict[str, int] = field(default_factory=dict)
    documents: list[str] = field(default_factory=list)
    ignored: bool = False  # `forget`: the tool does not hide this text any more

    @property
    def placeholder(self) -> str:
        return placeholder(self.type, self.number)


class Vault:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new = not self.path.exists()
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)
        if "ignored" not in {row["name"] for row in self.db.execute("PRAGMA table_info(entity)")}:
            self.db.execute("ALTER TABLE entity ADD COLUMN ignored INTEGER NOT NULL DEFAULT 0")  # an older vault
        if new:
            os.chmod(self.path, 0o600)  # only the owner can read the real data

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "Vault":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    @contextmanager
    def transaction(self):
        try:
            yield
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    # --- write ---------------------------------------------------------------

    def resolve(self, entity_type: str, surface: str, *, seed: bool = False, count: int = 1) -> Entity:
        """Return the entity for a written form. Create it if it is new."""
        surface = collapse(surface)
        key = entity_key(entity_type, surface)
        row = self.db.execute(
            "SELECT entity_id FROM entity_key WHERE type = ? AND key = ?", (entity_type, key)
        ).fetchone()
        if row is None and not seed:
            row = self._other_form(entity_type, key)
            if row:  # remember this key, so the next search is a plain lookup
                self.db.execute(
                    "INSERT OR IGNORE INTO entity_key (type, key, entity_id) VALUES (?, ?, ?)",
                    (entity_type, key, row["entity_id"]),
                )
        if row:
            entity_id = self._root(row["entity_id"])
        else:
            number = self._next_number(entity_type)
            cur = self.db.execute(
                "INSERT INTO entity (type, number) VALUES (?, ?)", (entity_type, number)
            )
            entity_id = cur.lastrowid
            self.db.execute(
                "INSERT INTO entity_key (type, key, entity_id) VALUES (?, ?, ?)",
                (entity_type, key, entity_id),
            )
        self.db.execute(
            "INSERT INTO form (entity_id, original, folded, count, seed) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (entity_id, original) DO UPDATE SET "
            "count = count + excluded.count, seed = MAX(seed, excluded.seed)",
            (entity_id, surface, fold(surface), count, 2 * int(seed)),  # the seed name wins over its aliases
        )
        return self.entity(entity_id)

    def add_alias(self, entity_id: int, surface: str, *, seed: bool = True) -> None:
        """Say that `surface` is another name of an existing entity."""
        entity = self.entity(entity_id)
        surface = collapse(surface)
        key = entity_key(entity.type, surface)
        row = self.db.execute(
            "SELECT entity_id FROM entity_key WHERE type = ? AND key = ?", (entity.type, key)
        ).fetchone()
        if row and self._root(row["entity_id"]) != entity.id:
            other = self.entity(self._root(row["entity_id"]))
            raise ValueError(
                f"'{surface}' is already {other.placeholder} ({other.canonical}). "
                f"Use merge to join {other.placeholder} and {entity.placeholder}."
            )
        self.db.execute(
            "INSERT OR IGNORE INTO entity_key (type, key, entity_id) VALUES (?, ?, ?)",
            (entity.type, key, entity.id),
        )
        self.db.execute(
            "INSERT INTO form (entity_id, original, folded, count, seed) VALUES (?, ?, ?, 0, ?) "
            "ON CONFLICT (entity_id, original) DO UPDATE SET seed = MAX(seed, excluded.seed)",
            (entity.id, surface, fold(surface), int(seed)),
        )

    def merge(self, source: str, target: str) -> Entity:
        """Join two entities. The source id stays valid and points to the target."""
        src, dst = self.by_placeholder(source), self.by_placeholder(target)
        if src is None or dst is None:
            raise KeyError(f"Unknown id: {source if src is None else target}")
        if src.id == dst.id:
            return dst
        if src.type != dst.type:
            raise ValueError(f"Cannot merge {src.type} into {dst.type}")
        with self.transaction():
            self.db.execute("UPDATE entity SET merged_into = ? WHERE id = ?", (dst.id, src.id))
            self.db.execute("UPDATE entity_key SET entity_id = ? WHERE entity_id = ?", (dst.id, src.id))
            self.db.execute("UPDATE entity SET merged_into = ? WHERE merged_into = ?", (dst.id, src.id))
            for row in self.db.execute("SELECT * FROM form WHERE entity_id = ?", (src.id,)).fetchall():
                self.db.execute(
                    "INSERT INTO form (entity_id, original, folded, count, seed) VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT (entity_id, original) DO UPDATE SET "
                    "count = count + excluded.count, seed = MAX(seed, excluded.seed)",
                    (dst.id, row["original"], row["folded"], row["count"], row["seed"]),
                )
            self.db.execute("DELETE FROM form WHERE entity_id = ?", (src.id,))
            for row in self.db.execute("SELECT * FROM mention WHERE entity_id = ?", (src.id,)).fetchall():
                self.db.execute(
                    "INSERT INTO mention (document_id, entity_id, count) VALUES (?, ?, ?) "
                    "ON CONFLICT (document_id, entity_id) DO UPDATE SET count = count + excluded.count",
                    (row["document_id"], dst.id, row["count"]),
                )
            self.db.execute("DELETE FROM mention WHERE entity_id = ?", (src.id,))
        return self.entity(dst.id)

    def forget(self, entity_id: int) -> Entity:
        """Say that this entity is not sensitive (a word that the model took for a name). The tool stops
        hiding its forms. Old documents still restore: the id stays in the vault."""
        entity = self.entity(entity_id)
        with self.transaction():
            self.db.execute("UPDATE entity SET ignored = 1 WHERE id = ?", (entity.id,))
            self.add_kept(entity.forms)
        return self.entity(entity.id)

    def split(self, entity_id: int, surface: str) -> Entity:
        """Take one written form (and the forms with the same key) out of an entity, into a new entity.
        Use it when the tool joined two different names. Documents that are already hidden keep their
        old id for this form."""
        entity = self.entity(entity_id)
        key = entity_key(entity.type, collapse(surface))
        moving = [f for f in entity.forms if entity_key(entity.type, f) == key]
        if not moving:
            raise ValueError(f"'{surface}' is not a form of {entity.placeholder}.")
        if len(moving) == len(entity.forms):
            raise ValueError(f"'{surface}' is the only name of {entity.placeholder}. There is nothing to split.")
        with self.transaction():
            cur = self.db.execute(
                "INSERT INTO entity (type, number) VALUES (?, ?)", (entity.type, self._next_number(entity.type))
            )
            new_id = cur.lastrowid
            self.db.execute(
                "INSERT OR REPLACE INTO entity_key (type, key, entity_id) VALUES (?, ?, ?)", (entity.type, key, new_id)
            )
            for form in moving:
                self.db.execute(
                    "UPDATE form SET entity_id = ? WHERE entity_id = ? AND original = ?", (new_id, entity.id, form)
                )
        return self.entity(new_id)

    def any_ignored(self) -> bool:
        return self.db.execute("SELECT 1 FROM entity WHERE ignored = 1 LIMIT 1").fetchone() is not None

    def is_ignored(self, entity_type: str, surface: str) -> bool:
        row = self.db.execute(
            "SELECT e.ignored FROM entity_key k JOIN entity e ON e.id = k.entity_id WHERE k.type = ? AND k.key = ?",
            (entity_type, entity_key(entity_type, surface)),
        ).fetchone()
        return bool(row and row["ignored"])

    def add_kept(self, phrases) -> None:
        """Remember text that the policy keeps visible (a court, a country). The leak check ignores it."""
        for phrase in phrases:
            folded = collapse(fold(phrase))
            if folded:
                self.db.execute("INSERT OR IGNORE INTO kept_phrase (folded) VALUES (?)", (folded,))

    def kept_phrases(self) -> list[str]:
        return [r["folded"] for r in self.db.execute("SELECT folded FROM kept_phrase")]

    def record_document(self, name: str, sha256: str, language: str | None, mentions: dict[int, int]) -> None:
        cur = self.db.execute(
            "INSERT INTO document (name, sha256, language, processed_at) VALUES (?, ?, ?, ?)",
            (name, sha256, language, datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        for entity_id, count in mentions.items():
            self.db.execute(
                "INSERT INTO mention (document_id, entity_id, count) VALUES (?, ?, ?)",
                (cur.lastrowid, entity_id, count),
            )

    # --- read ----------------------------------------------------------------

    def _root(self, entity_id: int) -> int:
        while True:
            row = self.db.execute("SELECT merged_into FROM entity WHERE id = ?", (entity_id,)).fetchone()
            if row is None or row["merged_into"] is None:
                return entity_id
            entity_id = row["merged_into"]

    def _next_number(self, entity_type: str) -> int:
        row = self.db.execute("SELECT COALESCE(MAX(number), 0) + 1 AS n FROM entity WHERE type = ?", (entity_type,)).fetchone()
        return row["n"]

    def _other_form(self, entity_type: str, key: str):
        """Find an entity that has this name in another Romanian form ("Popescului" for "Popescu")."""
        if entity_type not in INFLECTED_TYPES:
            return None
        words = key.split()
        ordered = entity_type != "PERSON"  # the key of a person has sorted words
        for row in self.db.execute("SELECT key, entity_id FROM entity_key WHERE type = ?", (entity_type,)):
            if same_lexeme(row["key"].split(), words, ordered=ordered):
                return row
        return None

    def _canonical(self, entity_id: int) -> str:
        # A seed name wins. Then a form with a capital letter ("Will", not "will"). Then the most common
        # form. Then the first one seen.
        # A form that is only an inflection of another form ("Popescului") does not win over its base.
        rows = self.db.execute(
            "SELECT original, folded, seed FROM form WHERE entity_id = ? ORDER BY seed DESC, count DESC, rowid ASC",
            (entity_id,),
        ).fetchall()
        if not rows:
            return ""
        rows.sort(key=lambda r: (-r["seed"], r["original"] == r["original"].lower()))  # a stable sort
        kind = self.db.execute("SELECT type FROM entity WHERE id = ?", (entity_id,)).fetchone()["type"]
        if kind in INFLECTED_TYPES and len(rows) > 1:
            ordered = kind != "PERSON"
            for row in rows:
                words = row["folded"].split()
                if not any(
                    derives_from(words, other["folded"].split(), ordered=ordered) for other in rows if other is not row
                ):
                    return row["original"]
        return rows[0]["original"]

    def entity(self, entity_id: int) -> Entity:
        row = self.db.execute("SELECT * FROM entity WHERE id = ?", (self._root(entity_id),)).fetchone()
        forms = {
            r["original"]: r["count"]
            for r in self.db.execute(
                "SELECT original, count FROM form WHERE entity_id = ? ORDER BY seed DESC, count DESC", (row["id"],)
            )
        }
        docs = [
            r["name"]
            for r in self.db.execute(
                "SELECT DISTINCT d.name FROM mention m JOIN document d ON d.id = m.document_id "
                "WHERE m.entity_id = ? ORDER BY d.id",
                (row["id"],),
            )
        ]
        return Entity(row["id"], row["type"], row["number"], self._canonical(row["id"]), forms, docs, bool(row["ignored"]))

    def by_placeholder(self, text: str) -> Entity | None:
        """Find an entity from text such as "[PERSON_001]" or "PERSON_001"."""
        match = PLACEHOLDER_RE.fullmatch(text.strip()) or PLACEHOLDER_RE.fullmatch(f"[{text.strip().strip('[]')}]")
        if not match:
            return None
        entity_type, number = parse_placeholder(match)
        return self.lookup(entity_type, number) if entity_type else None

    def lookup(self, entity_type: str, number: int) -> Entity | None:
        row = self.db.execute("SELECT id FROM entity WHERE type = ? AND number = ?", (entity_type, number)).fetchone()
        return self.entity(row["id"]) if row else None

    def entities(self) -> list[Entity]:
        rows = self.db.execute("SELECT id FROM entity WHERE merged_into IS NULL ORDER BY type, number").fetchall()
        return [self.entity(r["id"]) for r in rows]

    def known_forms(self, types: set[str] | None = None) -> list[tuple[str, str, int]]:
        """Return (folded form, entity type, entity id) for the sweep."""
        rows = self.db.execute(
            "SELECT DISTINCT f.folded, e.type, e.id FROM form f JOIN entity e ON e.id = f.entity_id "
            "WHERE e.merged_into IS NULL AND e.ignored = 0"
        ).fetchall()
        return [(r["folded"], r["type"], r["id"]) for r in rows if types is None or r["type"] in types]

    def documents(self) -> list[sqlite3.Row]:
        return self.db.execute("SELECT * FROM document ORDER BY id").fetchall()
