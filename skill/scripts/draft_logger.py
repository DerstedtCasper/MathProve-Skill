"""将已验证步骤追加到 MathProve 草稿。"""
import argparse
import json
import pathlib
import time

try:
    from .logger import log_event
except ImportError:  # pragma: no cover
    from logger import log_event

try:
    from .runtime_paths import assets_dir
except ImportError:  # pragma: no cover - 兼容脚本直接运行
    from runtime_paths import assets_dir


def _load_step(args):
    if args.step_json:
        return json.loads(args.step_json)
    if args.step_file:
        return json.loads(pathlib.Path(args.step_file).read_text(encoding="utf-8"))
    return {
        "id": args.step_id,
        "goal": args.goal,
        "difficulty": args.difficulty,
        "route": args.route,
        "evidence": args.evidence,
        "notes": args.notes,
    }


def append_step(draft_path, step):
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    lines = ["", f"### {step.get('id', 'S?')}"]
    lines.append(f"- 目标：{step.get('goal', '')}")
    lines.append(f"- 难度：{step.get('difficulty', '')}")
    lines.append(f"- 路线：{step.get('route', '')}")
    lines.append(f"- 证据：{step.get('evidence', '')}")

    symbols = step.get("symbols") or []
    if isinstance(symbols, list) and symbols:
        lines.append("- 符号：")
        for s in symbols:
            if isinstance(s, dict):
                name = str(s.get("name") or "").strip()
                meaning = str(s.get("meaning") or "").strip()
                if name or meaning:
                    lines.append(f"  - {name}：{meaning}")
            elif isinstance(s, str) and s.strip():
                lines.append(f"  - {s.strip()}")
    else:
        lines.append("- 符号：<待补全>")

    assumptions = step.get("assumptions") or []
    if isinstance(assumptions, list) and assumptions:
        lines.append("- 假设：")
        for a in assumptions:
            if isinstance(a, str) and a.strip():
                lines.append(f"  - {a.strip()}")
    else:
        lines.append("- 假设：<待补全>")

    lemmas = step.get("lemmas") or []
    if isinstance(lemmas, list) and lemmas:
        lines.append("- 引理/定理（候选/已用）：")
        for l in lemmas:
            if isinstance(l, str) and l.strip():
                lines.append(f"  - {l.strip()}")

    explanation = str(step.get("explanation") or "").strip()
    if explanation:
        lines.append("- 讲解：")
        for ln in explanation.splitlines():
            lines.append(f"  {ln}".rstrip())
    else:
        lines.append("- 讲解：<待补全>")

    lines.append(f"- 备注：{step.get('notes', '')}")
    lines.append(f"- 记录时间：{stamp}")
    lines.append("")
    draft = pathlib.Path(draft_path)
    if not draft.exists():
        tpl = assets_dir() / "templates" / "draft_template.md"
        if tpl.exists():
            draft.write_text(tpl.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            draft.write_text("# MathProve 草稿\n", encoding="utf-8")
    with draft.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="写入 MathProve 草稿记录")
    parser.add_argument("--draft", default="draft.md", help="草稿路径")
    parser.add_argument("--step-json", help="步骤 JSON 字符串")
    parser.add_argument("--step-file", help="步骤 JSON 文件")
    parser.add_argument("--step-id", help="步骤 ID")
    parser.add_argument("--goal", help="步骤目标")
    parser.add_argument("--difficulty", help="难度")
    parser.add_argument("--route", help="路线")
    parser.add_argument("--evidence", help="证据或文件路径")
    parser.add_argument("--notes", default="", help="备注")
    parser.add_argument("--log", help="日志路径（JSONL）")
    args = parser.parse_args()

    step = _load_step(args)
    if not step.get("id") or not step.get("goal"):
        raise SystemExit("缺少 step id 或 goal")

    append_step(args.draft, step)
    log_event({"event": "draft_append", "id": step.get("id")}, log_path=args.log)
    print(json.dumps({"status": "success", "draft": args.draft}, ensure_ascii=False))


if __name__ == "__main__":
    main()
