# MathProve Skill

Turn math into a **step-by-step, tool-checked, talk-ready** workflow.

MathProve has one simple rule: **don’t let proofs run on vibes**. Break the problem into small steps. If a step is “just algebra”, SymPy checks it fast. If a step needs real rigor, Lean4 + Mathlib verifies it. Every passed step leaves an audit trail in the draft, and the final output is a `Solution.md` that can survive questions.

---

## What you get

- **One step, one piece of evidence**: each step must pass SymPy or Lean4.
- **Talk-friendly by design**: per step, you write symbols/assumptions/why it works (great for talks & reviews).
- **Audit loop**: `draft.md` → `final_audit.py` → `Solution.md`.
- **Anti-cheat gate (optional)**: Lean4 reverse gate forbids `sorry/admit/axiom/constant/opaque`.
- **Parallel help (optional)**: subagent routing for explanations, Mathlib lemma scouting, Lean skeletons, SymPy checks.

---

## Natural-language usage (copy & paste)

You can hand tasks to your agent in plain language (no need to write steps first):

Example A (compute-heavy, SymPy-first):
```text
Use MathProve for this task:
- Problem: simplify (x+1)^2 - (x^2+2x+1)
- Output: must generate Solution.md, and draft.md must record symbols + evidence for every step
```

Example B (proof-heavy, Lean4-first):
```text
Use MathProve for this task:
- Problem: prove that for any natural number n, n + 0 = n
- Lean project: D:\MATH Studio\math_studio
- Output: must enable lean-gate, generate reverse_gate.lean, and only then produce Solution.md
```

Example C (hybrid + subagents):
```text
Use MathProve for this task:
- Problem: prove and verify: for any real x, (x+1)^2 = x^2 + 2x + 1
- Lean project: D:\MATH Studio\math_studio
- Subagents: yes (main agent plans + merges; subagents produce explanations / lemma candidates / Lean skeletons / SymPy checks)
- Output: draft.md must include notation table, assumption ledger, and step-by-step talk-friendly explanations
```

---

## 3-minute CLI quickstart

### 1) Install deps (SymPy is the minimum)
```powershell
python -m pip install -r requirements-dev.txt
```

### 2) Check Lean4 + Mathlib (recommended)
Point `--project` to your Lake + Mathlib project directory:
```powershell
python scripts/check_env.py --project "D:\MATH Studio\math_studio" --verify-mathlib
```

### 3) Route steps + run the final audit (with gate)
```powershell
python scripts/step_router.py --input "steps.json" --output "steps.routed.json" --explain
python scripts/final_audit.py --steps "steps.routed.json" --solution "Solution.md" --lean-cwd "D:\MATH Studio\math_studio" --lean-gate --lean-timeout 120
```

---

## Config knobs you’ll actually use

### Timeouts & retries
- SymPy default: `final_audit.py --timeout <seconds>`
- Lean4 default: `final_audit.py --lean-timeout <seconds>`
- Per-step override: `step.checker.timeout`
- Retries: `step.checker.retries`

### Subagents (parallel helpers)
- Explicit enable: `MATHPROVE_SUBAGENT=1`
- Optional driver: `MATHPROVE_SUBAGENT_DRIVER=<your IDE/CLI dispatcher>`
- Generate a task pack (for parallel dispatch or as a single-agent checklist):
```powershell
python scripts/subagent_tasks.py --steps steps.routed.json --out-dir subagent_tasks --emit-md
```

### Path overrides (multi-Python / multi-Lean setups)
- SymPy: `final_audit.py --python / --sympy-python`, or set `checker.python` per step
- Lean4: set `checker.lean_path / checker.lake_path`, or use `lean_repl_client.py --lean-path/--lake-path`

---

## What is the Lean4 reverse gate (and why you want it)

In one sentence: **it upgrades “seems proven” to “the compiler agrees”**.

With `--lean-gate`, MathProve will:
- generate `reverse_gate.lean` (collect all Lean steps into one file)
- lint it (ban `sorry/admit/axiom/constant/opaque`, require step map)
- compile it inside your `--lean-cwd` Lake+Mathlib project: `lake env lean reverse_gate.lean`

> On Windows you can use `scripts/check_reverse_lean4.ps1`. On other OSes, run `scripts/lint_reverse_lean4.py` + `lake env lean` manually for equivalent checks.

---

## Repo layout

- `SKILL.md`: the agent-facing master guide (start here)
- `scripts/`: executors (SymPy / Lean4 / reverse gate / subagents / final audit)
- `assets/`: templates + schema (talk-friendly)
- `references/`: playbooks + examples (incl. web-inspiration logging)

## Contributing

See `CONTRIBUTING.md`. PRs welcome: better Mathlib lemma scouting, stronger gates, clearer step explanations, better multi-agent task formats.

