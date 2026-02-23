"""CI smoke test -- verify core imports, runtime modules, and basic script functionality.

Design goals:
- Fast (< 15s, no Lean/Mathlib dependency)
- Explicit error context on failure (command, stdout, stderr)
- Covers both runtime module imports and CLI script entry points

Note: This is a minimal runnable gate, not a replacement for pytest.
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _python() -> str:
    return sys.executable or "python"


def _run(cmd: list[str], cwd: Path | None = None, timeout_s: int = 30) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or PROJECT_ROOT),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=timeout_s,
        check=False,
    )
    if proc.returncode != 0:
        joined = " ".join(cmd)
        raise AssertionError(
            "\n".join([
                f"  cmd: {joined}",
                f"  rc: {proc.returncode}",
                f"  stdout: {(proc.stdout or '').rstrip()[:500]}",
                f"  stderr: {(proc.stderr or '').rstrip()[:500]}",
            ])
        )
    return proc


failures: list[str] = []


def _check(name: str, fn):
    try:
        fn()
        print(f"  OK: {name}")
    except Exception as exc:
        failures.append(f"{name}: {exc}")
        print(f"  FAIL: {name} -> {exc}")


# ---------------------------------------------------------------------------
# Phase 1: Runtime module imports
# ---------------------------------------------------------------------------

REQUIRED_MODULES = [
    "skill.runtime.proof_tree",
    "skill.runtime.error_classifier",
    "skill.runtime.parallel_runner",
    "skill.runtime.safe_verify",
    "skill.runtime.orchestrator",
    "skill.runtime.config_loader",
    "skill.runtime.workspace_manager",
]


def check_imports():
    for mod_name in REQUIRED_MODULES:
        def _import(m=mod_name):
            importlib.import_module(m)
        _check(f"import {mod_name}", _import)


# ---------------------------------------------------------------------------
# Phase 2: Runtime module functionality
# ---------------------------------------------------------------------------

def check_proof_tree():
    def _test():
        from skill.runtime.proof_tree import ProofSearchTree, NodeStatus
        tree = ProofSearchTree("smoke_test")
        tree.add_node("S1")
        tree.advance("S1", NodeStatus.MAGI_APPROVED)
        data = tree.to_status_json()
        assert data["run_id"] == "smoke_test"
        assert len(data["nodes"]) == 1
    _check("ProofSearchTree round-trip", _test)


def check_error_classifier():
    def _test():
        from skill.runtime.error_classifier import classify
        err = classify("unknown identifier 'foo'", "lean")
        assert err.category is not None
    _check("ErrorClassifier classify", _test)


def check_safe_verify():
    def _test():
        from skill.runtime.safe_verify import scan_forbidden_tokens
        violations = scan_forbidden_tokens("theorem foo : True := by sorry", "test.lean")
        assert any(v.token.value == "sorry" for v in violations)
    _check("SafeVerify scan_forbidden_tokens", _test)


def check_config():
    def _test():
        from skill.runtime.config_loader import load_config
        cfg = load_config()
        assert cfg["skill"]["name"] == "mathprove"
    _check("ConfigLoader", _test)


# ---------------------------------------------------------------------------
# Phase 3: CLI script --help checks
# ---------------------------------------------------------------------------

HELP_CHECK_SCRIPTS = [
    "scripts/verify_sympy.py",
    "scripts/draft_logger.py",
    "scripts/step_router.py",
    "scripts/problem_router.py",
    "scripts/final_audit.py",
]


def check_script_help():
    py = _python()
    for script_rel in HELP_CHECK_SCRIPTS:
        script_path = PROJECT_ROOT / script_rel
        if not script_path.exists():
            # skip if root-level proxy not present
            continue
        def _test(s=str(script_path)):
            _run([py, s, "--help"], timeout_s=20)
        _check(f"--help {script_rel}", _test)


# ---------------------------------------------------------------------------
# Phase 4: Functional smoke (SymPy verify)
# ---------------------------------------------------------------------------

def check_sympy_functional():
    def _test():
        py = _python()
        verify_script = PROJECT_ROOT / "scripts" / "verify_sympy.py"
        if not verify_script.exists():
            # fall back to direct sympy test
            proc = _run(
                [py, "-c", "from sympy import symbols, expand; x = symbols('x'); assert expand((x+1)**2) == x**2+2*x+1; print('ok')"],
                timeout_s=15,
            )
            assert "ok" in proc.stdout
            return
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(
                "import sympy as sp\n"
                "x = sp.Symbol('x')\n"
                "assert sp.expand((x + 1)**2) == x**2 + 2*x + 1\n"
                'print(\'{"ok": true}\')\n'
            )
            code_path = f.name
        try:
            proc = _run(
                [py, str(verify_script), "--code-file", code_path, "--timeout", "10"],
                timeout_s=30,
            )
            data = json.loads(proc.stdout)
            assert data.get("status") == "success"
        finally:
            os.unlink(code_path)
    _check("SymPy functional verify", _test)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    print("[1/5] Runtime module imports")
    check_imports()

    print("[2/5] Runtime module functionality")
    check_proof_tree()
    check_error_classifier()
    check_safe_verify()
    check_config()

    print("[3/5] CLI script --help checks")
    check_script_help()

    print("[4/5] SymPy functional smoke")
    check_sympy_functional()

    print()
    if failures:
        print(f"SMOKE FAILED -- {len(failures)} failure(s):")
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    else:
        print("SMOKE PASSED -- all checks OK")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
