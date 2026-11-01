"""Settings for one run, and the loader for the user's config file.

Example config file (YAML):

    level: low                                 # low | medium | high (see LEVELS)
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
from urllib.parse import urlparse

import yaml

from .entities import ALL_TYPES, DEFAULT_HIDE
from .gliner_ner import GLINER_MODEL
from .llm_check import LLM_HOST, LLM_MODEL
from .ner import EN_MODEL, RO_MODEL

# What each level adds. The patterns and the BERT models run at every level.
#   low     patterns + BERT. Fast. This is the level of the first MVP.
#   medium  + GLiNER (a second model, it adds hits).
#   high    + a local LLM (through Ollama) that reads the hidden text and lists the names that remain.
LEVELS = {
    "low": {"gliner": False, "llm": False},
    "medium": {"gliner": True, "llm": False},
    "high": {"gliner": True, "llm": True},
}
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


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
    level: str = "low"
    gliner_model: str = GLINER_MODEL
    # The GLiNER scores are not on the scale of the BERT scores, so GLiNER has its own minimum.
    gliner_threshold: float = 0.5
    llm_model: str = LLM_MODEL
    llm_host: str = LLM_HOST

    @property
    def use_gliner(self) -> bool:
        return LEVELS[self.level]["gliner"]

    @property
    def use_llm(self) -> bool:
        return LEVELS[self.level]["llm"]

    def validate(self) -> None:
        if self.level not in LEVELS:
            raise ValueError(f"Unknown level '{self.level}'. Known: {sorted(LEVELS)}")
        host = urlparse(self.llm_host).hostname
        if host not in LOCAL_HOSTS:
            raise ValueError(f"llm_host '{self.llm_host}' is not on this computer. The text must not leave it.")
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
        settings.level = data.get("level", settings.level)
        settings.gliner_model = data.get("gliner_model", settings.gliner_model)
        settings.gliner_threshold = float(data.get("gliner_threshold", settings.gliner_threshold))
        settings.llm_model = data.get("llm_model", settings.llm_model)
        settings.llm_host = data.get("llm_host", settings.llm_host)
        for item in data.get("entities", []):
            settings.seeds.append(
                SeedEntity(item["type"], item["name"], list(item.get("aliases", [])))
            )
    if hide:
        settings.hide = set(hide)
    settings.validate()
    return settings
