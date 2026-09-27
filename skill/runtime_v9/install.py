"""Project-local native Codex installer; merge, backup, no trust/permission changes."""
from __future__ import annotations
import argparse
import base64
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import uuid
from .core import VERSION, ROLES, ProtocolError, atomic_write, dumps, safe_path, strict_json
from .hooks import EVENTS

TAG = "MathProve v9: "
READ_ONLY = {"librarian", "refuter", "auditor"}


def agent_config(skill_source: Path, role: str) -> str:
    common = (skill_source / "assets/v9/roles/common.md").read_text(encoding="utf-8")
    body = (skill_source / f"assets/v9/roles/{role}.md").read_text(encoding="utf-8")
    method = (skill_source / "assets/v9/research-method.md").read_text(encoding="utf-8")
    # JSON basic strings are TOML-compatible for this generated text; use ensure_ascii=False
    # (JSON surrogate escapes would not be legal TOML for non-BMP characters).
    fields = {"name": "mp_" + role, "description": body.splitlines()[0].lstrip("# "),
              "developer_instructions": common + "\n\n" + method + "\n\n" + body}
    if role in READ_ONLY: fields["sandbox_mode"] = "read-only"
    return "# Generated from shared MathProve v9 role sources. No model is hard-coded.\n" + "\n".join(k + " = " + json.dumps(v, ensure_ascii=False) for k,v in fields.items()) + "\n"


def hook_group(root: Path, skill_dest: Path, event: str) -> dict:
    args = [sys.executable, str(skill_dest / "scripts/mathprove_hook.py"), "--root", str(root), "--event", event]
    # Use explicit PowerShell with a safely encoded argv expression, not an implicit
    # unknown Windows shell. Live Windows/Codex execution is still an open validation item.
    ps_script = "& " + " ".join("'" + arg.replace("'", "''") + "'" for arg in args)
    windows_command = "powershell.exe -NoProfile -NonInteractive -EncodedCommand " + base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")
    handler = {"type": "command", "command": shlex.join(args),
               "commandWindows": windows_command,
               "timeout": 3 if event == "SessionEnd" else 10,
               "statusMessage": TAG + event}
    if event in {"SessionStart", "SubagentStart"}:
        handler["additionalContextLimit"] = 1500
    group: dict = {"hooks": [handler]}
    if event == "PreToolUse": group["matcher"] = "^(Bash|apply_patch|Edit|Write|exec_command|shell|write_file|edit_file)$"
    if event == "PostToolUse": group["matcher"] = "^(Bash|apply_patch|Edit|Write|exec_command|shell|write_file|edit_file)$"
    return group


def merge_hooks(existing: dict, root: Path, dest: Path) -> dict:
    if not isinstance(existing, dict) or not isinstance(existing.get("hooks", {}), dict):
        raise ProtocolError("Existing hooks.json is not a compatible JSON object")
    merged = json.loads(dumps(existing))
    hooks = merged.setdefault("hooks", {})
    for event in EVENTS:
        groups = hooks.get(event, [])
        if not isinstance(groups, list): raise ProtocolError("Existing hook event must be a matcher-group array: " + event)
        kept = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                raise ProtocolError("Malformed existing hook group; refusing to overwrite")
            clone = dict(group)
            # Preserve unrelated handlers even when they share one matcher group.
            clone["hooks"] = [h for h in group["hooks"] if not (isinstance(h, dict) and str(h.get("statusMessage", "")).startswith(TAG) and "mathprove_hook.py" in str(h.get("command", "")))]
            if clone["hooks"]: kept.append(clone)
        hooks[event] = kept + [hook_group(root, dest, event)]
    merged.setdefault("description", "Project hooks; MathProve v9 entries are merged, not exclusive.")
    return merged


