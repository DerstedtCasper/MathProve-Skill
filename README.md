# MathProve-Skill

Language / 语言: **English** | [中文](docs/README.zh-CN.md)

MathProve-Skill is a research-oriented proof engineering skill for long-horizon mathematical formalization. It combines Lean4, SymPy, staged agent orchestration, evidence-weighted candidate selection, and final audit gates to turn informal mathematical work into restartable, inspectable, and partially machine-checkable proof artifacts.

The project is designed for research settings where correctness, replayability, and failure diagnosis matter more than producing fluent proof sketches. It treats proof construction as an auditable pipeline: statements are locked, assumptions are recorded, candidate branches are compared by evidence, and promoted results must survive explicit verification gates.

## Research Scope

MathProve targets mathematical and mathematical-physics workflows such as:

- formalizing theorem statements from research notes or manuscripts;
- decomposing difficult arguments into theorem variants, lemma DAGs, skeletons, and line maps;
- searching for algebraic, analytic, combinatorial, representation-theoretic, braid/YBE, or quantum-group proof routes;
- running exact symbolic checks with explicit assumptions;
- using Lean4/Mathlib evidence where available, and recording precise blockers where unavailable;
- maintaining proof memory across long campaigns instead of relying on a single chat transcript.

MathProve does not treat natural-language plausibility as mathematical evidence. Agent votes, heuristic routes, and informal sketches can guide exploration, but they do not certify a theorem. Certification is reserved for kernel-checked artifacts, replayable symbolic computation, explicit counterexample search, or audited evidence packs.

## Ultra v8 Overview

The current v8 architecture upgrades the earlier MAGI + SymPy + Lean workflow into a long-horizon proof factory.

Core additions include:

- **Stage-gated proof factory**: problem lock, knowledge pack, notation gate, skeleton gate, line-map gate, lemma sprint, refutation, integration, final audit, and proof-memory update.
- **Evidence-weighted promotion**: candidates are ranked by tool verification, dependency closure, refutation coverage, evidence completeness, maintainability, restartability, novelty, and cost sanity.
- **Hard vetoes**: undefined symbols, unstated domains, theorem-statement drift, stale logs, missing evidence, non-skeleton `sorry`, Lean/SymPy failures, float-only exact proofs, and unaudited final claims fail closed.
- **Context lake**: long proofs externalize state into indexed shards, handoff capsules, candidate packs, logs, and proof-memory events.
- **MoE expert routing**: frontier/research/repeated-failure modes activate a fuller panel of formalizer, skeletonist, line mapper, librarian, tactic sprinter, algebraic verifier, refuter, repairer, integrator, auditor, and domain expert roles.
- **No premature closure**: local context exhaustion is not a valid stopping condition. A campaign must end with a gate decision, counterexample, user-visible theorem repair, or replayable environment blocker.

## Architecture

```text
MathProve-Skill/
├── skill/
│   ├── SKILL.md                  # Skill entrypoint and operational contract
│   ├── agent.md                  # Proof-engineering constitution
│   ├── config.yaml               # Default runtime and proof-factory configuration
│   ├── runtime/
│   │   ├── orchestrator.py        # High-level proof loop
│   │   ├── proof_factory_v8.py    # Stage gates, scoring, vetoes, audit helpers
│   │   ├── context_lake_v8.py     # Context shard and handoff utilities
│   │   ├── moe_router_v8.py       # Stage/difficulty expert activation
│   │   ├── safe_verify.py         # Lean-oriented safety checks
│   │   ├── parallel_runner.py     # Parallel candidate execution
│   │   └── magi/                  # Multi-role planning protocol
│   ├── scripts/                   # Skill-local CLI entrypoints
│   ├── references/                # Stage, routing, memory, and research protocols
│   └── assets/                    # Schemas, templates, prompts, Lean assets
├── scripts/                       # Compatibility wrappers
├── tests/                         # Regression tests
├── docs/
│   ├── README.en.md
│   ├── README.zh-CN.md
│   └── optimization/              # v8 report, patch notes, pseudotest report
└── runtime/                       # Compatibility runtime shims
```

## Installation

### Standalone repository

```bash
git clone https://github.com/DerstedtCasper/MathProve-Skill.git MathProve-Skill
cd MathProve-Skill
python -m pip install -r requirements-dev.txt
```

### Codex/Agent skill mount

Mount the `skill/` directory as the skill root:

```powershell
New-Item -ItemType Junction `
  -Path "$env:USERPROFILE\.codex\skills\mathprove" `
  -Target "D:\AI_studio\MathProve-Skill\skill"
```

The skill metadata name is `mathprove-skill`; the mount directory may remain `mathprove` if that is the local convention used by the agent runtime.

## Quickstart

### 1. Check local routes

```bash
python scripts/check_routes.py
```

This checks availability of configured symbolic, Lean, and optional orchestration routes.

### 2. Generate a MAGI plan

```bash
python scripts/magi_plan.py \
  --problem "Prove and verify: for every real x, (x+1)^2 = x^2 + 2*x + 1" \
  --steps-out steps.json \
  --draft draft.md
```

### 3. Route and execute proof steps

```bash
python scripts/step_router.py \
  --input steps.json \
  --output steps.routed.json \
  --explain
```

### 4. Run final audit

```bash
python scripts/final_audit.py \
  --steps steps.routed.json \
  --solution Solution.md \
  --lean-cwd "<path-to-lean-project>" \
  --lean-gate
```

### 5. Exercise the v8 proof factory protocol

```bash
python skill/scripts/mathprove_v8_pseudotest.py
python scripts/mathprove_v8_pseudotest.py
```

## Run Artifacts

Runtime artifacts are written outside the skill package by default. A typical run contains:

```text
mathprove_workspace/runs/<run_id>/
├── problem.md
├── problem_lock.md
├── assumptions.md
├── manifest.json
├── status.json
├── context_lake/
├── knowledge/
├── plan/
├── candidates/
├── magi/
├── sympy/
├── lean/
├── memory/
├── draft/
├── audit/
└── logs/
```

The package itself should remain immutable during a proof run. Temporary artifacts, logs, candidate packs, and handoff capsules belong in the workspace.

## Verification Discipline

MathProve distinguishes four levels of support:

1. kernel-checked Lean or another accepted proof-assistant artifact;
2. replayed exact symbolic computation with explicit assumptions;
3. bounded or exhaustive counterexample search with recorded scope;
4. human-readable derivation linked to auditable artifacts.

Only these levels may support promoted mathematical claims. Brainstorming, majority votes, analogies, and hidden reasoning are exploratory signals, not proof certificates.

## Development Checks

The repository currently verifies with:

```bash
python -m py_compile skill/runtime/proof_factory_v8.py skill/runtime/context_lake_v8.py skill/runtime/moe_router_v8.py
python skill/scripts/mathprove_v8_pseudotest.py
python scripts/mathprove_v8_pseudotest.py
python -m pytest -q
```

Latest local validation after the v8 merge:

```text
125 passed
```

## Documentation

- [English README](docs/README.en.md)
- [中文 README](docs/README.zh-CN.md)
- [v8 deep optimization report](docs/optimization/DEEP_OPTIMIZATION_REPORT_V8.md)
- [v8 patch notes](docs/optimization/PATCH_NOTES_V8.md)
- [v8 pseudotest report](docs/optimization/PSEUDOTEST_REPORT_V8.json)

## License

MIT License
