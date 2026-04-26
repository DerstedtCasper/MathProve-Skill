"""High-budget proof factory primitives for MathProve v7.

This module is deliberately stdlib-only.  It does not prove theorems by
itself; instead it gives the orchestrator a durable protocol for long-running,
multi-agent formalization campaigns:

* stage gates instead of one monolithic STEP_LOOP;
* evidence-weighted candidate selection instead of first-winner racing;
* proof-memory events for 1M+ context handoff across agents;
* checkpoint/resume records for 24h+ theorem-proving runs;
* static Lean safety checks that distinguish skeleton `sorry` from final `sorry`.
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
    INTAKE = "intake"
    NOTATION = "notation"
    BLUEPRINT = "blueprint"
    SKELETON = "skeleton"
    LINE_MAP = "line_map"
    LEMMA_SPRINT = "lemma_sprint"
    REFUTATION = "refutation"
    INTEGRATION = "integration"
    FINAL_AUDIT = "final_audit"


STAGE_ORDER: tuple[Stage, ...] = (
    Stage.INTAKE,
    Stage.NOTATION,
    Stage.BLUEPRINT,
    Stage.SKELETON,
    Stage.LINE_MAP,
    Stage.LEMMA_SPRINT,
    Stage.REFUTATION,
    Stage.INTEGRATION,
    Stage.FINAL_AUDIT,
)


class AgentRole(str, Enum):
    FORMALIZER = "formalizer"
    SKELETONIST = "skeletonist"
    LINE_MAPPER = "line_mapper"
    TACTIC_SPRINTER = "tactic_sprinter"
    REFUTER = "refuter"
    LIBRARIAN = "librarian"
    REPAIRER = "repairer"
    AUDITOR = "auditor"


@dataclass(frozen=True)
class StageSpec:
    stage: Stage
    objective: str
    required_inputs: tuple[str, ...]
    required_outputs: tuple[str, ...]
    allowed_roles: tuple[AgentRole, ...]
    hard_vetoes: tuple[str, ...]
    allow_sorry: bool = False


@dataclass
class CandidateEvidence:
    candidate_id: str
    stage: Stage
    role: AgentRole | str
    claim: str = ""
    artifact_paths: list[str] = field(default_factory=list)
    tool_logs: list[str] = field(default_factory=list)
    lean_passed: bool = False
    sympy_passed: bool = False
    no_sorry: bool = False
    dependency_closure: float = 0.0
    refutation_coverage: float = 0.0
    maintainability: float = 0.0
    restartability: float = 0.0
    novelty: float = 0.0
    cost_score: float = 1.0
    veto_reasons: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class ScoreWeights:
    tool_verification: float = 0.30
    dependency_closure: float = 0.18
    refutation_coverage: float = 0.18
    evidence_completeness: float = 0.12
    maintainability: float = 0.10
    restartability: float = 0.07
    novelty: float = 0.03
    cost_score: float = 0.02


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
        d = asdict(self)
        d["scores"] = [asdict(s) for s in self.scores]
        return d


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
            canonical = json.dumps({
                "event_type": self.event_type,
                "subject": self.subject,
                "relation": self.relation,
                "payload": self.payload,
                "stage": self.stage,
                "source": self.source,
                "created_at": self.created_at,
            }, sort_keys=True, ensure_ascii=False)
            self.event_id = hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]
        return self


@dataclass
class ProofFactoryState:
    run_id: str
    stage: Stage = Stage.INTAKE
    problem_hash: str = ""
    status: str = "running"
    current_goal: str = ""
    accepted_decisions: list[dict[str, Any]] = field(default_factory=list)
    memory_index_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["stage"] = self.stage.value
        return d


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


def clamp01(x: float) -> float:
    try:
        y = float(x)
    except Exception:
        return 0.0
    if y < 0:
        return 0.0
    if y > 1:
        return 1.0
    return y


def stage_specs() -> dict[Stage, StageSpec]:
    all_roles = tuple(AgentRole)
    return {
        Stage.INTAKE: StageSpec(Stage.INTAKE, "Lock theorem, domain, target formal system, and run budget.", ("problem.md",), ("problem_lock.md", "assumption_ledger.md"), all_roles, ("ambiguous goal", "missing domain")),
        Stage.NOTATION: StageSpec(Stage.NOTATION, "Create a stable symbol/type/namespace table before proof search.", ("problem_lock.md",), ("notation_table.md", "namespace_plan.md"), (AgentRole.FORMALIZER, AgentRole.LIBRARIAN, AgentRole.AUDITOR), ("undefined symbol", "overloaded notation")),
        Stage.BLUEPRINT: StageSpec(Stage.BLUEPRINT, "Produce dependency DAG and proof obligations without filling low-level tactics.", ("notation_table.md",), ("blueprint.md", "dependency_graph.json"), (AgentRole.FORMALIZER, AgentRole.SKELETONIST, AgentRole.REFUTER, AgentRole.AUDITOR), ("cyclic dependency", "unmotivated lemma")),
        Stage.SKELETON: StageSpec(Stage.SKELETON, "Create Lean declarations and lemma statements; sorry is allowed only here.", ("blueprint.md",), ("Skeleton.lean", "skeleton_report.md"), (AgentRole.SKELETONIST, AgentRole.LIBRARIAN, AgentRole.AUDITOR), ("statement drift", "missing import"), allow_sorry=True),
        Stage.LINE_MAP: StageSpec(Stage.LINE_MAP, "Map each informal proof line to a Lean declaration or proof obligation.", ("Skeleton.lean",), ("line_map.json", "obligation_table.md"), (AgentRole.LINE_MAPPER, AgentRole.FORMALIZER, AgentRole.AUDITOR), ("unmapped line", "many-to-one hidden leap")),
        Stage.LEMMA_SPRINT: StageSpec(Stage.LEMMA_SPRINT, "Run parallel lemma proof attempts under isolated Lean workspaces.", ("line_map.json",), ("lemma_results.jsonl", "proof_patches/"), (AgentRole.TACTIC_SPRINTER, AgentRole.REPAIRER, AgentRole.LIBRARIAN, AgentRole.AUDITOR), ("unverified proof", "new axiom", "non-skeleton sorry")),
        Stage.REFUTATION: StageSpec(Stage.REFUTATION, "Attack definitions, quantifiers, edge cases, and equivalence direction.", ("lemma_results.jsonl",), ("red_team_report.md", "counterexample_log.jsonl"), (AgentRole.REFUTER, AgentRole.AUDITOR, AgentRole.FORMALIZER), ("unresolved counterexample", "weakened theorem not recorded")),
        Stage.INTEGRATION: StageSpec(Stage.INTEGRATION, "Merge proofs, minimize imports, refactor names, and maintain replayability.", ("proof_patches/", "red_team_report.md"), ("Integrated.lean", "refactor_report.md"), (AgentRole.REPAIRER, AgentRole.LIBRARIAN, AgentRole.AUDITOR), ("broken dependency", "non-replayable patch")),
        Stage.FINAL_AUDIT: StageSpec(Stage.FINAL_AUDIT, "Replay, print axioms, scan forbidden tokens, and publish final solution only on approval.", ("Integrated.lean",), ("audit.json", "Solution.md"), (AgentRole.AUDITOR,), ("sorry", "admit", "unsafe", "new axiom", "failed replay")),
    }


def next_stage(stage: Stage | str) -> Stage | None:
    st = Stage(stage)
    i = STAGE_ORDER.index(st)
    if i + 1 >= len(STAGE_ORDER):
        return None
    return STAGE_ORDER[i + 1]


def evidence_completeness(c: CandidateEvidence) -> float:
    pieces = 0
    pieces += 1 if c.artifact_paths else 0
    pieces += 1 if c.tool_logs else 0
    pieces += 1 if c.claim.strip() else 0
    return pieces / 3.0


def candidate_hard_vetoes(c: CandidateEvidence) -> list[str]:
    reasons = list(c.veto_reasons)
    spec = stage_specs()[Stage(c.stage)]
    if c.stage != Stage.SKELETON and not c.no_sorry:
        reasons.append("non-skeleton candidate is not marked no_sorry")
    if c.stage in {Stage.LEMMA_SPRINT, Stage.INTEGRATION, Stage.FINAL_AUDIT} and not c.lean_passed:
        reasons.append("Lean verification is required at this stage")
    if not c.artifact_paths:
        reasons.append("missing durable artifact path")
    if not c.tool_logs and c.stage in {Stage.LEMMA_SPRINT, Stage.INTEGRATION, Stage.FINAL_AUDIT}:
        reasons.append("missing tool log")
    if "undefined symbol" in spec.hard_vetoes and "undefined_symbol" in c.notes:
        reasons.append("undefined symbol risk")
    return sorted(set(reasons))


def score_candidate(c: CandidateEvidence, weights: ScoreWeights | None = None) -> CandidateScore:
    w = weights or ScoreWeights()
    tool = 0.0
    if c.lean_passed:
        tool += 0.75
    if c.sympy_passed:
        tool += 0.25
    if c.stage in {Stage.NOTATION, Stage.BLUEPRINT, Stage.LINE_MAP, Stage.REFUTATION} and c.artifact_paths:
        tool = max(tool, 0.35)
    components = {
        "tool_verification": clamp01(tool),
        "dependency_closure": clamp01(c.dependency_closure),
        "refutation_coverage": clamp01(c.refutation_coverage),
        "evidence_completeness": evidence_completeness(c),
        "maintainability": clamp01(c.maintainability),
        "restartability": clamp01(c.restartability),
        "novelty": clamp01(c.novelty),
        "cost_score": clamp01(c.cost_score),
    }
    total = (
        components["tool_verification"] * w.tool_verification
        + components["dependency_closure"] * w.dependency_closure
        + components["refutation_coverage"] * w.refutation_coverage
        + components["evidence_completeness"] * w.evidence_completeness
        + components["maintainability"] * w.maintainability
        + components["restartability"] * w.restartability
        + components["novelty"] * w.novelty
        + components["cost_score"] * w.cost_score
    )
    vetoes = candidate_hard_vetoes(c)
    if vetoes:
        total = 0.0
    return CandidateScore(c.candidate_id, Stage(c.stage).value, round(total, 6), components, vetoes)


def select_candidate(candidates: Iterable[CandidateEvidence], threshold: float = 0.72) -> GateDecision:
    candidates = list(candidates)
    if not candidates:
        return GateDecision("unknown", None, False, [], "no candidates")
    stage = Stage(candidates[0].stage)
    scores = [score_candidate(c) for c in candidates]
    eligible = [s for s in scores if not s.veto_reasons]
    if not eligible:
        return GateDecision(stage.value, None, False, scores, "all candidates vetoed", None)
    best = max(eligible, key=lambda s: s.total)
    accepted = best.total >= threshold
    nxt = next_stage(stage)
    return GateDecision(
        stage=stage.value,
        selected_candidate_id=best.candidate_id if accepted else None,
        accepted=accepted,
        scores=scores,
        reason=("accepted by evidence-weighted gate" if accepted else f"best score {best.total} below threshold {threshold}"),
        next_stage=nxt.value if (accepted and nxt) else None,
    )


def write_json(path: str | Path, data: Any) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True), encoding='utf-8')
    return p


def append_jsonl(path: str | Path, record: dict[str, Any]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
    return p


def write_memory_event(memory_dir: str | Path, event: ProofMemoryEvent) -> Path:
    event.finalized()
    memory_dir = Path(memory_dir)
    record = asdict(event)
    append_jsonl(memory_dir / 'events.jsonl', record)
    write_json(memory_dir / 'by_id' / f'{event.event_id}.json', record)
    return memory_dir / 'events.jsonl'


def load_memory_events(memory_dir: str | Path, subject: str | None = None, relation: str | None = None) -> list[ProofMemoryEvent]:
    p = Path(memory_dir) / 'events.jsonl'
    events: list[ProofMemoryEvent] = []
    if not p.exists():
        return events
    for line in p.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        if subject is not None and data.get('subject') != subject:
            continue
        if relation is not None and data.get('relation') != relation:
            continue
        events.append(ProofMemoryEvent(**data))
    return events


def checkpoint(run_dir: str | Path, state: ProofFactoryState, payload: dict[str, Any] | None = None) -> Path:
    run_dir = Path(run_dir)
    data = {"state": state.to_dict(), "payload": payload or {}, "written_at": datetime.now(timezone.utc).isoformat()}
    write_json(run_dir / 'status.json', data)
    write_json(run_dir / 'checkpoints' / f'{state.stage.value}.json', data)
    return run_dir / 'status.json'


def load_checkpoint(run_dir: str | Path) -> dict[str, Any]:
    p = Path(run_dir) / 'status.json'
    if not p.exists():
        raise FileNotFoundError(p)
    return json.loads(p.read_text(encoding='utf-8'))


_FORBIDDEN_FINAL = re.compile(r"(?<![A-Za-z0-9_])(sorry|admit|unsafe|axiom|constant|opaque)(?![A-Za-z0-9_])")
_LINE_COMMENT = re.compile(r"(?m)--.*$")
_BLOCK_COMMENT = re.compile(r"/-.*?-/", re.S)


def strip_lean_comments(text: str) -> str:
    return _LINE_COMMENT.sub('', _BLOCK_COMMENT.sub('', text))


def lean_static_audit(lean_source: str, stage: Stage | str = Stage.FINAL_AUDIT) -> tuple[bool, list[str]]:
    st = Stage(stage)
    cleaned = strip_lean_comments(lean_source)
    violations = sorted(set(m.group(1) for m in _FORBIDDEN_FINAL.finditer(cleaned)))
    if st == Stage.SKELETON:
        violations = [v for v in violations if v not in {'sorry'}]
    return (len(violations) == 0, violations)


def validate_line_map(items: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for i, item in enumerate(items):
        line_id = str(item.get('line_id') or '').strip()
        formal_target = str(item.get('formal_target') or '').strip()
        obligation = str(item.get('obligation') or '').strip()
        deps = item.get('depends_on') or []
        if not line_id:
            errors.append(f'item {i}: missing line_id')
        if line_id in seen_ids:
            errors.append(f'item {i}: duplicate line_id {line_id}')
        seen_ids.add(line_id)
        if not formal_target:
            errors.append(f'{line_id}: missing formal_target')
        if not obligation:
            errors.append(f'{line_id}: missing obligation')
        for d in deps:
            if str(d) == line_id:
                errors.append(f'{line_id}: self dependency')
    return (len(errors) == 0, errors)


def budget_contract(unlimited: bool = True, wall_clock_hours: int = 24, context_target_tokens: int = 1_000_000) -> dict[str, Any]:
    """Return the high-budget contract used to discourage premature closure.

    `unlimited=True` does not mean infinite loops.  It means that the agent is
    not allowed to terminate merely because a local context is full or one proof
    branch failed; it must externalize state, split work, and resume.
    """
    return {
        "token_budget_policy": "externalize-and-continue" if unlimited else "bounded",
        "minimum_wall_clock_hours_for_hard_research": wall_clock_hours,
        "context_target_tokens_per_campaign": context_target_tokens,
        "termination_allowed_only_if": [
            "final_audit_approved",
            "formal_counterexample_found",
            "theorem_statement_repaired_and_user_visible",
            "environment_blocker_reported_with_replay_log",
        ],
        "anti_laziness_rule": "do not prefer short completion over verified progress",
    }


def demo_decision() -> GateDecision:
    candidates = [
        CandidateEvidence('pretty_but_unverified', Stage.LEMMA_SPRINT, AgentRole.TACTIC_SPRINTER, claim='Elegant proof sketch', artifact_paths=['draft.md'], no_sorry=True, maintainability=0.9, restartability=0.7, novelty=0.8),
        CandidateEvidence('compiled_patch', Stage.LEMMA_SPRINT, AgentRole.TACTIC_SPRINTER, claim='Lean patch', artifact_paths=['patch.lean'], tool_logs=['lean.log'], lean_passed=True, no_sorry=True, dependency_closure=0.9, refutation_coverage=0.6, maintainability=0.75, restartability=0.8, novelty=0.3),
        CandidateEvidence('fast_sorry', Stage.LEMMA_SPRINT, AgentRole.REPAIRER, claim='Uses sorry', artifact_paths=['bad.lean'], tool_logs=['lean.log'], lean_passed=True, no_sorry=False, dependency_closure=1.0),
    ]
    return select_candidate(candidates, threshold=0.70)
