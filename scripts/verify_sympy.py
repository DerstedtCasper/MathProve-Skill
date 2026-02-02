"""执行 SymPy 验证并返回结构化结果。"""
import argparse
import json
import pathlib
import subprocess
import sys
import time

try:
    from .logger import log_event
except ImportError:  # pragma: no cover - 兼容脚本直运行
    from logger import log_event

def _read_text(path):
    return pathlib.Path(path).read_text(encoding="utf-8")


def _extract_json(stdout_text):
    lines = stdout_text.strip().splitlines()
    for line in reversed(lines):
        candidate = line.strip()
        if not candidate:
            continue
        try:
            return json.loads(candidate), candidate
        except json.JSONDecodeError:
            continue
    return None, None


def run_code(code, template_path=None, timeout=10, python_path=None):
    template = ""
    if template_path:
        template = _read_text(template_path)

    full_code = f"{template}\n\n{code}".strip() + "\n"
    start = time.time()
    try:
        proc = subprocess.run(
            [python_path or sys.executable, "-"],
            input=full_code,
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error_type": "Timeout",
            "message": f"执行超时（>{timeout}s）",
            "stdout": "",
            "stderr": "",
        }

    elapsed = time.time() - start
    stdout_text = proc.stdout or ""
    stderr_text = proc.stderr or ""
    parsed, raw = _extract_json(stdout_text)

    if proc.returncode != 0:
        return {
            "status": "error",
            "error_type": "RuntimeError",
            "message": "SymPy 执行失败",
            "stdout": stdout_text,
            "stderr": stderr_text,
            "execution_time": round(elapsed, 4),
        }

    return {
        "status": "success",
        "output": parsed if parsed is not None else {"raw": stdout_text.strip()},
        "raw_json": raw,
        "stdout": stdout_text,
        "stderr": stderr_text,
        "execution_time": round(elapsed, 4),
    }


def main():
    parser = argparse.ArgumentParser(description="执行 SymPy 代码并返回结构化结果")
    parser.add_argument("--code", help="Python 代码字符串")
    parser.add_argument("--code-file", help="Python 代码文件路径")
    parser.add_argument(
        "--template",
        default=str(pathlib.Path(__file__).resolve().parent.parent / "assets" / "sympy_template.py"),
        help="模板路径",
    )
    parser.add_argument("--timeout", type=int, default=10, help="超时秒数")
    parser.add_argument("--python", help="指定 Python 路径执行 SymPy")
    parser.add_argument("--retries", type=int, default=0, help="失败重试次数")
    parser.add_argument("--log", help="日志路径（JSONL）")
    args = parser.parse_args()

    if args.code:
        code = args.code
    elif args.code_file:
        code = _read_text(args.code_file)
    else:
        if sys.stdin.isatty():
            raise SystemExit("缺少 --code 或 --code-file")
        code = sys.stdin.read()

    attempts = 0
    result = None
    while attempts <= args.retries:
        attempts += 1
        result = run_code(code, template_path=args.template, timeout=args.timeout, python_path=args.python)
        log_event(
            {
                "event": "sympy_run",
                "attempt": attempts,
                "status": result.get("status"),
                "error_type": result.get("error_type"),
            },
            log_path=args.log,
        )
        if result.get("status") == "success":
            break
    if result is None:
        result = {"status": "error", "error_type": "Unknown", "message": "未执行"}
    result["attempts"] = attempts
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
