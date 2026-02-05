"""对草稿步骤进行最终复核并生成正式稿。

核心目标：
- 每个 step 都必须通过工具校验（SymPy / Lean4）。
- 可选：对 Lean4 步骤生成 reverse gate 文件，并执行 lint + lake env lean 编译校验。
- 通过后生成/更新 Solution.md（正式稿）。
"""

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Any

try:
    from .logger import log_event
except ImportError:  # pragma: no cover
    from logger import log_event

try:
    from .runtime_paths import assets_dir, skill_root
except ImportError:  # pragma: no cover
    from runtime_paths import assets_dir, skill_root

try:
    from ..runtime.workspace_manager import ensure_run_dir, run_path
except Exception:  # pragma: no cover
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from runtime.workspace_manager import ensure_run_dir, run_path
_BASE_DIR = skill_root()
if str(_BASE_DIR) not in sys.path:
    sys.path.append(str(_BASE_DIR))
try:  # optional SkillMP runtime
    from runtime.workspace import EphemeralWorkspace
except Exception:  # noqa: BLE001
    EphemeralWorkspace = None


_STEP_ID_RE = re.compile(r"^S(\d+)$")
_STEP_DECL_RE = re.compile(r"(?m)^\s*(?:theorem|lemma)\s+(S\d+)(?!\d)(?![A-Za-z0-9_'])")
_FORBIDDEN_LEAN_DECL_RE = re.compile(r"(?m)^\s*(axiom|constant|opaque)\b")
_FORBIDDEN_LEAN_WORD_RE = re.compile(r"(?<![A-Za-z0-9_])(?:sorry|admit)(?![A-Za-z0-9_])")


def _strip_lean_comments(text: str) -> str:
    # Best-effort removal of Lean comments for static linting.
    text = re.sub(r"/-.*?-/", "", text, flags=re.S)
    text = re.sub(r"(?m)--.*$", "", text)
    return text


def _lean_static_precheck(step: dict, checker: dict) -> tuple[bool, dict]:
    """Fast, environment-independent checks for Lean step integrity.

    We do this before running Lean tooling so we can fail fast on forbidden
    constructs (axiom/constant/opaque/sorry/admit) and enforce traceability
    (`theorem/lemma Sx` must exist for step Sx).
    """

    sid = str(step.get("id") or "").strip()
    cmds = checker.get("cmds")
    if not cmds and checker.get("cmd"):
        cmds = [checker.get("cmd")]
    if not cmds and checker.get("code"):
        snippet = str(checker.get("code"))
        cmds = [ln for ln in snippet.splitlines() if ln.strip()]
    if not cmds:
        return False, {"error": "Lean4 检查缺少 cmds/cmd/code（静态预检失败）"}

    joined = "\n".join(str(x) for x in cmds)
    no_comments = _strip_lean_comments(joined)

    if _FORBIDDEN_LEAN_DECL_RE.search(no_comments) or _FORBIDDEN_LEAN_WORD_RE.search(no_comments):
        return False, {
            "error": "Lean4 代码包含禁止关键字（axiom/constant/opaque/sorry/admit），拒绝继续审计",
        }

    # Traceability: for canonical step IDs, require a matching theorem/lemma name.
    if _STEP_ID_RE.match(sid):
        decls = {m.group(1) for m in _STEP_DECL_RE.finditer(joined)}
        if sid not in decls:
            return False, {
                "error": f"Lean4 step {sid} 的代码必须包含 `theorem/lemma {sid}` 声明（便于映射与反向门禁）",
                "found_decls": sorted(decls),
            }

    return True, {"status": "ok"}


def _read_json(path: str) -> dict:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def _run_python(script_path: str, args: list[str], timeout: int = 20, python_path: str | None = None):
    cmd = [python_path or sys.executable or "python", script_path] + args
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _run_sympy(checker: dict, sympy_runner: str, timeout: int, python_path: str | None = None):
    code = checker.get("code")
    code_file = checker.get("code_file")
    if not code and not code_file:
        return False, {"error": "SymPy 检查缺少 code 或 code_file"}

    args = ["--timeout", str(timeout)]
    if code:
        args += ["--code", str(code)]
    else:
        args += ["--code-file", str(code_file)]

    code_rc, out, err = _run_python(sympy_runner, args, timeout=timeout + 5, python_path=python_path)
    if code_rc != 0:
        return False, {"error": "SymPy 执行失败", "stderr": err, "stdout": out}
    try:
        return True, json.loads(out)
    except json.JSONDecodeError:
        return False, {"error": "SymPy 输出解析失败", "stdout": out}


