"""执行 Lean4 验证并输出结构化结果。"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

try:
    from .logger import log_event
except ImportError:  # pragma: no cover
    from logger import log_event

try:
    from .runtime_paths import assets_dir
except ImportError:  # pragma: no cover
    from runtime_paths import assets_dir

try:
    from ..runtime.config_loader import load_config
    from ..runtime.workspace_manager import ensure_run_dir, run_path
except Exception:  # pragma: no cover
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from runtime.config_loader import load_config
    from runtime.workspace_manager import ensure_run_dir, run_path


def _read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _render_lean(template: str, code: str) -> str:
    if "{{CODE}}" in template:
        return template.replace("{{CODE}}", code.strip())
    return f"{template.rstrip()}\n\n{code.strip()}\n"


def _lean_filename(step_id: str | None) -> str:
    if not step_id:
        return "Step.lean"
    sid = step_id.strip().replace("/", "_").replace("\\", "_")
    if sid.lower().endswith(".lean"):
        return sid
    if sid.lower().startswith("step") or sid.startswith("S"):
        return f"{sid}.lean"
    return f"Step{sid}.lean"


def _resolve_cmd(cfg: dict, args: argparse.Namespace) -> list[str]:
    lean_cfg = (cfg.get("routes") or {}).get("lean") or {}
    lean_cmd = args.lean_cmd or lean_cfg.get("lean_cmd") or (cfg.get("paths") or {}).get("lean") or "lean"
    lake_cmd = args.lake_cmd or lean_cfg.get("lake_cmd") or (cfg.get("paths") or {}).get("lake") or "lake"
    if args.use_lake or args.lean_cwd:
        return [str(lake_cmd), "env", "lean"]
    return [str(lean_cmd)]


def main() -> int:
    parser = argparse.ArgumentParser(description="执行 Lean4 验证并输出结构化结果")
    parser.add_argument("--code", help="Lean 代码字符串")
    parser.add_argument("--code-file", help="Lean 代码文件路径")
    parser.add_argument(
        "--template",
        default=str(assets_dir() / "lean_template.lean"),
        help="Lean 模板路径",
    )
    parser.add_argument("--step-id", help="步骤 ID（用于命名 Lean 文件）")
    parser.add_argument("--run-dir", help="运行目录（工作区内）")
    parser.add_argument("--workspace-dir", help="工作区根目录（缺省则使用配置/默认值）")
    parser.add_argument("--out", help="日志输出路径（默认写入 run_dir/logs）")
    parser.add_argument("--timeout", type=int, default=60, help="超时秒数")
    parser.add_argument("--lean-cwd", help="Lean4 工作目录（Lake 工程路径）")
    parser.add_argument("--lean-cmd", help="Lean 可执行命令")
    parser.add_argument("--lake-cmd", help="Lake 可执行命令")
    parser.add_argument("--use-lake", action="store_true", help="使用 lake env lean 执行")
    parser.add_argument("--log", help="日志路径（JSONL）")
    args = parser.parse_args()

    run_dir = ensure_run_dir(args.run_dir, args.workspace_dir)
    if not args.log:
        args.log = str(run_path(run_dir, "logs/tool_calls.log"))

    if args.code:
        code = args.code
    elif args.code_file:
        code = _read_text(pathlib.Path(args.code_file))
    else:
        if sys.stdin.isatty():
            raise SystemExit("缺少 --code 或 --code-file")
        code = sys.stdin.read()

    template_path = pathlib.Path(args.template)
    template = _read_text(template_path) if template_path.exists() else ""
    lean_source = _render_lean(template, code)

    lean_dir = run_path(run_dir, "lean")
    lean_dir.mkdir(parents=True, exist_ok=True)
    lean_file = lean_dir / _lean_filename(args.step_id)
    lean_file.write_text(lean_source, encoding="utf-8")

    cfg = load_config()
    cmd = _resolve_cmd(cfg, args) + [str(lean_file)]
    start = time.time()
    proc = subprocess.run(
        cmd,
        cwd=args.lean_cwd,
        capture_output=True,
        text=True,
        timeout=args.timeout,
        check=False,
    )
    elapsed = time.time() - start

    out_path = None
    if args.out:
        out_path = run_path(run_dir, args.out) if not pathlib.Path(args.out).is_absolute() else pathlib.Path(args.out)
    else:
        stamp = args.step_id or "step"
        out_path = run_path(run_dir, f"logs/lean_{stamp}.log")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")

    status = "success" if proc.returncode == 0 else "error"
    result = {
        "status": status,
        "returncode": proc.returncode,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
        "execution_time": round(elapsed, 4),
        "log": str(out_path),
        "file": str(lean_file),
    }
    log_event(
        {"event": "lean_run", "status": status, "returncode": proc.returncode, "file": str(lean_file)},
        log_path=args.log,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if proc.returncode == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
