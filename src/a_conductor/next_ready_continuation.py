"""WO-P1-191 / ZRA-3 — automatic NEXT READY continuation (Phase A).

A THIN continuation decision seam composing ONLY existing authorities:

- ``GoalCloseout`` output: durable ``TaskState.COMPLETE`` on the parent job
  is the single completion truth (reviewer prose is never an input here);
- ``GraphLifecycleBridge`` projection semantics: a durable job per
  ``GraphDispatchKey`` IS the "already represented" record for a successor;
- ``graph.ready.compute_ready_set``: dependency/barrier/resource readiness;
- ``graph.dag.topological_sort`` + ``TaskNode.priority``: the scheduler's
  documented D6-CAP ordering (priority -> topo rank -> lexical id) used
  ONLY to pick at most one successor per tick — worker assignment stays
  with ``graph.scheduler.schedule_once`` at dispatch time;
- ``GraphDispatchCoordinator``: the one physical dispatch effect, whose
  durable job journal provides idempotency/restart semantics.

This module owns NO scheduler, store, lease, provider, retry, review, or
continuation-record authority. ``plan_next_ready_continuation`` is PURE:
no filesystem, Git, GitHub, subprocess, clock, network, or database
access. All side effects live in :class:`NextReadyContinuationExecutor`
over one injected dispatch port, executing at most ONE dispatch attempt
per call. UNKNOWN/ambiguous outcomes are RECONCILE/RECOVERY, never blind
replay. Fan-out to multiple successors in one tick is structurally
impossible (ZRA-4 / Issue #216 owns bounded parallel continuation).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .domain import TaskState
from .graph.dag import topological_sort
from .graph.dispatch import (
    GraphDispatchAction,
    GraphDispatchKey,
    GraphDispatchResult,
)
from .graph.domain import TaskGraph, TaskNodeStatus
from .graph.lifecycle_bridge import GraphJobStateReader, project_job_state
from .graph.ready import ReadySetResult, compute_ready_set
from .job_state import JobRuntimeState
from .job_store import JobStoreError

_IDENTITY_RE = re.compile(r"^[A-Za-z0-9._:/-]{1,256}$")


class NextReadyContinuationError(RuntimeError):
    """Stable typed failure; never echoes arbitrary input text."""

    def __init__(self, code: str) -> None:
        if not isinstance(code, str) or not code or len(code) > 128:
            raise ValueError("code is invalid")
        self.code = code
        super().__init__(code)


def _identity(value: object, field: str) -> str:
    if not isinstance(value, str) or not _IDENTITY_RE.fullmatch(value):
        raise ValueError(f"{field} is invalid")
    return value


# ---------------- immutable facts ----------------


@dataclass(frozen=True, slots=True)
class ContinuationGuards:
    """Boolean projections of the existing mutation/lease/provider gates.

    Each field is produced by its owning authority at the composition seam;
    this dataclass only transports their verdicts. Any ``False`` fails the
    continuation closed before a dispatch decision can be produced.
    """

    worktree_clean: bool
    head_matches_expected: bool
    lease_available: bool
    provider_admission_fresh: bool

    def __post_init__(self) -> None:
        for name in (
            "worktree_clean", "head_matches_expected",
            "lease_available", "provider_admission_fresh",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be bool")


@dataclass(frozen=True, slots=True)
class ParentCompletion:
    """Observed durable completion of the parent node's graph-dispatch job."""

    node_id: str
    job_id: str
    state: TaskState
    version: int
    completion_ref: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_id", _identity(self.node_id, "node_id"))
        object.__setattr__(self, "job_id", _identity(self.job_id, "job_id"))
        if not isinstance(self.state, TaskState):
            raise ValueError("state must be a TaskState")
        if (
            not isinstance(self.version, int)
            or isinstance(self.version, bool)
            or self.version < 1
        ):
            raise ValueError("version is invalid")
        if self.completion_ref is not None:
            object.__setattr__(
                self, "completion_ref", _identity(self.completion_ref, "completion_ref")
            )


@dataclass(frozen=True, slots=True)
class SuccessorObservation:
    """Durable representation of one direct successor (None = no job)."""

    node_id: str
    job_state: TaskState | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_id", _identity(self.node_id, "node_id"))
        if self.job_state is not None and not isinstance(self.job_state, TaskState):
            raise ValueError("job_state must be a TaskState or None")


