"""Proof Search Tree: state machine for tracking proof construction progress."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class NodeStatus(str, Enum):
    """Status of an individual proof step node."""

    PENDING = "pending"
    MAGI_REJECTED = "magi_rejected"
    MAGI_APPROVED = "magi_approved"
    SYMPY_PASSED = "sympy_passed"
    LEAN_PASSED = "lean_passed"
    PASSED = "passed"
    FAILED = "failed"


class Phase(str, Enum):
    """High-level phase of the entire proof search."""

    INIT = "init"
    PLANNING = "planning"
    STEP_LOOP = "step_loop"
    AUDITING = "auditing"
    DONE = "done"
    FAILED = "failed"


# Legal state transitions for a proof node.
VALID_TRANSITIONS: dict[NodeStatus, set[NodeStatus]] = {
    NodeStatus.PENDING: {
        NodeStatus.MAGI_APPROVED,
        NodeStatus.MAGI_REJECTED,
        NodeStatus.FAILED,
    },
    NodeStatus.MAGI_REJECTED: {
        NodeStatus.PENDING,
        NodeStatus.FAILED,
    },
    NodeStatus.MAGI_APPROVED: {
        NodeStatus.SYMPY_PASSED,
        NodeStatus.FAILED,
    },
    NodeStatus.SYMPY_PASSED: {
        NodeStatus.LEAN_PASSED,
        NodeStatus.FAILED,
    },
    NodeStatus.LEAN_PASSED: {
        NodeStatus.PASSED,
        NodeStatus.FAILED,
    },
    NodeStatus.PASSED: set(),
    NodeStatus.FAILED: set(),  # only resettable via backtrack()
}


def _now_iso() -> str:
    """Return current time as an ISO-8601 string."""
    return datetime.now().isoformat()


@dataclass
class ProofNode:
    """A single step in the proof search tree."""

    step_id: str
    status: NodeStatus = NodeStatus.PENDING
    parent_id: str | None = None
    children_ids: list[str] = field(default_factory=list)
    attempts: dict[str, int] = field(
        default_factory=lambda: {"magi": 0, "sympy": 0, "lean": 0}
    )
    last_error: str = ""
    evidence_path: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = _now_iso()
        if not self.updated_at:
            self.updated_at = _now_iso()


class ProofSearchTree:
    """State machine that tracks proof construction progress.

    Each proof step is represented as a :class:`ProofNode` arranged in a
    tree structure.  The tree enforces legal state transitions and
    provides helpers for backtracking, serialization, and status queries.
    """

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.phase = Phase.INIT
        self.nodes: dict[str, ProofNode] = {}
        self._order: list[str] = []

    # -- node management -----------------------------------------------------

    def add_node(self, step_id: str, parent_id: str | None = None) -> ProofNode:
        """Create a new proof node and register it in the tree."""
        if step_id in self.nodes:
            raise ValueError(f"Node already exists: {step_id}")
        node = ProofNode(step_id=step_id, parent_id=parent_id)
        self.nodes[step_id] = node
        self._order.append(step_id)
        if parent_id is not None:
            parent = self.nodes.get(parent_id)
            if parent is None:
                raise ValueError(f"Parent node not found: {parent_id}")
            parent.children_ids.append(step_id)
        return node

    def get_node(self, step_id: str) -> ProofNode | None:
        """Return the node with the given *step_id*, or ``None``."""
        return self.nodes.get(step_id)

    # -- state transitions ----------------------------------------------------

    def advance(self, step_id: str, new_status: NodeStatus) -> None:
        """Transition *step_id* to *new_status*, enforcing the transition matrix."""
        node = self._require_node(step_id)
        allowed = VALID_TRANSITIONS.get(node.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid transition: {node.status.value} -> {new_status.value}"
            )
        node.status = new_status
        node.updated_at = _now_iso()

    def backtrack(self, step_id: str) -> None:
        """Recursively fail all descendants, then reset *step_id* to PENDING."""
        node = self._require_node(step_id)
        # Fail all descendants first (depth-first).
        self._fail_descendants(node)
        # Reset this node.
        node.status = NodeStatus.PENDING
        node.last_error = ""
        node.updated_at = _now_iso()

    def increment_attempt(self, step_id: str, tool: str) -> None:
        """Increment the attempt counter for *tool* on the given node."""
        node = self._require_node(step_id)
        if tool not in node.attempts:
            node.attempts[tool] = 0
        node.attempts[tool] += 1

    # -- queries --------------------------------------------------------------

    def current_step(self) -> str | None:
        """Return the first step_id whose status is neither PASSED nor FAILED."""
        terminal = {NodeStatus.PASSED, NodeStatus.FAILED}
        for sid in self._order:
            if self.nodes[sid].status not in terminal:
                return sid
        return None

    def is_complete(self) -> bool:
        """Return ``True`` if every node has reached PASSED."""
        return all(n.status == NodeStatus.PASSED for n in self.nodes.values())

    def failed_nodes(self) -> list[ProofNode]:
        """Return all nodes whose status is FAILED."""
        return [n for n in self.nodes.values() if n.status == NodeStatus.FAILED]

    # -- serialization --------------------------------------------------------

    def to_status_json(self) -> dict[str, Any]:
        """Serialize the tree to a JSON-compatible dict."""
        return {
            "run_id": self.run_id,
            "phase": self.phase.value,
            "nodes": [self._node_to_dict(n) for n in self.nodes.values()],
            "order": list(self._order),
        }

    @classmethod
    def from_status_json(cls, data: dict[str, Any]) -> ProofSearchTree:
        """Deserialize a tree from a dict produced by :meth:`to_status_json`."""
        tree = cls(run_id=data["run_id"])
        tree.phase = Phase(data["phase"])
        tree._order = list(data["order"])
        for nd in data["nodes"]:
            node = ProofNode(
                step_id=nd["step_id"],
                status=NodeStatus(nd["status"]),
                parent_id=nd.get("parent_id"),
                children_ids=list(nd.get("children_ids", [])),
                attempts=dict(nd.get("attempts", {"magi": 0, "sympy": 0, "lean": 0})),
                last_error=nd.get("last_error", ""),
                evidence_path=nd.get("evidence_path", ""),
                created_at=nd.get("created_at", ""),
                updated_at=nd.get("updated_at", ""),
            )
            tree.nodes[node.step_id] = node
        return tree

    def save(self, path: str | Path) -> None:
        """Write the tree state to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_status_json(), fh, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str | Path) -> ProofSearchTree:
        """Load a tree from a JSON file written by :meth:`save`."""
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return cls.from_status_json(data)

    # -- internal helpers -----------------------------------------------------

    def _require_node(self, step_id: str) -> ProofNode:
        node = self.nodes.get(step_id)
        if node is None:
            raise KeyError(f"Node not found: {step_id}")
        return node

    def _fail_descendants(self, node: ProofNode) -> None:
        """Recursively mark all descendants as FAILED."""
        for child_id in node.children_ids:
            child = self.nodes[child_id]
            self._fail_descendants(child)
            child.status = NodeStatus.FAILED
            child.updated_at = _now_iso()

    @staticmethod
    def _node_to_dict(node: ProofNode) -> dict[str, Any]:
        return {
            "step_id": node.step_id,
            "status": node.status.value,
            "parent_id": node.parent_id,
            "children_ids": node.children_ids,
            "attempts": node.attempts,
            "last_error": node.last_error,
            "evidence_path": node.evidence_path,
            "created_at": node.created_at,
            "updated_at": node.updated_at,
        }
