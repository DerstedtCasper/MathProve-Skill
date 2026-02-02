"""验证最终复核与 Solution 生成。"""
import importlib.util
import json
import pathlib
import subprocess
import tempfile

import pytest


@pytest.mark.skipif(importlib.util.find_spec("sympy") is None, reason="未安装 sympy")
def test_final_audit_generates_solution():
    with tempfile.TemporaryDirectory() as temp_dir:
        steps_path = pathlib.Path(temp_dir) / "steps.json"
        solution_path = pathlib.Path(temp_dir) / "Solution.md"
        steps = {
            "problem": "验证恒等式",
            "steps": [
                {
                    "id": "S1",
                    "goal": "验证 (a+b)^2 展开",
                    "checker": {
                        "type": "sympy",
                        "code": "a,b=symbols('a b'); emit({'ok': simplify((a+b)**2-(a**2+2*a*b+b**2))==0})",
                    },
                }
            ],
        }
        steps_path.write_text(json.dumps(steps, ensure_ascii=False), encoding="utf-8")
        script_path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "final_audit.py"
        cmd = [
            "python",
            str(script_path),
            "--steps",
            str(steps_path),
            "--solution",
            str(solution_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        assert proc.returncode == 0
        result = json.loads(proc.stdout)
        assert result["status"] == "passed"
        assert solution_path.exists()
