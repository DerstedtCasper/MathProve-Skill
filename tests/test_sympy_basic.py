"""验证 SymPy 执行脚本的基础功能。"""
import importlib.util
import json
import pathlib
import subprocess

import pytest


@pytest.mark.skipif(importlib.util.find_spec("sympy") is None, reason="未安装 sympy")
def test_verify_sympy_identity():
    code = """
a, b = symbols('a b')
lhs = (a + b) ** 2
rhs = a ** 2 + 2 * a * b + b ** 2
diff = simplify(lhs - rhs)
emit({"verified": diff == 0})
""".strip()
    script_path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "verify_sympy.py"
    cmd = [
        "python",
        str(script_path),
        "--code",
        code,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["status"] == "success"
    assert payload["output"]["verified"] is True
