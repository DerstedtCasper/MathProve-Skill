"""CI/本地烟雾测试入口：验证关键脚本链路可运行。

设计目标：
- 快速（默认 < 10s，避免 CI 变慢）
- 无外部环境依赖（不要求 Lean/Mathlib）
- 失败时给出明确的错误上下文（命令、stdout/stderr）

注意：这是“最小可运行”门禁，不替代 pytest。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _run(cmd: list[str], cwd: Path, timeout_s: int = 30) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=timeout_s,
        check=False,
    )
    if proc.returncode != 0:
        joined = " ".join(cmd)
        raise SystemExit(
            "\n".join(
                [
                    "[smoke] command failed",
                    f"  cmd: {joined}",
                    f"  cwd: {cwd}",
                    f"  rc: {proc.returncode}",
                    "  --- stdout ---",
                    (proc.stdout or "").rstrip(),
                    "  --- stderr ---",
                    (proc.stderr or "").rstrip(),
                ]
            )
        )
    return proc


def _parse_json_from_stdout(stdout: str) -> dict:
    # 兼容脚本输出带缩进或多行：取最后一个可解析 JSON 的非空行
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    # 如果整段是 JSON（例如 indent=2），尝试整体解析
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:  # pragma: no cover
        raise SystemExit(f"[smoke] cannot parse json from stdout: {e}\n{stdout}") from e


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _python() -> str:
    return sys.executable or "python"


def _script(path_under_repo: str) -> Path:
    return _repo_root() / path_under_repo


def _help_checks() -> None:
    repo = _repo_root()
    py = _python()
    # 同时验证：
    # - 仓库根 `scripts/` 兼容入口
    # - 标准 Skill 入口 `skill/scripts/`
    variants = [
        "scripts",
        "skill/scripts",
    ]
    names = [
        "verify_sympy.py",
        "draft_logger.py",
        "step_router.py",
        "problem_router.py",
        "final_audit.py",
    ]
    for v in variants:
        for n in names:
            _run([py, str(_script(f"{v}/{n}")), "--help"], cwd=repo, timeout_s=20)


def _smoke_problem_router(script_rel: str) -> None:
    repo = _repo_root()
    py = _python()
    proc = _run(
        [py, str(_script(script_rel)), "--text", "证明并计算 (x+1)^2"],
        cwd=repo,
        timeout_s=20,
    )
    data = _parse_json_from_stdout(proc.stdout)
    if data.get("route") not in {"sympy", "lean4", "hybrid"}:
        raise SystemExit(f"[smoke] problem_router unexpected route: {data!r}")


def _smoke_step_router(tmp: Path, script_rel: str) -> None:
    repo = _repo_root()
    py = _python()
    inp = tmp / "steps.json"
    payload = {"problem": "smoke", "steps": [{"id": "S1", "goal": "计算 (a+b)^2 的展开"}]}
    inp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    proc = _run(
        [py, str(_script(script_rel)), "--input", str(inp), "--explain"],
        cwd=repo,
        timeout_s=20,
    )
    data = _parse_json_from_stdout(proc.stdout)
    steps = data.get("steps") or []
    if not steps or steps[0].get("route") not in {"sympy", "lean4", "hybrid"}:
        raise SystemExit(f"[smoke] step_router unexpected output: {data!r}")


def _smoke_verify_sympy(tmp: Path, script_rel: str) -> None:
    repo = _repo_root()
    py = _python()
    code_path = tmp / "check.py"
    code_path.write_text(
        "\n".join(
            [
                "import sympy as sp",
                "x = sp.Symbol('x')",
                "assert sp.expand((x + 1)**2) == x**2 + 2*x + 1",
                "print('{\"ok\": true}')",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    proc = _run(
        [py, str(_script(script_rel)), "--code-file", str(code_path), "--timeout", "10"],
        cwd=repo,
        timeout_s=30,
    )
    data = json.loads(proc.stdout)
    if data.get("status") != "success":
        raise SystemExit(f"[smoke] verify_sympy failed: {data!r}")


def _smoke_draft_logger(tmp: Path, script_rel: str) -> None:
    repo = _repo_root()
    py = _python()
    draft = tmp / "draft.md"
    step = {
        "id": "S1",
        "goal": "展开 (x+1)^2",
        "difficulty": "easy",
        "route": "sympy",
        "status": "passed",
        "evidence": "smoke",
        "notes": "smoke",
    }
    proc = _run(
        [
            py,
            str(_script(script_rel)),
            "--draft",
            str(draft),
            "--step-json",
            json.dumps(step, ensure_ascii=False),
        ],
        cwd=repo,
        timeout_s=20,
    )
    _ = _parse_json_from_stdout(proc.stdout)
    if not draft.exists() or "### S1" not in draft.read_text(encoding="utf-8", errors="replace"):
        raise SystemExit("[smoke] draft_logger did not write expected content")


def _smoke_final_audit(tmp: Path, script_rel: str) -> None:
    repo = _repo_root()
    py = _python()
    steps_path = tmp / "steps.json"
    solution_path = tmp / "Solution.md"
    steps_payload = {
        "problem": "smoke: expand identity",
        "steps": [
            {
                "id": "S1",
                "goal": "展开并验证 (x+1)^2",
                "checker": {
                    "type": "sympy",
                    "code": "\n".join(
                        [
                            "import sympy as sp",
                            "x = sp.Symbol('x')",
                            "assert sp.expand((x + 1)**2) == x**2 + 2*x + 1",
                            "print('ok')",
                        ]
                    ),
                },
            }
        ],
    }
    steps_path.write_text(json.dumps(steps_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    _run(
        [
            py,
            str(_script(script_rel)),
            "--steps",
            str(steps_path),
            "--solution",
            str(solution_path),
            "--timeout",
            "10",
        ],
        cwd=repo,
        timeout_s=60,
    )
    if not solution_path.exists() or solution_path.stat().st_size == 0:
        raise SystemExit("[smoke] final_audit did not generate Solution.md")


def main() -> None:
    # 让 CI 输出更稳定（避免本地环境影响）
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    _help_checks()
    for script_rel in ("scripts/problem_router.py", "skill/scripts/problem_router.py"):
        _smoke_problem_router(script_rel)

    with tempfile.TemporaryDirectory(prefix="mathprove_smoke_") as td:
        tmp = Path(td)
        for script_rel in ("scripts/step_router.py", "skill/scripts/step_router.py"):
            _smoke_step_router(tmp, script_rel)
        for script_rel in ("scripts/verify_sympy.py", "skill/scripts/verify_sympy.py"):
            _smoke_verify_sympy(tmp, script_rel)
        for script_rel in ("scripts/draft_logger.py", "skill/scripts/draft_logger.py"):
            _smoke_draft_logger(tmp, script_rel)
        for script_rel in ("scripts/final_audit.py", "skill/scripts/final_audit.py"):
            _smoke_final_audit(tmp, script_rel)

    print("[smoke] ok")


if __name__ == "__main__":
    main()
