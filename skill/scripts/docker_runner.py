"""在 Docker 容器内执行命令并返回结构化结果。"""
import argparse
import json
import pathlib
import subprocess
import time


def run_container(image, workdir, command, timeout=120):
    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{workdir}:/workspace",
        "-w",
        "/workspace",
        image,
    ] + command
    start = time.time()
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    elapsed = time.time() - start
    return {
        "status": "success" if proc.returncode == 0 else "error",
        "returncode": proc.returncode,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
        "execution_time": round(elapsed, 4),
        "command": cmd,
    }


def main():
    parser = argparse.ArgumentParser(description="Docker 容器执行器")
    parser.add_argument("--image", required=True, help="Docker 镜像")
    parser.add_argument("--workdir", default=".", help="宿主工作目录")
    parser.add_argument("--timeout", type=int, default=120, help="超时秒数")
    parser.add_argument("cmd", nargs=argparse.REMAINDER, help="容器内执行命令")
    args = parser.parse_args()

    if not args.cmd:
        raise SystemExit("缺少要执行的容器内命令")
    workdir = str(pathlib.Path(args.workdir).resolve())
    result = run_container(args.image, workdir, args.cmd, timeout=args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
