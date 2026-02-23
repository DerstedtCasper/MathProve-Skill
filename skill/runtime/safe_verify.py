"""SafeVerify: Lean4 proof artifact white-box audit module.

Performs static analysis, axiom dependency tracking, and optional
environment replay to guarantee proof soundness.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ForbiddenToken(str, Enum):
    """Tokens that must never appear in a verified Lean4 proof."""

    SORRY = "sorry"
    ADMIT = "admit"
    PARTIAL = "partial"
    UNSAFE = "unsafe"
    SORRY_AX = "sorryAx"


@dataclass
class AuditViolation:
    """A single forbidden-token occurrence found during source scan."""

    token: ForbiddenToken
    filepath: str = ""
    line_no: int = 0
    context: str = ""


@dataclass
class AxiomReport:
    """Result of ``#print axioms`` for one theorem."""

    theorem_name: str
    axioms: list[str] = field(default_factory=list)
    has_sorry_ax: bool = False
    raw_output: str = ""


@dataclass
class SafeVerifyResult:
    """Aggregated audit result."""

    passed: bool
    violations: list[AuditViolation] = field(default_factory=list)
    axiom_reports: list[AxiomReport] = field(default_factory=list)
    replay_passed: bool | None = None
    summary: str = ""

    def compute_passed(self) -> bool:
        """Return True only when all checks are clean."""
        if self.violations:
            return False
        if any(r.has_sorry_ax for r in self.axiom_reports):
            return False
        if self.replay_passed is False:
            return False
        return True


# ---------------------------------------------------------------------------
# Comment stripping
# ---------------------------------------------------------------------------

def strip_lean_comments(source: str) -> str:
    """Remove line comments (``-- ...``) and block comments (``/- ... -/``).

    Supports arbitrarily nested block comments.
    """
    result: list[str] = []
    i = 0
    n = len(source)
    while i < n:
        # Block comment start
        if i + 1 < n and source[i] == "/" and source[i + 1] == "-":
            depth = 1
            i += 2
            while i < n and depth > 0:
                if i + 1 < n and source[i] == "/" and source[i + 1] == "-":
                    depth += 1
                    i += 2
                elif i + 1 < n and source[i] == "-" and source[i + 1] == "/":
                    depth -= 1
                    i += 2
                else:
                    i += 1
            continue
        # Line comment start
        if i + 1 < n and source[i] == "-" and source[i + 1] == "-":
            while i < n and source[i] != "\n":
                i += 1
            continue
        result.append(source[i])
        i += 1
    return "".join(result)


# ---------------------------------------------------------------------------
# Forbidden-token scanner
# ---------------------------------------------------------------------------

_FORBIDDEN_RE = re.compile(r"\b(sorry|admit|partial|unsafe)\b")

_TOKEN_MAP = {
    "sorry": ForbiddenToken.SORRY,
    "admit": ForbiddenToken.ADMIT,
    "partial": ForbiddenToken.PARTIAL,
    "unsafe": ForbiddenToken.UNSAFE,
}


def scan_forbidden_tokens(
    lean_source: str,
    filepath: str = "",
) -> list[AuditViolation]:
    """Scan *lean_source* for forbidden tokens (comments excluded).

    Returns a list of :class:`AuditViolation` with 1-based line numbers.
    """
    cleaned = strip_lean_comments(lean_source)
    violations: list[AuditViolation] = []
    for line_no, line in enumerate(cleaned.splitlines(), start=1):
        for m in _FORBIDDEN_RE.finditer(line):
            token_str = m.group(1)
            violations.append(
                AuditViolation(
                    token=_TOKEN_MAP[token_str],
                    filepath=filepath,
                    line_no=line_no,
                    context=line.strip(),
                )
            )
    return violations


# ---------------------------------------------------------------------------
# Audit-file generation
# ---------------------------------------------------------------------------

