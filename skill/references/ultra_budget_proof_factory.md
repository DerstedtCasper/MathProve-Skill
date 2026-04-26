# Ultra-budget proof factory protocol

Use this reference when the problem is research-level, formalization-heavy, or expected to run for many hours.

## Budget semantics

“Unlimited budget” never means uncontrolled loops.  It means:

1. Do not terminate merely because one branch failed.
2. Externalize every stage artifact before continuing.
3. Treat context as a cache, not as the source of truth.
4. Use memory events, checkpoints, and logs to grow the effective campaign context beyond a single model window.
5. Stop only on final audit approval, a formal counterexample, a repaired theorem statement, or an environment blocker with replay logs.

## Campaign directories

```text
WORKSPACE/runs/<run_id>/
  problem.md
  problem_lock.md
  assumption_ledger.md
  status.json
  checkpoints/<stage>.json
  memory/events.jsonl
  notation/notation_table.md
  blueprint/blueprint.md
  skeleton/Skeleton.lean
  line_map/line_map.json
  lemma_sprint/branches/<lemma>/<agent>/
  refutation/red_team_report.md
  integration/Integrated.lean
  audit/audit.json
```

## Stage gates

Run stages in this order:

`intake -> notation -> blueprint -> skeleton -> line_map -> lemma_sprint -> refutation -> integration -> final_audit`.

A later stage may request a rollback, but rollback must create a memory event explaining exactly which artifact is being replaced and why.

## Anti-laziness rule

For hard mathematical research, a “fast complete proof” is suspicious unless it comes with replay logs, dependency closure, and a red-team report. Prefer slow verified progress over polished unverified closure.
