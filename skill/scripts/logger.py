"""结构化日志输出到 JSONL。"""
import json
import os
import pathlib
import time


def _default_log_path():
    env_path = os.environ.get("MATHPROVE_LOG")
    if env_path:
        return pathlib.Path(env_path)
    log_dir = pathlib.Path(__file__).resolve().parents[1] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d")
    return log_dir / f"skill_usage_{stamp}.jsonl"


def log_event(event, log_path=None):
    path = pathlib.Path(log_path) if log_path else _default_log_path()
    record = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        **event,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return str(path)
