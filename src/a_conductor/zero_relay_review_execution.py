"""WO-P1-226 / ZRA-2 — reviewer execution bridge over accepted ZRA-1 transport.

One bounded module that closes the missing reviewer-execution node:

    validated repaired-C0 task + DirectReviewRoute
      -> PURE pre-effect execution plan/fingerprint (no lease, admission,
         process, secret-value or store-mutation effect)
      -> all-equivalent fingerprint multiplicity gate (never newest-row)
      -> ONE durable launch winner through the EXISTING GraphDispatch
         lifecycle: ``ParallelReadyTask`` already enforces
         ``dispatch_request.key.job_id == harness_dispatch.execution_id ==
         route.dispatch_execution_id``, and
         ``DurableJobExecutionCoordinator.execute()`` performs the
         version-checked ``GATING -> EXECUTING`` CAS — the exclusive gate
         before any external execution. This module adds NO new lock, store,
         journal, schema or scheduler.
      -> exact READ_ONLY WorkerLease + ProviderAdmission acquisition through
         the canonical broker/store reentry contracts (deterministic batch)
      -> accepted ZRA-1 supervised ZCode assembly (review mode) with plan
         drift rejection before spawn
      -> reconcile the exact durable record set by fingerprint
      -> exact provider + WorkerLease cleanup truth per their REAL API
         contracts (provider lost-ack requires exact RELEASED reread with
         identity binding; lease release accepts only the two canonical
         boolean truth shapes)
      -> immutable ``DirectReviewExecutionHandoff`` only after execution +
         cleanup truth are proven.

Identity model (three distinct identities, cross-bound — never equated):
dispatch-context identity == GraphDispatch durable job id == admission
execution id; runtime supervised job ``job:<review_contract_ref>``; actual
``DurableExecutionRecord.execution_id``. Semantic verdict parsing belongs to
WO223/C1 and is intentionally absent here.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Protocol

from .claude_code_harness import TaskPacketFile
from .execution_deduplication import (
    ExecutionFingerprintSpec,
    compute_execution_fingerprint,
)
from .execution_record import DurableExecutionRecord, ExecutionProcessState
from .job_execution import JobBackendResult, JobExecutionContext
from .native_execution import NativeCommandResult
from .parallel_ready_execution import ParallelReadyTask
from .provider_config_store import ProviderAdmissionRecord, ProviderConfigStoreError
from .provider_configuration import HarnessStrategy
from .registry import windows_worktree_key
from .worker_lease import LeaseMutationIntent, LeaseOutcomeKind, WorkerLease
from .zero_relay_review_task import DirectReviewRoute
from .zcode_production_assembly import (
    ZCodeExecutionAuthorities,
    assemble_zcode_review_execution,
    derive_zcode_runtime_identity,
)
from .zcode_runner import ZCODE_BACKEND_ID, ZCodeTaskPacketIdentity

_LIVE_RECORD_STATES = frozenset(
    {
        ExecutionProcessState.QUEUED,
        ExecutionProcessState.STARTING,
        ExecutionProcessState.RUNNING,
        ExecutionProcessState.PROCESS_STILL_RUNNING,
    }
)
# stricter than the shared guard on purpose: a FAILED/PARTIAL/CANCELLED
# reviewer run is NOT reusable evidence here, and unknown states
# (PROCESS_EXITED_UNKNOWN_RESULT, RECOVERY_REQUIRED) stay recovery-consuming
_COMPLETED_RECORD_STATES = frozenset(
    {
        ExecutionProcessState.SUCCEEDED,
        ExecutionProcessState.FAILED,
        ExecutionProcessState.PARTIAL,
        ExecutionProcessState.CANCELLED,
        ExecutionProcessState.VERIFICATION_REQUIRED,
    }
)


class ZeroRelayReviewExecutionError(RuntimeError):
    """Stable typed failure; never echoes arbitrary input text."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ZeroRelayReviewExecutionError("REVIEW_INPUT_INVALID")
    return value.strip()


# ---------------- pure pre-effect plan ----------------


@dataclass(frozen=True, slots=True)
class ReviewerExecutionPlan:
    """Deterministic pre-effect execution plan (WO226 §5.1).

    Everything here is derived from trusted task/route/provider facts with
    ZERO side effects: no lease, no admission, no process, no secret value,
    no execution/job-store mutation.
    """

    review_contract_ref: str
    review_task_path: str
    review_task_sha256: str
    dispatch_execution_id: str
    reviewer_worker_id: str
    provider_id: str
    model_id: str
    project_id: str
    supervised_job_id: str
    batch_id: str
    operation_ref: str
    argv: tuple[str, ...]
    fingerprint_spec: ExecutionFingerprintSpec
    fingerprint: str
    timeout_seconds: int
    branch: str
    head: str
    repo_root: str


