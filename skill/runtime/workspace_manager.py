"""Workspace and run directory management for MathProve."""

from __future__ import annotations

import os
import secrets
import time
from pathlib import Path

from .config_loader import detect_skill_root, load_config

_RUN_DIR_ENV = "MATHPROVE_RUN_DIR"
_WORKSPACE_ENV_KEYS = (
    "MATHPROVE_WORKSPACE",
    "MATHPROVE_WORKSPACE_DIR",
    "WORKSPACE",
)

_DEFAULT_RUN_DIR: Path | None = None


def _resolve_path(raw: str, base: Path) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        return (base / path).resolve()
    return path.resolve()


def resolve_workspace_dir(
    workspace_dir: str | None = None,
    config: dict | None = None,
    env: dict[str, str] | None = None,
) -> Path:
    env = env or os.environ
    skill_root = detect_skill_root()

    if workspace_dir:
        return _resolve_path(workspace_dir, skill_root)

    for key in _WORKSPACE_ENV_KEYS:
        value = env.get(key)
        if value:
            return _resolve_path(value, skill_root)

    cfg = config or load_config(skill_root)
    cfg_workspace = cfg.get("workspace_dir") or (cfg.get("paths") or {}).get("workspace_dir")
    if cfg_workspace:
        return _resolve_path(str(cfg_workspace), skill_root)

    return (skill_root.parent / "mathprove_workspace").resolve()


def generate_run_id() -> str:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    suffix = secrets.token_hex(3)
    return f"run_{stamp}_{suffix}"


def ensure_run_dir(
    run_dir: str | Path | None = None,
    workspace_dir: str | None = None,
    create_subdirs: bool = True,
) -> Path:
    global _DEFAULT_RUN_DIR

    if run_dir is None:
        env_run = os.environ.get(_RUN_DIR_ENV)
        if env_run:
            run_dir = env_run
        elif _DEFAULT_RUN_DIR is not None:
            run_dir = _DEFAULT_RUN_DIR

    if run_dir is None:
        base = resolve_workspace_dir(workspace_dir)
        run_dir = base / generate_run_id()
    else:
        base = resolve_workspace_dir(workspace_dir)
        run_path = Path(run_dir)
        run_dir = run_path if run_path.is_absolute() else (base / run_path)

    run_path = Path(run_dir).resolve()
    run_path.mkdir(parents=True, exist_ok=True)

    if create_subdirs:
        for name in ("logs", "draft", "evidence", "audit", "magi", "sympy", "lean", "plan"):
            (run_path / name).mkdir(parents=True, exist_ok=True)

    os.environ[_RUN_DIR_ENV] = str(run_path)
    _DEFAULT_RUN_DIR = run_path
    return run_path


def run_path(run_dir: str | Path | None, relative: str) -> Path:
    base = ensure_run_dir(run_dir)
    rel = Path(relative)
    return rel if rel.is_absolute() else (base / rel)
