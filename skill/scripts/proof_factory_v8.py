#!/usr/bin/env python3
"""CLI wrapper for MathProve v8 proof-factory primitives."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.proof_factory_v8 import Stage, demo_decision, lean_static_audit, make_budget_contract, termination_allowed


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo-decision")
    p_audit = sub.add_parser("static-audit")
    p_audit.add_argument("lean_file")
    p_audit.add_argument("--stage", default="final_audit")
    p_budget = sub.add_parser("budget")
    p_budget.add_argument("--mode", default="frontier")
    p_term = sub.add_parser("termination")
    p_term.add_argument("status_json")
    args = parser.parse_args()

    if args.cmd == "demo-decision":
        print(json.dumps(demo_decision(frontier=True).to_dict(), indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "static-audit":
        text = Path(args.lean_file).read_text(encoding="utf-8")
        ok, violations = lean_static_audit(text, Stage(args.stage))
        print(json.dumps({"ok": ok, "violations": violations}, indent=2, ensure_ascii=False))
        return 0 if ok else 2
    if args.cmd == "budget":
        print(json.dumps(make_budget_contract(args.mode).to_dict(), indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "termination":
        status = json.loads(Path(args.status_json).read_text(encoding="utf-8"))
        ok, reason = termination_allowed(status)
        print(json.dumps({"allowed": ok, "reason": reason}, indent=2, ensure_ascii=False))
        return 0 if ok else 3
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
