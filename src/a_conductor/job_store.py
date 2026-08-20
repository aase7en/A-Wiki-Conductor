"""SQLite durable operational job state for A-Conductor.

The store wraps opaque A-Wiki work-order references and persists only runtime
state/checkpoint metadata. Planning content, prompts, transcripts, commands,
stdout/stderr, and model responses are deliberately outside this schema.
"""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Iterator

from .domain import RecoveryClassification, TaskState
from .job_state import (
    JobRuntimeState,
    JobStateError,
    new_job_state,
    plan_job_transition,
)


JOB_STORE_SCHEMA_VERSION = "1"
_TERMINAL_STATES = frozenset(
    {TaskState.COMPLETE, TaskState.FAILED, TaskState.CANCELLED}
)


class JobStoreError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class JobEventType(str, Enum):
    CREATED = "CREATED"
    TRANSITION = "TRANSITION"
    CHECKPOINT = "CHECKPOINT"


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


def _require_optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_text(value, field_name)


def _require_positive_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{field_name} must be >= 1")
    return value


@dataclass(frozen=True, slots=True)
class JobEvent:
    event_id: str
    job_id: str
    sequence_no: int
    event_type: JobEventType
    from_state: TaskState | None
    to_state: TaskState | None
    worker_id: str | None
    recovery_classification: RecoveryClassification | None
    checkpoint_ref: str | None
    evidence_ref: str | None
    recorded_at: str

    def __post_init__(self) -> None:
        _require_text(self.event_id, "event_id")
        _require_text(self.job_id, "job_id")
        _require_positive_int(self.sequence_no, "sequence_no")
        if not isinstance(self.event_type, JobEventType):
            raise ValueError("event_type must be a JobEventType")
        if self.from_state is not None and not isinstance(self.from_state, TaskState):
            raise ValueError("from_state must be a TaskState")
        if self.to_state is not None and not isinstance(self.to_state, TaskState):
            raise ValueError("to_state must be a TaskState")
        _require_optional_text(self.worker_id, "worker_id")
        if self.recovery_classification is not None and not isinstance(
            self.recovery_classification, RecoveryClassification
        ):
            raise ValueError("recovery_classification must be a RecoveryClassification")
        _require_optional_text(self.checkpoint_ref, "checkpoint_ref")
        _require_optional_text(self.evidence_ref, "evidence_ref")
        _require_text(self.recorded_at, "recorded_at")


