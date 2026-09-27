#!/usr/bin/env python3
"""Create an explicitly elementary research-protocol demo; no fake human approval."""
from pathlib import Path
import argparse
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skill'))
from runtime_v9.core import Store, atomic_write, dumps

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--run',default='demo');a=p.parse_args()
    root=Path(a.root).expanduser().resolve()
    if not root.is_dir():p.error('Create the empty demo directory first')
    base=Path(__file__).resolve().parents[1];store=Store(root,create=True)
    spec=json.loads((base/'examples/v9/research-spec.json').read_text());state=store.create_run(a.run,spec)
    h=state['spec_hash'];folder=root/'WORKSPACE'/a.run/'demo';folder.mkdir(parents=True,exist_ok=False)
    artifacts={
      'spec_review':{'spec_hash':h,'statement_match':True,'assumptions_checked':True,'reviewer':'SCRIPTED ELEMENTARY DEMO — not a human review','issues':[]},
      'plan':{'spec_hash':h,'target':'goal','nodes':[{'id':'goal','statement':spec['statement'],'depends_on':[]}],'literature':{'not_needed_reason':'Elementary reflexivity demonstration; no novelty claim'}},
      'candidate':'For an arbitrary natural number n, equality is reflexive, so n = n. This is an informal demo artifact, not a machine certificate.',
      'refutation':{'spec_hash':h,'reviewer':'SCRIPTED DEMO — not an independent agent','tests':[{'hypothesis':'n is a natural number','method':'inspect reflexive equality','result':'No special value restriction is used in this elementary argument','evidence':'candidate.txt'}],'limitations':['Scripted protocol demonstration; no general mathematical benchmark'],'unresolved_counterexamples':[]},
      'integration':'The elementary informal argument is integrated. No Lean invocation, novelty assessment or human review occurred.'}
    for kind,value in artifacts.items():
        path=folder/(kind+('.txt' if isinstance(value,str) else '.json'))
        atomic_write(path,value if isinstance(value,str) else dumps(value)+'\n');store.add_evidence(a.run,kind,path,producer='scripted-demo')
    gates=[]
    for stage in ('spec','plan','candidate','refutation','verify'):gates.append(store.gate(a.run,stage))
    cp=store.checkpoint(a.run,'demo-handoff')
    print(json.dumps({'run_id':a.run,'mode':'research','gates':gates,'checkpoint':cp,
                      'human_review_recorded':False,'formal_proof_claimed':False,
                      'next_action':'Inspect status and the example artifacts. Human review remains an explicit operator step.'},ensure_ascii=False,indent=2))
    return 0 if all(g['accepted'] for g in gates) else 2
if __name__=='__main__':raise SystemExit(main())
