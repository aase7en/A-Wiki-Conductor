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
    GraphDispatchAction,
    GraphDispatchMode,
    GraphDispatchRequest,
    GraphDispatchResult,
)
from .domain import TaskState
from .graph.scheduler import SchedulePlan, SelectedAssignment
from .provider_config_store import (
    ProviderAdmissionKind,
    ProviderAdmissionRecord,
    ProviderAdmissionResult,
    ProviderConfigurationSnapshot,
)
from .provider_configuration import (
    ProviderConfiguration,
    ProviderEndpointConfig,
    ProviderObservation,
    is_provider_ready,
)
from .provider_execution_authority import (
    ProviderExecutionAuthority,
    ProviderExecutionRequirement,
)
from .provider_policy import (
    ProviderPolicyTaskSecurity,
    evaluate_provider_policy,
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
    PROVIDER_ADMISSION_RECOVERY_REQUIRED = "PROVIDER_ADMISSION_RECOVERY_REQUIRED"
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
    provider_admission: ProviderAdmissionRecord | None = None


@dataclass(frozen=True, slots=True)
class ParallelReadyBatchResult:
    outcomes: tuple[ParallelReadyOutcome, ...]


class ParallelReadyRunner(Protocol):
    def run(self, task: "ParallelReadyTask", lease: WorkerLease) -> object: ...


class GraphDispatchPort(Protocol):
    def dispatch(
        self, request: GraphDispatchRequest, *, gate: DispatchGateDecision
    ) -> object: ...


class ProviderAdmissionPort(Protocol):
    def acquire_admission(
        self,
        *,
        provider_id: str,
        execution_id: str,
        batch_id: str,
        expected_max_concurrency: int,
        now: object,
        ttl_seconds: int,
        expected_configuration_generation: int | None = None,
    ) -> ProviderAdmissionResult: ...

    def load_provider_snapshot(
        self, provider_id: str
    ) -> ProviderConfigurationSnapshot | None: ...

    def release_admission(
        self,
        admission_id: str,
        *,
        provider_id: str,
        execution_id: str,
        batch_id: str,
        now: object,
    ) -> ProviderAdmissionRecord: ...


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
    provider_endpoint: ProviderEndpointConfig | None = None
    provider_security: ProviderPolicyTaskSecurity | None = None
    expected_configuration_generation: int | None = None
    require_quota: bool = False
    provider_requirement: ProviderExecutionRequirement | None = None

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
        authority = (
            self.provider_endpoint,
            self.provider_security,
            self.expected_configuration_generation,
        )
        if any(item is not None for item in authority):
            if not all(item is not None for item in authority):
                raise ValueError("provider execution authority must be complete")
            if not isinstance(self.provider_endpoint, ProviderEndpointConfig):
                raise ValueError("provider_endpoint must be ProviderEndpointConfig")
            if self.provider_endpoint.endpoint_ref != self.provider_profile.endpoint_ref:
                raise ValueError("provider endpoint identity mismatch")
            if not isinstance(self.provider_security, ProviderPolicyTaskSecurity):
                raise ValueError("provider_security must be ProviderPolicyTaskSecurity")
            generation = self.expected_configuration_generation
            if (
                isinstance(generation, bool)
                or not isinstance(generation, int)
                or generation < 1
            ):
                raise ValueError("expected_configuration_generation must be positive")
        if not isinstance(self.require_quota, bool):
            raise ValueError("require_quota must be bool")
        if self.provider_requirement is not None:
            requirement = self.provider_requirement
            if not isinstance(requirement, ProviderExecutionRequirement):
                raise ValueError("provider_requirement must be ProviderExecutionRequirement")
            if requirement.provider_id != self.provider_profile.provider_id:
                raise ValueError("provider requirement identity mismatch")
            if requirement.provider_security != self.provider_security:
                raise ValueError("provider requirement security mismatch")
            if requirement.expected_configuration_generation != self.expected_configuration_generation:
                raise ValueError("provider requirement generation mismatch")
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
        if self.provider_requirement is not None:
            if self.provider_requirement.task_contract_ref != dispatch.task_contract_ref:
                raise ValueError("provider requirement contract mismatch")
            if self.provider_requirement.operation_ref != graph_dispatch.operation_ref:
                raise ValueError("provider requirement operation mismatch")
        if request.lease_ttl_seconds <= dispatch.timeout_seconds:
            raise ValueError("lease TTL must exceed execution timeout")
        object.__setattr__(self, "candidates", candidates)


def _quota_reason(
    task: ParallelReadyTask,
    observation: ProviderObservation | None = None,
) -> str | None:
    if not task.require_quota:
        return None
    observation = task.provider_observation if observation is None else observation
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


def _safe_reason_code(code: object, fallback: str) -> str:
    if (
        isinstance(code, str)
        and code
        and len(code) <= 128
        and all(ch.isalnum() or ch in "._:-" for ch in code)
    ):
        return code
    return fallback


def _safe_exception_reason(exc: Exception, fallback: str) -> str:
    return _safe_reason_code(getattr(exc, "code", None), fallback)


def _dispatch_job_matches_task(result: GraphDispatchResult, task: ParallelReadyTask, lease: WorkerLease) -> bool:
    job = result.job
    request = task.dispatch_request
    if (
        job.job_id != request.key.job_id
        or job.project_id != request.project_id
        or job.work_order_ref != request.work_order_ref
        or job.max_attempts != request.max_attempts
    ):
        return False
    worker_bound_states = {
        TaskState.CLAIMED, TaskState.GATING, TaskState.EXECUTING,
        TaskState.VERIFYING, TaskState.REVIEW_PENDING, TaskState.CHANGES_REQUIRED,
        TaskState.REPAIRING, TaskState.RECOVERY_NEEDED,
    }
    if job.state in worker_bound_states:
        return job.worker_id == lease.worker_id
    return job.worker_id is None


def _typed_dispatch_policy(
    result: object, task: ParallelReadyTask, lease: WorkerLease
) -> tuple[bool, bool, str]:
    if not isinstance(result, GraphDispatchResult):
        return False, False, "DISPATCH_RESULT_UNSUPPORTED"
    if not _dispatch_job_matches_task(result, task, lease):
        return False, False, "DISPATCH_RESULT_IDENTITY_MISMATCH"
    reason = _safe_reason_code(result.reason_code, "DISPATCH_RESULT_RECONCILE_REQUIRED")
    if result.action is GraphDispatchAction.EXECUTED:
        execution = result.execution
        if execution is None:
            return False, False, "DISPATCH_EXECUTION_EVIDENCE_MISSING"
        if (
            result.job.state is TaskState.VERIFYING
            and result.job.attempt_count >= 1
            and execution.job == result.job
            and execution.success
            and not execution.recovery_required
            and execution.error_code is None
            and execution.evidence_ref is not None
        ):
            return True, True, reason
        return False, False, "DISPATCH_EXECUTION_EVIDENCE_INVALID"
    if result.action is GraphDispatchAction.EXISTING:
        if result.execution is not None:
            return False, False, "DISPATCH_NONEXECUTION_EVIDENCE_INVALID"
        if result.job.state in {TaskState.VERIFYING, TaskState.REVIEW_PENDING, TaskState.COMPLETE}:
            if result.job.attempt_count < 1:
                return False, False, "DISPATCH_EXISTING_STATE_INVALID"
            return True, True, reason
        if result.job.state in {TaskState.FAILED, TaskState.CANCELLED}:
            return False, True, reason
        return False, False, "DISPATCH_EXISTING_STATE_INVALID"
    if result.action is GraphDispatchAction.RECONCILE:
        return False, False, reason
    if result.action is GraphDispatchAction.BLOCKED:
        if result.execution is not None:
            return False, False, "DISPATCH_NONEXECUTION_EVIDENCE_INVALID"
        if result.job.state is TaskState.BLOCKED:
            return False, True, reason
        return False, False, "DISPATCH_BLOCKED_STATE_INVALID"
    if result.action is GraphDispatchAction.OFFERED:
        if result.execution is not None:
            return False, False, "DISPATCH_NONEXECUTION_EVIDENCE_INVALID"
        if result.job.state is TaskState.CLAIMED:
            return False, True, reason
        return False, False, "DISPATCH_OFFERED_STATE_INVALID"
    return False, False, "DISPATCH_ACTION_UNSUPPORTED"

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
    mapped = mapping.get(outcome.kind)
    if mapped is None:
        return ParallelReadyOutcome(
            node_id,
            ParallelReadyOutcomeKind.LEASE_RECOVERY_REQUIRED,
            "LEASE_OUTCOME_UNSUPPORTED",
            lease_outcome=outcome,
        )
    kind, reason = mapped
    return ParallelReadyOutcome(node_id, kind, reason, lease_outcome=outcome)


@dataclass(frozen=True, slots=True)
class ProviderAuthorityCheck:
    allowed: bool
    gate_refused: bool
    provider_unavailable: bool
    rate_limited: bool
    reason_code: str
    profile: ProviderConfiguration
    endpoint: ProviderEndpointConfig | None
    observation: ProviderObservation | None


def _authority_outcome(node_id: str, check: ProviderAuthorityCheck) -> ParallelReadyOutcome:
    if check.gate_refused:
        kind = ParallelReadyOutcomeKind.DISPATCH_GATE_BLOCKED
    elif check.rate_limited:
        kind = ParallelReadyOutcomeKind.PROVIDER_QUOTA_WAIT
    else:
        kind = ParallelReadyOutcomeKind.PROVIDER_WAIT
    return ParallelReadyOutcome(node_id, kind, check.reason_code)


def _validate_provider_admission_record(
    task: ParallelReadyTask, batch_id: str, admission: ProviderAdmissionRecord, now: object
) -> str | None:
    if not isinstance(admission, ProviderAdmissionRecord):
        return "PROVIDER_ADMISSION_RECORD_INVALID"
    if admission.provider_id != task.provider_profile.provider_id:
        return "PROVIDER_ADMISSION_IDENTITY_MISMATCH"
    if admission.execution_id != task.harness_dispatch.execution_id:
        return "PROVIDER_ADMISSION_IDENTITY_MISMATCH"
    if admission.batch_id != batch_id:
        return "PROVIDER_ADMISSION_IDENTITY_MISMATCH"
    if admission.status != "ACTIVE":
        return "PROVIDER_ADMISSION_NOT_ACTIVE"
    try:
        if admission.expires_at <= now:
            return "PROVIDER_ADMISSION_EXPIRED_RECONCILE"
    except (TypeError, AttributeError):
        return "PROVIDER_ADMISSION_RECORD_INVALID"
    expected = task.expected_configuration_generation
    if expected is not None and admission.configuration_generation != expected:
        return "PROVIDER_ADMISSION_GENERATION_STALE"
    return None


def _validate_provider_release_record(
    original: ProviderAdmissionRecord, released: object
) -> str | None:
    if not isinstance(released, ProviderAdmissionRecord):
        return "PROVIDER_ADMISSION_RELEASE_INVALID"
    if (
        released.admission_id != original.admission_id
        or released.provider_id != original.provider_id
        or released.execution_id != original.execution_id
        or released.batch_id != original.batch_id
        or released.configuration_generation != original.configuration_generation
        or released.status != "RELEASED"
        or released.released_at is None
    ):
        return "PROVIDER_ADMISSION_RELEASE_INVALID"
    return None


@dataclass(frozen=True, slots=True)
class ProviderAdmissionReservation:
    allowed: bool
    reason_code: str
    admission: ProviderAdmissionRecord | None = None
    capacity_wait: bool = False
    recovery_required: bool = False


class ParallelReadyExecutor:
    def __init__(
        self,
        *,
        broker: WorkerLeaseBroker,
        runner: ParallelReadyRunner,
        clock: Callable[[], object],
        provider_admission_store: ProviderAdmissionPort | None = None,
        require_provider_authority: bool = False,
    ) -> None:
        if not callable(getattr(broker, "acquire", None)):
            raise ValueError("broker must provide acquire")
        if not callable(getattr(runner, "run", None)):
            raise ValueError("runner must provide run")
        if not callable(clock):
            raise ValueError("clock must be callable")
        if not isinstance(require_provider_authority, bool):
            raise ValueError("require_provider_authority must be bool")
        if provider_admission_store is not None:
            if not callable(getattr(provider_admission_store, "acquire_admission", None)) or not callable(getattr(provider_admission_store, "release_admission", None)):
                raise ValueError("provider_admission_store must provide acquire_admission and release_admission")
        if require_provider_authority and provider_admission_store is None:
            raise ValueError("PROVIDER_AUTHORITY_REQUIRED: production execution requires provider authority")
        self._broker = broker
        self._runner = runner
        self._clock = clock
        self._provider_admission_store = provider_admission_store
        self._require_provider_authority = require_provider_authority
        self._provider_authority = None
        if provider_admission_store is not None and callable(getattr(provider_admission_store, "load_provider_snapshot", None)):
            try:
                self._provider_authority = ProviderExecutionAuthority(provider_admission_store)
            except ValueError:
                self._provider_authority = None
        if self._require_provider_authority and self._provider_authority is None:
            raise ValueError("PROVIDER_AUTHORITY_REQUIRED: provider snapshot authority missing")

    @property
    def requires_provider_authority(self) -> bool:
        return self._require_provider_authority

    @property
    def provider_authority_database_path(self):
        return None if self._provider_authority is None else self._provider_authority.database_path

    def check_provider_authority(
        self,
        *,
        profile: ProviderConfiguration,
        observation: ProviderObservation | None,
        endpoint: ProviderEndpointConfig,
        security: ProviderPolicyTaskSecurity,
        expected_generation: int,
        require_quota: bool = False,
        requirement: ProviderExecutionRequirement | None = None,
    ) -> ProviderAuthorityCheck:
        if self._provider_admission_store is None:
            return ProviderAuthorityCheck(
                False, False, True, False, "PROVIDER_AUTHORITY_STORE_MISSING",
                profile, endpoint, observation,
            )
        if requirement is not None:
            if self._provider_authority is None:
                return ProviderAuthorityCheck(False, False, True, False, "PROVIDER_AUTHORITY_STORE_MISSING", profile, endpoint, observation)
            decision = self._provider_authority.authorize(
                requirement, now=self._clock(), require_quota=require_quota
            )
            snapshot = decision.snapshot
            return ProviderAuthorityCheck(
                decision.allowed, decision.gate_refused, decision.provider_unavailable,
                decision.rate_limited, decision.reason_code,
                profile if snapshot is None else snapshot.profile,
                endpoint if snapshot is None else snapshot.endpoint,
                observation if snapshot is None else snapshot.observation,
            )
        reader = getattr(self._provider_admission_store, "load_provider_snapshot", None)
        if not callable(reader):
            return ProviderAuthorityCheck(
                False, False, True, False, "PROVIDER_AUTHORITY_SNAPSHOT_UNAVAILABLE",
                profile, endpoint, observation,
            )
        try:
            snapshot = reader(profile.provider_id)
        except Exception:
            return ProviderAuthorityCheck(
                False, False, True, False, "PROVIDER_AUTHORITY_SNAPSHOT_FAILED",
                profile, endpoint, observation,
            )
        if not isinstance(snapshot, ProviderConfigurationSnapshot):
            return ProviderAuthorityCheck(
                False, False, True, False, "PROVIDER_CONFIGURATION_UNAVAILABLE",
                profile, endpoint, observation,
            )
        if snapshot.generation != expected_generation:
            return ProviderAuthorityCheck(
                False, False, True, False, "PROVIDER_CONFIGURATION_STALE",
                snapshot.profile, snapshot.endpoint, snapshot.observation,
            )
        if snapshot.endpoint is None:
            return ProviderAuthorityCheck(
                False, False, True, False, "PROVIDER_CONFIGURATION_UNAVAILABLE",
                snapshot.profile, None, snapshot.observation,
            )
        if snapshot.profile != profile or snapshot.endpoint != endpoint:
            return ProviderAuthorityCheck(
                False, False, True, False, "PROVIDER_CONFIGURATION_DRIFT",
                snapshot.profile, snapshot.endpoint, snapshot.observation,
            )
        policy = evaluate_provider_policy(snapshot.profile, snapshot.endpoint, security)
        if not policy.allowed:
            return ProviderAuthorityCheck(
                False, True, False, False, policy.reason_code,
                snapshot.profile, snapshot.endpoint, snapshot.observation,
            )
        now = self._clock()
        if not is_provider_ready(
            snapshot.profile,
            snapshot.observation,
            now=now,
            expected_generation=expected_generation,
        ):
            return ProviderAuthorityCheck(
                False, False, True, False, "PROVIDER_NOT_READY",
                snapshot.profile, snapshot.endpoint, snapshot.observation,
            )
        if require_quota:
            quota = None if snapshot.observation is None else snapshot.observation.quota
            if quota is None or any(
                item is None
                for item in (quota.limit, quota.used, quota.remaining, quota.reset_at, quota.reset_in_seconds)
            ):
                return ProviderAuthorityCheck(
                    False, False, False, True, "PROVIDER_QUOTA_UNKNOWN",
                    snapshot.profile, snapshot.endpoint, snapshot.observation,
                )
            if quota.remaining is not None and quota.remaining <= 0:
                return ProviderAuthorityCheck(
                    False, False, False, True, "PROVIDER_QUOTA_EXHAUSTED",
                    snapshot.profile, snapshot.endpoint, snapshot.observation,
                )
        return ProviderAuthorityCheck(
            True, False, False, False, "PROVIDER_AUTHORITY_ALLOWED",
            snapshot.profile, snapshot.endpoint, snapshot.observation,
        )

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

    def reserve_provider_admission(
        self,
        *,
        node_id: str,
        provider_profile: ProviderConfiguration,
        execution_id: str,
        batch_id: str,
        ttl_seconds: int,
        requirement: ProviderExecutionRequirement,
        require_quota: bool = False,
    ) -> ProviderAdmissionReservation:
        if self._provider_admission_store is None or self._provider_authority is None:
            return ProviderAdmissionReservation(
                False, "PROVIDER_AUTHORITY_STORE_MISSING", recovery_required=True
            )
        decision = self._provider_authority.authorize(
            requirement, now=self._clock(), require_quota=require_quota
        )
        if not decision.allowed:
            return ProviderAdmissionReservation(False, decision.reason_code)
        snapshot = decision.snapshot
        if snapshot is None or snapshot.profile.provider_id != provider_profile.provider_id:
            return ProviderAdmissionReservation(
                False, "PROVIDER_CONFIGURATION_DRIFT", recovery_required=True
            )
        try:
            result = self._provider_admission_store.acquire_admission(
                provider_id=provider_profile.provider_id,
                execution_id=execution_id,
                batch_id=batch_id,
                expected_max_concurrency=snapshot.profile.max_concurrency,
                now=self._clock(),
                ttl_seconds=ttl_seconds,
                expected_configuration_generation=requirement.expected_configuration_generation,
            )
        except Exception as exc:
            return ProviderAdmissionReservation(
                False, _safe_exception_reason(exc, "PROVIDER_ADMISSION_EXCEPTION"),
                recovery_required=True,
            )
        if not isinstance(result, ProviderAdmissionResult) or not isinstance(result.kind, ProviderAdmissionKind):
            return ProviderAdmissionReservation(
                False, "PROVIDER_ADMISSION_OUTCOME_INVALID", recovery_required=True
            )
        if result.kind is ProviderAdmissionKind.CAPACITY_WAIT:
            return ProviderAdmissionReservation(
                False, _safe_reason_code(result.reason_code, "PROVIDER_CAPACITY_EXHAUSTED"),
                capacity_wait=True,
            )
        if result.kind is ProviderAdmissionKind.RECOVERY_REQUIRED:
            return ProviderAdmissionReservation(
                False, _safe_reason_code(result.reason_code, "PROVIDER_ADMISSION_RECONCILE_REQUIRED"),
                admission=result.admission, recovery_required=True,
            )
        if result.kind is ProviderAdmissionKind.EXISTING:
            return ProviderAdmissionReservation(
                False, "PROVIDER_ADMISSION_ALREADY_ACTIVE",
                admission=result.admission, recovery_required=True
            )
        if result.kind is not ProviderAdmissionKind.ADMITTED:
            return ProviderAdmissionReservation(
                False, "PROVIDER_ADMISSION_OUTCOME_UNSUPPORTED", recovery_required=True
            )
        admission = result.admission
        if not isinstance(admission, ProviderAdmissionRecord):
            return ProviderAdmissionReservation(
                False, "PROVIDER_ADMISSION_RECORD_INVALID", recovery_required=True
            )
        # A production pre-provision reservation may be re-read as EXISTING by the
        # later lease/runner stage. Exact identity + ACTIVE/non-expired generation
        # makes that reuse safe; every other EXISTING shape remains recovery.
        synthetic_task = type("_AdmissionIdentity", (), {})()
        synthetic_task.provider_profile = provider_profile
        synthetic_task.harness_dispatch = type("_DispatchIdentity", (), {"execution_id": execution_id})()
        synthetic_task.expected_configuration_generation = requirement.expected_configuration_generation
        reason = _validate_provider_admission_record(
            synthetic_task, batch_id, admission, self._clock()
        )
        if reason is not None:
            return ProviderAdmissionReservation(
                False, reason, admission=admission, recovery_required=True
            )
        return ProviderAdmissionReservation(True, "PROVIDER_ADMISSION_FENCED", admission)

    def release_reserved_provider_admission(
        self,
        *,
        provider_profile: ProviderConfiguration,
        execution_id: str,
        batch_id: str,
        admission: ProviderAdmissionRecord,
    ) -> str | None:
        if self._provider_admission_store is None:
            return "PROVIDER_AUTHORITY_STORE_MISSING"
        try:
            released = self._provider_admission_store.release_admission(
                admission.admission_id, provider_id=provider_profile.provider_id,
                execution_id=execution_id, batch_id=batch_id, now=self._clock(),
            )
        except Exception as exc:
            return _safe_exception_reason(exc, "PROVIDER_ADMISSION_RELEASE_EXCEPTION")
        return _validate_provider_release_record(admission, released)

    def _release_provider_admission(
        self,
        task: ParallelReadyTask,
        batch_id: str,
        admission: ProviderAdmissionRecord | None,
        now: object,
    ) -> str | None:
        if admission is None or self._provider_admission_store is None:
            return None
        try:
            released = self._provider_admission_store.release_admission(
                admission.admission_id,
                provider_id=task.provider_profile.provider_id,
                execution_id=task.harness_dispatch.execution_id,
                batch_id=batch_id,
                now=now,
            )
        except Exception as exc:
            return _safe_exception_reason(exc, "PROVIDER_ADMISSION_RELEASE_EXCEPTION")
        return _validate_provider_release_record(admission, released)

    def execute(
        self,
        plan: SchedulePlan,
        tasks_by_node: Mapping[str, ParallelReadyTask],
        *,
        provider_inflight: Mapping[str, int],
        batch_id: str | None = None,
        pre_acquired_admissions: Mapping[str, ProviderAdmissionRecord] | None = None,
    ) -> ParallelReadyBatchResult:
        """Execute one scheduler-owned batch against one capacity snapshot.

        This seam reserves provider capacity only inside this batch. Production assembly
        must serialize batch admission per provider, or inject ``provider_inflight`` from
        an existing atomic provider-capacity authority. Concurrent batch starts that reuse
        the same snapshot are unsupported because this module intentionally owns no second
        provider semaphore/store.
        """
        tasks = self._validate_batch(plan, tasks_by_node, provider_inflight)
        if pre_acquired_admissions is None:
            pre_acquired_admissions = {}
        elif not isinstance(pre_acquired_admissions, Mapping):
            raise ValueError("pre_acquired_admissions must be a mapping")
        if not set(pre_acquired_admissions).issubset({task.assignment.node_id for task in tasks}):
            raise ValueError("pre-acquired admission node mismatch")
        if self._provider_admission_store is not None:
            if not isinstance(batch_id, str) or not batch_id.strip():
                raise ValueError("batch_id is required with provider admission store")
            batch_id = batch_id.strip()
        now = self._clock()
        provider_batch_count: dict[str, int] = {}
        outcomes: dict[str, ParallelReadyOutcome] = {}
        runnable: list[tuple[ParallelReadyTask, WorkerLeaseOutcome, ProviderAdmissionRecord | None]] = []

        for task in tasks:
            node_id = task.assignment.node_id
            profile = task.provider_profile
            provider_id = profile.provider_id
            if self._require_provider_authority and task.provider_requirement is None:
                outcomes[node_id] = ParallelReadyOutcome(
                    node_id, ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED,
                    "PROVIDER_EXECUTION_REQUIREMENT_REQUIRED",
                )
                continue
            if not task.dispatch_gate.allowed:
                outcomes[node_id] = ParallelReadyOutcome(
                    node_id,
                    ParallelReadyOutcomeKind.DISPATCH_GATE_BLOCKED,
                    task.dispatch_gate.reason_code,
                )
                continue
            authority_enabled = task.provider_security is not None
            if authority_enabled:
                assert task.provider_endpoint is not None
                assert task.expected_configuration_generation is not None
                authority = self.check_provider_authority(
                    profile=profile,
                    observation=task.provider_observation,
                    endpoint=task.provider_endpoint,
                    security=task.provider_security,
                    expected_generation=task.expected_configuration_generation,
                    require_quota=task.require_quota,
                    requirement=task.provider_requirement,
                )
                if not authority.allowed:
                    outcomes[node_id] = _authority_outcome(node_id, authority)
                    continue
                profile = authority.profile
            else:
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

            admission = pre_acquired_admissions.get(node_id)
            if admission is not None:
                admission_reason = _validate_provider_admission_record(
                    task, batch_id or "", admission, self._clock()
                )
                if admission_reason is not None:
                    outcomes[node_id] = ParallelReadyOutcome(
                        node_id, ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED,
                        admission_reason, provider_admission=admission,
                    )
                    continue
            elif self._provider_admission_store is not None:
                try:
                    admission_result = self._provider_admission_store.acquire_admission(
                        provider_id=provider_id,
                        execution_id=task.harness_dispatch.execution_id,
                        batch_id=batch_id,
                        expected_max_concurrency=profile.max_concurrency,
                        now=now,
                        ttl_seconds=task.lease_request.lease_ttl_seconds,
                        expected_configuration_generation=task.expected_configuration_generation,
                    )
                except Exception as exc:
                    reason = _safe_exception_reason(exc, "PROVIDER_ADMISSION_EXCEPTION")
                    outcomes[node_id] = ParallelReadyOutcome(node_id, ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED, reason)
                    continue
                if not isinstance(admission_result, ProviderAdmissionResult):
                    outcomes[node_id] = ParallelReadyOutcome(node_id, ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED, "PROVIDER_ADMISSION_OUTCOME_INVALID")
                    continue
                if not isinstance(admission_result.kind, ProviderAdmissionKind):
                    outcomes[node_id] = ParallelReadyOutcome(node_id, ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED, "PROVIDER_ADMISSION_OUTCOME_UNSUPPORTED")
                    continue
                if admission_result.admission is not None and not isinstance(admission_result.admission, ProviderAdmissionRecord):
                    outcomes[node_id] = ParallelReadyOutcome(node_id, ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED, "PROVIDER_ADMISSION_RECORD_INVALID")
                    continue
                if admission_result.kind is ProviderAdmissionKind.CAPACITY_WAIT:
                    reason = _safe_reason_code(admission_result.reason_code, "PROVIDER_CAPACITY_EXHAUSTED")
                    outcomes[node_id] = ParallelReadyOutcome(node_id, ParallelReadyOutcomeKind.PROVIDER_CAPACITY_WAIT, reason)
                    continue
                if admission_result.kind in {ProviderAdmissionKind.EXISTING, ProviderAdmissionKind.RECOVERY_REQUIRED}:
                    reason = _safe_reason_code(admission_result.reason_code, "PROVIDER_ADMISSION_RECONCILE_REQUIRED")
                    outcomes[node_id] = ParallelReadyOutcome(
                        node_id, ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED,
                        reason, provider_admission=admission_result.admission,
                    )
                    continue
                admission = admission_result.admission
                if admission_result.kind is not ProviderAdmissionKind.ADMITTED or admission is None:
                    outcomes[node_id] = ParallelReadyOutcome(node_id, ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED, "PROVIDER_ADMISSION_RECORD_MISSING")
                    continue
                admission_reason = _validate_provider_admission_record(
                    task, batch_id or "", admission, self._clock()
                )
                if admission_reason is not None:
                    outcomes[node_id] = ParallelReadyOutcome(
                        node_id,
                        ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED,
                        admission_reason,
                        provider_admission=admission,
                    )
                    continue

            if authority_enabled:
                assert task.provider_endpoint is not None
                assert task.provider_security is not None
                assert task.expected_configuration_generation is not None
                pre_lease = self.check_provider_authority(
                    profile=task.provider_profile,
                    observation=task.provider_observation,
                    endpoint=task.provider_endpoint,
                    security=task.provider_security,
                    expected_generation=task.expected_configuration_generation,
                    require_quota=task.require_quota,
                    requirement=task.provider_requirement,
                )
                if not pre_lease.allowed:
                    release_reason = self._release_provider_admission(
                        task, batch_id or "", admission, self._clock()
                    )
                    if release_reason is not None:
                        outcomes[node_id] = ParallelReadyOutcome(
                            node_id,
                            ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED,
                            release_reason,
                            provider_admission=admission,
                        )
                    else:
                        outcomes[node_id] = _authority_outcome(node_id, pre_lease)
                    continue

            try:
                lease_outcome = self._broker.acquire(task.lease_request, task.candidates)
            except Exception as exc:
                outcomes[node_id] = ParallelReadyOutcome(
                    node_id,
                    ParallelReadyOutcomeKind.LEASE_RECOVERY_REQUIRED,
                    _safe_exception_reason(exc, "LEASE_ACQUIRE_EXCEPTION"),
                    provider_admission=admission,
                )
                continue
            if not isinstance(lease_outcome, WorkerLeaseOutcome):
                outcomes[node_id] = ParallelReadyOutcome(
                    node_id,
                    ParallelReadyOutcomeKind.LEASE_RECOVERY_REQUIRED,
                    "LEASE_OUTCOME_INVALID",
                    provider_admission=admission,
                )
                continue
            if lease_outcome.kind is not LeaseOutcomeKind.LEASED:
                mapped = _lease_wait_outcome(node_id, lease_outcome)
                if lease_outcome.kind in {LeaseOutcomeKind.WAIT, LeaseOutcomeKind.RDC_READ_ONLY}:
                    release_reason = self._release_provider_admission(
                        task, batch_id or "", admission, now
                    )
                    if release_reason is not None:
                        outcomes[node_id] = ParallelReadyOutcome(
                            node_id,
                            ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED,
                            release_reason,
                            lease_outcome=lease_outcome,
                            provider_admission=admission,
                        )
                        continue
                outcomes[node_id] = ParallelReadyOutcome(
                    node_id,
                    mapped.kind,
                    mapped.reason_code,
                    lease_outcome=lease_outcome,
                    provider_admission=admission,
                )
                continue
            if lease_outcome.lease is None:
                outcomes[node_id] = ParallelReadyOutcome(
                    node_id,
                    ParallelReadyOutcomeKind.LEASE_RECOVERY_REQUIRED,
                    "LEASE_RECORD_MISSING",
                    lease_outcome=lease_outcome,
                    provider_admission=admission,
                )
                continue
            if lease_outcome.lease.worker_id != task.assignment.worker_id:
                outcomes[node_id] = ParallelReadyOutcome(
                    node_id,
                    ParallelReadyOutcomeKind.LEASE_RECOVERY_REQUIRED,
                    "LEASE_WORKER_DRIFT",
                    lease_outcome=lease_outcome,
                    provider_admission=admission,
                )
                continue
            provider_batch_count[provider_id] = batch_count + 1
            runnable.append((task, lease_outcome, admission))

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
                    for task, lease_outcome, admission in runnable
                }
                for task, lease_outcome, admission in runnable:
                    node_id = task.assignment.node_id
                    try:
                        runner_result = futures[node_id].result()
                    except Exception as exc:
                        reason = _safe_exception_reason(exc, "RUNNER_EXCEPTION")
                        outcomes[node_id] = ParallelReadyOutcome(
                            node_id,
                            ParallelReadyOutcomeKind.RUNNER_RECOVERY_REQUIRED,
                            reason,
                            lease_outcome=lease_outcome,
                            provider_admission=admission,
                        )
                        continue
                    if admission is None and not isinstance(runner_result, GraphDispatchResult):
                        outcomes[node_id] = ParallelReadyOutcome(
                            node_id, ParallelReadyOutcomeKind.RUN_COMPLETED, "RUNNER_COMPLETED",
                            lease_outcome=lease_outcome, runner_result=runner_result,
                            provider_admission=None,
                        )
                        continue
                    typed_policy = _typed_dispatch_policy(runner_result, task, lease_outcome.lease)
                    if not typed_policy[0]:
                        _, release_admission, typed_reason = typed_policy
                        if release_admission:
                            release_reason = self._release_provider_admission(
                                task, batch_id or "", admission, self._clock()
                            )
                            if release_reason is not None:
                                outcomes[node_id] = ParallelReadyOutcome(
                                    node_id, ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED,
                                    release_reason, lease_outcome=lease_outcome, runner_result=runner_result,
                                    provider_admission=admission,
                                )
                                continue
                        outcomes[node_id] = ParallelReadyOutcome(
                            node_id, ParallelReadyOutcomeKind.RUNNER_RECOVERY_REQUIRED, typed_reason,
                            lease_outcome=lease_outcome, runner_result=runner_result,
                            provider_admission=admission,
                        )
                        continue
                    release_reason = self._release_provider_admission(task, batch_id or "", admission, self._clock())
                    if release_reason is not None:
                        outcomes[node_id] = ParallelReadyOutcome(node_id, ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED, release_reason, lease_outcome=lease_outcome, runner_result=runner_result, provider_admission=admission)
                        continue
                    outcomes[node_id] = ParallelReadyOutcome(
                        node_id,
                        ParallelReadyOutcomeKind.RUN_COMPLETED,
                        "RUNNER_COMPLETED",
                        lease_outcome=lease_outcome,
                        runner_result=runner_result,
                        provider_admission=admission,
                    )

        return ParallelReadyBatchResult(
            tuple(outcomes[item.node_id] for item in plan.selected)
        )
