"""Lean compilation and target/axiom checks in the current Lake project."""
from __future__ import annotations

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

from .core import VERSION, ProtocolError, Store, atomic_write, dumps, safe_path, utc

ALLOWED_AXIOMS = frozenset({"propext", "Classical.choice", "Quot.sound"})
EXCLUDED = {".git", ".lake", ".mathprove", "WORKSPACE", "__pycache__", ".venv", "node_modules"}


def source_inventory(project: Path) -> dict[str, str]:
    """Compatibility inventory: source paths, not content fingerprints."""
    if not project.is_dir():
        raise ProtocolError("Lean project directory is missing")
    result: dict[str, str] = {}
    for directory, dirs, files in os.walk(project, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED)
        for name in sorted(files):
            path = Path(directory) / name
            if path.suffix not in {".olean", ".ilean", ".pyc"}:
                rel = path.relative_to(project).as_posix()
                result[rel] = rel
    return result


def verifier_fingerprint() -> dict:
    """Historical API name; the version is informational only."""
    return {"version": VERSION}


def compiled_inventory(project: Path) -> dict[str, str]:
    """Optional artifact path inventory; never a verification prerequisite."""
    result: dict[str, str] = {}
    for directory, dirs, files in os.walk(project, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for name in sorted(files):
            path = Path(directory) / name
            if path.suffix in {".olean", ".ilean", ".so", ".dll", ".dylib"}:
                rel = path.relative_to(project).as_posix()
                result[rel] = rel
    return result


def lock_errors(project: Path) -> list[str]:
    """Historical API name; toolchain and dependency selection belong to Lake."""
    if not (project / "lakefile.toml").is_file() and not (project / "lakefile.lean").is_file():
        return ["Missing Lake configuration"]
    return []


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
    """Report obvious proof placeholders; target axioms determine acceptance."""
    flags: list[str] = []
    rx = re.compile(r"\b(sorry|admit|axiom)\b")
    for rel in inventory:
        if rel.endswith(".lean") and rel != "lakefile.lean":
            content = strip_comments_strings((project / rel).read_text(encoding="utf-8"))
            for match in rx.finditer(content):
                flags.append(f"{rel}:{content.count(chr(10), 0, match.start())+1}: static note: {match.group(0)}")
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
            "elapsed_seconds": round(time.monotonic() - started, 3), "log_path": str(log)}


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
        output = log.read_text(encoding="utf-8", errors="replace").strip()
        if result["exit_code"] != 0 or result["timed_out"]:
            raise ProtocolError("Command failed or timed out: " + " ".join(argv) + "\n" + output[-2000:])
        return output


def dependency_attestations(project: Path) -> list[dict]:
    """Historical API name; retain Lake metadata without Git or source checks."""
    manifest = project / "lake-manifest.json"
    if not manifest.is_file():
        return []
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        packages = data.get("packages", [])
        return [dict(package) for package in packages if isinstance(package, dict)] if isinstance(packages, list) else []
    except (OSError, ValueError, AttributeError):
        return []


def _audit_code(spec: dict, name: str) -> str:
    return (f"import {spec['lean']['module']}\nset_option autoImplicit false\n"
            f"theorem {name} : ({spec['lean']['expected_type']}) := @{spec['lean']['declaration']}\n"
            f"#print axioms {name}\n")


def verify_current_receipt(root: Path, spec: dict, receipt: dict) -> list[str]:
    """Validate the recorded check and goal, not current filesystem identity."""
    if receipt.get("schema") != "mathprove.lean-replay.v9" or receipt.get("result") != "checked_local":
        return ["Last Lean verification is not a successful local verification"]
    errors: list[str] = []
    if "spec" in receipt:
        if receipt["spec"] != spec:
            errors.append("Lean verification belongs to a different mathematical goal")
        if receipt.get("expected_type") != spec.get("lean", {}).get("expected_type"):
            errors.append("Recorded target expected_type does not match the current goal")
    else:
        # Old receipts remain readable, and their retained wrapper identifies the
        # Lean target. Without the spec text, they cannot certify a current goal.
        errors.append("Legacy receipt lacks mathematical goal text; rerun Lean verification")
        try:
            audit = safe_path(root, receipt["audit_source"]["path"], exists=True)
            if audit.read_text(encoding="utf-8") != _audit_code(spec, audit.stem):
                errors.append("Legacy target-audit source does not match the current Lean target")
        except (OSError, ProtocolError, KeyError, TypeError) as exc:
            errors.append("Legacy receipt has no readable matching target audit: " + str(exc))
    axioms = receipt.get("axioms")
    if not isinstance(axioms, list) or any(not isinstance(x, str) or x not in ALLOWED_AXIOMS for x in axioms):
        errors.append("Axiom profile is absent or outside the standard allowlist")
    if not receipt.get("target_type_checked") or not receipt.get("build_succeeded", receipt.get("fresh_build", False)):
        errors.append("No successful Lake build / exact target type check")
    logs = receipt.get("logs", [])
    if not isinstance(logs, list) or len(logs) != 2:
        errors.append("Missing build and target verification logs")
    else:
        for log in logs:
            try:
                path = safe_path(root, log["path"], exists=True)
                if not path.is_file():
                    errors.append("Verification log is not a file")
            except (OSError, ProtocolError, KeyError, TypeError) as exc:
                errors.append(str(exc))
    commands = receipt.get("commands", [])
    if (not isinstance(commands, list) or len(commands) != 2 or any(
            not isinstance(command, dict) or command.get("exit_code") != 0 or command.get("timed_out") is not False
            for command in commands)):
        errors.append("Missing successful build and target command results")
    else:
        build = commands[0].get("argv", [])
        target = commands[1].get("argv", [])
        if not isinstance(build, list) or build[1:] != ["build"] or not isinstance(target, list) or len(target) != 4 or target[1:3] != ["env", "lean"]:
            errors.append("Recorded commands are not a Lake build and Lean target check")
    return errors


