"""Lean4 watchdog: kill process if no output for N seconds."""
import argparse
import subprocess
import sys
import threading
import time


def run_watchdog(cmd: list[str], cwd: str | None, timeout_no_output: int) -> int:
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    last_output = time.time()
    lines: list[str] = []

    def _reader():
        nonlocal last_output
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.append(line)
            if line.strip():
                last_output = time.time()

    t = threading.Thread(target=_reader, daemon=True)
    t.start()

    try:
        while True:
            if proc.poll() is not None:
                break
            if timeout_no_output and (time.time() - last_output > timeout_no_output):
                proc.terminate()
                time.sleep(2)
                proc.kill()
                sys.stdout.write("".join(lines))
                print(f"\n[watchdog] terminated after {timeout_no_output}s without output")
                return 124
            time.sleep(0.05)
        t.join(timeout=1)
        sys.stdout.write("".join(lines))
        return proc.returncode or 0
    except Exception:  # noqa: BLE001
        try:
            proc.kill()
        except Exception:
            pass
        return 125


def main() -> int:
    parser = argparse.ArgumentParser(description="watchdog runner")
    parser.add_argument("--cwd", default=None, help="working directory")
    parser.add_argument("--timeout", type=int, default=20, help="no-output timeout seconds")
    parser.add_argument("--", dest="cmd", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    cmd = args.cmd
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        raise SystemExit("missing command after --")
    return run_watchdog(cmd, args.cwd, args.timeout)


if __name__ == "__main__":
    sys.exit(main())
