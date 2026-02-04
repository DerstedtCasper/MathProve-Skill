"""Emit MAGI logs and summaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def emit_jsonl(round_record: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(round_record, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as f:
        f.write(payload + "\n")


def emit_md_summary(rounds: list[dict], path: Path, status: str, note: str = "") -> None:
    lines: list[str] = []
    lines.append("# Math MAGI Summary\n")
    lines.append(f"- status: {status}\n")
    if note:
        lines.append(f"- note: {note}\n")
    for idx, record in enumerate(rounds, start=1):
        lines.append(f"\n## Round {idx}\n")
        roles = record.get("roles") or {}
        for key, info in roles.items():
            vote = info.get("vote", "")
            reasons = info.get("reasons") or []
            lines.append(f"- {key}: {vote}\n")
            for reason in reasons:
                lines.append(f"  - {reason}\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines), encoding="utf-8")
