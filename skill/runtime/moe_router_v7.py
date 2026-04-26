"""MoE-style expert activation policy for MathProve v7."""
EXPERTS = {"formalizer":"definitions and theorem statements","lean_kernel":"Lean tactic state","algebra_oracle":"exact computation","refuter":"counterexamples and missing hypotheses","librarian":"Mathlib/local theorem discovery","search":"proof tree expansion","integrator":"maintainable Lean/refactor","auditor":"manifest and reproducibility checks"}
ALL_EIGHT = list(EXPERTS.keys())
DEFAULT_BY_STAGE = {"problem_lock":["formalizer","refuter","auditor"],"library_recon":["librarian","formalizer","lean_kernel"],"notation":["formalizer","lean_kernel","refuter"],"skeleton":["formalizer","librarian","auditor"],"line_map":["formalizer","refuter","lean_kernel"],"lemma_sprint":["lean_kernel","search","librarian","algebra_oracle","refuter"],"refutation":["refuter","algebra_oracle","auditor"],"integration":["integrator","librarian","lean_kernel","auditor"],"final_audit":["auditor","lean_kernel","refuter"]}
def activate(stage: str, difficulty: str = "normal", uncertainty: bool = False) -> list[str]:
    if difficulty in {"hard","frontier","research"} or uncertainty: return ALL_EIGHT.copy()
    return DEFAULT_BY_STAGE.get(stage, ["formalizer","refuter","auditor"])
