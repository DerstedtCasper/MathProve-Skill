"""Explicit cold Lean replay. No LLM calls and no proof-by-log-import.

Runs reviewed build code with the caller's permissions. A fresh directory is NOT
an OS sandbox. Network access may be used by Lake to obtain pinned dependencies.
Use a disposable OS account/container for untrusted projects. Only invoke after
operator consent; never run from lifecycle hooks.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
import tempfile
import uuid
from typing import Any

from .core import VERSION, ProtocolError, Store, atomic_write, digest, dumps, file_hash, safe_path, utc

ALLOWED_AXIOMS = frozenset({"propext", "Classical.choice", "Quot.sound"})
EXCLUDED = {".git", ".lake", ".mathprove", "WORKSPACE", "__pycache__", ".venv", "node_modules"}
MAX_SOURCE_BYTES = 256 * 1024 * 1024


def source_inventory(project: Path) -> dict[str, str]:
    if not project.is_dir():
        raise ProtocolError("Lean project directory is missing")
    result: dict[str, str] = {}
    total = 0
    for directory, dirs, files in os.walk(project, followlinks=False):
        here = Path(directory)
        for name in dirs + files:
            if (here / name).is_symlink():
                raise ProtocolError("Cold replay refuses source symlinks, including excluded paths")
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED)
        for name in sorted(files):
            p = here / name
            if p.suffix in {".olean", ".ilean", ".pyc"}:
                continue
            total += p.stat().st_size
            if total > MAX_SOURCE_BYTES:
                raise ProtocolError("Project exceeds 256 MiB source cap; isolate a smaller replay project")
            result[p.relative_to(project).as_posix()] = file_hash(p)
    return result


def verifier_fingerprint() -> dict:
    return {"version": VERSION, "runner_sha256": file_hash(Path(__file__)),
            "core_sha256": file_hash(Path(__file__).with_name("core.py"))}


def compiled_inventory(project: Path) -> dict[str, str]:
    """Bind retained local build artifacts; this is not a signature/certificate."""
    result = {}
    total = 0
    for directory, dirs, files in os.walk(project, followlinks=False):
        here = Path(directory)
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for d in dirs:
            if (here / d).is_symlink():
                raise ProtocolError("Replay artifacts contain a symlink directory")
        for name in sorted(files):
            p = here / name
            if p.suffix not in {".olean", ".ilean", ".so", ".dll", ".dylib"}:
                continue
            if p.is_symlink():
                raise ProtocolError("Replay artifacts contain a symlink")
            total += p.stat().st_size
            if total > 4 * 1024**3 or len(result) >= 100000:
                raise ProtocolError("Compiled artifact inventory exceeds the 4 GiB / 100k-file profile cap")
            result[p.relative_to(project).as_posix()] = file_hash(p)
    return result


def lock_errors(project: Path) -> list[str]:
    errors: list[str] = []
    tc = project / "lean-toolchain"
    manifest = project / "lake-manifest.json"
    if not tc.is_file() or not re.fullmatch(r"leanprover/lean4:v\d+\.\d+\.\d+(?:-rc\d+)?", tc.read_text(encoding="utf-8").strip()):
        errors.append("lean-toolchain must pin leanprover/lean4:vMAJOR.MINOR.PATCH (optional -rcN)")
    if not (project / "lakefile.toml").is_file() and not (project / "lakefile.lean").is_file():
        errors.append("Missing Lake configuration")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        packages = data["packages"]
        if not isinstance(packages, list):
            raise ValueError("packages is not a list")
        names: set[str] = set()
        for package in packages:
            if not isinstance(package, dict) or package.get("type") != "git" or not re.fullmatch(r"[0-9a-fA-F]{40}", str(package.get("rev", ""))):
                errors.append("All dependencies must be git packages pinned to full 40-hex commits; path/registry-only dependencies are unsupported")
            if not isinstance(package, dict):
                continue
            name = package.get("name", "")
            if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", name) or name in names:
                errors.append("Manifest has an unsafe or duplicate package name")
            names.add(str(name))
            url = package.get("url", "")
            if not isinstance(url, str) or not url.startswith("https://"):
                errors.append("Cold replay accepts only HTTPS git dependency URLs")
    except (OSError, ValueError, KeyError, TypeError):
        errors.append("A readable lake-manifest.json with a packages array is required, including for zero dependencies")
    return errors


def strip_comments_strings(source: str) -> str:
    """Conservative lexical aid only; never substitutes for Lean's kernel."""
    out: list[str] = []
    i = 0
    depth = 0
    string = False
    while i < len(source):
        if depth:
            if source.startswith("/-", i):
                depth += 1; i += 2
            elif source.startswith("-/", i):
                depth -= 1; i += 2
            else:
                out.append("\n" if source[i] == "\n" else " "); i += 1
        elif string:
            if source[i] == "\\":
                i += 2
            elif source[i] == '"':
                string = False; i += 1
            else:
                i += 1
            out.append(" ")
        elif source.startswith("--", i):
            end = source.find("\n", i)
            i = len(source) if end < 0 else end
        elif source.startswith("/-", i):
            depth = 1; i += 2; out.append(" ")
        elif source[i] == '"':
            string = True; i += 1; out.append(" ")
        else:
            out.append(source[i]); i += 1
    return "".join(out)


