# Formalization Scaffold v8

Use the skeleton-first workflow for Lean projects.

1. Step 0: formalize symbols, structures, coefficients, namespaces, imports, and index conventions.
2. Step 1: create theorem and lemma skeletons with explicit `sorry` placeholders. Do not attempt full proof search yet.
3. Step 2A: map each informal proof line to a formal obligation. Each line must have a reason, dependency list, and Lean target.
4. Step 2B: fill leaf lemmas one at a time. Prefer small reusable lemmas over giant automation attempts.
5. Step 3: integrate, refactor, replay, audit, and update memory.

Low-level tactic failures are not evidence that the theorem is false. They are evidence that the statement, local lemma, rewrite direction, or import set may need repair.
