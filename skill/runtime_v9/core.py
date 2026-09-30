"""Transactional research state; Python 3.11+, standard library only.

This is a cooperative, single-user controller. SQLite transactions protect against
accidental concurrent writes, NOT against another process with the same OS access.
No agent self-report, imported receipt, score or vote is proof authority.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from typing import Any, Iterator
import uuid

VERSION = "9.1.0"
STAGES = ("spec", "plan", "candidate", "refutation", "verify", "release")
ROLES = ("coordinator", "formalizer", "strategist", "librarian", "prover",
         "experimenter", "refuter", "integrator", "auditor")
KINDS = ("spec_review", "plan", "candidate", "refutation", "literature",
         "computation", "counterexample_candidate", "note", "integration")
STATUSES = ("active", "paused", "reviewed_research", "reviewed_formal_local")

class ProtocolError(ValueError):
    """An invalid transition, stale result, or incomplete evidence."""


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    """Legacy API for deterministic metadata keys; no cryptographic hashing."""
    return dumps(value)


def file_hash(path: Path) -> str:
    """Retired compatibility API: return a path reference without reading bytes."""
    return str(path)


def _is_json(value: str) -> bool:
    try:
        json.loads(value)
        return True
    except ValueError:
        return False


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", value):
        raise ProtocolError("IDs must be 1-64 ASCII letters/digits, '_' or '-'.")
    return value


def text(value: Any, field: str, limit: int = 20000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ProtocolError(f"{field}: a nonempty string of at most {limit} characters is required")
    return value


def json_object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def strict_json(path: Path) -> Any:
    if path.stat().st_size > 4 * 1024 * 1024:
        raise ProtocolError("JSON file exceeds 4 MiB")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=json_object,
                      parse_constant=lambda x: (_ for _ in ()).throw(ProtocolError(f"Invalid JSON {x}")))


def atomic_write(path: Path, data: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ProtocolError(f"Refusing symlink destination: {path}")
    tmp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        with tmp.open("wb") as f:
            f.write(data.encode("utf-8") if isinstance(data, str) else data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def safe_path(root: Path, name: str | Path, *, exists: bool = False) -> Path:
    """Reject traversal and existing symlink components, including dangling ones."""
    root = root.resolve()
    p = Path(name)
    p = p if p.is_absolute() else root / p
    # Check the lexical path before resolving: a symlink to an in-root file is also rejected.
    try:
        rel = p.absolute().relative_to(root)
    except ValueError as e:
        raise ProtocolError("Path is outside the research root") from e
    cur = root
    for part in rel.parts:
        if part == "..":
            raise ProtocolError("Parent traversal is not permitted")
        cur = cur / part
        if cur.is_symlink():
            raise ProtocolError(f"Symlinks are not permitted: {cur}")
    p = p.resolve()
    if not p.is_relative_to(root):
        raise ProtocolError("Path escaped the research root")
    if exists and not p.exists():
        raise ProtocolError(f"Missing path: {p}")
    return p


def validate_spec(spec: Any) -> dict:
    if not isinstance(spec, dict):
        raise ProtocolError("Spec must be an object")
    text(spec.get("statement"), "statement")
    if spec.get("mode") not in ("research", "formal"):
        raise ProtocolError("mode must be research or formal")
    if not isinstance(spec.get("assumptions"), list) or not all(isinstance(x, str) for x in spec["assumptions"]):
        raise ProtocolError("assumptions must be a list of strings (empty is allowed)")
    if not isinstance(spec.get("symbols"), dict):
        raise ProtocolError("symbols must be an object (empty is allowed)")
    if spec["mode"] == "formal":
        lean = spec.get("lean")
        if not isinstance(lean, dict):
            raise ProtocolError("formal mode requires a lean object")
        for key in ("project", "module", "declaration", "expected_type"):
            text(lean.get(key), "lean." + key)
        for key in ("module", "declaration"):
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_']*(\.[A-Za-z_][A-Za-z0-9_']*)*", lean[key]):
                raise ProtocolError(f"lean.{key}: this adapter supports simple dotted identifiers only")
        t = lean["expected_type"]
        if any(x in t for x in ("\n", "\r", "--", "/-", "#", ";")) or re.search(
                r"\b(theorem|axiom|def|opaque|elab|macro|syntax|run_cmd|namespace|set_option|sorry|admit|unsafe|native_decide)\b", t):
            raise ProtocolError("expected_type must be one reviewed expression on one line, not Lean commands")
    # Deep copy also rejects NaN, non-JSON objects etc.
    return json.loads(dumps(spec))


SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runs(
 id TEXT PRIMARY KEY, revision INTEGER NOT NULL, spec TEXT NOT NULL,
 spec_hash TEXT NOT NULL, phase INTEGER NOT NULL DEFAULT -1,
 status TEXT NOT NULL DEFAULT 'active', max_parallel INTEGER NOT NULL,
 max_attempts INTEGER NOT NULL, budget_attempts INTEGER NOT NULL,
 created TEXT NOT NULL, pause_reason TEXT);
CREATE TABLE IF NOT EXISTS tasks(
 run_id TEXT NOT NULL REFERENCES runs(id), id TEXT NOT NULL,
 spec_hash TEXT NOT NULL, role TEXT NOT NULL, objective TEXT NOT NULL,
 deps TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'queued',
 owner TEXT, token TEXT, expires REAL, attempts INTEGER NOT NULL DEFAULT 0,
 result TEXT, work_dir TEXT, PRIMARY KEY(run_id,id));
CREATE TABLE IF NOT EXISTS evidence(
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
 spec_hash TEXT NOT NULL, kind TEXT NOT NULL, sha256 TEXT NOT NULL,
 object_path TEXT NOT NULL, origin TEXT, origin_sha256 TEXT,
 metadata TEXT NOT NULL, producer TEXT NOT NULL, created TEXT NOT NULL, withdrawn INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS issues(
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
 spec_hash TEXT NOT NULL, summary TEXT NOT NULL, resolved INTEGER NOT NULL DEFAULT 0,
 resolution_evidence TEXT, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS gates(
 id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL REFERENCES runs(id),
 stage TEXT NOT NULL, spec_hash TEXT NOT NULL, snapshot TEXT NOT NULL,
 accepted INTEGER NOT NULL, reasons TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reviews(
 id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL REFERENCES runs(id),
 snapshot TEXT NOT NULL, reviewer TEXT NOT NULL, note TEXT NOT NULL,
 created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events(
 seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, event TEXT NOT NULL,
 payload TEXT NOT NULL, previous TEXT NOT NULL, hash TEXT NOT NULL,
 dedupe TEXT UNIQUE, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(session_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id));
CREATE INDEX IF NOT EXISTS evidence_run ON evidence(run_id,spec_hash,kind);
CREATE INDEX IF NOT EXISTS events_run ON events(run_id,seq);
"""


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


