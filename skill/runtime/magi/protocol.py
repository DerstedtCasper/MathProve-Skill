"""Math MAGI protocol helpers."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    from ..config_loader import detect_skill_root
except Exception:  # pragma: no cover
    from runtime.config_loader import detect_skill_root

from .roles import DEFAULT_ROLES


def _missing_expected_evidence(steps: list[dict]) -> list[str]:
    missing = []
    for step in steps:
        expected = str(step.get("expected_evidence") or "").strip()
        if not expected:
            missing.append(str(step.get("id") or "S?"))
    return missing


def _load_prompts() -> tuple[dict[str, str], list[str]]:
    root = detect_skill_root()
    prompt_dir = root / "assets" / "magi_prompts"
    files = {
        "melchior": prompt_dir / "melchior_system.txt",
        "balthasar": prompt_dir / "balthasar_system.txt",
        "casper": prompt_dir / "casper_system.txt",
    }
    prompts: dict[str, str] = {}
    missing: list[str] = []
    for key, path in files.items():
        if path.exists():
            prompts[key] = path.read_text(encoding="utf-8")
        else:
            prompts[key] = ""
            missing.append(str(path))
    return prompts, missing


def run_round(problem: str, context: dict, force_veto: bool = False) -> dict:
    prompts, missing_prompts = _load_prompts()
    steps = context.get("steps") or []
    round_record: dict[str, Any] = {
        "problem": problem,
        "steps": steps,
        "prompts": {k: {"chars": len(v)} for k, v in prompts.items()},
        "prompt_missing": missing_prompts,
        "roles": {},
        "revised_plan_required": False,
    }

    missing_evidence = _missing_expected_evidence(steps)
    for role in DEFAULT_ROLES:
        vote = "APPROVE"
        reasons: list[str] = []
        if force_veto:
            vote = "VETO"
            reasons.append("force_veto enabled")
        if not steps:
            vote = "VETO"
            reasons.append("no steps in plan")
        if missing_evidence and role.key in {"casper", "melchior"}:
            vote = "VETO"
            reasons.append(f"missing expected_evidence for: {', '.join(missing_evidence)}")
        round_record["roles"][role.key] = {"vote": vote, "reasons": reasons}

    return round_record


def collect_votes(round_record: dict) -> dict:
    veto_reasons: list[str] = []
    veto_roles: list[str] = []
    for key, info in (round_record.get("roles") or {}).items():
        if str(info.get("vote") or "").upper() == "VETO":
            veto_roles.append(key)
            veto_reasons.extend(info.get("reasons") or [])
    return {"has_veto": bool(veto_roles), "veto_roles": veto_roles, "veto_reasons": veto_reasons}


def revise_plan(round_record: dict, veto_reasons: list[str]) -> dict:
    context = deepcopy(round_record)
    steps = context.get("steps") or []
    for step in steps:
        if not str(step.get("expected_evidence") or "").strip():
            route = step.get("route") or step.get("engine") or "unknown"
            if route in {"sympy", "hybrid"}:
                step["expected_evidence"] = "sympy output: simplify(...) == 0"
            elif route in {"lean4"}:
                step["expected_evidence"] = "lean build success (no goals, no sorries)"
            else:
                step["expected_evidence"] = "manual justification required"
    context["revised_plan_required"] = bool(veto_reasons)
    return context
