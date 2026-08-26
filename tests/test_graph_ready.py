"""GE-5 — ReadySet computation: deps ∧ resources ∧ capability ∧ gates.

A node is READY only when ALL conditions hold (ADR GE-0001 "Resource-aware
scheduling rule"):
1. Dependencies satisfied (all predecessors done or skipped)
2. No resource conflict with a currently-running node (GE-4 conflicts)
3. Node itself is in TODO status
4. Status != BLOCKED (readiness gate)

Readiness != execution: the scheduler picks from ReadySet by capacity/policy.
"""

from __future__ import annotations

import pytest

from a_conductor.graph.domain import DependencyType, TaskEdge, TaskNode, TaskNodeStatus
from a_conductor.graph.graph import build_graph
from a_conductor.graph.ready import (
    Blocker,
    BlockerKind,
    ReadyCheck,
    compute_ready_set,
)


def _node(
    node_id: str,
    status: TaskNodeStatus = TaskNodeStatus.TODO,
    write_set: tuple[str, ...] = (),
    worker_req: tuple[str, ...] = (),
) -> TaskNode:
    return TaskNode(
        id=node_id,
        objective=f"obj {node_id}",
        status=status,
        write_set=write_set,
        worker_requirement=worker_req,
    )


# --- basic dependency readiness ------------------------------------------------


def test_root_node_with_no_deps_is_ready() -> None:
    graph = build_graph([_node("a")], [])
    result = compute_ready_set(graph, {})
    assert "a" in result.ready_ids
    assert result.checks["a"].is_ready


def test_node_with_unfinished_dep_not_ready() -> None:
    graph = build_graph(
        [_node("a"), _node("b")],
        [TaskEdge("a", "b")],
    )
    result = compute_ready_set(graph, {})  # a is TODO (not done)
    assert "a" in result.ready_ids
    assert "b" not in result.ready_ids
    blockers = result.checks["b"].blockers
    assert any(b.kind == BlockerKind.DEPENDENCY and "a" in b.detail for b in blockers)


def test_node_with_done_dep_becomes_ready() -> None:
    graph = build_graph(
        [_node("a"), _node("b")],
        [TaskEdge("a", "b")],
    )
    states = {"a": TaskNodeStatus.DONE}
    result = compute_ready_set(graph, states)
    assert "b" in result.ready_ids


def test_node_with_skipped_dep_becomes_ready() -> None:
    graph = build_graph(
        [_node("a"), _node("b")],
        [TaskEdge("a", "b")],
    )
    states = {"a": TaskNodeStatus.SKIPPED}
    result = compute_ready_set(graph, states)
    assert "b" in result.ready_ids


def test_chain_ready_in_order() -> None:
    graph = build_graph(
        [_node("a"), _node("b"), _node("c")],
        [TaskEdge("a", "b"), TaskEdge("b", "c")],
    )
    r0 = compute_ready_set(graph, {})
    assert r0.ready_ids == {"a"}

    r1 = compute_ready_set(graph, {"a": TaskNodeStatus.DONE})
    assert r1.ready_ids == {"b"}

    r2 = compute_ready_set(graph, {"a": TaskNodeStatus.DONE, "b": TaskNodeStatus.DONE})
    assert r2.ready_ids == {"c"}


def test_multiple_deps_all_must_be_done() -> None:
    graph = build_graph(
        [_node("x"), _node("y"), _node("z")],
        [TaskEdge("x", "z"), TaskEdge("y", "z")],
    )
    # x done but y not → z not ready
    result = compute_ready_set(graph, {"x": TaskNodeStatus.DONE})
    assert "z" not in result.ready_ids
    assert len(result.checks["z"].blockers) == 1  # only y blocking

    # both done → z ready
    result2 = compute_ready_set(graph, {"x": TaskNodeStatus.DONE, "y": TaskNodeStatus.DONE})
    assert "z" in result2.ready_ids


# --- status-based blocks --------------------------------------------------------


