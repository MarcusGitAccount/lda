"""Write the result of one experiment run to eval/results/, with all that is needed to repeat it.

One run is one JSON file. The files are small and go into git, so the history of the results is
the history of the project. `python -m eval.report` makes a table from them (docs/results.md).
The notes that explain the results are in docs/experiments.md.
"""

from __future__ import annotations

import json
import platform
import subprocess
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "eval" / "results"
PACKAGES = ["presidio-analyzer", "transformers", "torch", "gliner", "legal-anonymizer"]


def _git(*args: str) -> str:
    try:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def environment() -> dict:
    versions = {}
    for name in PACKAGES:
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = None
    return {
        "commit": _git("rev-parse", "--short", "HEAD") or None,
        "dirty": bool(_git("status", "--porcelain")),
        "python": platform.python_version(),
        "machine": f"{platform.system()} {platform.machine()}",
        "packages": versions,
    }


def settings_dict(settings) -> dict:
    return {
        "level": settings.level,
        "min_score": settings.min_score,
        "keep_public_bodies": settings.keep_public_bodies,
        "ro_model": settings.ro_model,
        "en_model": settings.en_model,
        "gliner_model": settings.gliner_model if settings.use_gliner else None,
        "gliner_threshold": settings.gliner_threshold if settings.use_gliner else None,
        "llm_model": settings.llm_model if settings.use_llm else None,
    }


def record(dataset: str, name: str, settings, metrics: dict, seconds: float, extra: dict | None = None) -> Path:
    """Save one run. `name` says what was tried (for example "bert+gliner-multi-pii")."""
    now = datetime.now(timezone.utc)
    run = {
        "when": now.isoformat(timespec="seconds"),
        "dataset": dataset,
        "name": name,
        "settings": settings_dict(settings),
        "seconds": round(seconds, 1),
        "metrics": metrics,
        "environment": environment(),
        **(extra or {}),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_." else "-" for c in f"{dataset}_{name}")
    path = RESULTS / f"{now:%Y%m%d-%H%M%S}_{safe}.json"
    path.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
