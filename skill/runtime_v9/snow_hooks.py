"""Translate Snow CLI/App hook events to the MathProve v9 controller protocol."""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import shlex
import sys
from typing import Any

from .hooks import MAX_BYTES, handle

EVENT_MAP = {
    "onSessionStart": "SessionStart",
    "beforeToolCall": "PreToolUse",
    "afterToolCall": "PostToolUse",
    "beforeCompress": "PreCompact",
    "beforeSubAgentStart": "SubagentStart",
    "onSubAgentComplete": "SubagentStop",
    "onStop": "Stop",
}
RULE_PREFIX = "MathProve v9 Snow: "


def research_root(context: dict[str, Any]) -> Path | None:
    cwd = context.get("cwd") or os.environ.get("SNOW_CWD") or os.getcwd()
    try:
        path = Path(str(cwd)).expanduser().resolve()
    except (OSError, ValueError):
        return None
    for candidate in (path, *path.parents):
        if (candidate / ".mathprove/state.sqlite3").is_file():
            return candidate
    return None


def translated_tool(context: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    name = str(context.get("toolName") or context.get("tool_name") or "")
    args = context.get("args", context.get("tool_input", {}))
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except (ValueError, TypeError):
            args = {"command": args} if name in ("terminal-execute", "BashToolCall") else {}
    args = dict(args) if isinstance(args, dict) else {}
    if "filePath" in args:
        args["file_path"] = args["filePath"]
    if "sourcePath" in args:
        args["file_path"] = args["sourcePath"]
    if "destinationPath" in args:
        args["destination"] = args["destinationPath"]
    if name.startswith("filesystem-"):
        return "Edit", args
    if name in ("terminal-execute", "BashToolCall"):
        return "shell", args
    return name, args


def dispatch(event: str, context: Any, host: str) -> tuple[int, dict[str, Any] | None, str | None]:
    if event not in EVENT_MAP or host not in ("cli", "app"):
        raise ValueError("Unsupported Snow hook event or host")
    if not isinstance(context, dict):
        raise ValueError("Snow hook input must be a JSON object")
    root = research_root(context)
    if root is None:
        return 0, None, None
    tool_name, tool_input = translated_tool(context)
    payload = {
        "hook_event_name": EVENT_MAP[event],
        "session_id": context.get("sessionId") or context.get("session_id") or os.environ.get("SNOW_SESSION_ID"),
        "cwd": context.get("cwd") or str(root),
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_response": context.get("result"),
        "tool_use_id": context.get("toolUseId") or context.get("tool_use_id"),
    }
    output = handle(payload, EVENT_MAP[event], root)
    if event == "beforeToolCall":
        decision = output.get("hookSpecificOutput", {})
        if decision.get("permissionDecision") == "deny":
            return (1 if host == "cli" else 2), None, str(decision.get("permissionDecisionReason") or "MathProve blocked this tool call")
    message = output.get("hookSpecificOutput", {}).get("additionalContext")
    if message and event in ("onSessionStart", "beforeSubAgentStart"):
        return 0, {"additionalContext": message}, None
    return 0, None, None


def command_for(script: Path, event: str, host: str, python: str) -> str:
    argv = [python, str(script), "--event", event, "--host", host]
    if os.name == "nt":
        script_text = "& " + " ".join("'" + arg.replace("'", "''") + "'" for arg in argv) + "; exit $LASTEXITCODE"
        encoded = base64.b64encode(script_text.encode("utf-16le")).decode("ascii")
        return "powershell.exe -NoProfile -NonInteractive -EncodedCommand " + encoded
    return shlex.join(argv)


def merge_rules(existing: list[Any], event: str, script: Path, host: str, python: str) -> list[Any]:
    if not isinstance(existing, list):
        raise ValueError("Snow hook rules must be an array")
    marker = RULE_PREFIX + event
    other = [rule for rule in existing if not (isinstance(rule, dict) and rule.get("description") == marker)]
    rule: dict[str, Any] = {
        "description": marker,
        "hooks": [{"type": "command", "command": command_for(script, event, host, python), "timeout": 5000, "enabled": True}],
    }
    if event in ("beforeToolCall", "afterToolCall"):
        names = "filesystem-*,terminal-execute" if event == "beforeToolCall" else "*"
        rule["matcher"] = names if host == "cli" else ",".join("toolName:" + item for item in names.split(","))
    return other + [rule]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", choices=EVENT_MAP, required=True)
    parser.add_argument("--host", choices=("cli", "app"), required=True)
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.buffer.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Snow hook input exceeds 2 MiB")
        context = json.loads(raw.decode("utf-8"))
        code, output, error = dispatch(args.event, context, args.host)
        if output is not None:
            print(json.dumps(output, ensure_ascii=False, allow_nan=False))
        if error is not None:
            print(error, file=sys.stderr)
        return code
    except Exception as exc:
        print("MathProve Snow hook error: " + type(exc).__name__, file=sys.stderr)
        if args.event == "beforeToolCall":
            return 1 if args.host == "cli" else 2
        return 0
