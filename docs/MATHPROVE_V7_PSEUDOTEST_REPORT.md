# MathProve v7 Pseudotest Report

## Summary

Final status: PASS for both stdlib protocol suites.

## Suite A: `mathprove_v7_pseudotest.py`

Result: 7/7 passed.

Checks:

1. `evidence_weighted_selection`: verified evidence beats fluent but uncertified proof text.
2. `hard_veto_dominates`: hard vetoes override high nominal scores.
3. `final_rejects_forbidden_tokens`: final proof text containing `sorry` is rejected.
4. `context_lake_index`: context shards can be written and indexed.
5. `moe_eight_experts`: research mode activates the full eight-role expert set.
6. `notation_expert_selection`: notation gate activates Formalizer and Refuter roles.
7. `zero_shot_policy_present`: the skill explicitly forbids zero-shot whole-proof delegation.

## Suite B: `proof_factory_pseudotest.py`

Result: 8/8 passed.

Checks:

1. stage order is canonical;
2. verifier evidence beats rhetoric;
3. final `sorry` is vetoed;
4. skeleton-stage `sorry` is allowed only as a placeholder;
5. line-map guard is present;
6. checkpoint resume logic is represented;
7. proof-memory event roundtrip works;
8. anti-laziness budget contract is present.

## Packaging validation

- `package_skill.py` validation passed.
- `skill.zip`: 95 entries, `zipfile.testzip()` returned `None`.
- `MathProve-Skill-ultra-v7-source.zip`: 179 entries, `zipfile.testzip()` returned `None`.

## Limitation

These are protocol/static-safety tests. They do not replace a real Lean/Mathlib benchmark run.
