"""问题级路由器：判断 SymPy/Lean4/混合路线。"""
import argparse
import json

try:
    from .logger import log_event
except ImportError:  # pragma: no cover
    from logger import log_event

try:
    from ..runtime.config_loader import load_config
    from ..runtime.routes import apply_subagent_auto_enable
except Exception:  # pragma: no cover - direct script execution
    try:
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from runtime.config_loader import load_config
        from runtime.routes import apply_subagent_auto_enable
    except Exception:  # noqa: BLE001
        load_config = None
        apply_subagent_auto_enable = None

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


def _effective_subagent() -> dict:
    if load_config is None or apply_subagent_auto_enable is None:  # pragma: no cover
        return {"enabled": False, "driver": "", "mode": "none", "capability": {}}
    cfg = load_config()
    effective = apply_subagent_auto_enable(cfg)
    sub = (effective.get("routes") or {}).get("subagent") or {}
    return {
        "enabled": bool(sub.get("enabled")),
        "driver": str(sub.get("driver") or ""),
        "mode": str(sub.get("mode") or "none"),
        "capability": sub.get("capability") or {},
    }


def main():
    parser = argparse.ArgumentParser(description="MathProve 问题路由器")
    parser.add_argument("--text", required=True, help="问题文本")
    parser.add_argument("--log", help="日志路径（JSONL）")
    args = parser.parse_args()

    route = route_problem(args.text)
    sub = _effective_subagent()
    execution = "single_agent"
    if sub.get("enabled") and route in {"lean4", "hybrid"}:
        execution = "subagent"

    result = {"route": route, "execution": execution, "subagent": sub, "text": args.text}
    log_event({"event": "problem_route", "route": route}, log_path=args.log)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
