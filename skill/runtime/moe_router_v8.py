"""MoE-style expert activation policy for MathProve v8."""
from __future__ import annotations

EXPERTS = {
    "formalizer": "definitions, theorem statements, quantifiers, typeclass assumptions",
    "skeletonist": "lemma DAGs and Lean skeletons",
    "line_mapper": "informal-to-formal atomic obligations",
    "tactic_sprinter": "step-level Lean tactic attempts",
    "whole_proof_proposer": "high-level route candidates",
    "librarian": "Mathlib/local theorem discovery and imports",
    "algebraic_verifier": "exact computation, finite models, symbolic checks",
    "refuter": "counterexamples, hidden assumptions, false converses",
    "repairer": "statement repair and lemma extraction",
    "integrator": "namespace/import/refactor/maintainability",
    "auditor": "replay, evidence, dependency profile",
    "domain_expert": "field-specific mathematics",
}

FULL_PANEL = list(EXPERTS.keys())

DEFAULT_BY_STAGE = {
    "problem_lock": ["formalizer", "refuter", "auditor"],
    "knowledge_pack": ["librarian", "domain_expert", "formalizer", "auditor"],
    "notation": ["formalizer", "refuter", "auditor"],
    "skeleton": ["skeletonist", "librarian", "auditor"],
    "line_map": ["line_mapper", "formalizer", "refuter", "auditor"],
    "lemma_sprint": ["tactic_sprinter", "librarian", "algebraic_verifier", "repairer", "refuter", "auditor"],
    "refutation": ["refuter", "algebraic_verifier", "domain_expert", "auditor"],
    "integration": ["integrator", "librarian", "auditor"],
    "final_audit": ["auditor", "refuter"],
    "memory_update": ["auditor", "integrator"],
}


def activate(stage: str, difficulty: str = "normal", uncertainty: bool = False, repeated_failure: bool = False) -> list[str]:
    if difficulty in {"hard", "frontier", "research"} or uncertainty or repeated_failure:
        return FULL_PANEL.copy()
    return DEFAULT_BY_STAGE.get(stage, ["formalizer", "refuter", "auditor"])
