# Research basis for MathProve v7

This design is based on a conservative synthesis of current high-credibility systems:

- DeepSeek v3.2/Speciale: separate high-compute reasoning from production tool-use; MathProve uses deep reasoning for proposal/refutation but keeps Lean/SymPy as the authority.
- AlphaProof: treat proof search as interaction with a formal environment and use RL/test-time search ideas as a design analogue for staged exploration.
- DeepSeek-Prover-V2: recursively decompose hard theorems into subgoals and train/operate on subgoal chains.
- BFS-Prover-V2: prefer step-level tactic generation for interactivity and repairability.
- Tao/Claude Code workflow: start with notation, skeleton, line-map, then fill lemmas; avoid zero-shot whole-proof delegation.
- AXLE: proof manipulation and verification primitives should be infrastructure, not an afterthought.
- Gauss/Math Inc: large formalization requires blueprints, human scaffolding, long-running agents, integration, refactoring, and maintainability after compile success.

The operational consequence is: MathProve v7 is a proof factory, not a one-shot prover.
