"""AHA-4A atomic worker leasing and deterministic fallback.

This module extends existing worker/scheduler identity and conflict seams. It
owns runtime-capacity leases only; it is not a scheduler, task store, lifecycle,
dispatch system, retry loop, or replacement for A-Wiki work-order claims.
"""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Callable, Iterator, Sequence

from .domain import RecoveryClassification
from .graph.analyze import write_sets_overlap
from .registry import windows_worktree_key


_HEAD_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")
_DIRTY_STATES = frozenset({"CLEAN", "DIRTY", "UNKNOWN"})


class WorkerLeaseError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class LeaseMutationIntent(str, Enum):
    READ_ONLY = "READ_ONLY"
    MUTATION = "MUTATION"


class LeaseOutcomeKind(str, Enum):
    LEASED = "LEASED"
    EXISTING = "EXISTING"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    RDC_READ_ONLY = "RDC_READ_ONLY"
    WAIT = "WAIT"


class LeaseHealthKind(str, Enum):
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    QUARANTINED = "QUARANTINED"
    RELEASED = "RELEASED"
    EXPIRY_UNKNOWN = "EXPIRY_UNKNOWN"


class LeaseReconciliationKind(str, Enum):
    RELEASED = "RELEASED"
    QUARANTINED = "QUARANTINED"


class CandidateRejectionKind(str, Enum):
    CANDIDATE_MISSING = "CANDIDATE_MISSING"
    ACTIVE_TASK = "ACTIVE_TASK"
    WORKER_NOT_READY = "WORKER_NOT_READY"
    WORKER_RESERVED = "WORKER_RESERVED"
    CAPABILITY_MISMATCH = "CAPABILITY_MISMATCH"
    RUNTIME_MISMATCH = "RUNTIME_MISMATCH"
    PROJECT_MISMATCH = "PROJECT_MISMATCH"
    WORKTREE_MISMATCH = "WORKTREE_MISMATCH"
    BRANCH_MISMATCH = "BRANCH_MISMATCH"
    HEAD_MISMATCH = "HEAD_MISMATCH"
    HEALTH_STALE = "HEALTH_STALE"
    OWNERSHIP_UNKNOWN = "OWNERSHIP_UNKNOWN"
    DIRTY_UNKNOWN = "DIRTY_UNKNOWN"
    DIRTY_WORKTREE = "DIRTY_WORKTREE"
    MUTATION_UNAUTHORIZED = "MUTATION_UNAUTHORIZED"
    MUTABLE_SCOPE_OVERLAP = "MUTABLE_SCOPE_OVERLAP"
    LEASE_BUSY = "LEASE_BUSY"


def _text(value: str, field_name: str, *, max_length: int = 512) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    cleaned = value.strip()
    if len(cleaned) > max_length or "\x00" in cleaned or "\r" in cleaned or "\n" in cleaned:
        raise ValueError(f"{field_name} is invalid")
    return cleaned


def _optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _text(value, field_name)


