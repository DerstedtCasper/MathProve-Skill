"""Small context-lake helpers for MathProve v8."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .proof_factory_v8 import Stage, write_context_shard, write_handoff_capsule


def add_shard(root: str | Path, stage: str, kind: str, content: str, summary: str, depends_on: list[str] | None = None) -> dict[str, Any]:
    return write_context_shard(Path(root), Stage(stage), kind, content, summary, depends_on). __dict__


def load_index(root: str | Path) -> dict[str, Any]:
    path = Path(root) / "index.json"
    if not path.exists():
        return {"shards": []}
    return json.loads(path.read_text(encoding="utf-8"))


def make_handoff(root: str | Path, stage: str, theorem_signature: str, open_obligations: list[str], next_actions: list[str]) -> str:
    capsule = {
        "stage": stage,
        "theorem_signature": theorem_signature,
        "open_obligations": open_obligations,
        "next_actions": next_actions,
    }
    return str(write_handoff_capsule(root, Stage(stage), capsule))
