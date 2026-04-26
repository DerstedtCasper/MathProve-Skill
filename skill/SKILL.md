---
name: mathprove-skill
description: |
  Research-grade automated formal proof workflow for complex mathematics, Lean4/SymPy verification, multi-agent proof search, proof engineering, theorem formalization, long-horizon proof campaigns, counterexample search, and evidence-gated final audits. Use when asked to prove, formalize, verify, audit, refactor, or explore mathematical statements, especially algebra, representation theory, quantum groups, braid/YBE topics, olympiad-style formal proofs, or large Lean projects.
---

# MathProve Skill - Ultra v8

MathProve treats proof as a restartable, auditable software pipeline. Every promoted mathematical conclusion must bind to durable evidence: Lean/SymPy logs, exact assumptions, candidate packs, proof-memory events, and final audit output.

## 0. Non-negotiable rules

0.1 **Workspace boundary** — write temporary/run artifacts only under `WORKSPACE/`. Do not mutate the skill package during a run.

0.2 **Evidence before conclusion** — never claim a theorem is proved until the final audit gate approves. Before that, use statuses such as scaffold complete, partially verified, blocked, or counterexample found.

0.3 **No untracked crowd simulation** — multi-agent work must be represented as task cards, candidate packs, logs, and evidence decisions. Do not merely role-play several agents inside prose.

0.4 **Gate promotion** — a candidate moves forward only after the current stage gate accepts it by evidence-weighted scoring and no hard veto fires.

0.5 **Lean strictness** — `sorry` is allowed only in skeleton artifacts before lemma sprint. Non-skeleton proof files with `sorry`, `admit`, hidden axioms, or unsafe declarations fail closed.

0.6 **Large-budget mode** — when the user grants large or unlimited token/time budget, create a context lake and continue by externalizing state. Do not finish early merely because a short answer is easier.

0.7 **Reproducibility** — record commands, inputs, outputs, exit codes, timestamps, imports, environment blockers, and proof dependencies.

## 1. Workspace structure

```text
WORKSPACE/runs/<run_id>/
├── problem.md / problem_lock.md / assumptions.md / manifest.json / status.json
├── context_lake/      index.json + shards/*.md + handoff_capsules/*.md
├── knowledge/         retrieved_lemmas.md + library_search.jsonl + citations.md
├── plan/              theorem_variants.json + blueprint.md + lemma_dag.json
├── candidates/        <stage>/<candidate_id>/candidate.json + artifacts + logs
├── magi/              stage votes and vetoes
├── sympy/             exact checks + logs
├── lean/              Skeleton.lean + Integrated.lean + lemma files + logs
├── memory/            events.jsonl + by_id/*.json
├── draft/             line_map.json + proof_draft.md + Solution.md
├── audit/             audit.json + FAILURE_REPORT.md
└── logs/              init_check.log + tool_calls.log + errors.log
```

## 2. Ultra v8 workflow

1. **Preflight**: check routes, lock the problem, record assumptions, choose route.
2. **Budget contract**: if hard/frontier/research, enable `long_horizon=true`, `context_target_tokens>=1_000_000`, and stage-local branch queues.
3. **Knowledge pack**: collect relevant definitions, Mathlib lemmas, user documents, prior memory, and citation notes.
4. **Notation gate**: freeze variables, domains, namespaces, index conventions, coercions, and theorem signatures.
5. **Skeleton gate**: create Lean declarations and lemma DAG. Use `sorry` only here.
6. **Line-map gate**: convert informal proof lines into atomic formal obligations.
7. **Lemma sprint**: run parallel candidate attempts; accept by evidence-weighted gate, not majority vote.
8. **Refutation gate**: attack quantifiers, converse directions, boundary cases, hidden assumptions, and theorem drift.
9. **Integration/refactor**: merge proof patches, minimize imports, remove skeleton placeholders, replay.
10. **Final audit**: static scan + Lean replay + dependency/axiom profile + evidence coverage.
11. **Proof memory update**: write successes, blockers, counterexamples, and reusable repairs to graph memory.

## 3. Required references

Load these references when their gate is reached:

- `agent.md` — top-level operating charter.
- `references/stage-gates-v8.md` — gate criteria, hard vetoes, rewind rules, and minimum work quotas.
- `references/budget-and-context-lake-v8.md` — 1M+ context externalization and handoff discipline.
- `references/moe-expert-router-v8.md` — expert activation, stage-local task cards, and escalation policy.
- `references/formalization-scaffold-v8.md` — Tao-style skeleton → line map → lemma sprint workflow.
- `references/proof-memory-graph-v8.md` — durable memory schema and relation labels.
- `references/frontier-research-protocol-v8.md` — 24h+ proof-campaign protocol.
- `references/research-basis-2026-v8.md` — research inspirations and implementation translation.

## 4. Runtime helpers

Use these stdlib-only helpers when available:

- `runtime/proof_factory_v8.py` — stage specs, candidate scoring, hard vetoes, context lake, proof memory, budget contract, static Lean audit.
- `runtime/context_lake_v8.py` — context-shard index utilities.
- `runtime/moe_router_v8.py` — expert activation policy.
- `scripts/proof_factory_v8.py` — CLI wrapper for demo decisions and static audits.
- `scripts/mathprove_v8_pseudotest.py` — protocol regression tests.

## 5. Reporting standard

Every progress report should include: `run_id`, current stage, accepted candidate or blocker, evidence paths, unresolved hazards, and next gate. Do not paste long logs; quote only the decisive lines and keep full logs in workspace.

## 6. Failure handling

Fail closed when evidence is incomplete. On failure, write `FAILURE_REPORT.md` with stage, candidate ID, key error lines, log paths, retries used, suspected cause, and next repair actions. A precise failure certificate is a valid outcome; an unsupported proof claim is not.
