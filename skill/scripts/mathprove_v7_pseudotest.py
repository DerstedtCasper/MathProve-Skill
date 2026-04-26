#!/usr/bin/env python3
from __future__ import annotations
import json, tempfile, sys, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from runtime.proof_factory_v7 import Candidate, decide, validate_final_lean_text
from runtime.context_lake_v7 import ContextLake
from runtime.moe_router_v7 import activate
def check(name, cond, details=""):
    return {"name": name, "status": "PASS" if cond else "FAIL", "details": details}
def main():
    results=[]
    d=decide("lemma_sprint", [Candidate("lemma_sprint","fluent_no_log","obvious",maintainability=10), Candidate("lemma_sprint","lean_cert","small lemma",tool_status="pass",dependencies_closed=True,risks_covered=["type","boundary"],evidence_complete=True,restartable=True)])
    results.append(check("evidence_weighted_selection", d.accepted=="lean_cert", json.dumps(d.scores)))
    d2=decide("final_audit", [Candidate("final_audit","has_sorry","bad",tool_status="pass",dependencies_closed=True,evidence_complete=True,restartable=True,hard_vetoes=["sorry"]), Candidate("final_audit","clean","ok",tool_status="pass",dependencies_closed=True,evidence_complete=True,restartable=True)])
    results.append(check("hard_veto_dominates", d2.accepted=="clean", json.dumps(d2.scores)))
    ok,vetoes=validate_final_lean_text("theorem t : True := by sorry")
    results.append(check("final_rejects_forbidden_tokens", (not ok) and any("sorry" in v for v in vetoes), str(vetoes)))
    with tempfile.TemporaryDirectory() as td:
        lake=ContextLake(td,"run_demo"); lake.write_shard("problem_lock","problem_lock","Problem","# Problem\nProve demo theorem.","00_problem.md"); lake.write_shard("lemma_sprint","lemma_sprint","Long","A"*5000,"05_long.md")
        results.append(check("context_lake_index", len(lake.read_index())==2 and "Problem" in lake.active_packet(max_tokens=2000), "entries=2"))
    e=activate("lemma_sprint",difficulty="research")
    results.append(check("moe_eight_experts", len(e)==8 and "refuter" in e and "auditor" in e, ",".join(e)))
    e2=activate("notation")
    results.append(check("notation_expert_selection", "formalizer" in e2 and "refuter" in e2, ",".join(e2)))
    skill_md=(ROOT/"SKILL.md").read_text(encoding="utf-8")
    results.append(check("zero_shot_policy_present", "zero-shot" in skill_md, "policy string found"))
    passed=all(r["status"]=="PASS" for r in results)
    print(json.dumps({"passed": passed, "results": results}, indent=2, ensure_ascii=False), flush=True)
    return 0 if passed else 1
if __name__=="__main__":
    rc = main()
    os._exit(rc)