def _run_lean(
    checker: dict,
    lean_runner: str,
    timeout: int,
    python_path: str | None = None,
    default_mode: str | None = None,
    default_cwd: str | None = None,
):
    cmds = checker.get("cmds")
    if not cmds and checker.get("cmd"):
        cmds = [checker.get("cmd")]
    if not cmds and checker.get("code"):
        # Back-compat: allow `code` as a newline-separated Lean snippet.
        snippet = str(checker.get("code"))
        cmds = [ln for ln in snippet.splitlines() if ln.strip()]
    if not cmds:
        return False, {"error": "Lean4 检查缺少 cmds/cmd/code"}

    payload = json.dumps({"cmds": cmds}, ensure_ascii=False)
    args = ["--payload", payload, "--timeout", str(timeout)]

    mode = checker.get("mode") or default_mode
    if mode:
        args += ["--mode", str(mode)]

    file_cmd = checker.get("file_cmd")
    if file_cmd:
        args += ["--file-cmd", str(file_cmd)]

    repl_cmd = checker.get("repl_cmd")
    if repl_cmd:
        args += ["--repl-cmd", str(repl_cmd)]

    lean_path = checker.get("lean_path")
    if lean_path:
        args += ["--lean-path", str(lean_path)]

    lake_path = checker.get("lake_path")
    if lake_path:
        args += ["--lake-path", str(lake_path)]

    cwd = checker.get("cwd") or default_cwd
    if cwd:
        args += ["--cwd", str(cwd)]

    watchdog_timeout = checker.get("watchdog_timeout") or getattr(args, "lean_watchdog_timeout", 0) or 0
    if int(watchdog_timeout) > 0:
        args += ["--watchdog-timeout", str(int(watchdog_timeout))]

    code_rc, out, err = _run_python(lean_runner, args, timeout=timeout + 5, python_path=python_path)
    if code_rc != 0:
        return False, {"error": "Lean4 执行失败", "stderr": err, "stdout": out}
    try:
        result = json.loads(out)
    except json.JSONDecodeError:
        return False, {"error": "Lean4 输出解析失败", "stdout": out}
    if result.get("status") != "success":
        return False, result

    # Heuristic "passed": last command has no goals and no sorries.
    outputs = result.get("outputs", [])
    if outputs:
        last = outputs[-1]
        goals = last.get("goals")
        sorries = last.get("sorries")
        if goals == [] and (sorries == [] or sorries is None):
            return True, result
    return True, result


def _audit_steps(steps: list[dict], sympy_runner: str, lean_runner: str, timeout: int, args) -> tuple[bool, list[dict]]:
    report: list[dict] = []
    all_passed = True

    for step in steps:
        checker = step.get("checker") or {}
        ctype = checker.get("type") or step.get("route") or step.get("engine") or "unknown"
        result: dict[str, Any] = {"id": step.get("id"), "status": "failed"}

        if ctype == "sympy":
            python_path = checker.get("python") or args.sympy_python or args.python
            step_timeout = int(checker.get("timeout") or timeout)
            retries = int(checker.get("retries", 0) or 0)
            attempts = 0
            ok = False
            data: Any = None

            while attempts <= retries:
                attempts += 1
                ok, data = _run_sympy(checker, sympy_runner, step_timeout, python_path=python_path)
                log_event(
                    {
                        "event": "final_audit_sympy",
                        "id": step.get("id"),
                        "attempt": attempts,
                        "status": "passed" if ok else "failed",
                    },
                    log_path=args.log,
                )
                if ok:
                    break

            result["status"] = "passed" if ok else "failed"
            result["detail"] = data
            result["attempts"] = attempts

        elif ctype == "lean4":
            python_path = checker.get("python") or args.lean_python or args.python
            step_timeout = int(checker.get("timeout") or args.lean_timeout or timeout)
            retries = int(checker.get("retries", 0) or 0)
            attempts = 0
            ok = False
            data = None

            static_ok, static_detail = _lean_static_precheck(step, checker)
            if not static_ok:
                ok = False
                data = {"static_lint": static_detail}
                log_event(
                    {
                        "event": "final_audit_lean4_static_lint",
                        "id": step.get("id"),
                        "status": "failed",
                        "detail": static_detail,
                    },
                    log_path=args.log,
                )
            else:
                while attempts <= retries:
                    attempts += 1
                    ok, data = _run_lean(
                        checker,
                        lean_runner,
                        step_timeout,
                        python_path=python_path,
                        default_mode=args.lean_mode,
                        default_cwd=args.lean_cwd,
                    )
                    log_event(
                        {
                            "event": "final_audit_lean4",
                            "id": step.get("id"),
                            "attempt": attempts,
                            "status": "passed" if ok else "failed",
                        },
                        log_path=args.log,
                    )
                    if ok:
                        break

            result["status"] = "passed" if ok else "failed"
            result["detail"] = data
            result["attempts"] = attempts

        else:
            result["detail"] = {"error": f"不支持的 checker 类型: {ctype}"}
            all_passed = False

        if result["status"] != "passed":
            all_passed = False
        report.append(result)

    return all_passed, report


