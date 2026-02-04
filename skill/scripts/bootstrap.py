"""Bootstrap local config and references templates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .logger import log_event
    from .runtime_paths import references_dir
except ImportError:  # pragma: no cover
    from logger import log_event
    from runtime_paths import references_dir

try:
    from ..runtime.config_loader import config_paths
except Exception:  # pragma: no cover
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from runtime.config_loader import config_paths


CONFIG_TEMPLATE = """# Local overrides for MathProve (gitignored)
routes:
  sympy:
    enabled: true
    python: python
  lean:
    enabled: true
    lean_cmd: lean
    lake_cmd: lake
  web:
    enabled: false
    provider: null
  subagent:
    enabled: false
    mode: none
    driver: ""
    endpoint: ""
"""


REFS_TEMPLATE = """# References Log

记录外部来源（标题 | 链接 | 访问日期 | 用途）
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化 MathProve 本地配置与引用模板")
    parser.add_argument("--log", help="日志路径（JSONL）")
    args = parser.parse_args()

    base_path, local_path = config_paths()
    created: list[str] = []

    if not local_path.exists():
        local_path.write_text(CONFIG_TEMPLATE, encoding="utf-8")
        created.append(str(local_path))

    refs_dir = references_dir()
    refs_dir.mkdir(parents=True, exist_ok=True)
    refs_path = refs_dir / "refs.md"
    if not refs_path.exists():
        refs_path.write_text(REFS_TEMPLATE, encoding="utf-8")
        created.append(str(refs_path))

    status = "ok" if not created else "user_action_required"
    payload = {"status": status, "created": created, "config": str(base_path)}
    log_event({"event": "bootstrap", "status": status, "created": created}, log_path=args.log)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if status == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
