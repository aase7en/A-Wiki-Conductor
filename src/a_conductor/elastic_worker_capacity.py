"""Policy-bounded elastic worker expansion above the existing lease broker.

The coordinator owns no scheduler, worker registry, lifecycle implementation,
connector allocator, or retry loop. Provisioning reservations are stored in the
same SQLite file owned by ``SQLiteWorkerLeaseStore`` so independent processes
serialize one worker-capacity authority. Ambiguous provisioning consumes a slot
until explicit reconciliation; it is never retried blindly.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Iterator, Protocol, Sequence

from .graph.scheduler import BlockedReasonKind, SchedulePlan
from .worker_candidate_assembly import WorkerCandidateAssembler, WorkerSupplyRecord
from .worker_lease import (
    LeaseOutcomeKind,
    SQLiteWorkerLeaseStore,
    WorkerLeaseBroker,
    WorkerLeaseOutcome,
    WorkerLeaseRequest,
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
        kinds = tuple(_text(item, "runtime_kind", max_length=128) for item in self.permitted_runtime_kinds)
        if len(set(kinds)) != len(kinds):
            raise ValueError("permitted_runtime_kinds must not contain duplicates")
        object.__setattr__(self, "permitted_runtime_kinds", kinds)


class ProvisioningReservationKind(str, Enum):
    ACQUIRED = "ACQUIRED"
    EXISTING = "EXISTING"
    LIMIT_WAIT = "LIMIT_WAIT"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


@dataclass(frozen=True, slots=True)
class ProvisioningReservationRecord:
    reservation_id: str
    session_id: str
    task_id: str
    runtime_kind: str
    state: str
    worker_id: str | None
    acquired_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class ProvisioningReservationResult:
    kind: ProvisioningReservationKind
    record: ProvisioningReservationRecord | None
    reason_code: str


class SQLiteWorkerProvisioningReservations:
    """Bounded provisioning reservations tied to one worker-lease SQLite authority."""

    _CONSUMING = ("ACTIVE", "PROVISIONED", "RECOVERY_REQUIRED")

    def __init__(self, lease_store: SQLiteWorkerLeaseStore) -> None:
        if not isinstance(lease_store, SQLiteWorkerLeaseStore):
            raise ValueError("lease_store must be SQLiteWorkerLeaseStore")
        self._lease_store = lease_store
        self.database_path = lease_store.database_path
        self.initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connect() as connection:
            try:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS worker_provisioning_reservations (
                        reservation_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        task_id TEXT NOT NULL,
                        runtime_kind TEXT NOT NULL,
                        state TEXT NOT NULL,
                        worker_id TEXT,
                        acquired_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE UNIQUE INDEX IF NOT EXISTS ux_worker_provisioning_owner_task
                        ON worker_provisioning_reservations(session_id, task_id)
                        WHERE state != 'RELEASED';
                    """
                )
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                raise ElasticCapacityError("PROVISIONING_STORE_INIT_FAILED") from exc

    @staticmethod
    def _record(row: sqlite3.Row) -> ProvisioningReservationRecord:
        state = row["state"]
        if state not in {"ACTIVE", "PROVISIONED", "RECOVERY_REQUIRED", "RELEASED"}:
            raise ElasticCapacityError("PROVISIONING_RECORD_INVALID")
        try:
            acquired = _timestamp(row["acquired_at"], "acquired_at")
            updated = _timestamp(row["updated_at"], "updated_at")
        except (TypeError, ValueError) as exc:
            raise ElasticCapacityError("PROVISIONING_RECORD_INVALID") from exc
        return ProvisioningReservationRecord(
            reservation_id=_text(row["reservation_id"], "reservation_id"),
            session_id=_text(row["session_id"], "session_id"),
            task_id=_text(row["task_id"], "task_id"),
            runtime_kind=_text(row["runtime_kind"], "runtime_kind", max_length=128),
            state=state,
            worker_id=None if row["worker_id"] is None else _text(row["worker_id"], "worker_id"),
            acquired_at=acquired,
            updated_at=updated,
        )

    def acquire(
        self,
        *,
        reservation_id: str,
        session_id: str,
        task_id: str,
        runtime_kind: str,
        max_extra_workers: int,
        now: object,
    ) -> ProvisioningReservationResult:
        reservation_id = _text(reservation_id, "reservation_id")
        session_id = _text(session_id, "session_id")
        task_id = _text(task_id, "task_id")
        runtime_kind = _text(runtime_kind, "runtime_kind", max_length=128)
        if (
            not isinstance(max_extra_workers, int)
            or isinstance(max_extra_workers, bool)
            or max_extra_workers < 1
            or max_extra_workers > 99
        ):
            raise ValueError("max_extra_workers must be between 1 and 99")
        observed_at = _timestamp(now, "now")
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                existing_row = connection.execute(
                    "SELECT * FROM worker_provisioning_reservations "
                    "WHERE session_id = ? AND task_id = ? AND state != 'RELEASED'",
                    (session_id, task_id),
                ).fetchone()
                if existing_row is not None:
                    existing = self._record(existing_row)
                    connection.rollback()
                    return ProvisioningReservationResult(
                        ProvisioningReservationKind.EXISTING,
                        existing,
                        "PROVISIONING_ALREADY_ACTIVE",
                    )
                count = connection.execute(
                    "SELECT COUNT(*) AS total FROM worker_provisioning_reservations "
                    "WHERE state IN ('ACTIVE','PROVISIONED','RECOVERY_REQUIRED')"
                ).fetchone()["total"]
                if not isinstance(count, int) or count < 0:
                    connection.rollback()
                    return ProvisioningReservationResult(
                        ProvisioningReservationKind.RECOVERY_REQUIRED,
                        None,
                        "PROVISIONING_COUNT_INVALID",
                    )
                if count >= max_extra_workers:
                    connection.rollback()
                    return ProvisioningReservationResult(
                        ProvisioningReservationKind.LIMIT_WAIT,
                        None,
                        "ELASTIC_CAPACITY_LIMIT_REACHED",
                    )
                connection.execute(
                    "INSERT INTO worker_provisioning_reservations(" 
                    "reservation_id, session_id, task_id, runtime_kind, state, worker_id, acquired_at, updated_at) "
                    "VALUES(?, ?, ?, ?, 'ACTIVE', NULL, ?, ?)",
                    (reservation_id, session_id, task_id, runtime_kind, observed_at, observed_at),
                )
                row = connection.execute(
                    "SELECT * FROM worker_provisioning_reservations WHERE reservation_id = ?",
                    (reservation_id,),
                ).fetchone()
                connection.commit()
                return ProvisioningReservationResult(
                    ProvisioningReservationKind.ACQUIRED,
                    self._record(row),
                    "PROVISIONING_RESERVED",
                )
            except ElasticCapacityError:
                connection.rollback()
                raise
            except sqlite3.IntegrityError:
                connection.rollback()
                return ProvisioningReservationResult(
                    ProvisioningReservationKind.RECOVERY_REQUIRED,
                    None,
                    "PROVISIONING_RESERVATION_CONFLICT",
                )
            except sqlite3.Error as exc:
                connection.rollback()
                raise ElasticCapacityError("PROVISIONING_STORE_WRITE_FAILED") from exc

    def _transition(
        self,
        reservation_id: str,
        *,
        state: str,
        now: object,
        worker_id: str | None = None,
    ) -> ProvisioningReservationRecord:
        reservation_id = _text(reservation_id, "reservation_id")
        observed_at = _timestamp(now, "now")
        if state not in {"PROVISIONED", "RECOVERY_REQUIRED", "RELEASED"}:
            raise ValueError("provisioning transition state invalid")
        if worker_id is not None:
            worker_id = _text(worker_id, "worker_id")
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT * FROM worker_provisioning_reservations WHERE reservation_id = ?",
                    (reservation_id,),
                ).fetchone()
                if row is None:
                    connection.rollback()
                    raise ElasticCapacityError("PROVISIONING_RESERVATION_NOT_FOUND")
                current = self._record(row)
                if current.state == state and current.worker_id == worker_id:
                    connection.rollback()
                    return current
                if current.state != "ACTIVE":
                    connection.rollback()
                    raise ElasticCapacityError("PROVISIONING_RESERVATION_STATE_MISMATCH")
                connection.execute(
                    "UPDATE worker_provisioning_reservations "
                    "SET state = ?, worker_id = ?, updated_at = ? WHERE reservation_id = ?",
                    (state, worker_id, observed_at, reservation_id),
                )
                updated = connection.execute(
                    "SELECT * FROM worker_provisioning_reservations WHERE reservation_id = ?",
                    (reservation_id,),
                ).fetchone()
                connection.commit()
                return self._record(updated)
            except ElasticCapacityError:
                connection.rollback()
                raise
            except sqlite3.Error as exc:
                connection.rollback()
                raise ElasticCapacityError("PROVISIONING_STORE_WRITE_FAILED") from exc

    def mark_provisioned(
        self, reservation_id: str, *, worker_id: str, now: object
    ) -> ProvisioningReservationRecord:
        return self._transition(
            reservation_id, state="PROVISIONED", worker_id=worker_id, now=now
        )

    def mark_recovery(
        self, reservation_id: str, *, now: object
    ) -> ProvisioningReservationRecord:
        return self._transition(reservation_id, state="RECOVERY_REQUIRED", now=now)

    def release_unstarted(
        self, reservation_id: str, *, now: object
    ) -> ProvisioningReservationRecord:
        return self._transition(reservation_id, state="RELEASED", now=now)

    def list_consuming(self) -> tuple[ProvisioningReservationRecord, ...]:
        with self._connect() as connection:
            try:
                rows = connection.execute(
                    "SELECT * FROM worker_provisioning_reservations "
                    "WHERE state IN ('ACTIVE','PROVISIONED','RECOVERY_REQUIRED') "
                    "ORDER BY reservation_id"
                ).fetchall()
            except sqlite3.Error as exc:
                raise ElasticCapacityError("PROVISIONING_STORE_READ_FAILED") from exc
        return tuple(self._record(row) for row in rows)


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