def _bool(value: bool, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be bool")
    return value


def _scope(values: Sequence[str], field_name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{field_name} must be a sequence")
    result = tuple(_text(value, field_name, max_length=512) for value in values)
    if len(set(result)) != len(result):
        raise ValueError(f"{field_name} must not contain duplicates")
    return result


def _mutable_scope_is_authorized(allowed: tuple[str, ...], mutable: tuple[str, ...]) -> bool:
    """Fail closed unless every mutation expression is provably within allowed scope."""
    for expression in mutable:
        if expression in allowed:
            continue
        if any(ch in expression for ch in "*?["):
            return False
        if not any(fnmatchcase(expression, pattern) for pattern in allowed):
            return False
    return True


def _timestamp(value: object, field_name: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError(f"{field_name} must be timezone-aware")
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    return _text(value, field_name, max_length=64)  # type: ignore[arg-type]


def _timestamp_datetime(value: object, field_name: str) -> datetime:
    text = _timestamp(value, field_name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _timestamp_add_seconds(value: object, seconds: int, field_name: str) -> str:
    return _timestamp(_timestamp_datetime(value, field_name) + timedelta(seconds=seconds), field_name)


def _timestamp_compare(left: object, right: object) -> int:
    a = _timestamp_datetime(left, "timestamp")
    b = _timestamp_datetime(right, "timestamp")
    return (a > b) - (a < b)


@dataclass(frozen=True, slots=True)
class WorkerLeaseCandidate:
    worker_id: str
    state: str
    reserved: bool
    active_task: bool
    capabilities: tuple[str, ...]
    runtime_id: str | None
    project_id: str | None
    worktree: str | None
    branch: str | None
    head: str | None
    health_fresh: bool
    ownership_known: bool
    dirty_state: str
    mutation_authorized: bool
    occupied_mutable_scopes: tuple[tuple[str, ...], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "worker_id", _text(self.worker_id, "worker_id", max_length=128))
        object.__setattr__(self, "state", _text(self.state, "state", max_length=32).upper())
        object.__setattr__(self, "reserved", _bool(self.reserved, "reserved"))
        object.__setattr__(self, "active_task", _bool(self.active_task, "active_task"))
        object.__setattr__(self, "capabilities", _scope(self.capabilities, "capabilities"))
        object.__setattr__(self, "runtime_id", _optional_text(self.runtime_id, "runtime_id"))
        object.__setattr__(self, "project_id", _optional_text(self.project_id, "project_id"))
        object.__setattr__(self, "worktree", _optional_text(self.worktree, "worktree"))
        object.__setattr__(self, "branch", _optional_text(self.branch, "branch"))
        object.__setattr__(self, "head", _optional_text(self.head, "head"))
        object.__setattr__(self, "health_fresh", _bool(self.health_fresh, "health_fresh"))
        object.__setattr__(self, "ownership_known", _bool(self.ownership_known, "ownership_known"))
        object.__setattr__(self, "mutation_authorized", _bool(self.mutation_authorized, "mutation_authorized"))
        dirty = _text(self.dirty_state, "dirty_state", max_length=16).upper()
        if dirty not in _DIRTY_STATES:
            raise ValueError("dirty_state is invalid")
        object.__setattr__(self, "dirty_state", dirty)
        scopes: list[tuple[str, ...]] = []
        for item in self.occupied_mutable_scopes:
            scopes.append(_scope(item, "occupied_mutable_scopes"))
        object.__setattr__(self, "occupied_mutable_scopes", tuple(scopes))


@dataclass(frozen=True, slots=True)
class WorkerLeaseRequest:
    session_id: str
    task_id: str
    project_id: str
    ordered_worker_ids: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    required_runtime_id: str | None
    worktree: str
    branch: str
    expected_head: str
    mutation_intent: LeaseMutationIntent
    allowed_scope: tuple[str, ...] = ()
    forbidden_scope: tuple[str, ...] = ()
    mutable_scope: tuple[str, ...] = ()
    rdc_fallback_eligible: bool = False
    lease_ttl_seconds: int = 300

    def __post_init__(self) -> None:
        object.__setattr__(self, "session_id", _text(self.session_id, "session_id", max_length=128))
        object.__setattr__(self, "task_id", _text(self.task_id, "task_id", max_length=256))
        object.__setattr__(self, "project_id", _text(self.project_id, "project_id", max_length=128))
        workers = _scope(self.ordered_worker_ids, "ordered_worker_ids")
        if not workers:
            raise ValueError("ordered_worker_ids must not be empty")
        object.__setattr__(self, "ordered_worker_ids", workers)
        object.__setattr__(self, "required_capabilities", _scope(self.required_capabilities, "required_capabilities"))
        object.__setattr__(self, "required_runtime_id", _optional_text(self.required_runtime_id, "required_runtime_id"))
        object.__setattr__(self, "worktree", _text(self.worktree, "worktree"))
        object.__setattr__(self, "branch", _text(self.branch, "branch", max_length=256))
        head = _text(self.expected_head, "expected_head", max_length=64)
        if not _HEAD_RE.fullmatch(head):
            raise ValueError("expected_head must be a git object id")
        object.__setattr__(self, "expected_head", head.lower())
        if not isinstance(self.mutation_intent, LeaseMutationIntent):
            raise ValueError("mutation_intent must be LeaseMutationIntent")
        allowed = _scope(self.allowed_scope, "allowed_scope")
        forbidden = _scope(self.forbidden_scope, "forbidden_scope")
        mutable = _scope(self.mutable_scope, "mutable_scope")
        object.__setattr__(self, "allowed_scope", allowed)
        object.__setattr__(self, "forbidden_scope", forbidden)
        object.__setattr__(self, "mutable_scope", mutable)
        object.__setattr__(self, "rdc_fallback_eligible", _bool(self.rdc_fallback_eligible, "rdc_fallback_eligible"))
        if not isinstance(self.lease_ttl_seconds, int) or isinstance(self.lease_ttl_seconds, bool):
            raise ValueError("lease_ttl_seconds must be int")
        if self.lease_ttl_seconds < 1 or self.lease_ttl_seconds > 86400:
            raise ValueError("lease_ttl_seconds must be between 1 and 86400")
        if self.mutation_intent is LeaseMutationIntent.READ_ONLY and mutable:
            raise ValueError("read-only lease cannot request mutable_scope")
        if self.mutation_intent is LeaseMutationIntent.MUTATION and not mutable:
            raise ValueError("mutation lease requires mutable_scope")
        if self.mutation_intent is LeaseMutationIntent.MUTATION and not _mutable_scope_is_authorized(allowed, mutable):
            raise ValueError("mutable_scope escapes allowed_scope")
        if mutable and forbidden and write_sets_overlap(mutable, forbidden):
            raise ValueError("mutable_scope overlaps forbidden_scope")


@dataclass(frozen=True, slots=True)
class WorkerLease:
    lease_id: str
    worker_id: str
    session_id: str
    task_id: str
    project_id: str
    runtime_id: str | None
    worktree_key: str
    branch: str
    expected_head: str
    required_capabilities: tuple[str, ...]
    allowed_scope: tuple[str, ...]
    forbidden_scope: tuple[str, ...]
    mutable_scope: tuple[str, ...]
    mutation_intent: LeaseMutationIntent
    acquired_at: str
    heartbeat_at: str
    lease_ttl_seconds: int
    expires_at: str | None = None
    released_at: str | None = None
    quarantined_at: str | None = None
    quarantine_code: str | None = None
    recovery_classification: RecoveryClassification | None = None
    recovery_evidence_ref: str | None = None
    reconciled_at: str | None = None


@dataclass(frozen=True, slots=True)
class CandidateRejection:
    worker_id: str
    kind: CandidateRejectionKind


@dataclass(frozen=True, slots=True)
class WorkerLeaseOutcome:
    kind: LeaseOutcomeKind
    lease: WorkerLease | None = None
    rejections: tuple[CandidateRejection, ...] = ()


@dataclass(frozen=True, slots=True)
class LeaseHealth:
    kind: LeaseHealthKind
    lease: WorkerLease


@dataclass(frozen=True, slots=True)
class WorkerLeaseRecoveryObservation:
    worker_id: str
    worktree: str
    branch: str
    head: str
    dirty_state: str
    ownership_known: bool
    runtime_running: bool | None
    recovery_classification: RecoveryClassification
    evidence_ref: str
    observed_at: object

    def __post_init__(self) -> None:
        object.__setattr__(self, "worker_id", _text(self.worker_id, "worker_id", max_length=128))
        object.__setattr__(self, "worktree", _text(self.worktree, "worktree"))
        object.__setattr__(self, "branch", _text(self.branch, "branch", max_length=256))
        head = _text(self.head, "head", max_length=64)
        if not _HEAD_RE.fullmatch(head):
            raise ValueError("head must be a git object id")
        object.__setattr__(self, "head", head.lower())
        dirty = _text(self.dirty_state, "dirty_state", max_length=16).upper()
        if dirty not in _DIRTY_STATES:
            raise ValueError("dirty_state is invalid")
        object.__setattr__(self, "dirty_state", dirty)
        object.__setattr__(self, "ownership_known", _bool(self.ownership_known, "ownership_known"))
        if self.runtime_running is not None:
            object.__setattr__(self, "runtime_running", _bool(self.runtime_running, "runtime_running"))
        if not isinstance(self.recovery_classification, RecoveryClassification):
            raise ValueError("recovery_classification must be RecoveryClassification")
        object.__setattr__(self, "evidence_ref", _text(self.evidence_ref, "evidence_ref", max_length=512))
        object.__setattr__(self, "observed_at", _timestamp(self.observed_at, "observed_at"))


@dataclass(frozen=True, slots=True)
class LeaseReconciliationResult:
    kind: LeaseReconciliationKind
    lease: WorkerLease
    reason_code: str


@dataclass(frozen=True, slots=True)
class LeaseReleaseResult:
    released: bool
    already_released: bool


@dataclass(frozen=True, slots=True)
class LeaseStoreAcquireResult:
    lease: WorkerLease | None
    created: bool


def _decode_scope(raw: str) -> tuple[str, ...]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WorkerLeaseError("LEASE_DATA_INVALID") from exc
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise WorkerLeaseError("LEASE_DATA_INVALID")
    return tuple(value)


def _lease_from_row(row: sqlite3.Row) -> WorkerLease:
    try:
        intent = LeaseMutationIntent(row["mutation_intent"])
        recovery_raw = row["recovery_classification"]
        recovery = RecoveryClassification(recovery_raw) if recovery_raw is not None else None
        ttl = int(row["lease_ttl_seconds"])
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        raise WorkerLeaseError("LEASE_DATA_INVALID") from exc
    return WorkerLease(
        lease_id=row["lease_id"], worker_id=row["worker_id"],
        session_id=row["session_id"], task_id=row["task_id"], project_id=row["project_id"],
        runtime_id=row["runtime_id"], worktree_key=row["worktree_key"], branch=row["branch"],
        expected_head=row["expected_head"],
        required_capabilities=_decode_scope(row["required_capabilities_json"]),
        allowed_scope=_decode_scope(row["allowed_scope_json"]),
        forbidden_scope=_decode_scope(row["forbidden_scope_json"]),
        mutable_scope=_decode_scope(row["mutable_scope_json"]), mutation_intent=intent,
        acquired_at=row["acquired_at"], heartbeat_at=row["heartbeat_at"], lease_ttl_seconds=ttl,
        expires_at=row["expires_at"], released_at=row["released_at"],
        quarantined_at=row["quarantined_at"], quarantine_code=row["quarantine_code"],
        recovery_classification=recovery, recovery_evidence_ref=row["recovery_evidence_ref"],
        reconciled_at=row["reconciled_at"],
    )


def _request_matches_lease(request: WorkerLeaseRequest, lease: WorkerLease) -> bool:
    return (
        lease.worker_id in request.ordered_worker_ids
        and lease.project_id == request.project_id
        and lease.worktree_key == windows_worktree_key(request.worktree)
        and lease.branch == request.branch
        and lease.expected_head.casefold() == request.expected_head.casefold()
        and lease.mutation_intent is request.mutation_intent
        and frozenset(lease.required_capabilities) == frozenset(request.required_capabilities)
        and frozenset(lease.allowed_scope) == frozenset(request.allowed_scope)
        and frozenset(lease.forbidden_scope) == frozenset(request.forbidden_scope)
        and frozenset(lease.mutable_scope) == frozenset(request.mutable_scope)
        and lease.lease_ttl_seconds == request.lease_ttl_seconds
        and (request.required_runtime_id is None or lease.runtime_id == request.required_runtime_id)
    )


def _require_matching_request(request: WorkerLeaseRequest, lease: WorkerLease) -> WorkerLease:
    if not _request_matches_lease(request, lease):
        raise WorkerLeaseError("LEASE_REQUEST_CONFLICT")
    return lease


def _lease_health_kind(lease: WorkerLease, *, now: object) -> LeaseHealthKind:
    if lease.released_at is not None:
        return LeaseHealthKind.RELEASED
    if lease.quarantine_code is not None:
        return LeaseHealthKind.QUARANTINED
    if lease.expires_at is None:
        return LeaseHealthKind.EXPIRY_UNKNOWN
    if _timestamp_compare(now, lease.expires_at) >= 0:
        return LeaseHealthKind.STALE
    return LeaseHealthKind.ACTIVE


def _reconciliation_quarantine_reason(
    lease: WorkerLease,
    observation: WorkerLeaseRecoveryObservation,
) -> str | None:
    if observation.worker_id != lease.worker_id:
        return "WORKER_MISMATCH"
    if not observation.ownership_known:
        return "OWNERSHIP_UNKNOWN"
    try:
        if windows_worktree_key(observation.worktree) != lease.worktree_key:
            return "WORKTREE_MISMATCH"
    except ValueError:
        return "WORKTREE_MISMATCH"
    if observation.branch != lease.branch:
        return "BRANCH_MISMATCH"
    if observation.runtime_running is None:
        return "RUNTIME_STATE_UNKNOWN"
    if observation.runtime_running:
        return "RUNTIME_STILL_RUNNING"
    if observation.dirty_state == "UNKNOWN":
        return "WORKTREE_DIRTY_UNKNOWN"
    if observation.dirty_state != "CLEAN":
        return "WORKTREE_DIRTY"
    classification = observation.recovery_classification
    if classification is RecoveryClassification.UNKNOWN:
        return "RECOVERY_UNKNOWN"
    if classification is RecoveryClassification.PARTIAL_MUTATION:
        return "PARTIAL_MUTATION"
    if classification is RecoveryClassification.MUTATION_COMPLETE_UNVERIFIED:
        return "MUTATION_COMPLETE_UNVERIFIED"
    if classification is RecoveryClassification.UNEXPECTED_DRIFT:
        return "UNEXPECTED_DRIFT"
    if classification is RecoveryClassification.NO_MUTATION:
        if observation.head.casefold() != lease.expected_head.casefold():
            return "HEAD_MISMATCH"
        return None
    if classification is RecoveryClassification.COMPLETE_VERIFIED:
        return None
    return "RECOVERY_UNKNOWN"


class SQLiteWorkerLeaseStore:
    """Atomic worker-capacity leases in one SQLite database."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS worker_leases (
                    lease_id TEXT PRIMARY KEY,
                    worker_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    runtime_id TEXT,
                    worktree_key TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    expected_head TEXT NOT NULL,
                    required_capabilities_json TEXT NOT NULL,
                    allowed_scope_json TEXT NOT NULL,
                    forbidden_scope_json TEXT NOT NULL,
                    mutable_scope_json TEXT NOT NULL,
                    mutation_intent TEXT NOT NULL,
                    acquired_at TEXT NOT NULL,
                    heartbeat_at TEXT NOT NULL,
                    lease_ttl_seconds INTEGER NOT NULL,
                    expires_at TEXT,
                    released_at TEXT,
                    quarantined_at TEXT,
                    quarantine_code TEXT,
                    recovery_classification TEXT,
                    recovery_evidence_ref TEXT,
                    reconciled_at TEXT
                );
                CREATE UNIQUE INDEX IF NOT EXISTS ux_worker_leases_active_worker
                    ON worker_leases(worker_id) WHERE released_at IS NULL;
                CREATE UNIQUE INDEX IF NOT EXISTS ux_worker_leases_active_owner_task
                    ON worker_leases(session_id, task_id) WHERE released_at IS NULL;
                """
            )
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(worker_leases)")}
            migrations = {
                "heartbeat_at": "TEXT",
                "lease_ttl_seconds": "INTEGER",
                "quarantined_at": "TEXT",
                "quarantine_code": "TEXT",
                "recovery_classification": "TEXT",
                "recovery_evidence_ref": "TEXT",
                "reconciled_at": "TEXT",
            }
            for name, sql_type in migrations.items():
                if name not in columns:
                    connection.execute(f"ALTER TABLE worker_leases ADD COLUMN {name} {sql_type}")
            connection.execute(
                "UPDATE worker_leases SET heartbeat_at = acquired_at WHERE heartbeat_at IS NULL"
            )
            legacy_rows = connection.execute(
                "SELECT lease_id, acquired_at, expires_at FROM worker_leases "
                "WHERE lease_ttl_seconds IS NULL"
            ).fetchall()
            for row in legacy_rows:
                ttl = 300
                if row["expires_at"] is not None:
                    try:
                        delta = int(
                            (_timestamp_datetime(row["expires_at"], "expires_at") -
                             _timestamp_datetime(row["acquired_at"], "acquired_at")).total_seconds()
                        )
                        if 1 <= delta <= 86400:
                            ttl = delta
                    except ValueError:
                        pass
                connection.execute(
                    "UPDATE worker_leases SET lease_ttl_seconds = ? WHERE lease_id = ?",
                    (ttl, row["lease_id"]),
                )
            connection.commit()

    def find_active_owner_task(self, session_id: str, task_id: str) -> WorkerLease | None:
        session_id = _text(session_id, "session_id", max_length=128)
        task_id = _text(task_id, "task_id", max_length=256)
        with self._connect() as connection:
            try:
                row = connection.execute(
                    "SELECT * FROM worker_leases WHERE session_id = ? AND task_id = ? "
                    "AND released_at IS NULL",
                    (session_id, task_id),
                ).fetchone()
            except sqlite3.Error as exc:
                raise WorkerLeaseError("LEASE_STORE_READ_FAILED") from exc
        return None if row is None else _lease_from_row(row)

    def try_acquire_result(
        self,
        request: WorkerLeaseRequest,
        candidate: WorkerLeaseCandidate,
        *,
        lease_id: str,
        acquired_at: object,
        expires_at: str | None = None,
    ) -> LeaseStoreAcquireResult:
        lease_id = _text(lease_id, "lease_id", max_length=128)
        acquired = _timestamp(acquired_at, "acquired_at")
        expiry = _optional_text(expires_at, "expires_at")
        if expiry is None:
            expiry = _timestamp_add_seconds(acquired, request.lease_ttl_seconds, "expires_at")
        else:
            _timestamp_datetime(expiry, "expires_at")
        lease = WorkerLease(
            lease_id=lease_id, worker_id=candidate.worker_id,
            session_id=request.session_id, task_id=request.task_id,
            project_id=request.project_id, runtime_id=candidate.runtime_id,
            worktree_key=windows_worktree_key(request.worktree), branch=request.branch,
            expected_head=request.expected_head,
            required_capabilities=request.required_capabilities, allowed_scope=request.allowed_scope,
            forbidden_scope=request.forbidden_scope, mutable_scope=request.mutable_scope,
            mutation_intent=request.mutation_intent, acquired_at=acquired, heartbeat_at=acquired,
            lease_ttl_seconds=request.lease_ttl_seconds, expires_at=expiry,
        )
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                active_owner = connection.execute(
                    "SELECT * FROM worker_leases WHERE session_id = ? AND task_id = ? "
                    "AND released_at IS NULL",
                    (lease.session_id, lease.task_id),
                ).fetchone()
                if active_owner is not None:
                    existing = _require_matching_request(request, _lease_from_row(active_owner))
                    connection.rollback()
                    return LeaseStoreAcquireResult(existing, created=False)
                active_worker = connection.execute(
                    "SELECT lease_id FROM worker_leases WHERE worker_id = ? AND released_at IS NULL",
                    (lease.worker_id,),
                ).fetchone()
                if active_worker is not None:
                    connection.rollback()
                    return LeaseStoreAcquireResult(None, created=False)
                if lease.mutation_intent is LeaseMutationIntent.MUTATION:
                    rows = connection.execute(
                        "SELECT mutable_scope_json FROM worker_leases "
                        "WHERE released_at IS NULL AND worktree_key = ? AND mutation_intent = ?",
                        (lease.worktree_key, LeaseMutationIntent.MUTATION.value),
                    ).fetchall()
                    for row in rows:
                        if write_sets_overlap(lease.mutable_scope, _decode_scope(row["mutable_scope_json"])):
                            connection.rollback()
                            raise WorkerLeaseError("MUTABLE_SCOPE_OVERLAP")
                connection.execute(
                    "INSERT INTO worker_leases(lease_id, worker_id, session_id, task_id, "
                    "project_id, runtime_id, worktree_key, branch, expected_head, "
                    "required_capabilities_json, allowed_scope_json, forbidden_scope_json, mutable_scope_json, "
                    "mutation_intent, acquired_at, heartbeat_at, lease_ttl_seconds, expires_at, released_at, "
                    "quarantined_at, quarantine_code, recovery_classification, recovery_evidence_ref, reconciled_at) "
                    "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, NULL)",
                    (
                        lease.lease_id, lease.worker_id, lease.session_id, lease.task_id,
                        lease.project_id, lease.runtime_id, lease.worktree_key, lease.branch,
                        lease.expected_head, json.dumps(lease.required_capabilities),
                        json.dumps(lease.allowed_scope),
                        json.dumps(lease.forbidden_scope), json.dumps(lease.mutable_scope),
                        lease.mutation_intent.value, lease.acquired_at, lease.heartbeat_at,
                        lease.lease_ttl_seconds, lease.expires_at,
                    ),
                )
                connection.commit()
                return LeaseStoreAcquireResult(lease, created=True)
            except WorkerLeaseError:
                connection.rollback()
                raise
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                active = connection.execute(
                    "SELECT lease_id FROM worker_leases WHERE worker_id = ? AND released_at IS NULL",
                    (candidate.worker_id,),
                ).fetchone()
                if active is not None:
                    return LeaseStoreAcquireResult(None, created=False)
                raise WorkerLeaseError("LEASE_ID_CONFLICT") from exc
            except sqlite3.Error as exc:
                connection.rollback()
                raise WorkerLeaseError("LEASE_STORE_WRITE_FAILED") from exc

    def try_acquire(
        self,
        request: WorkerLeaseRequest,
        candidate: WorkerLeaseCandidate,
        *,
        lease_id: str,
        acquired_at: object,
        expires_at: str | None = None,
    ) -> WorkerLease | None:
        return self.try_acquire_result(
            request,
            candidate,
            lease_id=lease_id,
            acquired_at=acquired_at,
            expires_at=expires_at,
        ).lease

    def inspect_health(self, lease_id: str, *, now: object) -> LeaseHealth:
        lease_id = _text(lease_id, "lease_id", max_length=128)
        now_text = _timestamp(now, "now")
        with self._connect() as connection:
            try:
                row = connection.execute(
                    "SELECT * FROM worker_leases WHERE lease_id = ?", (lease_id,)
                ).fetchone()
            except sqlite3.Error as exc:
                raise WorkerLeaseError("LEASE_STORE_READ_FAILED") from exc
        if row is None:
            raise WorkerLeaseError("LEASE_NOT_FOUND")
        lease = _lease_from_row(row)
        return LeaseHealth(_lease_health_kind(lease, now=now_text), lease)

    def heartbeat(
        self,
        lease_id: str,
        *,
        session_id: str,
        task_id: str,
        heartbeat_at: object,
    ) -> WorkerLease:
        lease_id = _text(lease_id, "lease_id", max_length=128)
        session_id = _text(session_id, "session_id", max_length=128)
        task_id = _text(task_id, "task_id", max_length=256)
        beat = _timestamp(heartbeat_at, "heartbeat_at")
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT * FROM worker_leases WHERE lease_id = ?", (lease_id,)
                ).fetchone()
                if row is None:
                    connection.rollback()
                    raise WorkerLeaseError("LEASE_NOT_FOUND")
                lease = _lease_from_row(row)
                if lease.session_id != session_id or lease.task_id != task_id:
                    connection.rollback()
                    raise WorkerLeaseError("LEASE_OWNER_MISMATCH")
                if lease.released_at is not None:
                    connection.rollback()
                    raise WorkerLeaseError("LEASE_RELEASED")
                if lease.quarantine_code is not None:
                    connection.rollback()
                    raise WorkerLeaseError("LEASE_QUARANTINED")
                if lease.expires_at is None:
                    connection.rollback()
                    raise WorkerLeaseError("LEASE_EXPIRY_UNKNOWN")
                order = _timestamp_compare(beat, lease.heartbeat_at)
                if order < 0:
                    connection.rollback()
                    raise WorkerLeaseError("LEASE_HEARTBEAT_STALE")
                if order == 0:
                    connection.rollback()
                    return lease
                if _timestamp_compare(beat, lease.expires_at) >= 0:
                    connection.rollback()
                    raise WorkerLeaseError("LEASE_HEARTBEAT_EXPIRED")
                expiry = _timestamp_add_seconds(beat, lease.lease_ttl_seconds, "expires_at")
                connection.execute(
                    "UPDATE worker_leases SET heartbeat_at = ?, expires_at = ? "
                    "WHERE lease_id = ? AND released_at IS NULL",
                    (beat, expiry, lease_id),
                )
                updated = connection.execute(
                    "SELECT * FROM worker_leases WHERE lease_id = ?", (lease_id,)
                ).fetchone()
                connection.commit()
                if updated is None:
                    raise WorkerLeaseError("LEASE_DATA_INVALID")
                return _lease_from_row(updated)
            except WorkerLeaseError:
                connection.rollback()
                raise
            except sqlite3.Error as exc:
                connection.rollback()
                raise WorkerLeaseError("LEASE_STORE_WRITE_FAILED") from exc

    def reconcile_stale(
        self,
        lease_id: str,
        *,
        session_id: str,
        task_id: str,
        observation: WorkerLeaseRecoveryObservation,
    ) -> LeaseReconciliationResult:
        lease_id = _text(lease_id, "lease_id", max_length=128)
        session_id = _text(session_id, "session_id", max_length=128)
        task_id = _text(task_id, "task_id", max_length=256)
        if not isinstance(observation, WorkerLeaseRecoveryObservation):
            raise ValueError("observation must be WorkerLeaseRecoveryObservation")
        observed = _timestamp(observation.observed_at, "observed_at")
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT * FROM worker_leases WHERE lease_id = ?", (lease_id,)
                ).fetchone()
                if row is None:
                    connection.rollback()
                    raise WorkerLeaseError("LEASE_NOT_FOUND")
                lease = _lease_from_row(row)
                if lease.session_id != session_id or lease.task_id != task_id:
                    connection.rollback()
                    raise WorkerLeaseError("LEASE_OWNER_MISMATCH")
                if lease.released_at is not None:
                    connection.rollback()
                    raise WorkerLeaseError("LEASE_RELEASED")
                latest_evidence_at = lease.heartbeat_at
                for value in (lease.quarantined_at, lease.reconciled_at):
                    if value is not None and _timestamp_compare(value, latest_evidence_at) > 0:
                        latest_evidence_at = value
                if _timestamp_compare(observed, latest_evidence_at) < 0:
                    connection.rollback()
                    raise WorkerLeaseError("LEASE_OBSERVATION_STALE")
                health = _lease_health_kind(lease, now=observed)
                if health is LeaseHealthKind.ACTIVE:
                    connection.rollback()
                    raise WorkerLeaseError("LEASE_NOT_STALE")
                reason = _reconciliation_quarantine_reason(lease, observation)
                classification = observation.recovery_classification.value
                if reason is None:
                    connection.execute(
                        "UPDATE worker_leases SET released_at = ?, recovery_classification = ?, "
                        "recovery_evidence_ref = ?, reconciled_at = ? WHERE lease_id = ? AND released_at IS NULL",
                        (observed, classification, observation.evidence_ref, observed, lease_id),
                    )
                    kind = LeaseReconciliationKind.RELEASED
                    reason_code = "RECONCILED_SAFE_RELEASE"
                else:
                    connection.execute(
                        "UPDATE worker_leases SET quarantined_at = COALESCE(quarantined_at, ?), "
                        "quarantine_code = ?, recovery_classification = ?, recovery_evidence_ref = ?, "
                        "reconciled_at = ? WHERE lease_id = ? AND released_at IS NULL",
                        (observed, reason, classification, observation.evidence_ref, observed, lease_id),
                    )
                    kind = LeaseReconciliationKind.QUARANTINED
                    reason_code = reason
                updated = connection.execute(
                    "SELECT * FROM worker_leases WHERE lease_id = ?", (lease_id,)
                ).fetchone()
                connection.commit()
                if updated is None:
                    raise WorkerLeaseError("LEASE_DATA_INVALID")
                return LeaseReconciliationResult(kind, _lease_from_row(updated), reason_code)
            except WorkerLeaseError:
                connection.rollback()
                raise
            except sqlite3.Error as exc:
                connection.rollback()
                raise WorkerLeaseError("LEASE_STORE_WRITE_FAILED") from exc

    def list_active(self) -> tuple[WorkerLease, ...]:
        with self._connect() as connection:
            try:
                rows = connection.execute(
                    "SELECT * FROM worker_leases WHERE released_at IS NULL ORDER BY worker_id, lease_id"
                ).fetchall()
            except sqlite3.Error as exc:
                raise WorkerLeaseError("LEASE_STORE_READ_FAILED") from exc
        return tuple(_lease_from_row(row) for row in rows)

    def release(
        self,
        lease_id: str,
        *,
        session_id: str,
        task_id: str,
        released_at: object,
    ) -> LeaseReleaseResult:
        lease_id = _text(lease_id, "lease_id", max_length=128)
        session_id = _text(session_id, "session_id", max_length=128)
        task_id = _text(task_id, "task_id", max_length=256)
        released = _timestamp(released_at, "released_at")
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT * FROM worker_leases WHERE lease_id = ?",
                    (lease_id,),
                ).fetchone()
                if row is None:
                    connection.rollback()
                    raise WorkerLeaseError("LEASE_NOT_FOUND")
                lease = _lease_from_row(row)
                if lease.session_id != session_id or lease.task_id != task_id:
                    connection.rollback()
                    raise WorkerLeaseError("LEASE_OWNER_MISMATCH")
                if lease.released_at is not None:
                    connection.rollback()
                    return LeaseReleaseResult(released=False, already_released=True)
                if _timestamp_compare(released, lease.heartbeat_at) < 0:
                    connection.rollback()
                    raise WorkerLeaseError("LEASE_RELEASE_STALE")
                if lease.quarantine_code is not None:
                    connection.rollback()
                    raise WorkerLeaseError("LEASE_RECOVERY_REQUIRED")
                if lease.expires_at is None or _timestamp_compare(released, lease.expires_at) >= 0:
                    connection.rollback()
                    raise WorkerLeaseError("LEASE_RECOVERY_REQUIRED")
                connection.execute(
                    "UPDATE worker_leases SET released_at = ? WHERE lease_id = ? AND released_at IS NULL",
                    (released, lease_id),
                )
                connection.commit()
                return LeaseReleaseResult(released=True, already_released=False)
            except WorkerLeaseError:
                raise
            except sqlite3.Error as exc:
                connection.rollback()
                raise WorkerLeaseError("LEASE_STORE_WRITE_FAILED") from exc


