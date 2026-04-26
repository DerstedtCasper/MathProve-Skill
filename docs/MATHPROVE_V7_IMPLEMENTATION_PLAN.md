# MathProve v7 Implementation Plan

## P0 - Completed deliverables

- Rewrote `skill/SKILL.md` and `skill/agent.md` for long-horizon formal proof work.
- Added v7 references, SOP files, schemas, runtime helpers, and pseudotest scripts.
- Added context lake, MoE-style router, proof-factory scoring, and hard-veto logic.
- Packaged the updated skill as `skill.zip` with validator success.
- Built a full optimized source package.

## P1 - Verification integration

- Connect `proof_factory_v7.Candidate` to `verify_lean.py`, `verify_sympy.py`, and `final_audit.py`.
- Require every tool call to write a candidate manifest with artifact paths, tool status, hard vetoes, and risk coverage.
- Convert Lean/SymPy errors into stable error signatures for the failure bank.
- Feed final audit results back into the proof-memory graph.

## P2 - Long-context execution

- Use `context_lake_v7.ContextLake` as the mandatory run memory.
- Write one shard per phase, one shard per accepted lemma, and one shard per major failure class.
- Maintain `active_packet.md` for the current worker context and avoid loading the entire project history into every prompt.
- Summarize stale context only after preserving exact theorem statements, dependencies, and evidence hashes.

## P3 - Multi-agent stage execution

- For each gate, spawn or simulate Formalizer, Lean Kernel, Algebra Oracle, Refuter, Librarian, Search, Integrator, and Auditor branches.
- Enforce independent artifacts per branch.
- Aggregate by evidence-weighted score, not majority vote.
- Hard veto if final text contains `sorry`, `admit`, `axiom`, `unsafe`, unverified assumptions, undefined symbols, dependency cycles, or unresolved counterexamples.

## P4 - Research-math specialization

- Add domain reference packs for braid/YBE/PBW/rewriting systems and braided Fock structures.
- Maintain a theorem card for each lemma: statement, hypotheses, normal form, dependency edges, proof status, and refutation attempts.
- Use the line-map gate to translate informal PBW/critical-pair arguments into atomic Lean obligations.

## P5 - Production metrics

Track the following metrics per long run:

- number of accepted kernel-verified lemmas;
- number of rejected false theorem statements;
- error-signature reuse rate;
- dependency-cycle count;
- proof replay success rate;
- final audit pass/fail;
- human-review hours saved or required.