def source_files(source: Path) -> list[Path]:
    selected = []
    for p in sorted(source.rglob("*")):
        rel = p.relative_to(source)
        if any(x in {"__pycache__", ".git", ".mathprove", "WORKSPACE"} for x in rel.parts): continue
        if p.is_symlink(): raise ProtocolError("Installer source must not contain symlinks")
        if not p.is_file() or p.suffix == ".pyc": continue
        # Additive overlay must not silently reinstall an uninspected v8 runtime.
        name = rel.as_posix()
        if name in {"SKILL.md", "agent.md", "agents/openai.yaml", "scripts/mathprove.py", "scripts/mathprove_hook.py"} or name.startswith(("runtime_v9/", "assets/v9/", "references/v9/")):
            selected.append(p)
    if not (source / "SKILL.md").is_file(): raise ProtocolError("Missing skill/SKILL.md")
    return selected


def install(source: Path, root: Path, *, upgrade: bool = False, dry_run: bool = False, hooks: bool = True, agents: bool = True) -> dict:
    source = source.expanduser().resolve(); root = root.expanduser().resolve()
    if not root.is_dir(): raise ProtocolError("Target research project must be an existing directory")
    dest = safe_path(root, ".agents/skills/mathprove-skill")
    writes: dict[Path, bytes] = {safe_path(root, dest / p.relative_to(source)): p.read_bytes() for p in source_files(source)}
    marker = safe_path(root, dest / ".mathprove-v9-install.json")
    managed = marker.is_file()
    if dest.exists() and any(dest.iterdir()) and not managed and not upgrade and not dry_run:
        raise ProtocolError("Existing unmarked skill; use --upgrade after reviewing the dry-run and backup plan")
    if managed and not upgrade and not dry_run:
        for path, data in writes.items():
            if path.exists() and path.read_bytes() != data:
                raise ProtocolError("Existing skill differs; review --dry-run then use --upgrade for backed-up replacement")
    if agents:
        for role in ROLES:
            path = safe_path(root, f".codex/agents/mp_{role}.toml")
            data = agent_config(source, role).encode("utf-8")
            if path.exists() and path.read_bytes() != data and not upgrade and not dry_run:
                raise ProtocolError("Existing agent differs: " + str(path) + "; use --upgrade after review")
            writes[path] = data
    if hooks:
        path = safe_path(root, ".codex/hooks.json")
        old = strict_json(path) if path.is_file() else {}
        writes[path] = (json.dumps(merge_hooks(old, root, dest), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    writes[marker] = (dumps({"schema": "mathprove.install.v9", "version": VERSION, "root": str(root), "interpreter": sys.executable}) + "\n").encode()
    changes = {p: data for p, data in writes.items() if not p.is_file() or p.read_bytes() != data}
    result = {"version": VERSION, "root": str(root), "skill": str(dest), "dry_run": dry_run,
              "changed_paths": [p.relative_to(root).as_posix() for p in changes],
              "host_trust_modified": False, "next_action": "Review project trust and /hooks in Codex; restart to discover custom agents. Rerun installer after moving the project."}
    if dry_run: return result
    backup = safe_path(root, ".mathprove-install-backups/" + uuid.uuid4().hex)
    written: list[Path] = []
    previous: dict[Path, bytes | None] = {}
    try:
        for path, data in changes.items():
            old_data = path.read_bytes() if path.is_file() else None
            previous[path] = old_data
            if old_data is not None:
                atomic_write(safe_path(root, backup / path.relative_to(root)), old_data)
            atomic_write(path, data)
            written.append(path)
    except BaseException:
        for path in reversed(written):
            old = previous[path]
            if old is None: path.unlink(missing_ok=True)
            else: atomic_write(path, old)
        raise
    result["backup"] = str(backup) if backup.exists() else None
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Install v9 skill, native Codex hooks and role templates without changing approval settings")
    p.add_argument("--project", required=True); p.add_argument("--upgrade", action="store_true"); p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-hooks", action="store_true"); p.add_argument("--no-agents", action="store_true")
    a = p.parse_args(argv)
    try:
        result = install(Path(__file__).resolve().parents[1], Path(a.project), upgrade=a.upgrade, dry_run=a.dry_run, hooks=not a.no_hooks, agents=not a.no_agents)
        print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
    except (ProtocolError, OSError, ValueError) as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr); return 2