def _preflight(
    request: WorkerLeaseRequest,
    candidate: WorkerLeaseCandidate,
) -> CandidateRejectionKind | None:
    if candidate.active_task:
        return CandidateRejectionKind.ACTIVE_TASK
    if candidate.state != "READY":
        return CandidateRejectionKind.WORKER_NOT_READY
    if candidate.reserved:
        return CandidateRejectionKind.WORKER_RESERVED
    if not all(item in candidate.capabilities for item in request.required_capabilities):
        return CandidateRejectionKind.CAPABILITY_MISMATCH
    if request.required_runtime_id is not None and candidate.runtime_id != request.required_runtime_id:
        return CandidateRejectionKind.RUNTIME_MISMATCH
    if candidate.project_id != request.project_id:
        return CandidateRejectionKind.PROJECT_MISMATCH
    if candidate.worktree is None:
        return CandidateRejectionKind.WORKTREE_MISMATCH
    try:
        if windows_worktree_key(candidate.worktree) != windows_worktree_key(request.worktree):
            return CandidateRejectionKind.WORKTREE_MISMATCH
    except ValueError:
        return CandidateRejectionKind.WORKTREE_MISMATCH
    if candidate.branch != request.branch:
        return CandidateRejectionKind.BRANCH_MISMATCH
    if candidate.head is None or candidate.head.casefold() != request.expected_head.casefold():
        return CandidateRejectionKind.HEAD_MISMATCH
    if not candidate.health_fresh:
        return CandidateRejectionKind.HEALTH_STALE
    if not candidate.ownership_known:
        return CandidateRejectionKind.OWNERSHIP_UNKNOWN
    if candidate.dirty_state == "UNKNOWN":
        return CandidateRejectionKind.DIRTY_UNKNOWN
    if request.mutation_intent is LeaseMutationIntent.MUTATION:
        if candidate.dirty_state != "CLEAN":
            return CandidateRejectionKind.DIRTY_WORKTREE
        if not candidate.mutation_authorized:
            return CandidateRejectionKind.MUTATION_UNAUTHORIZED
        for occupied in candidate.occupied_mutable_scopes:
            if write_sets_overlap(request.mutable_scope, occupied):
                return CandidateRejectionKind.MUTABLE_SCOPE_OVERLAP
    return None


