# Prompt-level MoE activation protocol

The system cannot directly control a model's hidden MoE routing.  It can, however, create prompts and artifacts that increase the chance that useful mathematical subskills are activated.

Use concise role headers and artifact contracts:

- Algebra/formalizer mode: definitions, domains, coercions, theorem statements.
- Proof-search mode: induction, rewrite, contradiction, construction, calculation.
- Lean-engineering mode: imports, namespaces, theorem names, tactic sequence, compiler logs.
- Refuter mode: minimal counterexamples, boundary cases, missing hypotheses.
- Library mode: Mathlib/local search terms and exact lemma candidates.
- Auditor mode: forbidden tokens, axioms, replay, dependency closure.

Do not ask one agent to be all modes at once.  Dispatch narrow tasks, write results to disk, and let the gate selector compare artifacts.