def verify(store: Store, run: str, *, acknowledge: bool = False, timeout: int = 1800) -> dict:
    """Compile using Lake's configured toolchain, dependencies and local cache.

    acknowledge remains accepted for callers of older runners, but is not a gate.
    """
    if not 1 <= timeout <= 86400:
        raise ProtocolError("timeout must be 1..86400 seconds per build/check command")
    spec = store.spec(run)
    status = store.status(run)
    if spec["mode"] != "formal":
        raise ProtocolError("Lean verification requires formal mode")
    if status["status"] != "active":
        raise ProtocolError("Run is not active")
    project = safe_path(store.root, spec["lean"]["project"], exists=True)
    inventory = source_inventory(project)
    errors = lock_errors(project)
    lake = shutil.which("lake")
    if not lake:
        errors.append("lake is unavailable; no proof evidence can be produced")
    if errors:
        raise ProtocolError("Lean verification preflight failed:\n" + "\n".join(errors))
    folder = safe_path(store.root, f".mathprove/replays/{run}-{uuid.uuid4().hex}")
    folder.mkdir(parents=True)
    receipt: dict[str, Any] = {
        "schema": "mathprove.lean-replay.v9", "spec": spec,
        "spec_hash": status["spec_hash"], "created": utc(),
        "source_inventory": inventory, "source_paths": list(inventory),
        "project": spec["lean"]["project"], "replay_project": spec["lean"]["project"],
        "expected_type": spec["lean"]["expected_type"],
        "result": "failed", "build_succeeded": False, "target_type_checked": False,
        "proof_status": "not_checked", "verifier": verifier_fingerprint(),
        "axioms": None, "logs": [], "commands": [], "toolchain": {},
        "static_flags": static_flags(project, inventory),
        "trust_scope": "local Lean compilation and axiom inspection; historical result for the recorded goal",
    }
    try:
        log = folder / "build.log"
        command = run_process([lake, "build"], project, log, timeout)
        receipt["commands"].append(command)
        receipt["logs"].append({"path": log.relative_to(store.root).as_posix()})
        if command["exit_code"] != 0 or command["timed_out"]:
            receipt["proof_status"] = "build_failed"
            raise ProtocolError("Lake build failed or timed out")
        receipt["build_succeeded"] = True
        receipt["toolchain"] = {
            "lean_version": _command_output([lake, "env", "lean", "--version"], project, timeout),
            "lake_version": _command_output([lake, "--version"], project, timeout),
        }
        toolchain = project / "lean-toolchain"
        if toolchain.is_file():
            receipt["toolchain"]["lean_toolchain"] = toolchain.read_text(encoding="utf-8").strip()
        receipt["dependencies"] = dependency_attestations(project)
        name = "mathprove_audit_" + uuid.uuid4().hex
        audit = project / (name + ".lean")
        atomic_write(audit, _audit_code(spec, name))
        receipt["audit_source"] = {"path": audit.relative_to(store.root).as_posix()}
        log = folder / "target-and-axioms.log"
        command = run_process([lake, "env", "lean", audit.name], project, log, timeout)
        receipt["commands"].append(command)
        receipt["logs"].append({"path": log.relative_to(store.root).as_posix()})
        if command["exit_code"] != 0 or command["timed_out"]:
            receipt["proof_status"] = "type_check_failed"
            raise ProtocolError("Target type check failed or timed out")
        receipt["target_type_checked"] = True
        axioms = parse_axioms(log.read_text(encoding="utf-8", errors="replace"), name)
        receipt["axioms"] = axioms
        if "sorryAx" in axioms:
            receipt["proof_status"] = "sorry"
            raise ProtocolError("Target depends on sorryAx (sorry/admit)")
        unexpected = set(axioms) - ALLOWED_AXIOMS
        if unexpected:
            receipt["proof_status"] = "unexpected_axioms"
            raise ProtocolError("Unexpected axioms: " + ", ".join(sorted(unexpected)))
        receipt["proof_status"] = "checked"
        receipt["result"] = "checked_local"
    except (OSError, ProtocolError, subprocess.SubprocessError) as exc:
        receipt["failure"] = str(exc)
    # No transaction spans compilation. Compare the goal text before recording
    # evidence; spec_hash may be an opaque revision ID, not a digest of spec.
    with store.tx() as connection:
        current = store._run(connection, run)
        if json.loads(current["spec"]) != spec or current["status"] != "active":
            raise ProtocolError("Run changed during verification; logs retained but receipt is not accepted")
        eid = store._evidence(connection, current, "lean_replay", (dumps(receipt) + "\n").encode("utf-8"),
                              {"project": receipt["project"], "expected_type": receipt["expected_type"]}, "mathprove.runner.v9")
    return {"evidence_id": eid, "result": receipt["result"], "failure": receipt.get("failure"),
            "replay_directory": folder.relative_to(store.root).as_posix(),
            "trust_scope": receipt["trust_scope"]}
