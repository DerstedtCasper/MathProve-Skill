"""验证问题路由器分类逻辑。"""
from MathProve.scripts import problem_router


def test_route_sympy():
    assert problem_router.route_problem("计算积分") in {"sympy", "hybrid"}


def test_route_lean4():
    assert problem_router.route_problem("证明定理") in {"lean4", "hybrid"}


def test_route_hybrid():
    assert problem_router.route_problem("证明并计算") == "hybrid"