class WorkerLeaseBroker:
    def __init__(
        self,
        *,
        store: SQLiteWorkerLeaseStore,
        lease_id_factory: Callable[[], str],
        clock: Callable[[], object],
    ) -> None:
        if (
            not callable(getattr(store, "try_acquire_result", None))
            or not callable(getattr(store, "find_active_owner_task", None))
            or not callable(getattr(store, "inspect_health", None))
        ):
            raise ValueError("store must provide acquire, owner lookup and health inspection")
        if not callable(lease_id_factory):
            raise ValueError("lease_id_factory must be callable")
        if not callable(clock):
            raise ValueError("clock must be callable")
        self._store = store
        self._lease_id_factory = lease_id_factory
        self._clock = clock

    def acquire(
        self,
        request: WorkerLeaseRequest,
        candidates: Sequence[WorkerLeaseCandidate],
    ) -> WorkerLeaseOutcome:
        if not isinstance(request, WorkerLeaseRequest):
            raise ValueError("request must be WorkerLeaseRequest")
        now = self._clock()
        existing = self._store.find_active_owner_task(request.session_id, request.task_id)
        if existing is not None:
            matching = _require_matching_request(request, existing)
            health = self._store.inspect_health(matching.lease_id, now=now)
            if health.kind is LeaseHealthKind.ACTIVE:
                return WorkerLeaseOutcome(LeaseOutcomeKind.EXISTING, matching, ())
            return WorkerLeaseOutcome(LeaseOutcomeKind.RECOVERY_REQUIRED, matching, ())
        if isinstance(candidates, (str, bytes)):
            raise ValueError("candidates must be a sequence")
        by_worker: dict[str, WorkerLeaseCandidate] = {}
        for item in candidates:
            if not isinstance(item, WorkerLeaseCandidate):
                raise ValueError("candidate must be WorkerLeaseCandidate")
            if item.worker_id in by_worker:
                raise ValueError("candidate worker_id must be unique")
            by_worker[item.worker_id] = item

        rejections: list[CandidateRejection] = []
        for worker_id in request.ordered_worker_ids:
            item = by_worker.get(worker_id)
            if item is None:
                rejections.append(CandidateRejection(worker_id, CandidateRejectionKind.CANDIDATE_MISSING))
                continue
            reason = _preflight(request, item)
            if reason is not None:
                rejections.append(CandidateRejection(worker_id, reason))
                continue
            try:
                proposed_lease_id = _text(self._lease_id_factory(), "lease_id", max_length=128)
                acquire_result = self._store.try_acquire_result(
                    request,
                    item,
                    lease_id=proposed_lease_id,
                    acquired_at=now,
                )
                lease = acquire_result.lease
            except WorkerLeaseError as exc:
                if exc.code != "MUTABLE_SCOPE_OVERLAP":
                    raise
                rejections.append(
                    CandidateRejection(worker_id, CandidateRejectionKind.MUTABLE_SCOPE_OVERLAP)
                )
                continue
            if lease is not None:
                kind = LeaseOutcomeKind.LEASED if acquire_result.created else LeaseOutcomeKind.EXISTING
                return WorkerLeaseOutcome(kind, lease, tuple(rejections))
            rejections.append(CandidateRejection(worker_id, CandidateRejectionKind.LEASE_BUSY))

        if request.mutation_intent is LeaseMutationIntent.READ_ONLY and request.rdc_fallback_eligible:
            return WorkerLeaseOutcome(LeaseOutcomeKind.RDC_READ_ONLY, None, tuple(rejections))
        return WorkerLeaseOutcome(LeaseOutcomeKind.WAIT, None, tuple(rejections))
