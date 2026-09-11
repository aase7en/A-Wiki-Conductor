"""WO-P1-195 — truthful production composition for ZRA-3 NEXT READY.

This module owns no scheduler, worker lease, provider admission, retry, review,
or dispatch journal. It composes existing durable authorities into one bounded
continuation tick and delegates mutation-sensitive revalidation to the accepted
production executor.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol

from .domain import TaskState
from .elastic_worker_capacity import (
    ElasticCapacityPolicy,
    ProductionElasticExecutionKind,
    ProductionElasticExecutionResult,
)
from .goal_closeout import CloseoutStage, closeout_checkpoint_ref
from .graph.dispatch import GraphDispatchKey
from .graph.domain import TaskGraph
from .graph.ready import ReadySetResult
from .graph.scheduler import NodeEligibility, SchedulePolicy
from .job_state import JobRuntimeState
from .job_store import JobEvent, JobEventType, JobStoreError
from .worker_candidate_assembly import ParallelReadyNodeContract
from .next_ready_continuation import (
    NextReadyDecision,
    NextReadyPlan,
    observe_next_ready_facts,
    plan_next_ready_selection,
)

_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")


class NextReadyProductionError(RuntimeError):
    def __init__(self, code: str) -> None:
        if not isinstance(code, str) or not code or len(code) > 128:
            raise ValueError("code is invalid")
        self.code = code
        super().__init__(code)


class NextReadyProductionOutcome(str, Enum):
    NOOP = "NOOP"
    RECONCILE = "RECONCILE"
    EXECUTED = "EXECUTED"
    WAIT = "WAIT"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


@dataclass(frozen=True, slots=True)
class NextReadyProductionResult:
    outcome: NextReadyProductionOutcome
    plan: NextReadyPlan
    selected_node_id: str | None = None
    batch_id: str | None = None
    downstream: ProductionElasticExecutionResult | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, NextReadyProductionOutcome):
            raise ValueError("outcome is invalid")
        if not isinstance(self.plan, NextReadyPlan):
            raise ValueError("plan is invalid")
        if self.outcome is NextReadyProductionOutcome.EXECUTED and self.selected_node_id is None:
            raise ValueError("executed result requires selected_node_id")


class ContinuationJobEventReader(Protocol):
    def get_job(self, job_id: str) -> JobRuntimeState: ...
    def list_events(self, job_id: str) -> tuple[JobEvent, ...]: ...


class ContinuationGraphReader(Protocol):
    def load_graph(self, graph_id: str) -> TaskGraph: ...


class ProductionContinuationExecutor(Protocol):
    def execute_once(
        self,
        graph: TaskGraph,
        ready: ReadySetResult,
        contracts_by_node: Mapping[str, object],
        *,
        schedule_policy: SchedulePolicy,
        provider_inflight: Mapping[str, int],
        runtime_kind: str,
        elastic_policy: ElasticCapacityPolicy,
        running_write_sets: dict[str, tuple[str, ...]] | None = None,
        eligibility: dict[str, NodeEligibility] | None = None,
        batch_id: str | None = None,
    ) -> ProductionElasticExecutionResult: ...


def derive_zra3_batch_id(graph_id: str, graph_run_id: str, selected_job_id: str) -> str:
    """Stable batch identity derived only from canonical graph/dispatch identity."""
    for name, value in (
        ("graph_id", graph_id),
        ("graph_run_id", graph_run_id),
        ("selected_job_id", selected_job_id),
    ):
        if not isinstance(value, str) or not value.strip() or "\x00" in value:
            raise ValueError(f"{name} is invalid")
    material = b"zra3-batch-v1\x00" + b"\x00".join(
        value.strip().encode("utf-8")
        for value in (graph_id, graph_run_id, selected_job_id)
    )
    return f"zra3b1:{hashlib.sha256(material).hexdigest()}"


def _resolve_complete_evidence(job: JobRuntimeState, events: tuple[JobEvent, ...]) -> str:
    if not isinstance(job, JobRuntimeState) or job.state is not TaskState.COMPLETE:
        raise NextReadyProductionError("PARENT_NOT_COMPLETE")
    if not isinstance(events, tuple) or not all(isinstance(event, JobEvent) for event in events):
        raise NextReadyProductionError("PARENT_COMPLETION_EVENTS_INVALID")

    transitions = [event for event in events if event.event_type is JobEventType.TRANSITION]
    if not transitions:
        raise NextReadyProductionError("PARENT_COMPLETION_EVENT_MISSING")
    terminal = transitions[-1]
    if terminal.job_id != job.job_id:
        raise NextReadyProductionError("PARENT_COMPLETION_EVENT_IDENTITY_MISMATCH")
    if terminal.to_state is not TaskState.COMPLETE:
        raise NextReadyProductionError("PARENT_COMPLETION_EVENT_MISSING")

    ref = terminal.evidence_ref
    if not isinstance(ref, str) or not ref:
        raise NextReadyProductionError("PARENT_COMPLETION_EVIDENCE_MISSING")
    prefix = "closeout:complete:"
    if not ref.startswith(prefix):
        raise NextReadyProductionError("PARENT_COMPLETION_EVIDENCE_INVALID")
    body = ref[len(prefix):]
    try:
        task_id, candidate_sha = body.rsplit(":", 1)
    except ValueError:
        raise NextReadyProductionError("PARENT_COMPLETION_EVIDENCE_INVALID") from None
    if task_id != job.work_order_ref or not _SHA_RE.fullmatch(candidate_sha):
        raise NextReadyProductionError("PARENT_COMPLETION_EVIDENCE_INVALID")
    try:
        canonical = closeout_checkpoint_ref(
            CloseoutStage.COMPLETE,
            task_id=job.work_order_ref,
            candidate_sha=candidate_sha,
        )
    except ValueError:
        raise NextReadyProductionError("PARENT_COMPLETION_EVIDENCE_INVALID") from None
    if canonical != ref:
        raise NextReadyProductionError("PARENT_COMPLETION_EVIDENCE_INVALID")
    return ref


class NextReadyProductionAssembly:
    """Execute at most one production continuation attempt per invocation."""

    def __init__(
        self,
        *,
        jobs: ContinuationJobEventReader,
        graphs: ContinuationGraphReader,
        executor: ProductionContinuationExecutor,
    ) -> None:
        if not callable(getattr(jobs, "get_job", None)) or not callable(
            getattr(jobs, "list_events", None)
        ):
            raise ValueError("jobs must provide get_job/list_events")
        if not callable(getattr(graphs, "load_graph", None)):
            raise ValueError("graphs must provide load_graph")
        if not callable(getattr(executor, "execute_once", None)):
            raise ValueError("executor must provide execute_once")
        self._jobs = jobs
        self._graphs = graphs
        self._executor = executor

    def execute_once(
        self,
        *,
        graph_id: str,
        graph_run_id: str,
        parent_node_id: str,
        contracts_by_node: Mapping[str, object],
        schedule_policy: SchedulePolicy,
        provider_inflight: Mapping[str, int],
        runtime_kind: str,
        elastic_policy: ElasticCapacityPolicy,
        running_write_sets: dict[str, tuple[str, ...]] | None = None,
        eligibility: dict[str, NodeEligibility] | None = None,
    ) -> NextReadyProductionResult:
        if not isinstance(contracts_by_node, Mapping):
            raise ValueError("contracts_by_node must be a mapping")

        graph = self._graphs.load_graph(graph_id)
        if not isinstance(graph, TaskGraph):
            raise NextReadyProductionError("GRAPH_LOAD_INVALID")
        parent_key = GraphDispatchKey(graph_id, graph_run_id, parent_node_id)
        try:
            parent_job = self._jobs.get_job(parent_key.job_id)
        except JobStoreError as exc:
            if exc.code == "JOB_NOT_FOUND":
                raise NextReadyProductionError("PARENT_JOB_NOT_FOUND") from exc
            raise
        if not isinstance(parent_job, JobRuntimeState):
            raise NextReadyProductionError("PARENT_JOB_INVALID")
        if parent_job.job_id != parent_key.job_id:
            raise NextReadyProductionError("PARENT_JOB_IDENTITY_MISMATCH")

        completion_ref: str | None = None
        if parent_job.state is TaskState.COMPLETE:
            try:
                events = self._jobs.list_events(parent_key.job_id)
            except JobStoreError as exc:
                raise NextReadyProductionError("PARENT_COMPLETION_EVENTS_UNAVAILABLE") from exc
            completion_ref = _resolve_complete_evidence(parent_job, events)

        facts = observe_next_ready_facts(
            jobs=self._jobs,
            graph=graph,
            graph_id=graph_id,
            graph_run_id=graph_run_id,
            parent_node_id=parent_node_id,
            guards=None,
            completion_ref=completion_ref,
        )
        if (
            facts.parent.job_id != parent_job.job_id
            or facts.parent.version != parent_job.version
            or facts.parent.state is not parent_job.state
        ):
            raise NextReadyProductionError("PARENT_STATE_DRIFT")
        plan = plan_next_ready_selection(facts)

        if plan.decision is NextReadyDecision.RECONCILE_RECOVERY:
            return NextReadyProductionResult(NextReadyProductionOutcome.RECONCILE, plan)
        if plan.decision is not NextReadyDecision.DISPATCH_ONE:
            return NextReadyProductionResult(NextReadyProductionOutcome.NOOP, plan)

        selected = plan.selected_node_id
        assert selected is not None
        contract = contracts_by_node.get(selected)
        if contract is None:
            raise NextReadyProductionError("SELECTED_CONTRACT_MISSING")
        if not isinstance(contract, ParallelReadyNodeContract):
            raise NextReadyProductionError("SELECTED_CONTRACT_INVALID")
        dispatch_key = contract.dispatch_key
        expected_key = GraphDispatchKey(graph_id, graph_run_id, selected)
        if not isinstance(dispatch_key, GraphDispatchKey) or dispatch_key != expected_key:
            raise NextReadyProductionError("SELECTED_CONTRACT_IDENTITY_MISMATCH")

        check = facts.ready.checks.get(selected)
        if check is None or selected not in facts.ready.ready_ids:
            raise NextReadyProductionError("SELECTED_READY_EVIDENCE_MISSING")
        focused_ready = ReadySetResult(checks={selected: check}, ready_ids={selected})
        focused_contracts = {selected: contract}
        if eligibility is None or selected not in eligibility:
            raise NextReadyProductionError("SELECTED_ELIGIBILITY_MISSING")
        selected_eligibility = eligibility[selected]
        if not isinstance(selected_eligibility, NodeEligibility):
            raise NextReadyProductionError("SELECTED_ELIGIBILITY_INVALID")
        focused_eligibility = {selected: selected_eligibility}
        batch_id = derive_zra3_batch_id(graph_id, graph_run_id, expected_key.job_id)

        downstream = self._executor.execute_once(
            graph,
            focused_ready,
            focused_contracts,
            schedule_policy=schedule_policy,
            provider_inflight=provider_inflight,
            runtime_kind=runtime_kind,
            elastic_policy=elastic_policy,
            running_write_sets=running_write_sets,
            eligibility=focused_eligibility,
            batch_id=batch_id,
        )
        if not isinstance(downstream, ProductionElasticExecutionResult):
            raise NextReadyProductionError("DOWNSTREAM_RESULT_INVALID")
        if downstream.kind in {
            ProductionElasticExecutionKind.FIXED_POOL_EXECUTED,
            ProductionElasticExecutionKind.ELASTIC_EXECUTED,
        }:
            outcome = NextReadyProductionOutcome.EXECUTED
        elif downstream.kind is ProductionElasticExecutionKind.WAIT:
            outcome = NextReadyProductionOutcome.WAIT
        elif downstream.kind is ProductionElasticExecutionKind.RECOVERY_REQUIRED:
            outcome = NextReadyProductionOutcome.RECOVERY_REQUIRED
        else:
            raise NextReadyProductionError("DOWNSTREAM_RESULT_UNSUPPORTED")
        return NextReadyProductionResult(
            outcome,
            plan,
            selected_node_id=selected,
            batch_id=batch_id,
            downstream=downstream,
        )
