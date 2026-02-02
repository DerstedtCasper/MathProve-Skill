#!/usr/bin/env python3
"""
Lean4 reverse-audit linter for the "Mathematical Rigorous Exploration" workflow.

Goal: prevent "cheating" by passing the Lean gate with unrelated trivial theorems.

This linter intentionally stays lightweight: it only enforces structure and mapping
constraints; it does NOT attempt to prove semantic equivalence between Markdown steps
and Lean proofs (that would require a much richer pipeline).
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple


@dataclass(frozen=True)
class LintIssue:
    code: str
    message: str


STEP_IN_MD_RE = re.compile(r"\(\s*S(\d+)\s*\)")
# Require *exact* step names `S1`, `S2`, ... (no suffixes like `S1_example`).
# This keeps the mapping unambiguous and discourages leaving templates unchanged.
STEP_DECL_RE = re.compile(r"(?m)^\s*(?:theorem|lemma)\s+S(\d+)(?!\d)(?![A-Za-z0-9_'])")
STEP_MAP_RE = re.compile(r"(?m)^\s*--\s*S(\d+)\s*:")
DECL_KIND_RE = re.compile(r"(?m)^\s*(def|structure|inductive|abbrev)\s+([A-Za-z_][A-Za-z0-9_']*)\b")
FORBIDDEN_DECL_RE = re.compile(r"(?m)^\s*(axiom|constant|opaque)\b")
IMPORT_MATHLIB_RE = re.compile(r"(?m)^\s*import\s+Mathlib(\.|\\s|$)")
USER_MATRIX_DEF_RE = re.compile(r"(?m)^\s*(?:def|structure|inductive|abbrev)\s+Matrix\b")


def _read_text(p: Path) -> str:
    # Lean/Markdown may contain BOM on Windows; tolerate it.
    return p.read_text(encoding="utf-8-sig")


def _extract_md_steps(md: str) -> Set[int]:
    return {int(m.group(1)) for m in STEP_IN_MD_RE.finditer(md)}


def _extract_lean_steps(lean: str) -> Set[int]:
    return {int(m.group(1)) for m in STEP_DECL_RE.finditer(lean)}

def _extract_step_header_chunks(lean: str, *, max_chars: int = 2000) -> List[Tuple[int, str]]:
    """
    Extract a best-effort "header chunk" for each step theorem/lemma Sx, spanning
    multiple lines until the `:=` that starts the proof (or up to max_chars).

    This avoids false positives when types are formatted across lines (common for
    matrix equalities and long binders).
    """
    out: List[Tuple[int, str]] = []
    for m in STEP_DECL_RE.finditer(lean):
        step = int(m.group(1))
        start = m.start()
        # Best effort: take until ':=' which usually begins the proof term.
        j = lean.find(":=", m.end())
        if j == -1:
            j = min(len(lean), start + max_chars)
        else:
            j = min(j, start + max_chars)
        out.append((step, lean[start:j]))
    return out


def _extract_step_map(lean: str) -> Set[int]:
    return {int(m.group(1)) for m in STEP_MAP_RE.finditer(lean)}


def _extract_decl_kinds(lean: str) -> List[Tuple[str, str]]:
    return [(m.group(1), m.group(2)) for m in DECL_KIND_RE.finditer(lean)]


def _missing(expected: Iterable[int], got: Set[int]) -> List[int]:
    return [n for n in sorted(set(expected)) if n not in got]


def lint(
    *,
    lean_text: str,
    md_text: Optional[str],
    min_steps: int,
    require_step_map: bool,
    require_mathlib: bool,
    require_domain_defs: bool,
    lean_path: Optional[Path],
) -> List[LintIssue]:
    issues: List[LintIssue] = []

    lean_steps = _extract_lean_steps(lean_text)
    step_map = _extract_step_map(lean_text)
    decls = _extract_decl_kinds(lean_text)

    # Anti-cheat: forbid shortcuts that "typecheck" without actually proving.
    #
    # Notes:
    # - This is intentionally conservative. If you truly need axioms, you can still
    #   document them in the Assumption Ledger (Ai) and keep Lean steps honest.
    # - We strip comments before scanning for `sorry`/`admit` to avoid false positives
    #   in step-map comments or explanatory text.
    if FORBIDDEN_DECL_RE.search(lean_text):
        issues.append(
            LintIssue(
                "FORBIDDEN_DECL",
                "Found forbidden declaration keyword (axiom/constant/opaque). Do not bypass the Lean gate with axioms; add explicit assumptions in markdown instead.",
            )
        )

    no_comments = re.sub(r"/-.*?-/", "", lean_text, flags=re.S)
    no_comments = re.sub(r"(?m)--.*$", "", no_comments)
    if re.search(r"(?<![A-Za-z0-9_])sorry(?![A-Za-z0-9_])", no_comments):
        issues.append(LintIssue("FORBIDDEN_SORRY", "Found 'sorry' in Lean file. Replace it with a real proof or downgrade the related claim/step."))
    if re.search(r"(?<![A-Za-z0-9_])admit(?![A-Za-z0-9_])", no_comments):
        issues.append(LintIssue("FORBIDDEN_ADMIT", "Found 'admit' in Lean file. Replace it with a real proof or downgrade the related claim/step."))

    if require_mathlib:
        # Enforce a semantic model that cannot be faked by redefining core objects as stubs.
        # This is a hardening mode: prefer a Lake project + Mathlib imports.
        if not IMPORT_MATHLIB_RE.search(no_comments):
            issues.append(
                LintIssue(
                    "MATHLIB_REQUIRED",
                    "Mathlib is required in strict mode. Add `import Mathlib` (or `import Mathlib.<...>`) at top of the Lean file.",
                )
            )
        if USER_MATRIX_DEF_RE.search(no_comments):
            issues.append(
                LintIssue(
                    "FORBIDDEN_LOCAL_MATRIX_DEF",
                    "Do not define your own `Matrix` in strict mode. Use Mathlib's `Matrix` to avoid semantic stubs.",
                )
            )
        if re.search(r"(?i)placeholder", lean_text):
            issues.append(
                LintIssue(
                    "FORBIDDEN_PLACEHOLDER_MARKER",
                    "Found 'placeholder' marker text. In strict mode, remove placeholders and make the model explicit (Mathlib + real definitions).",
                )
            )
        # NOTE(MathProve): do not require a Lake project "alongside" the Lean file.
        # The gate may compile this file using a separate Lake project dir (ProjectDir).

    if len(lean_steps) < min_steps:
        issues.append(
            LintIssue(
                "LEAN_STEPS_TOO_FEW",
                f"Only {len(lean_steps)} Lean step theorem(s)/lemma(s) found (Sx). Require >= {min_steps}.",
            )
        )

    if require_step_map:
        if "RIGOR_STEP_MAP" not in lean_text:
            issues.append(LintIssue("MISSING_STEP_MAP_HEADER", "Missing '-- RIGOR_STEP_MAP' header in Lean file."))
        if len(step_map) < min_steps:
            issues.append(
                LintIssue(
                    "STEP_MAP_TOO_FEW",
                    f"Only {len(step_map)} step-map line(s) found ('-- Sx: ...'). Require >= {min_steps}.",
                )
            )

    # Optional structural hardening: require local domain vocabulary.
    if require_domain_defs:
        if not decls:
            issues.append(
                LintIssue(
                    "MISSING_DOMAIN_DEFS",
                    "No Lean definitions found (def/structure/inductive/abbrev). Add minimal domain definitions and then prove steps against them.",
                )
            )
        else:
            # Heuristic anti-cheat: each Sx declaration line should mention at least one
            # domain identifier defined in this file. This discourages "unrelated Nat lemmas".
            domain_names = {name for _, name in decls}
            if require_mathlib:
                # Allow a small set of Mathlib domain anchors (semantic objects) so steps
                # can legitimately talk about imported structures (e.g., Matrix) without
                # forcing artificial local wrappers.
                domain_names |= {"Matrix"}
            for step, header in _extract_step_header_chunks(lean_text):
                if not any(
                    re.search(rf"(?<![A-Za-z0-9_']){re.escape(n)}(?![A-Za-z0-9_'])", header) for n in domain_names
                ):
                    issues.append(
                        LintIssue(
                            "STEP_DOES_NOT_REFERENCE_DOMAIN",
                            f"S{step} declaration does not reference any domain definition from this file. Keep steps small and about your domain, not unrelated lemmas.",
                        )
                    )

    if md_text is not None:
        md_steps = _extract_md_steps(md_text)
        if md_steps:
            missing_steps = _missing(md_steps, lean_steps)
            if missing_steps:
                issues.append(
                    LintIssue(
                        "LEAN_MISSING_STEPS_FOR_MD",
                        f"Lean file is missing step(s) required by markdown: {', '.join('S'+str(n) for n in missing_steps)}.",
                    )
                )
            if require_step_map:
                missing_map = _missing(md_steps, step_map)
                if missing_map:
                    issues.append(
                        LintIssue(
                            "STEP_MAP_MISSING_FOR_MD",
                            f"Step-map is missing step(s) required by markdown: {', '.join('S'+str(n) for n in missing_map)}.",
                        )
                    )

    return issues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lean", required=True, help="Path to rigorous_reverse.lean")
    ap.add_argument("--markdown", required=False, help="Optional path to rigorous_content.md for step coverage checks")
    ap.add_argument("--min-steps", type=int, default=1, help="Minimum number of Sx steps required in Lean")
    ap.add_argument("--require-step-map", action="store_true", help="Require '-- RIGOR_STEP_MAP' + '-- Sx: ...' lines")
    ap.add_argument("--require-mathlib", action="store_true", help="Strict semantic mode: require Lake project + Mathlib; forbid local Matrix stubs.")
    ap.add_argument("--require-domain-defs", action="store_true", help="Optional hardening: require local domain definitions and step/domain linkage")
    args = ap.parse_args()

    lean_path = Path(args.lean)
    if not lean_path.exists():
        print(f"Lean file not found: {lean_path}", file=sys.stderr)
        return 2

    md_text = None
    if args.markdown:
        md_path = Path(args.markdown)
        if not md_path.exists():
            print(f"Markdown file not found: {md_path}", file=sys.stderr)
            return 2
        md_text = _read_text(md_path)

    lean_text = _read_text(lean_path)
    issues = lint(
        lean_text=lean_text,
        md_text=md_text,
        min_steps=args.min_steps,
        require_step_map=args.require_step_map,
        require_mathlib=args.require_mathlib,
        require_domain_defs=args.require_domain_defs,
        lean_path=lean_path,
    )
    if issues:
        print("Lean4 reverse-audit lint failed:", file=sys.stderr)
        for it in issues:
            print(f"[{it.code}] {it.message}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
