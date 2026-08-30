"""AHA-6 fixed-pool parallel execution over accepted coordination seams.

This module owns no scheduler, durable lifecycle/store, retry loop, provider client,
credential resolver, or lease implementation. It consumes an exact SchedulePlan,
provider readiness/capacity evidence, and the existing WorkerLeaseBroker, then runs
only newly leased tasks through an injected runner. Existing/recovery/uncertain work
is never replayed here.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping, Protocol

from .claude_code_harness import HarnessDispatch, TaskPacketFile
from .graph.dispatch import (
    DispatchGateDecision,
    GraphDispatchMode,
    GraphDispatchRequest,
)
from .graph.scheduler import SchedulePlan, SelectedAssignment
from .provider_configuration import (
    ProviderConfiguration,
    ProviderObservation,
    is_provider_ready,
)
from .registry import windows_worktree_key
from .worker_lease import (
    LeaseOutcomeKind,
    WorkerLease,
    WorkerLeaseBroker,
    WorkerLeaseCandidate,
    WorkerLeaseOutcome,
    WorkerLeaseRequest,
)


class ParallelReadyOutcomeKind(str, Enum):
    RUN_COMPLETED = "RUN_COMPLETED"
    RUNNER_RECOVERY_REQUIRED = "RUNNER_RECOVERY_REQUIRED"
    PROVIDER_WAIT = "PROVIDER_WAIT"
    PROVIDER_QUOTA_WAIT = "PROVIDER_QUOTA_WAIT"
    PROVIDER_CAPACITY_WAIT = "PROVIDER_CAPACITY_WAIT"
    DISPATCH_GATE_BLOCKED = "DISPATCH_GATE_BLOCKED"
    LEASE_WAIT = "LEASE_WAIT"
    LEASE_EXISTING_RECONCILE = "LEASE_EXISTING_RECONCILE"
    LEASE_RECOVERY_REQUIRED = "LEASE_RECOVERY_REQUIRED"
    RDC_READ_ONLY = "RDC_READ_ONLY"


@dataclass(frozen=True, slots=True)
class ParallelReadyOutcome:
    node_id: str
    kind: ParallelReadyOutcomeKind
    reason_code: str
    lease_outcome: WorkerLeaseOutcome | None = None
    runner_result: object | None = None


@dataclass(frozen=True, slots=True)
class ParallelReadyBatchResult:
    outcomes: tuple[ParallelReadyOutcome, ...]


class ParallelReadyRunner(Protocol):
    def run(self, task: "ParallelReadyTask", lease: WorkerLease) -> object: ...


class GraphDispatchPort(Protocol):
    def dispatch(
        self, request: GraphDispatchRequest, *, gate: DispatchGateDecision
    ) -> object: ...


class GraphDispatchParallelRunner:
    """Delegate one leased task to the accepted GE-7 durable dispatch coordinator."""

    def __init__(self, coordinator: GraphDispatchPort) -> None:
        if not callable(getattr(coordinator, "dispatch", None)):
            raise ValueError("coordinator must provide dispatch")
        self._coordinator = coordinator

    def run(self, task: "ParallelReadyTask", lease: WorkerLease) -> object:
        if lease.worker_id != task.assignment.worker_id:
            raise ValueError("lease worker does not match selected assignment")
        return self._coordinator.dispatch(
            task.dispatch_request, gate=task.dispatch_gate
        )


@dataclass(frozen=True, slots=True)
class ParallelReadyTask:
    assignment: SelectedAssignment
    dispatch_request: GraphDispatchRequest
    dispatch_gate: DispatchGateDecision
    lease_request: WorkerLeaseRequest
    candidates: tuple[WorkerLeaseCandidate, ...]
    provider_profile: ProviderConfiguration
    provider_observation: ProviderObservation | None
    harness_dispatch: HarnessDispatch
    task_packet: TaskPacketFile
    require_quota: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.assignment, SelectedAssignment):
            raise ValueError("assignment must be SelectedAssignment")
        if not isinstance(self.dispatch_request, GraphDispatchRequest):
            raise ValueError("dispatch_request must be GraphDispatchRequest")
        if not isinstance(self.dispatch_gate, DispatchGateDecision):
            raise ValueError("dispatch_gate must be DispatchGateDecision")
        if not isinstance(self.lease_request, WorkerLeaseRequest):
            raise ValueError("lease_request must be WorkerLeaseRequest")
        candidates = tuple(self.candidates)
        if len(candidates) != 1 or not isinstance(candidates[0], WorkerLeaseCandidate):
            raise ValueError("exactly one selected lease candidate is required")
        if self.lease_request.ordered_worker_ids != (self.assignment.worker_id,):
            raise ValueError("selected worker must be sole lease candidate")
        if candidates[0].worker_id != self.assignment.worker_id:
            raise ValueError("candidate worker must match selected assignment")
        if not isinstance(self.provider_profile, ProviderConfiguration):
            raise ValueError("provider_profile must be ProviderConfiguration")
        if self.provider_observation is not None and not isinstance(
            self.provider_observation, ProviderObservation
        ):
            raise ValueError("provider_observation must be ProviderObservation or None")
        if not isinstance(self.harness_dispatch, HarnessDispatch):
            raise ValueError("harness_dispatch must be HarnessDispatch")
        if not isinstance(self.task_packet, TaskPacketFile):
            raise ValueError("task_packet must be TaskPacketFile")
        if not isinstance(self.require_quota, bool):
            raise ValueError("require_quota must be bool")
        dispatch = self.harness_dispatch
        graph_dispatch = self.dispatch_request
        request = self.lease_request
        if graph_dispatch.assignment != self.assignment:
            raise ValueError("graph dispatch assignment mismatch")
        if graph_dispatch.dispatch_mode is not GraphDispatchMode.PROGRAMMATIC_PUSH:
            raise ValueError("parallel execution requires PROGRAMMATIC_PUSH")
        if graph_dispatch.key.job_id != dispatch.execution_id:
            raise ValueError("graph dispatch job identity mismatch")
        if graph_dispatch.project_id != dispatch.project_id:
            raise ValueError("graph dispatch project identity mismatch")
        if graph_dispatch.work_order_ref != dispatch.task_contract_ref:
            raise ValueError("graph dispatch work-order identity mismatch")
        if self.provider_profile.provider_id != dispatch.provider_id:
            raise ValueError("provider identity mismatch")
        if self.provider_observation is not None:
            if self.provider_observation.provider_id != dispatch.provider_id:
                raise ValueError("provider observation identity mismatch")
        if request.project_id != dispatch.project_id:
            raise ValueError("project identity mismatch")
        if windows_worktree_key(request.worktree) != windows_worktree_key(dispatch.worktree_path):
            raise ValueError("worktree identity mismatch")
        if dispatch.expected_branch is None or request.branch != dispatch.expected_branch:
            raise ValueError("branch identity mismatch")
        if request.expected_head.casefold() != dispatch.expected_head.casefold():
            raise ValueError("head identity mismatch")
        if self.task_packet.task_contract_ref != dispatch.task_contract_ref:
            raise ValueError("task packet contract mismatch")
        if request.lease_ttl_seconds <= dispatch.timeout_seconds:
            raise ValueError("lease TTL must exceed execution timeout")
        object.__setattr__(self, "candidates", candidates)


def _quota_reason(task: ParallelReadyTask) -> str | None:
    if not task.require_quota:
        return None
    observation = task.provider_observation
    quota = None if observation is None else observation.quota
    if quota is None:
        return "PROVIDER_QUOTA_UNKNOWN"
    required = (
        quota.limit,
        quota.used,
        quota.remaining,
        quota.reset_at,
        quota.reset_in_seconds,
    )
    if any(item is None for item in required):
        return "PROVIDER_QUOTA_UNKNOWN"
    if quota.remaining is not None and quota.remaining <= 0:
        return "PROVIDER_QUOTA_EXHAUSTED"
    return None


def _lease_wait_outcome(node_id: str, outcome: WorkerLeaseOutcome) -> ParallelReadyOutcome:
    mapping = {
        LeaseOutcomeKind.WAIT: (ParallelReadyOutcomeKind.LEASE_WAIT, "LEASE_WAIT"),
        LeaseOutcomeKind.EXISTING: (
            ParallelReadyOutcomeKind.LEASE_EXISTING_RECONCILE,
            "LEASE_ALREADY_ACTIVE_RECONCILE",
        ),
        LeaseOutcomeKind.RECOVERY_REQUIRED: (
            ParallelReadyOutcomeKind.LEASE_RECOVERY_REQUIRED,
            "LEASE_RECOVERY_REQUIRED",
        ),
        LeaseOutcomeKind.RDC_READ_ONLY: (ParallelReadyOutcomeKind.RDC_READ_ONLY, "RDC_READ_ONLY"),
    }
    kind, reason = mapping[outcome.kind]
    return ParallelReadyOutcome(node_id, kind, reason, lease_outcome=outcome)


class ParallelReadyExecutor:
    def __init__(
        self,
        *,
        broker: WorkerLeaseBroker,
        runner: ParallelReadyRunner,
        clock: Callable[[], object],
    ) -> None:
        if not callable(getattr(broker, "acquire", None)):
            raise ValueError("broker must provide acquire")
        if not callable(getattr(runner, "run", None)):
            raise ValueError("runner must provide run")
        if not callable(clock):
            raise ValueError("clock must be callable")
        self._broker = broker
        self._runner = runner
        self._clock = clock

    @staticmethod
    def _validate_batch(
        plan: SchedulePlan,
        tasks_by_node: Mapping[str, ParallelReadyTask],
        provider_inflight: Mapping[str, int],
    ) -> tuple[ParallelReadyTask, ...]:
        if not isinstance(plan, SchedulePlan):
            raise ValueError("plan must be SchedulePlan")
        if not isinstance(tasks_by_node, Mapping):
            raise ValueError("tasks_by_node must be a mapping")
        selected_ids = tuple(item.node_id for item in plan.selected)
        if len(set(selected_ids)) != len(selected_ids):
            raise ValueError("selected node IDs must be unique")
        if set(tasks_by_node) != set(selected_ids):
            raise ValueError("selected task mapping mismatch")
        if not isinstance(provider_inflight, Mapping):
            raise ValueError("provider_inflight must be a mapping")
        tasks: list[ParallelReadyTask] = []
        profiles: dict[str, ProviderConfiguration] = {}
        for assignment in plan.selected:
            task = tasks_by_node[assignment.node_id]
            if not isinstance(task, ParallelReadyTask):
                raise ValueError("task mapping values must be ParallelReadyTask")
            if task.assignment != assignment:
                raise ValueError("selected assignment drift")
            provider_id = task.provider_profile.provider_id
            prior = profiles.get(provider_id)
            if prior is not None and prior != task.provider_profile:
                raise ValueError("provider profile mismatch within batch")
            profiles[provider_id] = task.provider_profile
            if provider_id not in provider_inflight:
                raise ValueError(f"provider_inflight missing {provider_id}")
            inflight = provider_inflight[provider_id]
            if isinstance(inflight, bool) or not isinstance(inflight, int) or inflight < 0:
                raise ValueError("provider_inflight values must be non-negative integers")
            tasks.append(task)
        return tuple(tasks)

    def execute(
        self,
        plan: SchedulePlan,
        tasks_by_node: Mapping[str, ParallelReadyTask],
        *,
        provider_inflight: Mapping[str, int],
    ) -> ParallelReadyBatchResult:
        tasks = self._validate_batch(plan, tasks_by_node, provider_inflight)
        now = self._clock()
        provider_batch_count: dict[str, int] = {}
        outcomes: dict[str, ParallelReadyOutcome] = {}
        runnable: list[tuple[ParallelReadyTask, WorkerLeaseOutcome]] = []

        for task in tasks:
            node_id = task.assignment.node_id
            profile = task.provider_profile
            provider_id = profile.provider_id
            if not task.dispatch_gate.allowed:
                outcomes[node_id] = ParallelReadyOutcome(
                    node_id,
                    ParallelReadyOutcomeKind.DISPATCH_GATE_BLOCKED,
                    task.dispatch_gate.reason_code,
                )
                continue
            if not is_provider_ready(profile, task.provider_observation, now=now):
                outcomes[node_id] = ParallelReadyOutcome(
                    node_id,
                    ParallelReadyOutcomeKind.PROVIDER_WAIT,
                    "PROVIDER_NOT_READY",
                )
                continue
            quota_reason = _quota_reason(task)
            if quota_reason is not None:
                outcomes[node_id] = ParallelReadyOutcome(
                    node_id,
                    ParallelReadyOutcomeKind.PROVIDER_QUOTA_WAIT,
                    quota_reason,
                )
                continue
            batch_count = provider_batch_count.get(provider_id, 0)
            if provider_inflight[provider_id] + batch_count >= profile.max_concurrency:
                outcomes[node_id] = ParallelReadyOutcome(
                    node_id,
                    ParallelReadyOutcomeKind.PROVIDER_CAPACITY_WAIT,
                    "PROVIDER_CAPACITY_EXHAUSTED",
                )
                continue

            lease_outcome = self._broker.acquire(task.lease_request, task.candidates)
            if lease_outcome.kind is not LeaseOutcomeKind.LEASED:
                outcomes[node_id] = _lease_wait_outcome(node_id, lease_outcome)
                continue
            if lease_outcome.lease is None:
                raise RuntimeError("LEASED outcome missing lease")
            if lease_outcome.lease.worker_id != task.assignment.worker_id:
                raise RuntimeError("leased worker drifted from scheduler assignment")
            provider_batch_count[provider_id] = batch_count + 1
            runnable.append((task, lease_outcome))

        if runnable:
            with ThreadPoolExecutor(
                max_workers=len(runnable),
                thread_name_prefix="a-conductor-aha6",
            ) as pool:
                futures = {
                    task.assignment.node_id: pool.submit(
                        self._runner.run,
                        task,
                        lease_outcome.lease,
                    )
                    for task, lease_outcome in runnable
                }
                for task, lease_outcome in runnable:
                    node_id = task.assignment.node_id
                    try:
                        runner_result = futures[node_id].result()
                    except Exception as exc:
                        code = getattr(exc, "code", None)
                        reason = (
                            code
                            if isinstance(code, str)
                            and code
                            and len(code) <= 128
                            and all(ch.isalnum() or ch in "._:-" for ch in code)
                            else "RUNNER_EXCEPTION"
                        )
                        outcomes[node_id] = ParallelReadyOutcome(
                            node_id,
                            ParallelReadyOutcomeKind.RUNNER_RECOVERY_REQUIRED,
                            reason,
                            lease_outcome=lease_outcome,
                        )
                        continue
                    outcomes[node_id] = ParallelReadyOutcome(
                        node_id,
                        ParallelReadyOutcomeKind.RUN_COMPLETED,
                        "RUNNER_COMPLETED",
                        lease_outcome=lease_outcome,
                        runner_result=runner_result,
                    )

        return ParallelReadyBatchResult(
            tuple(outcomes[item.node_id] for item in plan.selected)
        )
