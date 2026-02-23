"""Tests for skill.runtime.orchestrator module."""
from __future__ import annotations

import pytest

from skill.runtime.orchestrator import (
    Orchestrator,
    OrchestratorConfig,
    OrchestratorResult,
    StepResult,
)
from skill.runtime.proof_tree import ProofSearchTree, NodeStatus, Phase
from skill.runtime.error_classifier import RetryBudget


# ---------------------------------------------------------------------------
# Dataclass defaults
# ---------------------------------------------------------------------------


class TestOrchestratorConfigDefaults:
    def test_max_magi_rounds(self):
        cfg = OrchestratorConfig()
        assert cfg.max_magi_rounds == 2

    def test_retry_limits_lean(self):
        cfg = OrchestratorConfig()
        assert cfg.retry_limits["lean"] == 5

    def test_retry_limits_sympy(self):
        cfg = OrchestratorConfig()
        assert cfg.retry_limits["sympy"] == 3

    def test_retry_limits_magi(self):
        cfg = OrchestratorConfig()
        assert cfg.retry_limits["magi"] == 2

    def test_parallel_candidates(self):
        cfg = OrchestratorConfig()
        assert cfg.parallel_candidates == 3

    def test_enable_safe_verify(self):
        cfg = OrchestratorConfig()
        assert cfg.enable_safe_verify is True

    def test_enable_replay(self):
        cfg = OrchestratorConfig()
        assert cfg.enable_replay is False

    def test_step_timeout(self):
        cfg = OrchestratorConfig()
        assert cfg.step_timeout == 30


class TestStepResultDefaults:
    def test_evidence_default(self):
        sr = StepResult(step_id="S1", status="passed", engine="sympy")
        assert sr.evidence == ""

    def test_error_default(self):
        sr = StepResult(step_id="S1", status="passed", engine="sympy")
        assert sr.error == ""

    def test_attempts_used_default(self):
        sr = StepResult(step_id="S1", status="passed", engine="sympy")
        assert sr.attempts_used == {}


class TestOrchestratorResultDefaults:
    def test_success_default_false(self):
        r = OrchestratorResult(run_id="test")
        assert r.success is False

    def test_steps_default_empty(self):
        r = OrchestratorResult(run_id="test")
        assert r.steps == []

    def test_safe_verify_default_none(self):
        r = OrchestratorResult(run_id="test")
        assert r.safe_verify is None

    def test_tree_snapshot_default_empty(self):
        r = OrchestratorResult(run_id="test")
        assert r.tree_snapshot == {}

    def test_summary_default_empty(self):
        r = OrchestratorResult(run_id="test")
        assert r.summary == ""


# ---------------------------------------------------------------------------
# Orchestrator init
# ---------------------------------------------------------------------------


class TestOrchestratorInit:
    def test_default_config(self):
        orch = Orchestrator()
        assert orch.config is not None
        assert isinstance(orch.config, OrchestratorConfig)

    def test_custom_config(self):
        cfg = OrchestratorConfig(max_magi_rounds=5)
        orch = Orchestrator(cfg)
        assert orch.config.max_magi_rounds == 5

    def test_tree_initially_none(self):
        orch = Orchestrator()
        assert orch._tree is None

    def test_budgets_initially_empty(self):
        orch = Orchestrator()
        assert orch._budgets == {}


# ---------------------------------------------------------------------------
# run() integration tests (use real subprocess for simple python code)
# ---------------------------------------------------------------------------


