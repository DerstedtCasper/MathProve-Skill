"""Tests for skill.runtime.parallel_runner."""
from __future__ import annotations

import json
import os

import pytest

from skill.runtime.parallel_runner import (
    BranchStatus,
    CandidateBranch,
    ParallelRunner,
    SearchTreeLog,
    _run_single_candidate,
)


# ---------------------------------------------------------------------------
# Enum and dataclass basics
# ---------------------------------------------------------------------------


def test_branch_status_enum():
    """All expected enum values exist."""
    assert BranchStatus.PENDING.value == "pending"
    assert BranchStatus.RUNNING.value == "running"
    assert BranchStatus.SUCCESS.value == "success"
    assert BranchStatus.FAILED.value == "failed"
    assert BranchStatus.CANCELLED.value == "cancelled"
    # Verify count
    assert len(BranchStatus) == 5


def test_candidate_branch_defaults():
    """CandidateBranch has correct defaults."""
    b = CandidateBranch(branch_id="b1", code="x=1", engine="sympy")
    assert b.branch_id == "b1"
    assert b.code == "x=1"
    assert b.engine == "sympy"
    assert b.workspace_path == ""
    assert b.status == BranchStatus.PENDING
    assert b.stdout == ""
    assert b.stderr == ""
    assert b.elapsed_sec == 0.0


def test_search_tree_log_to_dict():
    """to_dict returns all expected fields."""
    branch = CandidateBranch(branch_id="b1", code="print(1)", engine="sympy")
    log = SearchTreeLog(
        step_id="S1",
        branches=[branch],
        winner_id="b1",
        started_at="2026-01-01T00:00:00",
        finished_at="2026-01-01T00:00:01",
    )
    d = log.to_dict()
    assert d["step_id"] == "S1"
    assert d["winner_id"] == "b1"
    assert d["started_at"] == "2026-01-01T00:00:00"
    assert d["finished_at"] == "2026-01-01T00:00:01"
    assert len(d["branches"]) == 1
    assert d["branches"][0]["branch_id"] == "b1"
    assert d["branches"][0]["status"] == "pending"


def test_search_tree_log_save(tmp_path):
    """save writes a valid JSON file."""
    branch = CandidateBranch(branch_id="b1", code="print(1)", engine="sympy")
    log = SearchTreeLog(step_id="S1", branches=[branch])
    filepath = str(tmp_path / "log.json")
    log.save(filepath)

    assert os.path.isfile(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["step_id"] == "S1"
    assert len(data["branches"]) == 1


# ---------------------------------------------------------------------------
# _run_single_candidate tests
# ---------------------------------------------------------------------------


def test_run_single_candidate_python_success():
    """A simple print script should succeed."""
    branch = CandidateBranch(
        branch_id="ok", code="print('ok')", engine="sympy"
    )
    result = _run_single_candidate(branch, timeout=30)
    assert result.status == BranchStatus.SUCCESS
    assert "ok" in result.stdout
    assert result.elapsed_sec > 0


def test_run_single_candidate_python_fail():
    """A script that raises should fail."""
    branch = CandidateBranch(
        branch_id="bad", code="raise ValueError('bad')", engine="sympy"
    )
    result = _run_single_candidate(branch, timeout=30)
    assert result.status == BranchStatus.FAILED


def test_run_single_candidate_timeout():
    """A script that sleeps too long should fail via timeout."""
    branch = CandidateBranch(
        branch_id="slow",
        code="import time; time.sleep(999)",
        engine="sympy",
    )
    result = _run_single_candidate(branch, timeout=1)
    assert result.status == BranchStatus.FAILED


# ---------------------------------------------------------------------------
# ParallelRunner tests
# ---------------------------------------------------------------------------


def test_parallel_runner_picks_winner():
    """The fast successful candidate should win."""
    branch_a = CandidateBranch(
        branch_id="branch_a",
        code="import time; time.sleep(5)",
        engine="sympy",
    )
    branch_b = CandidateBranch(
        branch_id="branch_b",
        code="print('ok')",
        engine="sympy",
    )
    branch_c = CandidateBranch(
        branch_id="branch_c",
        code="raise ValueError()",
        engine="sympy",
    )

    runner = ParallelRunner(max_workers=3, timeout=10)
    log = runner.run_candidates("S1", [branch_a, branch_b, branch_c])

    assert log.winner_id == "branch_b"
    winner = runner.get_winner(log)
    assert winner is not None
    assert winner.status == BranchStatus.SUCCESS


def test_parallel_runner_all_fail():
    """When all candidates fail, winner_id should be None."""
    branch_x = CandidateBranch(
        branch_id="x", code="raise RuntimeError('x')", engine="sympy"
    )
    branch_y = CandidateBranch(
        branch_id="y", code="raise RuntimeError('y')", engine="sympy"
    )

    runner = ParallelRunner(max_workers=2, timeout=10)
    log = runner.run_candidates("S2", [branch_x, branch_y])

    assert log.winner_id is None
    assert runner.get_winner(log) is None


def test_parallel_runner_log_structure():
    """SearchTreeLog should have timestamps and correct branch count."""
    branch = CandidateBranch(
        branch_id="solo", code="print('hello')", engine="sympy"
    )

    runner = ParallelRunner(max_workers=1, timeout=10)
    log = runner.run_candidates("S3", [branch])

    assert log.started_at != ""
    assert log.finished_at != ""
    assert len(log.branches) == 1
