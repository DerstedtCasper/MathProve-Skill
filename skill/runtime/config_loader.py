"""Config loader for MathProve skill.

Supports optional local override via config.local.yaml. If PyYAML is not
available, a small YAML subset parser is used (nested mappings + scalars).
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any


def _walk_up(start: Path) -> list[Path]:
    out: list[Path] = []
    cur = start.resolve()
    while True:
        out.append(cur)
        if cur.parent == cur:
            return out
        cur = cur.parent


def detect_skill_root() -> Path:
    here = Path(__file__).resolve()
    for p in _walk_up(here.parent):
        if (p / "SKILL.md").exists():
            return p
        if (p / "skill" / "SKILL.md").exists():
            return p / "skill"
    return here.parents[2]


def _strip_comment(line: str) -> str:
    if "#" not in line:
        return line
    # Keep it simple: treat everything after '#' as comment.
    return line.split("#", 1)[0]


def _parse_value(value: str) -> Any:
    v = value.strip()
    if not v:
        return ""
    if (v.startswith("\"") and v.endswith("\"")) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    low = v.lower()
    if low in {"true", "yes", "on"}:
        return True
    if low in {"false", "no", "off"}:
        return False
    if low in {"null", "none"}:
        return None
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        return v


def _simple_yaml_load(text: str) -> dict:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for raw in text.splitlines():
        line = _strip_comment(raw).rstrip("\n")
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.lstrip(" ")
        key, sep, value = stripped.partition(":")
        if not sep:
            continue
        key = key.strip()
        value = value.strip()

        while indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if value == "":
            node: dict[str, Any] = {}
            parent[key] = node
            stack.append((indent, node))
        else:
            parent[key] = _parse_value(value)

    return root


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        return data or {}
    except Exception:
        return _simple_yaml_load(text)


def _deep_merge(base: dict, override: dict) -> dict:
    out = deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def default_config() -> dict:
    return {
        "skill": {"name": "mathprove", "version": "3.0.0"},
        "paths": {"python": "python", "lean": "lean", "lake": "lake"},
        "routes": {
            "sympy": {"enabled": True, "python": "python", "timeout_seconds": 20},
            "lean": {
                "enabled": True,
                "lean_cmd": "lean",
                "lake_cmd": "lake",
                "timeout_seconds": 120,
                "watchdog_no_output_seconds": 30,
                "static_precheck": True,
                "require_mathlib": True,
            },
            "web": {"enabled": False, "provider": None},
            "subagent": {
                "enabled": False,
                "auto_enable": True,
                "mode": "none",
                "driver": "",
                "endpoint": "",
                "note": "",
            },
        },
    }


def load_config(skill_root: Path | None = None) -> dict:
    sr = skill_root or detect_skill_root()
    base_path = sr / "config.yaml"
    local_path = sr / "config.local.yaml"

    base_cfg = _load_yaml(base_path)
    local_cfg = _load_yaml(local_path)
    merged = _deep_merge(default_config(), base_cfg)
    merged = _deep_merge(merged, local_cfg)
    return merged


def config_paths(skill_root: Path | None = None) -> tuple[Path, Path]:
    sr = skill_root or detect_skill_root()
    return sr / "config.yaml", sr / "config.local.yaml"
