"""Codex command-hook adapter. JSON stdin/stdout; deterministic, bounded, no LLM/build.

These checks reduce mistakes. They cannot mediate arbitrary shell, MCP, hosted tools
or same-user filesystem writes. Never treat a hook as a complete authorization gate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any
from .core import ProtocolError, Store, digest, json_object

EVENTS = ("SessionStart", "PreToolUse", "PostToolUse", "PreCompact", "PostCompact",
          "SubagentStart", "SubagentStop", "Stop", "SessionEnd")
MAX_BYTES = 2 * 1024 * 1024


def context(event: str, message: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": message[:3600]}}


def deny(reason: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                    "permissionDecisionReason": reason}}


def protected(name: str, root: Path, cwd: Path) -> bool:
    # Resolve lexical tool paths relative to the actual tool cwd, not process cwd.
    p = Path(name)
    p = p if p.is_absolute() else cwd / p
    p = p.resolve(strict=False)
    return p == root / ".mathprove" or p.is_relative_to(root / ".mathprove")


def pretool(payload: dict, root: Path) -> dict:
    tool = str(payload.get("tool_name", ""))
    inp = payload.get("tool_input", {})
    inp = inp if isinstance(inp, dict) else {}
    cwd = Path(str(payload.get("cwd") or root)).expanduser().resolve()
    names = [inp[k] for k in ("file_path", "path", "file", "destination") if isinstance(inp.get(k), str)]
    if tool in ("apply_patch", "Edit", "Write", "write_file", "edit_file"):
        patch = inp.get("command", inp.get("patch", ""))
        if isinstance(patch, str):
            names += re.findall(r"^\*\*\* (?:Update File|Add File|Delete File|Move to):\s*(.+)$", patch, re.M)
        if any(protected(name, root, cwd) for name in names):
            return deny("Use the MathProve controller; direct edits of .mathprove state/evidence/receipts are not permitted by the research protocol.")
    command = inp.get("command", inp.get("cmd", ""))
    if tool in ("Bash", "exec_command", "shell") and isinstance(command, str):
        # Narrow accidental self-approval check, not a claim to parse arbitrary shell.
        if "mathprove" in command.lower() and re.search(r"\breview\b", command) and "--human-ack" in command:
            return deny("Human review is an operator action outside agent execution. Return the snapshot for the human to review; do not self-sign it.")
        if re.search(r"\bsqlite3?\b", command) and ".mathprove" in command and re.search(r"\b(UPDATE|INSERT|DELETE|DROP|REPLACE|ALTER)\b", command, re.I):
            return deny("Direct state SQL mutation bypasses the controller. Use its documented commands.")
    return {}  # No 'allow': preserve the host's own permission decisions.


def handle(payload: Any, event: str, root: Path, explicit_run: str | None = None) -> dict:
    if not isinstance(payload, dict): raise ProtocolError("Hook input must be a JSON object")
    if event not in EVENTS: raise ProtocolError("Unsupported hook event")
    if payload.get("hook_event_name") not in (None, event):
        raise ProtocolError("Configured hook event does not match payload")
    root = root.expanduser().resolve()
    if event == "PreToolUse":
        blocked = pretool(payload, root)
        if blocked: return blocked
        return {}  # Critical hot path: no DB read or write for neutral tool calls.
    if not (root / ".mathprove/state.sqlite3").is_file():
        return context(event, "MathProve is installed but no workspace is initialized. Do not invent prior state.") if event in ("SessionStart", "SubagentStart") else {}
    store = Store(root)
    session = str(payload.get("session_id") or "unknown")[:256]
    run = explicit_run or store.session_run(session)
    if run is None:
        return context(event, "MathProve: no unambiguous active run. Use list/status and explicitly bind this session; never guess between projects.") if event in ("SessionStart", "SubagentStart") else {}
    if event in ("SessionStart", "SubagentStart"):
        return context(event, store.brief(run))
    if event == "PostToolUse":
        uid = payload.get("tool_use_id")
        # Do not persist raw commands, tool responses, tokens or transcript contents.
        data = {"session_hash": hashlib.sha256(session.encode()).hexdigest(),
                "tool_name": str(payload.get("tool_name", "unknown"))[:128],
                "input_hash": digest(payload.get("tool_input")),
                "response_hash": digest(payload.get("tool_response")), "proof_authority": "none"}
        key = digest([session, str(uid), event]) if uid else None
        store.hook_event(run, event, data, key)
        return {}
    if event in ("PreCompact", "PostCompact", "Stop", "SubagentStop", "SessionEnd"):
        store.checkpoint(run, "hook:" + event)
        if event in ("PreCompact", "PostCompact"):
            return {"systemMessage": "MathProve checkpoint saved. Restore current metadata with status; do not treat a saved summary as proof."}
        # Pausing is a legitimate outcome; never force an unbounded prove-until-success loop.
        return {}
    return {}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    p.add_argument("--event", choices=EVENTS, required=True)
    p.add_argument("--run")
    a = p.parse_args(argv)
    payload: Any = {}
    try:
        raw = sys.stdin.buffer.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES: raise ProtocolError("Hook payload exceeds 2 MiB")
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=json_object,
                             parse_constant=lambda x: (_ for _ in ()).throw(ProtocolError("Invalid numeric JSON")))
        output = handle(payload, a.event, Path(a.root), a.run)
        print(json.dumps(output, ensure_ascii=False, allow_nan=False))
        return 0
    except Exception as e:
        # No tracebacks or input echoes (could contain credentials). Stop failure blocks at most once.
        print("MathProve hook error: " + type(e).__name__, file=sys.stderr)
        if a.event == "PreToolUse":
            print(json.dumps(deny("MathProve pre-tool guard failed. Inspect the hook configuration before retrying.")))
        elif a.event in ("Stop", "SubagentStop") and not (isinstance(payload, dict) and payload.get("stop_hook_active")):
            print(json.dumps({"decision": "block", "reason": "MathProve could not persist a checkpoint. Save the unresolved status, repair the workspace, or explicitly pause; do not claim verification."}))
        else:
            print(json.dumps({"systemMessage": "MathProve checkpoint/context unavailable; inspect workspace state manually."}))
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