def static_flags(project: Path, inventory: dict[str, str]) -> list[str]:
    flags: list[str] = []
    # Strict candidate policy; legitimate custom metaprograms need a separately
    # reviewed dependency package, not a blanket permission in final candidates.
    rx = re.compile(r"\b(sorry|admit|axiom|unsafe|native_decide|run_cmd|elab|macro|implemented_by|extern)\b|#eval")
    for rel in inventory:
        if rel.endswith(".lean") and rel != "lakefile.lean":
            content = strip_comments_strings((project / rel).read_text(encoding="utf-8"))
            for m in rx.finditer(content):
                flags.append(f"{rel}:{content.count(chr(10), 0, m.start())+1}: strict static precheck: {m.group(0)}")
    return flags


def run_process(argv: list[str], cwd: Path, log: Path, timeout: int) -> dict:
    """No shell evaluation. Kill the spawned process tree on a timeout."""
    if timeout < 1:
        raise ProtocolError("timeout must be positive")
    started = time.monotonic()
    timed_out = False
    with log.open("wb") as stream:
        proc = subprocess.Popen(argv, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=(os.name != "nt"))
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            if os.name == "nt":
                # PID is a local integer, not user-provided shell syntax.
                try:
                    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False)
                except (OSError, subprocess.TimeoutExpired):
                    proc.kill()
            else:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            code = proc.wait(timeout=10)
        except BaseException:
            if os.name != "nt":
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                proc.kill()
            proc.wait()
            raise
    return {"argv": argv, "exit_code": code, "timed_out": timed_out,
            "elapsed_seconds": round(time.monotonic() - started, 3), "log_sha256": file_hash(log)}


def parse_axioms(output: str, declaration: str) -> list[str]:
    escaped = re.escape(declaration)
    none = re.findall(r"'" + escaped + r"' does not depend on any axioms", output)
    found = re.findall(r"'" + escaped + r"' depends on axioms:\s*\[([^\]]*)\]", output, re.S)
    if len(none) + len(found) != 1:
        raise ProtocolError("Missing, ambiguous, or unsupported Lean axiom output; refusing to infer success")
    if none:
        return []
    names = [x.strip() for x in found[0].split(",") if x.strip()]
    if not names and found[0].strip():
        raise ProtocolError("Unparseable axiom list")
    return sorted(set(names))


def _command_output(argv: list[str], cwd: Path, timeout: int = 20) -> str:
    with tempfile.TemporaryDirectory(prefix="mathprove-command-") as directory:
        log = Path(directory) / "output.log"
        result = run_process(argv, cwd, log, timeout)
        if log.stat().st_size > 2 * 1024 * 1024:
            raise ProtocolError("Command metadata output exceeds 2 MiB")
        output = log.read_text(encoding="utf-8", errors="replace").strip()
        if result["exit_code"] != 0 or result["timed_out"]:
            raise ProtocolError("Command failed or timed out: " + " ".join(argv) + "\n" + output[-2000:])
        return output


def dependency_attestations(project: Path) -> list[dict]:
    packages = json.loads((project / "lake-manifest.json").read_text(encoding="utf-8"))["packages"]
    attestations = []
    if packages and not shutil.which("git"):
        raise ProtocolError("git is required to check materialized dependencies")
    for package in packages:
        path = safe_path(project, f".lake/packages/{package['name']}", exists=True)
        head = _command_output(["git", "rev-parse", "HEAD"], path)
        if head.lower() != package["rev"].lower():
            raise ProtocolError("Materialized dependency revision mismatch: " + package["name"])
        dirty = _command_output(["git", "status", "--porcelain", "--untracked-files=normal"], path)
        if dirty:
            raise ProtocolError("Materialized dependency has modified/untracked files: " + package["name"])
        # Hash sources too; repository identity alone is not an artifact fingerprint.
        attestations.append({"name": package["name"], "rev": head, "source_hash": digest(source_inventory(path))})
    return attestations


