from __future__ import annotations

import json
import tempfile
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.proof_factory import (
    AgentRole,
    CandidateEvidence,
    ProofFactoryState,
    ProofMemoryEvent,
    Stage,
    STAGE_ORDER,
    budget_contract,
    checkpoint,
    demo_decision,
    lean_static_audit,
    load_checkpoint,
    load_memory_events,
    select_candidate,
    validate_line_map,
    write_memory_event,
)


def check(name, cond, detail=''):
    if not cond:
        raise AssertionError(f'{name} failed: {detail}')
    return {'name': name, 'status': 'PASS', 'detail': detail}


def run():
    results = []
    results.append(check('stage_order', [s.value for s in STAGE_ORDER] == ['intake','notation','blueprint','skeleton','line_map','lemma_sprint','refutation','integration','final_audit']))
    decision = demo_decision()
    results.append(check('evidence_beats_rhetoric', decision.accepted and decision.selected_candidate_id == 'compiled_patch', json.dumps(decision.to_dict(), ensure_ascii=False)))
    bad = CandidateEvidence('bad', Stage.LEMMA_SPRINT, AgentRole.TACTIC_SPRINTER, artifact_paths=['x.lean'], tool_logs=['lean.log'], lean_passed=True, no_sorry=False, dependency_closure=1.0)
    good = CandidateEvidence('good', Stage.LEMMA_SPRINT, AgentRole.TACTIC_SPRINTER, artifact_paths=['g.lean'], tool_logs=['lean.log'], lean_passed=True, no_sorry=True, dependency_closure=0.8, refutation_coverage=0.8, maintainability=0.8, restartability=0.8)
    decision2 = select_candidate([bad, good], threshold=0.6)
    results.append(check('sorry_veto', decision2.selected_candidate_id == 'good'))
    ok_skel, skel_viol = lean_static_audit('theorem S1 : True := by\n  sorry\n', Stage.SKELETON)
    ok_final, final_viol = lean_static_audit('theorem S1 : True := by\n  sorry\n', Stage.FINAL_AUDIT)
    results.append(check('skeleton_sorry_allowed', ok_skel and not ok_final and 'sorry' in final_viol))
    line_ok, line_errors = validate_line_map([{'line_id':'L1','formal_target':'lemma foo','obligation':'prove foo','depends_on':[]}])
    line_bad, bad_errors = validate_line_map([{'line_id':'L1','formal_target':'','obligation':'','depends_on':['L1']}])
    results.append(check('line_map_guard', line_ok and not line_bad and len(bad_errors) >= 2))
    with tempfile.TemporaryDirectory() as td:
        state = ProofFactoryState(run_id='run_demo', stage=Stage.LINE_MAP, problem_hash='abc')
        checkpoint(td, state, {'x': 1})
        loaded = load_checkpoint(td)
        results.append(check('checkpoint_resume', loaded['state']['stage'] == 'line_map'))
        write_memory_event(Path(td)/'memory', ProofMemoryEvent('lemma','myLemma','updates',{'new':'statement'},'blueprint','test'))
        events = load_memory_events(Path(td)/'memory', subject='myLemma')
        results.append(check('memory_event_roundtrip', len(events) == 1 and events[0].relation == 'updates'))
    contract = budget_contract(unlimited=True, wall_clock_hours=24, context_target_tokens=1_000_000)
    results.append(check('anti_laziness_budget_contract', contract['token_budget_policy'] == 'externalize-and-continue' and contract['minimum_wall_clock_hours_for_hard_research'] >= 24))
    return results


def main():
    results = run()
    print(json.dumps({'passed': len(results), 'results': results}, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
