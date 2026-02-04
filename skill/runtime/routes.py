"""Route detection helpers for MathProve."""

from __future__ import annotations

import os
from copy import deepcopy
from typing import Any


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def detect_subagent_capability(env: dict[str, str] | None = None) -> dict[str, Any]:
    env = env or os.environ
    driver = env.get("MATHPROVE_SUBAGENT_DRIVER", "")
    enabled = _truthy(env.get("MATHPROVE_SUBAGENT")) or bool(driver)

    for key in (
        "CODEX_SUBAGENT",
        "CODEX_SUBAGENTS",
        "MULTI_AGENT",
        "SUBAGENT",
        "SUBAGENTS",
    ):
        enabled = enabled or _truthy(env.get(key))

    return {
        "enabled": bool(enabled),
        "driver": driver,
        "signals": {k: env.get(k, "") for k in ["MATHPROVE_SUBAGENT", "MATHPROVE_SUBAGENT_DRIVER"]},
    }


def apply_subagent_auto_enable(config: dict, env: dict[str, str] | None = None) -> dict:
    cfg = deepcopy(config)
    routes = cfg.setdefault("routes", {})
    sub = routes.setdefault("subagent", {})
    cap = detect_subagent_capability(env)

    enabled = bool(sub.get("enabled"))
    auto_enable = bool(sub.get("auto_enable", True))
    auto_enabled = False
    if not enabled and auto_enable and cap.get("enabled"):
        enabled = True
        auto_enabled = True

    sub["enabled"] = enabled
    sub["auto_enabled"] = auto_enabled
    sub["capability"] = cap
    return cfg

