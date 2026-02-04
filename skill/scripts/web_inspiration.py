"""Record web inspiration results to references log."""
import argparse
import json
import pathlib
import time

try:
    from .logger import log_event
    from .runtime_paths import references_dir
except ImportError:  # pragma: no cover
    from logger import log_event
    from runtime_paths import references_dir


def _load_sources(args):
    if args.sources_json:
        return json.loads(args.sources_json)
    if args.sources_file:
        return json.loads(pathlib.Path(args.sources_file).read_text(encoding="utf-8"))
    return []


def append_refs(refs_path, query, sources, notes):
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    date = time.strftime("%Y-%m-%d")
    lines = [
        "",
        "## Web Inspiration Log",
        f"- Time: {stamp}",
        f"- Query: {query}",
        f"- Notes: {notes}",
        "- Sources:",
    ]
    if not sources:
        lines.append("  - (no sources provided)")
    else:
        for item in sources:
            title = item.get("title", "untitled")
            url = item.get("url", "")
            purpose = item.get("purpose") or item.get("summary") or notes or ""
            lines.append(f"  - {title} | {url} | {date} | {purpose}")
    refs = pathlib.Path(refs_path)
    refs.parent.mkdir(parents=True, exist_ok=True)
    if not refs.exists():
        refs.write_text(
            "# References Log\n\n记录外部来源（标题 | 链接 | 访问日期 | 用途）\n",
            encoding="utf-8",
        )
    with refs.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Record web inspiration results")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--sources-json", help="Sources JSON string")
    parser.add_argument("--sources-file", help="Sources JSON file")
    parser.add_argument("--notes", default="", help="Notes")
    parser.add_argument(
        "--refs",
        default=str(references_dir() / "refs.md"),
        help="References log path",
    )
    parser.add_argument("--log", help="Log path (JSONL)")
    args = parser.parse_args()

    sources = _load_sources(args)
    append_refs(args.refs, args.query, sources, args.notes)
    log_event({"event": "web_inspiration", "query": args.query, "count": len(sources)}, log_path=args.log)
    print(json.dumps({"status": "success", "refs": args.refs}, ensure_ascii=False))


if __name__ == "__main__":
    main()