def verify_current_receipt(root: Path, spec: dict, receipt: dict) -> list[str]:
    errors = []
    if receipt.get("schema") != "mathprove.lean-replay.v9" or receipt.get("result") != "checked_local":
        return ["Last clean replay is not a successful local verification"]
    if receipt.get("verifier") != verifier_fingerprint():
        errors.append("Verifier implementation changed after replay")
    if receipt.get("spec_hash") != digest(spec):
        errors.append("Replay statement lock is stale")
    try:
        project = safe_path(root, spec["lean"]["project"], exists=True)
        errors.extend(lock_errors(project))
        if digest(source_inventory(project)) != receipt.get("source_hash"):
            errors.append("Lean source/config/dependency lock changed after replay")
        audit = receipt.get("audit_source", {})
        audit_path = safe_path(root, audit["path"], exists=True)
        if file_hash(audit_path) != audit.get("sha256"):
            errors.append("Generated target-audit source hash mismatch")
        fresh = safe_path(root, receipt["replay_project"], exists=True)
        retained = source_inventory(fresh)
        retained.pop(audit_path.name, None)
        if digest(retained) != receipt.get("source_hash"):
            errors.append("Retained replay input snapshot changed")
        if not receipt.get("compiled_artifacts") or compiled_inventory(fresh) != receipt.get("compiled_artifacts"):
            errors.append("Retained compiled artifact inventory changed or is absent")
        for dep in receipt.get("dependencies", []):
            dep_path = safe_path(fresh, ".lake/packages/" + dep["name"], exists=True)
            if digest(source_inventory(dep_path)) != dep["source_hash"]:
                errors.append("Retained dependency source changed: " + dep["name"])
        for tool in ("lean", "lake"):
            binary = Path(receipt["toolchain"][tool + "_binary_path"])
            if not binary.is_file() or file_hash(binary) != receipt["toolchain"][tool + "_binary_sha256"]:
                errors.append("Resolved toolchain binary changed or disappeared: " + tool)
        for log in receipt.get("logs", []):
            path = safe_path(root, log["path"], exists=True)
            if file_hash(path) != log["sha256"]:
                errors.append("Replay log hash mismatch")
    except (OSError, ProtocolError, KeyError) as e:
        errors.append(str(e))
    if receipt.get("axioms") is None or not isinstance(receipt.get("axioms"), list) or any(
            x not in ALLOWED_AXIOMS for x in receipt.get("axioms", [])):
        errors.append("Axiom profile is absent or outside the standard allowlist")
    if not receipt.get("target_type_checked") or not receipt.get("fresh_build"):
        errors.append("No fresh build / locked target type check")
    if len(receipt.get("logs", [])) != 2 or not receipt.get("toolchain"):
        errors.append("Missing replay provenance")
    commands = receipt.get("commands", [])
    if len(commands) != 2 or any(x.get("exit_code") != 0 or x.get("timed_out") is not False for x in commands):
        errors.append("Missing successful build and target command results")
    return errors


