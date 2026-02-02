"""记录联网启发结果（由 IDE 联网能力提供）。"""
import argparse
import json
import pathlib
import time

try:
    from .logger import log_event
except ImportError:  # pragma: no cover
    from logger import log_event


def _load_sources(args):
    if args.sources_json:
        return json.loads(args.sources_json)
    if args.sources_file:
        return json.loads(pathlib.Path(args.sources_file).read_text(encoding="utf-8"))
    return []


def append_inspiration(draft_path, query, sources, notes):
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "",
        "## 联网启发记录",
        f"- 时间：{stamp}",
        f"- 查询：{query}",
        f"- 备注：{notes}",
        "- 来源：",
    ]
    if not sources:
        lines.append("  - （未提供来源明细）")
    else:
        for item in sources:
            title = item.get("title", "未命名来源")
            url = item.get("url", "")
            summary = item.get("summary", "")
            lines.append(f"  - {title} | {url} | {summary}")
    draft = pathlib.Path(draft_path)
    if not draft.exists():
        draft.write_text("# MathProve 草稿\n", encoding="utf-8")
    with draft.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="记录联网启发结果")
    parser.add_argument("--query", required=True, help="检索问题")
    parser.add_argument("--sources-json", help="来源 JSON 字符串")
    parser.add_argument("--sources-file", help="来源 JSON 文件")
    parser.add_argument("--notes", default="", help="补充说明")
    parser.add_argument("--draft", default="draft.md", help="草稿路径")
    parser.add_argument("--log", help="日志路径（JSONL）")
    args = parser.parse_args()

    sources = _load_sources(args)
    append_inspiration(args.draft, args.query, sources, args.notes)
    log_event({"event": "web_inspiration", "query": args.query, "count": len(sources)}, log_path=args.log)
    print(json.dumps({"status": "success", "draft": args.draft}, ensure_ascii=False))


if __name__ == "__main__":
    main()
