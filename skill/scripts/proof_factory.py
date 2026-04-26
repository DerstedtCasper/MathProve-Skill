from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from runtime.proof_factory import CandidateEvidence, Stage, AgentRole, demo_decision, select_candidate, write_json
except Exception:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT))
    from runtime.proof_factory import CandidateEvidence, Stage, AgentRole, demo_decision, select_candidate, write_json


def _candidate_from_dict(d):
    d = dict(d)
    d['stage'] = Stage(d['stage'])
    d['role'] = AgentRole(d['role']) if d.get('role') in {r.value for r in AgentRole} else d.get('role', 'unknown')
    return CandidateEvidence(**d)


def main(argv=None):
    parser = argparse.ArgumentParser(description='MathProve v7 proof-factory gate selector')
    parser.add_argument('--demo', action='store_true', help='write a sample gate decision')
    parser.add_argument('--candidates-json', help='JSON list of candidate evidence records')
    parser.add_argument('--out', default='gate_decision.json')
    parser.add_argument('--threshold', type=float, default=0.72)
    args = parser.parse_args(argv)
    if args.demo:
        decision = demo_decision()
    else:
        if not args.candidates_json:
            parser.error('--candidates-json is required unless --demo is used')
        raw = json.loads(Path(args.candidates_json).read_text(encoding='utf-8'))
        decision = select_candidate([_candidate_from_dict(x) for x in raw], threshold=args.threshold)
    write_json(args.out, decision.to_dict())
    print(json.dumps(decision.to_dict(), indent=2, ensure_ascii=False))
    return 0 if decision.accepted else 2

if __name__ == '__main__':
    raise SystemExit(main())
