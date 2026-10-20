"""
Forge CLI — Migration & utility toolkit
=======================================

Usage:  python -m app.forge <command> [options]

SQLAlchemy models + Alembic are the source of truth for schema. Entity
changes are made by editing model files and generating migrations —
there is no JSON → model codegen.

Migrations:
    forge migrate                 Generate + apply a migration (autogenerate)
    forge migrate --apply-only    Apply pending migrations
    forge migrate --status        Show current revision + recent history
    forge migrate --rollback [N]  Roll back N steps (default 1)

Info / utilities:
    forge status                  DB revision at a glance
    forge seed                    Run seed_data()
    forge console                 Python REPL with app context
    forge generate-types          TypeScript interfaces from entity metadata
"""
import argparse, asyncio, importlib, os, subprocess, sys
import time, itertools, threading
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────
APP_DIR     = Path(__file__).parent
BACKEND_DIR = APP_DIR.parent

# ─────────────────────────────────────────────────────────────────────────────
# UI helpers
# ─────────────────────────────────────────────────────────────────────────────
class Spinner:
    """Minimal braille-dot spinner used as a context manager."""
    def __init__(self, msg="Working"):
        self._msg = msg
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)
    def _run(self):
        for c in itertools.cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"):
            if self._stop.is_set(): break
            sys.stdout.write(f"\r{c} {self._msg}…"); sys.stdout.flush(); time.sleep(0.08)
        sys.stdout.write("\r" + " " * 60 + "\r")
    def __enter__(self):  self._t.start(); return self
    def __exit__(self, et, ev, tb):
        self._stop.set(); self._t.join()
        print(f"{'❌' if et else '✅'} {self._msg}")

def _alembic(*args, capture=False):
    """Run an Alembic CLI command as a subprocess."""
    return subprocess.run(
        ["alembic", *args], cwd=str(BACKEND_DIR), capture_output=capture, text=True,
        env={**os.environ, "PYTHONPATH": str(BACKEND_DIR)},
    )

def cmd_generate_types(args):
    """Generate TypeScript interfaces from entity metadata into frontend/app/types/entity-types.ts."""
    # Lazy imports — forge runs standalone so we import only what we need
    from app.core.loader import load_modules
    from app.entities import load_all_entities
    from app.meta.registry import MetaRegistry
    from app.domain.constants.field_types import VALID_FIELD_TYPES

    load_modules()
    load_all_entities()

    # TS type mapping: field_type → TypeScript type string
    # Based on VALID_FIELD_TYPES from shared constants
    TS_TYPE_MAP: dict[str, str] = {
        "string": "string", "str": "string", "text": "string",
        "textarea": "string", "richtext": "string", "rich_text": "string",
        "email": "string", "phone": "string", "url": "string",
        "password": "string", "link": "string", "select": "string",
        "multiselect": "string", "data": "string", "time": "string",
        "integer": "number", "int": "number",
        "float": "number", "number": "number",
        "currency": "number", "percent": "number",
        "decimal": "number",
        "boolean": "boolean", "bool": "boolean",
        "date": "string", "datetime": "string",
        "parent_child_link": "string",
        "query_link": "string",
        "attach": "string",
        "image": "string",
        "file": "string",
        "attach_image": "string",
    }

    _SERVER = frozenset({
        "id", "created_at", "updated_at", "created_by",
        "last_modified_by", "workflow_state", "row_no",
    })

    def to_ts_name(entity_name: str) -> str:
        """Convert snake_case entity name to PascalCase interface name."""
        return "".join(part.capitalize() for part in entity_name.split("_"))

    lines: list[str] = [
        "// Auto-generated TypeScript types from entity metadata",
        "// Do not edit manually - run: python -m app.forge generate-types",
        "",
        "export interface BaseEntity {",
        "  id: string",
        "  created_at: string",
        "  updated_at: string",
        "}",
        "",
    ]

    entities = MetaRegistry.list_all()
    for entity_meta in sorted(entities, key=lambda e: e.name):
        iface_name = to_ts_name(entity_meta.name)
        lines.append(f"export interface {iface_name} extends BaseEntity {{")

        for field in entity_meta.fields:
            if field.name in _SERVER:
                continue
            if field.computed_from or field.readonly:
                # Keep readonly fields in read interface but mark optional
                ts_type = TS_TYPE_MAP.get(field.field_type.lower(), "unknown")
                lines.append(f"  {field.name}?: {ts_type}")
                continue

            ts_type = TS_TYPE_MAP.get(field.field_type.lower(), "unknown")
            suffix = "" if field.required else "?"
            lines.append(f"  {field.name}{suffix}: {ts_type}")

        lines.append("}")
        lines.append("")

    # Resolve output path relative to this file (backend/app/forge.py → frontend/app/types/)
    out_path = BACKEND_DIR.parent / "frontend" / "app" / "types" / "entity-types.ts"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ Generated {len(entities)} TypeScript interfaces → {out_path.relative_to(BACKEND_DIR.parent)}")


# ─────────────────────────────────────────────────────────────────────────────
# MIGRATE  —  manual Alembic control
# ─────────────────────────────────────────────────────────────────────────────
def cmd_migrate(args):
    if args.status:
        _alembic("current")
        _alembic("history", "-v")
        return
    if args.rollback:
        n = args.rollback
        with Spinner(f"Rolling back {n} step(s)"):
            _alembic("downgrade", f"-{n}")
        return
    if args.apply_only:
        with Spinner("Applying pending migrations"):
            _alembic("upgrade", "head")
        return
    # Default: generate + apply
    msg = args.message or f"mig_{datetime.now().strftime('%H%M%S')}"
    with Spinner(f"Generate + apply: {msg}"):
        gen = _alembic("revision", "--autogenerate", "-m", msg, capture=True)
        if gen.returncode != 0:
            print(f"\n❌ Autogenerate failed:\n{gen.stderr}"); return
        _alembic("upgrade", "head")

def cmd_status(args):
    _alembic("current")

# ─────────────────────────────────────────────────────────────────────────────
# Parser & dispatch
# ─────────────────────────────────────────────────────────────────────────────
HELP_EPILOG = """\
examples:
  forge migrate -m "add cost_code"    autogenerate + apply a migration
  forge migrate --status              check DB revision
  forge migrate --rollback 2          undo last 2 migrations
  forge generate-types                sync TypeScript interfaces from entity metadata
"""

def main():
    p = argparse.ArgumentParser(
        prog="forge",
        description="Forge — Migration & utility toolkit",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command")

    # migrate
    m = sub.add_parser("migrate", help="manual Alembic control")
    m.add_argument("-m", "--message", help="migration label")
    m.add_argument("--apply-only", action="store_true", help="only apply pending migrations")
    m.add_argument("--rollback", type=int, nargs="?", const=1, help="rollback N steps (default 1)")
    m.add_argument("--status", action="store_true", help="show current revision + history")

    # simple commands
    sub.add_parser("status", help="show DB revision")
    sub.add_parser("seed", help="run seed_data()")
    sub.add_parser("console", help="interactive Python REPL")
    sub.add_parser("generate-types", help="generate TypeScript interfaces from entity metadata")

    dispatch = {
        "migrate": cmd_migrate, "status": cmd_status,
        "seed": lambda a: asyncio.run(importlib.import_module("app.core.seed").seed_data()),
        "console": lambda a: importlib.import_module("code").interact(local={"app": importlib.import_module("app")}),
        "generate-types": cmd_generate_types,
    }

    args = p.parse_args()
    fn = dispatch.get(args.command)
    if fn:
        fn(args)
    else:
        p.print_help()

if __name__ == "__main__":
    main()