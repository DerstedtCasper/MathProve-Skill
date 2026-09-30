# Command reference and operator workflow

Run the installed entrypoint with Python 3.11 or later. All commands accept `--root` **before** the command, emit JSON by default and use exit status 2 for a rejected operation/gate. `status --human --check` gives a small terminal summary. No third-party Python packages are needed.

Below, `MP` means `python /absolute/path/to/skill/scripts/mathprove.py --root /absolute/research/root`; substitute that complete command, not a nonexistent executable. Input files must exist under the research root. Existing roots are never created implicitly.

```text
MP init
MP doctor
MP start paper1 --spec spec.json --max-parallel 2 --max-attempts 3 --budget-attempts 32
MP list
MP status paper1 --human --check
MP spec paper1
MP bind paper1 --session THE_ACTUAL_HOST_SESSION_ID
MP task-add paper1 L1 --role prover --objective "Prove the exact base lemma"
MP task-add paper1 L2 --role refuter --objective "Check the boundary case" --depends-on L1
MP claim paper1 --owner coordinator-worker1 --task L1 --ttl 900
MP packet paper1 L1
```

Save the claim JSON in a private root-local file, for example `WORKSPACE/claim-L1.private.json`; do not send its lease_token to the model worker or commit it. The packet omits the token. The coordinator uses the private file for heartbeat and submission:

```text
MP heartbeat paper1 L1 --owner coordinator-worker1 --token-file WORKSPACE/claim-L1.private.json --ttl 900
MP finish paper1 L1 --owner coordinator-worker1 --token-file WORKSPACE/claim-L1.private.json --result WORKSPACE/result-L1.json
MP reap paper1
MP task-cancel paper1 L2 --reason "No longer on the research plan"
MP task-invalidate paper1 L1 --reason "A hidden hypothesis was discovered"
```

`spec_hash` is a legacy key for the current goal revision ID, not a hash. `result` JSON requires `task_id`, `spec_hash`, `outcome`, `summary`, `next_action`, and optional artifact paths inside the actual lease attempt directory. Outcomes are candidate, refuted, blocked and no_progress. Completed work has no proof authority by itself. A blocked task is not automatically retried forever: cancel/supersede it with an explicit new task after replanning. Expired attempts still count toward the attempt budget. `resume` can explicitly raise the global budget, never reset consumed attempts.

Register useful results separately. Working notes may be improved in place; register a replacement when the mathematical claim changes, not because its file hash changed.

```text
MP evidence-add paper1 spec_review WORKSPACE/spec-review.json --producer formalizer
MP gate paper1 spec
MP evidence-add paper1 plan WORKSPACE/plan.json --producer strategist
MP gate paper1 plan
MP evidence-add paper1 candidate WORKSPACE/candidate.md --producer prover
MP gate paper1 candidate
MP evidence-add paper1 refutation WORKSPACE/refutation.json --producer refuter
MP gate paper1 refutation
MP evidence-add paper1 integration WORKSPACE/integration.md --producer integrator
MP gate paper1 verify
```

For formal mode, run `MP verify paper1 --timeout 1800` in the existing Lean project, then record the verify stage. The runner reuses Lake caches and checks the exact mathematical target; no version pin, file hash or additional build acknowledgement is required.

```text
MP evidence-add paper1 counterexample_candidate WORKSPACE/witness.json --producer refuter
MP issue paper1 "Unverified use of a generic-rank argument at a singular point"
MP resolve paper1 I-RETURNED_ID E-RESOLUTION_EVIDENCE_ID
MP evidence-withdraw paper1 E-OLD_EVIDENCE_ID --reason "Superseded after review"
MP evidence-show paper1 E-RETURNED_ID
MP memory paper1 --query "singular" --limit 10
MP checkpoint paper1 --reason "End of work session"
MP pause paper1 --reason "Awaiting source access or human review"
MP resume paper1 --budget-attempts 48
```

Resolution binds existing evidence; its mathematical adequacy is a human/auditor responsibility. Withdrawing the resolution evidence makes the issue unresolved for gate purposes. New statement versions need a `revise ... --spec ... --reason ...`; prior run evidence is not silently carried forward.

Optional mathematical review notes can be recorded by the researcher or a reviewer; no additional acknowledgement is required:

```text
MP status paper1 --check
MP review paper1 --reviewer "YOUR_NAME" --note "Reviewed the stated scope and limitations" --snapshot EXACT_CURRENT_SNAPSHOT
MP gate paper1 release
MP export paper1 --out WORKSPACE/paper1-review.zip
MP audit-events
```

The note records a mathematical judgment. Working-file edits do not trigger hash validation or mandatory reapproval. Inspect the export before sharing; it is a review packet, not a standalone formal certificate. Back up the workspace with SQLite's online backup API or with all writers stopped; do not copy a live database while omitting its WAL.

For a formal translation audit, use an auditor or formalizer task with `MP packet paper1 AUDIT_TASK --blind-statement`. Give it to a fresh read-only worker and compare its back-translation to the original informal statement outside that worker. Do not pretend packet filtering is access isolation.
