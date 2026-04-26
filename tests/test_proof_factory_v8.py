from skill.runtime.proof_factory_v8 import Stage, demo_decision, lean_static_audit, make_budget_contract, termination_allowed
from skill.runtime.moe_router_v8 import activate, FULL_PANEL


def test_demo_decision_selects_verified_candidate():
    decision = demo_decision(frontier=True)
    assert decision.accepted
    assert decision.selected_candidate_id == "compiled_patch"


def test_sorry_policy_stage_sensitive():
    assert lean_static_audit("theorem t : True := by sorry", Stage.SKELETON)[0]
    ok, violations = lean_static_audit("theorem t : True := by sorry", Stage.FINAL_AUDIT)
    assert not ok
    assert "sorry" in violations


def test_frontier_budget_contract_and_termination_gate():
    budget = make_budget_contract("frontier").to_dict()
    assert budget["local_context_target_tokens"] >= 1_000_000
    assert budget["global_campaign_target_tokens"] >= 20_000_000
    assert budget["minimum_wall_clock_hours"] >= 24
    ok, _ = termination_allowed({"local_context_exhausted": True})
    assert not ok
    ok, reason = termination_allowed({"final_audit_approved": True})
    assert ok and reason == "final_audit_approved"


def test_moe_escalates_full_panel_for_frontier():
    assert set(activate("lemma_sprint", difficulty="frontier")) == set(FULL_PANEL)
