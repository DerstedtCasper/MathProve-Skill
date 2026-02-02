"""检查 MathProve 运行依赖并输出环境摘要。"""
import argparse
import json
import pathlib
import platform
import shutil
import subprocess
import sys


def _run_version(cmd, timeout=5, cwd=None):
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            check=False,
        )
        output = (result.stdout or result.stderr or "").strip()
        return True, output
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _check_sympy(python_path, timeout=8):
    if not python_path:
        return False, "未提供 Python 路径"
    try:
        result = subprocess.run(
            [python_path, "-c", "import sympy; print(sympy.__version__)"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "").strip()
    return True, (result.stdout or "").strip()


def main():
    parser = argparse.ArgumentParser(description="检查 MathProve 运行环境")
    parser.add_argument("--project", help="Lean 工程目录（可选）")
    parser.add_argument("--python", help="指定 Python 路径以检测 SymPy")
    parser.add_argument("--lean-path", help="指定 lean 可执行文件路径")
    parser.add_argument("--lake-path", help="指定 lake 可执行文件路径")
    parser.add_argument("--lean-timeout", type=int, default=15, help="Lean/Lake 版本探测超时秒数")
    parser.add_argument("--verify-mathlib", action="store_true", help="在 project 中做一次 import Mathlib 的编译探测")
    args = parser.parse_args()

    info = {
        "python": {
            "version": sys.version.split()[0],
            "executable": sys.executable,
            "platform": platform.platform(),
        }
    }

    if args.python:
        ok, version = _check_sympy(args.python)
        if ok:
            info["sympy"] = {"available": True, "version": version, "python": args.python}
        else:
            info["sympy"] = {"available": False, "error": version, "python": args.python}
    else:
        try:
            import sympy  # noqa: F401

            info["sympy"] = {"available": True, "version": getattr(sympy, "__version__", "unknown")}
        except Exception as exc:  # noqa: BLE001
            info["sympy"] = {"available": False, "error": str(exc)}

    lean_path = args.lean_path or shutil.which("lean")
    lake_path = args.lake_path or shutil.which("lake")
    info["lean4"] = {"lean": lean_path, "lake": lake_path}

    if lean_path:
        ok, out = _run_version([lean_path, "--version"], timeout=args.lean_timeout)
        info["lean4"]["lean_version_ok"] = ok
        info["lean4"]["lean_version"] = out
    if lake_path:
        ok, out = _run_version([lake_path, "--version"], timeout=args.lean_timeout)
        info["lean4"]["lake_version_ok"] = ok
        info["lean4"]["lake_version"] = out

    if args.project:
        info["lean4"]["project"] = args.project
        toolchain_path = pathlib.Path(args.project) / "lean-toolchain"
        info["lean4"]["lean_toolchain_file"] = str(toolchain_path) if toolchain_path.exists() else None
        if lake_path:
            ok, out = _run_version(
                [lake_path, "env", "lean", "--version"],
                timeout=args.lean_timeout,
                cwd=args.project,
            )
            info["lean4"]["project_lean_version_ok"] = ok
            info["lean4"]["project_lean_version"] = out

        if args.verify_mathlib and lake_path:
            probe = pathlib.Path(args.project) / ".mathprove_mathlib_probe.lean"
            try:
                probe.write_text("import Mathlib\n#check Nat\n", encoding="utf-8")
                # Mathlib 工程首次编译可能很慢；probe 默认给更宽的时间窗。
                probe_timeout = max(int(args.lean_timeout), 60)
                ok, out = _run_version(
                    [lake_path, "env", "lean", str(probe)],
                    timeout=probe_timeout,
                    cwd=args.project,
                )
                info["lean4"]["mathlib_probe_ok"] = ok
                info["lean4"]["mathlib_probe"] = out
            finally:
                try:
                    probe.unlink(missing_ok=True)
                except Exception:  # noqa: BLE001
                    pass

    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
