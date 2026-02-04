"""Check runtime routes and required dependencies."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

try:
    from .logger import log_event
except ImportError:  # pragma: no cover
    from logger import log_event

try:
    from ..runtime.config_loader import load_config
    from ..runtime.routes import apply_subagent_auto_enable
except Exception:  # pragma: no cover - direct script execution
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from runtime.config_loader import load_config
    from runtime.routes import apply_subagent_auto_enable


def _run_cmd(cmd: list[str], timeout: int = 10) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return False, "command not found"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "").strip()
    return True, (proc.stdout or proc.stderr or "").strip()


def _redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            key = str(k).lower()
            if any(x in key for x in ("key", "token", "secret", "password")):
                out[k] = "***"
            else:
                out[k] = _redact(v)
        return out
    if isinstance(obj, list):
        return [_redact(x) for x in obj]
    return obj


def _check_sympy(cfg: dict, missing: list[dict]) -> None:
    sympy_cfg = (cfg.get("routes") or {}).get("sympy") or {}
    if not sympy_cfg.get("enabled"):
        return
    python_path = sympy_cfg.get("python") or (cfg.get("paths") or {}).get("python") or sys.executable or "python"
    ok, out = _run_cmd([python_path, "-c", "import sympy; print(sympy.__version__)"], timeout=10)
    if not ok:
        missing.append(
            {
                "route": "sympy",
                "reason": out or "sympy import failed",
                "how_to_fix": [
                    "安装 SymPy：pip install sympy",
                    f"或在 config.local.yaml 中设置 routes.sympy.python = {python_path}",
                ],
            }
        )


def _check_lean(cfg: dict, missing: list[dict]) -> None:
    lean_cfg = (cfg.get("routes") or {}).get("lean") or {}
    if not lean_cfg.get("enabled"):
        return

    lean_cmd = lean_cfg.get("lean_cmd") or (cfg.get("paths") or {}).get("lean") or "lean"
    lake_cmd = lean_cfg.get("lake_cmd") or (cfg.get("paths") or {}).get("lake") or "lake"
    require_mathlib = bool(lean_cfg.get("require_mathlib", True))

    ok_lean, out_lean = _run_cmd([lean_cmd, "--version"], timeout=10)
    ok_lake, out_lake = _run_cmd([lake_cmd, "--version"], timeout=10)

    if not ok_lean:
        missing.append(
            {
                "route": "lean",
                "reason": out_lean or "lean --version failed",
                "how_to_fix": [
                    "安装 Lean4 并确保 lean 可执行文件在 PATH 中",
                    "或在 config.local.yaml 中设置 routes.lean.lean_cmd",
                ],
            }
        )
    if require_mathlib and not ok_lake:
        missing.append(
            {
                "route": "lean",
                "reason": out_lake or "lake --version failed",
                "how_to_fix": [
                    "安装 Lake/Mathlib 工程环境",
                    "或在 config.local.yaml 中设置 routes.lean.lake_cmd",
                ],
            }
        )


def _check_web(cfg: dict, missing: list[dict]) -> None:
    web_cfg = (cfg.get("routes") or {}).get("web") or {}
    if not web_cfg.get("enabled"):
        return
    provider = web_cfg.get("provider")
    if not provider:
        missing.append(
            {
                "route": "web",
                "reason": "web provider 未配置",
                "how_to_fix": ["在 config.local.yaml 中设置 routes.web.provider"],
            }
        )


def _check_subagent(cfg: dict, missing: list[dict]) -> None:
    sub_cfg = (cfg.get("routes") or {}).get("subagent") or {}
    if not sub_cfg.get("enabled"):
        return
    mode = str(sub_cfg.get("mode") or "none")
    if mode in {"none", ""}:
        missing.append(
            {
                "route": "subagent",
                "reason": "subagent 已启用但 mode 未设置",
                "how_to_fix": ["设置 routes.subagent.mode 为 local 或 remote"],
            }
        )
        return
    if mode == "local" and not sub_cfg.get("driver"):
        missing.append(
            {
                "route": "subagent",
                "reason": "subagent=local 但未配置 driver",
                "how_to_fix": ["设置 routes.subagent.driver 指向可执行入口"],
            }
        )
    if mode == "remote" and not sub_cfg.get("endpoint"):
        missing.append(
            {
                "route": "subagent",
                "reason": "subagent=remote 但未配置 endpoint",
                "how_to_fix": ["设置 routes.subagent.endpoint 指向服务地址"],
            }
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 MathProve 路由与依赖")
    parser.add_argument("--log", help="日志路径（JSONL）")
    args = parser.parse_args()

    cfg = apply_subagent_auto_enable(load_config())
    missing: list[dict] = []

    _check_sympy(cfg, missing)
    _check_lean(cfg, missing)
    _check_web(cfg, missing)
    _check_subagent(cfg, missing)

    status = "ok" if not missing else "user_action_required"
    output = {
        "status": status,
        "missing": missing,
        "effective_config": _redact(cfg),
    }
    log_event({"event": "check_routes", "status": status, "missing": len(missing)}, log_path=args.log)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if status == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
