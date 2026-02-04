"""Math MAGI protocol helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .roles import DEFAULT_ROLES


def _missing_expected_evidence(steps: list[dict]) -> list[str]:
    missing = []
    for step in steps:
        expected = str(step.get("expected_evidence") or "").strip()
        if not expected:
            missing.append(str(step.get("id") or "S?"))
    return missing


def run_round(problem: str, context: dict, force_veto: bool = False) -> dict:
    steps = context.get("steps") or []
    round_record: dict[str, Any] = {
        "problem": problem,
        "steps": steps,
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
