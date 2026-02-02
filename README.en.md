# MathProve

**MathProve** is a neuro-symbolic math verification pipeline. By integrating a symbolic computation engine (SymPy) and an interactive theorem prover (Lean 4), it provides formal verification and an auditable trail for large-language-model (LLM) mathematical reasoning.

The core goal is to mitigate LLM "hallucinations" in mathematical derivations: map Chain-of-Thought (CoT) into executable code or formal propositions, and ensure every step included in `Solution.md` has been checked by computation or by logic.

## Key Features

- **Hybrid Routing**: analyze step properties; route computation-heavy steps to SymPy; route proof-heavy steps to Lean 4 + Mathlib.
- **Strict Gatekeeping**: only steps that pass an execution backend are allowed into the final solution; failed steps trigger rollback or retries.
- **Formal Auditing**: generate a full `.lean` file and compile it for global consistency; prevent abusing `sorry` or circular arguments.
- **Structured Output**: produce standardized Markdown with notation, assumptions, and verification status.

## Architecture Overview

MathProve runs in the following stages:

1. **Decomposition**: convert a natural-language problem into atomic `steps.json`.
2. **Routing & Execution**:
   - **CAS Track**: use Python/SymPy for algebra, calculus, and other computational checks.
   - **ITP Track**: build Lean 4 statements and discharge them using Mathlib tactics.
3. **Verification**: validate return codes, stdout/stderr, and expected results per step.
4. **Synthesis**: aggregate all passed steps into the final report (`draft.md` → `Solution.md`).

## Requirements

- Python 3.8+
- Lean 4 + Lake (for formal verification; available via PATH or provided explicitly)
- Python deps:

```bash
python -m pip install -r requirements-dev.txt
```

## Installation

### As a standalone CLI tool

```bash
git clone https://github.com/DerstedtCasper/MathProve-Skill.git MathProve
cd MathProve
```

### Optional: integrate as an Agent/Codex skill

Mount the repo into the Codex skills directory (Windows default: `%USERPROFILE%\.codex\skills\`):

```powershell
New-Item -ItemType Junction `
  -Path "$env:USERPROFILE\.codex\skills\MathProve" `
  -Target "D:\AI bot\MathProve"
```

## Quickstart

### 1) Environment check (recommended)

Before running non-trivial proofs, ensure the Lean 4 project path is valid and Mathlib is built:

```bash
python scripts/check_env.py --project "<path-to-lean-project>" --verify-mathlib
```

### 2) Standard workflow (CLI)

Step A: route and validate per step

```bash
python scripts/step_router.py \
  --input "steps.json" \
  --output "steps.routed.json" \
  --explain
```

Flag notes:

- `--explain`: print routing decisions (SymPy vs Lean) in logs

Step B: final audit and synthesis

```bash
python scripts/final_audit.py \
  --steps "steps.routed.json" \
  --solution "Solution.md" \
  --lean-cwd "<path-to-lean-project>" \
  --lean-gate
```

Flag notes:

- `--lean-gate`: enable strict mode; generate `reverse_gate.lean` and compile the full proof chain

## `steps.json` format example

The schema is defined in `assets/step_schema.json`. The example below shows a SymPy step and a Lean4 step:

```json
{
  "problem": "Prove and verify: for any real x, (x+1)^2 = x^2 + 2x + 1",
  "steps": [
    {
      "id": "S1",
      "goal": "Expand (x + 1)^2",
      "checker": {
        "type": "sympy",
        "code": "import sympy as sp\nx = sp.Symbol('x')\nexpr = (x + 1)**2\nassert sp.expand(expr) == x**2 + 2*x + 1\nprint('ok')"
      }
    },
    {
      "id": "S2",
      "goal": "Formalize: right identity of addition on Nat",
      "checker": {
        "type": "lean4",
        "cmds": [
          "import Mathlib",
          "theorem S2 (n : Nat) : n + 0 = n := by simp"
        ]
      }
    }
  ]
}
```

## Advanced

### Lean Reverse Gate

To prevent "syntactically valid but logically invalid" proofs (e.g., abusing `axiom`, `constant`, or `sorry`), enable the reverse gate:

- generate `reverse_gate.lean` by aggregating all Lean steps
- lint: ban `sorry/admit/axiom/constant/opaque`
- compile via `lake env lean reverse_gate.lean` inside the Lake project

On Windows:

```powershell
pwsh -File scripts/check_reverse_lean4.ps1 `
  -Path "reverse_gate.lean" `
  -ProjectDir "<path-to-lean-project>" `
  -RequireMathlib `
  -RequireStepMap
```

### Subagent parallelization

For long proof chains, enable task splitting and generate a dispatchable task pack:

```bash
export MATHPROVE_SUBAGENT="1"
python scripts/subagent_tasks.py --steps steps.routed.json --out-dir ./tasks
```

## Repo layout

- `scripts/`: core executors
  - `step_router.py`: route steps (SymPy vs Lean4)
  - `final_audit.py`: final audit and `Solution.md` synthesis
  - `check_reverse_lean4.ps1`: reverse gate (lint + compile)
- `assets/`: schema and templates (`assets/step_schema.json`, `assets/templates/`)
- `tests/`: unit tests

## License

MIT License

