# MathProve Ultra v8 Patch Notes

## Added

- `skill/agent.md`: Ultra v8 constitution with no-premature-closure, context lake, MoE routing, proof memory, and Speciale-MLM loop.
- `skill/SKILL.md`: new stage-gated workflow and runtime references.
- `skill/config.yaml`: v8 proof_factory and MoE configuration.
- `skill/runtime/proof_factory_v8.py`: stage specs, candidate evidence, scoring, hard vetoes, quota vetoes, context shards, proof memory, termination gate, static Lean audit.
- `skill/runtime/context_lake_v8.py`: context index and handoff helpers.
- `skill/runtime/moe_router_v8.py`: stage/difficulty-based expert activation.
- `skill/scripts/proof_factory_v8.py`: CLI demo, static audit, budget, termination checks.
- `skill/scripts/mathprove_v8_pseudotest.py`: protocol regression tests.
- `skill/references/*-v8.md`: budget/context lake, stage gates, MoE router, formalization scaffold, proof memory, frontier protocol, research basis.
- `skill/assets/schemas/candidate_evidence_v8.schema.json`.
- `skill/assets/templates/v8_stage_manifest.md` and `handoff_capsule_v8.md`.

## Changed

- Candidate promotion now includes theorem-statement hash drift detection.
- Frontier mode now has stage minimum quota vetoes.
- Termination is explicitly limited to final audit approval, formal counterexample, user-visible theorem repair, or environment blocker with replay log.
- Full MoE panel activation is mandatory for frontier/research/repeated-failure modes.

## Tested

- `/usr/bin/python3 -m py_compile` on v8 runtime/scripts: passed.
- `skill/scripts/mathprove_v8_pseudotest.py`: 9/9 passed.
- skill packaging validator via skill-creator packager: passed.
- `unzip -t mathprove_ultra_v8_skill.zip`: passed.