def verify(store: Store, run: str, *, acknowledge: bool, timeout: int = 1800) -> dict:
    if not acknowledge:
        raise ProtocolError("Build files execute code. Review them and pass --allow-build only with operator consent")
    if not 1 <= timeout <= 86400:
        raise ProtocolError("timeout must be 1..86400 seconds per build/check command")
    spec = store.spec(run)
    if spec["mode"] != "formal":
        raise ProtocolError("Lean replay requires formal mode")
    if store.status(run)["status"] != "active":
        raise ProtocolError("Run is not active")
    project = safe_path(store.root, spec["lean"]["project"], exists=True)
    inventory = source_inventory(project)
    errors = lock_errors(project) + static_flags(project, inventory)
    lake = shutil.which("lake")
    if not lake:
        errors.append("lake is unavailable; no proof evidence can be produced")
    if errors:
        raise ProtocolError("Replay preflight failed:\n" + "\n".join(errors))
    folder = safe_path(store.root, f".mathprove/replays/{run}-{uuid.uuid4().hex}")
    fresh = folder / "project"
    fresh.mkdir(parents=True)
    for rel in inventory:
        dst = safe_path(fresh, rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(project / rel, dst)
    if digest(source_inventory(fresh)) != digest(inventory):
        raise ProtocolError("Source changed while copying; rerun with a stable candidate")
    source_hash = digest(inventory)
    receipt: dict[str, Any] = {"schema": "mathprove.lean-replay.v9", "spec_hash": digest(spec),
        "source_hash": source_hash, "source_inventory": inventory, "created": utc(),
        "result": "failed", "fresh_build": True, "target_type_checked": False,
        "verifier": verifier_fingerprint(), "replay_project": fresh.relative_to(store.root).as_posix(),
        "dependency_rebuild_guarantee": "Not attested; reviewed Lake scripts may use downloaded caches",
        "axioms": None, "logs": [], "commands": [], "toolchain": {},
        "trust_scope": "cooperative local replay; not an OS sandbox or third-party certificate"}
    try:
        version = _command_output([lake, "env", "lean", "--version"], fresh, timeout)
        executable = _command_output([lake, "env", "which" if os.name != "nt" else "where", "lean"], fresh, timeout).splitlines()[0]
        lean_bin = Path(executable)
        if not lean_bin.is_file():
            raise ProtocolError("Cannot identify resolved Lean executable")
        expected_version = (project / "lean-toolchain").read_text(encoding="utf-8").strip().split(":v", 1)[1]
        if not re.search(r"(?<![0-9.])" + re.escape(expected_version) + r"(?![0-9.])", version):
            raise ProtocolError("Resolved Lean version does not match lean-toolchain")
        receipt["toolchain"] = {"lean_version": version, "lean_binary_path": str(lean_bin.resolve()),
                                "lake_binary_path": str(Path(lake).resolve()), "lean_binary_sha256": file_hash(lean_bin),
                                "lake_binary_sha256": file_hash(Path(lake)),
                                "lean_toolchain": (project / "lean-toolchain").read_text(encoding="utf-8").strip()}
        for name, argv in [("build", [lake, "build"])]:
            log = folder / (name + ".log")
            command = run_process(argv, fresh, log, timeout)
            receipt["commands"].append(command)
            receipt["logs"].append({"path": log.relative_to(store.root).as_posix(), "sha256": file_hash(log)})
            if command["exit_code"] != 0 or command["timed_out"]:
                raise ProtocolError("Cold Lake build failed or timed out")
        # The generated wrapper checks the exact operator-reviewed expected type,
        # not merely that a theorem with the requested name exists.
        name = "mathprove_audit_" + uuid.uuid4().hex
        audit = fresh / (name + ".lean")
        code = (f"import {spec['lean']['module']}\nset_option autoImplicit false\n"
                f"theorem {name} : ({spec['lean']['expected_type']}) := @{spec['lean']['declaration']}\n"
                f"#print axioms {name}\n")
        atomic_write(audit, code)
        receipt["audit_source"] = {"path": audit.relative_to(store.root).as_posix(), "sha256": file_hash(audit)}
        log = folder / "target-and-axioms.log"
        command = run_process([lake, "env", "lean", audit.name], fresh, log, timeout)
        receipt["commands"].append(command)
        receipt["logs"].append({"path": log.relative_to(store.root).as_posix(), "sha256": file_hash(log)})
        if command["exit_code"] != 0 or command["timed_out"]:
            raise ProtocolError("Locked target type check failed or timed out")
        if log.stat().st_size > 16 * 1024 * 1024:
            raise ProtocolError("Axiom output exceeds parsing cap")
        axioms = parse_axioms(log.read_text(encoding="utf-8", errors="replace"), name)
        receipt["axioms"] = axioms
        if not set(axioms) <= ALLOWED_AXIOMS:
            raise ProtocolError("Unexpected axioms: " + ", ".join(sorted(set(axioms) - ALLOWED_AXIOMS)))
        receipt["target_type_checked"] = True
        receipt["dependencies"] = dependency_attestations(fresh)
        receipt["compiled_artifacts"] = compiled_inventory(fresh)
        if not receipt["compiled_artifacts"]:
            raise ProtocolError("No compiled artifacts were retained; check the Lake build targets")
        for rel, expected in inventory.items():
            if not (fresh / rel).is_file() or file_hash(fresh / rel) != expected:
                raise ProtocolError("Build mutated locked inputs: " + rel)
        fresh_inventory = source_inventory(fresh)
        fresh_inventory.pop(audit.name, None)
        if fresh_inventory != inventory:
            raise ProtocolError("Build added or removed undeclared project inputs")
        if digest(source_inventory(project)) != source_hash:
            raise ProtocolError("Original project changed during verification")
        receipt["result"] = "checked_local"
    except (OSError, ProtocolError, subprocess.SubprocessError) as e:
        receipt["failure"] = str(e)
    # No transaction is held across compilation. Recheck the statement before commit.
    with store.tx() as c:
        r = store._run(c, run)
        if r["spec_hash"] != digest(spec) or r["status"] != "active":
            raise ProtocolError("Run changed during replay; logs retained but receipt is not accepted")
        eid = store._evidence(c, r, "lean_replay", (dumps(receipt) + "\n").encode("utf-8"),
                              {"source_hash": source_hash}, "mathprove.runner.v9")
    return {"evidence_id": eid, "result": receipt["result"], "failure": receipt.get("failure"),
            "replay_directory": folder.relative_to(store.root).as_posix(),
            "trust_scope": receipt["trust_scope"]}
