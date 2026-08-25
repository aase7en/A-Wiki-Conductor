"""GE-1b — TaskGraph assembly + acyclicity (ADR GE-0001, GE-0004 credit)."""

from __future__ import annotations

import pytest

from a_conductor.graph.domain import DependencyType, TaskEdge, TaskNode
from a_conductor.graph.graph import GraphCycleError, TaskGraphBuilder, build_graph


def _node(node_id: str) -> TaskNode:
    return TaskNode(id=node_id, objective=f"objective {node_id}")


def test_builder_assembles_valid_graph() -> None:
    graph = (
        TaskGraphBuilder()
        .add_node(_node("a"))
        .add_node(_node("b"))
        .add_node(_node("c"))
        .add_edge(TaskEdge("a", "b", DependencyType.DATA))
        .add_edge(TaskEdge("b", "c", DependencyType.ORDERING))
        .build()
    )
    assert set(graph.node_ids()) == {"a", "b", "c"}
    assert len(graph.edges()) == 2


def test_builder_rejects_simple_cycle_and_rolls_back() -> None:
    builder = TaskGraphBuilder().add_node(_node("a")).add_node(_node("b"))
    builder.add_edge(TaskEdge("a", "b", DependencyType.DATA))
    with pytest.raises(GraphCycleError) as exc:
        builder.add_edge(TaskEdge("b", "a", DependencyType.ORDERING))
    assert "a" in str(exc.value) and "b" in str(exc.value)
    graph = builder.build()
    # The offending edge was rolled back: a->b remains, b->a is gone.
    assert len(graph.edges()) == 1
    assert graph.edges()[0].from_id == "a"


def test_builder_rejects_long_cycle_with_named_nodes() -> None:
    builder = TaskGraphBuilder()
    for n in ("a", "b", "c", "d"):
        builder.add_node(_node(n))
    builder.add_edge(TaskEdge("a", "b"))
    builder.add_edge(TaskEdge("b", "c"))
    builder.add_edge(TaskEdge("c", "d"))
    with pytest.raises(GraphCycleError) as exc:
        builder.add_edge(TaskEdge("d", "a"))
    assert set(exc.value.cycle) & {"a", "b", "c", "d"}
    assert len(builder.build().edges()) == 3  # rolled back


def test_diamond_shape_is_valid() -> None:
    graph = build_graph(
        [_node(x) for x in ("start", "left", "right", "join")],
        [
            TaskEdge("start", "left"),
            TaskEdge("start", "right"),
            TaskEdge("left", "join"),
            TaskEdge("right", "join"),
        ],
    )
    assert len(graph.edges()) == 4
    assert len(graph.edges_to("join")) == 2


def test_every_dependency_type_is_a_precedence_edge_for_cycles() -> None:
    builder = TaskGraphBuilder().add_node(_node("x")).add_node(_node("y"))
    builder.add_edge(TaskEdge("x", "y", DependencyType.HUMAN_APPROVAL))
    with pytest.raises(GraphCycleError):
        builder.add_edge(TaskEdge("y", "x", DependencyType.VERIFICATION))


def test_build_graph_convenience_matches_builder() -> None:
    graph = build_graph([_node("a"), _node("b")], [TaskEdge("a", "b")])
    assert graph.node("a").objective == "objective a"
    assert graph.edges()[0].dep_type.value == "DATA"
