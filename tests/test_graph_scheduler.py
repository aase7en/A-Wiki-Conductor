"""GE-6 — Pure deterministic scheduler: schedule_once() -> SchedulePlan.

ADR GE-0006: no polling, no thread, no dispatch, no mutation.
Selects from ReadySet by capacity + policy + conflicts.
"""

from __future__ import annotations

import pytest

from a_conductor.graph.domain import DependencyType, TaskEdge, TaskNode, TaskNodeStatus
from a_conductor.graph.graph import build_graph
from a_conductor.graph.ready import compute_ready_set
from a_conductor.graph.scheduler import (
    BlockedReason,
    SchedulePlan,
    SchedulePolicy,
    WorkerSnapshot,
    schedule_once,
)


def _node(node_id: str, priority: int = 0, worker_req: tuple[str, ...] = ("shell",),
          write_set: tuple[str, ...] = ()) -> TaskNode:
    return TaskNode(
        id=node_id,
        objective=f"obj {node_id}",
        priority=priority,
        worker_requirement=worker_req,
        write_set=write_set,
    )


def _worker(worker_id: str, state: str = "READY", caps: tuple[str, ...] = ("shell",),
            reserved: bool = False) -> WorkerSnapshot:
    return WorkerSnapshot(
        worker_id=worker_id,
        state=state,
        capabilities=caps,
        reserved=reserved,
    )


def _simple_setup(nodes, worker_count=3):
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    workers = tuple(_worker(f"w-{i}") for i in range(worker_count))
    return graph, ready, workers


# --- basic selection -----------------------------------------------------------


def test_selects_ready_nodes_up_to_worker_count() -> None:
    nodes = [_node("a"), _node("b"), _node("c")]
    graph, ready, workers = _simple_setup(nodes, worker_count=2)
    plan = schedule_once(graph, ready, workers, SchedulePolicy())
    assert len(plan.selected) <= 2


def test_max_parallel_limits_selection() -> None:
    nodes = [_node(f"n{i}") for i in range(10)]
    graph, ready, workers = _simple_setup(nodes, worker_count=5)
    plan = schedule_once(graph, ready, workers, SchedulePolicy(max_parallel=3))
    assert len(plan.selected) <= 3


def test_default_max_parallel_is_5() -> None:
    assert SchedulePolicy().max_parallel == 5


# --- priority ordering ---------------------------------------------------------


def test_higher_priority_selected_first() -> None:
    nodes = [_node("low", priority=1), _node("high", priority=10), _node("mid", priority=5)]
    graph, ready, workers = _simple_setup(nodes, worker_count=1)
    plan = schedule_once(graph, ready, workers, SchedulePolicy())
    assert plan.selected[0].node_id == "high"


def test_lexical_tiebreak_when_same_priority() -> None:
    nodes = [_node("z"), _node("a"), _node("m")]
    graph, ready, workers = _simple_setup(nodes, worker_count=1)
    plan = schedule_once(graph, ready, workers, SchedulePolicy())
    assert plan.selected[0].node_id == "a"


# --- capability matching ---------------------------------------------------------


def test_capability_mismatch_blocks() -> None:
    nodes = [_node("needs_shell", worker_req=("shell",))]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    workers = (_worker("w-0", caps=("documentation",)),)  # no shell
    plan = schedule_once(graph, ready, workers, SchedulePolicy())
    assert len(plan.selected) == 0
    assert any(r.node_id == "needs_shell" for r in plan.blocked)


def test_capability_match_selects() -> None:
    nodes = [_node("worker", worker_req=("shell",))]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    workers = (_worker("w-0", caps=("shell", "tests")),)
    plan = schedule_once(graph, ready, workers, SchedulePolicy())
    assert len(plan.selected) == 1
    assert plan.selected[0].worker_id == "w-0"


# --- worker availability ----------------------------------------------------------


def test_reserved_worker_not_selected() -> None:
    nodes = [_node("task")]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    workers = (_worker("w-0", reserved=True),)
    plan = schedule_once(graph, ready, workers, SchedulePolicy())
    assert len(plan.selected) == 0


def test_no_workers_no_selection() -> None:
    nodes = [_node("task")]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    plan = schedule_once(graph, ready, (), SchedulePolicy())
    assert len(plan.selected) == 0
    assert len(plan.blocked) >= 1


# --- conflict prevention ----------------------------------------------------------


def test_write_conflict_with_running_blocks() -> None:
    nodes = [
        _node("running", write_set=("f.py",)),
        _node("todo", write_set=("f.py",)),
    ]
    graph = build_graph(nodes, [])
    states = {"running": TaskNodeStatus.DOING, "todo": TaskNodeStatus.TODO}
    ready = compute_ready_set(graph, states)
    workers = (_worker("w-0"), _worker("w-1"))
    # running is DOING so not in ready set; todo should be blocked by conflict
    plan = schedule_once(graph, ready, workers, SchedulePolicy(),
                         running_write_sets={"running": ("f.py",)})
    assert all(s.node_id != "todo" for s in plan.selected)


def test_same_batch_conflict_prevented() -> None:
    """Two nodes writing the same file must NOT both be selected in one pass."""
    nodes = [
        _node("a", write_set=("shared.py",)),
        _node("b", write_set=("shared.py",)),
    ]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    workers = (_worker("w-0"), _worker("w-1"))
    plan = schedule_once(graph, ready, workers, SchedulePolicy())
    selected_ids = {s.node_id for s in plan.selected}
    # At most one of a/b should be selected (the other is deferred)
    assert not ("a" in selected_ids and "b" in selected_ids), (
        "Same-batch write conflict: both a and b selected"
    )


# --- SchedulePlan structure ---------------------------------------------------------


def test_plan_is_immutable() -> None:
    nodes = [_node("a")]
    graph, ready, workers = _simple_setup(nodes, 1)
    plan = schedule_once(graph, ready, workers, SchedulePolicy())
    with pytest.raises(AttributeError):
        plan.selected = ()


def test_blocked_has_reasons() -> None:
    nodes = [_node("needs_shell", worker_req=("shell",))]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    workers = (_worker("w-0", caps=("docs",)),)
    plan = schedule_once(graph, ready, workers, SchedulePolicy())
    assert len(plan.blocked) >= 1
    blocked = plan.blocked[0]
    assert blocked.reason != ""
    assert "capability" in blocked.reason.lower() or "worker" in blocked.reason.lower()


def test_pure_function_no_mutation() -> None:
    """schedule_once must not mutate graph nodes or workers."""
    nodes = [_node("a", priority=5)]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    workers = (_worker("w-0"),)
    plan = schedule_once(graph, ready, workers, SchedulePolicy())
    # Verify node unchanged
    assert graph.node("a").priority == 5
    assert graph.node("a").status == TaskNodeStatus.TODO
    # Verify worker unchanged
    assert workers[0].reserved is False
