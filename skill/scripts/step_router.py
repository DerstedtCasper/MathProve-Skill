"""为步骤评估难度并推荐 SymPy/Lean4 路线。"""
import argparse
import json
import pathlib

try:
    from .logger import log_event
except ImportError:  # pragma: no cover
    from logger import log_event


SYMPY_KEYWORDS = [
    "计算",
    "求导",
    "积分",
    "化简",
    "展开",
    "因式分解",
    "解方程",
    "矩阵",
    "simplify",
    "diff",
    "integrate",
    "solve",
]

LEAN_KEYWORDS = [
    "证明",
    "引理",
    "定理",
    "归纳",
    "等价",
    "蕴含",
    "∀",
    "∃",
    "forall",
    "exists",
    "lemma",
    "theorem",
]

HARD_KEYWORDS = [
    "收敛",
    "极限",
    "拓扑",
    "群",
    "环",
    "域",
    "测度",
    "σ",
    "无穷",
    "序列",
    "级数",
]


def _has_any(text, keywords):
    return any(k in text for k in keywords)


def infer_difficulty(goal):
    if _has_any(goal, HARD_KEYWORDS):
        return "hard"
    if _has_any(goal, LEAN_KEYWORDS):
        return "medium"
    if _has_any(goal, SYMPY_KEYWORDS):
        return "easy"
    if len(goal) > 80:
        return "hard"
    return "medium"


def infer_route(goal, difficulty):
    sympy_hit = _has_any(goal, SYMPY_KEYWORDS)
    lean_hit = _has_any(goal, LEAN_KEYWORDS) or difficulty == "hard"
    if sympy_hit and not lean_hit:
        return "sympy"
    if lean_hit and not sympy_hit:
        return "lean4"
    if lean_hit and sympy_hit:
        return "hybrid"
    return "lean4" if difficulty == "hard" else "hybrid"


def route_steps(payload, explain=False):
    for step in payload.get("steps", []):
        goal = step.get("goal", "")
        if not step.get("difficulty"):
            step["difficulty"] = infer_difficulty(goal)
        if not step.get("route"):
            step["route"] = infer_route(goal, step["difficulty"])
        if explain:
            step["route_reason"] = {
                "sympy_hint": _has_any(goal, SYMPY_KEYWORDS),
                "lean_hint": _has_any(goal, LEAN_KEYWORDS),
                "hard_hint": _has_any(goal, HARD_KEYWORDS),
            }
    return payload


def main():
    parser = argparse.ArgumentParser(description="步骤难度评估与路线推荐")
    parser.add_argument("--input", required=True, help="步骤 JSON 文件")
    parser.add_argument("--output", help="输出 JSON 文件（默认 stdout）")
    parser.add_argument("--explain", action="store_true", help="输出路线依据")
    parser.add_argument("--log", help="日志路径（JSONL）")
    args = parser.parse_args()

    data = json.loads(pathlib.Path(args.input).read_text(encoding="utf-8"))
    result = route_steps(data, explain=args.explain)
    log_event({"event": "route_steps", "count": len(result.get("steps", []))}, log_path=args.log)

    if args.output:
        pathlib.Path(args.output).write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
