"""Tests for skill.runtime.safe_verify module."""
from __future__ import annotations

import os

from skill.runtime.safe_verify import (
    AuditViolation,
    AxiomReport,
    ForbiddenToken,
    SafeVerifyResult,
    generate_audit_lean,
    parse_axioms_output,
    scan_forbidden_tokens,
    strip_lean_comments,
)


# ---------------------------------------------------------------------------
# strip_lean_comments
# ---------------------------------------------------------------------------

def test_strip_lean_comments_line():
    source = "theorem foo -- this is sorry\n:= by simp"
    result = strip_lean_comments(source)
    assert "sorry" not in result


def test_strip_lean_comments_block():
    source = "/- sorry admit -/ theorem bar := by simp"
    result = strip_lean_comments(source)
    assert "sorry" not in result
    assert "admit" not in result


def test_strip_lean_comments_nested():
    source = "/- outer /- inner sorry -/ still comment -/ real code"
    result = strip_lean_comments(source)
    assert result.strip() == "real code"


# ---------------------------------------------------------------------------
# scan_forbidden_tokens
# ---------------------------------------------------------------------------

def test_scan_finds_sorry():
    violations = scan_forbidden_tokens("theorem foo := by sorry")
    assert len(violations) == 1
    assert violations[0].token == ForbiddenToken.SORRY
    assert violations[0].line_no == 1


def test_scan_ignores_comments():
    source = "-- sorry\ntheorem foo := by simp"
    violations = scan_forbidden_tokens(source)
    assert len(violations) == 0


def test_scan_multiple_violations():
    source = "sorry\nadmit\nunsafe"
    violations = scan_forbidden_tokens(source)
    assert len(violations) == 3


def test_scan_word_boundary():
    source = "def sorry_helper := 42"
    violations = scan_forbidden_tokens(source)
    assert len(violations) == 0


# ---------------------------------------------------------------------------
# generate_audit_lean
# ---------------------------------------------------------------------------

def test_generate_audit_lean(tmp_path):
    output_path = str(tmp_path / "audit.lean")
    result = generate_audit_lean(["thm1", "thm2"], "MyModule", output_path)
    assert result == output_path
    content = open(output_path, encoding="utf-8").read()
    assert "import MyModule" in content
    assert "#print axioms thm1" in content
    assert "#print axioms thm2" in content


# ---------------------------------------------------------------------------
# parse_axioms_output
# ---------------------------------------------------------------------------

def test_parse_axioms_depends():
    stdout = "'thm1' depends on axioms: [propext, Classical.choice]"
    reports = parse_axioms_output(stdout)
    assert len(reports) == 1
    assert reports[0].theorem_name == "thm1"
    assert reports[0].axioms == ["propext", "Classical.choice"]
    assert reports[0].has_sorry_ax is False


def test_parse_axioms_sorry():
    stdout = "'thm1' depends on axioms: [sorryAx]"
    reports = parse_axioms_output(stdout)
    assert len(reports) == 1
    assert reports[0].has_sorry_ax is True


def test_parse_axioms_no_deps():
    stdout = "'thm1' does not depend on any axioms"
    reports = parse_axioms_output(stdout)
    assert len(reports) == 1
    assert reports[0].theorem_name == "thm1"
    assert reports[0].axioms == []
    assert reports[0].has_sorry_ax is False


# ---------------------------------------------------------------------------
# SafeVerifyResult.compute_passed
# ---------------------------------------------------------------------------

def test_result_passed_logic():
    # Clean result -> passed
    r1 = SafeVerifyResult(passed=False)
    assert r1.compute_passed() is True

    # With violations -> not passed
    r2 = SafeVerifyResult(
        passed=False,
        violations=[
            AuditViolation(token=ForbiddenToken.SORRY, line_no=1)
        ],
    )
    assert r2.compute_passed() is False

    # With sorryAx -> not passed
    r3 = SafeVerifyResult(
        passed=False,
        axiom_reports=[
            AxiomReport(theorem_name="t", axioms=["sorryAx"], has_sorry_ax=True)
        ],
    )
    assert r3.compute_passed() is False

    # replay_passed=False -> not passed
    r4 = SafeVerifyResult(passed=False, replay_passed=False)
    assert r4.compute_passed() is False

    # replay_passed=None (not run) -> passed
    r5 = SafeVerifyResult(passed=False, replay_passed=None)
    assert r5.compute_passed() is True