@dataclass(frozen=True, slots=True)
class NextReadyContinuationFacts:
    """One continuation tick's immutable durable observations."""

    graph_id: str
    graph_run_id: str
    parent: ParentCompletion
    graph: TaskGraph
    ready: ReadySetResult
    successors: tuple[SuccessorObservation, ...]
    guards: ContinuationGuards

    def __post_init__(self) -> None:
        object.__setattr__(self, "graph_id", _identity(self.graph_id, "graph_id"))
        object.__setattr__(
            self, "graph_run_id", _identity(self.graph_run_id, "graph_run_id")
        )
        if not isinstance(self.parent, ParentCompletion):
            raise ValueError("parent must be ParentCompletion")
        if not isinstance(self.graph, TaskGraph):
            raise ValueError("graph must be TaskGraph")
        if not isinstance(self.ready, ReadySetResult):
            raise ValueError("ready must be ReadySetResult")
        if not isinstance(self.guards, ContinuationGuards):
            raise ValueError("guards must be ContinuationGuards")
        successors = tuple(self.successors)
        for observation in successors:
            if not isinstance(observation, SuccessorObservation):
                raise ValueError("successors must contain SuccessorObservation")
        object.__setattr__(self, "successors", successors)


# ---------------- successor representation vocabulary ----------------


class RepresentationKind(str, Enum):
    """Classification of a successor's durable representation.

    Output vocabulary only — the durable job state machine remains the
    authority; this classification decides "may this successor be
    dispatched?" and nothing else.
    """

    UNREPRESENTED = "UNREPRESENTED"
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    RECOVERY = "RECOVERY"
    BLOCKED_REPRESENTED = "BLOCKED_REPRESENTED"
    TERMINAL = "TERMINAL"


_REPRESENTATION_BY_STATE: dict[TaskState, RepresentationKind] = {
    TaskState.NEW: RepresentationKind.PENDING,
    TaskState.PLANNING: RepresentationKind.PENDING,
    TaskState.READY: RepresentationKind.PENDING,
    TaskState.CLAIMED: RepresentationKind.ACTIVE,
    TaskState.GATING: RepresentationKind.ACTIVE,
    TaskState.EXECUTING: RepresentationKind.ACTIVE,
    TaskState.VERIFYING: RepresentationKind.ACTIVE,
    TaskState.REVIEW_PENDING: RepresentationKind.ACTIVE,
    TaskState.CHANGES_REQUIRED: RepresentationKind.ACTIVE,
    TaskState.REPAIRING: RepresentationKind.ACTIVE,
    TaskState.BLOCKED: RepresentationKind.BLOCKED_REPRESENTED,
    TaskState.RECOVERY_NEEDED: RepresentationKind.RECOVERY,
    TaskState.COMPLETE: RepresentationKind.TERMINAL,
    TaskState.FAILED: RepresentationKind.TERMINAL,
    TaskState.CANCELLED: RepresentationKind.TERMINAL,
}


def classify_successor_state(job_state: TaskState | None) -> RepresentationKind:
    if job_state is None:
        return RepresentationKind.UNREPRESENTED
    if not isinstance(job_state, TaskState):
        raise ValueError("job_state must be a TaskState or None")
    return _REPRESENTATION_BY_STATE[job_state]


# ---------------- pure planner ----------------


class NextReadyDecision(str, Enum):
    DISPATCH_ONE = "DISPATCH_ONE"
    NOOP_NO_SUCCESSOR_READY = "NOOP_NO_SUCCESSOR_READY"
    NOOP_ALL_REPRESENTED = "NOOP_ALL_REPRESENTED"
    NOOP_PARENT_NOT_COMPLETE = "NOOP_PARENT_NOT_COMPLETE"
    RECONCILE_RECOVERY = "RECONCILE_RECOVERY"


@dataclass(frozen=True, slots=True)
class NextReadyPlan:
    decision: NextReadyDecision
    selected_node_id: str | None
    detail: str
    candidate_node_ids: tuple[str, ...] = ()
    represented_node_ids: tuple[str, ...] = ()
    recovery_node_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.decision, NextReadyDecision):
            raise ValueError("decision is invalid")
        for name in (
            "candidate_node_ids", "represented_node_ids", "recovery_node_ids",
        ):
            values = getattr(self, name)
            for value in values:
                _identity(value, name)
            object.__setattr__(self, name, tuple(values))
        if self.decision is NextReadyDecision.DISPATCH_ONE:
            _identity(self.selected_node_id, "selected_node_id")
        elif self.selected_node_id is not None:
            raise ValueError("selected_node_id is only valid for DISPATCH_ONE")
        if not isinstance(self.detail, str):
            raise ValueError("detail must be str")
        object.__setattr__(self, "detail", self.detail[:256])


