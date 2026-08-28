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
            reserved: bool = False, workspace: str | None = None,
            mutation_authorized: bool = True) -> WorkerSnapshot:
    return WorkerSnapshot(
        worker_id=worker_id,
        state=state,
        capabilities=caps,
        reserved=reserved,
        workspace=workspace,
        mutation_authorized=mutation_authorized,
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
    """External running write-set must block an otherwise-ready node.

    Conflicts with in-graph DOING nodes are already surfaced by
    compute_ready_set; the scheduler seam covers external reservations
    supplied via running_write_sets.
    """
    nodes = [
        TaskNode(
            id="todo",
            objective="o",
            worker_requirement=("shell",),
            write_set=("f.py",),
            model_requirement="ws:/repo",
        ),
    ]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    workers = (_worker("w-0", workspace="/repo"),)
    plan = schedule_once(
        graph,
        ready,
        workers,
        SchedulePolicy(),
        running_write_sets={"external-running": ("f.py",)},
    )
    assert all(s.node_id != "todo" for s in plan.selected)
    assert any(
        "conflict" in r.reason.lower() for r in plan.blocked if r.node_id == "todo"
    )


def test_same_batch_conflict_prevented() -> None:
    """Two nodes writing the same file must NOT both be selected in one pass."""
    nodes = [
        TaskNode(
            id="a",
            objective="o",
            worker_requirement=("shell",),
            write_set=("shared.py",),
            model_requirement="ws:/repo",
        ),
        TaskNode(
            id="b",
            objective="o",
            worker_requirement=("shell",),
            write_set=("shared.py",),
            model_requirement="ws:/repo",
        ),
    ]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    workers = (_worker("w-0", workspace="/repo"), _worker("w-1", workspace="/repo"))
    plan = schedule_once(graph, ready, workers, SchedulePolicy())
    selected_ids = {s.node_id for s in plan.selected}
    # At most one of a/b should be selected (the other is deferred)
    assert not ("a" in selected_ids and "b" in selected_ids), (
        "Same-batch write conflict: both a and b selected"
    )
    assert len(selected_ids) == 1  # identity passes; exactly one runs, one conflicts


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


# --- GE-6 review round 2: ADR GE-0006 ordering / identity / eligibility ------

# Blocker 1: priority -> earlier topological rank -> lexical node ID.


def test_same_priority_orders_by_topological_rank_before_lexical_id() -> None:
    """c-early (topo rank 1) must beat b-later (topo rank 2, lexically first)."""
    nodes = [
        _node("a-done"),
        _node("b-later"),  # depends on a-done; "b-later" < "c-early" lexically
        _node("c-early"),
    ]
    graph = build_graph(
        nodes, [TaskEdge(from_id="a-done", to_id="b-later")]
    )
    states = {"a-done": TaskNodeStatus.DONE}
    ready = compute_ready_set(graph, states)
    assert "b-later" in ready.ready_ids and "c-early" in ready.ready_ids
    plan = schedule_once(graph, ready, (_worker("w-0"),), SchedulePolicy())
    assert [s.node_id for s in plan.selected] == ["c-early"]


# Blocker 2: equivalent worker selection is stable by worker ID.


def test_equivalent_worker_selection_is_stable_by_worker_id() -> None:
    """Input order must not decide which worker gets the first node."""
    nodes = [_node("t1"), _node("t2")]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    workers = (_worker("w-bravo"), _worker("w-alpha"))  # deliberately unsorted
    plan = schedule_once(graph, ready, workers, SchedulePolicy())
    assert plan.selected[0].worker_id == "w-alpha"
    assert plan.selected[1].worker_id == "w-bravo"


# Blocker 3: mutating tasks enforce project/workspace identity fail-closed.


def _mutating_node(node_id: str, model_requirement: str | None) -> TaskNode:
    return TaskNode(
        id=node_id,
        objective=f"obj {node_id}",
        worker_requirement=("shell",),
        write_set=("src/x.py",),
        model_requirement=model_requirement,
    )


def test_mutating_node_requires_matching_workspace_identity() -> None:
    nodes = [_mutating_node("mut", "ws:/repo/alpha")]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})

    wrong = _worker("w-wrong", workspace="/repo/beta")
    plan = schedule_once(graph, ready, (wrong,), SchedulePolicy())
    assert all(s.node_id != "mut" for s in plan.selected)
    assert any("identity" in r.reason.lower() for r in plan.blocked)

    right = _worker("w-right", workspace="/repo/alpha")
    plan2 = schedule_once(graph, ready, (right,), SchedulePolicy())
    assert [s.node_id for s in plan2.selected] == ["mut"]


