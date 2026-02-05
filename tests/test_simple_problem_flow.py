"""验证简单问题流程与工作区落盘。"""
import importlib.util
import json
import pathlib
import subprocess

import pytest


def _repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[1]


@pytest.mark.skipif(importlib.util.find_spec("sympy") is None, reason="未安装 sympy")
def test_simple_problem_flow(tmp_path):
    run_dir = tmp_path / "run_simple"
    steps_path = run_dir / "plan" / "steps.json"
    steps_path.parent.mkdir(parents=True, exist_ok=True)

    steps = {
        "problem": "验证 (a+b)^2 展开",
        "steps": [
            {
                "id": "S1",
                "goal": "展开 (a+b)^2",
                "checker": {
                    "type": "sympy",
                    "code": "a,b=symbols('a b'); emit({'ok': simplify((a+b)**2-(a**2+2*a*b+b**2))==0})",
                },
            }
        ],
    }
    steps_path.write_text(json.dumps(steps, ensure_ascii=False), encoding="utf-8")

    script_path = _repo_root() / "scripts" / "final_audit.py"
    cmd = [
        "python",
        str(script_path),
        "--run-dir",
        str(run_dir),
        "--steps",
        "plan/steps.json",
        "--solution",
        "Solution.md",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["status"] == "passed"
    assert (run_dir / "audit" / "Solution.md").exists()
    assert (run_dir / "logs" / "tool_calls.log").exists()
