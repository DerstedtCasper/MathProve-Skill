"""Tests for skill.runtime.proof_tree module."""
from __future__ import annotations

import pytest

from skill.runtime.proof_tree import (
    NodeStatus,
    Phase,
    ProofNode,
    ProofSearchTree,
    VALID_TRANSITIONS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tree_with_chain() -> ProofSearchTree:
    """Return a tree with root -> child1 -> child2."""
    tree = ProofSearchTree(run_id="test-chain")
    tree.add_node("root")
    tree.add_node("child1", parent_id="root")
    tree.add_node("child2", parent_id="child1")
    return tree


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_tree_and_add_nodes():
    """Create a tree, add 3 nodes, verify get_node and _order."""
    tree = ProofSearchTree(run_id="run-001")
    tree.add_node("s1")
    tree.add_node("s2")
    tree.add_node("s3")

    assert tree.get_node("s1") is not None
    assert tree.get_node("s2") is not None
    assert tree.get_node("s3") is not None
    assert tree.get_node("nonexistent") is None
    assert tree._order == ["s1", "s2", "s3"]
    assert len(tree.nodes) == 3


def test_add_node_with_parent():
    """Verify parent.children_ids is updated when adding a child node."""
    tree = ProofSearchTree(run_id="run-002")
    tree.add_node("parent")
    tree.add_node("child", parent_id="parent")

    parent_node = tree.get_node("parent")
    assert parent_node is not None
    assert "child" in parent_node.children_ids

    child_node = tree.get_node("child")
    assert child_node is not None
    assert child_node.parent_id == "parent"


def test_add_node_duplicate_raises():
    """Adding a node with an existing step_id should raise ValueError."""
    tree = ProofSearchTree(run_id="run-dup")
    tree.add_node("s1")
    with pytest.raises(ValueError, match="already exists"):
        tree.add_node("s1")


def test_add_node_missing_parent_raises():
    """Adding a node referencing a nonexistent parent should raise ValueError."""
    tree = ProofSearchTree(run_id="run-nop")
    with pytest.raises(ValueError, match="Parent node not found"):
        tree.add_node("child", parent_id="ghost")


def test_full_advance_chain():
    """PENDING -> MAGI_APPROVED -> SYMPY_PASSED -> LEAN_PASSED -> PASSED."""
    tree = ProofSearchTree(run_id="run-003")
    tree.add_node("step1")

    tree.advance("step1", NodeStatus.MAGI_APPROVED)
    assert tree.get_node("step1").status == NodeStatus.MAGI_APPROVED

    tree.advance("step1", NodeStatus.SYMPY_PASSED)
    assert tree.get_node("step1").status == NodeStatus.SYMPY_PASSED

    tree.advance("step1", NodeStatus.LEAN_PASSED)
    assert tree.get_node("step1").status == NodeStatus.LEAN_PASSED

    tree.advance("step1", NodeStatus.PASSED)
    assert tree.get_node("step1").status == NodeStatus.PASSED


def test_invalid_advance_raises():
    """PENDING -> LEAN_PASSED should raise ValueError."""
    tree = ProofSearchTree(run_id="run-004")
    tree.add_node("step1")

    with pytest.raises(ValueError, match="Invalid transition"):
        tree.advance("step1", NodeStatus.LEAN_PASSED)


def test_passed_is_terminal():
    """Once PASSED, no further transitions are allowed."""
    tree = ProofSearchTree(run_id="run-005")
    tree.add_node("step1")

    # Advance to PASSED
    tree.advance("step1", NodeStatus.MAGI_APPROVED)
    tree.advance("step1", NodeStatus.SYMPY_PASSED)
    tree.advance("step1", NodeStatus.LEAN_PASSED)
    tree.advance("step1", NodeStatus.PASSED)

    # Any transition from PASSED should fail
    for target in NodeStatus:
        with pytest.raises(ValueError, match="Invalid transition"):
            tree.advance("step1", target)


def test_failed_is_terminal_via_advance():
    """Once FAILED, no further transitions are allowed via advance()."""
    tree = ProofSearchTree(run_id="run-fail")
    tree.add_node("step1")
    tree.advance("step1", NodeStatus.FAILED)

    for target in NodeStatus:
        with pytest.raises(ValueError, match="Invalid transition"):
            tree.advance("step1", target)


def test_backtrack():
    """Backtrack root: root=PENDING, all children=FAILED."""
    tree = _make_tree_with_chain()

    # Advance all to MAGI_APPROVED
    for sid in ["root", "child1", "child2"]:
        tree.advance(sid, NodeStatus.MAGI_APPROVED)

    tree.backtrack("root")

    assert tree.get_node("root").status == NodeStatus.PENDING
    assert tree.get_node("root").last_error == ""
    assert tree.get_node("child1").status == NodeStatus.FAILED
    assert tree.get_node("child2").status == NodeStatus.FAILED


def test_backtrack_leaf():
    """Backtracking a leaf node (no children) resets it to PENDING."""
    tree = ProofSearchTree(run_id="run-leaf")
    tree.add_node("leaf")
    tree.advance("leaf", NodeStatus.MAGI_APPROVED)

    tree.backtrack("leaf")
    assert tree.get_node("leaf").status == NodeStatus.PENDING


def test_increment_attempt():
    """Increment lean counter 5 times, verify attempts['lean'] == 5."""
    tree = ProofSearchTree(run_id="run-006")
    tree.add_node("step1")

    for _ in range(5):
        tree.increment_attempt("step1", "lean")

    node = tree.get_node("step1")
    assert node.attempts["lean"] == 5
    assert node.attempts["magi"] == 0
    assert node.attempts["sympy"] == 0


def test_increment_attempt_custom_tool():
    """Incrementing a tool not in the default dict should work."""
    tree = ProofSearchTree(run_id="run-custom")
    tree.add_node("step1")
    tree.increment_attempt("step1", "z3")
    assert tree.get_node("step1").attempts["z3"] == 1


def test_current_step():
    """current_step returns the first non-terminal node in order."""
    tree = ProofSearchTree(run_id="run-007")
    tree.add_node("s1")
    tree.add_node("s2")
    tree.add_node("s3")

    assert tree.current_step() == "s1"

    # Advance s1 to PASSED
    tree.advance("s1", NodeStatus.MAGI_APPROVED)
    tree.advance("s1", NodeStatus.SYMPY_PASSED)
    tree.advance("s1", NodeStatus.LEAN_PASSED)
    tree.advance("s1", NodeStatus.PASSED)

    assert tree.current_step() == "s2"

    # Fail s2
    tree.advance("s2", NodeStatus.FAILED)
    assert tree.current_step() == "s3"

    # Pass s3
    tree.advance("s3", NodeStatus.MAGI_APPROVED)
    tree.advance("s3", NodeStatus.SYMPY_PASSED)
    tree.advance("s3", NodeStatus.LEAN_PASSED)
    tree.advance("s3", NodeStatus.PASSED)

    assert tree.current_step() is None


def test_is_complete():
    """is_complete returns True only when all nodes are PASSED."""
    tree = ProofSearchTree(run_id="run-008")
    tree.add_node("s1")
    tree.add_node("s2")

    assert tree.is_complete() is False

    # Pass s1
    tree.advance("s1", NodeStatus.MAGI_APPROVED)
    tree.advance("s1", NodeStatus.SYMPY_PASSED)
    tree.advance("s1", NodeStatus.LEAN_PASSED)
    tree.advance("s1", NodeStatus.PASSED)
    assert tree.is_complete() is False

    # Pass s2
    tree.advance("s2", NodeStatus.MAGI_APPROVED)
    tree.advance("s2", NodeStatus.SYMPY_PASSED)
    tree.advance("s2", NodeStatus.LEAN_PASSED)
    tree.advance("s2", NodeStatus.PASSED)
    assert tree.is_complete() is True


def test_is_complete_empty_tree():
    """An empty tree (no nodes) is trivially complete."""
    tree = ProofSearchTree(run_id="run-empty")
    assert tree.is_complete() is True


def test_failed_nodes():
    """failed_nodes returns all nodes with status FAILED."""
    tree = ProofSearchTree(run_id="run-009")
    tree.add_node("s1")
    tree.add_node("s2")
    tree.add_node("s3")

    tree.advance("s1", NodeStatus.FAILED)
    tree.advance("s3", NodeStatus.FAILED)

    failed = tree.failed_nodes()
    failed_ids = [n.step_id for n in failed]
    assert sorted(failed_ids) == ["s1", "s3"]


def test_serialize_roundtrip():
    """to_status_json -> from_status_json preserves all fields."""
    tree = _make_tree_with_chain()
    tree.phase = Phase.STEP_LOOP
    tree.advance("root", NodeStatus.MAGI_APPROVED)
    tree.increment_attempt("root", "magi")
    tree.get_node("root").last_error = "some error"
    tree.get_node("root").evidence_path = "/tmp/evidence.json"

    data = tree.to_status_json()
    restored = ProofSearchTree.from_status_json(data)

    assert restored.run_id == tree.run_id
    assert restored.phase == tree.phase
    assert restored._order == tree._order
    assert len(restored.nodes) == len(tree.nodes)

    for sid in tree._order:
        orig = tree.get_node(sid)
        rest = restored.get_node(sid)
        assert rest is not None
        assert rest.step_id == orig.step_id
        assert rest.status == orig.status
        assert rest.parent_id == orig.parent_id
        assert rest.children_ids == orig.children_ids
        assert rest.attempts == orig.attempts
        assert rest.last_error == orig.last_error
        assert rest.evidence_path == orig.evidence_path
        assert rest.created_at == orig.created_at
        assert rest.updated_at == orig.updated_at


def test_save_load(tmp_path):
    """save to file then load, verify equality."""
    tree = _make_tree_with_chain()
    tree.phase = Phase.AUDITING
    tree.advance("root", NodeStatus.MAGI_APPROVED)
    tree.advance("root", NodeStatus.SYMPY_PASSED)
    tree.increment_attempt("root", "sympy")

    filepath = tmp_path / "proof_state.json"
    tree.save(filepath)

    assert filepath.exists()

    loaded = ProofSearchTree.load(filepath)
    assert loaded.run_id == tree.run_id
    assert loaded.phase == tree.phase
    assert loaded._order == tree._order
    assert len(loaded.nodes) == len(tree.nodes)

    for sid in tree._order:
        orig = tree.get_node(sid)
        rest = loaded.get_node(sid)
        assert rest.step_id == orig.step_id
        assert rest.status == orig.status
        assert rest.parent_id == orig.parent_id
        assert rest.children_ids == orig.children_ids
        assert rest.attempts == orig.attempts


def test_node_timestamps():
    """Nodes should have non-empty created_at and updated_at after creation."""
    tree = ProofSearchTree(run_id="run-ts")
    node = tree.add_node("s1")
    assert node.created_at != ""
    assert node.updated_at != ""


def test_advance_updates_timestamp():
    """advance() should update the updated_at field."""
    tree = ProofSearchTree(run_id="run-ts2")
    node = tree.add_node("s1")
    old_ts = node.updated_at

    # Small trick: overwrite to detect change
    node.updated_at = "2000-01-01T00:00:00"
    tree.advance("s1", NodeStatus.MAGI_APPROVED)
    assert node.updated_at != "2000-01-01T00:00:00"


def test_phase_enum_values():
    """Verify all Phase enum values."""
    assert Phase.INIT.value == "init"
    assert Phase.PLANNING.value == "planning"
    assert Phase.STEP_LOOP.value == "step_loop"
    assert Phase.AUDITING.value == "auditing"
    assert Phase.DONE.value == "done"
    assert Phase.FAILED.value == "failed"


def test_valid_transitions_completeness():
    """Every NodeStatus must be a key in VALID_TRANSITIONS."""
    for status in NodeStatus:
        assert status in VALID_TRANSITIONS