class TestOrchestratorRunSimpleSympy:
    def test_simple_passing_step(self):
        orch = Orchestrator()
        result = orch.run(
            "test problem",
            [
                {
                    "id": "S1",
                    "goal": "test",
                    "engine": "sympy",
                    "checker": {"type": "sympy", "code": "print('ok')"},
                }
            ],
        )
        assert result.success is True
        assert result.phase == Phase.DONE.value
        assert len(result.steps) == 1
        assert result.steps[0].status == NodeStatus.PASSED.value
        assert "ok" in result.steps[0].evidence

    def test_multiple_passing_steps(self):
        orch = Orchestrator()
        result = orch.run(
            "test problem",
            [
                {
                    "id": "S1",
                    "goal": "step 1",
                    "engine": "sympy",
                    "checker": {"type": "sympy", "code": "print('step1')"},
                },
                {
                    "id": "S2",
                    "goal": "step 2",
                    "engine": "sympy",
                    "checker": {"type": "sympy", "code": "print('step2')"},
                },
            ],
        )
        assert result.success is True
        assert len(result.steps) == 2
        assert all(s.status == NodeStatus.PASSED.value for s in result.steps)


class TestOrchestratorRunFailingStep:
    def test_failing_step_exhausts_budget(self):
        cfg = OrchestratorConfig(
            retry_limits={"magi": 0, "sympy": 1, "lean": 0}
        )
        orch = Orchestrator(cfg)
        result = orch.run(
            "test",
            [
                {
                    "id": "S1",
                    "goal": "fail test",
                    "engine": "sympy",
                    "checker": {
                        "type": "sympy",
                        "code": "raise ValueError('bad')",
                    },
                }
            ],
        )
        assert result.success is False
        assert result.phase == Phase.FAILED.value

    def test_failing_step_with_zero_retries(self):
        cfg = OrchestratorConfig(
            retry_limits={"magi": 0, "sympy": 0, "lean": 0}
        )
        orch = Orchestrator(cfg)
        result = orch.run(
            "test",
            [
                {
                    "id": "S1",
                    "goal": "fail test",
                    "engine": "sympy",
                    "checker": {
                        "type": "sympy",
                        "code": "raise ValueError('bad')",
                    },
                }
            ],
        )
        assert result.success is False
        assert result.steps[0].status == NodeStatus.FAILED.value


# ---------------------------------------------------------------------------
# _handle_failure unit tests
# ---------------------------------------------------------------------------


class TestHandleFailure:
    def _make_orchestrator_with_node(
        self, step_id: str = "S1", limits: dict | None = None, used: dict | None = None
    ) -> Orchestrator:
        """Helper to set up an orchestrator with a single node at MAGI_APPROVED."""
        orch = Orchestrator()
        orch._tree = ProofSearchTree("test")
        orch._tree.add_node(step_id)
        orch._tree.advance(step_id, NodeStatus.MAGI_APPROVED)
        budget_kwargs: dict = {"step_id": step_id}
        if limits is not None:
            budget_kwargs["limits"] = limits
        if used is not None:
            budget_kwargs["used"] = used
        orch._budgets = {step_id: RetryBudget(**budget_kwargs)}
        return orch

    def test_can_retry_with_budget(self):
        orch = self._make_orchestrator_with_node()
        can_retry = orch._handle_failure(
            "S1", "SyntaxError: bad", {"engine": "sympy", "id": "S1"}
        )
        assert can_retry is True

    def test_budget_exhausted_returns_false(self):
        orch = self._make_orchestrator_with_node(
            limits={"magi": 0, "sympy": 0, "lean": 0},
            used={"magi": 0, "sympy": 0, "lean": 0},
        )
        can_retry = orch._handle_failure(
            "S1", "error", {"engine": "sympy", "id": "S1"}
        )
        assert can_retry is False

    def test_retry_increments_attempt(self):
        orch = self._make_orchestrator_with_node()
        orch._handle_failure(
            "S1", "SyntaxError: bad", {"engine": "sympy", "id": "S1"}
        )
        node = orch._tree.get_node("S1")
        assert node.attempts["sympy"] == 1

    def test_budget_consumed_after_retry(self):
        orch = self._make_orchestrator_with_node()
        orch._handle_failure(
            "S1", "SyntaxError: bad", {"engine": "sympy", "id": "S1"}
        )
        budget = orch._budgets["S1"]
        assert budget.used["sympy"] == 1

    def test_missing_tree_returns_false(self):
        orch = Orchestrator()
        orch._tree = None
        result = orch._handle_failure("S1", "err", {"engine": "sympy", "id": "S1"})
        assert result is False

    def test_missing_budget_returns_false(self):
        orch = Orchestrator()
        orch._tree = ProofSearchTree("test")
        orch._tree.add_node("S1")
        orch._budgets = {}
        result = orch._handle_failure("S1", "err", {"engine": "sympy", "id": "S1"})
        assert result is False


