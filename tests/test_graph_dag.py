"""GE-3 — DAG engine: topological ordering, ready levels, cycle naming.

Port of A-Wiki scripts/eval/dag_eval.py semantics (ADR GE-0004, D1):
Kahn's algorithm + cycle detection with the actual cycle path named.
Ready levels answer "which nodes can run in parallel at each wave".
"""

from __future__ import annotations

import pytest

from a_conductor.graph.dag import (
    DagResult,
    compute_ready_levels,
    topological_sort,
    validate_acyclic,
)
from a_conductor.graph.domain import DependencyType, TaskEdge, TaskNode
from a_conductor.graph.graph import build_graph


def _node(node_id: str) -> TaskNode:
    return TaskNode(id=node_id, objective=f"obj {node_id}")


def _linear() -> "object":
    return build_graph(
        [_node(x) for x in ("a", "b", "c")],
        [TaskEdge("a", "b"), TaskEdge("b", "c")],
    )


def _diamond() -> "object":
    return build_graph(
        [_node(x) for x in ("start", "left", "right", "join")],
        [
            TaskEdge("start", "left"),
            TaskEdge("start", "right"),
            TaskEdge("left", "join"),
            TaskEdge("right", "join"),
        ],
    )


def _fanout() -> "object":
    return build_graph(
        [_node(x) for x in ("root", "x", "y", "z", "sink")],
        [
            TaskEdge("root", "x"),
            TaskEdge("root", "y"),
            TaskEdge("root", "z"),
            TaskEdge("x", "sink"),
            TaskEdge("y", "sink"),
            TaskEdge("z", "sink"),
        ],
    )


def _cyclic() -> "object":
    """Build a cyclic graph bypassing the builder's invariant.

    The builder rejects cycles, so we construct the raw TaskGraph directly
    to test the DAG engine's own cycle detection.
    """
    from a_conductor.graph.domain import TaskGraph

    graph = TaskGraph()
    for n in ("a", "b", "c"):
        graph.add_node(_node(n))
    graph.add_edge(TaskEdge("a", "b"))
    graph.add_edge(TaskEdge("b", "c"))
    graph.add_edge(TaskEdge("c", "a"))  # cycle!
    return graph


# --- topological sort --------------------------------------------------------


def test_linear_topological_sort() -> None:
    result = topological_sort(_linear())
    assert isinstance(result, DagResult)
    assert result.order == ("a", "b", "c")
    assert result.cycle is None


def test_diamond_topological_sort() -> None:
    result = topological_sort(_diamond())
    assert result.order[0] == "start"
    assert result.order[-1] == "join"
    assert set(result.order[1:3]) == {"left", "right"}


def test_fanout_topological_sort() -> None:
    result = topological_sort(_fanout())
    assert result.order[0] == "root"
    assert result.order[-1] == "sink"
    assert set(result.order[1:4]) == {"x", "y", "z"}


def test_single_node_sort() -> None:
    result = topological_sort(build_graph([_node("only")], []))
    assert result.order == ("only",)


def test_empty_graph_sort() -> None:
    result = topological_sort(build_graph([], []))
    assert result.order == ()
    assert result.cycle is None


# --- cycle detection ----------------------------------------------------------


def test_cyclic_graph_returns_cycle_not_crash() -> None:
    result = topological_sort(_cyclic())
    assert result.cycle is not None
    assert set(result.cycle) == {"a", "b", "c"}
    assert result.order == ()  # no valid ordering


def test_cycle_path_is_connected() -> None:
    """The cycle list should be an actual walkable path, not random names."""
    result = topological_sort(_cyclic())
    assert result.cycle is not None
    cycle = result.cycle
    # Each consecutive pair (excluding the closing wrap) should be an edge
    edge_set = {("a", "b"), ("b", "c"), ("c", "a")}
    for i in range(len(cycle) - 1):
        pair = (cycle[i], cycle[i + 1])
        assert pair in edge_set, f"cycle walk broken at {pair}"
    # The cycle should close: last node connects back to first
    assert (cycle[-1], cycle[0]) in edge_set or cycle[-1] == cycle[0]


# --- ready levels ---------------------------------------------------------------


def test_linear_ready_levels() -> None:
    levels = compute_ready_levels(_linear())
    assert levels == [("a",), ("b",), ("c",)]


def test_diamond_ready_levels() -> None:
    levels = compute_ready_levels(_diamond())
    assert len(levels) == 3
    assert levels[0] == ("start",)
    assert set(levels[1]) == {"left", "right"}
    assert levels[2] == ("join",)


def test_fanout_ready_levels() -> None:
    levels = compute_ready_levels(_fanout())
    assert levels[0] == ("root",)
    assert set(levels[1]) == {"x", "y", "z"}
    assert levels[2] == ("sink",)


def test_independent_nodes_same_level() -> None:
    graph = build_graph([_node("p"), _node("q"), _node("r")], [])
    levels = compute_ready_levels(graph)
    assert len(levels) == 1
    assert set(levels[0]) == {"p", "q", "r"}


# --- validate_acyclic helper ----------------------------------------------------


def test_validate_acyclic_passes_for_valid_dag() -> None:
    assert validate_acyclic(_diamond()) is None


def test_validate_acyclic_returns_cycle_for_cyclic() -> None:
    cycle = validate_acyclic(_cyclic())
    assert cycle is not None
    assert set(cycle) == {"a", "b", "c"}


def test_dag_result_reports_levels_and_order() -> None:
    result = topological_sort(_diamond())
    assert result.levels is not None
    assert len(result.levels) == 3
    assert set(result.levels[1]) == {"left", "right"}
