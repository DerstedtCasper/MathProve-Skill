---
name: mathprove-skill
description: Evidence-bound mathematical research with persistent workspaces, lemma tasks, bounded multi-agent collaboration, adversarial review and optional Lean 4 verification. Use for sustained research or proof projects; not for routine one-off arithmetic. Requires explicit operator approval for builds, tool installation and human review.
---

# MathProve v9 — portable research protocol

Select the backend before beginning. For an existing CoMath deployment, read `references/v9/comath-backed.md` and use only its actual operator tools; do not initialize a local shadow database or adopt the portable task JSON. Do not silently change backends on a missing tool.

The remaining sections describe **Portable-local** mode. Read `agent.md` for that mode. This is the v9 release-candidate entrypoint, independent of retained legacy state. Use only `scripts/mathprove.py` for v9 state. A selected v8 scoring/graph helper has a compatibility patch, but legacy database migration and full legacy regression are not provided.

## Start and resume

1. Establish the research root and goal from the current user request. Run `python <skill-root>/scripts/mathprove.py --root <research-root> doctor`. Do not install missing tools automatically.
2. Initialize once with `init`, then `list`/`status <run> --check`. If multiple runs exist, explicitly select and `bind <run> --session <session-id>`; do not guess. Restore a bounded checkpoint and relevant artifacts, not the full conversation.
3. For a new run, create a spec JSON **inside the research root** with mode, statement, assumptions, symbols. Formal mode also needs `lean.project`, `lean.module`, `lean.declaration`, and the exact reviewed `lean.expected_type`. Use `start <run> --spec <file>`; it defaults to two parallel leases, three attempts per task and 32 attempts total.
4. Read `references/v9/operations.md` for exact commands and `references/v9/protocol.md` for evidence requirements. Use `--help` rather than guessing flags. Keep the root before the subcommand.

## Research cycle

Follow `spec → plan → candidate → refutation → verify → release`. A gate is a structural/evidence check, not an LLM verdict. Later gates recheck earlier requirements and current evidence hashes. Statement changes go through `revise`; never edit a lock, database, receipt or old artifact in place.

Create a small lemma DAG. Reuse known results only with checked hypotheses and exact source references. Record missing source coverage rather than claim novelty from absent search results. Compare a proof route with a genuinely different route or adverse-evidence probe before expensive parallel work.

Use `task-add`, `claim`, `packet`, `heartbeat`, `finish` for bounded tasks. The coordinator owns lease tokens and shared state. Writable workers stay in their attempt directories; read-only workers return inline drafts. Register artifacts with `evidence-add` separately; a completed task is not proof. Counterexample leads become unresolved issues, not silently dropped objections. Preserve failed approaches with assumptions and reproduction details.

Default to one coordinator and only the specialist roles needed for the current bottleneck. Native Codex presets are `mp_formalizer`, `mp_strategist`, `mp_librarian`, `mp_prover`, `mp_experimenter`, `mp_refuter`, `mp_integrator`, `mp_auditor`. The parent may adopt `mp_coordinator` instructions; do not spawn a second coordinator. Shared role sources are in `assets/v9/roles/`. No subagent tool means explicitly sequential role passes, not fictional independent agents.

Use minimal context packets. `packet --blind-statement` with a formalizer/auditor task withholds the informal target and previous opinions for a separate back-translation pass. It is context filtering, not access-control isolation. The host must create a truly separate context for independent review.

## Verification and stop conditions

Research mode can produce a `reviewed_research` packet after integration and human review. This is **not a formal proof certificate**. CAS calculations, finite search, empirical tests and reviewed informal proofs remain labeled by their evidence type.

Formal mode uses explicit `verify <run> --allow-build` only after the human has approved the build code and environment. The runner uses a fresh workspace, a pinned Lean toolchain and dependency manifest, a wrapper checking the exact expected type, and an axiom allowlist. No hook may compile, install dependencies, call an LLM, or promote tool success to proof. Read the runner limitations in `references/v9/protocol.md` before claiming what was checked.

A failed, missing or stale verification blocks formal release. Human review must bind the current snapshot and be invoked by the operator outside agent execution. Do not invoke `review --human-ack` on the user's behalf. Even the final `reviewed_formal_local` label is a cooperative local record, not authenticated independent certification or a novelty judgment.

On budget exhaustion, interruption, a blocked dependency, or a request to stop: checkpoint, report the precise unresolved obligation, and pause. Do not force an endless Stop-hook loop, demand a million-token budget, or infer impossibility from an unsuccessful attempt. A continuation must state what new evidence, tool, approach or budget justifies it.

## Host integration

The native installer merges project-local Codex command hooks and standalone agent TOML presets; the human must review/trust the project and hooks through the host. Changes require re-review. Hooks are convenience guardrails, not comprehensive security. Other hosts can call the same CLI and use the shared prompts manually; their hook schemas are not assumed identical to Codex.

No external service, plugin, model provider or API key is required by this controller. It does not itself launch LLMs or pay for inference. Actual agent tools, model choice, sandbox permissions and billing caps remain host/operator responsibilities.
