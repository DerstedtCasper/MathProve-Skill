#!/usr/bin/env python3
"""Protocol regression tests for MathProve Ultra v8.

These tests do not require Lean. They verify the safety/control protocol that
prevents unverified branches from being promoted.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.moe_router_v8 import activate, FULL_PANEL
from runtime.proof_factory_v8 import (
    AgentRole,
    CandidateEvidence,
    Stage,
    demo_decision,
    lean_static_audit,
    make_budget_contract,
    select_candidate,
    stable_hash,
    termination_allowed,
    validate_line_map,
    write_context_shard,
    write_memory_event,
    load_memory_events,
    ProofMemoryEvent,
)


def record(name: str, status: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "PASS" if status else "FAIL", "detail": detail}


def run() -> dict[str, object]:
    results: list[dict[str, str]] = []

    decision = demo_decision(frontier=True)
    results.append(record("evidence_weighted_selection", decision.accepted and decision.selected_candidate_id == "compiled_patch", json.dumps(decision.to_dict(), ensure_ascii=False)))

    bad = CandidateEvidence("drift", Stage.LEMMA_SPRINT, AgentRole.TACTIC_SPRINTER, claim="drift", artifact_paths=["x.lean"], tool_logs=["x.log"], lean_passed=True, no_sorry=True, expected_statement_hash="a", theorem_statement_hash="b", quota_observations={"candidate_packs": 1})
    drift_decision = select_candidate([bad], frontier=True)
    results.append(record("statement_drift_veto", not drift_decision.accepted and "theorem statement drift" in drift_decision.scores[0].veto_reasons, str(drift_decision.scores[0].veto_reasons)))

    ok_skel, skel_violations = lean_static_audit("theorem t : True := by sorry", Stage.SKELETON)
    ok_final, final_violations = lean_static_audit("theorem t : True := by sorry", Stage.FINAL_AUDIT)
    results.append(record("skeleton_sorry_only", ok_skel and not ok_final and "sorry" in final_violations, f"skeleton={skel_violations}, final={final_violations}"))

    lm_ok, lm_errors = validate_line_map([
        {"line_id": "L1", "formal_target": "lemma_a", "obligation": "prove A", "depends_on": []},
        {"line_id": "L2", "formal_target": "lemma_b", "obligation": "prove B", "depends_on": ["L1"]},
    ])
    lm_bad, lm_bad_errors = validate_line_map([{"line_id": "L1", "formal_target": "x", "obligation": "", "depends_on": ["L1"]}])
    results.append(record("line_map_guard", lm_ok and not lm_bad and any("self dependency" in e for e in lm_bad_errors), str(lm_bad_errors)))

    budget = make_budget_contract("frontier").to_dict()
    results.append(record("budget_contract_frontier", budget["local_context_target_tokens"] >= 1_000_000 and budget["global_campaign_target_tokens"] >= 20_000_000 and budget["minimum_wall_clock_hours"] >= 24, json.dumps(budget, ensure_ascii=False)))

    term_ok, term_reason = termination_allowed({"final_audit_approved": False, "local_context_exhausted": True})
    term_ok2, term_reason2 = termination_allowed({"environment_blocker_with_replay_log": True})
    results.append(record("no_premature_termination", (not term_ok) and term_ok2, f"{term_reason}; {term_reason2}"))

    full = activate("lemma_sprint", difficulty="frontier")
    normal = activate("notation")
    results.append(record("moe_full_panel_escalation", set(full) == set(FULL_PANEL) and "formalizer" in normal and "auditor" in normal, ",".join(full)))

    with tempfile.TemporaryDirectory() as tmp:
        shard = write_context_shard(tmp, Stage.NOTATION, "ledger", "x : Nat\n", "Nat variable fixed")
        event = ProofMemoryEvent("lemma", "Nat.add_zero", "proves", {"lean": "Nat.add_zero"}, Stage.LEMMA_SPRINT.value, shard.shard_id).finalized()
        write_memory_event(Path(tmp) / "memory", event)
        loaded = load_memory_events(Path(tmp) / "memory", subject="Nat.add_zero")
        index_exists = (Path(tmp) / "index.json").exists()
    results.append(record("context_lake_and_memory_roundtrip", index_exists and len(loaded) == 1 and loaded[0].relation == "proves"))

    quota_missing = CandidateEvidence("too_fast", Stage.LEMMA_SPRINT, AgentRole.TACTIC_SPRINTER, claim="fast", artifact_paths=["x.lean"], tool_logs=["x.log"], lean_passed=True, no_sorry=True, expected_statement_hash=stable_hash("a"), theorem_statement_hash=stable_hash("a"))
    quota_decision = select_candidate([quota_missing], frontier=True)
    results.append(record("frontier_quota_veto", not quota_decision.accepted and any(v.startswith("quota_not_met") for v in quota_decision.scores[0].veto_reasons), str(quota_decision.scores[0].veto_reasons)))

    passed = all(r["status"] == "PASS" for r in results)
    return {"passed": passed, "results": results}


if __name__ == "__main__":
    payload = run()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    raise SystemExit(0 if payload["passed"] else 1)