def test_mutating_node_fails_closed_without_identity_binding() -> None:
    nodes = [_mutating_node("mut", None)]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    capable = _worker("w-ok", workspace="/repo/alpha")
    plan = schedule_once(graph, ready, (capable,), SchedulePolicy())
    assert all(s.node_id != "mut" for s in plan.selected)
    assert any("identity" in r.reason.lower() for r in plan.blocked)


def test_mutating_node_requires_mutation_authorized_worker() -> None:
    nodes = [_mutating_node("mut", "ws:/repo/alpha")]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    unauthorized = _worker(
        "w-noauth", workspace="/repo/alpha", mutation_authorized=False
    )
    plan = schedule_once(graph, ready, (unauthorized,), SchedulePolicy())
    assert all(s.node_id != "mut" for s in plan.selected)
    assert any("mutation" in r.reason.lower() for r in plan.blocked)


def test_read_only_node_not_blocked_by_mutation_unauthorized() -> None:
    """Empty write_set = read-only: mutation authority must not block it."""
    nodes = [_node("ro")]  # read-only: no write_set
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    worker = _worker("w-ro", mutation_authorized=False)
    plan = schedule_once(graph, ready, (worker,), SchedulePolicy())
    assert [s.node_id for s in plan.selected] == ["ro"]


# Blocker 4: injected gate/provider eligibility seam (no reservation, no dispatch).


@pytest.mark.parametrize(
    "flag,expected_fragment",
    [
        ("gate_refused", "gate"),
        ("provider_unavailable", "provider"),
        ("rate_limited", "rate"),
    ],
)
def test_ineligibility_blocks_without_selection(flag: str, expected_fragment: str) -> None:
    from a_conductor.graph.scheduler import NodeEligibility

    nodes = [_node("n")]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    workers = (_worker("w-0"),)
    plan = schedule_once(
        graph,
        ready,
        workers,
        SchedulePolicy(),
        eligibility={"n": NodeEligibility(**{flag: True})},
    )
    assert all(s.node_id != "n" for s in plan.selected)
    reasons = [r.reason.lower() for r in plan.blocked if r.node_id == "n"]
    assert any(expected_fragment in reason for reason in reasons)


def test_eligible_node_with_default_eligibility_still_selects() -> None:
    from a_conductor.graph.scheduler import NodeEligibility

    nodes = [_node("n")]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    plan = schedule_once(
        graph,
        ready,
        (_worker("w-0"),),
        SchedulePolicy(),
        eligibility={"n": NodeEligibility()},
    )
    assert [s.node_id for s in plan.selected] == ["n"]


# --- GE-6 final round: explicit worker binding (ADR §4/§5) --------------------


def _bound_node(node_id: str, binding: str, write_set: tuple[str, ...] = ()) -> TaskNode:
    return TaskNode(
        id=node_id,
        objective=f"obj {node_id}",
        worker_requirement=("shell",),
        write_set=write_set,
        model_requirement=binding,
    )


def test_explicit_worker_binding_is_authoritative() -> None:
    """Bound `worker:w-z` must win over the stable worker-ID order (w-a)."""
    nodes = [_bound_node("n", "worker:w-z")]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    workers = (_worker("w-a"), _worker("w-z"))
    plan = schedule_once(graph, ready, workers, SchedulePolicy())
    assert [(s.node_id, s.worker_id) for s in plan.selected] == [("n", "w-z")]


@pytest.mark.parametrize(
    "bound_worker",
    [
        _worker("w-z", state="STOPPED"),
        _worker("w-z", reserved=True),
        _worker("w-z", caps=("documentation",)),
    ],
    ids=["not-ready", "reserved", "capability-mismatch"],
)
def test_bound_worker_unusable_blocks_never_falls_back(bound_worker) -> None:
    """An unusable bound worker must block, never silently pick w-a."""
    nodes = [_bound_node("n", "worker:w-z")]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    workers = (_worker("w-a"), bound_worker)
    plan = schedule_once(graph, ready, workers, SchedulePolicy())
    assert plan.selected == ()
    reasons = [r.reason.lower() for r in plan.blocked if r.node_id == "n"]
    assert any("binding" in reason for reason in reasons)


def test_bound_worker_missing_entirely_blocks_never_falls_back() -> None:
    nodes = [_bound_node("n", "worker:w-z")]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    workers = (_worker("w-a"),)  # w-z not even in the snapshot
    plan = schedule_once(graph, ready, workers, SchedulePolicy())
    assert plan.selected == ()
    assert any("binding" in r.reason.lower() for r in plan.blocked)


