"""GE-2 — durable SQLite persistence for TaskGraph (round-trip + events)."""

from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.graph.domain import DependencyType, TaskEdge, TaskNode, TaskNodeStatus
from a_conductor.graph.graph import build_graph
from a_conductor.graph.store import GraphStore


def _node(node_id: str, **overrides) -> TaskNode:
    defaults = dict(
        id=node_id,
        objective=f"objective {node_id}",
        expected_outputs=("out.md",),
        read_set=("src/**",),
        write_set=("docs/x.md",),
        worker_requirement=("repository-read", "shell"),
        priority=5,
        timeout_seconds=600,
        retry_policy_ref="default",
        status=TaskNodeStatus.TODO,
    )
    defaults.update(overrides)
    return TaskNode(**defaults)


def _simple_graph() -> "object":
    return build_graph(
        [_node("a"), _node("b"), _node("c")],
        [
            TaskEdge("a", "b", DependencyType.DATA),
            TaskEdge("b", "c", DependencyType.VERIFICATION),
        ],
    )


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    store = GraphStore(tmp_path / "graphs.sqlite")
    graph = _simple_graph()
    store.save_graph(graph, "g1")

    loaded = store.load_graph("g1")
    assert set(loaded.node_ids()) == {"a", "b", "c"}
    assert len(loaded.edges()) == 2
    assert loaded.node("a").objective == "objective a"
    assert loaded.node("b").worker_requirement == ("repository-read", "shell")
    assert loaded.node("c").expected_outputs == ("out.md",)


def test_save_replaces_existing_graph(tmp_path: Path) -> None:
    store = GraphStore(tmp_path / "g.sqlite")
    store.save_graph(_simple_graph(), "g1")
    smaller = build_graph([_node("only")], [])
    store.save_graph(smaller, "g1")
    loaded = store.load_graph("g1")
    assert loaded.node_ids() == ("only",)
    assert loaded.edges() == ()


def test_list_and_delete(tmp_path: Path) -> None:
    store = GraphStore(tmp_path / "g.sqlite")
    store.save_graph(_simple_graph(), "g1")
    store.save_graph(build_graph([_node("z")], []), "g2")
    assert set(store.list_graph_ids()) == {"g1", "g2"}
    store.delete_graph("g1")
    assert store.list_graph_ids() == ["g2"]


def test_node_events_round_trip(tmp_path: Path) -> None:
    store = GraphStore(tmp_path / "g.sqlite")
    store.save_graph(_simple_graph(), "g1")
    store.record_node_event("g1", "a", "claimed", '{"worker": "w1"}')
    store.record_node_event("g1", "a", "completed", '{"evidence": "tests pass"}')
    store.record_node_event("g1", "b", "started", "{}")

    events_a = store.node_events("g1", "a")
    assert len(events_a) == 2
    assert events_a[0]["event_type"] == "claimed"
    assert "w1" in events_a[0]["payload"]
    assert events_a[1]["event_type"] == "completed"

    events_b = store.node_events("g1", "b")
    assert len(events_b) == 1


def test_status_round_trip_preserves_enum(tmp_path: Path) -> None:
    store = GraphStore(tmp_path / "g.sqlite")
    graph = build_graph([_node("s", status=TaskNodeStatus.DOING)], [])
    store.save_graph(graph, "gs")
    loaded = store.load_graph("gs")
    assert loaded.node("s").status == TaskNodeStatus.DOING


def test_cycle_still_rejected_after_load(tmp_path: Path) -> None:
    store = GraphStore(tmp_path / "g.sqlite")
    store.save_graph(_simple_graph(), "g1")
    loaded = store.load_graph("g1")
    # Add an edge that would create a cycle: c -> a
    from a_conductor.graph.graph import GraphCycleError
    # Simulate: rebuild with the extra edge should fail
    with pytest.raises(GraphCycleError):
        build_graph(
            loaded.nodes(),
            list(loaded.edges()) + [TaskEdge("c", "a", DependencyType.DATA)],
        )
