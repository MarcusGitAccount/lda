"""Settings for one run, and the loader for the user's config file.

Example config file (YAML):

    hide: [PERSON, ORGANIZATION, LOCATION, ADDRESS, DATE_TIME]   # optional
    keep: ["Tribunalul București", "ANAF"]    # never hide these texts
    keep_public_bodies: false                  # true: do not hide courts, ministries
    entities:                                  # known entities with aliases
      - type: PERSON
        name: Ion Popescu
        aliases: [Popescu Ion, dl. Popescu]
      - type: ORGANIZATION
        name: Alfa Construct SRL
        aliases: [Alfa Construct, Alfa]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .entities import ALL_TYPES, DEFAULT_HIDE
from .ner import EN_MODEL, RO_MODEL


@dataclass
class SeedEntity:
    type: str
    name: str
    aliases: list[str] = field(default_factory=list)


@dataclass
class Settings:
    hide: set[str] = field(default_factory=lambda: set(DEFAULT_HIDE))
    keep: list[str] = field(default_factory=list)
    seeds: list[SeedEntity] = field(default_factory=list)
    # A NER result with a lower score is dropped. A low value gives more recall.
    min_score: float = 0.4
    # Do not hide courts, ministries and EU bodies. Off by default: it is safer to hide.
    keep_public_bodies: bool = False
    ro_model: str = RO_MODEL
    en_model: str = EN_MODEL

    def validate(self) -> None:
        unknown = self.hide - ALL_TYPES
        if unknown:
            raise ValueError(f"Unknown entity types: {sorted(unknown)}. Known: {sorted(ALL_TYPES)}")
        for seed in self.seeds:
            if seed.type not in ALL_TYPES:
                raise ValueError(f"Seed '{seed.name}' has unknown type '{seed.type}'")


def load_settings(path: str | Path | None = None, *, hide: list[str] | None = None) -> Settings:
    settings = Settings()
    if path:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        if "hide" in data:
            settings.hide = set(data["hide"])
        settings.keep = list(data.get("keep", []))
        settings.min_score = float(data.get("min_score", settings.min_score))
        settings.keep_public_bodies = bool(data.get("keep_public_bodies", settings.keep_public_bodies))
        settings.ro_model = data.get("ro_model", settings.ro_model)
        settings.en_model = data.get("en_model", settings.en_model)
        for item in data.get("entities", []):
            settings.seeds.append(
                SeedEntity(item["type"], item["name"], list(item.get("aliases", [])))
            )
    if hide:
        settings.hide = set(hide)
    settings.validate()
    return settings
