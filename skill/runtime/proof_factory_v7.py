"""Stage-parallel candidate scoring and gate validation for MathProve v7."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
from typing import Iterable
HARD_FORBIDDEN = {"sorry","admit","unsafe","partial","sorryAx"}
@dataclass
class Candidate:
    stage: str
    branch_id: str
    claim: str
    tool_status: str = "unknown"
    dependencies_closed: bool = False
    hard_vetoes: list[str] = field(default_factory=list)
    artifact_paths: list[str] = field(default_factory=list)
    risks_covered: list[str] = field(default_factory=list)
    maintainability: int = 0
    evidence_complete: bool = False
    restartable: bool = False
@dataclass
class Decision:
    stage: str
    accepted: str | None
    rejected: list[str]
    scores: dict[str, int]
    reasons: dict[str, list[str]]
def scan_forbidden_text(text: str) -> list[str]:
    return sorted({t for t in HARD_FORBIDDEN if t in text})
def score_candidate(c: Candidate) -> tuple[int, list[str]]:
    if c.hard_vetoes: return -10000, [f"hard_veto:{v}" for v in c.hard_vetoes]
    score, reasons = 0, []
    if c.tool_status == "pass": score += 40; reasons.append("tool_certificate")
    elif c.tool_status == "fail": score -= 40; reasons.append("tool_failed")
    if c.dependencies_closed: score += 20; reasons.append("dependencies_closed")
    score += min(15, 5 * len(set(c.risks_covered)))
    score += max(0, min(10, c.maintainability))
    if c.evidence_complete: score += 10; reasons.append("evidence_complete")
    if c.restartable: score += 5; reasons.append("restartable")
    return score, reasons
def decide(stage: str, candidates: Iterable[Candidate]) -> Decision:
    scores, reasons, best, best_score = {}, {}, None, -10001
    for c in candidates:
        s, r = score_candidate(c); scores[c.branch_id] = s; reasons[c.branch_id] = r
        if s > best_score: best, best_score = c, s
    accepted = best.branch_id if best and best_score > 0 and not best.hard_vetoes else None
    return Decision(stage, accepted, [b for b in scores if b != accepted], scores, reasons)
def write_decision(path: str | Path, decision: Decision) -> None:
    Path(path).write_text(json.dumps(asdict(decision), indent=2, ensure_ascii=False), encoding="utf-8")
def validate_final_lean_text(text: str) -> tuple[bool, list[str]]:
    vetoes = [f"forbidden_token:{t}" for t in scan_forbidden_text(text)]
    if "theorem" in text and "by" not in text: vetoes.append("no_proof_body_detected")
    return not vetoes, vetoes
