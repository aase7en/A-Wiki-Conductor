from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.domain import TaskState
from a_conductor.graph.dispatch import GraphDispatchKey
from a_conductor.graph.domain import TaskEdge, TaskNode, TaskNodeStatus
from a_conductor.graph.graph import build_graph
from a_conductor.graph.operator_view import (
    GraphOperatorViewError,
    list_operator_graph_ids,
    read_graph_operator_snapshot,
)
from a_conductor.graph.store import GraphStore
from a_conductor.job_store import SQLiteJobStore


def _graph():
    return build_graph(
        [
            TaskNode(id="a", objective="prepare"),
            TaskNode(id="b", objective="verify"),
            TaskNode(id="join", objective="finish"),
        ],
        [TaskEdge("a", "join"), TaskEdge("b", "join")],
    )

def _to_state(store: SQLiteJobStore, state, target: TaskState, **kwargs):
    return store.transition(
        state.job_id,
        target,
        expected_version=state.version,
        **kwargs,
    )


def _job(store: SQLiteJobStore, job_id: str, target: TaskState):
    state = store.create_job(
        job_id=job_id,
        work_order_ref="wo:ge11",
        project_id="project-1",
    )
    if target is TaskState.NEW:
        return state
    state = _to_state(store, state, TaskState.READY)
    if target is TaskState.READY:
        return state
    state = _to_state(store, state, TaskState.CLAIMED, worker_id="a-worker-01")
    if target is TaskState.CLAIMED:
        return state
    state = _to_state(store, state, TaskState.GATING, worker_id="a-worker-01")
    if target is TaskState.GATING:
        return state
    state = _to_state(store, state, TaskState.EXECUTING, worker_id="a-worker-01")
    if target is TaskState.EXECUTING:
        return state
    state = _to_state(store, state, TaskState.VERIFYING, worker_id="a-worker-01")
    if target is TaskState.VERIFYING:
        return state
    return _to_state(store, state, target)

def test_list_graph_ids_on_missing_database_is_read_only(tmp_path: Path) -> None:
    database = tmp_path / "missing.sqlite"

    assert list_operator_graph_ids(database) == ()
    assert not database.exists()


def test_planning_snapshot_has_no_runtime_evidence_and_does_not_write(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    graph = _graph()
    GraphStore(database).save_graph(graph, "graph-1")
    before = database.stat().st_mtime_ns

    snapshot = read_graph_operator_snapshot(database, "graph-1")

    assert snapshot.graph_id == "graph-1"
    assert snapshot.graph_run_id is None
    assert snapshot.runtime_evidence is False
    assert {node.node_id: node.status for node in snapshot.nodes} == {
        "a": TaskNodeStatus.TODO,
        "b": TaskNodeStatus.TODO,
        "join": TaskNodeStatus.TODO,
    }
    assert snapshot.events == ()
    assert database.stat().st_mtime_ns == before

def test_unproven_explicit_run_does_not_claim_runtime_evidence(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    GraphStore(database).save_graph(_graph(), "graph-1")
    SQLiteJobStore(database).initialize()

    snapshot = read_graph_operator_snapshot(database, "graph-1", "run-does-not-exist")

    assert snapshot.graph_run_id == "run-does-not-exist"
    assert snapshot.runtime_evidence is False
    assert all(node.status is TaskNodeStatus.TODO for node in snapshot.nodes)
    assert snapshot.events == ()


def test_explicit_run_projects_durable_states_and_worker_identity(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    graph = _graph()
    GraphStore(database).save_graph(graph, "graph-1")
    jobs = SQLiteJobStore(database)
    key_a = GraphDispatchKey("graph-1", "run-1", "a")
    key_b = GraphDispatchKey("graph-1", "run-1", "b")
    _job(jobs, key_a.job_id, TaskState.COMPLETE)
    _job(jobs, key_b.job_id, TaskState.EXECUTING)

    snapshot = read_graph_operator_snapshot(database, "graph-1", "run-1")
    states = {node.node_id: node.status for node in snapshot.nodes}
    workers = {node.node_id: node.worker_id for node in snapshot.nodes}

    assert snapshot.runtime_evidence is True
    assert states == {
        "a": TaskNodeStatus.DONE,
        "b": TaskNodeStatus.DOING,
        "join": TaskNodeStatus.TODO,
    }
    assert workers["a"] is None
    assert workers["b"] == "a-worker-01"
    assert workers["join"] is None


def test_runtime_timeline_is_bounded_and_uses_durable_job_events(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    GraphStore(database).save_graph(_graph(), "graph-1")
    jobs = SQLiteJobStore(database)
    key = GraphDispatchKey("graph-1", "run-1", "a")
    state = _job(jobs, key.job_id, TaskState.EXECUTING)
    for index in range(8):
        state = jobs.checkpoint(
            state.job_id,
            checkpoint_ref=f"ge11:event:{index}",
            expected_version=state.version,
        )

    snapshot = read_graph_operator_snapshot(
        database, "graph-1", "run-1", event_limit=5
    )

    assert len(snapshot.events) == 5
    assert all(event.node_id == "a" for event in snapshot.events)
    assert snapshot.events[0].sequence_no > snapshot.events[-1].sequence_no

def test_missing_graph_fails_closed(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    GraphStore(database).save_graph(_graph(), "graph-1")

    with pytest.raises(GraphOperatorViewError) as exc:
        read_graph_operator_snapshot(database, "missing")

    assert exc.value.code == "GRAPH_NOT_FOUND"


def test_explicit_run_id_is_required_for_runtime_projection(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    graph = _graph()
    GraphStore(database).save_graph(graph, "graph-1")
    jobs = SQLiteJobStore(database)
    key = GraphDispatchKey("graph-1", "run-hidden", "a")
    _job(jobs, key.job_id, TaskState.COMPLETE)

    planning = read_graph_operator_snapshot(database, "graph-1")
    runtime = read_graph_operator_snapshot(database, "graph-1", "run-hidden")

    assert next(node for node in planning.nodes if node.node_id == "a").status is TaskNodeStatus.TODO
    assert next(node for node in runtime.nodes if node.node_id == "a").status is TaskNodeStatus.DONE
