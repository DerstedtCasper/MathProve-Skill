"""Generate a Math MAGI plan and draft steps.json."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

try:
    from .logger import log_event
    from .runtime_paths import logs_dir, subagent_tasks_dir
except ImportError:  # pragma: no cover
    from logger import log_event
    from runtime_paths import logs_dir, subagent_tasks_dir

try:
    from ..runtime.workspace_manager import ensure_run_dir, run_path
except Exception:  # pragma: no cover
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from runtime.workspace_manager import ensure_run_dir, run_path
try:
    from ..runtime.config_loader import load_config
    from ..runtime.routes import apply_subagent_auto_enable
    from ..runtime.magi import run_round, collect_votes, revise_plan
    from ..runtime.magi import emit_jsonl, emit_md_summary
except Exception:  # pragma: no cover - direct script execution
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from runtime.config_loader import load_config
    from runtime.routes import apply_subagent_auto_enable
    from runtime.magi import run_round, collect_votes, revise_plan
    from runtime.magi import emit_jsonl, emit_md_summary

try:
    from .problem_router import route_problem
except ImportError:  # pragma: no cover
    from problem_router import route_problem

try:
    from .step_router import route_steps
except ImportError:  # pragma: no cover
    from step_router import route_steps

try:
    from . import subagent_tasks as sat
except Exception:  # pragma: no cover
    sat = None


def _load_problem(args) -> tuple[str, list[dict] | None]:
    if args.problem_json:
        data = json.loads(args.problem_json)
        return str(data.get("problem") or ""), data.get("steps")
    if args.problem_file:
        path = Path(args.problem_file)
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            data = json.loads(text)
            return str(data.get("problem") or ""), data.get("steps")
        return text.strip(), None
    return str(args.problem or ""), None


def _expected_for(route: str) -> str:
    if route == "sympy":
        return "sympy output: simplify(...) == 0"
    if route == "lean4":
        return "lean build success (no goals, no sorries)"
    return "manual justification required"


def _default_steps(problem: str, route: str) -> list[dict]:
    steps: list[dict] = []
    if route == "hybrid":
        steps.append(
            {
                "id": "S1",
                "goal": "建立等式/代数关系并进行符号验证",
                "difficulty": "medium",
                "route": "sympy",
                "engine": "sympy",
                "status": "pending",
                "expected_evidence": _expected_for("sympy"),
            }
        )
        steps.append(
            {
                "id": "S2",
                "goal": "在 Lean4 中形式化核心证明步骤",
                "difficulty": "hard",
                "route": "lean4",
                "engine": "lean4",
                "status": "pending",
                "expected_evidence": _expected_for("lean4"),
            }
        )
        return steps

    steps.append(
        {
            "id": "S1",
            "goal": "构造可验证的中间结论或等式",
            "difficulty": "medium" if route == "sympy" else "hard",
            "route": route,
            "engine": route,
            "status": "pending",
            "expected_evidence": _expected_for(route),
        }
    )
    steps.append(
        {
            "id": "S2",
            "goal": "完成最终结论的验证与一致性检查",
            "difficulty": "easy",
            "route": route,
            "engine": route,
            "status": "pending",
            "expected_evidence": _expected_for(route),
        }
    )
    return steps


def _normalize_steps(seed_steps: list[dict], route: str) -> list[dict]:
    payload = {"steps": seed_steps}
    try:
        routed = route_steps(payload, explain=False)
        steps = routed.get("steps") or seed_steps
    except Exception:  # noqa: BLE001
        steps = seed_steps
    for idx, step in enumerate(steps, start=1):
        if not step.get("id"):
            step["id"] = f"S{idx}"
        step.setdefault("route", route)
        step.setdefault("engine", step.get("route"))
        step.setdefault("status", "pending")
        if not str(step.get("expected_evidence") or "").strip():
            step["expected_evidence"] = _expected_for(step.get("route") or route)
    return steps


def _append_draft_summary(draft_path: Path, status: str, rounds: list[dict]) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []
    lines.append("\n## Math MAGI 规划摘要\n")
    lines.append(f"- 时间: {stamp}\n")
    lines.append(f"- 状态: {status}\n")
    for idx, record in enumerate(rounds, start=1):
        lines.append(f"\n### Round {idx}\n")
        roles = record.get("roles") or {}
        for key, info in roles.items():
            lines.append(f"- {key}: {info.get('vote')}\n")
            for reason in info.get("reasons") or []:
                lines.append(f"  - {reason}\n")
    draft_path.write_text(draft_path.read_text(encoding="utf-8") + "".join(lines), encoding="utf-8")


def _write_subagent_tasks(steps: list[dict], out_dir: Path) -> dict:
    if sat is None:  # pragma: no cover
        return {}
    tasks: list[dict] = []
    for i, step in enumerate(steps, start=1):
        for kind in sat._select_kinds(step):  # noqa: SLF001
            task = sat._mk_task(step, i, kind)  # noqa: SLF001
            tasks.append(task)

    payload = {
        "meta": {"task_count": len(tasks)},
        "tasks": [sat.asdict(t) for t in tasks],  # type: ignore[attr-defined]
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / "subagent_tasks.json"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md = out_dir / "subagent_tasks.md"
    sat._render_md(tasks, out_md)  # noqa: SLF001
    return {"json": str(out_json), "md": str(out_md)}


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 Math MAGI 规划与 steps.json 草案")
    parser.add_argument("--problem", help="问题文本")
    parser.add_argument("--problem-json", help="包含 problem/steps 的 JSON 字符串")
    parser.add_argument("--problem-file", help="问题文本或 JSON 文件")
    parser.add_argument("--steps-out", default="steps.json", help="输出 steps.json 路径")
    parser.add_argument("--draft", default="draft.md", help="草稿路径")
    parser.add_argument("--run-dir", help="运行目录（工作区内）")
    parser.add_argument("--workspace-dir", help="工作区根目录（缺省则使用配置/默认值）")
    parser.add_argument("--max-rounds", type=int, default=3, help="最大 Magi 迭代轮数")
    parser.add_argument("--force-veto", action="store_true", help="强制制造 veto（用于测试）")
    parser.add_argument("--log", help="日志路径（JSONL）")
    args = parser.parse_args()

    run_dir = ensure_run_dir(args.run_dir, args.workspace_dir)
    if not args.log:
        args.log = str(run_path(run_dir, "logs/tool_calls.log"))

    steps_out = Path(args.steps_out)
    if not steps_out.is_absolute():
        if args.steps_out == "steps.json":
            steps_out = run_path(run_dir, "plan/steps.json")
        else:
            steps_out = run_path(run_dir, args.steps_out)

    draft_path = Path(args.draft)
    if not draft_path.is_absolute():
        if args.draft == "draft.md":
            draft_path = run_path(run_dir, "draft/steps_draft.md")
        else:
            draft_path = run_path(run_dir, args.draft)

    problem, seed_steps = _load_problem(args)
    route = route_problem(problem) if problem else "hybrid"

    if seed_steps:
        steps = _normalize_steps(seed_steps, route)
    else:
        steps = _default_steps(problem, route)

    cfg = apply_subagent_auto_enable(load_config())
    rounds: list[dict] = []
    logs_path = run_path(run_dir, f"logs/magi_session_{time.strftime('%Y%m%d_%H%M%S')}.jsonl")

    context = {"steps": steps, "route": route}
    status = "ok"
    for round_idx in range(1, int(args.max_rounds) + 1):
        record = run_round(problem, context, force_veto=args.force_veto and round_idx == 1)
        record["round"] = round_idx
        rounds.append(record)
        emit_jsonl(record, logs_path)

        vote = collect_votes(record)
        if not vote.get("has_veto"):
            status = "ok"
            break
        status = "user_action_required"
        if args.force_veto:
            break
        context = revise_plan(record, vote.get("veto_reasons") or [])

    steps_payload = {"problem": problem, "steps": context.get("steps") or steps, "magi_status": status}
    steps_out.parent.mkdir(parents=True, exist_ok=True)
    steps_out.write_text(json.dumps(steps_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if not draft_path.exists():
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        draft_path.write_text("# MathProve 草稿\n", encoding="utf-8")
    _append_draft_summary(draft_path, status, rounds)

    summary_path = run_path(run_dir, "logs/magi_summary.md")
    emit_md_summary(rounds, summary_path, status, note="auto-generated")

    subagent_info: dict = {}
    sub_cfg = (cfg.get("routes") or {}).get("subagent") or {}
    if sub_cfg.get("enabled") and sat is not None:
        subagent_info = _write_subagent_tasks(context.get("steps") or steps, subagent_tasks_dir())

    output = {
        "status": status,
        "steps": str(steps_out),
        "draft": str(draft_path),
        "logs": str(logs_path),
        "subagent": subagent_info,
    }
    log_event({"event": "magi_plan", "status": status}, log_path=args.log)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if status == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