def test_mutating_bound_worker_still_requires_identity_and_authority() -> None:
    """Binding is authoritative but never bypasses identity/mutation gates."""
    nodes = [_bound_node("mut", "ws:/repo/alpha|worker:w-z", write_set=("src/x.py",))]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})

    wrong_ws = _worker("w-z", workspace="/repo/beta")
    plan = schedule_once(
        graph, ready, (_worker("w-a", workspace="/repo/alpha"), wrong_ws), SchedulePolicy()
    )
    assert plan.selected == ()
    assert any("binding" in r.reason.lower() for r in plan.blocked)

    no_auth = _worker("w-z", workspace="/repo/alpha", mutation_authorized=False)
    plan2 = schedule_once(
        graph, ready, (_worker("w-a", workspace="/repo/alpha"), no_auth), SchedulePolicy()
    )
    assert plan2.selected == ()
    assert any("binding" in r.reason.lower() for r in plan2.blocked)

    good = _worker("w-z", workspace="/repo/alpha")
    plan3 = schedule_once(
        graph, ready, (_worker("w-a", workspace="/repo/alpha"), good), SchedulePolicy()
    )
    assert [(s.node_id, s.worker_id) for s in plan3.selected] == [("mut", "w-z")]


# --- GE-6 final round: human approval + stable typed block kinds (ADR §7) -----


def test_human_approval_pending_blocks_before_worker_selection() -> None:
    from a_conductor.graph.scheduler import BlockedReasonKind, NodeEligibility

    nodes = [_node("n")]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    plan = schedule_once(
        graph,
        ready,
        (_worker("w-0"),),
        SchedulePolicy(),
        eligibility={"n": NodeEligibility(human_approval_pending=True)},
    )
    assert plan.selected == ()
    entry = next(r for r in plan.blocked if r.node_id == "n")
    assert entry.kind is BlockedReasonKind.HUMAN_APPROVAL_WAIT
    assert "approval" in entry.reason.lower()


@pytest.mark.parametrize(
    "flag,expected_kind",
    [
        ("gate_refused", "GATE_NO_GO"),
        ("human_approval_pending", "HUMAN_APPROVAL_WAIT"),
        ("provider_unavailable", "PROVIDER_WAIT"),
        ("rate_limited", "RATE_LIMIT_WAIT"),
    ],
)
def test_eligibility_block_reasons_have_stable_typed_kinds(
    flag: str, expected_kind: str
) -> None:
    from a_conductor.graph.scheduler import BlockedReasonKind, NodeEligibility

    nodes = [_node("n")]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    plan = schedule_once(
        graph,
        ready,
        (_worker("w-0"),),
        SchedulePolicy(),
        eligibility={"n": NodeEligibility(**{flag: True})},
    )
    entry = next(r for r in plan.blocked if r.node_id == "n")
    assert entry.kind is BlockedReasonKind(expected_kind)
    assert entry.kind.value == expected_kind


def test_non_eligibility_blocks_have_stable_typed_kinds() -> None:
    from a_conductor.graph.scheduler import BlockedReasonKind

    # capacity: two nodes, one worker
    nodes = [_node("a"), _node("b")]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    plan = schedule_once(graph, ready, (_worker("w-0"),), SchedulePolicy())
    kinds = {r.node_id: r.kind for r in plan.blocked}
    assert kinds["b"] is BlockedReasonKind.CAPACITY

    # capability
    nodes = [_node("c", worker_req=("shell",))]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    plan = schedule_once(graph, ready, (_worker("w-x", caps=("documentation",)),), SchedulePolicy())
    assert plan.blocked[0].kind is BlockedReasonKind.CAPABILITY

    # identity (mutating without binding)
    nodes = [
        TaskNode(id="m", objective="o", worker_requirement=("shell",),
                 write_set=("x.py",))
    ]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    plan = schedule_once(graph, ready, (_worker("w-y", workspace="/repo"),), SchedulePolicy())
    assert plan.blocked[0].kind is BlockedReasonKind.IDENTITY

    # conflict (external running write set)
    nodes = [
        TaskNode(id="cf", objective="o", worker_requirement=("shell",),
                 write_set=("f.py",), model_requirement="ws:/repo")
    ]
    graph = build_graph(nodes, [])
    ready = compute_ready_set(graph, {})
    plan = schedule_once(
        graph, ready, (_worker("w-z", workspace="/repo"),), SchedulePolicy(),
        running_write_sets={"ext": ("f.py",)},
    )
    assert plan.blocked[0].kind is BlockedReasonKind.CONFLICT
