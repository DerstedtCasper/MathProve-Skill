"""ErrorClassifier: structured error classification and self-healing budget tracker."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class ErrorCategory(str, Enum):
    """Three-level error category for proof verification failures."""

    SYNTAX = "syntax"
    LOGIC = "logic"
    ENVIRONMENT = "environment"


class ErrorSource(str, Enum):
    """Origin tool that produced the error."""

    SYMPY = "sympy"
    LEAN = "lean"
    MAGI = "magi"


@dataclass
class StructuredError:
    """Parsed and classified error with human-readable summary and fix suggestion."""

    category: ErrorCategory
    source: ErrorSource
    message: str
    location: str = ""
    raw_stderr: str = ""
    suggestion: str = ""


@dataclass
class RetryBudget:
    """Per-step retry budget tracker across tool backends.

    Each tool has an independent retry limit. Consuming beyond the limit
    raises ``RuntimeError`` so callers can fail fast.
    """

    step_id: str
    limits: dict[str, int] = field(
        default_factory=lambda: {"magi": 2, "sympy": 3, "lean": 5},
    )
    used: dict[str, int] = field(
        default_factory=lambda: {"magi": 0, "sympy": 0, "lean": 0},
    )

    def can_retry(self, tool: str) -> bool:
        """Return True if *tool* still has remaining retries."""
        return self.used.get(tool, 0) < self.limits.get(tool, 0)

    def consume(self, tool: str) -> None:
        """Consume one retry for *tool*. Raise ``RuntimeError`` if exhausted."""
        if not self.can_retry(tool):
            raise RuntimeError(
                f"Retry budget exhausted for tool '{tool}' at step '{self.step_id}'"
            )
        self.used[tool] = self.used.get(tool, 0) + 1

    def remaining(self, tool: str) -> int:
        """Return the number of retries left for *tool*."""
        return self.limits.get(tool, 0) - self.used.get(tool, 0)

    def is_exhausted(self) -> bool:
        """Return True if **all** tracked tools have exhausted their budgets."""
        return all(
            self.used.get(t, 0) >= self.limits.get(t, 0)
            for t in self.limits
        )


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

_LEAN_SYNTAX_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"expected\b", re.IGNORECASE),
    re.compile(r"unknown identifier", re.IGNORECASE),
    re.compile(r"unexpected token", re.IGNORECASE),
    re.compile(r"unterminated", re.IGNORECASE),
    re.compile(r"\bmissing\b", re.IGNORECASE),
    re.compile(r"parse error", re.IGNORECASE),
]

_LEAN_LOGIC_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"type mismatch", re.IGNORECASE),
    re.compile(r"tactic[\s\S]*?failed", re.IGNORECASE),
    re.compile(r"unsolved goals", re.IGNORECASE),
    re.compile(r"unknown constant", re.IGNORECASE),
    re.compile(r"application type mismatch", re.IGNORECASE),
    re.compile(r"invalid field", re.IGNORECASE),
    re.compile(r"failed to synthesize", re.IGNORECASE),
]

_SYMPY_SYNTAX_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"SyntaxError", re.IGNORECASE),
    re.compile(r"IndentationError", re.IGNORECASE),
    re.compile(r"NameError", re.IGNORECASE),
    re.compile(r"unexpected EOF", re.IGNORECASE),
]

_SYMPY_LOGIC_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"TypeError", re.IGNORECASE),
    re.compile(r"ValueError", re.IGNORECASE),
    re.compile(r"Assert(?:ion)?Error", re.IGNORECASE),
    re.compile(r"\bassert\b", re.IGNORECASE),
    re.compile(r"\bcannot\b", re.IGNORECASE),
    re.compile(r"\bfailed\b", re.IGNORECASE),
]


def _first_meaningful_line(stderr: str) -> str:
    """Extract the first non-empty, non-whitespace line from *stderr*."""
    for line in stderr.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return stderr.strip()[:120] if stderr else "(empty stderr)"


def _match_any(text: str, patterns: list[re.Pattern[str]]) -> bool:
    """Return True if *text* matches any of the compiled patterns."""
    return any(p.search(text) for p in patterns)


def _classify_lean(stderr: str) -> ErrorCategory:
    """Classify a Lean 4 stderr string."""
    if _match_any(stderr, _LEAN_LOGIC_PATTERNS):
        return ErrorCategory.LOGIC
    if _match_any(stderr, _LEAN_SYNTAX_PATTERNS):
        return ErrorCategory.SYNTAX
    return ErrorCategory.ENVIRONMENT


def _classify_sympy(stderr: str) -> ErrorCategory:
    """Classify a SymPy (Python) stderr string."""
    if _match_any(stderr, _SYMPY_SYNTAX_PATTERNS):
        return ErrorCategory.SYNTAX
    if _match_any(stderr, _SYMPY_LOGIC_PATTERNS):
        return ErrorCategory.LOGIC
    return ErrorCategory.ENVIRONMENT


def _classify_magi(stderr: str) -> ErrorCategory:
    """Classify a MAGI planner stderr string."""
    if "REJECTED" in stderr.upper():
        return ErrorCategory.LOGIC
    if "timeout" in stderr.lower() or "connection" in stderr.lower():
        return ErrorCategory.ENVIRONMENT
    return ErrorCategory.LOGIC


def classify(stderr: str, source: str) -> StructuredError:
    """Classify *stderr* from *source* into a ``StructuredError``.

    Parameters
    ----------
    stderr:
        Raw stderr output from the verification backend.
    source:
        One of ``"lean"``, ``"sympy"``, or ``"magi"`` (case-insensitive).

    Returns
    -------
    StructuredError
        Structured error with category, source, and extracted message.
    """
    src_lower = source.lower()
    error_source = ErrorSource(src_lower)

    if src_lower == "lean":
        category = _classify_lean(stderr)
    elif src_lower == "sympy":
        category = _classify_sympy(stderr)
    elif src_lower == "magi":
        category = _classify_magi(stderr)
    else:
        category = ErrorCategory.ENVIRONMENT

    message = _first_meaningful_line(stderr)

    return StructuredError(
        category=category,
        source=error_source,
        message=message,
        raw_stderr=stderr,
    )


# ---------------------------------------------------------------------------
# Suggestion and prompt formatting
# ---------------------------------------------------------------------------

def suggest_fix(error: StructuredError) -> str:
    """Generate a human-readable fix suggestion and attach it to *error*.

    Returns the suggestion string (also stored as ``error.suggestion``).
    """
    loc = error.location or "(unknown location)"

    if error.category == ErrorCategory.SYNTAX:
        if error.source == ErrorSource.LEAN:
            suggestion = (
                f"Lean syntax error detected. Review the code near {loc} "
                "for typos, missing parentheses, or undefined identifiers."
            )
        elif error.source == ErrorSource.SYMPY:
            suggestion = (
                f"Python syntax error. Check indentation, brackets, and "
                f"variable names near {loc}."
            )
        else:
            suggestion = f"Syntax error from {error.source.value}: {error.message}"

    elif error.category == ErrorCategory.LOGIC:
        if error.source == ErrorSource.LEAN:
            suggestion = (
                f"Lean logic error: {error.message}. Consider using a "
                "different tactic, checking theorem statement compatibility, "
                "or searching mathlib for alternative lemmas."
            )
        elif error.source == ErrorSource.SYMPY:
            suggestion = (
                f"SymPy logic error: {error.message}. Verify the "
                "mathematical reasoning and check for type/value mismatches."
            )
        elif error.source == ErrorSource.MAGI:
            suggestion = (
                f"MAGI rejected the plan: {error.message}. Revise the "
                "proof strategy and address the concerns raised."
            )
        else:
            suggestion = f"Logic error from {error.source.value}: {error.message}"

    else:
        # ENVIRONMENT
        suggestion = (
            f"Environment error: {error.message}. This may be a transient "
            "issue -- consider retrying or checking dependencies."
        )

    error.suggestion = suggestion
    return suggestion


def format_feedback_prompt(error: StructuredError, step_id: str = "") -> str:
    """Format a ``StructuredError`` into a feedback prompt for the MAGI planner.

    Parameters
    ----------
    error:
        Classified error to include in the prompt.
    step_id:
        Optional proof-step identifier for context.

    Returns
    -------
    str
        Multi-line feedback prompt ready to be injected into a planning call.
    """
    return (
        f"[Error Feedback for Step {step_id}]\n"
        f"Category: {error.category.value}\n"
        f"Source: {error.source.value}\n"
        f"Error: {error.message}\n"
        f"Suggestion: {error.suggestion}\n"
        "Please adjust the proof strategy based on this feedback."
    )
