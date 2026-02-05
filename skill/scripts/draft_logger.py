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

try:
    from ..runtime.workspace_manager import ensure_run_dir, run_path
except Exception:  # pragma: no cover
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from runtime.workspace_manager import ensure_run_dir, run_path


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
        "status": args.status,
        "evidence": args.evidence,
        "evidence_path": args.evidence_path,
        "evidence_digest": args.evidence_digest,
        "notes": args.notes,
    }


def _is_passed(step: dict) -> bool:
    return str(step.get("status") or "").strip().lower() == "passed"


def _has_evidence(step: dict) -> bool:
    if str(step.get("evidence_path") or "").strip():
        return True
    if str(step.get("evidence_digest") or "").strip():
        return True
    # Back-compat: treat legacy "evidence" as a digest when present.
    return bool(str(step.get("evidence") or "").strip())


def append_step(draft_path, step):
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    lines = ["", f"### {step.get('id', 'S?')}"]
    lines.append(f"- 目标：{step.get('goal', '')}")
    lines.append(f"- 难度：{step.get('difficulty', '')}")
    lines.append(f"- 路线：{step.get('route', '')}")
    evidence_path = str(step.get('evidence_path') or '').strip()
    evidence_digest = str(step.get('evidence_digest') or '').strip()
    legacy_evidence = str(step.get('evidence') or '').strip()
    if evidence_path:
        lines.append(f"- 证据路径：{evidence_path}")
    elif evidence_digest:
        lines.append(f"- 证据摘要：{evidence_digest}")
    else:
        lines.append(f"- 证据（legacy）：{legacy_evidence}")

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
    draft.parent.mkdir(parents=True, exist_ok=True)
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
    parser.add_argument("--status", default="", help="步骤状态：passed/pending/failed/skipped")
    parser.add_argument("--evidence", help="证据或文件路径")
    parser.add_argument("--evidence-path", help="证据路径")
    parser.add_argument("--evidence-digest", help="证据摘要/哈希")
    parser.add_argument("--notes", default="", help="备注")
    parser.add_argument("--run-dir", help="运行目录（工作区内）")
    parser.add_argument("--workspace-dir", help="工作区根目录（缺省则使用配置/默认值）")
    parser.add_argument(
        "--allow-unverified",
        action="store_true",
        help="允许写入未验证 step（开启后不再强制要求 status=passed 且 evidence 非空）",
    )
    parser.add_argument("--log", help="日志路径（JSONL）")
    args = parser.parse_args()

    run_dir = ensure_run_dir(args.run_dir, args.workspace_dir)
    if not args.log:
        args.log = str(run_path(run_dir, "logs/tool_calls.log"))

    draft_path = pathlib.Path(args.draft)
    if not draft_path.is_absolute():
        if args.draft == "draft.md":
            draft_path = run_path(run_dir, "draft/proof_draft.md")
        else:
            draft_path = run_path(run_dir, args.draft)
    args.draft = str(draft_path)

    step = _load_step(args)
    if not step.get("id") or not step.get("goal"):
        raise SystemExit("缺少 step id 或 goal")

    # Hard gate: by default, only allow verified steps into draft.md.
    if not args.allow_unverified:
        if not _is_passed(step):
            raise SystemExit("draft_logger: step.status 必须为 'passed'（如需绕过请显式使用 --allow-unverified）")
        if not _has_evidence(step):
            raise SystemExit("draft_logger: 已通过 step 必须提供 evidence（如需绕过请显式使用 --allow-unverified）")

    append_step(args.draft, step)
    log_event({"event": "draft_append", "id": step.get("id")}, log_path=args.log)
    print(json.dumps({"status": "success", "draft": args.draft}, ensure_ascii=False))


if __name__ == "__main__":
    main()
