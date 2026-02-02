/-
MathProve Reverse Lean4 Gate (Mathlib)

Hard rules:
  - One proof step per theorem/lemma: S1, S2, ...
  - No `sorry` / `admit` / `axiom` / `constant` / `opaque` (see lint_reverse_lean4.py)
  - Keep assumptions explicit in markdown / steps.json (do not hide them in Lean stubs)

This file is intended to be generated/overwritten by:
  - scripts/final_audit.py --lean-gate
-/

import Mathlib

set_option autoImplicit false
set_option maxRecDepth 512

-- Keep this mapping in sync with steps.json.
-- RIGOR_STEP_MAP
-- S1: <step_id> - <goal>
-- S2: ...

namespace MathProve

-- Paste one theorem/lemma per step below.
-- Example skeleton:
--
-- theorem S1 : True := by
--   trivial

end MathProve

