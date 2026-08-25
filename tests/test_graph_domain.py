"""GE-1a — graph domain contract (ADR GE-0001..0005, decisions D1-D5).

Pure data + invariants only: no persistence, scheduling, dispatch, or
lifecycle integration (D5 limits this node to domain + tests).

Guardrails encoded here:
- D2: TaskNode carries NO dependency field — TaskEdge/TaskGraph own
  dependency relations (single source of truth).
- D2: node status is planning metadata; execution/retry state stays in
  the existing lifecycle state machine.
- D4: the 12-value DependencyType vocabulary ships exactly as accepted;
  HUMAN_APPROVAL is a readiness gate type, never a repair back-edge
  (ordering semantics arrive with GE-3).
"""

from __future__ import annotations

import dataclasses

import pytest

from a_conductor.graph.domain import (
    CAPABILITY_VOCABULARY,
    DependencyType,
    TaskEdge,
    TaskGraph,
    TaskNode,
    TaskNodeStatus,
)


def _node(node_id: str = "n1", **overrides) -> TaskNode:
    defaults = dict(
        id=node_id,
        objective="Do the thing",
        expected_outputs=("out.txt",),
        read_set=("src/**",),
        write_set=("docs/out.txt",),
        worker_requirement=("repository-read", "shell"),
        priority=5,
        timeout_seconds=600,
        retry_policy_ref="default",
    )
    defaults.update(overrides)
    return TaskNode(**defaults)


def _edge(src: str, dst: str, dep: DependencyType = DependencyType.DATA) -> TaskEdge:
    return TaskEdge(from_id=src, to_id=dst, dep_type=dep)


# --- vocabulary contracts ----------------------------------------------------


def test_dependency_type_vocabulary_is_exactly_the_accepted_twelve() -> None:
    assert [d.value for d in DependencyType] == [
        "DATA",
        "ORDERING",
        "FILE_WRITE",
        "WORKSPACE_WRITE",
        "GIT",
        "WORKER",
        "RUNTIME",
        "PROVIDER",
        "RATE_LIMIT",
        "RESOURCE",
        "VERIFICATION",
        "HUMAN_APPROVAL",
    ]


def test_capability_vocabulary_matches_awiki_task_v1() -> None:
    assert len(CAPABILITY_VOCABULARY) == 20
    assert "repository-read" in CAPABILITY_VOCABULARY
    assert "memory-write" in CAPABILITY_VOCABULARY


def test_node_status_is_the_awiki_planning_vocabulary() -> None:
    values = {s.value for s in TaskNodeStatus}
    assert {"todo", "doing", "done", "blocked", "skipped"} <= values


# --- node contract ------------------------------------------------------------


def test_task_node_is_frozen_and_has_no_dependency_field() -> None:
    node = _node()
    assert dataclasses.is_dataclass(node)
    with pytest.raises(Exception):
        node.id = "other"  # type: ignore[misc]
    # D2: dependencies live ONLY on edges — the node must not carry them.
    assert not hasattr(node, "dependencies")
    assert not hasattr(node, "depends_on")


def test_task_node_requires_an_id() -> None:
    with pytest.raises(ValueError):
        _node("")


def test_task_node_rejects_unknown_capability() -> None:
    with pytest.raises(ValueError):
        _node(worker_requirement=("telepathy",))


def test_task_node_rejects_negative_priority_and_timeout() -> None:
    with pytest.raises(ValueError):
        _node(priority=-1)
    with pytest.raises(ValueError):
        _node(timeout_seconds=0)


# --- edge contract ------------------------------------------------------------


def test_task_edge_holds_the_relation_and_is_frozen() -> None:
    edge = _edge("a", "b", DependencyType.HUMAN_APPROVAL)
    assert edge.from_id == "a" and edge.to_id == "b"
    assert edge.dep_type is DependencyType.HUMAN_APPROVAL
    with pytest.raises(Exception):
        edge.from_id = "z"  # type: ignore[misc]


# --- graph invariants ----------------------------------------------------------


def test_graph_accepts_nodes_and_edges_and_reports_them() -> None:
    graph = TaskGraph()
    graph.add_node(_node("a"))
    graph.add_node(_node("b"))
    graph.add_edge(_edge("a", "b", DependencyType.ORDERING))
    assert set(graph.node_ids()) == {"a", "b"}
    assert list(graph.edges()) == [_edge("a", "b", DependencyType.ORDERING)]
    assert list(graph.edges_to("b")) == [_edge("a", "b", DependencyType.ORDERING)]
    assert list(graph.edges_from("a")) == [_edge("a", "b", DependencyType.ORDERING)]


def test_graph_rejects_duplicate_node_ids() -> None:
    graph = TaskGraph()
    graph.add_node(_node("a"))
    with pytest.raises(ValueError):
        graph.add_node(_node("a"))


def test_graph_rejects_edges_with_unknown_endpoints() -> None:
    graph = TaskGraph()
    graph.add_node(_node("a"))
    with pytest.raises(ValueError):
        graph.add_edge(_edge("a", "ghost"))
    with pytest.raises(ValueError):
        graph.add_edge(_edge("ghost", "a"))


def test_graph_rejects_self_edges() -> None:
    graph = TaskGraph()
    graph.add_node(_node("a"))
    with pytest.raises(ValueError):
        graph.add_edge(_edge("a", "a"))


def test_graph_rejects_duplicate_edges() -> None:
    graph = TaskGraph()
    graph.add_node(_node("a"))
    graph.add_node(_node("b"))
    graph.add_edge(_edge("a", "b"))
    with pytest.raises(ValueError):
        graph.add_edge(_edge("a", "b"))  # same (from, to, type)
    # a different type on the same pair is a distinct relation
    graph.add_edge(_edge("a", "b", DependencyType.FILE_WRITE))


def test_graph_is_friendly_to_iteration_and_len() -> None:
    graph = TaskGraph()
    graph.add_node(_node("a"))
    graph.add_node(_node("b"))
    graph.add_edge(_edge("a", "b"))
    assert len(graph.nodes()) == 2
    assert graph.node("a").objective == "Do the thing"