class Store:
    def __init__(self, root: str | Path, *, create: bool = False):
        self.root = Path(root).expanduser().resolve()
        if not self.root.is_dir():
            raise ProtocolError("Research root must be an existing directory")
        self.state = safe_path(self.root, ".mathprove")
        self.db = safe_path(self.root, ".mathprove/state.sqlite3")
        if create:
            self.state.mkdir(mode=0o700, exist_ok=True)
            for name in ("objects", "checkpoints", "replays"):
                safe_path(self.root, self.state / name).mkdir(exist_ok=True)
            with self.connect() as c:
                c.executescript(SCHEMA)
                row = c.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
                if row and row[0] != "9":
                    raise ProtocolError("Unknown schema; refusing automatic migration")
                c.execute("INSERT OR IGNORE INTO meta VALUES('schema','9')")
        elif not self.db.is_file():
            raise ProtocolError("Workspace not initialized; run init first")
        with self.connect() as c:
            row = c.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
            if not row or row[0] != "9":
                raise ProtocolError("Unsupported state schema")

    def connect(self) -> sqlite3.Connection:
        safe_path(self.root, self.db)
        for suffix in ("-wal", "-shm", "-journal"):
            safe_path(self.root, str(self.db) + suffix)
        c = sqlite3.connect(self.db, timeout=5, isolation_level=None, factory=ClosingConnection)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=5000")
        return c

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        c = self.connect()
        try:
            c.execute("BEGIN IMMEDIATE")
            yield c
            c.execute("COMMIT")
        except BaseException:
            if c.in_transaction:
                c.execute("ROLLBACK")
            raise
        finally:
            c.close()

    def _run(self, c: sqlite3.Connection, run: str) -> sqlite3.Row:
        row = c.execute("SELECT * FROM runs WHERE id=?", (identifier(run),)).fetchone()
        if not row:
            raise ProtocolError("Unknown run")
        return row

    def _event(self, c: sqlite3.Connection, run: str | None, event: str,
               payload: Any, dedupe: str | None = None) -> bool:
        if dedupe and c.execute("SELECT 1 FROM events WHERE dedupe=?", (dedupe,)).fetchone():
            return False
        c.execute("INSERT INTO events(run_id,event,payload,previous,hash,dedupe,created) VALUES(?,?,?,?,?,?,?)",
                  (run, event, dumps(payload), "", "event-" + uuid.uuid4().hex, dedupe, utc()))
        return True

    def create_run(self, run: str, spec: dict, *, max_parallel: int = 2,
                   max_attempts: int = 3, budget_attempts: int = 32) -> dict:
        identifier(run)
        spec = validate_spec(spec)
        if not (1 <= max_parallel <= 32 and 1 <= max_attempts <= 100 and 1 <= budget_attempts <= 10000):
            raise ProtocolError("Invalid parallelism/attempt limits")
        with self.tx() as c:
            if c.execute("SELECT 1 FROM runs WHERE id=?", (run,)).fetchone():
                raise ProtocolError("Run exists; use revise explicitly, or a new run ID")
            c.execute("INSERT INTO runs(id,revision,spec,spec_hash,max_parallel,max_attempts,budget_attempts,created) VALUES(?,?,?,?,?,?,?,?)",
                      (run, 1, dumps(spec), f"{run}:1", max_parallel, max_attempts, budget_attempts, utc()))
            self._event(c, run, "run.created", {"spec_revision": f"{run}:1", "mode": spec["mode"]})
        return self.status(run)

    def revise(self, run: str, spec: dict, reason: str) -> dict:
        spec = validate_spec(spec)
        text(reason, "revision reason")
        with self.tx() as c:
            r = self._run(c, run)
            if json.loads(r["spec"]) == spec:
                raise ProtocolError("Spec is unchanged")
            c.execute("UPDATE runs SET revision=revision+1,spec=?,spec_hash=?,phase=-1,status='active',pause_reason=NULL WHERE id=?",
                      (dumps(spec), f"{run}:{r['revision'] + 1}", run))
            # Old tasks and evidence remain inspectable but cannot support the new lock.
            c.execute("UPDATE tasks SET state='superseded',token=NULL,expires=NULL WHERE run_id=?", (run,))
            self._event(c, run, "spec.revised", {"old": r["spec_hash"], "new": f"{run}:{r['revision'] + 1}", "reason": reason})
        return self.status(run)

    def add_task(self, run: str, task: str, role: str, objective: str,
                 deps: list[str] | None = None) -> dict:
        identifier(task)
        if role not in ROLES:
            raise ProtocolError("Unknown role")
        text(objective, "objective")
        deps = deps or []
        if not isinstance(deps, list) or not all(isinstance(d, str) for d in deps) or len(set(deps)) != len(deps):
            raise ProtocolError("Dependencies must be a duplicate-free list")
        with self.tx() as c:
            r = self._run(c, run)
            self._require_active(r)
            if c.execute("SELECT 1 FROM tasks WHERE run_id=? AND id=?", (run, task)).fetchone():
                raise ProtocolError("Task ID exists; use a new ID for revised work")
            for dep in deps:
                identifier(dep)
                d = c.execute("SELECT spec_hash FROM tasks WHERE run_id=? AND id=?", (run, dep)).fetchone()
                if not d or d[0] != r["spec_hash"]:
                    raise ProtocolError("Dependency does not exist under the current statement lock")
            # Edges point only to existing nodes, so creation cannot introduce cycles.
            c.execute("INSERT INTO tasks(run_id,id,spec_hash,role,objective,deps) VALUES(?,?,?,?,?,?)",
                      (run, task, r["spec_hash"], role, objective, dumps(deps)))
            self._event(c, run, "task.created", {"task": task, "role": role, "deps": deps})
            self._invalidate_release(c, run)
        return {"task_id": task, "state": "queued"}

    @staticmethod
    def _require_active(r: sqlite3.Row) -> None:
        if r["status"] != "active":
            raise ProtocolError("Run is not active; explicitly resume before adding or claiming work")

    @staticmethod
    def _invalidate_release(c: sqlite3.Connection, run: str) -> None:
        c.execute("UPDATE runs SET phase=MIN(phase,4),status=CASE WHEN status LIKE 'reviewed_%' THEN 'active' ELSE status END WHERE id=?", (run,))

    def _expire(self, c: sqlite3.Connection, r: sqlite3.Row, now: float) -> None:
        expired = c.execute("SELECT id,attempts FROM tasks WHERE run_id=? AND state='leased' AND expires<=?", (r["id"], now)).fetchall()
        for t in expired:
            state = "blocked" if t["attempts"] >= r["max_attempts"] else "queued"
            c.execute("UPDATE tasks SET state=?,owner=NULL,token=NULL,expires=NULL WHERE run_id=? AND id=?",
                      (state, r["id"], t["id"]))
            self._event(c, r["id"], "lease.expired", {"task": t["id"], "state": state})

    def claim(self, run: str, owner: str, task: str | None = None, *, ttl: int = 900) -> dict:
        text(owner, "owner", 128)
        if not 1 <= ttl <= 86400:
            raise ProtocolError("Lease ttl must be 1..86400 seconds")
        if task is not None:
            identifier(task)
        with self.tx() as c:
            r = self._run(c, run)
            self._require_active(r)
            now = time.time()
            self._expire(c, r, now)
            used = c.execute("SELECT COALESCE(SUM(attempts),0) FROM tasks WHERE run_id=?", (run,)).fetchone()[0]
            if used >= r["budget_attempts"]:
                raise ProtocolError("Attempt budget exhausted; checkpoint and pause, or explicitly raise the budget")
            active = c.execute("SELECT COUNT(*) FROM tasks WHERE run_id=? AND state='leased'", (run,)).fetchone()[0]
            if active >= r["max_parallel"]:
                raise ProtocolError("Parallel lease limit reached")
            rows = c.execute("SELECT * FROM tasks WHERE run_id=? AND spec_hash=? AND state='queued' ORDER BY rowid",
                             (run, r["spec_hash"])).fetchall()
            selected = None
            for t in rows:
                if t["attempts"] >= r["max_attempts"]:
                    continue
                if task is not None and t["id"] != task:
                    continue
                if all(self._dependency_ready(c, run, dep)
                       for dep in json.loads(t["deps"])):
                    selected = t
                    break
            if selected is None:
                raise ProtocolError("No ready task: missing dependencies, blocked task, or empty queue")
            token = secrets.token_urlsafe(24)
            work = f"WORKSPACE/{run}/tasks/{selected['id']}/attempt-{selected['attempts'] + 1}-{uuid.uuid4().hex[:8]}"
            safe_path(self.root, work).mkdir(parents=True, exist_ok=False)
            c.execute("UPDATE tasks SET state='leased',owner=?,token=?,expires=?,attempts=attempts+1,work_dir=? WHERE run_id=? AND id=?",
                      (owner, token, now + ttl, work, run, selected["id"]))
            self._event(c, run, "task.claimed", {"task": selected["id"], "owner": owner, "work_dir": work, "expires": now + ttl})
            return {"run_id": run, "task_id": selected["id"], "role": selected["role"],
                    "objective": selected["objective"], "spec_hash": r["spec_hash"],
                    "lease_token": token, "expires": now + ttl, "work_dir": work,
                    "dependencies": json.loads(selected["deps"])}

    def _task_artifact_errors(self, task: sqlite3.Row) -> list[str]:
        if not task["result"]:
            return []
        result = json.loads(task["result"])
        paths = result.get("artifacts", []) or [ref["path"] for ref in result.get("artifact_hashes", [])]
        errors = []
        for name in paths:
            try:
                safe_path(self.root, name, exists=True)
            except (OSError, ProtocolError):
                errors.append("Task artifact missing: " + task["id"] + ":" + name)
        return errors

    def _dependency_ready(self, c: sqlite3.Connection, run: str, task: str) -> bool:
        t = c.execute("SELECT * FROM tasks WHERE run_id=? AND id=?", (run, task)).fetchone()
        return bool(t and t["state"] == "done" and t["result"] and json.loads(t["result"]).get("outcome") == "candidate" and not self._task_artifact_errors(t))

    def reap(self, run: str) -> dict:
        with self.tx() as c:
            r = self._run(c, run)
            self._expire(c, r, time.time())
        return self.status(run)

    def invalidate_task(self, run: str, task: str, reason: str) -> dict:
        """Cancel an invalid result and its descendants; never erase old results."""
        text(reason, "invalidation reason")
        with self.tx() as c:
            r = self._run(c, run)
            rows = c.execute("SELECT id,deps FROM tasks WHERE run_id=? AND spec_hash=?", (run, r["spec_hash"])).fetchall()
            if task not in {t["id"] for t in rows}:
                raise ProtocolError("Unknown current task")
            affected = {task}
            changed = True
            while changed:
                changed = False
                for t in rows:
                    if t["id"] not in affected and affected.intersection(json.loads(t["deps"])):
                        affected.add(t["id"])
                        changed = True
            for key in affected:
                c.execute("UPDATE tasks SET state='cancelled',token=NULL,expires=NULL WHERE run_id=? AND id=?", (run, key))
            self._invalidate_release(c, run)
            self._event(c, run, "task.invalidated", {"tasks": sorted(affected), "reason": reason})
            issue_id = self._issue(c, r, "Task invalidation requires dependent evidence review: " + task + ": " + reason)
        return {"cancelled": sorted(affected), "issue_id": issue_id, "next_action": "Create new task IDs; withdraw affected evidence explicitly and rerun gates"}

    def heartbeat(self, run: str, task: str, owner: str, token: str, ttl: int = 900) -> dict:
        if not 1 <= ttl <= 86400:
            raise ProtocolError("Lease ttl must be 1..86400 seconds")
        with self.tx() as c:
            self._require_active(self._run(c, run))
            t = self._lease(c, run, task, owner, token)
            expires = time.time() + ttl
            c.execute("UPDATE tasks SET expires=? WHERE run_id=? AND id=?", (expires, run, t["id"]))
            return {"expires": expires}

    def _lease(self, c: sqlite3.Connection, run: str, task: str, owner: str, token: str) -> sqlite3.Row:
        r = self._run(c, run)
        t = c.execute("SELECT * FROM tasks WHERE run_id=? AND id=?", (run, identifier(task))).fetchone()
        if not t or t["state"] != "leased" or t["owner"] != owner or not secrets.compare_digest(t["token"] or "", token):
            raise ProtocolError("No matching active lease")
        if t["expires"] <= time.time() or t["spec_hash"] != r["spec_hash"]:
            raise ProtocolError("Expired lease or stale statement lock; result cannot be accepted")
        return t

    def finish(self, run: str, task: str, owner: str, token: str, result: dict) -> dict:
        if not isinstance(result, dict) or result.get("outcome") not in ("candidate", "blocked", "refuted", "no_progress"):
            raise ProtocolError("outcome must be candidate, blocked, refuted or no_progress; never 'proved'")
        if len(dumps(result)) > 65536:
            raise ProtocolError("Task result exceeds 64k characters; store large content as an artifact")
        text(result.get("summary"), "summary", 6000)
        text(result.get("next_action"), "next_action", 3000)
        if not isinstance(result.get("artifacts", []), list) or len(result.get("artifacts", [])) > 128:
            raise ProtocolError("artifacts must be a list of relative paths")
        with self.tx() as c:
            r = self._run(c, run)
            self._require_active(r)
            t = self._lease(c, run, task, owner, token)
            if result.get("spec_hash") != r["spec_hash"] or result.get("task_id") != task:
                raise ProtocolError("Result must bind the leased task and current statement revision")
            refs = []
            work = safe_path(self.root, t["work_dir"], exists=True)
            for name in result.get("artifacts", []):
                p = safe_path(self.root, name, exists=True)
                if not p.is_file() or not p.is_relative_to(work):
                    raise ProtocolError("Task results may reference files only inside their leased work directory")
                refs.append({"path": p.relative_to(self.root).as_posix()})
            state = "done" if result["outcome"] in ("candidate", "refuted") else (
                "blocked" if t["attempts"] >= r["max_attempts"] or result["outcome"] == "blocked" else "queued")
            saved = {**result, "artifacts": [ref["path"] for ref in refs]}
            c.execute("UPDATE tasks SET state=?,result=?,token=NULL,expires=NULL WHERE run_id=? AND id=?",
                      (state, dumps(saved), run, task))
            self._event(c, run, "task.finished", {"task": task, "state": state, "result": saved})
            self._invalidate_release(c, run)
            if result["outcome"] == "refuted":
                self._issue(c, r, "Unconfirmed counterexample from task " + task + ": " + result["summary"])
            return {"task_id": task, "state": state, "proof_authority": "none"}

    def _save_object(self, content: bytes) -> tuple[str, str]:
        object_id = "object-" + uuid.uuid4().hex
        rel = f".mathprove/objects/{object_id}.blob"
        atomic_write(safe_path(self.root, rel), content)
        return object_id, rel

    def _evidence(self, c: sqlite3.Connection, r: sqlite3.Row, kind: str,
                  content: bytes, metadata: dict, producer: str,
                  origin: str | None = None, origin_sha256: str | None = None) -> str:
        h, rel = self._save_object(content)
        eid = "E-" + uuid.uuid4().hex[:16]
        c.execute("INSERT INTO evidence(id,run_id,spec_hash,kind,sha256,object_path,origin,origin_sha256,metadata,producer,created) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                  (eid, r["id"], r["spec_hash"], kind, h, rel, origin, origin_sha256,
                   dumps(metadata), producer, utc()))
        self._event(c, r["id"], "evidence.recorded", {"id": eid, "kind": kind, "sha256": h, "producer": producer})
        self._invalidate_release(c, r["id"])
        return eid

    def add_evidence(self, run: str, kind: str, source: str | Path, producer: str = "coordinator") -> dict:
        if kind not in KINDS:
            raise ProtocolError("Unsupported public evidence kind; verification receipts are runner-only")
        p = safe_path(self.root, source, exists=True)
        if not p.is_file() or p.stat().st_size > 16 * 1024 * 1024:
            raise ProtocolError("Evidence must be a file of at most 16 MiB")
        content = p.read_bytes()
        if not content.strip():
            raise ProtocolError("Evidence content is empty")
        with self.tx() as c:
            r = self._run(c, run)
            self._require_active(r)
            eid = self._evidence(c, r, kind, content, {}, text(producer, "producer", 128),
                                 p.relative_to(self.root).as_posix(), None)
            if kind == "counterexample_candidate":
                self._issue(c, r, "Counterexample candidate requires an explicit resolution: " + eid)
            return {"evidence_id": eid, "proof_authority": "none"}

    def withdraw(self, run: str, evidence_id: str, reason: str) -> dict:
        """Retire stale evidence without deleting objects/history; re-run gates afterward."""
        text(reason, "withdrawal reason")
        with self.tx() as c:
            r = self._run(c, run)
            row = c.execute("SELECT id FROM evidence WHERE id=? AND run_id=? AND spec_hash=? AND withdrawn=0", (evidence_id, run, r["spec_hash"])).fetchone()
            if not row:
                raise ProtocolError("Unknown or already-withdrawn evidence")
            c.execute("UPDATE evidence SET withdrawn=1 WHERE id=?", (evidence_id,))
            self._invalidate_release(c, run)
            self._event(c, run, "evidence.withdrawn", {"id": evidence_id, "reason": reason})
        return {"evidence_id": evidence_id, "withdrawn": True}

    def _issue(self, c: sqlite3.Connection, r: sqlite3.Row, summary: str) -> str:
        iid = "I-" + uuid.uuid4().hex[:16]
        c.execute("INSERT INTO issues(id,run_id,spec_hash,summary,created) VALUES(?,?,?,?,?)",
                  (iid, r["id"], r["spec_hash"], summary, utc()))
        self._invalidate_release(c, r["id"])
        self._event(c, r["id"], "issue.opened", {"id": iid, "summary": summary})
        return iid

    def issue(self, run: str, summary: str) -> dict:
        with self.tx() as c:
            r = self._run(c, run)
            return {"issue_id": self._issue(c, r, text(summary, "issue"))}

    def resolve(self, run: str, issue: str, evidence_id: str) -> dict:
        with self.tx() as c:
            r = self._run(c, run)
            row = c.execute("SELECT * FROM issues WHERE id=? AND run_id=? AND spec_hash=?", (issue, run, r["spec_hash"])).fetchone()
            ev = c.execute("SELECT * FROM evidence WHERE id=? AND run_id=? AND spec_hash=? AND withdrawn=0", (evidence_id, run, r["spec_hash"])).fetchone()
            if not row or not ev or self._stale(ev):
                raise ProtocolError("Resolution needs a current issue and non-stale evidence from this run")
            c.execute("UPDATE issues SET resolved=1,resolution_evidence=? WHERE id=?", (evidence_id, issue))
            self._invalidate_release(c, run)
            self._event(c, run, "issue.resolved", {"id": issue, "evidence": evidence_id})
            return {"issue_id": issue, "resolved": True, "semantic_check": "human_or_reviewer_required"}

    def _stale(self, ev: sqlite3.Row) -> str | None:
        try:
            safe_path(self.root, ev["object_path"], exists=True)
            return None
        except (OSError, ProtocolError):
            return "registered evidence file is missing"

    def _snapshot(self, c: sqlite3.Connection, r: sqlite3.Row) -> str:
        sequence = c.execute("SELECT COALESCE(MAX(seq),0) FROM events WHERE run_id=?", (r["id"],)).fetchone()[0]
        return f"{r['id']}:{r['revision']}:{sequence}"

    def status(self, run: str) -> dict:
        with self.connect() as c:
            r = self._run(c, run)
            tasks = c.execute("SELECT id,role,state,owner,expires,attempts,work_dir FROM tasks WHERE run_id=? AND spec_hash=? ORDER BY rowid", (run, r["spec_hash"])).fetchall()
            ev = c.execute("SELECT id,kind,sha256,object_path,origin,origin_sha256 FROM evidence WHERE run_id=? AND spec_hash=? AND withdrawn=0 ORDER BY created", (run, r["spec_hash"])).fetchall()
            return {"run_id": run, "revision": r["revision"], "spec_hash": r["spec_hash"], "spec_revision": r["spec_hash"],
                    "mode": json.loads(r["spec"])["mode"], "status": r["status"],
                    "status_is_historical": True, "freshness_action": "gate release --check; never use status as a fresh certificate",
                    "last_accepted_stage": STAGES[r["phase"]] if r["phase"] >= 0 else None,
                    "next_stage": STAGES[r["phase"] + 1] if r["phase"] < len(STAGES)-1 else None,
                    "snapshot": self._snapshot(c, r), "tasks": [dict(x) for x in tasks],
                    "evidence": [{**dict(x), "stale": self._stale(x)} for x in ev],
                    "open_issues": [dict(x) for x in c.execute("SELECT id,summary FROM issues WHERE run_id=? AND spec_hash=? AND resolved=0", (run, r["spec_hash"]))],
                    "pause_reason": r["pause_reason"], "max_parallel": r["max_parallel"],
                    "budget_attempts": r["budget_attempts"],
                    "attempts_used": c.execute("SELECT COALESCE(SUM(attempts),0) FROM tasks WHERE run_id=?", (run,)).fetchone()[0],
                    "proof_authority": "Lean kernel only; release label is local/cooperative, not an independent certificate"}

    def list_runs(self) -> list[dict]:
        with self.connect() as c:
            return [dict(r) for r in c.execute("SELECT id,status,revision,spec_hash,phase FROM runs ORDER BY created")]

    def spec(self, run: str) -> dict:
        with self.connect() as c:
            return json.loads(self._run(c, run)["spec"])

    def _json_evidence(self, ev: sqlite3.Row) -> dict:
        try:
            value = strict_json(safe_path(self.root, ev["object_path"], exists=True))
            return value if isinstance(value, dict) else {}
        except (ValueError, OSError):
            return {}

    def gate(self, run: str, stage: str, *, record: bool = True) -> dict:
        if stage not in STAGES:
            raise ProtocolError("Unknown stage")
        with self.tx() as c:
            r = self._run(c, run)
            idx = STAGES.index(stage)
            reasons: list[str] = []
            if idx > r["phase"] + 1:
                reasons.append("Previous stage has not been accepted")
            rows = c.execute("SELECT * FROM evidence WHERE run_id=? AND spec_hash=? AND withdrawn=0 ORDER BY created", (run, r["spec_hash"])).fetchall()
            valid: dict[str, list[sqlite3.Row]] = {}
            for ev in rows:
                stale = self._stale(ev)
                if stale:
                    reasons.append(f"{ev['id']}: {stale}")
                else:
                    valid.setdefault(ev["kind"], []).append(ev)
            if idx >= 2:
                for t in c.execute("SELECT * FROM tasks WHERE run_id=? AND spec_hash=? AND state='done'", (run, r["spec_hash"])):
                    reasons.extend(self._task_artifact_errors(t))
                issues = c.execute("SELECT id,resolved,resolution_evidence FROM issues WHERE run_id=? AND spec_hash=?", (run, r["spec_hash"])).fetchall()
                for issue in issues:
                    if not issue["resolved"]:
                        reasons.append("Unresolved adverse issue: " + issue["id"])
                    elif issue["resolution_evidence"] not in {e["id"] for es in valid.values() for e in es}:
                        reasons.append("Stale issue resolution: " + issue["id"])
            def latest(kind: str) -> dict:
                return self._json_evidence(valid[kind][-1]) if kind in valid else {}
            # Recheck earlier requirements on later gates, not just historical green flags.
            review = latest("spec_review")
            if not (review.get("spec_hash") == r["spec_hash"] and review.get("statement_match") is True and review.get("assumptions_checked") is True
                    and review.get("issues") == [] and isinstance(review.get("reviewer"), str) and review["reviewer"].strip()):
                reasons.append("Need spec_review JSON: current spec_hash, statement_match=true, assumptions_checked=true, reviewer, issues=[]")
            if idx >= 1:
                plan = latest("plan")
                reasons.extend(validate_plan(plan, r["spec_hash"]))
            if idx >= 2 and "candidate" not in valid:
                reasons.append("Need a candidate derivation/proof artifact; task completion is not proof")
            if idx >= 3:
                ref = latest("refutation")
                if not (ref.get("spec_hash") == r["spec_hash"] and isinstance(ref.get("tests"), list) and ref["tests"] and ref.get("unresolved_counterexamples") == []
                        and isinstance(ref.get("limitations"), list) and isinstance(ref.get("reviewer"), str) and ref["reviewer"].strip()):
                    reasons.append("Need refutation JSON: current spec_hash, nonempty tests, limitations, reviewer and unresolved_counterexamples=[]")
                else:
                    for test in ref["tests"]:
                        if not isinstance(test, dict) or not all(isinstance(test.get(k), str) and test[k].strip() for k in ("hypothesis", "method", "result", "evidence")):
                            reasons.append("Every refutation test needs hypothesis/method/result/evidence strings")
                            break
            if idx >= 4:
                unfinished = c.execute("SELECT id,state FROM tasks WHERE run_id=? AND spec_hash=? AND state NOT IN ('done','cancelled')", (run, r["spec_hash"])).fetchall()
                if unfinished:
                    reasons.append("Unfinished tasks: " + ", ".join(f"{x['id']}={x['state']}" for x in unfinished))
                if json.loads(r["spec"])["mode"] == "formal":
                    from .runner import verify_current_receipt
                    receipts = valid.get("lean_replay", [])
                    if not receipts:
                        reasons.append("No runner-generated fresh-workspace Lean replay")
                    else:
                        receipt = receipts[-1]
                        if receipt["producer"] != "mathprove.runner.v9":
                            reasons.append("Verification receipt is not controller-generated")
                        reasons.extend(verify_current_receipt(self.root, json.loads(r["spec"]), self._json_evidence(receipt)))
                elif "integration" not in valid:
                    reasons.append("Research mode needs an integration note with remaining unformalized obligations")
            snapshot = self._snapshot(c, r)
            if r["status"] == "paused":
                reasons.append("Run is paused")
            accepted = not reasons
            if record:
                c.execute("INSERT INTO gates(run_id,stage,spec_hash,snapshot,accepted,reasons,created) VALUES(?,?,?,?,?,?,?)",
                          (run, stage, r["spec_hash"], snapshot, int(accepted), dumps(reasons), utc()))
                if accepted:
                    c.execute("UPDATE runs SET phase=MAX(phase,?) WHERE id=?", (idx, run))
                    if idx == 5:
                        status = "reviewed_formal_local" if json.loads(r["spec"])["mode"] == "formal" else "reviewed_research"
                        c.execute("UPDATE runs SET status=? WHERE id=?", (status, run))
                else:
                    c.execute("UPDATE runs SET phase=MIN(phase,?),status=CASE WHEN status LIKE 'reviewed_%' THEN 'active' ELSE status END WHERE id=?", (idx-1, run))
                self._event(c, run, "gate.decided", {"stage": stage, "accepted": accepted, "snapshot": snapshot, "reasons": reasons})
            return {"stage": stage, "accepted": accepted, "snapshot": snapshot, "reasons": reasons,
                    "meaning": "Protocol/evidence gate; not a semantic proof verifier or identity authentication"}

    def review(self, run: str, reviewer: str, note: str, snapshot: str, *, acknowledge: bool = False) -> dict:
        text(reviewer, "reviewer", 128)
        text(note, "review note")
        check = self.gate(run, "verify", record=False)
        if not check["accepted"]:
            raise ProtocolError("Verification gate not ready: " + "; ".join(check["reasons"]))
        with self.tx() as c:
            r = self._run(c, run)
            current = self._snapshot(c, r)
            if snapshot != current or snapshot != check["snapshot"]:
                raise ProtocolError("Review snapshot is stale")
            c.execute("INSERT INTO reviews(run_id,snapshot,reviewer,note,created) VALUES(?,?,?,?,?)", (run, snapshot, reviewer, note, utc()))
            self._event(c, run, "human.review_recorded", {"snapshot": snapshot, "reviewer": reviewer, "note": note,
                                                         "identity_authentication": "not_provided"})
            return {"reviewed_snapshot": snapshot, "identity_authentication": "not_provided"}

    def pause(self, run: str, reason: str) -> dict:
        text(reason, "pause reason")
        with self.tx() as c:
            self._run(c, run)
            c.execute("UPDATE runs SET status='paused',pause_reason=? WHERE id=?", (reason, run))
            self._event(c, run, "run.paused", {"reason": reason})
        return self.checkpoint(run, "pause")

    def resume(self, run: str, *, budget_attempts: int | None = None) -> dict:
        if budget_attempts is not None and not 1 <= budget_attempts <= 10000:
            raise ProtocolError("budget_attempts must be 1..10000")
        with self.tx() as c:
            r = self._run(c, run)
            c.execute("UPDATE runs SET status='active',phase=MIN(phase,4),pause_reason=NULL WHERE id=?", (run,))
            if budget_attempts is not None:
                c.execute("UPDATE runs SET budget_attempts=? WHERE id=?", (budget_attempts, run))
            self._expire(c, r, time.time())
            self._event(c, run, "run.resumed", {"budget_attempts": budget_attempts})
        return self.status(run)

    def cancel_task(self, run: str, task: str, reason: str) -> dict:
        text(reason, "cancellation reason")
        with self.tx() as c:
            r = self._run(c, run)
            row = c.execute("SELECT * FROM tasks WHERE run_id=? AND id=? AND spec_hash=?", (run, identifier(task), r["spec_hash"])).fetchone()
            if not row or row["state"] == "done":
                raise ProtocolError("Unknown task or completed task; do not cancel accepted work")
            c.execute("UPDATE tasks SET state='cancelled',token=NULL,expires=NULL WHERE run_id=? AND id=?", (run, task))
            self._invalidate_release(c, run)
            self._event(c, run, "task.cancelled", {"task": task, "reason": reason})
        return {"task_id": task, "state": "cancelled"}

    def bind(self, session: str, run: str) -> dict:
        text(session, "session_id", 256)
        with self.tx() as c:
            self._run(c, run)
            c.execute("INSERT INTO sessions VALUES(?,?) ON CONFLICT(session_id) DO UPDATE SET run_id=excluded.run_id", (session, run))
        return {"session_id": session, "run_id": run}

    def session_run(self, session: str) -> str | None:
        with self.connect() as c:
            row = c.execute("SELECT run_id FROM sessions WHERE session_id=?", (session,)).fetchone()
            if row:
                return row[0]
            rows = c.execute("SELECT id FROM runs WHERE status='active'").fetchall()
            return rows[0][0] if len(rows) == 1 else None

    def checkpoint(self, run: str, reason: str = "manual") -> dict:
        # Snapshot is immutable; the hook does not parse or replay a full transcript.
        with self.tx() as c:
            r = self._run(c, run)
            tasks = [dict(x) for x in c.execute("SELECT id,role,state,work_dir FROM tasks WHERE run_id=? AND spec_hash=? ORDER BY rowid LIMIT 128", (run, r["spec_hash"]))]
            task_count = c.execute("SELECT COUNT(*) FROM tasks WHERE run_id=? AND spec_hash=?", (run, r["spec_hash"])).fetchone()[0]
            open_issues = [dict(x) for x in c.execute("SELECT id,summary FROM issues WHERE run_id=? AND spec_hash=? AND resolved=0 LIMIT 32", (run, r["spec_hash"]))]
            issue_count = c.execute("SELECT COUNT(*) FROM issues WHERE run_id=? AND spec_hash=? AND resolved=0", (run, r["spec_hash"])).fetchone()[0]
            capsule = {"version": VERSION, "run_id": run, "spec_hash": r["spec_hash"],
                       "revision": r["revision"], "status": r["status"], "phase": r["phase"],
                       "snapshot": self._snapshot(c, r), "tasks": tasks, "open_issues": open_issues,
                       "counts": {"tasks": task_count, "open_issues": issue_count},
                       "truncated": task_count > len(tasks) or issue_count > len(open_issues),
                       "created": utc(), "reason": reason,
                       "instruction": "Read the current goal, mathematical evidence and unresolved tasks. This is a cache, not proof authority."}
            rel = f".mathprove/checkpoints/{run}-{uuid.uuid4().hex}.json"
            atomic_write(safe_path(self.root, rel), dumps(capsule) + "\n")
            self._event(c, run, "checkpoint.created", {"path": rel, "snapshot": capsule["snapshot"], "reason": reason})
            return {"path": rel, "snapshot": capsule["snapshot"], "run_id": run}

    def brief(self, run: str) -> str:
        """Hook-safe bounded metadata: do not inject imported papers or task text."""
        with self.connect() as c:
            r = self._run(c, run)
            counts = {x[0]: x[1] for x in c.execute("SELECT state,COUNT(*) FROM tasks WHERE run_id=? AND spec_hash=? GROUP BY state", (run, r["spec_hash"]))}
            nxt = STAGES[min(r["phase"] + 1, len(STAGES)-1)]
            return (f"MathProve run={run}; revision={r['revision']}; spec_revision={r['spec_hash']}; "
                    f"status={r['status']}; next_gate={nxt}; tasks={dumps(counts)}. "
                    "Read current state through the controller. Agent prose, scores and tool success are not proof. "
                    "Checkpoint and pause are valid outcomes. Review notes record mathematical judgments, not an extra approval ceremony.")

    def hook_event(self, run: str | None, event: str, data: dict, dedupe: str | None) -> bool:
        with self.tx() as c:
            if run:
                self._run(c, run)
            return self._event(c, run, "hook." + event, data, dedupe)

    def memory(self, run: str, query: str = "", limit: int = 20) -> list[dict]:
        if not 1 <= limit <= 100:
            raise ProtocolError("limit must be 1..100")
        with self.connect() as c:
            self._run(c, run)
            # Literal substring; not SQL interpolation and not wildcard interpretation.
            rows = c.execute("SELECT seq,event,payload,created FROM events WHERE run_id=? AND instr(lower(payload),lower(?))>0 ORDER BY seq DESC LIMIT ?", (run, query, limit)).fetchall()
            return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows]

    def audit_events(self) -> dict:
        with self.connect() as c:
            rows = c.execute("SELECT seq,payload FROM events ORDER BY seq").fetchall()
        invalid = [row["seq"] for row in rows if not _is_json(row["payload"])]
        return {"consistent": not invalid, "events": len(rows), "invalid_json_events": invalid,
                "hash_verification": False, "tamper_proof": False}


