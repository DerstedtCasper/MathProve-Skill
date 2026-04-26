"""MathProve Ultra v8 proof-factory primitives.

Stdlib-only protocol utilities for long-horizon formal proof campaigns:

* stage gates and hard vetoes;
* evidence-weighted candidate selection;
* 1M+ effective context through context-lake shards;
* proof-memory graph events;
* high-budget anti-premature-closure contract;
* static Lean safety audit that permits `sorry` only in skeleton stage.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable


class Stage(str, Enum):
    PROBLEM_LOCK = "problem_lock"
    KNOWLEDGE_PACK = "knowledge_pack"
    NOTATION = "notation"
    SKELETON = "skeleton"
    LINE_MAP = "line_map"
    LEMMA_SPRINT = "lemma_sprint"
    REFUTATION = "refutation"
    INTEGRATION = "integration"
    FINAL_AUDIT = "final_audit"
    MEMORY_UPDATE = "memory_update"


STAGE_ORDER: tuple[Stage, ...] = tuple(Stage)


class AgentRole(str, Enum):
    FORMALIZER = "formalizer"
    SKELETONIST = "skeletonist"
    LINE_MAPPER = "line_mapper"
    TACTIC_SPRINTER = "tactic_sprinter"
    WHOLE_PROOF_PROPOSER = "whole_proof_proposer"
    LIBRARIAN = "librarian"
    ALGEBRAIC_VERIFIER = "algebraic_verifier"
    REFUTER = "refuter"
    REPAIRER = "repairer"
    INTEGRATOR = "integrator"
    AUDITOR = "auditor"
    DOMAIN_EXPERT = "domain_expert"


@dataclass(frozen=True)
class StageSpec:
    stage: Stage
    objective: str
    required_inputs: tuple[str, ...]
    required_outputs: tuple[str, ...]
    allowed_roles: tuple[AgentRole, ...]
    hard_vetoes: tuple[str, ...]
    minimum_quota: dict[str, int] = field(default_factory=dict)
    allow_sorry: bool = False


@dataclass
class CandidateEvidence:
    candidate_id: str
    stage: Stage | str
    role: AgentRole | str
    claim: str = ""
    artifact_paths: list[str] = field(default_factory=list)
    tool_logs: list[str] = field(default_factory=list)
    lean_passed: bool = False
    sympy_passed: bool = False
    no_sorry: bool = False
    dependency_closure: float = 0.0
    refutation_coverage: float = 0.0
    evidence_coverage: float = 0.0
    maintainability: float = 0.0
    restartability: float = 0.0
    novelty: float = 0.0
    cost_sanity: float = 1.0
    theorem_statement_hash: str = ""
    expected_statement_hash: str = ""
    quota_observations: dict[str, int] = field(default_factory=dict)
    veto_reasons: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class ScoreWeights:
    tool_verification: float = 0.35
    dependency_closure: float = 0.18
    refutation_coverage: float = 0.14
    evidence_completeness: float = 0.12
    maintainability: float = 0.09
    restartability: float = 0.07
    novelty: float = 0.03
    cost_sanity: float = 0.02


@dataclass
class CandidateScore:
    candidate_id: str
    stage: str
    total: float
    components: dict[str, float]
    veto_reasons: list[str] = field(default_factory=list)


@dataclass
class GateDecision:
    stage: str
    selected_candidate_id: str | None
    accepted: bool
    scores: list[CandidateScore]
    reason: str
    next_stage: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["scores"] = [asdict(score) for score in self.scores]
        return data


@dataclass
class ContextShard:
    shard_id: str
    stage: str
    kind: str
    path: str
    summary: str
    token_estimate: int
    depends_on: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ProofMemoryEvent:
    event_type: str
    subject: str
    relation: str
    payload: dict[str, Any]
    stage: str
    source: str
    confidence: float = 1.0
    replaces: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_id: str = ""

    def finalized(self) -> "ProofMemoryEvent":
        if not self.event_id:
            canonical = json.dumps(
                {
                    "event_type": self.event_type,
                    "subject": self.subject,
                    "relation": self.relation,
                    "payload": self.payload,
                    "stage": self.stage,
                    "source": self.source,
                    "created_at": self.created_at,
                },
                sort_keys=True,
                ensure_ascii=False,
            )
            self.event_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
        return self


@dataclass
class BudgetContract:
    mode: str = "frontier"
    local_context_target_tokens: int = 1_000_000
    global_campaign_target_tokens: int = 20_000_000
    minimum_wall_clock_hours: int = 24
    default_parallel_branches: int = 8
    max_parallel_branches: int = 64
    require_context_lake: bool = True
    require_refutation_gate: bool = True
    anti_laziness_rule: str = "externalize-and-continue"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["termination_allowed_only_if"] = [
            "final_audit_approved",
            "formal_counterexample_found",
            "theorem_statement_repaired_and_user_visible",
            "environment_blocker_with_replay_log",
        ]
        return data


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def clamp01(value: float) -> float:
    try:
        v = float(value)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, v))


def next_stage(stage: Stage | str) -> Stage | None:
    st = Stage(stage)
    idx = STAGE_ORDER.index(st)
    if idx + 1 >= len(STAGE_ORDER):
        return None
    return STAGE_ORDER[idx + 1]


def stage_specs() -> dict[Stage, StageSpec]:
    all_roles = tuple(AgentRole)
    return {
        Stage.PROBLEM_LOCK: StageSpec(Stage.PROBLEM_LOCK, "Lock theorem variants, domain, and budget.", ("problem.md",), ("problem_lock.md", "assumptions.md"), all_roles, ("ambiguous goal", "missing domain"), {"theorem_variants": 1}),
        Stage.KNOWLEDGE_PACK: StageSpec(Stage.KNOWLEDGE_PACK, "Retrieve prior memory, Mathlib candidates, and source references.", ("problem_lock.md",), ("knowledge_pack.md", "library_search.jsonl"), (AgentRole.LIBRARIAN, AgentRole.DOMAIN_EXPERT, AgentRole.FORMALIZER, AgentRole.AUDITOR), ("unverified lemma as fact",), {"library_search_passes": 1}),
        Stage.NOTATION: StageSpec(Stage.NOTATION, "Freeze symbols, types, coercions, indices, and theorem signature.", ("knowledge_pack.md",), ("notation_ledger.md", "namespace_plan.md"), (AgentRole.FORMALIZER, AgentRole.REFUTER, AgentRole.AUDITOR), ("undefined symbol", "domain drift"), {"notation_entries": 1}),
        Stage.SKELETON: StageSpec(Stage.SKELETON, "Create Lean skeleton and dependency DAG.", ("notation_ledger.md",), ("Skeleton.lean", "lemma_dag.json"), (AgentRole.SKELETONIST, AgentRole.LIBRARIAN, AgentRole.AUDITOR), ("statement drift", "cyclic dependency"), {"skeleton_decompositions": 1}, allow_sorry=True),
        Stage.LINE_MAP: StageSpec(Stage.LINE_MAP, "Map informal proof lines to formal obligations.", ("Skeleton.lean",), ("line_map.json", "obligation_table.md"), (AgentRole.LINE_MAPPER, AgentRole.FORMALIZER, AgentRole.REFUTER, AgentRole.AUDITOR), ("unmapped line", "hidden leap"), {"mapped_lines": 1}),
        Stage.LEMMA_SPRINT: StageSpec(Stage.LEMMA_SPRINT, "Prove leaf lemmas with parallel branch candidates.", ("line_map.json",), ("lemma_results.jsonl", "proof_patches/"), (AgentRole.TACTIC_SPRINTER, AgentRole.REPAIRER, AgentRole.LIBRARIAN, AgentRole.ALGEBRAIC_VERIFIER, AgentRole.REFUTER, AgentRole.AUDITOR), ("unverified proof", "new axiom", "non-skeleton sorry"), {"candidate_packs": 1}),
        Stage.REFUTATION: StageSpec(Stage.REFUTATION, "Attack quantifiers, boundary cases, and theorem drift.", ("lemma_results.jsonl",), ("red_team_report.md", "counterexample_log.jsonl"), (AgentRole.REFUTER, AgentRole.ALGEBRAIC_VERIFIER, AgentRole.DOMAIN_EXPERT, AgentRole.AUDITOR), ("unresolved counterexample",), {"red_team_passes": 1}),
        Stage.INTEGRATION: StageSpec(Stage.INTEGRATION, "Merge patches, replay, and refactor maintainably.", ("proof_patches/", "red_team_report.md"), ("Integrated.lean", "refactor_report.md"), (AgentRole.INTEGRATOR, AgentRole.LIBRARIAN, AgentRole.AUDITOR), ("broken dependency", "non-replayable patch"), {"replay_attempts": 1}),
        Stage.FINAL_AUDIT: StageSpec(Stage.FINAL_AUDIT, "Replay final proof and publish only if evidence coverage is complete.", ("Integrated.lean",), ("audit.json", "Solution.md"), (AgentRole.AUDITOR,), ("sorry", "admit", "unsafe", "axiom", "failed replay"), {"audit_passes": 1}),
        Stage.MEMORY_UPDATE: StageSpec(Stage.MEMORY_UPDATE, "Write proof-memory graph events.", ("audit.json",), ("memory/events.jsonl",), (AgentRole.AUDITOR, AgentRole.INTEGRATOR), ("unindexed memory",), {"memory_events": 1}),
    }


def evidence_completeness(candidate: CandidateEvidence) -> float:
    pieces = 0
    pieces += 1 if candidate.artifact_paths else 0
    pieces += 1 if candidate.tool_logs else 0
    pieces += 1 if candidate.claim.strip() else 0
    pieces += 1 if candidate.evidence_coverage > 0 else 0
    return pieces / 4.0


def quota_vetoes(candidate: CandidateEvidence, frontier: bool = False) -> list[str]:
    spec = stage_specs()[Stage(candidate.stage)]
    reasons: list[str] = []
    if not frontier:
        return reasons
    for name, minimum in spec.minimum_quota.items():
        observed = int(candidate.quota_observations.get(name, 0))
        if observed < minimum:
            reasons.append(f"quota_not_met:{name}:{observed}<{minimum}")
    return reasons


def candidate_hard_vetoes(candidate: CandidateEvidence, frontier: bool = False) -> list[str]:
    stage = Stage(candidate.stage)
    spec = stage_specs()[stage]
    reasons = list(candidate.veto_reasons)
    if stage != Stage.SKELETON and not candidate.no_sorry:
        reasons.append("non-skeleton candidate is not marked no_sorry")
    if stage in {Stage.LEMMA_SPRINT, Stage.INTEGRATION, Stage.FINAL_AUDIT} and not candidate.lean_passed:
        reasons.append("Lean verification is required at this stage")
    if not candidate.artifact_paths:
        reasons.append("missing durable artifact path")
    if not candidate.tool_logs and stage in {Stage.LEMMA_SPRINT, Stage.INTEGRATION, Stage.FINAL_AUDIT}:
        reasons.append("missing tool log")
    if candidate.expected_statement_hash and candidate.theorem_statement_hash and candidate.expected_statement_hash != candidate.theorem_statement_hash:
        reasons.append("theorem statement drift")
    if "undefined symbol" in spec.hard_vetoes and "undefined_symbol" in candidate.notes:
        reasons.append("undefined symbol risk")
    reasons.extend(quota_vetoes(candidate, frontier=frontier))
    return sorted(set(reasons))


def score_candidate(candidate: CandidateEvidence, weights: ScoreWeights | None = None, frontier: bool = False) -> CandidateScore:
    weights = weights or ScoreWeights()
    stage = Stage(candidate.stage)
    tool = 0.0
    if candidate.lean_passed:
        tool += 0.80
    if candidate.sympy_passed:
        tool += 0.20
    if stage in {Stage.PROBLEM_LOCK, Stage.KNOWLEDGE_PACK, Stage.NOTATION, Stage.SKELETON, Stage.LINE_MAP, Stage.REFUTATION, Stage.MEMORY_UPDATE} and candidate.artifact_paths:
        tool = max(tool, 0.35)
    components = {
        "tool_verification": clamp01(tool),
        "dependency_closure": clamp01(candidate.dependency_closure),
        "refutation_coverage": clamp01(candidate.refutation_coverage),
        "evidence_completeness": max(evidence_completeness(candidate), clamp01(candidate.evidence_coverage)),
        "maintainability": clamp01(candidate.maintainability),
        "restartability": clamp01(candidate.restartability),
        "novelty": clamp01(candidate.novelty),
        "cost_sanity": clamp01(candidate.cost_sanity),
    }
    total = sum(
        components[name] * getattr(weights, name)
        for name in components
    )
    vetoes = candidate_hard_vetoes(candidate, frontier=frontier)
    if vetoes:
        total = 0.0
    return CandidateScore(candidate.candidate_id, stage.value, round(total, 6), components, vetoes)


def select_candidate(candidates: Iterable[CandidateEvidence], threshold: float = 0.72, frontier: bool = False) -> GateDecision:
    items = list(candidates)
    if not items:
        return GateDecision("unknown", None, False, [], "no candidates")
    stage = Stage(items[0].stage)
    scores = [score_candidate(item, frontier=frontier) for item in items]
    eligible = [score for score in scores if not score.veto_reasons]
    if not eligible:
        return GateDecision(stage.value, None, False, scores, "all candidates vetoed", None)
    best = max(eligible, key=lambda score: score.total)
    accepted = best.total >= threshold
    nxt = next_stage(stage)
    return GateDecision(stage.value, best.candidate_id if accepted else None, accepted, scores, "accepted by evidence-weighted gate" if accepted else f"best score {best.total} below threshold {threshold}", nxt.value if accepted and nxt else None)


def write_json(path: str | Path, data: Any) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return p


def append_jsonl(path: str | Path, record: dict[str, Any]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return p


def write_context_shard(context_dir: str | Path, stage: Stage | str, kind: str, content: str, summary: str, depends_on: list[str] | None = None) -> ContextShard:
    context_dir = Path(context_dir)
    stage_value = Stage(stage).value
    shard_id = f"{stage_value}-{stable_hash(kind + summary + content)}"
    shard_path = context_dir / "shards" / f"{shard_id}.md"
    shard_path.parent.mkdir(parents=True, exist_ok=True)
    shard_path.write_text(content, encoding="utf-8")
    shard = ContextShard(shard_id, stage_value, kind, str(shard_path), summary, max(1, len(content) // 4), depends_on or [])
    index_path = context_dir / "index.json"
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
    else:
        index = {"shards": []}
    index["shards"] = [x for x in index.get("shards", []) if x.get("shard_id") != shard_id]
    index["shards"].append(asdict(shard))
    write_json(index_path, index)
    return shard


def write_handoff_capsule(context_dir: str | Path, stage: Stage | str, capsule: dict[str, Any]) -> Path:
    context_dir = Path(context_dir)
    stage_value = Stage(stage).value
    path = context_dir / "handoff_capsules" / f"{stage_value}-{stable_hash(json.dumps(capsule, sort_keys=True, ensure_ascii=False))}.json"
    return write_json(path, capsule)


def write_memory_event(memory_dir: str | Path, event: ProofMemoryEvent) -> Path:
    event.finalized()
    memory_dir = Path(memory_dir)
    record = asdict(event)
    append_jsonl(memory_dir / "events.jsonl", record)
    write_json(memory_dir / "by_id" / f"{event.event_id}.json", record)
    return memory_dir / "events.jsonl"


def load_memory_events(memory_dir: str | Path, subject: str | None = None, relation: str | None = None) -> list[ProofMemoryEvent]:
    path = Path(memory_dir) / "events.jsonl"
    if not path.exists():
        return []
    events: list[ProofMemoryEvent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        if subject is not None and data.get("subject") != subject:
            continue
        if relation is not None and data.get("relation") != relation:
            continue
        events.append(ProofMemoryEvent(**data))
    return events


_FORBIDDEN_FINAL = re.compile(r"(?<![A-Za-z0-9_])(sorry|admit|unsafe|axiom|constant|opaque)(?![A-Za-z0-9_])")
_LINE_COMMENT = re.compile(r"(?m)--.*$")
_BLOCK_COMMENT = re.compile(r"/-.*?-/", re.S)


def strip_lean_comments(text: str) -> str:
    return _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", text))


def lean_static_audit(lean_source: str, stage: Stage | str = Stage.FINAL_AUDIT) -> tuple[bool, list[str]]:
    stage_value = Stage(stage)
    cleaned = strip_lean_comments(lean_source)
    violations = sorted(set(match.group(1) for match in _FORBIDDEN_FINAL.finditer(cleaned)))
    if stage_value == Stage.SKELETON:
        violations = [v for v in violations if v != "sorry"]
    return (not violations, violations)


def validate_line_map(items: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    seen: set[str] = set()
    for idx, item in enumerate(items):
        line_id = str(item.get("line_id") or "").strip()
        formal_target = str(item.get("formal_target") or "").strip()
        obligation = str(item.get("obligation") or "").strip()
        deps = item.get("depends_on") or []
        if not line_id:
            errors.append(f"item {idx}: missing line_id")
        if line_id in seen:
            errors.append(f"item {idx}: duplicate line_id {line_id}")
        seen.add(line_id)
        if not formal_target:
            errors.append(f"{line_id}: missing formal_target")
        if not obligation:
            errors.append(f"{line_id}: missing obligation")
        for dep in deps:
            if str(dep) == line_id:
                errors.append(f"{line_id}: self dependency")
    return (not errors, errors)


def make_budget_contract(mode: str = "frontier") -> BudgetContract:
    if mode in {"frontier", "research", "hard"}:
        return BudgetContract(mode="frontier")
    return BudgetContract(mode="normal", local_context_target_tokens=200_000, global_campaign_target_tokens=1_000_000, minimum_wall_clock_hours=1, default_parallel_branches=3, max_parallel_branches=8)


def termination_allowed(status: dict[str, Any]) -> tuple[bool, str]:
    flags = {
        "final_audit_approved": bool(status.get("final_audit_approved")),
        "formal_counterexample_found": bool(status.get("formal_counterexample_found")),
        "theorem_statement_repaired_and_user_visible": bool(status.get("theorem_statement_repaired_and_user_visible")),
        "environment_blocker_with_replay_log": bool(status.get("environment_blocker_with_replay_log")),
    }
    for key, value in flags.items():
        if value:
            return True, key
    return False, "no valid termination condition"


def demo_decision(frontier: bool = True) -> GateDecision:
    expected = stable_hash("theorem target")
    candidates = [
        CandidateEvidence("pretty_but_unverified", Stage.LEMMA_SPRINT, AgentRole.WHOLE_PROOF_PROPOSER, claim="Elegant proof sketch", artifact_paths=["draft.md"], no_sorry=True, evidence_coverage=0.25, maintainability=0.9, restartability=0.6, novelty=0.8, expected_statement_hash=expected, theorem_statement_hash=expected, quota_observations={"candidate_packs": 1}),
        CandidateEvidence("compiled_patch", Stage.LEMMA_SPRINT, AgentRole.TACTIC_SPRINTER, claim="Lean patch", artifact_paths=["patch.lean"], tool_logs=["lean.log"], lean_passed=True, no_sorry=True, dependency_closure=0.9, refutation_coverage=0.65, evidence_coverage=1.0, maintainability=0.78, restartability=0.85, novelty=0.25, expected_statement_hash=expected, theorem_statement_hash=expected, quota_observations={"candidate_packs": 1}),
        CandidateEvidence("fast_sorry", Stage.LEMMA_SPRINT, AgentRole.REPAIRER, claim="Uses sorry", artifact_paths=["bad.lean"], tool_logs=["lean.log"], lean_passed=True, no_sorry=False, dependency_closure=1.0, evidence_coverage=1.0, expected_statement_hash=expected, theorem_statement_hash=expected, quota_observations={"candidate_packs": 1}),
    ]
    return select_candidate(candidates, threshold=0.72, frontier=frontier)
