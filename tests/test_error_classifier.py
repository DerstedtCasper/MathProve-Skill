"""Tests for skill.runtime.error_classifier module."""
from __future__ import annotations

import pytest

from skill.runtime.error_classifier import (
    ErrorCategory,
    ErrorSource,
    RetryBudget,
    StructuredError,
    classify,
    format_feedback_prompt,
    suggest_fix,
)


# ---- Enum value tests ----

class TestEnumValues:
    def test_error_category_values(self):
        assert ErrorCategory.SYNTAX == "syntax"
        assert ErrorCategory.LOGIC == "logic"
        assert ErrorCategory.ENVIRONMENT == "environment"
        assert len(ErrorCategory) == 3

    def test_error_source_values(self):
        assert ErrorSource.SYMPY == "sympy"
        assert ErrorSource.LEAN == "lean"
        assert ErrorSource.MAGI == "magi"
        assert len(ErrorSource) == 3


# ---- Lean classification tests ----

class TestClassifyLean:
    def test_classify_lean_syntax(self):
        stderr = "error: expected ':=' or '|'"
        result = classify(stderr, "lean")
        assert result.category == ErrorCategory.SYNTAX
        assert result.source == ErrorSource.LEAN

    def test_classify_lean_logic(self):
        stderr = "error: type mismatch\n  expected Nat\n  got Bool"
        result = classify(stderr, "lean")
        assert result.category == ErrorCategory.LOGIC

    def test_classify_lean_tactic_failed(self):
        stderr = "tactic 'simp' failed, nested error"
        assert classify(stderr, "lean").category == ErrorCategory.LOGIC

    def test_classify_lean_environment(self):
        stderr = "error: could not find module 'Mathlib.Algebra'"
        assert classify(stderr, "lean").category == ErrorCategory.ENVIRONMENT


# ---- SymPy classification tests ----

class TestClassifySympy:
    def test_classify_sympy_syntax(self):
        stderr = "SyntaxError: unexpected EOF while parsing"
        assert classify(stderr, "sympy").category == ErrorCategory.SYNTAX

    def test_classify_sympy_logic(self):
        stderr = "AssertionError: simplify result mismatch"
        assert classify(stderr, "sympy").category == ErrorCategory.LOGIC

    def test_classify_sympy_name_error(self):
        stderr = "NameError: name 'x' is not defined"
        assert classify(stderr, "sympy").category == ErrorCategory.SYNTAX


# ---- MAGI classification tests ----

class TestClassifyMagi:
    def test_classify_magi_rejected(self):
        stderr = "REJECTED: proof strategy is incomplete"
        assert classify(stderr, "magi").category == ErrorCategory.LOGIC

    def test_classify_magi_timeout(self):
        stderr = "timeout: magi planning exceeded 60s"
        assert classify(stderr, "magi").category == ErrorCategory.ENVIRONMENT


# ---- RetryBudget tests ----

class TestRetryBudget:
    def test_retry_budget_basic(self):
        budget = RetryBudget(step_id="S1")
        assert budget.can_retry("lean") is True
        budget.consume("lean")
        assert budget.remaining("lean") == 4

    def test_retry_budget_exhausted(self):
        budget = RetryBudget(
            step_id="S1",
            limits={"lean": 1},
            used={"lean": 0},
        )
        budget.consume("lean")
        assert not budget.can_retry("lean")
        with pytest.raises(RuntimeError):
            budget.consume("lean")

    def test_retry_budget_is_exhausted(self):
        budget = RetryBudget(
            step_id="S1",
            limits={"magi": 0, "sympy": 0, "lean": 0},
            used={"magi": 0, "sympy": 0, "lean": 0},
        )
        assert budget.is_exhausted()


# ---- suggest_fix tests ----

class TestSuggestFix:
    def test_suggest_fix_lean_syntax(self):
        error = StructuredError(
            category=ErrorCategory.SYNTAX,
            source=ErrorSource.LEAN,
            message="expected ':='",
            location="file.lean:10",
        )
        result = suggest_fix(error)
        assert "syntax" in result.lower()
        assert error.suggestion == result

    def test_suggest_fix_lean_logic(self):
        error = StructuredError(
            category=ErrorCategory.LOGIC,
            source=ErrorSource.LEAN,
            message="type mismatch",
        )
        result = suggest_fix(error)
        assert "tactic" in result.lower() or "lemma" in result.lower()


# ---- format_feedback_prompt tests ----

class TestFormatFeedbackPrompt:
    def test_format_feedback_prompt(self):
        error = StructuredError(
            category=ErrorCategory.LOGIC,
            source=ErrorSource.LEAN,
            message="type mismatch",
            suggestion="try different tactic",
        )
        prompt = format_feedback_prompt(error, "S3")
        assert "Step S3" in prompt
        assert "type mismatch" in prompt
        assert "logic" in prompt.lower()
