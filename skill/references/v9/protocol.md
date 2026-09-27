# v9 protocol and trust contract

This protocol is intentionally **single-user, local-filesystem, cooperative**. The coordinator is the intended sole state writer. SQLite transactions serialize concurrent compliant clients; worker leases reject late/duplicate submissions. These are not OS authentication. A process with the same filesystem access can rewrite the database, scripts and hash chain. Never describe the local review flag as cryptographic human authorization.

## State and evidence

`.mathprove/state.sqlite3` is authoritative for the portable controller. `.mathprove/objects` contains content-addressed evidence snapshots; `.mathprove/checkpoints` contains resumable summaries; `.mathprove/replays` contains verification working trees and logs. `WORKSPACE/<run>/tasks/<task>/attempt-...` holds worker artifacts. Never treat Markdown summaries as state authority. Keep the state on a local disk, not an untested network filesystem. No v8 database migration is attempted.

Each run locks a canonical JSON statement hash. Spec revisions invalidate previous task authority and gate progression. Every submitted result must bind both a live lease and the current hash. Keep lease tokens in private claim JSON files, not prompts, shared agent packets or command-line arguments. Tokens prevent accidental cross-worker submission; they are not a defense against the same OS user.

Evidence keeps its registered origin hash. Editing or removing an origin makes it stale; restore it or `evidence-withdraw` with a reason and register a replacement. Withdrawal never deletes history. Completed task artifact hashes are checked at dependency consumption and later gates. `task-invalidate` cancels that task and descendants, opens a review issue and requires a new plan/new task IDs. It does not magically know which mathematical claims depend on a free-form note: the coordinator must also withdraw affected evidence.

Status fields are historical; use `status --check` or the relevant `gate --check` for current validity. Hook briefings deliberately avoid expensive file hashing and raw research text. An event hash chain detects corruption or incomplete edits, but an attacker able to rewrite all records can recompute it.

## Six cumulative gates

| Gate | Required current evidence | Meaning |
|---|---|---|
| spec | spec_review JSON: current spec_hash, statement_match=true, assumptions_checked=true, reviewer, issues=[] | A recorded translation/assumption review, not automatic semantic equivalence |
| plan | plan JSON: current hash, exact node statements, acyclic dependencies, target, checked literature records or justified exemption | A structurally usable plan; citation truth still requires source review |
| candidate | candidate artifact; no unresolved adverse issue or stale task artifact | A candidate exists, not a theorem proved |
| refutation | current-hash refutation JSON, nonempty reproducible test records, limitations, reviewer, no unresolved counterexample | Adverse-evidence search recorded; no-counterexample-found is not proof |
| verify | all tasks done/cancelled; research integration note OR the latest runner-produced successful local Lean receipt | Research completeness review or scoped local formal checking |
| release | all prior checks fresh, exact-snapshot human review | reviewed_research or reviewed_formal_local, never a blanket novelty/security certificate |

`checked:true`, reviewer names, source URLs and human-ack are attestations/structure. The controller cannot determine whether a person truly read a paper, whether an informal proof is correct, or who is physically using the terminal. The human/auditor must check substantive content.

## Formal verification profile

Use a dedicated small Lake project. The initial adapter supports a concrete versioned `leanprover/lean4:vX.Y.Z` (optionally `-rcN`), a checked-in `lake-manifest.json`, and HTTPS Git dependencies pinned to full 40-hex revisions. Path packages, registry-only pins, custom universes/complex declaration names and some metaprogramming-heavy projects need an explicitly reviewed extension, not a silent bypass.

The runner does not import a caller-supplied success log. It creates a new directory without copying the original `.lake` cache, executes the reviewed Lake build, generates a random audit theorem with `autoImplicit false`, checks that the target term has the exact expected type, and reads the generated theorem's axiom dependencies. The allowlist is `propext`, `Classical.choice`, `Quot.sound`; other axioms, absent output, failed commands, changed input sources and missing provenance fail closed. Source lexical checks are conservative aids, not a Lean parser or substitute for the kernel.

The receipt records source/config hashes, dependency source revisions/hashes, resolved toolchain identity, generated audit source and build/check logs. Gate checks rehash current original sources, retained replay inputs, compiled artifacts, materialized dependency sources, toolchain binaries, audit source and logs; they also invalidate receipts when the verifier implementation changes. The receipt is produced by the local runner and remains within the same-user trust boundary.

**Important limits:** a fresh directory is not a sandbox. Lake files and dependency code can execute with the caller's permissions and may use the network. Arbitrary build scripts may download caches; this adapter does not attest a hermetic, source-only rebuild of every transitive dependency. A human must review build behavior or run it in a controlled external environment. A formal result still depends on the trusted compiler/kernel, libraries/definitions and the faithful formal specification. This is not CoMath's uninspected proof-kernel/host-approval implementation and must not replace it as a security boundary.

No Lean/lake in the environment means no formal evidence, not a fallback to 'LLM verified'. Operator consent is mandatory for `--allow-build`. Use a disposable controlled environment for unfamiliar projects. `timeout` is per command, not a total run-cost cap. Failed attempts retain logs and cannot inherit a previous successful receipt by pretending the latest failure did not happen.

## Context, budgets and independence

The controller bounds concurrent leases and task attempts, not token spending or provider costs. The host must enforce billing/time limits. A compact packet contains one task, one statement lock and relevant references. Its character cap refuses oversize input instead of truncating mathematical statements. Search stored failure notes before reattempting a route; do not make a million-token context target a success criterion.

The blind statement packet omits the original informal statement, task advocacy and other verdicts. It does not prevent an agent with broad file-read access from finding them. True blinded review needs a separate host context and restricted data access; the portable controller only supplies the filtered packet. A sequential 'auditor' pass cannot be reported as an independent agent's conclusion.

## Hooks and privacy

Native Codex command hooks cover SessionStart, PreToolUse, PostToolUse, PreCompact, PostCompact, SubagentStart, SubagentStop, Stop and SessionEnd. Hooks never call models or compile proofs. Neutral PreToolUse returns `{}` and does not grant permissions. Its narrow write/self-review checks are best-effort guardrails, not shell-language enforcement. Hosted tools, tool aliases, persistent shell sessions and same-user processes prevent comprehensive mediation.

PostToolUse records hashes rather than raw commands, responses or transcripts. Stop checkpoints once and permits unresolved work to stop; a checkpoint failure requests one repair turn at most using stop_hook_active. SessionEnd is best effort under its host timeout. The installer does not change trust, permission policy or global config. Inspect `/hooks`, and re-review modified hooks. Exact commands use installed absolute paths; reinstall after moving a project or Python.

Exports contain unpublished research and reviewer notes. They exclude the live SQLite database, lease tokens and transcripts, but are not automatically safe for publication. A review export is not a complete transitive-dependency replay bundle. Never upload without a human check.