def _load_template(path: pathlib.Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _render_steps_section(steps: list[dict], report: list[dict]) -> str:
    status_by_id = {r.get("id"): r.get("status") for r in report}
    lines: list[str] = []

    for step in steps:
        sid = step.get("id", "S?")
        lines.append(f"### {sid}")
        lines.append(f"- 目标：{step.get('goal', '')}")
        lines.append(f"- 难度：{step.get('difficulty', '')}")
        lines.append(f"- 路线：{step.get('route', '')}")
        lines.append(f"- 状态：{status_by_id.get(sid, 'unknown')}")
        evidence_path = str(step.get('evidence_path') or '').strip()
        evidence_digest = str(step.get('evidence_digest') or '').strip()
        legacy_evidence = str(step.get('evidence') or '').strip()
        if evidence_path:
            lines.append(f"- ??: {evidence_path}")
        elif evidence_digest:
            lines.append(f"- ??: {evidence_digest}")
        else:
            lines.append(f"- ??: {legacy_evidence}")

        symbols = step.get("symbols") or []
        if isinstance(symbols, list) and symbols:
            lines.append("- 符号：")
            for s in symbols:
                if isinstance(s, dict):
                    name = str(s.get("name") or "").strip()
                    meaning = str(s.get("meaning") or "").strip()
                    if name or meaning:
                        lines.append(f"  - {name}：{meaning}")
                elif isinstance(s, str) and s.strip():
                    lines.append(f"  - {s.strip()}")

        assumptions = step.get("assumptions") or []
        if isinstance(assumptions, list) and assumptions:
            lines.append("- 假设：")
            for a in assumptions:
                if isinstance(a, str) and a.strip():
                    lines.append(f"  - {a.strip()}")

        lemmas = step.get("lemmas") or []
        if isinstance(lemmas, list) and lemmas:
            lines.append("- 引理/定理：")
            for l in lemmas:
                if isinstance(l, str) and l.strip():
                    lines.append(f"  - {l.strip()}")

        explanation = str(step.get("explanation") or "").strip()
        if explanation:
            lines.append("- 讲解：")
            for ln in explanation.splitlines():
                lines.append(f"  {ln}".rstrip())

        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _render_solution(problem: str | None, steps: list[dict], report: list[dict], audit_status: str, audit_report: str) -> str:
    proof_tpl = assets_dir() / "proof_template.md"
    tpl_path = proof_tpl if proof_tpl.exists() else (assets_dir() / "templates" / "solution_template.md")
    tpl = _load_template(tpl_path)
    if not tpl:
        # Fallback: minimal output.
        lines = ["# MathProve 正式稿", "", "## 问题", f"- {problem or '未提供'}", ""]
        lines.append(_render_steps_section(steps, report))
        lines.append("## 最终一致性检查（Audit）")
        lines.append(f"- 状态：{audit_status}")
        lines.append(f"- 说明：{audit_report}")
        return "\n".join(lines).strip() + "\n"

    steps_section = _render_steps_section(steps, report)
    out = tpl.replace("{{STEPS_SECTION}}", steps_section)
    out = out.replace("{{PROBLEM}}", problem or "未提供")
    out = out.replace("{{AUDIT_STATUS}}", audit_status)
    out = out.replace("{{AUDIT_REPORT}}", audit_report)
    return out.strip() + "\n"


def _extract_step_num(step_id: str) -> int | None:
    m = _STEP_ID_RE.match(step_id.strip())
    if not m:
        return None
    return int(m.group(1))


def _generate_reverse_gate_file(steps: list[dict], out_path: pathlib.Path, template_path: pathlib.Path) -> tuple[bool, str]:
    """Generate a single Lean file for reverse gating. Return (ok, message)."""
    tpl = _load_template(template_path)
    if not tpl:
        return False, f"缺少 reverse gate 模板: {template_path}"

    template_lines = tpl.splitlines()

    try:
        i_map = next(i for i, ln in enumerate(template_lines) if "RIGOR_STEP_MAP" in ln)
    except StopIteration:
        return False, "reverse gate 模板缺少 '-- RIGOR_STEP_MAP' 标记"

    # Replace the placeholder map lines right after the header.
    out_lines = template_lines[: i_map + 1]
    for step in steps:
        sid = str(step.get("id") or "").strip()
        n = _extract_step_num(sid)
        if n is None:
            return False, f"reverse gate 要求 step id 形如 S1/S2/...，当前: {sid!r}"
        goal = str(step.get("goal") or "").strip()
        out_lines.append(f"-- S{n}: {goal}")

    j = i_map + 1
    while j < len(template_lines) and re.match(r"^\s*--\s*S\d+\s*:", template_lines[j]):
        j += 1
    out_lines.extend(template_lines[j:])

    # Insert step code blocks before `end MathProve`.
    try:
        i_end = next(i for i, ln in enumerate(out_lines) if re.match(r"^\s*end\s+MathProve\b", ln))
    except StopIteration:
        return False, "reverse gate 模板缺少 'end MathProve'"

    extra_imports: set[str] = set()
    inserts: list[str] = []
    for step in steps:
        checker = step.get("checker") or {}
        ctype = checker.get("type") or step.get("route") or "unknown"
        sid = str(step.get("id") or "S?").strip()
        goal = str(step.get("goal") or "").strip()

        inserts.append("")
        inserts.append(f"-- STEP {sid}: {goal}")

        if ctype != "lean4":
            inserts.append("-- (non-Lean step; verified elsewhere)")
            continue

        # Lean code lines: prefer cmds; fall back to code/cmd.
        cmds = checker.get("cmds")
        if not cmds and checker.get("cmd"):
            cmds = [checker.get("cmd")]
        if not cmds and checker.get("code"):
            snippet = str(checker.get("code"))
            cmds = [ln for ln in snippet.splitlines() if ln.strip()]
        if not cmds:
            return False, f"Lean step {sid} 缺少 checker.cmds/cmd/code，无法生成 reverse gate"

        # Precheck: require theorem/lemma name matches the step id.
        raw_lines = [str(x) for x in cmds]
        joined = "\n".join(raw_lines)
        decls = {m.group(1) for m in _STEP_DECL_RE.finditer(joined)}
        if sid not in decls:
            return False, f"Lean step {sid} 的代码必须包含 'theorem/lemma {sid}' 声明（用于 lint 与可追溯映射）"

        # Hoist `import ...` lines to the file header (Lean requires imports at the top).
        code_lines: list[str] = []
        for ln in raw_lines:
            if re.match(r"^\s*import\s+", ln):
                extra_imports.add(ln.strip())
                continue
            code_lines.append(ln)

        # Attach talk-friendly metadata as comments.
        symbols = step.get("symbols") or []
        if isinstance(symbols, list) and symbols:
            inserts.append("-- Symbols:")
            for s in symbols:
                if isinstance(s, dict):
                    name = str(s.get("name") or "").strip()
                    meaning = str(s.get("meaning") or "").strip()
                    if name or meaning:
                        inserts.append(f"--   - {name}: {meaning}")
                elif isinstance(s, str) and s.strip():
                    inserts.append(f"--   - {s.strip()}")

        assumptions = step.get("assumptions") or []
        if isinstance(assumptions, list) and assumptions:
            inserts.append("-- Assumptions:")
            for a in assumptions:
                if isinstance(a, str) and a.strip():
                    inserts.append(f"--   - {a.strip()}")

        explanation = str(step.get("explanation") or "").strip()
        if explanation:
            inserts.append("-- Explanation:")
            for ln in explanation.splitlines():
                inserts.append(f"--   {ln}".rstrip())

        inserts.append("")  # separate comments from code
        inserts.extend(code_lines)

    # Insert hoisted imports right after the template's import block.
    if extra_imports:
        try:
            i_imp = next(i for i, ln in enumerate(out_lines) if ln.strip().startswith("import "))
            j_imp = i_imp
            while j_imp < len(out_lines) and out_lines[j_imp].strip().startswith("import "):
                j_imp += 1
            existing_imports = {ln.strip() for ln in out_lines[i_imp:j_imp] if ln.strip().startswith("import ")}
            to_add = sorted([imp for imp in extra_imports if imp not in existing_imports and imp != "import Mathlib"])
            if to_add:
                out_lines[j_imp:j_imp] = to_add + [""]
        except StopIteration:
            # If the template has no import line, we still proceed; lint will fail if Mathlib is required.
            pass

    out_lines[i_end:i_end] = inserts
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out_lines).rstrip() + "\n", encoding="utf-8")
    return True, f"reverse gate 文件已生成: {out_path}"


