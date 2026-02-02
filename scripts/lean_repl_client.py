"""调用 Lean4 REPL 执行 JSON 命令并返回结构化结果。"""
import argparse
import json
import pathlib
import shlex
import subprocess
import sys
import tempfile

try:
    from .logger import log_event
except ImportError:  # pragma: no cover
    from logger import log_event


def _parse_payload(args):
    if args.payload:
        return json.loads(args.payload)
    if args.payload_file:
        return json.loads(open(args.payload_file, "r", encoding="utf-8").read())
    if not sys.stdin.isatty():
        return json.loads(sys.stdin.read())
    raise SystemExit("缺少 --payload 或 --payload-file")


def _to_cmd_list(repl_cmd):
    if isinstance(repl_cmd, list):
        return repl_cmd
    return shlex.split(repl_cmd)


def _extract_json_lines(stdout_text):
    outputs = []
    for line in stdout_text.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        try:
            outputs.append(json.loads(candidate))
        except json.JSONDecodeError:
            continue
    return outputs


def _build_input(cmds):
    lines = []
    for item in cmds:
        if isinstance(item, str):
            lines.append(item)
        else:
            lines.append(json.dumps(item, ensure_ascii=False))
    return "\n".join(lines) + "\n"


def _extract_cmds(cmds):
    extracted = []
    for item in cmds:
        if isinstance(item, str):
            extracted.append(item)
            continue
        if isinstance(item, dict) and item.get("cmd"):
            extracted.append(item["cmd"])
            continue
        raise ValueError("file 模式仅支持 string 或包含 cmd 的对象")
    return extracted


def _run_file_mode(cmds, file_cmd, cwd=None, timeout=30):
    lines = _extract_cmds(cmds)
    content = "\n\n".join(lines).strip() + "\n"
    with tempfile.NamedTemporaryFile("w", suffix=".lean", delete=False, encoding="utf-8") as fp:
        fp.write(content)
        temp_path = fp.name
    try:
        proc = subprocess.run(
            _to_cmd_list(file_cmd) + [temp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=cwd,
        )
    finally:
        try:
            pathlib.Path(temp_path).unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass
    if proc.returncode != 0:
        return {
            "status": "error",
            "error_type": "RuntimeError",
            "message": "Lean4 文件模式执行失败",
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
        }
    return {
        "status": "success",
        "outputs": [],
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
    }


def run_repl(cmds, repl_cmd, timeout=15, cwd=None):
    try:
        proc = subprocess.run(
            _to_cmd_list(repl_cmd),
            input=_build_input(cmds),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error_type": "Timeout",
            "message": f"Lean4 REPL 超时（>{timeout}s）",
            "stdout": "",
            "stderr": "",
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "error_type": "NotFound",
            "message": f"无法执行 REPL 命令: {repl_cmd}",
            "stdout": "",
            "stderr": "",
        }

    outputs = _extract_json_lines(proc.stdout or "")
    if proc.returncode != 0:
        return {
            "status": "error",
            "error_type": "RuntimeError",
            "message": "Lean4 REPL 执行失败",
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "outputs": outputs,
        }

    return {
        "status": "success",
        "outputs": outputs,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
    }


def main():
    parser = argparse.ArgumentParser(description="Lean4 REPL 客户端")
    parser.add_argument("--payload", help="JSON 字符串，包含 cmds 列表")
    parser.add_argument("--payload-file", help="payload JSON 文件路径")
    default_repl_cmd = "lake exe repl"
    default_file_cmd = "lake env lean"
    parser.add_argument(
        "--repl-cmd",
        default=default_repl_cmd,
        help="REPL 启动命令（默认: lake exe repl）",
    )
    parser.add_argument(
        "--file-cmd",
        default=default_file_cmd,
        help="文件模式执行命令（默认: lake env lean）",
    )
    parser.add_argument("--lean-path", help="指定 lean 可执行文件路径")
    parser.add_argument("--lake-path", help="指定 lake 可执行文件路径")
    parser.add_argument(
        "--mode",
        default="repl",
        choices=["repl", "file", "auto"],
        help="执行模式（repl 或 file）",
    )
    parser.add_argument("--timeout", type=int, default=15, help="超时秒数")
    parser.add_argument("--cwd", help="REPL 工作目录")
    parser.add_argument("--retries", type=int, default=0, help="失败重试次数")
    parser.add_argument("--log", help="日志路径（JSONL）")
    args = parser.parse_args()

    payload = _parse_payload(args)
    cmds = payload.get("cmds") or []
    if not cmds:
        raise SystemExit("payload 缺少 cmds")

    attempts = 0
    result = None
    while attempts <= args.retries:
        attempts += 1
        if args.mode == "file":
            if args.file_cmd == default_file_cmd:
                if args.lean_path:
                    args.file_cmd = f"\"{args.lean_path}\""
                elif args.lake_path:
                    args.file_cmd = f"\"{args.lake_path}\" env lean"
            result = _run_file_mode(cmds, file_cmd=args.file_cmd, cwd=args.cwd, timeout=args.timeout)
        elif args.mode == "auto":
            if args.repl_cmd == default_repl_cmd and args.lake_path:
                args.repl_cmd = f"\"{args.lake_path}\" exe repl"
            result = run_repl(cmds, repl_cmd=args.repl_cmd, timeout=args.timeout, cwd=args.cwd)
            if result.get("status") != "success":
                stderr = (result.get("stderr") or "").lower()
                if "unknown executable repl" in stderr or "not found" in stderr or "no such file" in stderr:
                    if args.file_cmd == default_file_cmd:
                        if args.lean_path:
                            args.file_cmd = f"\"{args.lean_path}\""
                        elif args.lake_path:
                            args.file_cmd = f"\"{args.lake_path}\" env lean"
                    result = _run_file_mode(cmds, file_cmd=args.file_cmd, cwd=args.cwd, timeout=args.timeout)
        else:
            if args.repl_cmd == default_repl_cmd and args.lake_path:
                args.repl_cmd = f"\"{args.lake_path}\" exe repl"
            result = run_repl(cmds, repl_cmd=args.repl_cmd, timeout=args.timeout, cwd=args.cwd)

        log_event(
            {
                "event": "lean_run",
                "attempt": attempts,
                "mode": args.mode,
                "status": result.get("status"),
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
