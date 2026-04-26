# MathProve-Skill

Language / 语言: **English** | [中文](README.zh-CN.md)

MathProve-Skill is a research-oriented proof engineering skill for long-horizon mathematical formalization. It combines Lean4, SymPy, staged agent orchestration, evidence-weighted candidate selection, and final audit gates to turn informal mathematical work into restartable, inspectable, and partially machine-checkable proof artifacts.

The project is intended for research workflows where correctness, replayability, and explicit failure modes are central. It treats theorem proving as a pipeline of durable artifacts rather than a single conversational answer.

## Research Scope

MathProve supports:

- theorem statement formalization and assumption locking;
- theorem-variant generation, lemma DAG construction, proof skeletons, and line maps;
- Lean4/Mathlib-oriented proof attempts and static safety checks;
- SymPy-based exact algebraic verification under explicit hypotheses;
- refutation and boundary-case search;
- long-horizon proof campaigns using context shards, candidate packs, handoff capsules, and proof-memory events.

It is especially suitable for algebra, representation theory, braid/YBE problems, quantum-group calculations, symbolic identities, and mathematical-physics arguments that benefit from a bridge between informal structure and machine-checkable evidence.

## Ultra v8 Architecture

v8 upgrades MathProve into a proof factory with the following components:

- **Stage gates**: problem lock, knowledge pack, notation, skeleton, line map, lemma sprint, refutation, integration, final audit, and proof-memory update.
- **Evidence-weighted candidate selection**: tool verification, dependency closure, refutation coverage, evidence completeness, maintainability, restartability, novelty, and cost sanity are scored explicitly.
- **Hard vetoes**: theorem drift, missing evidence, stale logs, non-skeleton `sorry`, Lean/SymPy failure, undefined domains, and unaudited final claims prevent promotion.
- **Context lake**: long-running campaigns externalize context into indexed shards and handoff capsules.
- **MoE routing**: difficult or frontier tasks activate a broader expert panel for formalization, line mapping, tactic search, refutation, repair, integration, and audit.
- **Final audit discipline**: a theorem is not reported as proved until dependency closure, no-sorry checks, replay logs, and evidence coverage are accepted.

## Installation

```bash
git clone https://github.com/DerstedtCasper/MathProve-Skill.git MathProve-Skill
cd MathProve-Skill
python -m pip install -r requirements-dev.txt
```

Mount as a Codex/Agent skill:

```powershell
New-Item -ItemType Junction `
  -Path "$env:USERPROFILE\.codex\skills\mathprove" `
  -Target "D:\AI_studio\MathProve-Skill\skill"
```

## Quickstart

```bash
python scripts/check_routes.py

python scripts/magi_plan.py \
  --problem "Prove and verify: for every real x, (x+1)^2 = x^2 + 2*x + 1" \
  --steps-out steps.json \
  --draft draft.md

python scripts/step_router.py \
  --input steps.json \
  --output steps.routed.json \
  --explain

python scripts/final_audit.py \
  --steps steps.routed.json \
  --solution Solution.md \
  --lean-cwd "<path-to-lean-project>" \
  --lean-gate
```

Exercise the v8 protocol:

```bash
python skill/scripts/mathprove_v8_pseudotest.py
python scripts/mathprove_v8_pseudotest.py
```

## Repository Layout

```text
skill/                 installable skill root
skill/runtime/         orchestration, proof factory, verification helpers
skill/scripts/         skill-local CLI tools
skill/references/      stage protocols and research references
skill/assets/          schemas, templates, prompts, Lean assets
scripts/               compatibility wrappers
tests/                 regression tests
docs/optimization/     v8 report, patch notes, and pseudotest data
```

## Verification

Recommended checks:

```bash
python -m py_compile skill/runtime/proof_factory_v8.py skill/runtime/context_lake_v8.py skill/runtime/moe_router_v8.py
python skill/scripts/mathprove_v8_pseudotest.py
python scripts/mathprove_v8_pseudotest.py
python -m pytest -q
```

Latest local validation:

```text
125 passed
```

## License

MIT License
