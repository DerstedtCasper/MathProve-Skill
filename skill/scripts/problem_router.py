"""问题级路由器：判断 SymPy/Lean4/混合路线。"""
import argparse
import json
import os

try:
    from .logger import log_event
except ImportError:  # pragma: no cover
    from logger import log_event


SYM_KEYWORDS = [
    "计算",
    "求解",
    "积分",
    "求导",
    "化简",
    "展开",
    "因式分解",
    "矩阵",
]

LEAN_KEYWORDS = [
    "证明",
    "定理",
    "引理",
    "归纳",
    "等价",
    "蕴含",
    "∀",
    "∃",
]


def _hit(text, keywords):
    return any(k in text for k in keywords)


def route_problem(text):
    sym = _hit(text, SYM_KEYWORDS)
    lean = _hit(text, LEAN_KEYWORDS)
    if sym and lean:
        return "hybrid"
    if lean:
        return "lean4"
    if sym:
        return "sympy"
    return "hybrid"


def _truthy(v: str | None) -> bool:
    if v is None:
        return False
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def detect_subagent_capability() -> dict:
    """Best-effort detection for multi-agent / subagent capable runtimes."""
    driver = os.environ.get("MATHPROVE_SUBAGENT_DRIVER") or ""
    enabled = _truthy(os.environ.get("MATHPROVE_SUBAGENT")) or bool(driver)
    for k in ("CODEX_SUBAGENT", "CODEX_SUBAGENTS", "MULTI_AGENT", "SUBAGENT", "SUBAGENTS"):
        enabled = enabled or _truthy(os.environ.get(k))
    return {"enabled": bool(enabled), "driver": driver}


def main():
    parser = argparse.ArgumentParser(description="MathProve 问题路由器")
    parser.add_argument("--text", required=True, help="问题文本")
    parser.add_argument("--log", help="日志路径（JSONL）")
    args = parser.parse_args()

    route = route_problem(args.text)
    cap = detect_subagent_capability()
    execution = "single_agent"
    if cap.get("enabled") and route in {"lean4", "hybrid"}:
        execution = "subagent"

    result = {"route": route, "execution": execution, "subagent": cap, "text": args.text}
    log_event({"event": "problem_route", "route": route}, log_path=args.log)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
