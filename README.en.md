# MathProve

Language / 语言: [English](README.en.md) | [中文](README.md)

MathProve is a neuro-symbolic math verification pipeline that combines SymPy and Lean4 to provide an auditable evidence trail. The goal is to turn natural-language derivations into executable steps and summarize verified results in `Solution.md`.

## Highlights
- **Hybrid routing**: switch between SymPy and Lean4 per step, with manual overrides.
- **MATH MAGI planning**: three-role voting with veto, producing structured `steps.json`.
- **Strict gates**: only `status=passed` steps with evidence can enter `draft.md`.
- **Audit closed-loop**: `final_audit.py` produces the audit result and `Solution.md`.
- **Auditable logs**: JSONL + Markdown summaries.
- **Optional routes**: subagent dispatch and web inspiration logging.

## Installation

### As a standalone CLI tool
```bash
git clone https://github.com/DerstedtCasper/MathProve-Skill.git MathProve
cd MathProve
```

### Mount as a Codex/Agent Skill
Mount the `skill/` directory and keep the directory name consistent with `name: mathprove` in `SKILL.md`:
```powershell
New-Item -ItemType Junction `
  -Path "$env:USERPROFILE\.codex\skills\mathprove" `
  -Target "D:\AI bot\MathProve\skill"
```

## Quickstart

### 1) Bootstrap (optional)
Generate local overrides and refs template:
```bash
python scripts/bootstrap.py
```

### 2) Route check (required)
Validate SymPy/Lean4/Mathlib availability:
```bash
python scripts/check_routes.py
```

### 3) MATH MAGI plan (required)
```bash
python scripts/magi_plan.py --problem "<problem text>" --steps-out steps.json --draft draft.md
```

### 4) Step routing & execution (required)
```bash
python scripts/step_router.py \
  --input "steps.json" \
  --output "steps.routed.json" \
  --explain
```

### 5) Final audit (required)
```bash
python scripts/final_audit.py \
  --steps "steps.routed.json" \
  --solution "Solution.md" \
  --lean-cwd "<path-to-lean-project>" \
  --lean-gate
```

### 6) Draft append (optional)
Append a single verified step:
```bash
python scripts/draft_logger.py --draft draft.md --step-file one_step.json
```

## State machine
BOOTSTRAP → ROUTE_CHECK → MATH_MAGI_PLAN → STEP_EXECUTE → VERIFY → AUDIT → DRAFT_COMMIT → FINAL_RESPONSE

## `steps.json` example
```json
{
  "problem": "Prove and verify: for any real x, (x+1)^2 = x^2 + 2x + 1",
  "steps": [
    {
      "id": "S1",
      "goal": "Expand (x + 1)^2",
      "engine": "sympy",
      "expected_evidence": "sympy output: simplify(...) == 0",
      "checker": {
        "type": "sympy",
        "code": "import sympy as sp\nx = sp.Symbol('x')\nexpr = (x + 1)**2\nassert sp.expand(expr) == x**2 + 2*x + 1\nprint('ok')"
      }
    },
    {
      "id": "S2",
      "goal": "Formalize: right identity of addition on Nat",
      "engine": "lean4",
      "expected_evidence": "lean build success (no goals, no sorries)",
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

## Configuration & routing

### config.yaml / config.local.yaml
- `skill/config.yaml`: defaults.
- `skill/config.local.yaml`: local overrides (gitignored), created by `bootstrap.py`.

### Path overrides
- SymPy interpreter: `final_audit.py --python` or `--sympy-python`
- Lean4 client: `final_audit.py --lean-python`
- Lean/Lake executables: `step.checker.lean_path` / `step.checker.lake_path`

### Subagent route
- Auto-enable when `routes.subagent.auto_enable=true`.
- Task pack generation: `python scripts/subagent_tasks.py --steps steps.routed.json --out-dir ./tasks`

## Web inspiration example
Append web inspiration to `skill/references/refs.md`:
```bash
python skill/scripts/web_inspiration.py \
  --query "mathlib lemma for ring simplification" \
  --sources-json "[{\"title\":\"Mathlib simp lemma\",\"url\":\"https://example.com\",\"summary\":\"used for ring simplification\"}]" \
  --notes "selecting candidate lemmas"
```

## Repo layout
- `skill/`: installable Skill root (recommended mount)
  - `SKILL.md`: entry and hard rules
  - `assets/`: schemas and templates
  - `references/`: external references log
  - `config.yaml` / `config.local.yaml`
  - `runtime/`: runtime helpers
  - `scripts/`: standard script entrypoints
- `scripts/`: compatibility entrypoints (proxy to `skill/scripts/`)
- `tests/`: unit tests

## License
MIT License