def test_done_node_not_ready() -> None:
    graph = build_graph([_node("a", status=TaskNodeStatus.DONE)], [])
    result = compute_ready_set(graph, {"a": TaskNodeStatus.DONE})
    assert "a" not in result.ready_ids


def test_doing_node_not_ready() -> None:
    graph = build_graph([_node("a", status=TaskNodeStatus.DOING)], [])
    result = compute_ready_set(graph, {"a": TaskNodeStatus.DOING})
    assert "a" not in result.ready_ids


def test_blocked_node_not_ready() -> None:
    graph = build_graph([_node("a", status=TaskNodeStatus.BLOCKED)], [])
    result = compute_ready_set(graph, {"a": TaskNodeStatus.BLOCKED})
    assert "a" not in result.ready_ids


def test_blocked_status_has_blocker() -> None:
    graph = build_graph([_node("a", status=TaskNodeStatus.BLOCKED)], [])
    result = compute_ready_set(graph, {"a": TaskNodeStatus.BLOCKED})
    assert any(b.kind == BlockerKind.GATE for b in result.checks["a"].blockers)


# --- resource conflicts (running node blocks conflicting TODO node) --------------


def test_running_node_blocks_write_conflict() -> None:
    graph = build_graph(
        [
            _node("a", write_set=("f.py",), status=TaskNodeStatus.DOING),
            _node("b", write_set=("f.py",)),
        ],
        [],
    )
    result = compute_ready_set(graph, {"a": TaskNodeStatus.DOING})
    assert "b" not in result.ready_ids
    blockers = result.checks["b"].blockers
    assert any(b.kind == BlockerKind.RESOURCE and "a" in b.detail for b in blockers)


def test_running_node_no_write_overlap_no_block() -> None:
    graph = build_graph(
        [
            _node("a", write_set=("f1.py",), status=TaskNodeStatus.DOING),
            _node("b", write_set=("f2.py",)),
        ],
        [],
    )
    result = compute_ready_set(graph, {"a": TaskNodeStatus.DOING})
    assert "b" in result.ready_ids


# --- ReadySetResult structure ----------------------------------------------------


def test_result_has_checks_for_all_nodes() -> None:
    graph = build_graph([_node("a"), _node("b"), _node("c")], [])
    result = compute_ready_set(graph, {})
    assert set(result.checks.keys()) == {"a", "b", "c"}
    assert all(isinstance(c, ReadyCheck) for c in result.checks.values())


def test_result_ready_ids_is_sorted_set() -> None:
    graph = build_graph([_node("c"), _node("a"), _node("b")], [])
    result = compute_ready_set(graph, {})
    assert result.ready_ids == {"a", "b", "c"}


def test_empty_graph_empty_result() -> None:
    result = compute_ready_set(build_graph([], []), {})
    assert result.ready_ids == set()
    assert result.checks == {}


# --- blocker details ---------------------------------------------------------------


def test_dependency_blocker_names_the_predecessor() -> None:
    graph = build_graph(
        [_node("pre"), _node("post")],
        [TaskEdge("pre", "post")],
    )
    result = compute_ready_set(graph, {})
    dep_blockers = [b for b in result.checks["post"].blockers if b.kind == BlockerKind.DEPENDENCY]
    assert len(dep_blockers) == 1
    assert "pre" in dep_blockers[0].detail


def test_multiple_blockers_reported() -> None:
    """A node blocked by both a dependency AND a resource conflict."""
    graph = build_graph(
        [
            _node("dep1"),
            _node("dep2"),
            _node("running", write_set=("f.py",), status=TaskNodeStatus.DOING),
            _node("target", write_set=("f.py",)),
        ],
        [TaskEdge("dep1", "target"), TaskEdge("dep2", "target")],
    )
    states = {"running": TaskNodeStatus.DOING}
    result = compute_ready_set(graph, states)
    check = result.checks["target"]
    assert not check.is_ready
    kinds = {b.kind for b in check.blockers}
    assert BlockerKind.DEPENDENCY in kinds
    assert BlockerKind.RESOURCE in kinds
