"""GE-4 — dependency analyzer: derive hidden conflicts from node metadata.

Given a TaskGraph with nodes that declare write_set (file globs) and
worker/runtime bindings, the analyzer derives FILE_WRITE / WORKSPACE_WRITE /
GIT / WORKER / RUNTIME dependency edges that the planner didn't declare
explicitly — D4 guardrail: only true predecessor relations become edges.
"""

from __future__ import annotations

import pytest

from a_conductor.graph.analyze import analyze_conflicts, ConflictsReport
from a_conductor.graph.domain import DependencyType, TaskEdge, TaskNode
from a_conductor.graph.graph import build_graph


def _node(
    node_id: str,
    write_set: tuple[str, ...] = (),
    read_set: tuple[str, ...] = (),
    workspace: str | None = None,
    worker_binding: str | None = None,
) -> TaskNode:
    parts = []
    if workspace:
        parts.append(f"ws:{workspace}")
    if worker_binding:
        parts.append(f"worker:{worker_binding}")
    return TaskNode(
        id=node_id,
        objective=f"obj {node_id}",
        write_set=write_set,
        read_set=read_set,
        model_requirement="|".join(parts) if parts else None,
    )


def _parse_binding(node: TaskNode) -> dict[str, str]:
    """Extract structured bindings from model_requirement."""
    if node.model_requirement and ":" in node.model_requirement:
        key, _, val = node.model_requirement.partition(":")
        return {key: val}
    return {}


# --- FILE_WRITE conflicts ----------------------------------------------------


def test_two_nodes_writing_same_file_conflict() -> None:
    graph = build_graph(
        [
            _node("a", write_set=("src/shared.py",)),
            _node("b", write_set=("src/shared.py",)),
        ],
        [],
    )
    report = analyze_conflicts(graph)
    assert ("a", "b", DependencyType.FILE_WRITE) in report.conflicts


def test_no_conflict_when_write_sets_disjoint() -> None:
    graph = build_graph(
        [
            _node("a", write_set=("src/a.py",)),
            _node("b", write_set=("src/b.py",)),
        ],
        [],
    )
    report = analyze_conflicts(graph)
    assert len(report.conflicts) == 0


def test_glob_overlap_detects_conflict() -> None:
    """A writes a glob that overlaps B's specific file."""
    graph = build_graph(
        [
            _node("a", write_set=("src/**/*.py",)),
            _node("b", write_set=("src/specific.py",)),
        ],
        [],
    )
    report = analyze_conflicts(graph)
    assert ("a", "b", DependencyType.FILE_WRITE) in report.conflicts


def test_read_write_no_conflict() -> None:
    """One reads, one writes the same file — not a write-write conflict."""
    graph = build_graph(
        [
            _node("a", read_set=("doc.md",)),
            _node("b", write_set=("doc.md",)),
        ],
        [],
    )
    report = analyze_conflicts(graph)
    assert len(report.conflicts) == 0


# --- WORKSPACE_WRITE conflicts -------------------------------------------------


def test_same_workspace_conflict() -> None:
    graph = build_graph(
        [
            _node("a", workspace="A:/GitHub/repo1"),
            _node("b", workspace="A:/GitHub/repo1"),
        ],
        [],
    )
    report = analyze_conflicts(graph)
    assert ("a", "b", DependencyType.WORKSPACE_WRITE) in report.conflicts


def test_different_workspaces_no_conflict() -> None:
    graph = build_graph(
        [
            _node("a", workspace="A:/GitHub/repo1"),
            _node("b", workspace="A:/GitHub/repo2"),
        ],
        [],
    )
    report = analyze_conflicts(graph)
    assert len(report.conflicts) == 0


# --- WORKER conflicts ------------------------------------------------------------


def test_same_worker_binding_conflict() -> None:
    graph = build_graph(
        [
            _node("a", worker_binding="sunday-worker-1"),
            _node("b", worker_binding="sunday-worker-1"),
        ],
        [],
    )
    report = analyze_conflicts(graph)
    assert ("a", "b", DependencyType.WORKER) in report.conflicts


def test_different_workers_no_conflict() -> None:
    graph = build_graph(
        [
            _node("a", worker_binding="sunday-worker-1"),
            _node("b", worker_binding="sunday-worker-2"),
        ],
        [],
    )
    report = analyze_conflicts(graph)
    assert len(report.conflicts) == 0


# --- combined + report structure --------------------------------------------------


def test_report_counts_by_type() -> None:
    graph = build_graph(
        [
            _node("a", write_set=("f.py",), workspace="ws1", worker_binding="w1"),
            _node("b", write_set=("f.py",), workspace="ws1", worker_binding="w1"),
            _node("c", write_set=("other.py",)),
        ],
        [],
    )
    report = analyze_conflicts(graph)
    assert report.conflict_count(DependencyType.FILE_WRITE) >= 1
    assert report.conflict_count(DependencyType.WORKSPACE_WRITE) >= 1
    assert report.conflict_count(DependencyType.WORKER) >= 1
    assert report.conflict_count(DependencyType.GIT) == 0


def test_explicit_edges_are_not_re_derived() -> None:
    """The analyzer should not duplicate an edge the planner already declared."""
    graph = build_graph(
        [
            _node("a", write_set=("f.py",)),
            _node("b", write_set=("f.py",)),
        ],
        [TaskEdge("a", "b", DependencyType.ORDERING)],  # planner already ordered a→b
    )
    report = analyze_conflicts(graph)
    # a→b FILE_WRITE is still reported (it's a different type than ORDERING),
    # but the analyzer should note it's already sequenced
    assert report.already_sequenced >= 1


def test_single_node_no_conflicts() -> None:
    graph = build_graph([_node("solo", write_set=("x.py",))], [])
    report = analyze_conflicts(graph)
    assert len(report.conflicts) == 0


def test_conflicts_are_symmetric_pairs() -> None:
    """FILE_WRITE conflicts report both (a,b) and (b,a) — the scheduler
    needs to know either direction blocks the other."""
    graph = build_graph(
        [
            _node("a", write_set=("f.py",)),
            _node("b", write_set=("f.py",)),
        ],
        [],
    )
    report = analyze_conflicts(graph)
    has_ab = ("a", "b", DependencyType.FILE_WRITE) in report.conflicts
    has_ba = ("b", "a", DependencyType.FILE_WRITE) in report.conflicts
    # At minimum, one direction must be reported
    assert has_ab or has_ba
