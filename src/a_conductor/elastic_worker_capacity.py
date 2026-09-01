"""Policy-bounded elastic worker expansion above the existing lease broker.

The coordinator owns no scheduler, worker registry, lifecycle implementation,
connector allocator, or retry loop. Provisioning reservations are stored in the
same SQLite file owned by ``SQLiteWorkerLeaseStore`` so independent processes
serialize one worker-capacity authority. Ambiguous provisioning consumes a slot
until explicit reconciliation; it is never retried blindly.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Mapping, Protocol

from .graph.domain import TaskGraph
from .graph.ready import ReadySetResult
from .graph.scheduler import (
    BlockedReasonKind,
    NodeEligibility,
    SchedulePlan,
    SchedulePolicy,
    schedule_once,
)
from .parallel_ready_execution import (
    ParallelReadyBatchResult,
    ParallelReadyExecutor,
    ParallelReadyOutcomeKind,
)
from .worker_candidate_assembly import (
    ParallelReadyNodeContract,
    WorkerSupplyRecord,
    WorkerSupplySnapshot,
    assemble_parallel_ready_tasks,
)
from .worker_lease import (
    LeaseOutcomeKind,
    SQLiteWorkerLeaseStore,
    WorkerLeaseBroker,
    WorkerLeaseOutcome,
    WorkerLeaseRequest,
    WorkerProvisioningReservationKind,
    WorkerProvisioningReservationRecord,
    WorkerProvisioningReservationResult,
)


class ElasticCapacityError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _text(value: str, field_name: str, *, max_length: int = 256) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    cleaned = value.strip()
    if len(cleaned) > max_length or any(ch in cleaned for ch in "\x00\r\n"):
        raise ValueError(f"{field_name} is invalid")
    return cleaned


def _optional_text(
    value: str | None,
    field_name: str,
    *,
    max_length: int = 256,
) -> str | None:
    if value is None:
        return None
    return _text(value, field_name, max_length=max_length)


def _safe_reason_code(value: object, fallback: str) -> str:
    if (
        isinstance(value, str)
        and value
        and len(value) <= 128
        and all(ch.isalnum() or ch in "._:-" for ch in value)
    ):
        return value
    return fallback


def _timestamp(value: object, field_name: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError(f"{field_name} must be timezone-aware")
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        )
    text = _text(value, field_name, max_length=64)  # type: ignore[arg-type]
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


@dataclass(frozen=True, slots=True)
class ElasticCapacityPolicy:
    enabled: bool
    max_extra_workers: int
    permitted_runtime_kinds: tuple[str, ...]
    allow_remote_connector: bool = False
    transport_authorization_ref: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool) or not isinstance(self.allow_remote_connector, bool):
            raise ValueError("elastic policy booleans are invalid")
        if (
            not isinstance(self.max_extra_workers, int)
            or isinstance(self.max_extra_workers, bool)
            or self.max_extra_workers < 0
            or self.max_extra_workers > 99
        ):
            raise ValueError("max_extra_workers must be between 0 and 99")
        if isinstance(self.permitted_runtime_kinds, (str, bytes)):
            raise ValueError("permitted_runtime_kinds must be a sequence")
        kinds = tuple(
            _text(item, "runtime_kind", max_length=128)
            for item in self.permitted_runtime_kinds
        )
        if len(set(kinds)) != len(kinds):
            raise ValueError("permitted_runtime_kinds must not contain duplicates")
        object.__setattr__(self, "permitted_runtime_kinds", kinds)
        object.__setattr__(
            self,
            "transport_authorization_ref",
            _optional_text(
                self.transport_authorization_ref,
                "transport_authorization_ref",
                max_length=256,
            ),
        )


ProvisioningReservationKind = WorkerProvisioningReservationKind
ProvisioningReservationRecord = WorkerProvisioningReservationRecord
ProvisioningReservationResult = WorkerProvisioningReservationResult


def _reservation_store_error_code(code: str) -> str:
    return {
        "PROVISIONING_RESERVATION_DATA_INVALID": "PROVISIONING_RECORD_INVALID",
    }.get(code, code)


class SQLiteWorkerProvisioningReservations:
    """Compatibility adapter over the existing SQLiteWorkerLeaseStore authority."""

    def __init__(self, lease_store: SQLiteWorkerLeaseStore) -> None:
        if not isinstance(lease_store, SQLiteWorkerLeaseStore):
            raise ValueError("lease_store must be SQLiteWorkerLeaseStore")
        self._lease_store = lease_store
        self.database_path = lease_store.database_path

    def acquire(
        self,
        *,
        reservation_id: str,
        session_id: str,
        task_id: str,
        runtime_kind: str,
        max_extra_workers: int,
        now: object,
        project_id: str | None = None,
        worktree: str | None = None,
        mutable_scope: tuple[str, ...] = (),
    ) -> ProvisioningReservationResult:
        try:
            return self._lease_store.acquire_provisioning_reservation(
                reservation_id=reservation_id,
                session_id=session_id,
                task_id=task_id,
                runtime_kind=runtime_kind,
                max_extra_workers=max_extra_workers,
                now=now,
                project_id=project_id,
                worktree=worktree,
                mutable_scope=mutable_scope,
            )
        except Exception as exc:
            if isinstance(exc, ElasticCapacityError):
                raise
            code = getattr(exc, "code", None)
            if isinstance(code, str) and code:
                raise ElasticCapacityError(_reservation_store_error_code(code)) from exc
            raise

    def _transition(
        self,
        reservation_id: str,
        *,
        session_id: str,
        task_id: str,
        state: str,
        now: object,
        worker_id: str | None = None,
    ) -> ProvisioningReservationRecord:
        try:
            return self._lease_store.transition_provisioning_reservation(
                reservation_id,
                session_id=session_id,
                task_id=task_id,
                state=state,
                now=now,
                worker_id=worker_id,
            )
        except Exception as exc:
            code = getattr(exc, "code", None)
            if isinstance(code, str) and code:
                raise ElasticCapacityError(_reservation_store_error_code(code)) from exc
            raise

    def mark_provisioning_started(
        self,
        reservation_id: str,
        *,
        session_id: str,
        task_id: str,
        now: object,
    ) -> ProvisioningReservationRecord:
        return self._transition(
            reservation_id,
            session_id=session_id,
            task_id=task_id,
            state="PROVISIONING",
            now=now,
        )

    def mark_provisioned(
        self,
        reservation_id: str,
        *,
        session_id: str,
        task_id: str,
        worker_id: str,
        now: object,
    ) -> ProvisioningReservationRecord:
        return self._transition(
            reservation_id,
            session_id=session_id,
            task_id=task_id,
            state="PROVISIONED",
            worker_id=worker_id,
            now=now,
        )

    def mark_capacity(
        self,
        reservation_id: str,
        *,
        session_id: str,
        task_id: str,
        worker_id: str,
        now: object,
    ) -> ProvisioningReservationRecord:
        return self._transition(
            reservation_id,
            session_id=session_id,
            task_id=task_id,
            state="CAPACITY",
            worker_id=worker_id,
            now=now,
        )

    def mark_recovery(
        self,
        reservation_id: str,
        *,
        session_id: str,
        task_id: str,
        now: object,
        worker_id: str | None = None,
    ) -> ProvisioningReservationRecord:
        return self._transition(
            reservation_id,
            session_id=session_id,
            task_id=task_id,
            state="RECOVERY_REQUIRED",
            worker_id=worker_id,
            now=now,
        )

    def release_unstarted(
        self,
        reservation_id: str,
        *,
        session_id: str,
        task_id: str,
        now: object,
    ) -> ProvisioningReservationRecord:
        return self._transition(
            reservation_id,
            session_id=session_id,
            task_id=task_id,
            state="RELEASED",
            now=now,
        )

    def list_consuming(self) -> tuple[ProvisioningReservationRecord, ...]:
        try:
            return self._lease_store.list_provisioning_reservations(consuming_only=True)
        except Exception as exc:
            code = getattr(exc, "code", None)
            if isinstance(code, str) and code:
                raise ElasticCapacityError(_reservation_store_error_code(code)) from exc
            raise

    def reconcile_stale(
        self,
        reservation_id: str,
        *,
        session_id: str,
        task_id: str,
        now: object,
        stale_after_seconds: int,
    ) -> ProvisioningReservationRecord:
        try:
            return self._lease_store.reconcile_stale_provisioning(
                reservation_id,
                session_id=session_id,
                task_id=task_id,
                now=now,
                stale_after_seconds=stale_after_seconds,
            )
        except Exception as exc:
            code = getattr(exc, "code", None)
            if isinstance(code, str) and code:
                raise ElasticCapacityError(_reservation_store_error_code(code)) from exc
            raise


@dataclass(frozen=True, slots=True)
class ElasticProvisionRequest:
    session_id: str
    task_id: str
    project_id: str
    runtime_kind: str
    worktree: str
    branch: str
    expected_head: str
    required_capabilities: tuple[str, ...]
    remote_connector_allowed: bool = False
    transport_authorization_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "session_id", _text(self.session_id, "session_id"))
        object.__setattr__(self, "task_id", _text(self.task_id, "task_id"))
        object.__setattr__(self, "project_id", _text(self.project_id, "project_id"))
        object.__setattr__(
            self,
            "runtime_kind",
            _text(self.runtime_kind, "runtime_kind", max_length=128),
        )
        object.__setattr__(self, "worktree", _text(self.worktree, "worktree", max_length=512))
        object.__setattr__(self, "branch", _text(self.branch, "branch", max_length=256))
        object.__setattr__(self, "expected_head", _text(self.expected_head, "expected_head", max_length=64))
        if isinstance(self.required_capabilities, (str, bytes)):
            raise ValueError("required_capabilities must be a sequence")
        capabilities = tuple(
            _text(item, "required_capability", max_length=128)
            for item in self.required_capabilities
        )
        object.__setattr__(self, "required_capabilities", capabilities)
        if not isinstance(self.remote_connector_allowed, bool):
            raise ValueError("remote_connector_allowed must be bool")
        object.__setattr__(
            self,
            "transport_authorization_ref",
            _optional_text(
                self.transport_authorization_ref,
                "transport_authorization_ref",
                max_length=256,
            ),
        )


@dataclass(frozen=True, slots=True)
class ElasticProvisionedWorker:
    worker_id: str
    runtime_kind: str
    remote_connector_configured: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "worker_id", _text(self.worker_id, "worker_id"))
        object.__setattr__(
            self,
            "runtime_kind",
            _text(self.runtime_kind, "runtime_kind", max_length=128),
        )
        if not isinstance(self.remote_connector_configured, bool):
            raise ValueError("remote_connector_configured must be bool")


class ElasticWorkerProvisioner(Protocol):
    def provision(self, request: ElasticProvisionRequest) -> ElasticProvisionedWorker: ...


class WorkerSupplyAssemblerPort(Protocol):
    def assemble(self, worker_id: str) -> WorkerSupplyRecord: ...

    def assemble_for_owner(
        self, worker_id: str, *, session_id: str, task_id: str
    ) -> WorkerSupplyRecord: ...


class ElasticCapacityOutcomeKind(str, Enum):
    PROVISIONED_READY = "PROVISIONED_READY"
    PROVISIONED_AND_LEASED = "PROVISIONED_AND_LEASED"
    POLICY_DISABLED = "POLICY_DISABLED"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    NOT_CAPACITY_FAILURE = "NOT_CAPACITY_FAILURE"
    LIMIT_WAIT = "LIMIT_WAIT"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


@dataclass(frozen=True, slots=True)
class ElasticCapacityOutcome:
    kind: ElasticCapacityOutcomeKind
    reason_code: str
    reservation_id: str | None = None
    worker_id: str | None = None
    supply: WorkerSupplyRecord | None = None
    lease_outcome: WorkerLeaseOutcome | None = None


def _capacity_only(plan: SchedulePlan) -> bool:
    if not plan.blocked:
        return False
    return all(
        item.kind in {BlockedReasonKind.CAPACITY, BlockedReasonKind.NO_WORKERS}
        for item in plan.blocked
    )


class ElasticWorkerCapacityCoordinator:
    def __init__(
        self,
        *,
        broker: WorkerLeaseBroker,
        reservations: SQLiteWorkerProvisioningReservations,
        provisioner: ElasticWorkerProvisioner,
        candidate_assembler: WorkerSupplyAssemblerPort,
        reservation_id_factory: Callable[[], str],
        clock: Callable[[], object],
    ) -> None:
        if not callable(getattr(broker, "acquire", None)):
            raise ValueError("broker must provide acquire")
        if not isinstance(reservations, SQLiteWorkerProvisioningReservations):
            raise ValueError("reservations must be SQLiteWorkerProvisioningReservations")
        if not callable(getattr(provisioner, "provision", None)):
            raise ValueError("provisioner must provide provision")
        if not callable(getattr(candidate_assembler, "assemble", None)):
            raise ValueError("candidate_assembler must provide assemble")
        if not callable(getattr(candidate_assembler, "assemble_for_owner", None)):
            raise ValueError("candidate_assembler must provide assemble_for_owner")
        if not callable(reservation_id_factory) or not callable(clock):
            raise ValueError("reservation_id_factory and clock must be callable")
        self._broker = broker
        self._reservations = reservations
        self._provisioner = provisioner
        self._assembler = candidate_assembler
        self._reservation_id_factory = reservation_id_factory
        self._clock = clock

    @property
    def authority_database_path(self):
        """Database path shared by production lease and provisioning capacity authority."""
        return self._reservations.database_path

    def _recovery(
        self,
        reservation_id: str,
        reason_code: str,
        *,
        worker_id: str | None = None,
        lease_outcome: WorkerLeaseOutcome | None = None,
    ) -> ElasticCapacityOutcome:
        return ElasticCapacityOutcome(
            ElasticCapacityOutcomeKind.RECOVERY_REQUIRED,
            _safe_reason_code(reason_code, "ELASTIC_RECOVERY_REQUIRED"),
            reservation_id=reservation_id,
            worker_id=worker_id,
            lease_outcome=lease_outcome,
        )

    @staticmethod
    def _reservation_identity_matches(
        record: ProvisioningReservationRecord,
        *,
        reservation_id: str,
        lease_request: WorkerLeaseRequest,
        runtime_kind: str,
    ) -> bool:
        return (
            record.reservation_id == reservation_id
            and record.session_id == lease_request.session_id
            and record.task_id == lease_request.task_id
            and record.runtime_kind == runtime_kind
            and record.state == "PRE_PROVISION"
            and record.worker_id is None
        )

    def _mark_recovery(
        self,
        reservation_id: str,
        lease_request: WorkerLeaseRequest,
        *,
        worker_id: str | None = None,
    ) -> None:
        self._reservations.mark_recovery(
            reservation_id,
            session_id=lease_request.session_id,
            task_id=lease_request.task_id,
            now=self._clock(),
            worker_id=worker_id,
        )

    def provision_ready(
        self,
        plan: SchedulePlan,
        lease_request: WorkerLeaseRequest,
        *,
        runtime_kind: str,
        policy: ElasticCapacityPolicy,
        eligibility: Mapping[str, NodeEligibility] | None,
    ) -> ElasticCapacityOutcome:
        """Reserve, provision, and re-observe one worker without pre-leasing it.

        ``eligibility`` is the same scheduler admission evidence
        ``ProductionElasticWorkerExecutor.execute_once`` requires: provisioning
        may only start after non-capacity gates are proven for the blocked
        nodes, never from a plan assembled without that evidence.
        """
        if not isinstance(plan, SchedulePlan):
            raise ValueError("plan must be SchedulePlan")
        if not isinstance(lease_request, WorkerLeaseRequest):
            raise ValueError("lease_request must be WorkerLeaseRequest")
        if not isinstance(policy, ElasticCapacityPolicy):
            raise ValueError("policy must be ElasticCapacityPolicy")
        runtime_kind = _text(runtime_kind, "runtime_kind", max_length=128)
        if not policy.enabled or policy.max_extra_workers == 0:
            return ElasticCapacityOutcome(
                ElasticCapacityOutcomeKind.POLICY_DISABLED,
                "ELASTIC_DISABLED",
            )
        if runtime_kind not in policy.permitted_runtime_kinds:
            return ElasticCapacityOutcome(
                ElasticCapacityOutcomeKind.POLICY_BLOCKED,
                "RUNTIME_KIND_NOT_ALLOWED",
            )
        if policy.allow_remote_connector and policy.transport_authorization_ref is None:
            return ElasticCapacityOutcome(
                ElasticCapacityOutcomeKind.POLICY_BLOCKED,
                "REMOTE_TRANSPORT_AUTHORIZATION_REQUIRED",
            )
        blocked_ids = {item.node_id for item in plan.blocked}
        if (
            eligibility is None
            or not isinstance(eligibility, Mapping)
            or not blocked_ids.issubset(eligibility)
        ):
            return ElasticCapacityOutcome(
                ElasticCapacityOutcomeKind.RECOVERY_REQUIRED,
                "SCHEDULER_ELIGIBILITY_EVIDENCE_MISSING",
            )
        for node_id in blocked_ids:
            evidence = eligibility[node_id]
            if not isinstance(evidence, NodeEligibility):
                return ElasticCapacityOutcome(
                    ElasticCapacityOutcomeKind.RECOVERY_REQUIRED,
                    "SCHEDULER_ELIGIBILITY_EVIDENCE_INVALID",
                )
            if not evidence.eligible:
                return ElasticCapacityOutcome(
                    ElasticCapacityOutcomeKind.NOT_CAPACITY_FAILURE,
                    "SCHEDULER_ELIGIBILITY_REFUSED",
                )
        if not _capacity_only(plan):
            return ElasticCapacityOutcome(
                ElasticCapacityOutcomeKind.NOT_CAPACITY_FAILURE,
                "ELASTIC_TRIGGER_NOT_CAPACITY",
            )

        reservation_id = _text(
            self._reservation_id_factory(),
            "reservation_id",
            max_length=256,
        )
        try:
            result = self._reservations.acquire(
                reservation_id=reservation_id,
                session_id=lease_request.session_id,
                task_id=lease_request.task_id,
                runtime_kind=runtime_kind,
                max_extra_workers=policy.max_extra_workers,
                now=self._clock(),
                project_id=lease_request.project_id,
                worktree=lease_request.worktree,
                mutable_scope=lease_request.mutable_scope,
            )
        except Exception:
            return self._recovery(reservation_id, "PROVISIONING_RESERVATION_EXCEPTION")
        if not isinstance(result, ProvisioningReservationResult):
            return self._recovery(reservation_id, "PROVISIONING_RESERVATION_RESULT_INVALID")
        if not isinstance(result.kind, ProvisioningReservationKind):
            return self._recovery(reservation_id, "PROVISIONING_RESERVATION_OUTCOME_UNSUPPORTED")
        if result.record is not None and not isinstance(result.record, ProvisioningReservationRecord):
            return self._recovery(reservation_id, "PROVISIONING_RESERVATION_RECORD_INVALID")
        if result.kind is ProvisioningReservationKind.LIMIT_WAIT:
            if result.record is not None:
                return self._recovery(reservation_id, "PROVISIONING_RESERVATION_RECORD_UNEXPECTED")
            return ElasticCapacityOutcome(
                ElasticCapacityOutcomeKind.LIMIT_WAIT,
                _safe_reason_code(result.reason_code, "ELASTIC_CAPACITY_LIMIT_REACHED"),
            )
        if result.kind is not ProvisioningReservationKind.ACQUIRED:
            return self._recovery(reservation_id, "PROVISIONING_RECONCILE_REQUIRED")
        if result.record is None:
            return self._recovery(reservation_id, "PROVISIONING_RESERVATION_RECORD_MISSING")
        if not self._reservation_identity_matches(
            result.record,
            reservation_id=reservation_id,
            lease_request=lease_request,
            runtime_kind=runtime_kind,
        ):
            return self._recovery(reservation_id, "PROVISIONING_RESERVATION_IDENTITY_MISMATCH")

        request = ElasticProvisionRequest(
            session_id=lease_request.session_id,
            task_id=lease_request.task_id,
            project_id=lease_request.project_id,
            runtime_kind=runtime_kind,
            worktree=lease_request.worktree,
            branch=lease_request.branch,
            expected_head=lease_request.expected_head,
            required_capabilities=lease_request.required_capabilities,
            remote_connector_allowed=policy.allow_remote_connector,
            transport_authorization_ref=policy.transport_authorization_ref,
        )
        try:
            self._reservations.mark_provisioning_started(
                reservation_id,
                session_id=lease_request.session_id,
                task_id=lease_request.task_id,
                now=self._clock(),
            )
        except Exception:
            return self._recovery(
                reservation_id, "PROVISIONING_START_PERSISTENCE_FAILED"
            )
        try:
            provisioned = self._provisioner.provision(request)
        except Exception:
            try:
                self._mark_recovery(reservation_id, lease_request)
            except Exception:
                pass
            return self._recovery(reservation_id, "PROVISIONING_UNCERTAIN")
        if not isinstance(provisioned, ElasticProvisionedWorker):
            try:
                self._mark_recovery(reservation_id, lease_request)
            except Exception:
                pass
            return self._recovery(reservation_id, "PROVISIONING_RESULT_INVALID")
        if provisioned.runtime_kind != runtime_kind:
            try:
                self._mark_recovery(
                    reservation_id, lease_request, worker_id=provisioned.worker_id
                )
            except Exception:
                pass
            return self._recovery(
                reservation_id,
                "PROVISIONED_RUNTIME_KIND_MISMATCH",
                worker_id=provisioned.worker_id,
            )
        if provisioned.remote_connector_configured and (
            not policy.allow_remote_connector
            or policy.transport_authorization_ref is None
        ):
            try:
                self._mark_recovery(
                    reservation_id, lease_request, worker_id=provisioned.worker_id
                )
            except Exception:
                pass
            return self._recovery(
                reservation_id,
                "REMOTE_CONNECTOR_UNAUTHORIZED",
                worker_id=provisioned.worker_id,
            )
        try:
            self._reservations.mark_provisioned(
                reservation_id,
                session_id=lease_request.session_id,
                task_id=lease_request.task_id,
                worker_id=provisioned.worker_id,
                now=self._clock(),
            )
        except ElasticCapacityError as exc:
            try:
                self._mark_recovery(
                    reservation_id, lease_request, worker_id=provisioned.worker_id
                )
            except Exception:
                pass
            return self._recovery(
                reservation_id,
                _safe_reason_code(
                    getattr(exc, "code", None),
                    "PROVISIONING_STATE_PERSISTENCE_FAILED",
                ),
                worker_id=provisioned.worker_id,
            )
        except Exception:
            try:
                self._mark_recovery(
                    reservation_id, lease_request, worker_id=provisioned.worker_id
                )
            except Exception:
                pass
            return self._recovery(
                reservation_id,
                "PROVISIONING_STATE_PERSISTENCE_FAILED",
                worker_id=provisioned.worker_id,
            )
        try:
            supply = self._assembler.assemble_for_owner(
                provisioned.worker_id,
                session_id=lease_request.session_id,
                task_id=lease_request.task_id,
            )
        except Exception:
            try:
                self._mark_recovery(
                    reservation_id, lease_request, worker_id=provisioned.worker_id
                )
            except Exception:
                pass
            return self._recovery(
                reservation_id,
                "PROVISIONED_WORKER_OBSERVATION_FAILED",
                worker_id=provisioned.worker_id,
            )
        if not isinstance(supply, WorkerSupplyRecord) or supply.worker_id != provisioned.worker_id:
            try:
                self._mark_recovery(
                    reservation_id, lease_request, worker_id=provisioned.worker_id
                )
            except Exception:
                pass
            return self._recovery(
                reservation_id,
                "PROVISIONED_WORKER_OBSERVATION_INVALID",
                worker_id=provisioned.worker_id,
            )
        return ElasticCapacityOutcome(
            ElasticCapacityOutcomeKind.PROVISIONED_READY,
            "ELASTIC_WORKER_REOBSERVED",
            reservation_id=reservation_id,
            worker_id=provisioned.worker_id,
            supply=supply,
        )

    def finalize_capacity(
        self,
        reservation_id: str,
        lease_request: WorkerLeaseRequest,
        *,
        worker_id: str,
    ) -> ProvisioningReservationRecord:
        return self._reservations.mark_capacity(
            reservation_id,
            session_id=lease_request.session_id,
            task_id=lease_request.task_id,
            worker_id=worker_id,
            now=self._clock(),
        )

    def abandon_provisioned_handoff(
        self,
        reservation_id: str | None,
        lease_request: WorkerLeaseRequest,
        *,
        worker_id: str | None = None,
    ) -> None:
        """Best-effort durable RECOVERY_REQUIRED mark for an uncertain handoff.

        Used on post-PROVISIONED_READY failure paths where the typed outcome is
        already decided: the persisted reservation must still explain why
        replay is unsafe. Never raises and never releases capacity.
        """
        if not reservation_id:
            return
        try:
            self._reservations.mark_recovery(
                reservation_id,
                session_id=lease_request.session_id,
                task_id=lease_request.task_id,
                now=self._clock(),
                worker_id=worker_id,
            )
        except Exception:
            pass

    def expand(
        self,
        plan: SchedulePlan,
        lease_request: WorkerLeaseRequest,
        *,
        runtime_kind: str,
        policy: ElasticCapacityPolicy,
        eligibility: Mapping[str, NodeEligibility] | None,
    ) -> ElasticCapacityOutcome:
        """Compatibility seam: provision safely, then lease through the existing broker."""
        prepared = self.provision_ready(
            plan,
            lease_request,
            runtime_kind=runtime_kind,
            policy=policy,
            eligibility=eligibility,
        )
        if prepared.kind is not ElasticCapacityOutcomeKind.PROVISIONED_READY:
            return prepared
        if prepared.supply is None or prepared.worker_id is None:
            self.abandon_provisioned_handoff(
                prepared.reservation_id, lease_request, worker_id=prepared.worker_id
            )
            return self._recovery(
                prepared.reservation_id or "unknown-reservation",
                "PROVISIONED_WORKER_OBSERVATION_INVALID",
            )
        retry_request = replace(
            lease_request,
            ordered_worker_ids=(prepared.worker_id,),
            required_runtime_id=prepared.supply.candidate.runtime_id,
        )
        try:
            lease_outcome = self._broker.acquire(
                retry_request,
                (prepared.supply.candidate,),
            )
        except Exception:
            try:
                self._mark_recovery(
                    prepared.reservation_id or "unknown-reservation",
                    lease_request,
                    worker_id=prepared.worker_id,
                )
            except Exception:
                pass
            return self._recovery(
                prepared.reservation_id or "unknown-reservation",
                "PROVISIONED_WORKER_LEASE_EXCEPTION",
                worker_id=prepared.worker_id,
            )
        if not isinstance(lease_outcome, WorkerLeaseOutcome):
            try:
                self._mark_recovery(
                    prepared.reservation_id or "unknown-reservation",
                    lease_request,
                    worker_id=prepared.worker_id,
                )
            except Exception:
                pass
            return self._recovery(
                prepared.reservation_id or "unknown-reservation",
                "PROVISIONED_WORKER_LEASE_RESULT_INVALID",
                worker_id=prepared.worker_id,
            )
        if (
            lease_outcome.kind is not LeaseOutcomeKind.LEASED
            or lease_outcome.lease is None
            or lease_outcome.lease.worker_id != prepared.worker_id
        ):
            try:
                self._mark_recovery(
                    prepared.reservation_id or "unknown-reservation",
                    lease_request,
                    worker_id=prepared.worker_id,
                )
            except Exception:
                pass
            return self._recovery(
                prepared.reservation_id or "unknown-reservation",
                "PROVISIONED_WORKER_NOT_LEASED",
                worker_id=prepared.worker_id,
                lease_outcome=lease_outcome,
            )
        try:
            self.finalize_capacity(
                prepared.reservation_id or "unknown-reservation",
                retry_request,
                worker_id=prepared.worker_id,
            )
        except Exception:
            self.abandon_provisioned_handoff(
                prepared.reservation_id, lease_request, worker_id=prepared.worker_id
            )
            return self._recovery(
                prepared.reservation_id or "unknown-reservation",
                "PROVISIONING_CAPACITY_PERSISTENCE_FAILED",
                worker_id=prepared.worker_id,
                lease_outcome=lease_outcome,
            )
        return ElasticCapacityOutcome(
            ElasticCapacityOutcomeKind.PROVISIONED_AND_LEASED,
            "ELASTIC_WORKER_LEASED",
            reservation_id=prepared.reservation_id,
            worker_id=prepared.worker_id,
            supply=prepared.supply,
            lease_outcome=lease_outcome,
        )



class ProductionElasticExecutionKind(str, Enum):
    FIXED_POOL_EXECUTED = "FIXED_POOL_EXECUTED"
    ELASTIC_EXECUTED = "ELASTIC_EXECUTED"
    WAIT = "WAIT"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


@dataclass(frozen=True, slots=True)
class ProductionElasticExecutionResult:
    kind: ProductionElasticExecutionKind
    reason_code: str
    initial_plan: SchedulePlan
    final_plan: SchedulePlan | None = None
    batch_result: ParallelReadyBatchResult | None = None
    elastic_outcome: ElasticCapacityOutcome | None = None


class ProductionWorkerSupplyAssemblerPort(WorkerSupplyAssemblerPort, Protocol):
    def assemble_all(self) -> tuple[WorkerSupplyRecord, ...]: ...

    def assemble_all_for_owner(
        self, *, session_id: str, task_id: str
    ) -> tuple[WorkerSupplyRecord, ...]: ...


class ProductionElasticWorkerExecutor:
    """One bounded production pass: observe ? schedule ? optional expand ? execute."""

    def __init__(
        self,
        *,
        candidate_assembler: ProductionWorkerSupplyAssemblerPort,
        capacity_coordinator: ElasticWorkerCapacityCoordinator,
        parallel_executor: ParallelReadyExecutor,
    ) -> None:
        if not callable(getattr(candidate_assembler, "assemble_all", None)):
            raise ValueError("candidate_assembler must provide assemble_all")
        if not callable(getattr(candidate_assembler, "assemble_all_for_owner", None)):
            raise ValueError("candidate_assembler must provide assemble_all_for_owner")
        if not isinstance(capacity_coordinator, ElasticWorkerCapacityCoordinator):
            raise ValueError("capacity_coordinator must be ElasticWorkerCapacityCoordinator")
        if not isinstance(parallel_executor, ParallelReadyExecutor):
            raise ValueError("parallel_executor must be ParallelReadyExecutor")
        assembler_authority = getattr(
            candidate_assembler, "lease_evidence_database_path", None
        )
        coordinator_authority = capacity_coordinator.authority_database_path
        if assembler_authority is not None and Path(assembler_authority) != Path(
            coordinator_authority
        ):
            raise ValueError(
                "ELASTIC_SUPPLY_AUTHORITY_MISMATCH: candidate assembly and elastic "
                "capacity must observe one shared SQLite worker authority"
            )
        self._assembler = candidate_assembler
        self._capacity = capacity_coordinator
        self._executor = parallel_executor

    @staticmethod
    def _batch_kind(
        batch: ParallelReadyBatchResult,
        *,
        success_kind: ProductionElasticExecutionKind,
    ) -> tuple[ProductionElasticExecutionKind, str]:
        kinds = {item.kind for item in batch.outcomes}
        if kinds and kinds == {ParallelReadyOutcomeKind.RUN_COMPLETED}:
            return success_kind, "PARALLEL_READY_RUN_COMPLETED"
        recovery = {
            ParallelReadyOutcomeKind.RUNNER_RECOVERY_REQUIRED,
            ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED,
            ParallelReadyOutcomeKind.LEASE_RECOVERY_REQUIRED,
            ParallelReadyOutcomeKind.LEASE_EXISTING_RECONCILE,
        }
        if kinds & recovery:
            return ProductionElasticExecutionKind.RECOVERY_REQUIRED, "PARALLEL_READY_RECOVERY_REQUIRED"
        return ProductionElasticExecutionKind.WAIT, "PARALLEL_READY_WAIT"

    def _supply_snapshot(self) -> WorkerSupplySnapshot:
        records = self._assembler.assemble_all()
        if not isinstance(records, tuple):
            raise ValueError("assemble_all must return a tuple")
        return WorkerSupplySnapshot.from_records(records)

    def _supply_snapshot_for_owner(
        self, *, session_id: str, task_id: str
    ) -> WorkerSupplySnapshot:
        records = self._assembler.assemble_all_for_owner(
            session_id=session_id, task_id=task_id
        )
        if not isinstance(records, tuple):
            raise ValueError("assemble_all_for_owner must return a tuple")
        return WorkerSupplySnapshot.from_records(records)

    def _execute_plan(
        self,
        plan: SchedulePlan,
        contracts_by_node: Mapping[str, ParallelReadyNodeContract],
        supply: WorkerSupplySnapshot,
        *,
        provider_inflight: Mapping[str, int],
        batch_id: str | None,
    ) -> ParallelReadyBatchResult:
        selected_contracts = {
            item.node_id: contracts_by_node[item.node_id]
            for item in plan.selected
        }
        tasks = assemble_parallel_ready_tasks(plan, selected_contracts, supply)
        return self._executor.execute(
            plan,
            tasks,
            provider_inflight=provider_inflight,
            batch_id=batch_id,
        )

    def execute_once(
        self,
        graph: TaskGraph,
        ready: ReadySetResult,
        contracts_by_node: Mapping[str, ParallelReadyNodeContract],
        *,
        schedule_policy: SchedulePolicy,
        provider_inflight: Mapping[str, int],
        runtime_kind: str,
        elastic_policy: ElasticCapacityPolicy,
        running_write_sets: dict[str, tuple[str, ...]] | None = None,
        eligibility: dict[str, NodeEligibility] | None = None,
        batch_id: str | None = None,
    ) -> ProductionElasticExecutionResult:
        if not isinstance(graph, TaskGraph):
            raise ValueError("graph must be TaskGraph")
        if not isinstance(ready, ReadySetResult):
            raise ValueError("ready must be ReadySetResult")
        if not isinstance(contracts_by_node, Mapping):
            raise ValueError("contracts_by_node must be a mapping")
        if not set(ready.ready_ids).issubset(contracts_by_node):
            raise ValueError("missing production contract for ready node")
        if not isinstance(schedule_policy, SchedulePolicy):
            raise ValueError("schedule_policy must be SchedulePolicy")
        if not isinstance(elastic_policy, ElasticCapacityPolicy):
            raise ValueError("elastic_policy must be ElasticCapacityPolicy")
        if eligibility is None or not set(ready.ready_ids).issubset(eligibility):
            return ProductionElasticExecutionResult(
                ProductionElasticExecutionKind.RECOVERY_REQUIRED,
                "SCHEDULER_ELIGIBILITY_EVIDENCE_MISSING",
                SchedulePlan((), (), "eligibility-evidence-missing"),
            )
        effective_eligibility = dict(eligibility)
        for node_id in ready.ready_ids:
            contract = contracts_by_node[node_id]
            current = effective_eligibility[node_id]
            if not isinstance(current, NodeEligibility):
                return ProductionElasticExecutionResult(
                    ProductionElasticExecutionKind.RECOVERY_REQUIRED,
                    "SCHEDULER_ELIGIBILITY_EVIDENCE_INVALID",
                    SchedulePlan((), (), "eligibility-evidence-invalid"),
                )
            if not contract.dispatch_gate.allowed and not current.gate_refused:
                effective_eligibility[node_id] = NodeEligibility(
                    gate_refused=True,
                    human_approval_pending=current.human_approval_pending,
                    provider_unavailable=current.provider_unavailable,
                    rate_limited=current.rate_limited,
                )
        try:
            initial_supply = self._supply_snapshot()
        except Exception:
            empty = SchedulePlan((), (), "worker-supply-recovery")
            return ProductionElasticExecutionResult(
                ProductionElasticExecutionKind.RECOVERY_REQUIRED,
                "WORKER_SUPPLY_OBSERVATION_FAILED",
                empty,
            )
        initial_plan = schedule_once(
            graph,
            ready,
            initial_supply.scheduler_workers,
            schedule_policy,
            running_write_sets=running_write_sets,
            eligibility=effective_eligibility,
        )
        if initial_plan.selected:
            try:
                batch = self._execute_plan(
                    initial_plan,
                    contracts_by_node,
                    initial_supply,
                    provider_inflight=provider_inflight,
                    batch_id=batch_id,
                )
            except Exception:
                return ProductionElasticExecutionResult(
                    ProductionElasticExecutionKind.RECOVERY_REQUIRED,
                    "PARALLEL_READY_EXECUTION_EXCEPTION",
                    initial_plan,
                )
            kind, reason = self._batch_kind(
                batch, success_kind=ProductionElasticExecutionKind.FIXED_POOL_EXECUTED
            )
            return ProductionElasticExecutionResult(
                kind, reason, initial_plan, final_plan=initial_plan, batch_result=batch
            )
        if not _capacity_only(initial_plan):
            return ProductionElasticExecutionResult(
                ProductionElasticExecutionKind.WAIT,
                "SCHEDULER_BLOCK_NOT_CAPACITY",
                initial_plan,
            )
        blocked_node = initial_plan.blocked[0].node_id
        contract = contracts_by_node.get(blocked_node)
        if not isinstance(contract, ParallelReadyNodeContract):
            return ProductionElasticExecutionResult(
                ProductionElasticExecutionKind.RECOVERY_REQUIRED,
                "ELASTIC_TASK_CONTRACT_MISSING",
                initial_plan,
            )
        elastic = self._capacity.provision_ready(
            initial_plan,
            contract.lease_request,
            runtime_kind=runtime_kind,
            policy=elastic_policy,
            eligibility=effective_eligibility,
        )
        if elastic.kind is not ElasticCapacityOutcomeKind.PROVISIONED_READY:
            kind = (
                ProductionElasticExecutionKind.RECOVERY_REQUIRED
                if elastic.kind is ElasticCapacityOutcomeKind.RECOVERY_REQUIRED
                else ProductionElasticExecutionKind.WAIT
            )
            return ProductionElasticExecutionResult(
                kind,
                elastic.reason_code,
                initial_plan,
                elastic_outcome=elastic,
            )
        try:
            final_supply = self._supply_snapshot_for_owner(
                session_id=contract.lease_request.session_id,
                task_id=contract.lease_request.task_id,
            )
        except Exception:
            self._capacity.abandon_provisioned_handoff(
                elastic.reservation_id, contract.lease_request, worker_id=elastic.worker_id
            )
            return ProductionElasticExecutionResult(
                ProductionElasticExecutionKind.RECOVERY_REQUIRED,
                "PROVISIONED_WORKER_FULL_REOBSERVATION_FAILED",
                initial_plan,
                elastic_outcome=elastic,
            )
        final_plan = schedule_once(
            graph,
            ready,
            final_supply.scheduler_workers,
            schedule_policy,
            running_write_sets=running_write_sets,
            eligibility=effective_eligibility,
        )
        if (
            len(final_plan.selected) != 1
            or final_plan.selected[0].node_id != blocked_node
            or final_plan.selected[0].worker_id != elastic.worker_id
        ):
            self._capacity.abandon_provisioned_handoff(
                elastic.reservation_id, contract.lease_request, worker_id=elastic.worker_id
            )
            return ProductionElasticExecutionResult(
                ProductionElasticExecutionKind.RECOVERY_REQUIRED,
                "PROVISIONED_WORKER_RESCHEDULE_DRIFT",
                initial_plan,
                final_plan=final_plan,
                elastic_outcome=elastic,
            )
        try:
            batch = self._execute_plan(
                final_plan,
                contracts_by_node,
                final_supply,
                provider_inflight=provider_inflight,
                batch_id=batch_id,
            )
        except Exception:
            self._capacity.abandon_provisioned_handoff(
                elastic.reservation_id, contract.lease_request, worker_id=elastic.worker_id
            )
            return ProductionElasticExecutionResult(
                ProductionElasticExecutionKind.RECOVERY_REQUIRED,
                "PARALLEL_READY_EXECUTION_EXCEPTION",
                initial_plan,
                final_plan=final_plan,
                elastic_outcome=elastic,
            )
        kind, reason = self._batch_kind(
            batch, success_kind=ProductionElasticExecutionKind.ELASTIC_EXECUTED
        )
        if kind is not ProductionElasticExecutionKind.ELASTIC_EXECUTED:
            self._capacity.abandon_provisioned_handoff(
                elastic.reservation_id, contract.lease_request, worker_id=elastic.worker_id
            )
        else:
            try:
                self._capacity.finalize_capacity(
                    elastic.reservation_id or "unknown-reservation",
                    contract.lease_request,
                    worker_id=elastic.worker_id or "unknown-worker",
                )
            except Exception:
                self._capacity.abandon_provisioned_handoff(
                    elastic.reservation_id, contract.lease_request,
                    worker_id=elastic.worker_id,
                )
                return ProductionElasticExecutionResult(
                    ProductionElasticExecutionKind.RECOVERY_REQUIRED,
                    "PROVISIONING_CAPACITY_PERSISTENCE_FAILED",
                    initial_plan,
                    final_plan=final_plan,
                    batch_result=batch,
                    elastic_outcome=elastic,
                )
        return ProductionElasticExecutionResult(
            kind,
            reason,
            initial_plan,
            final_plan=final_plan,
            batch_result=batch,
            elastic_outcome=elastic,
        )

def build_sqlite_elastic_worker_capacity_coordinator(
    *,
    database_path,
    provisioner: ElasticWorkerProvisioner,
    candidate_assembler: WorkerSupplyAssemblerPort,
    lease_id_factory: Callable[[], str],
    reservation_id_factory: Callable[[], str],
    clock: Callable[[], object],
) -> ElasticWorkerCapacityCoordinator:
    """Build elastic capacity with one shared SQLite worker-capacity authority."""
    store = SQLiteWorkerLeaseStore(database_path)
    assembler_authority = getattr(
        candidate_assembler, "lease_evidence_database_path", None
    )
    if assembler_authority is not None and Path(assembler_authority) != Path(
        store.database_path
    ):
        raise ValueError(
            "ELASTIC_SUPPLY_AUTHORITY_MISMATCH: candidate assembly and elastic "
            "capacity must observe one shared SQLite worker authority"
        )
    broker = WorkerLeaseBroker(
        store=store,
        lease_id_factory=lease_id_factory,
        clock=clock,
    )
    reservations = SQLiteWorkerProvisioningReservations(store)
    return ElasticWorkerCapacityCoordinator(
        broker=broker,
        reservations=reservations,
        provisioner=provisioner,
        candidate_assembler=candidate_assembler,
        reservation_id_factory=reservation_id_factory,
        clock=clock,
    )
