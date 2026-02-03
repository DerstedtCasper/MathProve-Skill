import argparse
import json
import os
import pathlib
from dataclasses import dataclass, asdict

try:
    from .logger import log_event
except Exception:  # pragma: no cover
    from logger import log_event


def _truthy(v: str | None) -> bool:
    if v is None:
        return False
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def detect_subagent_capability() -> dict:
    """
    Best-effort capability detection.

    Different CLIs/IDEs expose subagent features differently; we keep this conservative:
    - Explicit opt-in: MATHPROVE_SUBAGENT=1
    - Or driver provided: MATHPROVE_SUBAGENT_DRIVER=<command>
    - Or common generic flags (best-effort).
    """

    driver = os.environ.get("MATHPROVE_SUBAGENT_DRIVER")
    enabled = _truthy(os.environ.get("MATHPROVE_SUBAGENT")) or bool(driver)

    # Generic / vendor-agnostic environment flags (optional).
    for k in (
        "CODEX_SUBAGENT",
        "CODEX_SUBAGENTS",
        "MULTI_AGENT",
        "SUBAGENT",
        "SUBAGENTS",
    ):
        enabled = enabled or _truthy(os.environ.get(k))

    return {
        "enabled": bool(enabled),
        "driver": driver or "",
        "evidence": {k: os.environ.get(k, "") for k in ["MATHPROVE_SUBAGENT", "MATHPROVE_SUBAGENT_DRIVER"]},
    }


@dataclass
class SubagentTask:
    id: str
    kind: str
    step_id: str
    step_index: int
    difficulty: str
    route: str
    goal: str
    constraints: list[str]
    expected_output: str


def _mk_task(step: dict, step_index: int, kind: str) -> SubagentTask:
    step_id = str(step.get("id") or f"step_{step_index}")
    difficulty = str(step.get("difficulty") or "unknown")
    route = str(step.get("route") or "hybrid")
    goal = str(step.get("goal") or "")

    constraints: list[str] = [
        "输出必须可回填到 steps.json / draft.md（不要只给口头描述）。",
        "必须显式列出本 step 引入/使用的符号与其含义（演讲友好）。",
    ]

    if kind == "explain":
        expected = (
            "给出 5-10 行以内的讲解版说明：\n"
            "1) 本步目标（1句）\n"
            "2) 新符号/约定（逐条）\n"
            "3) 关键逻辑跳跃/不变量（逐条）\n"
            "4) 结论如何被后续使用（1句）"
        )
    elif kind == "mathlib_lemma_search":
        constraints.append("优先使用 Mathlib；给出可直接 `apply`/`have` 的 lemma 名称与 import 建议。")
        expected = "列出 3-5 个候选 lemma/定理（含全名），并说明各自适配点与使用方式。"
    elif kind == "sympy_check":
        constraints.append("给出最小可运行 SymPy 片段（能验证本步关键等式/不等式/化简）。")
        expected = "输出一段 SymPy 代码（含 symbols 定义 + assert/简化验证），并说明期望结果。"
    elif kind == "lean_proof":
        constraints.append("给出 Lean4 代码骨架：theorem/lemma + `by` 证明思路，避免 `sorry/admit`。")
        expected = "输出 Lean4 代码（可直接放进 reverse gate 文件编译），并说明需要的前提假设。"
    else:
        expected = "给出可执行的产物（代码/表格/清单），避免空泛。"

    task_id = f"{step_index:03d}_{step_id}_{kind}"
    return SubagentTask(
        id=task_id,
        kind=kind,
        step_id=step_id,
        step_index=step_index,
        difficulty=difficulty,
        route=route,
        goal=goal,
        constraints=constraints,
        expected_output=expected,
    )


def _select_kinds(step: dict) -> list[str]:
    difficulty = str(step.get("difficulty") or "")
    route = str(step.get("route") or "")

    kinds = ["explain"]

    # Always helpful for non-trivial steps.
    if difficulty in {"medium", "hard"} or route in {"lean4", "hybrid"}:
        kinds.append("mathlib_lemma_search")

    # Add compute checks if SymPy is involved or step looks algebraic.
    if route in {"sympy", "hybrid"}:
        kinds.append("sympy_check")

    # Add Lean proof attempts only if Lean route is chosen.
    if route in {"lean4", "hybrid"}:
        kinds.append("lean_proof")

    # Deduplicate while preserving order.
    out = []
    for k in kinds:
        if k not in out:
            out.append(k)
    return out


def _render_md(tasks: list[SubagentTask], out_path: pathlib.Path) -> None:
    lines: list[str] = []
    lines.append("# MathProve Subagent Task Pack\n")
    lines.append("该文件由 `scripts/subagent_tasks.py` 生成，用于并行分发或作为单代理自检清单。\n")

    by_step: dict[int, list[SubagentTask]] = {}
    for t in tasks:
        by_step.setdefault(t.step_index, []).append(t)

    for step_index in sorted(by_step.keys()):
        step_tasks = by_step[step_index]
        step_id = step_tasks[0].step_id
        lines.append(f"## Step {step_index}: {step_id}\n")
        for t in step_tasks:
            lines.append(f"### {t.kind}\n")
            if t.goal:
                lines.append(f"- 目标: {t.goal}\n")
            lines.append(f"- 路线: {t.route}\n")
            lines.append(f"- 难度: {t.difficulty}\n")
            lines.append("- 约束:\n")
            for c in t.constraints:
                lines.append(f"  - {c}\n")
            lines.append("- 期望输出:\n")
            for ln in t.expected_output.splitlines():
                lines.append(f"  {ln}\n")
            lines.append("\n")

    out_path.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="生成 MathProve 子代理任务包（JSON + 可选 Markdown）")
    ap.add_argument("--steps", required=True, help="步骤 JSON 文件（step_router 输出或手写）")
    ap.add_argument("--out-dir", default="subagent_tasks", help="输出目录")
    ap.add_argument("--emit-md", action="store_true", help="同时输出 Markdown 任务清单")
    ap.add_argument("--log", default="", help="日志路径（JSONL）")
    args = ap.parse_args()

    cap = detect_subagent_capability()
    if args.log:
        log_event({"event": "subagent.detect", "capability": cap}, log_path=args.log)

    steps_path = pathlib.Path(args.steps)
    data = json.loads(steps_path.read_text(encoding="utf-8"))
    steps = data.get("steps") or []
    if not isinstance(steps, list) or not steps:
        raise SystemExit("steps.json 缺少 steps 数组，或为空")

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tasks: list[SubagentTask] = []
    for i, step in enumerate(steps, start=1):
        for kind in _select_kinds(step):
            tasks.append(_mk_task(step, i, kind))

    payload = {
        "meta": {
            "generated_from": str(steps_path),
            "subagent_capability": cap,
            "task_count": len(tasks),
        },
        "tasks": [asdict(t) for t in tasks],
    }

    out_json = out_dir / "subagent_tasks.json"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.log:
        log_event({"event": "subagent.tasks_written", "path": str(out_json), "count": len(tasks)}, log_path=args.log)

    if args.emit_md:
        out_md = out_dir / "subagent_tasks.md"
        _render_md(tasks, out_md)
        if args.log:
            log_event({"event": "subagent.tasks_md_written", "path": str(out_md)}, log_path=args.log)

    print(json.dumps({"status": "ok", "tasks": len(tasks), "out_dir": str(out_dir)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