def derive_reviewer_batch_id(
    *,
    review_contract_ref: str,
    dispatch_execution_id: str,
    reviewed_head: str,
    task_sha256: str,
) -> str:
    """Deterministic versioned reviewer batch identity from trusted facts
    only — stable on exact replay, different on any identity change."""
    payload = json.dumps(
        {
            "schema": "zra2-review-batch-v1",
            "review_contract_ref": review_contract_ref,
            "dispatch_execution_id": dispatch_execution_id,
            "reviewed_head": reviewed_head.casefold(),
            "task_sha256": task_sha256.strip().lower(),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return f"zra2-review-batch-v1:{hashlib.sha256(payload).hexdigest()}"


def _snapshot_facts(provider_snapshot) -> tuple:
    profile = getattr(provider_snapshot, "profile", None)
    generation = getattr(provider_snapshot, "generation", None)
    endpoint = getattr(provider_snapshot, "endpoint", None)
    base_url = getattr(endpoint, "base_url", None) if endpoint is not None else None
    if profile is None or generation is None:
        raise ZeroRelayReviewExecutionError("REVIEW_PROVIDER_SNAPSHOT_INVALID")
    if not isinstance(base_url, str) or not base_url.strip():
        raise ZeroRelayReviewExecutionError("REVIEW_ENDPOINT_AUTHORITY_MISSING")
    return profile, int(generation), base_url.strip()


def plan_reviewer_execution(
    *,
    route: DirectReviewRoute,
    route_task: ParallelReadyTask,
    provider_snapshot,
    repo_root: str,
    executable: str,
    bundle_js: str,
    timeout_seconds: int = 300,
) -> ReviewerExecutionPlan:
    """PURE deterministic plan derivation with full route/task binding.

    Fails closed on ANY identity mismatch between route, C0 task, packet,
    lease request, dispatch request and provider snapshot — before any
    external effect exists.
    """
    if not isinstance(route, DirectReviewRoute):
        raise ZeroRelayReviewExecutionError("REVIEW_ROUTE_INVALID")
    if not isinstance(route_task, ParallelReadyTask):
        raise ZeroRelayReviewExecutionError("REVIEW_TASK_INVALID")

    dispatch = route_task.harness_dispatch
    lease_request = route_task.lease_request
    packet = route_task.task_packet
    graph_key = route_task.dispatch_request.key

    # strategy: the direct ZCode reviewer path only
    if HarnessStrategy.ZCODE_APP_SERVER not in (dispatch.harness_strategy,):
        if getattr(dispatch.harness_strategy, "value", None) != HarnessStrategy.ZCODE_APP_SERVER.value:
            raise ZeroRelayReviewExecutionError("REVIEW_STRATEGY_NOT_ZCODE")

    # route <-> task cross binding
    if route.review_contract_ref != packet.task_contract_ref or \
            route.review_contract_ref != dispatch.task_contract_ref or \
            route.review_contract_ref != lease_request.task_id:
        raise ZeroRelayReviewExecutionError("REVIEW_CONTRACT_MISMATCH")
    if route.dispatch_execution_id != dispatch.execution_id or \
            route.dispatch_execution_id != graph_key.job_id:
        raise ZeroRelayReviewExecutionError("REVIEW_DISPATCH_IDENTITY_MISMATCH")
    if route.reviewer_worker_id != route_task.assignment.worker_id:
        raise ZeroRelayReviewExecutionError("REVIEW_WORKER_MISMATCH")
    if route.provider_id != dispatch.provider_id:
        raise ZeroRelayReviewExecutionError("REVIEW_PROVIDER_MISMATCH")
    if route.model_id != dispatch.model_id:
        raise ZeroRelayReviewExecutionError("REVIEW_MODEL_MISMATCH")
    if route.project_id != dispatch.project_id or \
            route.project_id != lease_request.project_id:
        raise ZeroRelayReviewExecutionError("REVIEW_PROJECT_MISMATCH")
    repo_key = windows_worktree_key(str(repo_root))
    if windows_worktree_key(route.worktree) != repo_key or \
            windows_worktree_key(dispatch.worktree_path) != repo_key or \
            windows_worktree_key(lease_request.worktree) != repo_key:
        raise ZeroRelayReviewExecutionError("REVIEW_WORKTREE_MISMATCH")
    if route.branch != dispatch.expected_branch or route.branch != lease_request.branch:
        raise ZeroRelayReviewExecutionError("REVIEW_BRANCH_MISMATCH")
    if route.reviewed_head.casefold() != dispatch.expected_head.casefold() or \
            route.reviewed_head.casefold() != lease_request.expected_head.casefold():
        raise ZeroRelayReviewExecutionError("REVIEW_HEAD_MISMATCH")

    # READ_ONLY authority: exact intent + empty scopes on both sides
    if lease_request.mutation_intent is not LeaseMutationIntent.READ_ONLY:
        raise ZeroRelayReviewExecutionError("REVIEW_LEASE_INTENT_INVALID")
    if tuple(lease_request.mutable_scope or ()):
        raise ZeroRelayReviewExecutionError("REVIEW_LEASE_SCOPE_NOT_EMPTY")

    # verified packet identity (read-only verify; TOCTOU base re-verified at launch)
    packet_identity = ZCodeTaskPacketIdentity.from_task_packet_file(
        packet, trusted_root=str(repo_root)
    )
    if packet_identity.task_contract_ref != route.review_contract_ref:
        raise ZeroRelayReviewExecutionError("REVIEW_PACKET_CONTRACT_MISMATCH")
    if packet.sha256 != route.review_task_sha256:
        raise ZeroRelayReviewExecutionError("REVIEW_PACKET_SHA_MISMATCH")
    if windows_worktree_key(packet.path) != windows_worktree_key(route.review_task_path):
        raise ZeroRelayReviewExecutionError("REVIEW_PACKET_PATH_MISMATCH")

    # provider snapshot facts + runtime identity
    profile, generation, base_url = _snapshot_facts(provider_snapshot)
    if profile.provider_id != route.provider_id:
        raise ZeroRelayReviewExecutionError("REVIEW_PROVIDER_SNAPSHOT_MISMATCH")
    model = next(
        (m for m in profile.models if m.model_id == route.model_id), None
    )
    if model is None or model.runtime_binding is None:
        raise ZeroRelayReviewExecutionError("REVIEW_RUNTIME_BINDING_MISSING")
    binding = model.runtime_binding
    runtime_profile_ref = derive_zcode_runtime_identity(
        provider_id=profile.provider_id,
        model_id=route.model_id,
        endpoint_base_url=base_url,
        runtime_provider_ref=binding.runtime_provider_ref,
        runtime_model_ref=binding.runtime_model_ref,
        generation=generation,
    )
    if int(generation) < 1:
        raise ZeroRelayReviewExecutionError("REVIEW_PROVIDER_GENERATION_INVALID")

    # operation identity derives from the exact task identity (single
    # authority: ZCodeTaskPacketIdentity.canonical_operation_ref)
    operation_ref = packet_identity.canonical_operation_ref()
    if route_task.dispatch_request.operation_ref != operation_ref:
        raise ZeroRelayReviewExecutionError("REVIEW_OPERATION_REF_MISMATCH")

    argv = (str(executable), str(bundle_js), "app-server", "--stdio", "--surface", "desktop")
    repo_root_resolved = str(Path(str(repo_root)).expanduser().resolve(strict=False))
    spec = ExecutionFingerprintSpec(
        project_id=route.project_id,
        job_id=f"job:{route.review_contract_ref}",
        work_order_ref=route.review_contract_ref,
        backend_id=ZCODE_BACKEND_ID,
        repo_root=repo_root_resolved,
        branch=route.branch,
        head_before=route.reviewed_head.casefold(),
        operation_ref=operation_ref,
        runtime_profile_ref=runtime_profile_ref,
        target_argv=argv,
    )
    fingerprint = compute_execution_fingerprint(spec)
    batch_id = derive_reviewer_batch_id(
        review_contract_ref=route.review_contract_ref,
        dispatch_execution_id=route.dispatch_execution_id,
        reviewed_head=route.reviewed_head,
        task_sha256=packet.sha256,
    )
    timeout = int(dispatch.timeout_seconds if dispatch.timeout_seconds else timeout_seconds)
    return ReviewerExecutionPlan(
        review_contract_ref=route.review_contract_ref,
        review_task_path=packet.path,
        review_task_sha256=packet.sha256,
        dispatch_execution_id=route.dispatch_execution_id,
        reviewer_worker_id=route.reviewer_worker_id,
        provider_id=route.provider_id,
        model_id=route.model_id,
        project_id=route.project_id,
        supervised_job_id=spec.job_id,
        batch_id=batch_id,
        operation_ref=operation_ref,
        argv=argv,
        fingerprint_spec=spec,
        fingerprint=fingerprint,
        timeout_seconds=timeout,
        branch=route.branch,
        head=route.reviewed_head.casefold(),
        repo_root=repo_root_resolved,
    )


# ---------------- all-equivalent multiplicity ----------------


class EquivalenceKind(str, Enum):
    CANDIDATE_TO_LAUNCH = "CANDIDATE_TO_LAUNCH"
    REUSE_COMPLETED = "REUSE_COMPLETED"
    ATTACH_RUNNING = "ATTACH_RUNNING"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


@dataclass(frozen=True, slots=True)
class EquivalentExecutionClassification:
    kind: EquivalenceKind
    reason_code: str
    records: tuple[DurableExecutionRecord, ...]
    chosen: DurableExecutionRecord | None = None


def _record_matches_plan(record: DurableExecutionRecord, plan: ReviewerExecutionPlan) -> bool:
    spec = plan.fingerprint_spec
    return (
        record.command_fingerprint == plan.fingerprint
        and record.job_id == spec.job_id
        and record.work_order_ref == spec.work_order_ref
        and record.project_id == spec.project_id
        and record.backend_id == spec.backend_id
        and str(record.repo_root) == str(spec.repo_root)
        and record.branch == spec.branch
        and str(record.head_before).casefold() == str(spec.head_before).casefold()
        and record.operation_ref == spec.operation_ref
        and record.runtime_profile_ref == spec.runtime_profile_ref
    )


def classify_equivalent_executions(
    records,
    *,
    plan: ReviewerExecutionPlan,
    reviewer_worker_id: str,
) -> EquivalentExecutionClassification:
    """Resolve ALL equivalent fingerprint records (Astra F2 closure).

    Never consumes a single newest row: an older live equivalent must never
    be hidden by a newer completed one, and multiplicity is recovery unless
    exactly one canonical record exists. Worker equality is a separate
    mandatory binding (the fingerprint does not carry it).
    """
    seen: list[DurableExecutionRecord] = []
    for record in tuple(records or ()):
        if not isinstance(record, DurableExecutionRecord):
            return EquivalentExecutionClassification(
                EquivalenceKind.RECOVERY_REQUIRED, "EQUIVALENT_RECORD_INVALID",
                tuple(records or ()), None,
            )
        if record.command_fingerprint != plan.fingerprint or not _record_matches_plan(record, plan):
            return EquivalentExecutionClassification(
                EquivalenceKind.RECOVERY_REQUIRED, "EQUIVALENT_IDENTITY_MISMATCH",
                tuple(records or ()), None,
            )
        seen.append(record)
    if not seen:
        return EquivalentExecutionClassification(
            EquivalenceKind.CANDIDATE_TO_LAUNCH, "NO_EQUIVALENT_EXECUTION", (), None,
        )
    foreign = [r for r in seen if r.worker_id != reviewer_worker_id]
    if foreign:
        return EquivalentExecutionClassification(
            EquivalenceKind.RECOVERY_REQUIRED, "EQUIVALENT_WORKER_MISMATCH",
            tuple(seen), None,
        )
    live = [r for r in seen if r.execution_state in _LIVE_RECORD_STATES]
    completed = [r for r in seen if r.execution_state in _COMPLETED_RECORD_STATES]
    other = [r for r in seen if r.execution_state not in _LIVE_RECORD_STATES
             and r.execution_state not in _COMPLETED_RECORD_STATES]
    if other:
        return EquivalentExecutionClassification(
            EquivalenceKind.RECOVERY_REQUIRED, "EQUIVALENT_STATE_UNKNOWN",
            tuple(seen), None,
        )
    if len(seen) > 1:
        # an older RUNNING equivalent must never be hidden by a newer
        # completed row; multiple completed equivalents have no canonical
        # collapse proof either — both are typed recovery
        reason = "EQUIVALENT_MULTIPLICITY_LIVE" if live else "EQUIVALENT_MULTIPLICITY_COMPLETED"
        return EquivalentExecutionClassification(
            EquivalenceKind.RECOVERY_REQUIRED, reason, tuple(seen), None,
        )
    sole = seen[0]
    if live:
        return EquivalentExecutionClassification(
            EquivalenceKind.ATTACH_RUNNING, "EQUIVALENT_EXECUTION_ACTIVE",
            tuple(seen), sole,
        )
    if sole.execution_state in (ExecutionProcessState.SUCCEEDED,
                                ExecutionProcessState.VERIFICATION_REQUIRED):
        return EquivalentExecutionClassification(
            EquivalenceKind.REUSE_COMPLETED, "EQUIVALENT_EXECUTION_COMPLETED",
            tuple(seen), sole,
        )
    # single FAILED/PARTIAL/CANCELLED terminal record: a new attempt is NOT
    # authorized here — recovery consumption owns that decision upstream
    return EquivalentExecutionClassification(
        EquivalenceKind.RECOVERY_REQUIRED, "EQUIVALENT_TERMINAL_NOT_USABLE",
        tuple(seen), sole,
    )


# ---------------- terminal cleanup truth ----------------


def _release_admission_terminal(
    provider_store,
    *,
    admission_id: str,
    provider_id: str,
    execution_id: str,
    batch_id: str,
    now: datetime,
    expected_generation: int | None,
) -> ProviderAdmissionRecord:
    """Provider-admission cleanup per the real API contract (Astra F3).

    A repeated release may raise PROVIDER_ADMISSION_NOT_ACTIVE after a lost
    acknowledgement; that exception alone is NOT success — the exact
    admission is reread by canonical identity and only terminal RELEASED
    with matching provider/dispatch/batch (and generation when known)
    binding proves cleanup.
    """
    record: ProviderAdmissionRecord | None = None
    try:
        record = provider_store.release_admission(
            admission_id,
            provider_id=provider_id,
            execution_id=execution_id,
            batch_id=batch_id,
            now=now,
        )
    except ProviderConfigStoreError as exc:
        if exc.code != "PROVIDER_ADMISSION_NOT_ACTIVE":
            raise
        reread = provider_store.get_admission(admission_id)
        if reread is None:
            raise ZeroRelayReviewExecutionError("ADMISSION_CLEANUP_RECORD_MISSING") from exc
        if (
            reread.provider_id != provider_id
            or reread.execution_id != execution_id
            or reread.batch_id != batch_id
        ):
            raise ZeroRelayReviewExecutionError("ADMISSION_CLEANUP_IDENTITY_MISMATCH") from exc
        record = reread
    if record.status != "RELEASED":
        raise ZeroRelayReviewExecutionError("ADMISSION_NOT_RELEASED")
    if (
        expected_generation is not None
        and record.configuration_generation is not None
        and int(record.configuration_generation) != int(expected_generation)
    ):
        raise ZeroRelayReviewExecutionError("ADMISSION_CLEANUP_GENERATION_MISMATCH")
    return record


def _release_lease_terminal(
    lease_store,
    *,
    lease_id: str,
    session_id: str,
    task_id: str,
    clock: Callable[[], datetime],
):
    """WorkerLease cleanup accepts only the canonical truth shapes
    ``(released=True, already_released=False)`` or ``(False, True)`` for the
    exact lease/session/task owner; anything else is typed recovery and the
    caller must not receive a usable handoff."""
    result = lease_store.release(
        lease_id, session_id=session_id, task_id=task_id, released_at=clock()
    )
    released = getattr(result, "released", None)
    already = getattr(result, "already_released", None)
    if not isinstance(released, bool) or not isinstance(already, bool):
        raise ZeroRelayReviewExecutionError("LEASE_CLEANUP_OUTCOME_INVALID")
    if released and already:
        raise ZeroRelayReviewExecutionError("LEASE_CLEANUP_OUTCOME_CONTRADICTORY")
    if not released and not already:
        raise ZeroRelayReviewExecutionError("LEASE_CLEANUP_NOT_CONFIRMED")
    return result


# ---------------- handoff ----------------


@dataclass(frozen=True, slots=True)
class DirectReviewExecutionHandoff:
    """Immutable transport handoff (NOT semantic review evidence — C1/WO223
    owns verdict parsing).

    Preserves dispatch-context identity and the actual durable runtime
    execution identity distinctly, plus the canonical provider-admission and
    WorkerLease identities and their terminal cleanup truth.
    """

    review_contract_ref: str
    dispatch_execution_id: str
    runtime_execution_id: str
    supervised_job_id: str
    fingerprint: str
    record_version: int
    record_state: str
    stdout_ref: str
    stderr_ref: str
    result_ref: str | None
    report_ref: str | None
    task_packet_path: str
    task_packet_sha256: str
    provider_id: str
    model_id: str
    project_id: str
    worker_id: str
    repo_root: str
    branch: str
    head: str
    admission_id: str
    admission_batch_id: str
    admission_status: str
    lease_id: str
    lease_session_id: str
    lease_task_id: str
    lease_released: bool
    cleanup_terminal: bool
    exit_code: int | None
    outcome: str


# ---------------- backend (runs only for the durable CAS winner) ----------------


class ReviewerRunnerFactory(Protocol):
    def __call__(self, *, plan: ReviewerExecutionPlan, lease: WorkerLease,
                 admission: ProviderAdmissionRecord) -> object: ...


def default_reviewer_runner_factory(
    *,
    provider_snapshot,
    secret_resolver,
    execution_store,
    supervised_controller,
    supervised_observer,
    python_executable,
    workspace: str,
    deadline_seconds: float,
):
    """Build the accepted ZRA-1 review-mode assembly (real supervised path)."""

    def _factory(*, plan: ReviewerExecutionPlan, lease: WorkerLease,
                 admission: ProviderAdmissionRecord):
        authorities = ZCodeExecutionAuthorities(
            provider_snapshot=provider_snapshot,
            secret_resolver=secret_resolver,
            execution_store=execution_store,
            supervised_controller=supervised_controller,
            supervised_observer=supervised_observer,
            python_executable=python_executable,
            lease_evidence=lease,
            admission_evidence=admission,
            dispatch_batch_id=plan.batch_id,
            dispatch_execution_id=plan.dispatch_execution_id,
            project_id=plan.project_id,
            requested_mutable_scope=(),
            worker_id=plan.reviewer_worker_id,
            repo_root=plan.repo_root,
            branch=plan.branch,
            head=plan.head,
            dirty=False,
        )
        packet = TaskPacketFile(
            task_contract_ref=plan.review_contract_ref,
            path=plan.review_task_path,
            sha256=plan.review_task_sha256,
        )
        profile = getattr(provider_snapshot, "profile", None)
        return assemble_zcode_review_execution(
            authorities=authorities,
            packet=packet,
            model_id=plan.model_id,
            expected_generation=int(getattr(provider_snapshot, "generation")),
            expected_base_url=getattr(
                getattr(provider_snapshot, "endpoint", None), "base_url", ""
            ).strip(),
            secret_reference=profile.credential_ref,
            workspace=workspace,
            executable=plan.argv[0],
            bundle_js=plan.argv[1],
            deadline_seconds=deadline_seconds,
        )

    return _factory


@dataclass(frozen=True, slots=True)
class _CleanupEvidence:
    admission: ProviderAdmissionRecord | None
    lease_result: object | None


class ReviewerExecutionBackend:
    """``JobExecutionBackend`` executing ONE READ_ONLY reviewer turn.

    This code runs ONLY after the existing durable ``GATING -> EXECUTING``
    version-CAS in ``DurableJobExecutionCoordinator.execute()`` won — the
    single-winner gate. Resource acquisition, plan-drift rejection, the
    supervised run, all-equivalent reconciliation and terminal cleanup all
    happen here; a usable handoff exists only after cleanup truth.
    """

    def __init__(
        self,
        *,
        plan: ReviewerExecutionPlan,
        route_task: ParallelReadyTask,
        provider_store,
        lease_broker,
        lease_store,
        execution_store,
        runner_factory,
        secret_resolver=None,
        provider_snapshot=None,
        repo_root: str = "",
        executable: str = "",
        bundle_js: str = "",
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._plan = plan
        self._route_task = route_task
        self._provider_store = provider_store
        self._lease_broker = lease_broker
        self._lease_store = lease_store
        self._execution_store = execution_store
        self._runner_factory = runner_factory
        self._secret_resolver = secret_resolver
        self._provider_snapshot = provider_snapshot
        self._repo_root = repo_root
        self._executable = executable
        self._bundle_js = bundle_js
        self._clock = clock
        self.handoff: DirectReviewExecutionHandoff | None = None
        self.failure_code: str = ""
        self._last_lease_id: str | None = None
        self._last_admission_id: str | None = None
        self._launch_count = 0

    # -- resource acquisition through canonical reentry contracts ---------

    def _acquire_lease(self) -> WorkerLease:
        outcome = self._lease_broker.acquire(
            self._route_task.lease_request, self._route_task.candidates
        )
        if outcome.kind not in (LeaseOutcomeKind.LEASED, LeaseOutcomeKind.EXISTING):
            raise ZeroRelayReviewExecutionError("REVIEW_LEASE_NOT_ACQUIRED")
        lease = outcome.lease
        if not isinstance(lease, WorkerLease) or lease.worker_id != self._plan.reviewer_worker_id:
            raise ZeroRelayReviewExecutionError("REVIEW_LEASE_WORKER_MISMATCH")
        # canonical winner->resource association (exact-key equality)
        if lease.task_id != self._plan.review_contract_ref:
            raise ZeroRelayReviewExecutionError("REVIEW_LEASE_TASK_BINDING_MISMATCH")
        return lease

    def _acquire_admission(self, *, max_concurrency: int) -> ProviderAdmissionRecord:
        result = self._provider_store.acquire_admission(
            provider_id=self._plan.provider_id,
            execution_id=self._plan.dispatch_execution_id,
            batch_id=self._plan.batch_id,
            expected_max_concurrency=max_concurrency,
            now=self._clock(),
            ttl_seconds=max(self._plan.timeout_seconds, 60) + 300,
            expected_configuration_generation=self._expected_generation(),
        )
        kind = getattr(result, "kind", None)
        admission = getattr(result, "admission", None)
        if kind is None or admission is None:
            raise ZeroRelayReviewExecutionError("REVIEW_ADMISSION_NOT_ACQUIRED")
        kind_name = getattr(kind, "name", str(kind))
        if kind_name not in ("ADMITTED", "EXISTING"):
            raise ZeroRelayReviewExecutionError("REVIEW_ADMISSION_NOT_ACQUIRED")
        # canonical winner->resource association (exact-key equality)
        if (
            admission.provider_id != self._plan.provider_id
            or admission.execution_id != self._plan.dispatch_execution_id
            or admission.batch_id != self._plan.batch_id
        ):
            raise ZeroRelayReviewExecutionError("REVIEW_ADMISSION_BINDING_MISMATCH")
        return admission

    def _expected_generation(self) -> int:
        return int(getattr(self._provider_snapshot, "generation"))

    def _max_concurrency(self) -> int:
        profile = getattr(self._provider_snapshot, "profile", None)
        value = getattr(profile, "max_concurrency", 1) if profile is not None else 1
        return int(value) if value else 1

    def _cleanup(self, *, lease, admission) -> _CleanupEvidence:
        """Terminal cleanup of exactly the acquired resources, in the real
        API contracts; raises typed errors when truth is ambiguous."""
        admission_final: ProviderAdmissionRecord | None = None
        if admission is not None:
            admission_final = _release_admission_terminal(
                self._provider_store,
                admission_id=admission.admission_id,
                provider_id=self._plan.provider_id,
                execution_id=self._plan.dispatch_execution_id,
                batch_id=self._plan.batch_id,
                now=self._clock(),
                expected_generation=self._expected_generation(),
            )
        lease_result = None
        if lease is not None:
            lease_result = _release_lease_terminal(
                self._lease_store,
                lease_id=lease.lease_id,
                session_id=lease.session_id,
                task_id=lease.task_id,
                clock=self._clock,
            )
        return _CleanupEvidence(admission_final, lease_result)

    # -- the one bounded execution -----------------------------------------

    def execute(self, operation_ref: str, context: JobExecutionContext) -> JobBackendResult:
        from .domain import RecoveryClassification

        plan = self._plan
        if operation_ref != plan.operation_ref:
            self.failure_code = "REVIEW_OPERATION_MISMATCH"
            return JobBackendResult(
                success=False,
                recovery_classification=RecoveryClassification.UNKNOWN,
                error_code=self.failure_code,
            )
        if (
            context.job_id != plan.dispatch_execution_id
            or context.worker_id != plan.reviewer_worker_id
            or context.work_order_ref != plan.review_contract_ref
            or context.project_id != plan.project_id
        ):
            self.failure_code = "REVIEW_CONTEXT_MISMATCH"
            return JobBackendResult(
                success=False,
                recovery_classification=RecoveryClassification.UNKNOWN,
                error_code=self.failure_code,
            )

        lease = None
        admission = None
        try:
            lease = self._acquire_lease()
            self._last_lease_id = lease.lease_id
            admission = self._acquire_admission(max_concurrency=self._max_concurrency())
            self._last_admission_id = admission.admission_id

            runner = self._runner_factory(
                plan=plan, lease=lease, admission=admission,
                execution_store=self._execution_store,
            )
            spec_method = getattr(runner, "execution_fingerprint_spec", None)
            if not callable(spec_method):
                self.failure_code = "REVIEW_RUNNER_SEAM_INVALID"
                raise ZeroRelayReviewExecutionError(self.failure_code)
            if spec_method() != plan.fingerprint_spec:
                self.failure_code = "REVIEW_PLAN_DRIFT"
                raise ZeroRelayReviewExecutionError(self.failure_code)

            pre = self._execution_store.find_by_fingerprint(plan.fingerprint)
            pre_class = classify_equivalent_executions(
                pre, plan=plan, reviewer_worker_id=plan.reviewer_worker_id
            )
            if pre_class.kind is not EquivalenceKind.CANDIDATE_TO_LAUNCH:
                # an equivalent appeared between preflight and the winner CAS:
                # never launch a second child over it
                self.failure_code = f"REVIEW_PRE_LAUNCH_{pre_class.kind.value}"
                raise ZeroRelayReviewExecutionError(self.failure_code)

            self._launch_count += 1
            result = runner.run(timeout_seconds=plan.timeout_seconds)
            if not isinstance(result, NativeCommandResult):
                self.failure_code = "REVIEW_RUN_RESULT_INVALID"
                raise ZeroRelayReviewExecutionError(self.failure_code)

            post = self._execution_store.find_by_fingerprint(plan.fingerprint)
            post_class = classify_equivalent_executions(
                post, plan=plan, reviewer_worker_id=plan.reviewer_worker_id
            )
            if post_class.kind is EquivalenceKind.RECOVERY_REQUIRED or post_class.chosen is None:
                self.failure_code = f"REVIEW_POST_RUN_{post_class.reason_code}"
                raise ZeroRelayReviewExecutionError(self.failure_code)
            chosen = post_class.chosen

            cleanup = self._cleanup(lease=lease, admission=admission)
            lease = None
            admission = None

            terminal_ok = chosen.execution_state in (
                ExecutionProcessState.SUCCEEDED,
                ExecutionProcessState.VERIFICATION_REQUIRED,
            )
            exit_ok = result.exit_code is not None and result.exit_code == 0
            self.handoff = DirectReviewExecutionHandoff(
                review_contract_ref=plan.review_contract_ref,
                dispatch_execution_id=plan.dispatch_execution_id,
                runtime_execution_id=chosen.execution_id,
                supervised_job_id=plan.supervised_job_id,
                fingerprint=plan.fingerprint,
                record_version=int(chosen.version),
                record_state=chosen.execution_state.value,
                stdout_ref=chosen.stdout_ref,
                stderr_ref=chosen.stderr_ref,
                result_ref=chosen.result_ref,
                report_ref=chosen.report_ref,
                task_packet_path=plan.review_task_path,
                task_packet_sha256=plan.review_task_sha256,
                provider_id=plan.provider_id,
                model_id=plan.model_id,
                project_id=plan.project_id,
                worker_id=plan.reviewer_worker_id,
                repo_root=plan.repo_root,
                branch=plan.branch,
                head=plan.head,
                admission_id=cleanup.admission.admission_id,
                admission_batch_id=cleanup.admission.batch_id,
                admission_status=cleanup.admission.status,
                lease_id=self._last_lease_id or "",
                lease_session_id=self._route_task.lease_request.session_id,
                lease_task_id=plan.review_contract_ref,
                lease_released=True,
                cleanup_terminal=True,
                exit_code=result.exit_code,
                outcome="EXECUTED",
            )
            if terminal_ok and exit_ok:
                return JobBackendResult(
                    success=True,
                    evidence_ref=f"zra2-review-execution:{chosen.execution_id}",
                )
            self.failure_code = f"REVIEW_RUN_TERMINAL_{chosen.execution_state.value}"
            return JobBackendResult(
                success=False,
                recovery_classification=RecoveryClassification.UNKNOWN,
                error_code=self.failure_code,
            )
        except ZeroRelayReviewExecutionError:
            self._cleanup_best_effort(lease=lease, admission=admission)
            return JobBackendResult(
                success=False,
                recovery_classification=RecoveryClassification.UNKNOWN,
                error_code=self.failure_code or "REVIEW_EXECUTION_FAILED",
            )
        except Exception as exc:  # runner/store faults: fail closed + cleanup
            self._cleanup_best_effort(lease=lease, admission=admission)
            code = getattr(exc, "code", None)
            self.failure_code = (
                code if isinstance(code, str) and code else "REVIEW_BACKEND_FAULT"
            )
            return JobBackendResult(
                success=False,
                recovery_classification=RecoveryClassification.UNKNOWN,
                error_code=self.failure_code,
            )

    def _cleanup_best_effort(self, *, lease, admission) -> None:
        """Cleanup after a failed attempt: the resources acquired by THIS
        attempt must not leak. Cleanup truth failures are surfaced, never
        swallowed — but they must not mask the primary failure code."""
        try:
            self._cleanup(lease=lease, admission=admission)
        except Exception as exc:  # noqa: BLE001 - evidence retained
            code = getattr(exc, "code", None)
            suffix = code if isinstance(code, str) and code else "UNKNOWN"
            self.failure_code = f"{self.failure_code or 'REVIEW_FAILED'}+CLEANUP_{suffix}"


# ---------------- replay/reconciliation (no new model effect) -------------


@dataclass(frozen=True, slots=True)
class ReviewerExecutionResult:
    outcome: str  # EXECUTED / REUSE_COMPLETED / ATTACH_RUNNING /
    #             RECOVERY_REQUIRED / NOT_ATTEMPTED_CLEANED / REFUSED
    reason_code: str
    handoff: DirectReviewExecutionHandoff | None = None
    dispatch_action: str | None = None


def _cleanup_only_handoff(
    *,
    plan: ReviewerExecutionPlan,
    chosen: DurableExecutionRecord,
    session_id: str,
    lease_id: str,
    cleanup: _CleanupEvidence,
    exit_code: int | None,
) -> DirectReviewExecutionHandoff:
    return DirectReviewExecutionHandoff(
        review_contract_ref=plan.review_contract_ref,
        dispatch_execution_id=plan.dispatch_execution_id,
        runtime_execution_id=chosen.execution_id,
        supervised_job_id=plan.supervised_job_id,
        fingerprint=plan.fingerprint,
        record_version=int(chosen.version),
        record_state=chosen.execution_state.value,
        stdout_ref=chosen.stdout_ref,
        stderr_ref=chosen.stderr_ref,
        result_ref=chosen.result_ref,
        report_ref=chosen.report_ref,
        task_packet_path=plan.review_task_path,
        task_packet_sha256=plan.review_task_sha256,
        provider_id=plan.provider_id,
        model_id=plan.model_id,
        project_id=plan.project_id,
        worker_id=plan.reviewer_worker_id,
        repo_root=plan.repo_root,
        branch=plan.branch,
        head=plan.head,
        admission_id=cleanup.admission.admission_id if cleanup.admission else "",
        admission_batch_id=cleanup.admission.batch_id if cleanup.admission else "",
        admission_status=cleanup.admission.status if cleanup.admission else "",
        lease_id=lease_id,
        lease_session_id=session_id,
        lease_task_id=plan.review_contract_ref,
        lease_released=True,
        cleanup_terminal=True,
        exit_code=exit_code,
        outcome="REUSE_COMPLETED",
    )


def _reconcile_cleanup(
    *,
    provider_store,
    lease,
    admission,
    lease_store,
    clock: Callable[[], datetime],
) -> _CleanupEvidence:
    """Terminal cleanup of resources reconstructed by exact-key reentry."""
    admission_final = None
    if admission is not None:
        admission_final = _release_admission_terminal(
            provider_store,
            admission_id=admission.admission_id,
            provider_id=admission.provider_id,
            execution_id=admission.execution_id,
            batch_id=admission.batch_id,
            now=clock(),
            expected_generation=None,
        )
    lease_result = None
    if lease is not None:
        lease_result = _release_lease_terminal(
            lease_store, lease_id=lease.lease_id, session_id=lease.session_id,
            task_id=lease.task_id, clock=clock,
        )
    return _CleanupEvidence(admission_final, lease_result)


def reconcile_review_execution(
    *,
    plan: ReviewerExecutionPlan,
    route_task: ParallelReadyTask,
    provider_store,
    lease_broker,
    lease_store,
    execution_store,
    clock: Callable[[], datetime],
    max_concurrency: int = 1,
    expected_generation: int | None = None,
) -> ReviewerExecutionResult:
    """Reconcile a completed equivalent WITHOUT any new model/launch/acquire
    model effect (exact cleanup/reconcile effects are still performed)."""
    records = execution_store.find_by_fingerprint(plan.fingerprint)
    classification = classify_equivalent_executions(
        records, plan=plan, reviewer_worker_id=plan.reviewer_worker_id
    )
    if classification.kind is EquivalenceKind.ATTACH_RUNNING:
        return ReviewerExecutionResult("ATTACH_RUNNING", classification.reason_code)
    if classification.kind is EquivalenceKind.RECOVERY_REQUIRED:
        return ReviewerExecutionResult("RECOVERY_REQUIRED", classification.reason_code)
    chosen = classification.chosen
    if chosen is None:
        return ReviewerExecutionResult("RECOVERY_REQUIRED", "EQUIVALENT_CHOSEN_MISSING")
    # cleanup-only: reconstruct held resources by exact reentry and release
    outcome = lease_broker.acquire(route_task.lease_request, route_task.candidates)
    lease = outcome.lease if outcome.kind in (
        LeaseOutcomeKind.LEASED, LeaseOutcomeKind.EXISTING,
    ) and isinstance(outcome.lease, WorkerLease) else None
    admission_result = provider_store.acquire_admission(
        provider_id=plan.provider_id,
        execution_id=plan.dispatch_execution_id,
        batch_id=plan.batch_id,
        expected_max_concurrency=max_concurrency,
        now=clock(),
        ttl_seconds=max(plan.timeout_seconds, 60) + 300,
        expected_configuration_generation=expected_generation,
    )
    admission = getattr(admission_result, "admission", None)
    cleanup = _reconcile_cleanup(
        provider_store=provider_store, lease=lease, admission=admission,
        lease_store=lease_store, clock=clock,
    )
    handoff = _cleanup_only_handoff(
        plan=plan, chosen=chosen,
        session_id=route_task.lease_request.session_id,
        lease_id=lease.lease_id if lease is not None else "",
        cleanup=cleanup, exit_code=None,
    )
    return ReviewerExecutionResult("REUSE_COMPLETED", classification.reason_code,
                                   handoff=handoff)


# ---------------- top-level one-attempt dispatch ----------------


def execute_review_dispatch(
    *,
    route: DirectReviewRoute,
    route_task: ParallelReadyTask,
    provider_snapshot,
    provider_store,
    lease_broker,
    lease_store,
    execution_store,
    job_store,
    runner_factory,
    secret_resolver=None,
    repo_root: str = "",
    executable: str = "",
    bundle_js: str = "",
    clock: Callable[[], datetime] = _utc_now,
) -> ReviewerExecutionResult:
    """One bounded reviewer execution attempt over the repaired C0 route.

    Preflight is pure; the durable GraphDispatch lifecycle provides the
    single-winner CAS; replay paths reconcile by exact identity and never
    repeat the model call.
    """
    from .graph.dispatch import (
        GraphDispatchAction,
        GraphDispatchCoordinator,
        StaticWorkerDispatchModeResolver,
    )
    from .job_execution import DurableJobExecutionCoordinator
    from .job_control import DurableJobControlService

    plan = plan_reviewer_execution(
        route=route,
        route_task=route_task,
        provider_snapshot=provider_snapshot,
        repo_root=repo_root,
        executable=executable,
        bundle_js=bundle_js,
        timeout_seconds=getattr(route_task.harness_dispatch, "timeout_seconds", 300) or 300,
    )
    profile, generation, base_url = _snapshot_facts(provider_snapshot)
    max_concurrency = int(getattr(profile, "max_concurrency", 1) or 1)

    # provider drift preflight: the plan was derived from THIS snapshot, so
    # the canonical store must still serve the exact same generation and
    # endpoint authority before anything is dispatched (TOCTOU narrowing;
    # the admission acquire re-checks the generation again inside its
    # transaction).
    current_snapshot = provider_store.load_provider_snapshot(plan.provider_id)
    if (
        current_snapshot is None
        or int(getattr(current_snapshot, "generation", -1)) != int(generation)
        or str(getattr(getattr(current_snapshot, "endpoint", None), "base_url", "")).strip()
        != base_url
    ):
        return ReviewerExecutionResult(
            "RECOVERY_REQUIRED", "REVIEW_PROVIDER_GENERATION_DRIFT"
        )

    equivalents = classify_equivalent_executions(
        execution_store.find_by_fingerprint(plan.fingerprint),
        plan=plan,
        reviewer_worker_id=plan.reviewer_worker_id,
    )
    if equivalents.kind is EquivalenceKind.RECOVERY_REQUIRED:
        return ReviewerExecutionResult("RECOVERY_REQUIRED", equivalents.reason_code)
    if equivalents.kind is EquivalenceKind.ATTACH_RUNNING:
        return ReviewerExecutionResult("ATTACH_RUNNING", equivalents.reason_code)
    if equivalents.kind is EquivalenceKind.REUSE_COMPLETED:
        # completed equivalent: cleanup/reconcile only, NO new model effect
        return reconcile_review_execution(
            plan=plan,
            route_task=route_task,
            provider_store=provider_store,
            lease_broker=lease_broker,
            lease_store=lease_store,
            execution_store=execution_store,
            clock=clock,
            max_concurrency=max_concurrency,
            expected_generation=generation,
        )

    # CANDIDATE_TO_LAUNCH: the ONLY launch path is through the existing
    # durable GraphDispatch lifecycle (single-winner CAS)
    backend = ReviewerExecutionBackend(
        plan=plan,
        route_task=route_task,
        provider_store=provider_store,
        lease_broker=lease_broker,
        lease_store=lease_store,
        execution_store=execution_store,
        runner_factory=runner_factory,
        secret_resolver=secret_resolver,
        provider_snapshot=provider_snapshot,
        repo_root=repo_root,
        executable=executable,
        bundle_js=bundle_js,
        clock=clock,
    )
    service = DurableJobControlService(
        store=job_store,
        coordinator=DurableJobExecutionCoordinator(store=job_store, backend=backend),
    )
    coordinator = GraphDispatchCoordinator(
        service=service,
        mode_resolver=StaticWorkerDispatchModeResolver(
            {plan.reviewer_worker_id: _programmatic_push()}
        ),
    )
    dispatch_result = coordinator.dispatch(
        route_task.dispatch_request, gate=route_task.dispatch_gate
    )
    action = dispatch_result.action
    if action is GraphDispatchAction.EXECUTED:
        if backend.handoff is not None:
            return ReviewerExecutionResult(
                "EXECUTED", dispatch_result.reason_code, handoff=backend.handoff,
                dispatch_action=action.value,
            )
        return ReviewerExecutionResult(
            "RECOVERY_REQUIRED", backend.failure_code or "REVIEW_BACKEND_NO_HANDOFF",
            dispatch_action=action.value,
        )
    if action is GraphDispatchAction.EXISTING:
        job_state = dispatch_result.job.state.value
        if job_state in ("VERIFYING", "REVIEW_PENDING", "COMPLETE"):
            return reconcile_review_execution(
                plan=plan,
                route_task=route_task,
                provider_store=provider_store,
                lease_broker=lease_broker,
                lease_store=lease_store,
                execution_store=execution_store,
                clock=clock,
                max_concurrency=max_concurrency,
                expected_generation=generation,
            )
        return ReviewerExecutionResult(
            "RECOVERY_REQUIRED", f"DISPATCH_EXISTING_{job_state}",
            dispatch_action=action.value,
        )
    if action is GraphDispatchAction.RECONCILE:
        # mid-lifecycle job (e.g. EXECUTING from a crashed attempt): consume
        # recovery, never launch a second child
        records = execution_store.find_by_fingerprint(plan.fingerprint)
        classification = classify_equivalent_executions(
            records, plan=plan, reviewer_worker_id=plan.reviewer_worker_id
        )
        if classification.kind is EquivalenceKind.REUSE_COMPLETED:
            return reconcile_review_execution(
                plan=plan,
                route_task=route_task,
                provider_store=provider_store,
                lease_broker=lease_broker,
                lease_store=lease_store,
                execution_store=execution_store,
                clock=clock,
                max_concurrency=max_concurrency,
                expected_generation=generation,
            )
        # the backend's own typed failure (when it ran) is the true reason
        reason = backend.failure_code or dispatch_result.reason_code
        if classification.kind is EquivalenceKind.ATTACH_RUNNING:
            reason = classification.reason_code
        elif classification.records and not backend.failure_code:
            reason = classification.reason_code
        if not classification.records:
            # crashed attempt left resources without any execution record:
            # clean them by exact reentry, then report not-attempted
            cleaned = _cleanup_held_resources_without_record(
                plan=plan, route_task=route_task, provider_store=provider_store,
                lease_broker=lease_broker, lease_store=lease_store,
                expected_generation=generation, max_concurrency=max_concurrency,
                clock=clock,
            )
            if cleaned:
                return ReviewerExecutionResult(
                    "NOT_ATTEMPTED_CLEANED", reason,
                    dispatch_action=action.value,
                )
        return ReviewerExecutionResult(
            "RECOVERY_REQUIRED", reason, dispatch_action=action.value,
        )
    # BLOCKED / OFFERED: typed refusal, nothing acquired
    return ReviewerExecutionResult(
        "REFUSED", dispatch_result.reason_code, dispatch_action=action.value,
    )


def _programmatic_push():
    from .graph.dispatch import GraphDispatchMode

    return GraphDispatchMode.PROGRAMMATIC_PUSH


def _cleanup_held_resources_without_record(
    *,
    plan: ReviewerExecutionPlan,
    route_task: ParallelReadyTask,
    provider_store,
    lease_broker,
    lease_store,
    expected_generation: int | None,
    max_concurrency: int,
    clock: Callable[[], datetime],
) -> bool:
    """After a crashed attempt with no durable execution record: the exact
    reentry keys either resolve the held resources (release them) or prove
    nothing was held. Returns True when cleanup was achieved."""
    lease = None
    admission = None
    try:
        outcome = lease_broker.acquire(route_task.lease_request, route_task.candidates)
        if outcome.kind in (LeaseOutcomeKind.LEASED, LeaseOutcomeKind.EXISTING) and \
                isinstance(outcome.lease, WorkerLease):
            lease = outcome.lease
    except Exception:  # noqa: BLE001 - absence means not-held
        lease = None
    try:
        result = provider_store.acquire_admission(
            provider_id=plan.provider_id,
            execution_id=plan.dispatch_execution_id,
            batch_id=plan.batch_id,
            expected_max_concurrency=max_concurrency,
            now=clock(),
            ttl_seconds=max(plan.timeout_seconds, 60) + 300,
            expected_configuration_generation=expected_generation,
        )
        admission = getattr(result, "admission", None)
    except Exception:  # noqa: BLE001 - absence means not-held
        admission = None
    try:
        _reconcile_cleanup(
            provider_store=provider_store, lease=lease, admission=admission,
            lease_store=lease_store, clock=clock,
        )
        return True
    except Exception:  # noqa: BLE001 - ambiguous cleanup stays recovery
        return False