_GUARD_CODES = (
    ("worktree_clean", "WORKTREE_DIRTY"),
    ("head_matches_expected", "HEAD_DRIFT"),
    ("lease_available", "LEASE_CONFLICT"),
    ("provider_admission_fresh", "PROVIDER_ADMISSION_STALE"),
)


def plan_next_ready_continuation(facts: NextReadyContinuationFacts) -> NextReadyPlan:
    """PURE deterministic ZRA-3 continuation decision for one tick.

    Decision order: structural identity -> parent completion -> guards ->
    successor representation -> bounded selection. Identical durable facts
    always yield an identical plan; ambiguity never dispatches.
    """
    if not isinstance(facts, NextReadyContinuationFacts):
        raise ValueError("facts must be NextReadyContinuationFacts")

    graph = facts.graph
    node_ids = set(graph.node_ids())
    if facts.parent.node_id not in node_ids:
        raise NextReadyContinuationError("PARENT_NODE_UNKNOWN")

    expected_job_id = GraphDispatchKey(
        facts.graph_id, facts.graph_run_id, facts.parent.node_id
    ).job_id
    if facts.parent.job_id != expected_job_id:
        raise NextReadyContinuationError("PARENT_JOB_IDENTITY_MISMATCH")

    child_ids = {
        edge.to_id for edge in graph.edges_from(facts.parent.node_id)
    }
    seen: set[str] = set()
    for observation in facts.successors:
        if observation.node_id not in child_ids:
            raise NextReadyContinuationError("SUCCESSOR_NOT_CHILD_OF_PARENT")
        if observation.node_id in seen:
            raise NextReadyContinuationError("SUCCESSOR_DUPLICATE")
        seen.add(observation.node_id)

    dag = topological_sort(graph)
    if dag.cycle is not None:
        raise NextReadyContinuationError("GRAPH_CYCLE")
    topo_rank = {node_id: index for index, node_id in enumerate(dag.order)}

    if facts.parent.state is not TaskState.COMPLETE:
        return NextReadyPlan(
            NextReadyDecision.NOOP_PARENT_NOT_COMPLETE,
            None,
            f"parent state is {facts.parent.state.value}; "
            "only durable COMPLETE authorizes continuation",
        )

    for field_name, code in _GUARD_CODES:
        if not getattr(facts.guards, field_name):
            return _guard_plan(code)

    candidates: list[tuple[int, int, str]] = []
    represented: list[tuple[int, int, str]] = []
    recovery: list[tuple[int, int, str]] = []
    for observation in facts.successors:
        node = graph.node(observation.node_id)
        order_key = (-node.priority, topo_rank.get(node.id, len(topo_rank)), node.id)
        kind = classify_successor_state(observation.job_state)
        if kind is RepresentationKind.UNREPRESENTED:
            if observation.node_id in facts.ready.ready_ids:
                candidates.append(order_key)
            # unrepresented but not ready: dependency/barrier/resource
            # semantics (compute_ready_set) keep it out of this tick
        elif kind is RepresentationKind.RECOVERY:
            recovery.append(order_key)
        else:
            represented.append(order_key)

    if candidates:
        candidates.sort()
        selected = candidates[0][2]
        detail = "one unrepresented READY successor selected (bounded ZRA-3)"
        if recovery:
            names = ",".join(key[2] for key in sorted(recovery))
            detail += f"; recovery siblings await reconciliation: {names}"
        return NextReadyPlan(
            NextReadyDecision.DISPATCH_ONE,
            selected,
            detail,
            candidate_node_ids=tuple(key[2] for key in candidates),
            represented_node_ids=tuple(key[2] for key in sorted(represented)),
            recovery_node_ids=tuple(key[2] for key in sorted(recovery)),
        )

    if recovery:
        return NextReadyPlan(
            NextReadyDecision.RECONCILE_RECOVERY,
            None,
            "prior successor dispatch is uncertain (RECOVERY_NEEDED); "
            "reconcile through existing recovery authority; never blind replay",
            candidate_node_ids=(),
            represented_node_ids=tuple(key[2] for key in sorted(represented)),
            recovery_node_ids=tuple(key[2] for key in sorted(recovery)),
        )

    if represented:
        return NextReadyPlan(
            NextReadyDecision.NOOP_ALL_REPRESENTED,
            None,
            "every direct successor is durably represented; no respawn",
            represented_node_ids=tuple(key[2] for key in sorted(represented)),
        )

    return NextReadyPlan(
        NextReadyDecision.NOOP_NO_SUCCESSOR_READY,
        None,
        "no direct successor is newly READY for this transition",
    )


