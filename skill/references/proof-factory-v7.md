# MathProve v7 Proof Factory

Use this for hard formalization projects where aggregate context exceeds one model window. The run is split into gates: problem lock, library reconnaissance, notation, skeleton, line map, lemma sprint, refutation, integration/refactor, final audit, and research handoff.

Each gate writes a stage manifest and may launch many candidate branches. Branches do not rewrite the whole proof: they solve one gate or one lemma cluster. Selection is evidence-weighted: Lean/SymPy certificate first, then closed dependencies, refutation coverage, maintainability, manifest completeness, and restartability.

Stop only when the final audit passes, a falsifying counterexample is certified, or a precise environmental blocker is documented.