def _run_reverse_gate(args, gate_path: pathlib.Path) -> tuple[bool, dict]:
    ps1 = pathlib.Path(__file__).resolve().parent / "check_reverse_lean4.ps1"
    if not ps1.exists():
        return False, {"error": f"缺少脚本: {ps1}"}

    if not args.lean_cwd:
        return False, {"error": "启用 --lean-gate 需要同时提供 --lean-cwd（Lake/Mathlib 工程目录）"}

    project_dir = args.lean_cwd
    if getattr(args, "_ephemeral_project", None):
        project_dir = args._ephemeral_project
        try:
            temp_gate = pathlib.Path(project_dir) / gate_path.name
            temp_gate.write_text(gate_path.read_text(encoding="utf-8"), encoding="utf-8")
            gate_path = temp_gate
        except Exception as exc:  # noqa: BLE001
            return False, {"error": "reverse gate 复制到临时工程失败", "detail": str(exc)}

    cmd = [
        "powershell",
        "-File",
        str(ps1),
        "-Path",
        str(gate_path),
        "-ProjectDir",
        str(project_dir),
        "-TimeoutSec",
        str(max(int(args.lean_gate_timeout or 0), int(args.lean_timeout or 0), int(args.timeout) + 10)),
        "-Python",
        str(args.python or sys.executable or "python"),
        "-RequireStepMap",
    ]
    if int(getattr(args, "lean_watchdog_timeout", 0) or 0) > 0:
        cmd += ["-NoOutputTimeoutSec", str(int(args.lean_watchdog_timeout))]
    if not args.lean_gate_no_mathlib:
        cmd.append("-RequireMathlib")
    if args.lean_gate_skip_lint:
        cmd.append("-SkipLint")

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return False, {"error": "reverse gate 失败", "stderr": proc.stderr, "stdout": proc.stdout}
    try:
        return True, json.loads(proc.stdout) if proc.stdout.strip() else {"status": "passed"}
    except json.JSONDecodeError:
        return True, {"status": "passed", "stdout": proc.stdout}