def _guard_plan(code: str) -> NextReadyPlan:
    raise NextReadyContinuationError(code)


# ---------------- read-only fact observation ----------------


ContinuationJobReader = GraphJobStateReader


def observe_next_ready_facts(
    *,
    jobs: ContinuationJobReader,
    graph: TaskGraph,
    graph_id: str,
    graph_run_id: str,
    parent_node_id: str,
    guards: ContinuationGuards,
) -> NextReadyContinuationFacts:
    """Assemble one tick's facts from durable job reads (no mutation).

    Reuses the GraphLifecycleBridge projection for readiness and reads the
    raw durable state for successor representation. A missing parent job
    fails typed; a foreign graph-run identity therefore can never supply
    a completion for this run.
    """
    if not callable(getattr(jobs, "get_job", None)):
        raise ValueError("jobs must provide get_job")

    graph_id = _identity(graph_id, "graph_id")
    graph_run_id = _identity(graph_run_id, "graph_run_id")
    parent_node_id = _identity(parent_node_id, "parent_node_id")

    parent_key = GraphDispatchKey(graph_id, graph_run_id, parent_node_id)
    try:
        parent_job = jobs.get_job(parent_key.job_id)
    except JobStoreError as exc:
        if exc.code == "JOB_NOT_FOUND":
            raise NextReadyContinuationError("PARENT_JOB_NOT_FOUND") from exc
        raise
    if not isinstance(parent_job, JobRuntimeState):
        raise NextReadyContinuationError("PARENT_JOB_INVALID")
    if parent_job.job_id != parent_key.job_id:
        raise NextReadyContinuationError("PARENT_JOB_IDENTITY_MISMATCH")

    child_ids = {edge.to_id for edge in graph.edges_from(parent_node_id)}
    node_states: dict[str, TaskNodeStatus] = {}
    successor_states: dict[str, TaskState | None] = {}
    for node in graph.nodes():
        key = GraphDispatchKey(graph_id, graph_run_id, node.id)
        try:
            job = jobs.get_job(key.job_id)
        except JobStoreError as exc:
            if exc.code != "JOB_NOT_FOUND":
                raise
            job = None
        if job is None:
            node_states[node.id] = TaskNodeStatus.TODO
            if node.id in child_ids:
                successor_states[node.id] = None
            continue
        if not isinstance(job, JobRuntimeState):
            raise NextReadyContinuationError("GRAPH_JOB_INVALID")
        if job.job_id != key.job_id:
            raise NextReadyContinuationError("GRAPH_JOB_IDENTITY_MISMATCH")
        node_states[node.id] = project_job_state(job)
        if node.id in child_ids:
            successor_states[node.id] = job.state

    successors = tuple(
        SuccessorObservation(node_id=node_id, job_state=state)
        for node_id, state in sorted(successor_states.items())
    )
    return NextReadyContinuationFacts(
        graph_id=graph_id,
        graph_run_id=graph_run_id,
        parent=ParentCompletion(
            node_id=parent_node_id,
            job_id=parent_job.job_id,
            state=parent_job.state,
            version=parent_job.version,
            completion_ref=None,
        ),
        graph=graph,
        ready=compute_ready_set(graph, node_states),
        successors=successors,
        guards=guards,
    )


# ---------------- thin executor over one injected port ----------------


class SuccessorDispatchPort(Protocol):
    """One physical dispatch attempt for the selected successor node.

    Production binds this to worker selection (schedule_once) plus the
    durable GraphDispatchCoordinator; the port contract keeps this module
    free of scheduler/lease/provider wiring.
    """

    def dispatch_successor(self, node_id: str) -> object: ...


