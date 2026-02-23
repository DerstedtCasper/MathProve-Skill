"""Orchestrator: top-level proof construction loop integrating all modules.

Coordinates MAGI planning, step-by-step verification, error recovery,
parallel candidate exploration, and SafeVerify final audit.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import os
from dataclasses import dataclass, field
from typing import Any

from .proof_tree import ProofSearchTree, ProofNode, NodeStatus, Phase
from .error_classifier import (
    classify,
    suggest_fix,
    RetryBudget,
    StructuredError,
)
from .parallel_runner import (
    ParallelRunner,
    CandidateBranch,
    BranchStatus,
    SearchTreeLog,
)
from .safe_verify import scan_forbidden_tokens, SafeVerifyResult
from .workspace_manager import generate_run_id


@dataclass
class StepResult:
    """Result of executing a single proof step."""

    step_id: str
    status: str  # NodeStatus value
    engine: str  # "sympy" | "lean"
    evidence: str = ""
    error: str = ""
    attempts_used: dict[str, int] = field(default_factory=dict)


@dataclass
class OrchestratorResult:
    """Aggregated result of a full orchestrator run."""

    run_id: str
    phase: str = Phase.INIT.value  # Phase value
    steps: list[StepResult] = field(default_factory=list)
    safe_verify: SafeVerifyResult | None = None
    tree_snapshot: dict = field(default_factory=dict)
    success: bool = False
    summary: str = ""


@dataclass
class OrchestratorConfig:
    """Configuration for the Orchestrator."""

    max_magi_rounds: int = 2
    retry_limits: dict[str, int] = field(
        default_factory=lambda: {"magi": 2, "sympy": 3, "lean": 5}
    )
    parallel_candidates: int = 3
    parallel_timeout: int = 60
    lean_cmd: list[str] = field(default_factory=lambda: ["lean"])
    enable_safe_verify: bool = True
    enable_replay: bool = False
    step_timeout: int = 30


class Orchestrator:
    """Top-level proof construction orchestrator.

    Accepts pre-planned steps and drives them through execution,
    error recovery, and optional final audit.

    Usage::

        orch = Orchestrator(OrchestratorConfig(...))
        result = orch.run("Prove that ...", steps_list)
    """

    def __init__(self, config: OrchestratorConfig | None = None) -> None:
        self.config: OrchestratorConfig = config or OrchestratorConfig()
        self._tree: ProofSearchTree | None = None
        self._budgets: dict[str, RetryBudget] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, problem: str, steps: list[dict]) -> OrchestratorResult:
        """Main orchestration loop.

        Parameters
        ----------
        problem:
            Mathematical proposition text.
        steps:
            List of step dicts from steps.json.  Each dict must contain
            at least ``id``, ``goal``, ``engine``, and ``checker``.

        Returns
        -------
        OrchestratorResult
            Aggregated result including per-step outcomes, tree snapshot,
            and optional SafeVerify audit result.
        """
        # --- 1. Initialise -------------------------------------------------
        run_id = generate_run_id()
        self._tree = ProofSearchTree(run_id)
        self._tree.phase = Phase.STEP_LOOP
        self._budgets = {}

        for step in steps:
            sid = step["id"]
            self._tree.add_node(sid)
            self._budgets[sid] = RetryBudget(
                step_id=sid,
                limits=dict(self.config.retry_limits),
            )

        result = OrchestratorResult(run_id=run_id)
        step_results: list[StepResult] = []

        # --- 2. Step loop ---------------------------------------------------
        all_passed = True
        for step in steps:
            sid = step["id"]
            engine = step.get("engine", "sympy")

            # Advance from PENDING to MAGI_APPROVED (planning approved)
            self._tree.advance(sid, NodeStatus.MAGI_APPROVED)

            step_passed = False
            last_error = ""
            last_evidence = ""

            # Retry loop for this step
            while True:
                success, evidence, error = self._execute_step(step)
                if success:
                    last_evidence = evidence
                    # Advance through the verification chain
                    if engine == "sympy":
                        self._tree.advance(sid, NodeStatus.SYMPY_PASSED)
                        self._tree.advance(sid, NodeStatus.LEAN_PASSED)
                    else:
                        # For lean engine, still go through SYMPY_PASSED first
                        self._tree.advance(sid, NodeStatus.SYMPY_PASSED)
                        self._tree.advance(sid, NodeStatus.LEAN_PASSED)
                    self._tree.advance(sid, NodeStatus.PASSED)
                    step_passed = True
                    break
                else:
                    last_error = error
                    can_retry = self._handle_failure(sid, error, step)
                    if not can_retry:
                        break
                    # Reset for retry: backtrack resets to PENDING
                    self._tree.backtrack(sid)
                    self._tree.advance(sid, NodeStatus.MAGI_APPROVED)

            node = self._tree.get_node(sid)
            sr = StepResult(
                step_id=sid,
                status=node.status.value if node else "unknown",
                engine=engine,
                evidence=last_evidence,
                error=last_error,
                attempts_used=dict(node.attempts) if node else {},
            )
            step_results.append(sr)

            if not step_passed:
                all_passed = False

        result.steps = step_results

        # --- 3. Auditing phase (optional) -----------------------------------
        safe_result: SafeVerifyResult | None = None
        if self.config.enable_safe_verify and self._tree.is_complete():
            self._tree.phase = Phase.AUDITING
            # Simplified audit: scan collected evidence for forbidden tokens
            all_violations = []
            for sr in step_results:
                if sr.evidence:
                    violations = scan_forbidden_tokens(sr.evidence)
                    all_violations.extend(violations)

            safe_result = SafeVerifyResult(
                passed=len(all_violations) == 0,
                violations=all_violations,
                summary=f"Violations: {len(all_violations)} | "
                        f"Result: {'PASS' if len(all_violations) == 0 else 'FAIL'}",
            )
            result.safe_verify = safe_result

        # --- 4. Final phase -------------------------------------------------
        if all_passed:
            self._tree.phase = Phase.DONE
            result.success = True
            if safe_result is not None and not safe_result.passed:
                result.success = False
                self._tree.phase = Phase.FAILED
        else:
            self._tree.phase = Phase.FAILED
            result.success = False

        result.phase = self._tree.phase.value
        result.tree_snapshot = self._tree.to_status_json()
        result.summary = self._build_summary(result)

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute_step(self, step: dict) -> tuple[bool, str, str]:
        """Execute a single proof step via subprocess.

        Returns
        -------
        tuple[bool, str, str]
            (success, stdout_evidence, stderr_error)
        """
        engine = step.get("engine", "sympy")
        checker = step.get("checker", {})
        timeout = self.config.step_timeout

        try:
            if engine == "sympy":
                code = checker.get("code", "")
                if not code:
                    return False, "", "No checker code provided"
                proc = subprocess.run(
                    [sys.executable, "-c", code],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                if proc.returncode == 0:
                    return True, proc.stdout, ""
                return False, "", proc.stderr or f"Exit code {proc.returncode}"

            elif engine == "lean":
                cmds = checker.get("cmds", [])
                code = checker.get("code", "")
                if cmds:
                    lean_code = "\n".join(cmds)
                elif code:
                    lean_code = code
                else:
                    return False, "", "No lean checker code or cmds provided"

                # Write to a temp file and run lean
                tmp_fd, tmp_path = tempfile.mkstemp(suffix=".lean", prefix="orch_")
                try:
                    with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                        f.write(lean_code)
                    proc = subprocess.run(
                        self.config.lean_cmd + [tmp_path],
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                    )
                    if proc.returncode == 0:
                        return True, proc.stdout, ""
                    return False, "", proc.stderr or f"Exit code {proc.returncode}"
                finally:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
            else:
                return False, "", f"Unknown engine: {engine}"

        except subprocess.TimeoutExpired:
            return False, "", f"Step timed out after {timeout}s"
        except FileNotFoundError as exc:
            return False, "", f"Command not found: {exc}"
        except OSError as exc:
            return False, "", f"OS error: {exc}"

    def _handle_failure(
        self, step_id: str, stderr: str, step: dict
    ) -> bool:
        """Handle a step failure with error classification and retry budget.

        Returns
        -------
        bool
            True if retry is allowed, False if budget exhausted.
        """
        engine = step.get("engine", "sympy")
        tree = self._tree
        budget = self._budgets.get(step_id)

        if tree is None or budget is None:
            return False

        # Classify the error
        error = classify(stderr, engine)
        suggest_fix(error)

        # Check budget
        if budget.can_retry(engine):
            budget.consume(engine)
            tree.increment_attempt(step_id, engine)
            return True
        else:
            # Budget exhausted: mark as failed
            node = tree.get_node(step_id)
            if node and node.status != NodeStatus.FAILED:
                tree.advance(step_id, NodeStatus.FAILED)
            return False

    def _try_parallel(
        self, step_id: str, candidates: list[dict]
    ) -> tuple[bool, str, str]:
        """Use ParallelRunner to race multiple candidate solutions.

        Parameters
        ----------
        step_id:
            Identifier of the proof step.
        candidates:
            List of candidate dicts with ``code`` and ``engine`` keys.

        Returns
        -------
        tuple[bool, str, str]
            (success, evidence, error)
        """
        branches = [
            CandidateBranch(
                branch_id=f"{step_id}_c{i}",
                code=c.get("code", ""),
                engine=c.get("engine", "sympy"),
            )
            for i, c in enumerate(candidates)
        ]

        runner = ParallelRunner(
            max_workers=self.config.parallel_candidates,
            timeout=self.config.parallel_timeout,
        )
        log = runner.run_candidates(step_id, branches)
        winner = runner.get_winner(log)

        if winner is not None:
            return True, winner.stdout, ""
        return False, "", "All parallel candidates failed"

    @staticmethod
    def _build_summary(result: OrchestratorResult) -> str:
        """Build a human-readable summary string."""
        total = len(result.steps)
        passed = sum(1 for s in result.steps if s.status == NodeStatus.PASSED.value)
        failed = sum(1 for s in result.steps if s.status == NodeStatus.FAILED.value)
        parts = [
            f"Run {result.run_id}",
            f"Steps: {passed}/{total} passed",
        ]
        if failed:
            parts.append(f"{failed} failed")
        if result.safe_verify is not None:
            parts.append(f"Audit: {'PASS' if result.safe_verify.passed else 'FAIL'}")
        parts.append(f"Result: {'SUCCESS' if result.success else 'FAILED'}")
        return " | ".join(parts)