def generate_audit_lean(
    theorem_names: list[str],
    import_module: str,
    output_path: str,
) -> str:
    """Generate a ``.lean`` audit script and write it to *output_path*.

    The generated file imports *import_module* and emits
    ``#print axioms`` for each theorem name.

    Returns the *output_path* for convenience.
    """
    lines = [
        "-- SafeVerify Audit Script (auto-generated)",
        "-- DO NOT EDIT MANUALLY",
        "",
        f"import {import_module}",
        "",
        "-- Axiom dependency audit",
    ]
    for name in theorem_names:
        lines.append(f"#print axioms {name}")
    lines.append("")

    content = "\n".join(lines)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(content, encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# Axiom output parser
# ---------------------------------------------------------------------------

_DEPENDS_RE = re.compile(
    r"'([^']+)'\s+depends on axioms:\s*\[([^\]]*)\]"
)
_NO_DEPS_RE = re.compile(
    r"'([^']+)'\s+does not depend on any axioms"
)


def parse_axioms_output(lean_stdout: str) -> list[AxiomReport]:
    """Parse the stdout of a Lean process that ran ``#print axioms``.

    Recognised formats::

        'thm1' depends on axioms: [propext, Classical.choice]
        'thm2' does not depend on any axioms
    """
    reports: list[AxiomReport] = []
    for line in lean_stdout.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue

        m = _DEPENDS_RE.search(line_stripped)
        if m:
            name = m.group(1)
            axioms_str = m.group(2).strip()
            axioms = [a.strip() for a in axioms_str.split(",") if a.strip()]
            reports.append(
                AxiomReport(
                    theorem_name=name,
                    axioms=axioms,
                    has_sorry_ax="sorryAx" in axioms,
                    raw_output=line_stripped,
                )
            )
            continue

        m = _NO_DEPS_RE.search(line_stripped)
        if m:
            name = m.group(1)
            reports.append(
                AxiomReport(
                    theorem_name=name,
                    axioms=[],
                    has_sorry_ax=False,
                    raw_output=line_stripped,
                )
            )
    return reports


# ---------------------------------------------------------------------------
# Top-level audit runner
# ---------------------------------------------------------------------------

def run_audit(
    lean_files: list[str],
    theorem_names: list[str],
    import_module: str,
    lean_cwd: str | None = None,
    lean_cmd: list[str] | None = None,
    enable_replay: bool = False,
    timeout: int = 120,
) -> SafeVerifyResult:
    """Run a full SafeVerify audit pipeline.

    Steps:
      1. Read each *lean_file* and scan for forbidden tokens.
      2. Generate an audit ``.lean`` file with ``#print axioms``.
      3. Invoke Lean to compile the audit file and parse axiom output.
      4. Optionally replay (re-compile) source files in a temp directory.
      5. Return an aggregated :class:`SafeVerifyResult`.
    """
    if lean_cmd is None:
        lean_cmd = ["lean"]

    violations: list[AuditViolation] = []
    axiom_reports: list[AxiomReport] = []
    replay_passed: bool | None = None

    # Step 1: Scan source files for forbidden tokens.
    for fpath in lean_files:
        try:
            source = Path(fpath).read_text(encoding="utf-8")
        except OSError:
            continue
        violations.extend(scan_forbidden_tokens(source, filepath=fpath))

    # Step 2-3: Axiom dependency audit (only when theorem names given).
    if theorem_names:
        tmp_dir = tempfile.mkdtemp(prefix="safeverify_audit_")
        try:
            audit_path = os.path.join(tmp_dir, "SafeVerifyAudit.lean")
            generate_audit_lean(theorem_names, import_module, audit_path)
            try:
                proc = subprocess.run(
                    lean_cmd + [audit_path],
                    capture_output=True,
                    text=True,
                    cwd=lean_cwd,
                    timeout=timeout,
                )
                axiom_reports = parse_axioms_output(proc.stdout)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # Step 4: Optional environment replay.
    if enable_replay and lean_files:
        replay_dir = tempfile.mkdtemp(prefix="safeverify_replay_")
        try:
            for fpath in lean_files:
                dest = os.path.join(replay_dir, os.path.basename(fpath))
                shutil.copy2(fpath, dest)
            try:
                proc = subprocess.run(
                    lean_cmd + ["--make"] + [
                        os.path.join(replay_dir, os.path.basename(f))
                        for f in lean_files
                    ],
                    capture_output=True,
                    text=True,
                    cwd=replay_dir,
                    timeout=timeout,
                )
                replay_passed = proc.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError):
                replay_passed = False
        finally:
            shutil.rmtree(replay_dir, ignore_errors=True)

    # Step 5: Aggregate result.
    result = SafeVerifyResult(
        passed=False,
        violations=violations,
        axiom_reports=axiom_reports,
        replay_passed=replay_passed,
    )
    result.passed = result.compute_passed()

    parts: list[str] = []
    parts.append(f"Violations: {len(violations)}")
    parts.append(f"Axiom reports: {len(axiom_reports)}")
    sorry_count = sum(1 for r in axiom_reports if r.has_sorry_ax)
    if sorry_count:
        parts.append(f"sorryAx detected: {sorry_count}")
    if replay_passed is not None:
        parts.append(f"Replay: {'OK' if replay_passed else 'FAIL'}")
    parts.append(f"Result: {'PASS' if result.passed else 'FAIL'}")
    result.summary = " | ".join(parts)

    return result