class SQLiteJobStore:
    def __init__(
        self,
        database_path: str | Path,
        *,
        event_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self._event_id_factory = event_id_factory or (
            lambda: f"job-event-{uuid.uuid4().hex}"
        )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.database_path)
        except (OSError, sqlite3.Error) as exc:
            raise JobStoreError("JOB_STORE_OPEN_FAILED") from exc
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 5000")
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connect() as connection:
            try:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS job_store_meta (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS job_records (
                        job_id TEXT PRIMARY KEY CHECK (trim(job_id) <> ''),
                        work_order_ref TEXT NOT NULL CHECK (trim(work_order_ref) <> ''),
                        project_id TEXT NOT NULL CHECK (trim(project_id) <> ''),
                        state TEXT NOT NULL,
                        worker_id TEXT,
                        attempt_count INTEGER NOT NULL CHECK (attempt_count >= 0),
                        max_attempts INTEGER NOT NULL CHECK (max_attempts >= 1),
                        recovery_classification TEXT,
                        version INTEGER NOT NULL CHECK (version >= 1),
                        created_at TEXT NOT NULL DEFAULT (
                            strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        ),
                        updated_at TEXT NOT NULL DEFAULT (
                            strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        )
                    );

                    CREATE TABLE IF NOT EXISTS job_events (
                        event_id TEXT PRIMARY KEY CHECK (trim(event_id) <> ''),
                        job_id TEXT NOT NULL,
                        sequence_no INTEGER NOT NULL CHECK (sequence_no >= 1),
                        event_type TEXT NOT NULL,
                        from_state TEXT,
                        to_state TEXT,
                        worker_id TEXT,
                        recovery_classification TEXT,
                        checkpoint_ref TEXT,
                        evidence_ref TEXT,
                        recorded_at TEXT NOT NULL DEFAULT (
                            strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        ),
                        UNIQUE(job_id, sequence_no),
                        FOREIGN KEY(job_id) REFERENCES job_records(job_id)
                    );
                    """
                )
                row = connection.execute(
                    "SELECT value FROM job_store_meta WHERE key = 'schema_version'"
                ).fetchone()
                if row is None:
                    connection.execute(
                        "INSERT INTO job_store_meta(key, value) VALUES('schema_version', ?)",
                        (JOB_STORE_SCHEMA_VERSION,),
                    )
                elif row["value"] != JOB_STORE_SCHEMA_VERSION:
                    raise JobStoreError("JOB_STORE_SCHEMA_UNSUPPORTED")
                connection.commit()
            except JobStoreError:
                connection.rollback()
                raise
            except sqlite3.Error as exc:
                connection.rollback()
                raise JobStoreError("JOB_STORE_INITIALIZE_FAILED") from exc

    def _next_event_id(self) -> str:
        try:
            value = self._event_id_factory()
        except Exception as exc:
            raise JobStoreError("JOB_EVENT_ID_FAILED") from exc
        try:
            return _require_text(value, "event_id")
        except ValueError as exc:
            raise JobStoreError("JOB_EVENT_ID_INVALID") from exc

    @staticmethod
    def _state_from_row(row: sqlite3.Row) -> JobRuntimeState:
        try:
            recovery = row["recovery_classification"]
            return JobRuntimeState(
                job_id=row["job_id"],
                work_order_ref=row["work_order_ref"],
                project_id=row["project_id"],
                state=TaskState(row["state"]),
                worker_id=row["worker_id"],
                attempt_count=int(row["attempt_count"]),
                max_attempts=int(row["max_attempts"]),
                recovery_classification=(
                    RecoveryClassification(recovery) if recovery is not None else None
                ),
                version=int(row["version"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise JobStoreError("JOB_RECORD_INVALID") from exc

    @staticmethod
    def _load_job_row(connection: sqlite3.Connection, job_id: str) -> sqlite3.Row:
        row = connection.execute(
            "SELECT job_id, work_order_ref, project_id, state, worker_id, "
            "attempt_count, max_attempts, recovery_classification, version "
            "FROM job_records WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            raise JobStoreError("JOB_NOT_FOUND")
        return row

    @staticmethod
    def _next_sequence(connection: sqlite3.Connection, job_id: str) -> int:
        row = connection.execute(
            "SELECT MAX(sequence_no) AS max_sequence FROM job_events WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None or row["max_sequence"] is None:
            return 1
        return int(row["max_sequence"]) + 1

    def _insert_event(
        self,
        connection: sqlite3.Connection,
        *,
        job_id: str,
        event_type: JobEventType,
        from_state: TaskState | None,
        to_state: TaskState | None,
        worker_id: str | None,
        recovery_classification: RecoveryClassification | None,
        checkpoint_ref: str | None,
        evidence_ref: str | None,
    ) -> None:
        connection.execute(
            "INSERT INTO job_events("
            "event_id, job_id, sequence_no, event_type, from_state, to_state, "
            "worker_id, recovery_classification, checkpoint_ref, evidence_ref"
            ") VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                self._next_event_id(),
                job_id,
                self._next_sequence(connection, job_id),
                event_type.value,
                from_state.value if from_state is not None else None,
                to_state.value if to_state is not None else None,
                worker_id,
                (
                    recovery_classification.value
                    if recovery_classification is not None
                    else None
                ),
                checkpoint_ref,
                evidence_ref,
            ),
        )

    def create_job(
        self,
        *,
        job_id: str,
        work_order_ref: str,
        project_id: str,
        max_attempts: int = 3,
    ) -> JobRuntimeState:
        job = new_job_state(
            job_id=job_id,
            work_order_ref=work_order_ref,
            project_id=project_id,
            max_attempts=max_attempts,
        )
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    "SELECT 1 FROM job_records WHERE job_id = ?", (job.job_id,)
                ).fetchone()
                if existing is not None:
                    raise JobStoreError("JOB_ALREADY_EXISTS")
                connection.execute(
                    "INSERT INTO job_records("
                    "job_id, work_order_ref, project_id, state, worker_id, "
                    "attempt_count, max_attempts, recovery_classification, version"
                    ") VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        job.job_id,
                        job.work_order_ref,
                        job.project_id,
                        job.state.value,
                        job.worker_id,
                        job.attempt_count,
                        job.max_attempts,
                        None,
                        job.version,
                    ),
                )
                self._insert_event(
                    connection,
                    job_id=job.job_id,
                    event_type=JobEventType.CREATED,
                    from_state=None,
                    to_state=job.state,
                    worker_id=None,
                    recovery_classification=None,
                    checkpoint_ref=None,
                    evidence_ref=None,
                )
                connection.commit()
                return job
            except JobStoreError:
                connection.rollback()
                raise
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                raise JobStoreError("JOB_STORE_CONFLICT") from exc
            except sqlite3.Error as exc:
                connection.rollback()
                raise JobStoreError("JOB_STORE_WRITE_FAILED") from exc

    def get_job(self, job_id: str) -> JobRuntimeState:
        _require_text(job_id, "job_id")
        self.initialize()
        with self._connect() as connection:
            try:
                return self._state_from_row(self._load_job_row(connection, job_id))
            except JobStoreError:
                raise
            except sqlite3.Error as exc:
                raise JobStoreError("JOB_STORE_READ_FAILED") from exc

    @staticmethod
    def _check_version(current: JobRuntimeState, expected_version: int) -> None:
        _require_positive_int(expected_version, "expected_version")
        if current.version != expected_version:
            raise JobStoreError("JOB_VERSION_CONFLICT")

    def transition(
        self,
        job_id: str,
        target_state: TaskState,
        *,
        expected_version: int,
        worker_id: str | None = None,
        recovery_classification: RecoveryClassification | None = None,
        evidence_ref: str | None = None,
    ) -> JobRuntimeState:
        _require_text(job_id, "job_id")
        _require_positive_int(expected_version, "expected_version")
        _require_optional_text(evidence_ref, "evidence_ref")
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                current = self._state_from_row(self._load_job_row(connection, job_id))
                self._check_version(current, expected_version)
                plan = plan_job_transition(
                    current,
                    target_state,
                    worker_id=worker_id,
                    recovery_classification=recovery_classification,
                )
                next_version = current.version + 1
                cursor = connection.execute(
                    "UPDATE job_records SET state = ?, worker_id = ?, attempt_count = ?, "
                    "recovery_classification = ?, version = ?, "
                    "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
                    "WHERE job_id = ? AND version = ?",
                    (
                        plan.target_state.value,
                        plan.worker_id,
                        plan.attempt_count,
                        (
                            plan.recovery_classification.value
                            if plan.recovery_classification is not None
                            else None
                        ),
                        next_version,
                        current.job_id,
                        current.version,
                    ),
                )
                if cursor.rowcount != 1:
                    raise JobStoreError("JOB_VERSION_CONFLICT")
                self._insert_event(
                    connection,
                    job_id=current.job_id,
                    event_type=JobEventType.TRANSITION,
                    from_state=current.state,
                    to_state=plan.target_state,
                    worker_id=plan.worker_id,
                    recovery_classification=plan.recovery_classification,
                    checkpoint_ref=None,
                    evidence_ref=evidence_ref,
                )
                result = JobRuntimeState(
                    job_id=current.job_id,
                    work_order_ref=current.work_order_ref,
                    project_id=current.project_id,
                    state=plan.target_state,
                    worker_id=plan.worker_id,
                    attempt_count=plan.attempt_count,
                    max_attempts=current.max_attempts,
                    recovery_classification=plan.recovery_classification,
                    version=next_version,
                )
                connection.commit()
                return result
            except (JobStoreError, JobStateError):
                connection.rollback()
                raise
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                raise JobStoreError("JOB_STORE_CONFLICT") from exc
            except sqlite3.Error as exc:
                connection.rollback()
                raise JobStoreError("JOB_STORE_WRITE_FAILED") from exc

    def checkpoint(
        self,
        job_id: str,
        *,
        checkpoint_ref: str,
        expected_version: int,
        evidence_ref: str | None = None,
    ) -> JobRuntimeState:
        _require_text(job_id, "job_id")
        _require_text(checkpoint_ref, "checkpoint_ref")
        _require_positive_int(expected_version, "expected_version")
        _require_optional_text(evidence_ref, "evidence_ref")
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                current = self._state_from_row(self._load_job_row(connection, job_id))
                self._check_version(current, expected_version)
                if current.state in _TERMINAL_STATES:
                    raise JobStateError("JOB_TERMINAL")
                next_version = current.version + 1
                cursor = connection.execute(
                    "UPDATE job_records SET version = ?, "
                    "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
                    "WHERE job_id = ? AND version = ?",
                    (next_version, current.job_id, current.version),
                )
                if cursor.rowcount != 1:
                    raise JobStoreError("JOB_VERSION_CONFLICT")
                self._insert_event(
                    connection,
                    job_id=current.job_id,
                    event_type=JobEventType.CHECKPOINT,
                    from_state=current.state,
                    to_state=current.state,
                    worker_id=current.worker_id,
                    recovery_classification=current.recovery_classification,
                    checkpoint_ref=checkpoint_ref,
                    evidence_ref=evidence_ref,
                )
                result = JobRuntimeState(
                    job_id=current.job_id,
                    work_order_ref=current.work_order_ref,
                    project_id=current.project_id,
                    state=current.state,
                    worker_id=current.worker_id,
                    attempt_count=current.attempt_count,
                    max_attempts=current.max_attempts,
                    recovery_classification=current.recovery_classification,
                    version=next_version,
                )
                connection.commit()
                return result
            except (JobStoreError, JobStateError):
                connection.rollback()
                raise
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                raise JobStoreError("JOB_STORE_CONFLICT") from exc
            except sqlite3.Error as exc:
                connection.rollback()
                raise JobStoreError("JOB_STORE_WRITE_FAILED") from exc

    def list_events(self, job_id: str) -> tuple[JobEvent, ...]:
        _require_text(job_id, "job_id")
        self.initialize()
        with self._connect() as connection:
            try:
                exists = connection.execute(
                    "SELECT 1 FROM job_records WHERE job_id = ?", (job_id,)
                ).fetchone()
                if exists is None:
                    raise JobStoreError("JOB_NOT_FOUND")
                rows = connection.execute(
                    "SELECT event_id, job_id, sequence_no, event_type, from_state, "
                    "to_state, worker_id, recovery_classification, checkpoint_ref, "
                    "evidence_ref, recorded_at FROM job_events WHERE job_id = ? "
                    "ORDER BY sequence_no",
                    (job_id,),
                ).fetchall()
            except JobStoreError:
                raise
            except sqlite3.Error as exc:
                raise JobStoreError("JOB_STORE_READ_FAILED") from exc

        events: list[JobEvent] = []
        expected_sequence = 1
        try:
            for row in rows:
                if row["sequence_no"] != expected_sequence:
                    raise JobStoreError("JOB_EVENT_SEQUENCE_INVALID")
                recovery = row["recovery_classification"]
                events.append(
                    JobEvent(
                        event_id=row["event_id"],
                        job_id=row["job_id"],
                        sequence_no=int(row["sequence_no"]),
                        event_type=JobEventType(row["event_type"]),
                        from_state=(
                            TaskState(row["from_state"])
                            if row["from_state"] is not None
                            else None
                        ),
                        to_state=(
                            TaskState(row["to_state"])
                            if row["to_state"] is not None
                            else None
                        ),
                        worker_id=row["worker_id"],
                        recovery_classification=(
                            RecoveryClassification(recovery)
                            if recovery is not None
                            else None
                        ),
                        checkpoint_ref=row["checkpoint_ref"],
                        evidence_ref=row["evidence_ref"],
                        recorded_at=row["recorded_at"],
                    )
                )
                expected_sequence += 1
        except JobStoreError:
            raise
        except (TypeError, ValueError) as exc:
            raise JobStoreError("JOB_EVENT_INVALID") from exc
        return tuple(events)
