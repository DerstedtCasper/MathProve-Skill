"""ParallelCandidateRunner: race N proof candidates and pick the first winner."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed, Future
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class BranchStatus(str, Enum):
    """Status of a single candidate branch."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CandidateBranch:
    """A single proof candidate to be executed in isolation."""

    branch_id: str
    code: str
    engine: str  # "lean" or "sympy"
    workspace_path: str = ""
    status: BranchStatus = BranchStatus.PENDING
    stdout: str = ""
    stderr: str = ""
    elapsed_sec: float = 0.0


@dataclass
class SearchTreeLog:
    """Log entry recording a parallel search step."""

    step_id: str
    branches: list[CandidateBranch] = field(default_factory=list)
    winner_id: str | None = None
    started_at: str = ""
    finished_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return {
            "step_id": self.step_id,
            "branches": [
                {
                    "branch_id": b.branch_id,
                    "code": b.code,
                    "engine": b.engine,
                    "workspace_path": b.workspace_path,
                    "status": b.status.value if isinstance(b.status, BranchStatus) else b.status,
                    "stdout": b.stdout,
                    "stderr": b.stderr,
                    "elapsed_sec": b.elapsed_sec,
                }
                for b in self.branches
            ],
            "winner_id": self.winner_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

    def save(self, path: str) -> None:
        """Write the log to a JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, ensure_ascii=False)


def _now_iso() -> str:
    """Return current time as an ISO-8601 string."""
    return datetime.now().isoformat()


def _run_single_candidate(branch: CandidateBranch, timeout: int) -> CandidateBranch:
    """Execute a single candidate in an isolated temp directory.

    This is a module-level function so it can be pickled by ProcessPoolExecutor.
    """
    tmp_dir = tempfile.mkdtemp(prefix="mathprove_branch_")
    branch.workspace_path = tmp_dir
    branch.status = BranchStatus.RUNNING

    t0 = time.monotonic()
    try:
        # Choose file extension and command based on engine
        if branch.engine == "lean":
            filename = "Main.lean"
            cmd = ["lean", os.path.join(tmp_dir, filename)]
        else:
            # Default to sympy / python
            filename = "main.py"
            cmd = [sys.executable, os.path.join(tmp_dir, filename)]

        # Write code to file
        filepath = os.path.join(tmp_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(branch.code)

        # Execute
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tmp_dir,
        )
        branch.elapsed_sec = round(time.monotonic() - t0, 3)
        branch.stdout = result.stdout
        branch.stderr = result.stderr

        if result.returncode == 0:
            branch.status = BranchStatus.SUCCESS
        else:
            branch.status = BranchStatus.FAILED

    except subprocess.TimeoutExpired as exc:
        branch.elapsed_sec = round(time.monotonic() - t0, 3)
        branch.stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        branch.stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        branch.status = BranchStatus.FAILED

    except FileNotFoundError:
        branch.elapsed_sec = round(time.monotonic() - t0, 3)
        branch.status = BranchStatus.FAILED
        branch.stderr = f"Command not found: {cmd[0]}"

    except Exception as exc:  # noqa: BLE001
        branch.elapsed_sec = round(time.monotonic() - t0, 3)
        branch.status = BranchStatus.FAILED
        branch.stderr = str(exc)

    finally:
        # Clean up temp directory
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:  # noqa: BLE001
            pass

    return branch


class ParallelRunner:
    """Run N candidate branches in parallel, pick the first winner."""

    def __init__(self, max_workers: int = 4, timeout: int = 60) -> None:
        self.max_workers = max_workers
        self.timeout = timeout

    def run_candidates(
        self, step_id: str, candidates: list[CandidateBranch]
    ) -> SearchTreeLog:
        """Submit all candidates and return a SearchTreeLog with the first winner.

        Note: ProcessPoolExecutor pickles arguments and return values, so the
        returned CandidateBranch from each future is a *new* object.  We build
        a results dict keyed by branch_id and replace the log branches at the
        end to keep everything consistent.
        """
        log = SearchTreeLog(
            step_id=step_id,
            started_at=_now_iso(),
        )

        # Map future -> branch_id for lookup
        future_to_id: dict[Future, str] = {}
        # Keep original branch objects indexed by id for fallback
        id_to_original: dict[str, CandidateBranch] = {b.branch_id: b for b in candidates}
        # Collect results indexed by branch_id
        results: dict[str, CandidateBranch] = {}

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            for candidate in candidates:
                fut = executor.submit(_run_single_candidate, candidate, self.timeout)
                future_to_id[fut] = candidate.branch_id

            winner_found = False
            completed_ids: set[str] = set()

            for fut in as_completed(future_to_id):
                bid = future_to_id[fut]
                try:
                    result_branch = fut.result()
                except Exception as exc:  # noqa: BLE001
                    # If the future itself raised, mark branch as failed
                    result_branch = id_to_original[bid]
                    result_branch.status = BranchStatus.FAILED
                    result_branch.stderr = str(exc)

                results[bid] = result_branch
                completed_ids.add(bid)

                if result_branch.status == BranchStatus.SUCCESS and not winner_found:
                    winner_found = True
                    log.winner_id = bid
                    # Cancel remaining futures
                    for other_fut, other_id in future_to_id.items():
                        if other_id not in completed_ids:
                            other_fut.cancel()

        # Build final branches list: use result if available, else original
        final_branches: list[CandidateBranch] = []
        for c in candidates:
            branch = results.get(c.branch_id, c)
            # Mark any branch still PENDING or RUNNING as CANCELLED
            if branch.status in (BranchStatus.PENDING, BranchStatus.RUNNING):
                branch.status = BranchStatus.CANCELLED
            final_branches.append(branch)

        log.branches = final_branches
        log.finished_at = _now_iso()
        return log

    def get_winner(self, log: SearchTreeLog) -> CandidateBranch | None:
        """Return the winning branch from a SearchTreeLog, or None."""
        if log.winner_id is None:
            return None
        for b in log.branches:
            if b.branch_id == log.winner_id:
                return b
        return None
