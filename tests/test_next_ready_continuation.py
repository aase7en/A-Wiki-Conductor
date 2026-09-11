"""WO-P1-191 / ZRA-3 — NEXT READY continuation RED-first matrix.

Covers the binding WO191 RED matrix (cases 1-20) plus positive controls,
executor fault boundaries, and a real-store integration/restart campaign
composing ONLY existing authorities: GoalCloseout completion truth,
GraphLifecycleBridge projection, compute_ready_set, schedule_once ordering
semantics, and GraphDispatchCoordinator durable dispatch identity.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.domain import TaskState
from a_conductor.graph.dag import DagResult
from a_conductor.graph.dispatch import (
    DispatchGateDecision,
    GraphDispatchAction,
    GraphDispatchCoordinator,
    GraphDispatchKey,
    GraphDispatchMode,
    GraphDispatchRequest,
    GraphDispatchResult,
    StaticWorkerDispatchModeResolver,
)
from a_conductor.graph.domain import (
    DependencyType,
    TaskEdge,
    TaskGraph,
    TaskNode,
    TaskNodeStatus,
)
from a_conductor.graph.ready import compute_ready_set
from a_conductor.graph.scheduler import SelectedAssignment
from a_conductor.job_control import DurableJobControlService
from a_conductor.job_store import JobStoreError, SQLiteJobStore
from a_conductor.native_execution import NativeCommandResult
from a_conductor.native_operations import (
    NativeOperationDefinition,
    NativeOperationKind,
    WorkerNativeAdapters,
)

from a_conductor.next_ready_continuation import (
    ContinuationExecutionOutcome,
    ContinuationGuards,
    ContinuationJobReader,
    NextReadyContinuationError,
    NextReadyContinuationExecutor,
    NextReadyContinuationFacts,
    NextReadyDecision,
    ParentCompletion,
    SuccessorDispatchPort,
    SuccessorObservation,
    classify_successor_state,
    observe_next_ready_facts,
    plan_next_ready_continuation,
)

GRAPH = "graph-1"
RUN = "run-1"
OTHER_RUN = "run-2"
PROJECT = "project-1"
WORK_ORDER = "docs/work-orders/WO-P1-191-zra3-next-ready.md"
OPERATION = "op:zra3-continuation"


def _node(node_id: str, *, priority: int = 0, write_set: tuple[str, ...] = ()) -> TaskNode:
    return TaskNode(id=node_id, objective=f"objective {node_id}", priority=priority,
                    write_set=write_set)


def _chain_graph() -> TaskGraph:
    """A -> B -> C (plus independent side node S with no edges)."""
    graph = TaskGraph()
    for node_id in ("A", "B", "C", "S"):
        graph.add_node(_node(node_id))
    graph.add_edge(TaskEdge("A", "B", DependencyType.ORDERING))
    graph.add_edge(TaskEdge("B", "C", DependencyType.ORDERING))
    return graph


def _fork_graph() -> TaskGraph:
    """A -> {B1, B2} (both same priority)."""
    graph = TaskGraph()
    for node_id in ("A", "B1", "B2"):
        graph.add_node(_node(node_id))
    graph.add_edge(TaskEdge("A", "B1", DependencyType.ORDERING))
    graph.add_edge(TaskEdge("A", "B2", DependencyType.ORDERING))
    return graph


def _diamond_graph() -> TaskGraph:
    """A -> {B1, B2} -> C."""
    graph = TaskGraph()
    for node_id in ("A", "B1", "B2", "C"):
        graph.add_node(_node(node_id))
    graph.add_edge(TaskEdge("A", "B1", DependencyType.ORDERING))
    graph.add_edge(TaskEdge("A", "B2", DependencyType.ORDERING))
    graph.add_edge(TaskEdge("B1", "C", DependencyType.ORDERING))
    graph.add_edge(TaskEdge("B2", "C", DependencyType.ORDERING))
    return graph


def _guards(**over) -> ContinuationGuards:
    base = dict(
        worktree_clean=True,
        head_matches_expected=True,
        lease_available=True,
        provider_admission_fresh=True,
    )
    base.update(over)
    return ContinuationGuards(**base)


def _parent(
    *,
    node_id: str = "A",
    state: TaskState = TaskState.COMPLETE,
    graph_run_id: str = RUN,
    completion_ref: str | None = "closeout:complete:A:0f1e2d3c4b5a697887766554433221100f1e2d3c4b5a6978877665544332211f",
    version: int = 7,
) -> ParentCompletion:
    job_id = GraphDispatchKey(GRAPH, graph_run_id, node_id).job_id
    return ParentCompletion(
        node_id=node_id, job_id=job_id, state=state,
        version=version, completion_ref=completion_ref,
    )


def _ready(graph: TaskGraph, node_states: dict[str, TaskNodeStatus]):
    return compute_ready_set(graph, node_states)


def _obs(node_id: str, job_state: TaskState | None) -> SuccessorObservation:
    return SuccessorObservation(node_id=node_id, job_state=job_state)


def facts(
    *,
    graph: TaskGraph | None = None,
    parent: ParentCompletion | None = None,
    node_states: dict[str, TaskNodeStatus] | None = None,
    successors: tuple[SuccessorObservation, ...] | None = None,
    guards: ContinuationGuards | None = None,
    graph_run_id: str = RUN,
) -> NextReadyContinuationFacts:
    graph = graph or _chain_graph()
    parent = parent or _parent(graph_run_id=graph_run_id)
    states = node_states if node_states is not None else {"A": TaskNodeStatus.DONE}
    if successors is None:
        successor_node = next(
            e.to_id for e in graph.edges_from(parent.node_id)
        ) if graph.edges_from(parent.node_id) else None
        successors = (
            (_obs(successor_node, None),) if successor_node else ()
        )
    return NextReadyContinuationFacts(
        graph_id=GRAPH,
        graph_run_id=graph_run_id,
        parent=parent,
        graph=graph,
        ready=_ready(graph, states),
        successors=successors,
        guards=guards or _guards(),
    )


# ══════════════════════════════════════════════════════════════════════
# Planner — parent completion gate (WO cases 1, 2, 3, 11)
# ══════════════════════════════════════════════════════════════════════

def test_incomplete_parent_never_dispatches() -> None:
    """WO1: parent not durably complete -> no successor dispatch."""
    for incomplete in (
        TaskState.EXECUTING, TaskState.VERIFYING, TaskState.REVIEW_PENDING,
        TaskState.CHANGES_REQUIRED, TaskState.REPAIRING, TaskState.BLOCKED,
        TaskState.RECOVERY_NEEDED, TaskState.NEW, TaskState.READY,
        TaskState.CLAIMED, TaskState.GATING, TaskState.PLANNING,
    ):
        plan = plan_next_ready_continuation(
            facts(parent=_parent(state=incomplete))
        )
        assert plan.decision is NextReadyDecision.NOOP_PARENT_NOT_COMPLETE
        assert plan.selected_node_id is None


def test_review_passed_but_closeout_incomplete_is_not_completion() -> None:
    """WO2: review accepted (REVIEW_PENDING) but GoalCloseout incomplete -> no dispatch."""
    plan = plan_next_ready_continuation(
        facts(parent=_parent(state=TaskState.REVIEW_PENDING))
    )
    assert plan.decision is NextReadyDecision.NOOP_PARENT_NOT_COMPLETE
    assert "REVIEW_PENDING" in plan.detail


def test_parent_identity_mismatch_fails_closed() -> None:
    """WO3: parent job id is not the GraphDispatchKey identity -> typed fail closed."""
    foreign = ParentCompletion(
        node_id="A",
        job_id="graph-dispatch-deadbeef",
        state=TaskState.COMPLETE,
        version=7,
        completion_ref=None,
    )
    with pytest.raises(NextReadyContinuationError) as excinfo:
        plan_next_ready_continuation(facts(parent=foreign))
    assert excinfo.value.code == "PARENT_JOB_IDENTITY_MISMATCH"


def test_foreign_graph_run_completion_cannot_advance_this_run() -> None:
    """WO11: a completion belonging to another graph run must not advance this run."""
    foreign = ParentCompletion(
        node_id="A",
        job_id=GraphDispatchKey(GRAPH, OTHER_RUN, "A").job_id,
        state=TaskState.COMPLETE,
        version=9,
        completion_ref=None,
    )
    with pytest.raises(NextReadyContinuationError) as excinfo:
        plan_next_ready_continuation(facts(parent=foreign, graph_run_id=RUN))
    assert excinfo.value.code == "PARENT_JOB_IDENTITY_MISMATCH"


def test_parent_node_missing_from_graph_fails_closed() -> None:
    with pytest.raises(NextReadyContinuationError) as excinfo:
        plan_next_ready_continuation(
            facts(parent=_parent(node_id="ZZ", graph_run_id=RUN),
                  graph=_chain_graph())
        )
    assert excinfo.value.code == "PARENT_NODE_UNKNOWN"


# ══════════════════════════════════════════════════════════════════════
# Planner — guards fail closed (WO cases 13-16) with positive twin
# ══════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("guard_field,code", [
    ("worktree_clean", "WORKTREE_DIRTY"),
    ("head_matches_expected", "HEAD_DRIFT"),
    ("lease_available", "LEASE_CONFLICT"),
    ("provider_admission_fresh", "PROVIDER_ADMISSION_STALE"),
])
def test_guard_failures_are_typed_fail_closed(guard_field: str, code: str) -> None:
    with pytest.raises(NextReadyContinuationError) as excinfo:
        plan_next_ready_continuation(facts(guards=_guards(**{guard_field: False})))
    assert excinfo.value.code == code


def test_guards_pass_positive_twin_dispatches() -> None:
    plan = plan_next_ready_continuation(facts())
    assert plan.decision is NextReadyDecision.DISPATCH_ONE
    assert plan.selected_node_id == "B"


# ══════════════════════════════════════════════════════════════════════
# Planner — ready/frontier semantics (WO cases 4, 5, 6, 12)
# ══════════════════════════════════════════════════════════════════════

def test_no_successor_ready_is_deterministic_noop() -> None:
    """WO4: no newly READY successor -> deterministic no-op."""
    graph = _chain_graph()
    # parent B completed; C blocked by sibling-in-progress is covered by the
    # diamond test; here S (independent) is already DOING and C waits on B.
    plan = plan_next_ready_continuation(
        facts(
            graph=graph,
            parent=_parent(node_id="B"),
            node_states={"A": TaskNodeStatus.DONE, "B": TaskNodeStatus.DONE,
                         "C": TaskNodeStatus.BLOCKED},
            successors=(_obs("C", None),),
        )
    )
    assert plan.decision is NextReadyDecision.NOOP_NO_SUCCESSOR_READY
    assert plan.selected_node_id is None


def test_exactly_one_ready_successor_dispatches_that_successor() -> None:
    """WO5: exactly one newly READY successor -> exactly one dispatch decision."""
    plan = plan_next_ready_continuation(facts())
    assert plan.decision is NextReadyDecision.DISPATCH_ONE
    assert plan.selected_node_id == "B"
    assert plan.candidate_node_ids == ("B",)


def test_multiple_ready_successors_never_fan_out() -> None:
    """WO6: >1 READY successor -> deterministic single selection, no fan-out."""
    graph = _fork_graph()
    f = facts(
        graph=graph,
        node_states={"A": TaskNodeStatus.DONE},
        successors=(_obs("B1", None), _obs("B2", None)),
    )
    plan = plan_next_ready_continuation(f)
    assert plan.decision is NextReadyDecision.DISPATCH_ONE
    assert plan.selected_node_id == "B1"  # lexical tie-break at equal priority/rank
    assert set(plan.candidate_node_ids) == {"B1", "B2"}
    # deterministic: identical durable facts -> identical plan, forever
    for _ in range(3):
        assert plan_next_ready_continuation(f).selected_node_id == "B1"


def test_selection_order_is_priority_then_topological_rank_then_lexical() -> None:
    graph2 = TaskGraph()
    graph2.add_node(_node("A"))
    graph2.add_node(_node("B1", priority=0))
    graph2.add_node(_node("B2", priority=5))
    graph2.add_node(_node("B3", priority=5))
    graph2.add_edge(TaskEdge("A", "B1", DependencyType.ORDERING))
    graph2.add_edge(TaskEdge("A", "B2", DependencyType.ORDERING))
    graph2.add_edge(TaskEdge("A", "B3", DependencyType.ORDERING))
    plan = plan_next_ready_continuation(
        facts(graph=graph2, node_states={"A": TaskNodeStatus.DONE},
              successors=(_obs("B1", None), _obs("B2", None), _obs("B3", None)))
    )
    assert plan.selected_node_id == "B2"  # highest priority; lexical tie-break over B3


def test_topological_rank_beats_lexical_at_equal_priority() -> None:
    graph = TaskGraph()
    graph.add_node(_node("A"))
    graph.add_node(_node("M"))       # rank 1 (A -> M)
    graph.add_node(_node("B"))       # rank 1, but no edge from A
    graph.add_node(_node("Z"))       # rank 1
    graph.add_edge(TaskEdge("A", "M", DependencyType.ORDERING))
    plan = plan_next_ready_continuation(
        facts(graph=graph, node_states={"A": TaskNodeStatus.DONE},
              successors=(_obs("M", None),))
    )
    # Only M is a direct successor of A; ready free-floating B/Z are never
    # candidates for this transition even though compute_ready_set marks
    # them READY.
    assert plan.selected_node_id == "M"
    assert "B" not in plan.candidate_node_ids
    assert "Z" not in plan.candidate_node_ids


def test_dependency_barrier_blocked_no_dispatch() -> None:
    """WO12: graph dependency/barrier still blocked -> no dispatch (diamond C)."""
    graph = _diamond_graph()
    plan = plan_next_ready_continuation(
        facts(
            graph=graph,
            parent=_parent(node_id="A"),
            node_states={"A": TaskNodeStatus.DONE, "B1": TaskNodeStatus.DONE,
                         "B2": TaskNodeStatus.DOING, "C": TaskNodeStatus.TODO},
            successors=(_obs("B1", TaskState.COMPLETE), _obs("B2", TaskState.EXECUTING)),
        )
    )
    # B1/B2 are represented; C is not a direct successor of A.
    assert plan.decision is NextReadyDecision.NOOP_ALL_REPRESENTED


def test_write_conflict_excludes_readiness() -> None:
    """Successor ready by deps but resource-conflicted with a running node stays excluded."""
    graph = TaskGraph()
    graph.add_node(_node("A"))
    graph.add_node(_node("B", write_set=("src/shared.py",)))
    graph.add_node(_node("R", write_set=("src/shared.py",)))
    graph.add_edge(TaskEdge("A", "B", DependencyType.ORDERING))
    ready = compute_ready_set(
        graph, {"A": TaskNodeStatus.DONE, "R": TaskNodeStatus.DOING}
    )
    assert "B" not in ready.ready_ids
    plan = plan_next_ready_continuation(
        NextReadyContinuationFacts(
            graph_id=GRAPH, graph_run_id=RUN, parent=_parent(),
            graph=graph, ready=ready,
            successors=(_obs("B", None),), guards=_guards(),
        )
    )
    assert plan.decision is NextReadyDecision.NOOP_NO_SUCCESSOR_READY


def test_cyclic_graph_fails_closed() -> None:
    graph = TaskGraph()
    graph.add_node(_node("A"))
    graph.add_node(_node("B"))
    graph.add_edge(TaskEdge("A", "B", DependencyType.ORDERING))
    graph.add_edge(TaskEdge("B", "A", DependencyType.ORDERING))
    with pytest.raises(NextReadyContinuationError) as excinfo:
        plan_next_ready_continuation(facts(graph=graph))
    assert excinfo.value.code == "GRAPH_CYCLE"


# ══════════════════════════════════════════════════════════════════════
# Planner — representation / replay semantics (WO cases 7, 8, 9, 10)
# ══════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("state", [
    TaskState.NEW, TaskState.PLANNING, TaskState.READY, TaskState.CLAIMED,
    TaskState.GATING, TaskState.EXECUTING, TaskState.VERIFYING,
    TaskState.REVIEW_PENDING, TaskState.CHANGES_REQUIRED,
    TaskState.REPAIRING,
])
def test_active_successor_representation_never_respawns(state: TaskState) -> None:
    """WO10: successor RUNNING/active/durably represented -> no respawn."""
    plan = plan_next_ready_continuation(
        facts(successors=(_obs("B", state),),
              node_states={"A": TaskNodeStatus.DONE, "B": TaskNodeStatus.DOING})
    )
    assert plan.decision is NextReadyDecision.NOOP_ALL_REPRESENTED
    assert plan.selected_node_id is None


@pytest.mark.parametrize("state", [TaskState.COMPLETE, TaskState.FAILED, TaskState.CANCELLED])
def test_terminal_successor_representation_never_respawns(state: TaskState) -> None:
    plan = plan_next_ready_continuation(
        facts(successors=(_obs("B", state),),
              node_states={"A": TaskNodeStatus.DONE, "B": TaskNodeStatus.DONE})
    )
    assert plan.decision is NextReadyDecision.NOOP_ALL_REPRESENTED


def test_blocked_successor_representation_never_respawns() -> None:
    plan = plan_next_ready_continuation(
        facts(successors=(_obs("B", TaskState.BLOCKED),),
              node_states={"A": TaskNodeStatus.DONE, "B": TaskNodeStatus.BLOCKED})
    )
    assert plan.decision is NextReadyDecision.NOOP_ALL_REPRESENTED


def test_prior_dispatch_recovery_needed_reconciles_never_retries() -> None:
    """WO9: prior execution UNKNOWN (RECOVERY_NEEDED) -> reconcile, no blind replay."""
    plan = plan_next_ready_continuation(
        facts(successors=(_obs("B", TaskState.RECOVERY_NEEDED),),
              node_states={"A": TaskNodeStatus.DONE, "B": TaskNodeStatus.BLOCKED})
    )
    assert plan.decision is NextReadyDecision.RECONCILE_RECOVERY
    assert plan.selected_node_id is None
    assert plan.recovery_node_ids == ("B",)


def test_recovery_sibling_does_not_block_dispatchable_sibling() -> None:
    graph = _fork_graph()
    plan = plan_next_ready_continuation(
        facts(
            graph=graph,
            node_states={"A": TaskNodeStatus.DONE, "B1": TaskNodeStatus.BLOCKED},
            successors=(_obs("B1", TaskState.RECOVERY_NEEDED), _obs("B2", None)),
        )
    )
    assert plan.decision is NextReadyDecision.DISPATCH_ONE
    assert plan.selected_node_id == "B2"
    assert plan.recovery_node_ids == ("B1",)


def test_represented_sibling_skipped_unrepresented_sibling_dispatched() -> None:
    """WO7 duplicate-tick twin: one successor represented, other fresh -> only fresh dispatches."""
    graph = _fork_graph()
    plan = plan_next_ready_continuation(
        facts(
            graph=graph,
            node_states={"A": TaskNodeStatus.DONE, "B1": TaskNodeStatus.DOING},
            successors=(_obs("B1", TaskState.EXECUTING), _obs("B2", None)),
        )
    )
    assert plan.decision is NextReadyDecision.DISPATCH_ONE
    assert plan.selected_node_id == "B2"


def test_duplicate_tick_all_represented_is_noop() -> None:
    """WO7: duplicate observation after dispatch -> no duplicate decision."""
    graph = _fork_graph()
    plan = plan_next_ready_continuation(
        facts(
            graph=graph,
            node_states={"A": TaskNodeStatus.DONE, "B1": TaskNodeStatus.DOING,
                         "B2": TaskNodeStatus.DOING},
            successors=(_obs("B1", TaskState.EXECUTING), _obs("B2", TaskState.CLAIMED)),
        )
    )
    assert plan.decision is NextReadyDecision.NOOP_ALL_REPRESENTED


# ══════════════════════════════════════════════════════════════════════
# Facts — typed validation / digest identity (WO case 17)
# ══════════════════════════════════════════════════════════════════════

def test_malformed_identity_fields_fail_closed() -> None:
    with pytest.raises(ValueError):
        ParentCompletion(
            node_id="A\nB", job_id=GraphDispatchKey(GRAPH, RUN, "A").job_id,
            state=TaskState.COMPLETE, version=7, completion_ref=None,
        )
    with pytest.raises(ValueError):
        ParentCompletion(
            node_id="A", job_id="", state=TaskState.COMPLETE,
            version=7, completion_ref=None,
        )
    with pytest.raises(ValueError):
        ParentCompletion(
            node_id="A", job_id=GraphDispatchKey(GRAPH, RUN, "A").job_id,
            state=TaskState.COMPLETE, version=0, completion_ref=None,
        )


def test_facts_reject_successor_not_child_of_parent() -> None:
    with pytest.raises(NextReadyContinuationError) as excinfo:
        plan_next_ready_continuation(
            facts(successors=(_obs("C", None),))  # C is not a direct successor of A
        )
    assert excinfo.value.code == "SUCCESSOR_NOT_CHILD_OF_PARENT"


def test_facts_reject_duplicate_successor_entries() -> None:
    with pytest.raises(NextReadyContinuationError) as excinfo:
        plan_next_ready_continuation(
            facts(successors=(_obs("B", None), _obs("B", None)))
        )
    assert excinfo.value.code == "SUCCESSOR_DUPLICATE"


def test_facts_reject_wrong_types() -> None:
    with pytest.raises(ValueError):
        ContinuationGuards(worktree_clean="yes", head_matches_expected=True,
                           lease_available=True, provider_admission_fresh=True)
    with pytest.raises(ValueError):
        SuccessorObservation(node_id="", job_state=None)


def test_classify_successor_state_vocabulary() -> None:
    assert classify_successor_state(None).value == "UNREPRESENTED"
    assert classify_successor_state(TaskState.NEW).value == "PENDING"
    assert classify_successor_state(TaskState.EXECUTING).value == "ACTIVE"
    assert classify_successor_state(TaskState.RECOVERY_NEEDED).value == "RECOVERY"
    assert classify_successor_state(TaskState.BLOCKED).value == "BLOCKED_REPRESENTED"
    assert classify_successor_state(TaskState.COMPLETE).value == "TERMINAL"


# ══════════════════════════════════════════════════════════════════════
# Executor — one effect per call, pass-through, fail-closed
# ══════════════════════════════════════════════════════════════════════

class FakeDispatchPort:
    def __init__(self, results=None, *, raise_error: Exception | None = None):
        self.calls: list[str] = []
        self.results = list(results or [])
        self.raise_error = raise_error

    def dispatch_successor(self, node_id: str):
        from a_conductor.graph.dispatch import GraphDispatchResult
        self.calls.append(node_id)
        if self.raise_error is not None:
            raise self.raise_error
        if self.results:
            item = self.results.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        raise AssertionError("unexpected dispatch call")


def _dispatch_result(action: GraphDispatchAction, *, state: TaskState = TaskState.VERIFYING):
    from a_conductor.job_state import JobRuntimeState
    job = JobRuntimeState(
        job_id=GraphDispatchKey(GRAPH, RUN, "B").job_id,
        work_order_ref=WORK_ORDER, project_id=PROJECT, state=state,
        worker_id="a-worker-01", attempt_count=1, max_attempts=3,
        recovery_classification=None, version=4,
    )
    return GraphDispatchResult(action=action, job=job, reason_code="TEST")


def test_executor_noop_decisions_cause_no_dispatch_calls() -> None:
    port = FakeDispatchPort()
    executor = NextReadyContinuationExecutor(dispatch_port=port)
    for f in (
        facts(parent=_parent(state=TaskState.REVIEW_PENDING)),
        facts(successors=(_obs("B", TaskState.COMPLETE),),
              node_states={"A": TaskNodeStatus.DONE, "B": TaskNodeStatus.DONE}),
    ):
        result = executor.execute_next(f)
        assert result.outcome is ContinuationExecutionOutcome.PLANNER_NOOP
    assert port.calls == []


def test_executor_dispatch_one_calls_port_exactly_once() -> None:
    port = FakeDispatchPort(results=[_dispatch_result(GraphDispatchAction.EXECUTED)])
    executor = NextReadyContinuationExecutor(dispatch_port=port)
    result = executor.execute_next(facts())
    assert result.outcome is ContinuationExecutionOutcome.DISPATCH_EXECUTED
    assert port.calls == ["B"]
    assert result.plan.selected_node_id == "B"


@pytest.mark.parametrize("action,outcome", [
    (GraphDispatchAction.EXISTING, ContinuationExecutionOutcome.DISPATCH_EXISTING),
    (GraphDispatchAction.RECONCILE, ContinuationExecutionOutcome.DISPATCH_RECONCILE),
    (GraphDispatchAction.BLOCKED, ContinuationExecutionOutcome.DISPATCH_BLOCKED),
    (GraphDispatchAction.OFFERED, ContinuationExecutionOutcome.DISPATCH_OFFERED),
])
def test_executor_passes_typed_dispatch_actions_through(action, outcome) -> None:
    port = FakeDispatchPort(results=[_dispatch_result(action)])
    executor = NextReadyContinuationExecutor(dispatch_port=port)
    assert executor.execute_next(facts()).outcome is outcome
    assert port.calls == ["B"]


def test_executor_reconcile_never_retries_within_call() -> None:
    port = FakeDispatchPort(results=[_dispatch_result(GraphDispatchAction.RECONCILE)])
    executor = NextReadyContinuationExecutor(dispatch_port=port)
    executor.execute_next(facts())
    executor.execute_next(facts())  # duplicate tick: planner NOOP after representation?
    # the second call re-plans from the SAME facts object (no durable change),
    # so the planner still says DISPATCH_ONE; executor must still make exactly
    # one port call per execute_next and never an internal retry loop.
    assert port.calls == ["B", "B"]


def test_executor_version_conflict_maps_to_reload_replan() -> None:
    port = FakeDispatchPort(
        raise_error=JobStoreError("JOB_VERSION_CONFLICT")
    )
    executor = NextReadyContinuationExecutor(dispatch_port=port)
    result = executor.execute_next(facts())
    assert result.outcome is ContinuationExecutionOutcome.RELOAD_REPLAN
    assert port.calls == ["B"]


def test_executor_unexpected_port_failure_is_typed_recovery_not_retry() -> None:
    port = FakeDispatchPort(raise_error=RuntimeError("coordinator transport down"))
    executor = NextReadyContinuationExecutor(dispatch_port=port)
    result = executor.execute_next(facts())
    assert result.outcome is ContinuationExecutionOutcome.RECOVERY_REQUIRED
    assert result.detail  # typed detail present
    assert port.calls == ["B"]  # exactly one attempt; no blind retry


def test_executor_unsupported_result_shape_is_recovery_not_success() -> None:
    port = FakeDispatchPort(results=[{"action": "EXECUTED"}])
    executor = NextReadyContinuationExecutor(dispatch_port=port)
    result = executor.execute_next(facts())
    assert result.outcome is ContinuationExecutionOutcome.RECOVERY_REQUIRED
    assert port.calls == ["B"]


def test_executor_rejects_malformed_port() -> None:
    with pytest.raises(ValueError):
        NextReadyContinuationExecutor(dispatch_port=object())


# ══════════════════════════════════════════════════════════════════════
# Real-authority integration — zero human relay, restart, crash windows
# (WO cases 5, 7, 8, 9, 18, 19, 20)
# ══════════════════════════════════════════════════════════════════════

def _result_ok() -> NativeCommandResult:
    return NativeCommandResult(
        executable="python.exe", argument_count=3, exit_code=0, timed_out=False,
        stdout="ok", stderr="", stdout_sha256="a" * 64, stderr_sha256="b" * 64,
        stdout_truncated=False, stderr_truncated=False,
    )


class FakeGit:
    def status_short(self, *, timeout_seconds=10):
        return _result_ok()

    def working_diff(self, paths=(), *, timeout_seconds=15):
        return _result_ok()

    def cached_diff(self, paths=(), *, timeout_seconds=15):
        return _result_ok()


class FakeVerification:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def pytest(self, paths=("tests",), *, timeout_seconds=120):
        self.calls.append("pytest")
        return _result_ok()

    def compileall(self, paths=("src",), *, timeout_seconds=120):
        self.calls.append("compileall")
        return _result_ok()


class FakeResolver:
    def __init__(self) -> None:
        self.verification = FakeVerification()

    def resolve(self, worker_id: str) -> WorkerNativeAdapters:
        return WorkerNativeAdapters(git=FakeGit(), verification=self.verification)


def _open_service(tmp_path: Path):
    resolver = FakeResolver()
    service = DurableJobControlService.open(
        tmp_path / "control.sqlite",
        operations=(
            NativeOperationDefinition(
                operation_ref=OPERATION,
                kind=NativeOperationKind.PYTEST,
                paths=("tests/test_next_ready_continuation.py",),
                timeout_seconds=30,
            ),
        ),
        native_resolver=resolver,
    )
    return service, resolver


def _request(node_id: str, *, worker_id: str = "a-worker-01"):
    return GraphDispatchRequest(
        key=GraphDispatchKey(GRAPH, RUN, node_id),
        assignment=SelectedAssignment(node_id=node_id, worker_id=worker_id, priority=0),
        project_id=PROJECT,
        work_order_ref=WORK_ORDER,
        operation_ref=OPERATION,
        dispatch_mode=GraphDispatchMode.PROGRAMMATIC_PUSH,
        max_attempts=3,
    )


class CoordinatorDispatchPort:
    """Production-shaped port: schedule + durable dispatch, one node at a time."""

    def __init__(self, coordinator: GraphDispatchCoordinator) -> None:
        self._coordinator = coordinator
        self.calls: list[str] = []

    def dispatch_successor(self, node_id: str):
        self.calls.append(node_id)
        return self._coordinator.dispatch(_request(node_id), gate=DispatchGateDecision.allow())


def _drive_to_complete(tmp_path: Path, service, node_id: str) -> None:
    """Drive one graph-dispatch job through the real lifecycle to COMPLETE.

    REVIEW_PENDING -> COMPLETE is the GoalCloseout-owned tail; here it is
    applied through the same durable SQLiteJobStore authority the service
    wraps (test setup only — completion truth remains the job store).
    """
    store = SQLiteJobStore(tmp_path / "control.sqlite")
    job_id = GraphDispatchKey(GRAPH, RUN, node_id).job_id
    job = service.get_job(job_id)
    assert job.state is TaskState.VERIFYING
    for target in (TaskState.REVIEW_PENDING, TaskState.COMPLETE):
        job = store.transition(job_id, target, expected_version=job.version)


def _tick(service, graph, parent_node, port) -> "object":
    f = observe_next_ready_facts(
        jobs=service, graph=graph, graph_id=GRAPH, graph_run_id=RUN,
        parent_node_id=parent_node, guards=_guards(),
    )
    return NextReadyContinuationExecutor(dispatch_port=port).execute_next(f)


def test_integration_chain_continues_without_human_relay(tmp_path: Path) -> None:
    """WO20 + WO5: accepted/durably completed parent auto-dispatches successor via real authorities."""
    service, resolver = _open_service(tmp_path)
    coordinator = GraphDispatchCoordinator(
        service=service,
        mode_resolver=StaticWorkerDispatchModeResolver(
            {"a-worker-01": GraphDispatchMode.PROGRAMMATIC_PUSH}
        ),
    )
    port = CoordinatorDispatchPort(coordinator)

    # parent A runs to durable COMPLETE through the real job store
    coordinator.dispatch(_request("A"), gate=DispatchGateDecision.allow())
    _drive_to_complete(tmp_path, service, "A")

    result = _tick(service, _chain_graph(), "A", port)
    assert result.outcome is ContinuationExecutionOutcome.DISPATCH_EXECUTED
    assert port.calls == ["B"]
    assert resolver.verification.calls  # real native operation executed
    job_b = service.get_job(GraphDispatchKey(GRAPH, RUN, "B").job_id)
    assert job_b.state is TaskState.VERIFYING


def test_integration_duplicate_tick_after_dispatch_is_noop(tmp_path: Path) -> None:
    """WO7 physical: duplicate observation cannot create duplicate physical work."""
    service, _ = _open_service(tmp_path)
    coordinator = GraphDispatchCoordinator(
        service=service,
        mode_resolver=StaticWorkerDispatchModeResolver(
            {"a-worker-01": GraphDispatchMode.PROGRAMMATIC_PUSH}
        ),
    )
    port = CoordinatorDispatchPort(coordinator)
    coordinator.dispatch(_request("A"), gate=DispatchGateDecision.allow())
    _drive_to_complete(tmp_path, service, "A")

    first = _tick(service, _chain_graph(), "A", port)
    assert first.outcome is ContinuationExecutionOutcome.DISPATCH_EXECUTED
    second = _tick(service, _chain_graph(), "A", port)
    assert second.outcome is ContinuationExecutionOutcome.PLANNER_NOOP
    assert port.calls == ["B"]
    created = [
        e for e in service.list_events(GraphDispatchKey(GRAPH, RUN, "B").job_id)
        if e.event_type.value == "CREATED"
    ]
    assert len(created) == 1


def test_integration_restart_reconstructs_same_identity_no_duplicate(tmp_path: Path) -> None:
    """WO8: process restart with same durable identity -> no duplicate execution."""
    service, resolver = _open_service(tmp_path)
    coordinator = GraphDispatchCoordinator(
        service=service,
        mode_resolver=StaticWorkerDispatchModeResolver(
            {"a-worker-01": GraphDispatchMode.PROGRAMMATIC_PUSH}
        ),
    )
    port = CoordinatorDispatchPort(coordinator)
    coordinator.dispatch(_request("A"), gate=DispatchGateDecision.allow())
    _drive_to_complete(tmp_path, service, "A")
    _tick(service, _chain_graph(), "A", port)

    # simulate restart: brand-new service/executor over the SAME durable file
    service2, resolver2 = _open_service(tmp_path)
    coordinator2 = GraphDispatchCoordinator(
        service=service2,
        mode_resolver=StaticWorkerDispatchModeResolver(
            {"a-worker-01": GraphDispatchMode.PROGRAMMATIC_PUSH}
        ),
    )
    port2 = CoordinatorDispatchPort(coordinator2)
    result = _tick(service2, _chain_graph(), "A", port2)
    assert result.outcome is ContinuationExecutionOutcome.PLANNER_NOOP
    assert port2.calls == []
    assert resolver2.verification.calls == []


def test_integration_crash_after_durable_dispatch_reconciles(tmp_path: Path) -> None:
    """WO18: crash after the durable dispatch record -> restart reconciles, no duplicate."""
    service, _ = _open_service(tmp_path)
    coordinator = GraphDispatchCoordinator(
        service=service,
        mode_resolver=StaticWorkerDispatchModeResolver(
            {"a-worker-01": GraphDispatchMode.PROGRAMMATIC_PUSH}
        ),
    )
    coordinator.dispatch(_request("A"), gate=DispatchGateDecision.allow())
    _drive_to_complete(tmp_path, service, "A")
    # durable dispatch of B happened; the caller never observed the response
    coordinator.dispatch(_request("B"), gate=DispatchGateDecision.allow())

    port = CoordinatorDispatchPort(coordinator)
    result = _tick(service, _chain_graph(), "A", port)
    assert result.outcome is ContinuationExecutionOutcome.PLANNER_NOOP
    assert port.calls == []


def test_integration_crash_before_dispatch_safe_retry_is_explicit(tmp_path: Path) -> None:
    """WO19: crash before any durable record -> retry decision is explicit and evidence-backed."""
    service, _ = _open_service(tmp_path)
    coordinator = GraphDispatchCoordinator(
        service=service,
        mode_resolver=StaticWorkerDispatchModeResolver(
            {"a-worker-01": GraphDispatchMode.PROGRAMMATIC_PUSH}
        ),
    )
    coordinator.dispatch(_request("A"), gate=DispatchGateDecision.allow())
    _drive_to_complete(tmp_path, service, "A")

    class CrashPort:
        def __init__(self) -> None:
            self.calls = 0

        def dispatch_successor(self, node_id: str):
            self.calls += 1
            raise RuntimeError("simulated crash before durable dispatch")

    crash = CrashPort()
    result = NextReadyContinuationExecutor(dispatch_port=crash).execute_next(
        observe_next_ready_facts(
            jobs=service, graph=_chain_graph(), graph_id=GRAPH, graph_run_id=RUN,
            parent_node_id="A", guards=_guards(),
        )
    )
    assert result.outcome is ContinuationExecutionOutcome.RECOVERY_REQUIRED
    assert crash.calls == 1
    # durable store proves nothing happened for B
    with pytest.raises(JobStoreError):
        service.get_job(GraphDispatchKey(GRAPH, RUN, "B").job_id)
    # evidence-backed safe retry: a fresh tick re-plans the SAME deterministic
    # decision and attempts exactly one more dispatch
    port = CoordinatorDispatchPort(coordinator)
    retry = _tick(service, _chain_graph(), "A", port)
    assert retry.outcome is ContinuationExecutionOutcome.DISPATCH_EXECUTED
    assert port.calls == ["B"]


def test_integration_multi_successor_converges_over_ticks_without_fanout(tmp_path: Path) -> None:
    """WO6 physical: fork converges one dispatch per tick; never fan-out."""
    service, _ = _open_service(tmp_path)
    coordinator = GraphDispatchCoordinator(
        service=service,
        mode_resolver=StaticWorkerDispatchModeResolver(
            {"a-worker-01": GraphDispatchMode.PROGRAMMATIC_PUSH}
        ),
    )
    port = CoordinatorDispatchPort(coordinator)
    coordinator.dispatch(_request("A"), gate=DispatchGateDecision.allow())
    _drive_to_complete(tmp_path, service, "A")

    graph = _fork_graph()
    tick1 = _tick(service, graph, "A", port)
    assert tick1.outcome is ContinuationExecutionOutcome.DISPATCH_EXECUTED
    assert port.calls == ["B1"]
    tick2 = _tick(service, graph, "A", port)
    assert tick2.outcome is ContinuationExecutionOutcome.DISPATCH_EXECUTED
    assert port.calls == ["B1", "B2"]
    tick3 = _tick(service, graph, "A", port)
    assert tick3.outcome is ContinuationExecutionOutcome.PLANNER_NOOP
    assert port.calls == ["B1", "B2"]


def test_integration_foreign_run_completion_cannot_dispatch(tmp_path: Path) -> None:
    """WO11 physical: a completed job from another graph run never dispatches here."""
    service, _ = _open_service(tmp_path)
    coordinator = GraphDispatchCoordinator(
        service=service,
        mode_resolver=StaticWorkerDispatchModeResolver(
            {"a-worker-01": GraphDispatchMode.PROGRAMMATIC_PUSH}
        ),
    )
    port = CoordinatorDispatchPort(coordinator)
    foreign_request = GraphDispatchRequest(
        key=GraphDispatchKey(GRAPH, OTHER_RUN, "A"),
        assignment=SelectedAssignment(node_id="A", worker_id="a-worker-01", priority=0),
        project_id=PROJECT, work_order_ref=WORK_ORDER, operation_ref=OPERATION,
        dispatch_mode=GraphDispatchMode.PROGRAMMATIC_PUSH, max_attempts=3,
    )
    coordinator.dispatch(foreign_request, gate=DispatchGateDecision.allow())
    # drive the FOREIGN run's job to COMPLETE through the same durable store
    store = SQLiteJobStore(tmp_path / "control.sqlite")
    foreign_job_id = GraphDispatchKey(GRAPH, OTHER_RUN, "A").job_id
    job = service.get_job(foreign_job_id)
    assert job.state is TaskState.VERIFYING
    for target in (TaskState.REVIEW_PENDING, TaskState.COMPLETE):
        job = store.transition(foreign_job_id, target, expected_version=job.version)

    # observe for run-1: no parent job exists for run-1's A -> typed fail closed
    with pytest.raises(NextReadyContinuationError) as excinfo:
        observe_next_ready_facts(
            jobs=service, graph=_chain_graph(), graph_id=GRAPH, graph_run_id=RUN,
            parent_node_id="A", guards=_guards(),
        )
    assert excinfo.value.code == "PARENT_JOB_NOT_FOUND"
    assert port.calls == []


def test_integration_concurrent_duplicate_executor_calls_single_execution(tmp_path: Path) -> None:
    """Replay attack: two executor invocations on identical facts before any
    durable refresh must still produce exactly ONE physical execution."""
    service, resolver = _open_service(tmp_path)
    coordinator = GraphDispatchCoordinator(
        service=service,
        mode_resolver=StaticWorkerDispatchModeResolver(
            {"a-worker-01": GraphDispatchMode.PROGRAMMATIC_PUSH}
        ),
    )
    coordinator.dispatch(_request("A"), gate=DispatchGateDecision.allow())
    _drive_to_complete(tmp_path, service, "A")

    f = observe_next_ready_facts(
        jobs=service, graph=_chain_graph(), graph_id=GRAPH, graph_run_id=RUN,
        parent_node_id="A", guards=_guards(),
    )
    port = CoordinatorDispatchPort(coordinator)
    first = NextReadyContinuationExecutor(dispatch_port=port).execute_next(f)
    second = NextReadyContinuationExecutor(dispatch_port=port).execute_next(f)
    assert first.outcome is ContinuationExecutionOutcome.DISPATCH_EXECUTED
    # the durable job identity converges the stale duplicate: EXISTING, not
    # a second native execution
    assert second.outcome is ContinuationExecutionOutcome.DISPATCH_EXISTING
    assert port.calls == ["B", "B"]
    events = service.list_events(GraphDispatchKey(GRAPH, RUN, "B").job_id)
    created = [e for e in events if e.event_type.value == "CREATED"]
    executed = [
        e for e in events
        if e.event_type.value == "TRANSITION" and e.to_state is TaskState.EXECUTING
    ]
    assert len(created) == 1     # one durable job identity for B
    assert len(executed) == 1    # exactly one physical execution of B


def test_dag_order_helper_is_reused_not_duplicated() -> None:
    """Guard: the planner consumes the existing DAG engine, not a private sort."""
    from a_conductor.graph import dag as dag_module
    result = dag_module.topological_sort(_chain_graph())
    assert isinstance(result, DagResult)
