"""验证步骤路由与难度评估规则。"""
from MathProve.scripts import step_router


def test_route_sympy_easy():
    payload = {"steps": [{"id": "S1", "goal": "计算 (a+b)^2 的展开"}]}
    result = step_router.route_steps(payload, explain=True)
    step = result["steps"][0]
    assert step["difficulty"] == "easy"
    assert step["route"] in {"sympy", "hybrid"}


def test_route_lean_hard():
    payload = {"steps": [{"id": "S2", "goal": "证明级数收敛性"}]}
    result = step_router.route_steps(payload, explain=True)
    step = result["steps"][0]
    assert step["difficulty"] == "hard"
    assert step["route"] in {"lean4", "hybrid"}