@dataclass(frozen=True, slots=True)
class ElasticProvisionedWorker:
    worker_id: str
    runtime_kind: str
    remote_connector_configured: bool = False

    def __post_init__(self) -> None:
        _text(self.worker_id, "worker_id")
        _text(self.runtime_kind, "runtime_kind", max_length=128)
        if not isinstance(self.remote_connector_configured, bool):
            raise ValueError("remote_connector_configured must be bool")


class ElasticWorkerProvisioner(Protocol):
    def provision(self, request: ElasticProvisionRequest) -> ElasticProvisionedWorker: ...


class WorkerSupplyAssemblerPort(Protocol):
    def assemble(self, worker_id: str) -> WorkerSupplyRecord: ...


class ElasticCapacityOutcomeKind(str, Enum):
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
        if not callable(reservation_id_factory) or not callable(clock):
            raise ValueError("reservation_id_factory and clock must be callable")
        self._broker = broker
        self._reservations = reservations
        self._provisioner = provisioner
        self._assembler = candidate_assembler
        self._reservation_id_factory = reservation_id_factory
        self._clock = clock

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
            reason_code,
            reservation_id=reservation_id,
            worker_id=worker_id,
            lease_outcome=lease_outcome,
        )

    def expand(
        self,
        plan: SchedulePlan,
        lease_request: WorkerLeaseRequest,
        *,
        runtime_kind: str,
        policy: ElasticCapacityPolicy,
    ) -> ElasticCapacityOutcome:
        if not isinstance(plan, SchedulePlan):
            raise ValueError("plan must be SchedulePlan")
        if not isinstance(lease_request, WorkerLeaseRequest):
            raise ValueError("lease_request must be WorkerLeaseRequest")
        if not isinstance(policy, ElasticCapacityPolicy):
            raise ValueError("policy must be ElasticCapacityPolicy")
        runtime_kind = _text(runtime_kind, "runtime_kind", max_length=128)
        if not policy.enabled or policy.max_extra_workers == 0:
            return ElasticCapacityOutcome(
                ElasticCapacityOutcomeKind.POLICY_DISABLED, "ELASTIC_DISABLED"
            )
        if runtime_kind not in policy.permitted_runtime_kinds:
            return ElasticCapacityOutcome(
                ElasticCapacityOutcomeKind.POLICY_BLOCKED,
                "RUNTIME_KIND_NOT_ALLOWED",
            )
        if not _capacity_only(plan):
            return ElasticCapacityOutcome(
                ElasticCapacityOutcomeKind.NOT_CAPACITY_FAILURE,
                "ELASTIC_TRIGGER_NOT_CAPACITY",
            )

        reservation_id = _text(
            self._reservation_id_factory(), "reservation_id", max_length=256
        )
        now = self._clock()
        try:
            result = self._reservations.acquire(
                reservation_id=reservation_id,
                session_id=lease_request.session_id,
                task_id=lease_request.task_id,
                runtime_kind=runtime_kind,
                max_extra_workers=policy.max_extra_workers,
                now=now,
            )
        except Exception:
            return self._recovery(reservation_id, "PROVISIONING_RESERVATION_EXCEPTION")
        if not isinstance(result, ProvisioningReservationResult):
            return self._recovery(reservation_id, "PROVISIONING_RESERVATION_RESULT_INVALID")
        if result.kind is ProvisioningReservationKind.LIMIT_WAIT:
            return ElasticCapacityOutcome(
                ElasticCapacityOutcomeKind.LIMIT_WAIT,
                result.reason_code,
            )
        if result.kind is not ProvisioningReservationKind.ACQUIRED or result.record is None:
            return self._recovery(
                reservation_id,
                "PROVISIONING_RECONCILE_REQUIRED",
            )

        provision_request = ElasticProvisionRequest(
            session_id=lease_request.session_id,
            task_id=lease_request.task_id,
            project_id=lease_request.project_id,
            runtime_kind=runtime_kind,
            worktree=lease_request.worktree,
            branch=lease_request.branch,
            expected_head=lease_request.expected_head,
            required_capabilities=lease_request.required_capabilities,
            remote_connector_allowed=policy.allow_remote_connector,
        )
        try:
            provisioned = self._provisioner.provision(provision_request)
        except Exception:
            try:
                self._reservations.mark_recovery(reservation_id, now=self._clock())
            except Exception:
                pass
            return self._recovery(reservation_id, "PROVISIONING_UNCERTAIN")
        if not isinstance(provisioned, ElasticProvisionedWorker):
            try:
                self._reservations.mark_recovery(reservation_id, now=self._clock())
            except Exception:
                pass
            return self._recovery(reservation_id, "PROVISIONING_RESULT_INVALID")
        if provisioned.runtime_kind != runtime_kind:
            try:
                self._reservations.mark_recovery(reservation_id, now=self._clock())
            except Exception:
                pass
            return self._recovery(
                reservation_id,
                "PROVISIONED_RUNTIME_KIND_MISMATCH",
                worker_id=provisioned.worker_id,
            )
        if provisioned.remote_connector_configured and not policy.allow_remote_connector:
            try:
                self._reservations.mark_recovery(reservation_id, now=self._clock())
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
                worker_id=provisioned.worker_id,
                now=self._clock(),
            )
        except Exception:
            return self._recovery(
                reservation_id,
                "PROVISIONING_STATE_PERSISTENCE_FAILED",
                worker_id=provisioned.worker_id,
            )

        try:
            supply = self._assembler.assemble(provisioned.worker_id)
        except Exception:
            return self._recovery(
                reservation_id,
                "PROVISIONED_WORKER_OBSERVATION_FAILED",
                worker_id=provisioned.worker_id,
            )
        if not isinstance(supply, WorkerSupplyRecord) or supply.worker_id != provisioned.worker_id:
            return self._recovery(
                reservation_id,
                "PROVISIONED_WORKER_OBSERVATION_INVALID",
                worker_id=provisioned.worker_id,
            )

        retry_request = replace(
            lease_request,
            ordered_worker_ids=(provisioned.worker_id,),
        )
        try:
            lease_outcome = self._broker.acquire(retry_request, (supply.candidate,))
        except Exception:
            return self._recovery(
                reservation_id,
                "PROVISIONED_WORKER_LEASE_EXCEPTION",
                worker_id=provisioned.worker_id,
            )
        if not isinstance(lease_outcome, WorkerLeaseOutcome):
            return self._recovery(
                reservation_id,
                "PROVISIONED_WORKER_LEASE_RESULT_INVALID",
                worker_id=provisioned.worker_id,
            )
        if (
            lease_outcome.kind is not LeaseOutcomeKind.LEASED
            or lease_outcome.lease is None
            or lease_outcome.lease.worker_id != provisioned.worker_id
        ):
            return self._recovery(
                reservation_id,
                "PROVISIONED_WORKER_NOT_LEASED",
                worker_id=provisioned.worker_id,
                lease_outcome=lease_outcome,
            )
        return ElasticCapacityOutcome(
            ElasticCapacityOutcomeKind.PROVISIONED_AND_LEASED,
            "ELASTIC_WORKER_LEASED",
            reservation_id=reservation_id,
            worker_id=provisioned.worker_id,
            lease_outcome=lease_outcome,
        )
