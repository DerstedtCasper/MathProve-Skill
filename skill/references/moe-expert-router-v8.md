# MoE Expert Router v8

Use MoE-style routing as task specialization, not theatrical role-play. Each expert produces a task card or candidate pack.

## Default routing

- problem_lock: Formalizer, Refuter, Auditor
- knowledge_pack: Librarian, DomainExpert, Formalizer
- notation: Formalizer, LeanKernel, Refuter
- skeleton: Skeletonist, Librarian, Auditor
- line_map: LineMapper, Formalizer, Refuter
- lemma_sprint: TacticSprinter, Librarian, AlgebraicVerifier, Repairer, Refuter
- refutation: Refuter, AlgebraicVerifier, Auditor, DomainExpert
- integration: Integrator, Librarian, LeanKernel, Auditor
- final_audit: Auditor, LeanKernel, Refuter

Escalate to the full panel for frontier, repeated failure, high uncertainty, or theorem-statement drift.

## Selection rule

Do not average opinions. Score candidate packs by evidence: kernel/tool verification, dependency closure, refutation coverage, evidence completeness, maintainability, restartability, novelty, and cost sanity. A hard soundness veto beats all votes.