class ContinuationExecutionOutcome(str, Enum):
    PLANNER_NOOP = "PLANNER_NOOP"
    DISPATCH_EXECUTED = "DISPATCH_EXECUTED"
    DISPATCH_OFFERED = "DISPATCH_OFFERED"
    DISPATCH_BLOCKED = "DISPATCH_BLOCKED"
    DISPATCH_EXISTING = "DISPATCH_EXISTING"
    DISPATCH_RECONCILE = "DISPATCH_RECONCILE"
    RELOAD_REPLAN = "RELOAD_REPLAN"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


_ACTION_OUTCOMES: dict[GraphDispatchAction, ContinuationExecutionOutcome] = {
    GraphDispatchAction.EXECUTED: ContinuationExecutionOutcome.DISPATCH_EXECUTED,
    GraphDispatchAction.OFFERED: ContinuationExecutionOutcome.DISPATCH_OFFERED,
    GraphDispatchAction.BLOCKED: ContinuationExecutionOutcome.DISPATCH_BLOCKED,
    GraphDispatchAction.EXISTING: ContinuationExecutionOutcome.DISPATCH_EXISTING,
    GraphDispatchAction.RECONCILE: ContinuationExecutionOutcome.DISPATCH_RECONCILE,
}


@dataclass(frozen=True, slots=True)
class ContinuationExecutionResult:
    outcome: ContinuationExecutionOutcome
    plan: NextReadyPlan
    dispatch_result: object | None = None
    detail: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, ContinuationExecutionOutcome):
            raise ValueError("outcome is invalid")
        if not isinstance(self.plan, NextReadyPlan):
            raise ValueError("plan must be NextReadyPlan")
        if not isinstance(self.detail, str):
            raise ValueError("detail must be str")
        object.__setattr__(self, "detail", self.detail[:256])


class NextReadyContinuationExecutor:
    """Executes at most ONE dispatch attempt per call over an injected port.

    No internal loop, no retry, no state of its own. The durable dispatch
    journal (GraphDispatchCoordinator job identity) is the replay boundary:
    after any outcome, the next tick re-observes durable truth and re-plans.
    """

    def __init__(self, *, dispatch_port: SuccessorDispatchPort) -> None:
        if not callable(getattr(dispatch_port, "dispatch_successor", None)):
            raise ValueError("dispatch_port must provide dispatch_successor")
        self._port = dispatch_port

    def execute_next(self, facts: NextReadyContinuationFacts) -> ContinuationExecutionResult:
        plan = plan_next_ready_continuation(facts)
        if plan.decision is not NextReadyDecision.DISPATCH_ONE:
            return ContinuationExecutionResult(
                ContinuationExecutionOutcome.PLANNER_NOOP, plan, None, plan.detail
            )

        assert plan.selected_node_id is not None  # DISPATCH_ONE invariant
        try:
            result = self._port.dispatch_successor(plan.selected_node_id)
        except JobStoreError as exc:
            if exc.code == "JOB_VERSION_CONFLICT":
                return ContinuationExecutionResult(
                    ContinuationExecutionOutcome.RELOAD_REPLAN, plan, None,
                    "JOB_VERSION_CONFLICT",
                )
            return ContinuationExecutionResult(
                ContinuationExecutionOutcome.RECOVERY_REQUIRED, plan, None,
                f"DISPATCH_STORE_FAILED:{exc.code}",
            )
        except NextReadyContinuationError as exc:
            raise
        except Exception as exc:
            # bounded, non-sensitive detail: type name only, never payloads
            return ContinuationExecutionResult(
                ContinuationExecutionOutcome.RECOVERY_REQUIRED, plan, None,
                f"DISPATCH_PORT_FAILED:{type(exc).__name__}",
            )

        if not isinstance(result, GraphDispatchResult):
            return ContinuationExecutionResult(
                ContinuationExecutionOutcome.RECOVERY_REQUIRED, plan, result,
                "DISPATCH_RESULT_UNSUPPORTED",
            )
        outcome = _ACTION_OUTCOMES.get(result.action)
        if outcome is None:
            return ContinuationExecutionResult(
                ContinuationExecutionOutcome.RECOVERY_REQUIRED, plan, result,
                f"DISPATCH_ACTION_UNSUPPORTED:{result.action.value}",
            )
        return ContinuationExecutionResult(outcome, plan, result, result.reason_code)
