from skill.runtime.proof_factory_v7 import Candidate, decide, validate_final_lean_text
from skill.runtime.moe_router_v7 import activate
def test_evidence_beats_fluent_branch():
    d=decide("lemma_sprint", [Candidate("lemma_sprint","fluent","words",maintainability=10), Candidate("lemma_sprint","certified","proof",tool_status="pass",dependencies_closed=True,evidence_complete=True,restartable=True)])
    assert d.accepted == "certified"
def test_hard_veto_rejects_sorry_branch():
    d=decide("final_audit", [Candidate("final_audit","bad","bad",tool_status="pass",dependencies_closed=True,evidence_complete=True,hard_vetoes=["sorry"]), Candidate("final_audit","ok","ok",tool_status="pass",dependencies_closed=True,evidence_complete=True)])
    assert d.accepted == "ok"
def test_final_lean_forbidden_scan():
    ok,v=validate_final_lean_text("theorem t : True := by admit")
    assert not ok and any("admit" in x for x in v)
def test_research_mode_activates_all_eight():
    experts=activate("lemma_sprint", difficulty="research")
    assert len(experts)==8 and "auditor" in experts and "refuter" in experts
