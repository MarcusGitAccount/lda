"""Command line: `lda`."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

from .config import LEVELS, Settings, load_settings
from .documents import UnsupportedFormat
from .vault import Vault

MATTER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def default_home() -> Path:
    return Path(os.environ.get("LDA_HOME", Path.home() / ".legal-anonymizer"))


def vault_path(home: Path, matter: str) -> Path:
    if not MATTER_RE.match(matter):
        raise SystemExit(f"Bad matter name '{matter}'. Use letters, digits, '-', '_' and '.'.")
    return home / f"{matter}.db"


def output_name(name: str, mode: str) -> str:
    path = Path(name)
    stem = path.stem[: -len(".anon")] if mode == "restored" and path.stem.endswith(".anon") else path.stem
    suffix = "anon" if mode == "anon" else "restored"
    # We read a PDF but we write text. An AI tool cannot edit a PDF.
    extension = ".txt" if path.suffix.lower() == ".pdf" else path.suffix
    return f"{stem}.{suffix}{extension}"


def read_files(paths: list[str]) -> list[tuple[str, bytes]]:
    files = []
    for item in paths:
        path = Path(item)
        if not path.is_file():
            raise SystemExit(f"File not found: {item}")
        files.append((path.name, path.read_bytes()))
    return files


def cmd_setup(args) -> int:
    from .detector import Detector

    settings = Settings(level=args.level)
    detector = Detector(settings)
    for lang in ("ro", "en"):
        print(f"Loading the {lang} model. The first time, it is downloaded (about 1.3 GB for English) ...")
        detector.warm_up((lang,))
    print("Done. The models are ready.")
    return 0


def cmd_text(args) -> int:
    """Show the text that the tool reads from a file. For a PDF this is the text after we join the lines."""
    from .documents import open_document

    for name, data in read_files(args.files):
        try:
            text = "\n".join(open_document(name, data).units())
        except (UnsupportedFormat, ValueError) as error:
            raise SystemExit(f"Error: {error}") from error
        if len(args.files) > 1:
            print(f"=== {name}")
        print(text)
    return 0


def cmd_anonymize(args) -> int:
    from .engine import Engine

    settings = load_settings(args.config, hide=args.hide.split(",") if args.hide else None)
    if args.level:
        settings.level = args.level
        settings.validate()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = read_files(args.files)
    with Vault(vault_path(args.home, args.matter)) as vault:
        engine = Engine(vault, settings)
        engine.load_seeds()
        try:
            results = engine.anonymize_many(files, language=args.lang)
        except (UnsupportedFormat, ValueError, RuntimeError) as error:  # RuntimeError: no Ollama, no GLiNER
            raise SystemExit(f"Error: {error}") from error
        bad = 0
        for (name, _), result in zip(files, results):
            target = out_dir / output_name(name, "anon")
            if result.leaks:  # do not leave a leaking file next to the safe ones
                target = out_dir / "needs-review" / target.name
                target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(result.data)
            kinds = Counter(re.match(r"\[([A-Z_]+?)_\d+\]", p).group(1) for p in result.counts.elements())
            summary = ", ".join(f"{n} {k}" for k, n in sorted(kinds.items())) or "nothing found"
            print(f"{name} ({result.language}) -> {target}\n  hidden: {summary}")
            if result.leaks:
                bad += 1
                print(f"  WARNING: text of {', '.join(result.leaks)} is still in the file. It is in the folder 'needs-review'. Check it before you use it.")
    if bad:
        print(f"\n{bad} file(s) have a warning.")
    print(
        "\nReview the output before you send it to an AI tool. Use `lda entities` to see what was hidden.\n"
        "Keep the vault private: " + str(vault_path(args.home, args.matter))
    )
    return 1 if bad else 0


def cmd_restore(args) -> int:
    from .engine import Engine

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = read_files(args.files)
    bad = 0
    with Vault(vault_path(args.home, args.matter)) as vault:
        engine = Engine(vault)
        for name, data in files:
            try:
                result = engine.restore(name, data)
            except (UnsupportedFormat, ValueError) as error:
                raise SystemExit(f"Error: {error}") from error
            target = out_dir / output_name(name, "restored")
            target.write_bytes(result.data)
            print(f"{name} -> {target}\n  restored: {sum(result.restored.values())} ids ({len(result.restored)} different)")
            if result.unknown:
                bad += 1
                print(f"  WARNING: these ids are not in the vault and stay as they are: {', '.join(result.unknown)}")
            if result.suspect:
                bad += 1
                print(f"  WARNING: this text looks like an id and was not restored: {', '.join(result.suspect)}")
    return 1 if bad else 0


def cmd_entities(args) -> int:
    with Vault(vault_path(args.home, args.matter)) as vault:
        entities = vault.entities()
        if args.json:
            print(json.dumps([
                {"id": e.placeholder, "type": e.type, "text": e.canonical, "forms": e.forms, "documents": e.documents}
                for e in entities
            ], ensure_ascii=False, indent=2))
            return 0
        if not entities:
            print("The vault has no entities.")
        for e in entities:
            others = [f for f in e.forms if f != e.canonical]
            extra = f"  also: {', '.join(others)}" if others else ""
            note = "  (forgotten: not hidden any more)" if e.ignored else ""
            print(f"{e.placeholder:18} {e.canonical}{extra}{note}   [{', '.join(e.documents)}]")
    return 0


def cmd_merge(args) -> int:
    with Vault(vault_path(args.home, args.matter)) as vault:
        try:
            target = vault.merge(args.source, args.target)
        except (KeyError, ValueError) as error:
            raise SystemExit(f"Error: {error}") from error
        print(f"{args.source} is now {target.placeholder} ({target.canonical}). Old documents still restore.")
    return 0


def cmd_alias(args) -> int:
    with Vault(vault_path(args.home, args.matter)) as vault:
        entity = vault.by_placeholder(args.entity)
        if entity is None:
            raise SystemExit(f"Error: unknown id {args.entity}")
        try:
            with vault.transaction():
                vault.add_alias(entity.id, args.text)
        except ValueError as error:
            raise SystemExit(f"Error: {error}") from error
        print(f"'{args.text}' is now another name of {entity.placeholder} ({entity.canonical}).")
    return 0


def cmd_forget(args) -> int:
    with Vault(vault_path(args.home, args.matter)) as vault:
        entity = vault.by_placeholder(args.entity)
        if entity is None:
            raise SystemExit(f"Error: unknown id {args.entity}")
        vault.forget(entity.id)
        print(f"{entity.placeholder} ({entity.canonical}) is not hidden any more. Old documents still restore.")
    return 0


def cmd_split(args) -> int:
    with Vault(vault_path(args.home, args.matter)) as vault:
        entity = vault.by_placeholder(args.entity)
        if entity is None:
            raise SystemExit(f"Error: unknown id {args.entity}")
        try:
            new = vault.split(entity.id, args.text)
        except ValueError as error:
            raise SystemExit(f"Error: {error}") from error
        print(f"'{args.text}' is now {new.placeholder}. {entity.placeholder} keeps its other names.")
    return 0


def cmd_verify(args) -> int:
    from .engine import Engine

    bad = 0
    with Vault(vault_path(args.home, args.matter)) as vault:
        engine = Engine(vault)
        for name, data in read_files(args.files):
            leaks = engine.find_leaks(name, data)
            if leaks:
                bad += 1
                print(f"{name}: LEAK - text of {', '.join(leaks)} is in the file")
            else:
                print(f"{name}: ok - no known text found")
    return 1 if bad else 0


def cmd_serve(args) -> int:
    import uvicorn

    from .api import create_app

    uvicorn.run(create_app(args.home), host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lda", description="Hide and restore sensitive data in legal documents.")
    parser.add_argument("--home", type=Path, default=default_home(), help="folder for the vaults (env LDA_HOME)")
    sub = parser.add_subparsers(dest="command", required=True)
    # `--home` also works after the command. SUPPRESS keeps the value from before the command.
    home_option = argparse.ArgumentParser(add_help=False)
    home_option.add_argument("--home", type=Path, default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    def matter(p):
        p.add_argument("--matter", "-m", required=True, help="name of the case; one vault for each case")

    p = sub.add_parser("setup", help="download the models", parents=[home_option])
    p.add_argument("--level", choices=sorted(LEVELS), default="low", help="medium and high also download GLiNER")
    p.set_defaults(func=cmd_setup)

    p = sub.add_parser("text", help="show the text that the tool reads from a file (also from a PDF)", parents=[home_option])
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_text)

    p = sub.add_parser("anonymize", help="hide sensitive data in documents (.txt .md .docx .pdf)", parents=[home_option])
    p.add_argument("files", nargs="+")
    matter(p)
    p.add_argument("--out", "-o", default="anonymized", help="output folder (default: anonymized)")
    p.add_argument("--config", "-c", help="YAML file with known entities, aliases and options")
    p.add_argument("--lang", choices=["ro", "en"], help="language (default: detect for each file)")
    p.add_argument("--hide", help="comma list of entity types to hide, for example PERSON,ORGANIZATION,DATE_TIME")
    p.add_argument("--level", choices=sorted(LEVELS), help="low = BERT (fast), medium = + GLiNER, high = + local LLM (slow). Default: from the config file, or low")
    p.set_defaults(func=cmd_anonymize)

    p = sub.add_parser("restore", help="put the real data back in documents", parents=[home_option])
    p.add_argument("files", nargs="+")
    matter(p)
    p.add_argument("--out", "-o", default="restored", help="output folder (default: restored)")
    p.set_defaults(func=cmd_restore)

    p = sub.add_parser("entities", help="show what the vault holds (contains real data)", parents=[home_option])
    matter(p)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_entities)

    p = sub.add_parser("merge", help="say that two ids are one entity, for example PERSON_003 PERSON_001", parents=[home_option])
    p.add_argument("source")
    p.add_argument("target")
    matter(p)
    p.set_defaults(func=cmd_merge)

    p = sub.add_parser("alias", help="add another name to an entity", parents=[home_option])
    p.add_argument("entity", help="for example PERSON_001")
    p.add_argument("text", help="the other name")
    matter(p)
    p.set_defaults(func=cmd_alias)

    p = sub.add_parser("forget", help="stop hiding an entity that is not sensitive (the model made a mistake)", parents=[home_option])
    p.add_argument("entity", help="for example PERSON_007")
    matter(p)
    p.set_defaults(func=cmd_forget)

    p = sub.add_parser("split", help="take one name out of an entity, when the tool joined two names", parents=[home_option])
    p.add_argument("entity", help="for example PERSON_001")
    p.add_argument("text", help="the name that gets its own id")
    matter(p)
    p.set_defaults(func=cmd_split)

    p = sub.add_parser("verify", help="look for known sensitive text in files", parents=[home_option])
    p.add_argument("files", nargs="+")
    matter(p)
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("serve", help="start the local API", parents=[home_option])
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.set_defaults(func=cmd_serve)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.home = Path(args.home)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
