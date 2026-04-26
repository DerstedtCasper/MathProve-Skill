# MathProve v7 Deep Optimization Report

## Executive conclusion

This round turns MathProve into a long-horizon, file-backed proof factory rather than a one-shot proof prompt. The design assumes that token and wall-clock budgets may be intentionally large. The system therefore uses phase manifests, context shards, proof-memory events, evidence-weighted candidate selection, hard vetoes, and restartable multi-agent work packets.

The upgrade is source-level, not only prompt-level. It adds runtime helpers, scripts, schemas, references, SOP files, and pseudotests while preserving the original emphasis on Lean/SymPy verification and final audit.

## Source audit result

The uploaded source package contained a useful MathProve structure and documentation, including top-level proxy scripts, skill prompts, Lean templates, and proof workflow material. The package did not expose every implementation layer described by earlier README-level claims. v7 therefore treats the previous design as the target architecture and fills the missing operational layer with a small, standard-library proof-factory runtime.

## Main v7 upgrades

1. Long-horizon proof factory: hard theorems must pass through problem lock, library reconnaissance, notation gate, blueprint gate, skeleton gate, line-map gate, lemma sprint gate, refutation gate, integration/refactor gate, final audit gate, and research handoff.
2. File-backed context lake: every phase writes summaries, candidate manifests, proof-memory events, error signatures, and evidence paths so total project state can exceed one model context.
3. MoE-style expert router: v7 cannot force hidden model-internal MoE routing, so it operationalizes expert diversity through task packets for Formalizer, Lean Kernel, Algebra Oracle, Refuter, Librarian, Search, Integrator, and Auditor roles.
4. Evidence-weighted selection: verified and replayable candidates beat fluent but uncertified candidates. Majority vote is never allowed to overrule hard verification evidence.
5. Anti-laziness budget contract: a large budget is treated as permission for deeper search, refutation, and refactoring, not as permission for unfalsified confidence.
6. Integration/refactor emphasis: large formalization projects fail when compilation, imports, naming, maintainability, and dependency closure are ignored. v7 makes this a required gate.

## Research basis encoded in the design

- Recursive theorem proving and subgoal decomposition inspired the proof-forest and lemma-cluster structure.
- Step-level tactic generation inspired the lemma sprint gate.
- Lean-environment feedback as sequential proof state inspired the verifier-centered candidate loop.
- Large public formalization projects inspired the blueprint, integration, and refactor gates.
- Graph memory systems inspired the proof-memory event model with update, extend, contradict, and derive relations.

## Key files added or updated

- `skill/SKILL.md`: v7 entrypoint and non-negotiable proof rules.
- `skill/agent.md`: long-horizon orchestrator constitution.
- `skill/runtime/proof_factory.py`: high-budget stage/candidate/memory utilities.
- `skill/runtime/proof_factory_v7.py`: v7 evidence scoring and hard veto helpers.
- `skill/runtime/context_lake_v7.py`: persistent context shard index.
- `skill/runtime/moe_router_v7.py`: stage-specific expert activation.
- `skill/scripts/mathprove_v7_pseudotest.py`: stdlib protocol test suite.
- `skill/scripts/proof_factory_pseudotest.py`: proof-factory safety test suite.
- `skill/sop/proof_factory_v7.md`: operational SOP.
- `skill/references/*v7.md`: detailed protocol references.
- `tests/test_proof_factory_v7.py`: pytest-style coverage for the new runtime helpers.

## Validation performed

Completed checks:

- `package_skill.py` validation passed.
- Final installable `skill.zip` was produced successfully.
- `skill.zip` has 95 entries and `zipfile.testzip()` returned `None`.
- `MathProve-Skill-ultra-v7-source.zip` has 179 entries and `zipfile.testzip()` returned `None`.
- `mathprove_v7_pseudotest.py` passed 7/7 protocol checks.
- `proof_factory_pseudotest.py` passed 8/8 proof-factory checks.

Scope limitation:

This container was not a full Lean/Mathlib benchmark environment. The validation performed here is protocol, packaging, and static-safety validation. A real theorem benchmark should be run in the local Lean/Mathlib or CI environment.

## Recommended next engineering steps

1. Connect `proof_factory_v7.Candidate` manifests to `verify_lean.py`, `verify_sympy.py`, and `final_audit.py` outputs.
2. Write Lean/SymPy logs into candidate evidence fields automatically.
3. Build a local Mathlib retrieval index for the Librarian expert.
4. Partition lemma DAGs into independent clusters and launch parallel lemma sprint workers.
5. Add nightly long-run benchmarks for miniF2F-style, ProofNet-style, and research-project-style tasks.
6. Add proof refactor/golf/import minimization after each verified integration gate.
