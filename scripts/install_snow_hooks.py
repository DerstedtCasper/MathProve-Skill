#!/usr/bin/env python3
"""Install MathProve v9 hook rules for Snow CLI and Snow App without replacing other rules."""
from __future__ import annotations

import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skill"))
from runtime_v9.core import atomic_write
from runtime_v9.snow_hooks import EVENT_MAP, merge_rules


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def install(cli_dir: Path, app_db: Path, script: Path, backup_dir: Path, python: str, *, apply: bool = False) -> dict:
    cli_dir = cli_dir.resolve()
    app_db = app_db.resolve()
    script = script.resolve()
    backup_dir = backup_dir.resolve()
    if not cli_dir.is_dir() or not app_db.is_file() or not script.is_file():
        raise ValueError("Snow CLI hook directory, App database, and adapter script must exist")
    if not Path(python).is_file():
        raise ValueError("Python interpreter must be an existing absolute file")

    cli_changes: dict[Path, bytes] = {}
    previous: dict[Path, bytes | None] = {}
    for event in EVENT_MAP:
        path = cli_dir / f"{event}.json"
        old = path.read_bytes() if path.is_file() else None
        existing = json.loads(old.decode("utf-8")) if old is not None else {}
        if not isinstance(existing, dict):
            raise ValueError("Invalid Snow CLI hook file: " + str(path))
        updated = dict(existing)
        updated[event] = merge_rules(existing.get(event, []), event, script, "cli", python)
        data = _json_bytes(updated)
        if old != data:
            cli_changes[path] = data
            previous[path] = old

    with closing(sqlite3.connect(f"file:{app_db.as_posix()}?mode=rw", uri=True, timeout=10)) as db:
        row = db.execute("SELECT id, setting_value FROM system_settings WHERE setting_code=?", ("hooks_global",)).fetchone()
        app_existing = json.loads(row[1]) if row else {}
        if not isinstance(app_existing, dict):
            raise ValueError("Invalid Snow App global hook settings")
        app_updated = dict(app_existing)
        for event in EVENT_MAP:
            app_updated[event] = merge_rules(app_existing.get(event, []), event, script, "app", python)
        app_changed = app_updated != app_existing

    result = {"applied": apply, "changed": bool(cli_changes or app_changed),
              "cli_events": list(EVENT_MAP), "cli_changed": [path.name for path in cli_changes],
              "app_changed": app_changed, "backup": None}
    if not apply or not result["changed"]:
        return result

    backup = backup_dir / uuid.uuid4().hex
    backup.mkdir(parents=True, exist_ok=False)
    with closing(sqlite3.connect(f"file:{app_db.as_posix()}?mode=ro", uri=True)) as source_db, closing(sqlite3.connect(backup / "snowapp.db")) as backup_db:
        source_db.backup(backup_db)
    for path, old in previous.items():
        if old is not None:
            atomic_write(backup / path.name, old)
    written: list[Path] = []
    try:
        for path, data in cli_changes.items():
            atomic_write(path, data)
            written.append(path)
        if app_changed:
            with closing(sqlite3.connect(f"file:{app_db.as_posix()}?mode=rw", uri=True, timeout=10)) as db:
                db.execute("BEGIN IMMEDIATE")
                current = db.execute("SELECT id, setting_value FROM system_settings WHERE setting_code=?", ("hooks_global",)).fetchone()
                if (current[1] if current else None) != (row[1] if row else None):
                    raise RuntimeError("Snow App hooks changed during installation")
                value = json.dumps(app_updated, ensure_ascii=False, separators=(",", ":"))
                if current:
                    db.execute("UPDATE system_settings SET setting_value=?, updated_at=datetime('now','localtime') WHERE id=?", (value, current[0]))
                else:
                    db.execute("INSERT INTO system_settings (id,setting_name,setting_code,setting_value) VALUES (?,?,?,?)",
                               (uuid.uuid4().hex, "Hooks config", "hooks_global", value))
                db.commit()
    except BaseException:
        for path in reversed(written):
            old = previous[path]
            if old is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, old)
        raise
    result["backup"] = str(backup)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli-dir", type=Path, required=True)
    parser.add_argument("--app-db", type=Path, required=True)
    parser.add_argument("--skill-root", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--python", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        result = install(args.cli_dir, args.app_db, args.skill_root / "scripts/mathprove_snow_hook.py",
                         args.backup_dir, args.python, apply=args.apply)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
