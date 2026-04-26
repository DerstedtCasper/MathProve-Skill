# Stage-parallel eight-variant ensemble

At each stage, dispatch up to eight variants.  They are not fictional personalities; they are work packages with separate artifacts.

1. Formalizer: sharpen definitions, quantifiers, domains, coercions, and theorem statements.
2. Skeletonist: write Lean declarations and dependency DAG, allowing `sorry` only in skeleton files.
3. Line Mapper: map each informal proof line to a formal declaration or proof obligation.
4. Tactic Sprinter: attack one lemma at a time in isolated Lean workspaces.
5. Refuter: search for counterexamples, missing hypotheses, wrong directions, and degenerate cases.
6. Librarian: search Mathlib/local library for exact lemmas, imports, and naming conventions.
7. Repairer: use compiler errors to produce minimal patches, never new axioms.
8. Auditor: verify logs, forbidden tokens, dependency closure, axiom reports, and replayability.

Selection is evidence-weighted, not majority vote.  Hard veto beats popularity.  A single verified counterexample blocks promotion.

Default scoring:

- tool verification: 0.30
- dependency closure: 0.18
- refutation coverage: 0.18
- evidence completeness: 0.12
- maintainability: 0.10
- restartability: 0.07
- novelty: 0.03
- cost score: 0.02

Candidates below threshold must either be repaired or kept as memory, not silently promoted.