# ---------------------------------------------------------------------------
# Tree snapshot
# ---------------------------------------------------------------------------


class TestTreeSnapshot:
    def test_snapshot_is_nonempty_dict(self):
        orch = Orchestrator()
        result = orch.run(
            "test",
            [
                {
                    "id": "S1",
                    "goal": "test",
                    "engine": "sympy",
                    "checker": {"type": "sympy", "code": "print('ok')"},
                }
            ],
        )
        assert isinstance(result.tree_snapshot, dict)
        assert len(result.tree_snapshot) > 0

    def test_snapshot_contains_run_id(self):
        orch = Orchestrator()
        result = orch.run(
            "test",
            [
                {
                    "id": "S1",
                    "goal": "test",
                    "engine": "sympy",
                    "checker": {"type": "sympy", "code": "print('ok')"},
                }
            ],
        )
        assert "run_id" in result.tree_snapshot

    def test_snapshot_run_id_matches(self):
        orch = Orchestrator()
        result = orch.run(
            "test",
            [
                {
                    "id": "S1",
                    "goal": "test",
                    "engine": "sympy",
                    "checker": {"type": "sympy", "code": "print('ok')"},
                }
            ],
        )
        assert result.tree_snapshot["run_id"] == result.run_id

    def test_snapshot_contains_nodes(self):
        orch = Orchestrator()
        result = orch.run(
            "test",
            [
                {
                    "id": "S1",
                    "goal": "test",
                    "engine": "sympy",
                    "checker": {"type": "sympy", "code": "print('ok')"},
                }
            ],
        )
        assert "nodes" in result.tree_snapshot
        assert len(result.tree_snapshot["nodes"]) == 1


# ---------------------------------------------------------------------------
# _execute_step edge cases
# ---------------------------------------------------------------------------


class TestExecuteStep:
    def test_no_checker_code(self):
        orch = Orchestrator()
        success, evidence, error = orch._execute_step(
            {"id": "S1", "engine": "sympy", "checker": {}}
        )
        assert success is False
        assert "No checker code" in error

    def test_unknown_engine(self):
        orch = Orchestrator()
        success, evidence, error = orch._execute_step(
            {"id": "S1", "engine": "unknown", "checker": {"code": "x"}}
        )
        assert success is False
        assert "Unknown engine" in error

    def test_timeout_handling(self):
        cfg = OrchestratorConfig(step_timeout=1)
        orch = Orchestrator(cfg)
        success, evidence, error = orch._execute_step(
            {
                "id": "S1",
                "engine": "sympy",
                "checker": {"code": "import time; time.sleep(10)"},
            }
        )
        assert success is False
        assert "timed out" in error


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


class TestSummary:
    def test_summary_not_empty(self):
        orch = Orchestrator()
        result = orch.run(
            "test",
            [
                {
                    "id": "S1",
                    "goal": "test",
                    "engine": "sympy",
                    "checker": {"type": "sympy", "code": "print('ok')"},
                }
            ],
        )
        assert result.summary != ""
        assert "SUCCESS" in result.summary

    def test_failed_summary(self):
        cfg = OrchestratorConfig(
            retry_limits={"magi": 0, "sympy": 0, "lean": 0}
        )
        orch = Orchestrator(cfg)
        result = orch.run(
            "test",
            [
                {
                    "id": "S1",
                    "goal": "test",
                    "engine": "sympy",
                    "checker": {"code": "raise Exception('x')"},
                }
            ],
        )
        assert "FAILED" in result.summary
