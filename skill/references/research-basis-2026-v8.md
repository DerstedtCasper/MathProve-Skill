# Research Basis 2026 v8

Implementation translations used by this skill:

- AlphaProof-style verifier environment: model proof search as states, tactics/actions, verifier rewards, and replayable trajectories.
- DeepSeek-Prover-V2-style recursive decomposition: decompose hard targets into subgoals, solve leaves, then synthesize upward.
- BFS-Prover-V2-style inference scaling: planner-enhanced multi-agent tree search, shared subgoal cache, and step-level prover attempts.
- Kimina-Prover-style reasoning-driven exploration: use structured reasoning to generate/refine Lean steps, but certify only with the verifier.
- AXLE/Axiom-style proof manipulation: treat proof verification and extraction/manipulation primitives as infrastructure, not optional extras.
- Gauss-style proof engineering: blueprint, massive parallelism, refactoring, maintainability, and integration into Mathlib-scale code are part of the final objective.
- Tao-style human-assisted formalization: skeleton first, line-map second, leaf-lemma sprint third.

This file is a design basis, not a citation database. Cite external sources in user-facing research reports when factual claims about systems/results are made.