def validate_plan(plan: dict, spec_hash: str) -> list[str]:
    errors: list[str] = []
    if plan.get("spec_hash") != spec_hash:
        errors.append("Plan must bind the current spec_hash")
    nodes = plan.get("nodes")
    if not isinstance(nodes, list) or not nodes or len(nodes) > 2048:
        return errors + ["Plan needs a nonempty lemma DAG of at most 2048 nodes"]
    graph: dict[str, list[str]] = {}
    for node in nodes:
        if not isinstance(node, dict):
            return errors + ["Invalid DAG node"]
        try:
            key = identifier(node.get("id"))
            text(node.get("statement"), "node.statement")
        except ProtocolError as e:
            return errors + [str(e)]
        deps = node.get("depends_on", [])
        if key in graph or not isinstance(deps, list) or not all(isinstance(d, str) for d in deps):
            return errors + ["Duplicate node or invalid dependency list"]
        graph[key] = deps
    target = plan.get("target")
    if not isinstance(target, str) or target not in graph:
        errors.append("Plan target must name a DAG node")
    visiting: set[str] = set()
    seen: set[str] = set()
    def visit(key: str) -> None:
        if key not in graph:
            raise ProtocolError("DAG references an unknown lemma")
        if key in visiting:
            raise ProtocolError("Cyclic lemma dependency")
        if key in seen:
            return
        visiting.add(key)
        for dep in graph[key]:
            visit(dep)
        visiting.remove(key)
        seen.add(key)
    try:
        for key in graph:
            visit(key)
    except (ProtocolError, RecursionError) as e:
        errors.append(str(e) or "DAG too deep")
    lit = plan.get("literature")
    if not isinstance(lit, dict):
        errors.append("Plan needs literature sources or a not_needed_reason for elementary tasks")
    elif not (isinstance(lit.get("not_needed_reason"), str) and lit["not_needed_reason"].strip()):
        sources = lit.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append("Literature coverage is empty")
        else:
            for source in sources:
                if not isinstance(source, dict) or source.get("checked") is not True or not all(
                    isinstance(source.get(k), str) and source[k].strip() for k in ("title", "url", "location", "accessed", "relation")):
                    errors.append("Each source needs title/url/location/accessed/relation and checked=true (reviewer attestation, not automatic browsing)")
                    break
    return errors
