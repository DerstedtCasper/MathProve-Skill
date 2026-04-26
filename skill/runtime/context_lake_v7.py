"""Persistent context lake for long-horizon MathProve v7 runs."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timezone
import json, re

@dataclass
class ShardEntry:
    run_id: str
    shard_type: str
    path: str
    title: str
    summary: str
    stage: str
    tokens_estimate: int
    created_at: str

class ContextLake:
    def __init__(self, root: str | Path, run_id: str):
        self.root = Path(root); self.run_id = run_id
        self.dir = self.root / "runs" / run_id / "context_lake"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.index = self.dir / "shard_index.jsonl"
    @staticmethod
    def estimate_tokens(text: str) -> int:
        return max(1, len(text) // 3)
    def write_shard(self, shard_type: str, stage: str, title: str, body: str, filename: str | None = None) -> ShardEntry:
        safe = filename or re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{stage}_{shard_type}.md")
        path = self.dir / safe
        summary = "\n".join(body.strip().splitlines()[:20])
        path.write_text(body, encoding="utf-8")
        entry = ShardEntry(self.run_id, shard_type, str(path), title, summary, stage, self.estimate_tokens(body), datetime.now(timezone.utc).isoformat())
        with self.index.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        return entry
    def read_index(self) -> list[ShardEntry]:
        if not self.index.exists(): return []
        return [ShardEntry(**json.loads(line)) for line in self.index.read_text(encoding="utf-8").splitlines() if line.strip()]
    def active_packet(self, max_tokens: int = 100000, stages: set[str] | None = None) -> str:
        entries = self.read_index()
        if stages: entries = [e for e in entries if e.stage in stages]
        packet, used = [], 0
        for e in reversed(entries):
            if used + e.tokens_estimate > max_tokens:
                packet.append(f"[SKIP {e.stage}/{e.shard_type}: token budget]"); continue
            try: txt = Path(e.path).read_text(encoding="utf-8")
            except OSError as exc: txt = f"[UNREADABLE {e.path}: {exc}]"
            packet.append(f"\n## {e.stage} / {e.title}\n{txt}"); used += e.tokens_estimate
        return "\n".join(reversed(packet))