def main() -> None:
    parser = argparse.ArgumentParser(description="MathProve 最终复核")
    parser.add_argument("--steps", required=True, help="步骤 JSON 文件")
    parser.add_argument("--solution", default="Solution.md", help="正式稿路径")
    parser.add_argument(
        "--sympy-runner",
        default=str(pathlib.Path(__file__).resolve().parent / "verify_sympy.py"),
        help="SymPy 执行脚本",
    )
    parser.add_argument(
        "--lean-runner",
        default=str(pathlib.Path(__file__).resolve().parent / "lean_repl_client.py"),
        help="Lean4 执行脚本",
    )
    parser.add_argument("--timeout", type=int, default=15, help="默认单步超时（SymPy；Lean4 可用 --lean-timeout 覆盖）")
    parser.add_argument("--lean-timeout", type=int, default=60, help="Lean4 单步默认超时（可被 step.checker.timeout 覆盖）")
    parser.add_argument("--python", help="默认 Python 路径（SymPy/Lean4/辅助脚本）")
    parser.add_argument("--sympy-python", help="SymPy 运行的 Python 路径（执行脚本解释器）")
    parser.add_argument("--lean-python", help="Lean4 客户端运行的 Python 路径（执行脚本解释器）")
    parser.add_argument("--lean-mode", choices=["repl", "file", "auto"], help="Lean4 默认执行模式")
    parser.add_argument("--lean-cwd", help="Lean4 默认工作目录（推荐：Lake+Mathlib 工程）")
    parser.add_argument("--lean-ephemeral", action="store_true", help="Lean4 执行使用临时工作区（反污染）")
    parser.add_argument("--lean-watchdog-timeout", type=int, default=0, help="Lean4 文件模式无输出超时秒数")
    parser.add_argument("--run-dir", help="运行目录（工作区内）")
    parser.add_argument("--workspace-dir", help="工作区根目录（缺省则使用配置/默认值）")
    parser.add_argument("--log", help="日志路径（JSONL）")

    # Reverse gate (Lean4 strict gate).
    parser.add_argument("--lean-gate", action="store_true", help="启用 reverse Lean4 gate（lint + 编译）")
    parser.add_argument("--lean-gate-out", default="", help="reverse gate 输出 .lean 文件路径（默认放到 Solution 同目录）")
    parser.add_argument(
        "--lean-gate-template",
        default=str(assets_dir() / "lean" / "reverse_template_mathlib.lean"),
        help="reverse gate Lean 模板路径",
    )
    parser.add_argument("--lean-gate-timeout", type=int, default=0, help="reverse gate 超时秒数（默认使用 timeout+10）")
    parser.add_argument("--lean-gate-skip-lint", action="store_true", help="reverse gate 跳过 lint（不推荐）")
    parser.add_argument("--lean-gate-no-mathlib", action="store_true", help="reverse gate 不使用 Lake+Mathlib（不推荐）")

    args = parser.parse_args()

    run_dir = ensure_run_dir(args.run_dir, args.workspace_dir)
    if not args.log:
        args.log = str(run_path(run_dir, "logs/tool_calls.log"))

    steps_path = pathlib.Path(args.steps)
    if not steps_path.is_absolute():
        steps_path = run_path(run_dir, args.steps)
    args.steps = str(steps_path)

    solution_path = pathlib.Path(args.solution)
    if not solution_path.is_absolute():
        if args.solution == "Solution.md":
            solution_path = run_path(run_dir, "audit/Solution.md")
        else:
            solution_path = run_path(run_dir, args.solution)
    args.solution = str(solution_path)

    payload = _read_json(args.steps)
    steps = payload.get("steps") or []
    problem = payload.get("problem")

    ctx = None
    try:
        use_ephemeral = bool(args.lean_ephemeral) or os.environ.get("MATHPROVE_EPHEMERAL") == "1"
        if use_ephemeral and args.lean_cwd and EphemeralWorkspace:
            ctx = EphemeralWorkspace(args.lean_cwd)
            args._ephemeral_project = ctx.__enter__()
            args.lean_cwd = args._ephemeral_project

        all_passed, report = _audit_steps(steps, args.sympy_runner, args.lean_runner, args.timeout, args)

        gate_result: dict[str, Any] = {"enabled": bool(args.lean_gate), "status": "skipped"}
        if args.lean_gate:
            # If any Lean steps exist, generate gate file and run it.
            has_lean = any(((s.get("checker") or {}).get("type") == "lean4") for s in steps)
            if has_lean:
                sol_path = pathlib.Path(args.solution)
                gate_path = pathlib.Path(args.lean_gate_out) if args.lean_gate_out else (sol_path.parent / "reverse_gate.lean")
                tpl_path = pathlib.Path(args.lean_gate_template)
                ok, msg = _generate_reverse_gate_file(steps, gate_path, tpl_path)
                gate_result["generate"] = {"ok": ok, "message": msg, "path": str(gate_path)}
                if ok:
                    ok2, detail = _run_reverse_gate(args, gate_path)
                    gate_result["status"] = "passed" if ok2 else "failed"
                    gate_result["detail"] = detail
                    log_event(
                        {"event": "final_audit_reverse_gate", "status": gate_result["status"], "path": str(gate_path)},
                        log_path=args.log,
                    )
                    if not ok2:
                        all_passed = False
                else:
                    gate_result["status"] = "failed"
                    all_passed = False
            else:
                gate_result["status"] = "skipped"
                gate_result["detail"] = {"info": "steps 中未发现 lean4 checker，跳过 reverse gate"}

        failed_steps = [r.get("id") for r in report if r.get("status") != "passed"]
        audit_status = "passed" if all_passed else "failed"
        audit_report_parts = []
        audit_report_parts.append(f"steps: {len(report) - len(failed_steps)}/{len(report)} passed")
        if failed_steps:
            audit_report_parts.append(f"failed: {', '.join(str(x) for x in failed_steps)}")
        if args.lean_gate:
            audit_report_parts.append(f"reverse_gate: {gate_result.get('status')}")
        audit_report = "; ".join(audit_report_parts)

        output = {
            "status": audit_status,
            "report": report,
            "reverse_gate": gate_result,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))

        if audit_status == "passed":
            pathlib.Path(args.solution).write_text(
                _render_solution(problem, steps, report, audit_status=audit_status, audit_report=audit_report),
                encoding="utf-8",
            )
    finally:
        if ctx:
            ctx.__exit__(None, None, None)


if __name__ == "__main__":
    main()
