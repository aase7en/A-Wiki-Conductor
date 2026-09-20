"""SQLite persistence for transport-independent durable execution records.

The store persists bounded execution metadata only. It does not launch,
inspect, collect, retry, reconnect, cancel, route, or deduplicate processes.
"""

from __future__ import annotations

import re
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Callable, Iterator, Mapping

from .execution_record import (
    DurableExecutionReceipt,
    DurableExecutionRecord,
    ExecutionProcessState,
    ReceiptDisposition,
    TransportState,
)


EXECUTION_STORE_SCHEMA_VERSION = "2"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# WO-P1-246: every recognized execution_records shape (v1 legacy, partial-v2,
# full v2) must carry these core columns; anything else fails closed.
_CORE_RECORD_COLUMNS = frozenset(
    {
        "execution_id",
        "job_id",
        "work_order_ref",
        "project_id",
        "worker_id",
        "backend_id",
        "agent_ref",
        "repo_root",
        "branch",
        "head_before",
        "operation_ref",
        "command_fingerprint",
        "command_summary",
        "runtime_profile_ref",
        "run_dir_ref",
        "stdout_ref",
        "stderr_ref",
        "result_ref",
        "report_ref",
        "transport_state",
        "execution_state",
        "pid",
        "exit_code",
        "started_at",
        "finished_at",
        "version",
        "created_at",
        "updated_at",
    }
)


# WO-P1-246 repair: a pre-existing provenance column is accepted only in
# this exact canonical declared shape — exact declared type (TEXT attempt,
# INTEGER generation), nullable, no default, not part of the primary key.
# A name-only check would accept e.g. a TEXT-typed author_generation whose
# affinity silently coerces every stored generation to text, so generation
# 0 would read back as text and every record reconstruct as
# EXECUTION_RECORD_INVALID after the v2 stamp. Anything non-canonical
# fails closed before acceptance/stamp instead.
_PROVENANCE_COLUMN_DECLARED_TYPES = {
    "author_attempt_id": "TEXT",
    "author_generation": "INTEGER",
}


def _provenance_shape_is_canonical(
    column_info: Mapping[str, tuple[str, int, str | None, int]],
) -> bool:
    for name, declared_type in _PROVENANCE_COLUMN_DECLARED_TYPES.items():
        if name not in column_info:
            continue
        type_, notnull, default, pk = column_info[name]
        if type_ != declared_type or notnull != 0 or default is not None or pk != 0:
            return False
    return True


class ExecutionStoreError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ExecutionEventType(str, Enum):
    CREATED = "CREATED"
    TRANSPORT_STATE_CHANGED = "TRANSPORT_STATE_CHANGED"
    EXECUTION_STATE_CHANGED = "EXECUTION_STATE_CHANGED"
    PROCESS_METADATA_UPDATED = "PROCESS_METADATA_UPDATED"
    RESULT_METADATA_UPDATED = "RESULT_METADATA_UPDATED"
    RECEIPT_RECORDED = "RECEIPT_RECORDED"


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
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
class ExecutionEvent:
    event_id: str
    execution_id: str
    sequence_no: int
    event_type: ExecutionEventType
    transport_state: TransportState | None
    execution_state: ExecutionProcessState | None
    pid: int | None
    exit_code: int | None
    started_at: str | None
    finished_at: str | None
    evidence_ref: str | None
    recorded_at: str

    def __post_init__(self) -> None:
        _require_text(self.event_id, "event_id")
        _require_text(self.execution_id, "execution_id")
        _require_positive_int(self.sequence_no, "sequence_no")
        if not isinstance(self.event_type, ExecutionEventType):
            raise ValueError("event_type must be an ExecutionEventType")
        if self.transport_state is not None and not isinstance(
            self.transport_state, TransportState
        ):
            raise ValueError("transport_state must be a TransportState")
        if self.execution_state is not None and not isinstance(
            self.execution_state, ExecutionProcessState
        ):
            raise ValueError("execution_state must be an ExecutionProcessState")
        if self.pid is not None:
            _require_positive_int(self.pid, "pid")
        if self.exit_code is not None and (
            not isinstance(self.exit_code, int) or isinstance(self.exit_code, bool)
        ):
            raise ValueError("exit_code must be an integer")
        _require_optional_text(self.started_at, "started_at")
        _require_optional_text(self.finished_at, "finished_at")
        _require_optional_text(self.evidence_ref, "evidence_ref")
        _require_text(self.recorded_at, "recorded_at")


class SQLiteExecutionStore:
    def __init__(
        self,
        database_path: str | Path,
        *,
        event_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self._event_id_factory = event_id_factory or (
            lambda: f"execution-event-{uuid.uuid4().hex}"
        )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.database_path)
        except (OSError, sqlite3.Error) as exc:
            raise ExecutionStoreError("EXECUTION_STORE_OPEN_FAILED") from exc
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
                    CREATE TABLE IF NOT EXISTS execution_store_meta (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS execution_records (
                        execution_id TEXT PRIMARY KEY CHECK (trim(execution_id) <> ''),
                        job_id TEXT NOT NULL CHECK (trim(job_id) <> ''),
                        work_order_ref TEXT NOT NULL CHECK (trim(work_order_ref) <> ''),
                        project_id TEXT NOT NULL CHECK (trim(project_id) <> ''),
                        worker_id TEXT NOT NULL CHECK (trim(worker_id) <> ''),
                        backend_id TEXT NOT NULL CHECK (trim(backend_id) <> ''),
                        agent_ref TEXT,
                        repo_root TEXT NOT NULL CHECK (trim(repo_root) <> ''),
                        branch TEXT NOT NULL CHECK (trim(branch) <> ''),
                        head_before TEXT NOT NULL CHECK (trim(head_before) <> ''),
                        operation_ref TEXT NOT NULL CHECK (trim(operation_ref) <> ''),
                        command_fingerprint TEXT NOT NULL CHECK (length(command_fingerprint) = 64),
                        command_summary TEXT NOT NULL CHECK (
                            trim(command_summary) <> '' AND length(command_summary) <= 256
                        ),
                        runtime_profile_ref TEXT,
                        run_dir_ref TEXT,
                        stdout_ref TEXT,
                        stderr_ref TEXT,
                        result_ref TEXT,
                        report_ref TEXT,
                        transport_state TEXT NOT NULL,
                        execution_state TEXT NOT NULL,
                        pid INTEGER,
                        exit_code INTEGER,
                        started_at TEXT,
                        finished_at TEXT,
                        version INTEGER NOT NULL CHECK (version >= 1),
                        author_attempt_id TEXT,
                        author_generation INTEGER CHECK (author_generation IN (0, 1)),
                        created_at TEXT NOT NULL DEFAULT (
                            strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        ),
                        updated_at TEXT NOT NULL DEFAULT (
                            strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        ),
                        CHECK (
                            (author_attempt_id IS NULL AND author_generation IS NULL)
                            OR (
                                author_attempt_id IS NOT NULL
                                AND author_generation IS NOT NULL
                            )
                        )
                    );

                    CREATE INDEX IF NOT EXISTS idx_execution_records_fingerprint_created
                    ON execution_records(command_fingerprint, created_at DESC, execution_id DESC);

                    CREATE TABLE IF NOT EXISTS execution_events (
                        event_id TEXT PRIMARY KEY CHECK (trim(event_id) <> ''),
                        execution_id TEXT NOT NULL,
                        sequence_no INTEGER NOT NULL CHECK (sequence_no >= 1),
                        event_type TEXT NOT NULL,
                        transport_state TEXT,
                        execution_state TEXT,
                        pid INTEGER,
                        exit_code INTEGER,
                        started_at TEXT,
                        finished_at TEXT,
                        evidence_ref TEXT,
                        recorded_at TEXT NOT NULL DEFAULT (
                            strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        ),
                        UNIQUE (execution_id, sequence_no),
                        FOREIGN KEY (execution_id)
                            REFERENCES execution_records(execution_id)
                            ON DELETE RESTRICT
                    );

                    CREATE TABLE IF NOT EXISTS execution_receipts (
                        receipt_id TEXT PRIMARY KEY CHECK (length(receipt_id) = 64),
                        execution_id TEXT NOT NULL CHECK (trim(execution_id) <> ''),
                        attempt_id TEXT NOT NULL CHECK (trim(attempt_id) <> ''),
                        result_digest TEXT NOT NULL CHECK (length(result_digest) = 64),
                        binding_digest TEXT NOT NULL CHECK (length(binding_digest) = 64),
                        claim_generation INTEGER NOT NULL CHECK (claim_generation >= 1),
                        authority_sha TEXT NOT NULL CHECK (length(authority_sha) = 40),
                        execution_sha TEXT NOT NULL CHECK (length(execution_sha) = 40),
                        disposition TEXT NOT NULL CHECK (
                            disposition IN ('ACCEPTED', 'QUARANTINED')
                        ),
                        evidence_ref TEXT,
                        recorded_at TEXT NOT NULL DEFAULT (
                            strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        ),
                        UNIQUE (execution_id, attempt_id, result_digest, binding_digest),
                        FOREIGN KEY (execution_id)
                            REFERENCES execution_records(execution_id)
                            ON DELETE RESTRICT
                    );

                    CREATE INDEX IF NOT EXISTS idx_execution_receipts_execution_recorded
                    ON execution_receipts(execution_id, recorded_at DESC, receipt_id DESC);
                    """
                )

                self._reconcile_schema_version(connection)

                connection.commit()
            except ExecutionStoreError:
                connection.rollback()
                raise
            except sqlite3.Error as exc:
                connection.rollback()
                raise ExecutionStoreError("EXECUTION_STORE_INIT_FAILED") from exc

    @staticmethod
    def _schema_version(connection: sqlite3.Connection) -> str | None:
        row = connection.execute(
            "SELECT value FROM execution_store_meta WHERE key = 'schema_version'"
        ).fetchone()
        return None if row is None else row["value"]

    @staticmethod
    def _record_column_info(
        connection: sqlite3.Connection,
    ) -> dict[str, tuple[str, int, str | None, int]]:
        """WO-P1-246: declared shape of every execution_records column.

        Maps column name to ``(declared_type, notnull, default, pk)``
        exactly as reported by ``PRAGMA table_info``.
        """
        return {
            str(row[1]): (str(row[2]), int(row[3]), row[4], int(row[5]))
            for row in connection.execute("PRAGMA table_info(execution_records)")
        }

    def _reconcile_schema_version(self, connection: sqlite3.Connection) -> None:
        """WO-P1-246 v1 -> v2 migration, INSIDE ``initialize()``.

        Runs after the ``executescript`` DDL has completed/committed and
        BEFORE the strict version rejection. Fresh databases are created in
        the v2 shape by the DDL; existing v1 (or shape-equivalent) databases
        are migrated by nullable ``ALTER TABLE`` steps inside one explicit
        ``BEGIN IMMEDIATE`` transaction. Legacy rows are preserved exactly
        and remain ``NULL/NULL`` — there is no backfill. Record-layer
        both-or-neither/generation validation stays authoritative for every
        database shape (migrated tables cannot carry the cross-column
        CHECK without a rebuild, which is deliberately avoided).

        WO-P1-246 repair: provenance columns are validated by declared
        shape, never by name only. Any pre-existing
        ``author_attempt_id``/``author_generation`` column must already be
        canonical — exact declared type (TEXT / INTEGER), nullable, no
        default, not part of the primary key — before it is accepted,
        ALTERed around, or stamped ``schema_version = 2``. The shape is
        validated before mutation and re-read/re-validated inside the
        ``BEGIN IMMEDIATE`` transaction, so a failed shape is never
        stamped v2.
        """
        version = self._schema_version(connection)
        column_info = self._record_column_info(connection)
        has_attempt = "author_attempt_id" in column_info
        has_generation = "author_generation" in column_info
        if _CORE_RECORD_COLUMNS - column_info.keys():
            raise ExecutionStoreError("EXECUTION_SCHEMA_SHAPE_INVALID")
        if version == EXECUTION_STORE_SCHEMA_VERSION:
            if (
                not (has_attempt and has_generation)
                or not _provenance_shape_is_canonical(column_info)
            ):
                raise ExecutionStoreError("EXECUTION_SCHEMA_SHAPE_INVALID")
            return
        if version not in (None, "1"):
            raise ExecutionStoreError("EXECUTION_SCHEMA_VERSION_UNSUPPORTED")
        if not _provenance_shape_is_canonical(column_info):
            # a pre-existing provenance column must be canonical before any
            # stamp or mutation
            raise ExecutionStoreError("EXECUTION_SCHEMA_SHAPE_INVALID")
        if version is None and has_attempt and has_generation:
            # fresh creation, or the DDL-committed/meta-write crash edge:
            # stamp version 2 only after the shape is proven. WO-P1-246
            # repair: initialize() can be reached concurrently; both
            # callers observe this absent meta row and race on the stamp
            # INSERT. Make the stamp idempotent at the SQLite uniqueness
            # boundary, then re-read the durable winner and verify it —
            # a conflicting non-2 value is never overwritten.
            connection.execute(
                "INSERT INTO execution_store_meta(key, value) "
                "VALUES('schema_version', ?) ON CONFLICT(key) DO NOTHING",
                (EXECUTION_STORE_SCHEMA_VERSION,),
            )
            if self._schema_version(connection) != EXECUTION_STORE_SCHEMA_VERSION:
                raise ExecutionStoreError("EXECUTION_SCHEMA_VERSION_UNSUPPORTED")
            return
        # version is 1, or absent while the table is legacy/partial-v2 shaped
        connection.execute("BEGIN IMMEDIATE")
        version = self._schema_version(connection)
        column_info = self._record_column_info(connection)
        if version == EXECUTION_STORE_SCHEMA_VERSION:
            # idempotent: the migration already landed under this lock
            if not (
                "author_attempt_id" in column_info
                and "author_generation" in column_info
            ) or not _provenance_shape_is_canonical(column_info):
                connection.rollback()
                raise ExecutionStoreError("EXECUTION_SCHEMA_SHAPE_INVALID")
            connection.rollback()
            return
        if version not in (None, "1"):
            connection.rollback()
            raise ExecutionStoreError("EXECUTION_SCHEMA_VERSION_UNSUPPORTED")
        if _CORE_RECORD_COLUMNS - column_info.keys():
            connection.rollback()
            raise ExecutionStoreError("EXECUTION_SCHEMA_SHAPE_INVALID")
        # re-read and re-validate the declared shape under the write lock
        # BEFORE any mutation
        if not _provenance_shape_is_canonical(column_info):
            connection.rollback()
            raise ExecutionStoreError("EXECUTION_SCHEMA_SHAPE_INVALID")
        if "author_attempt_id" not in column_info:
            connection.execute(
                "ALTER TABLE execution_records ADD COLUMN author_attempt_id TEXT"
            )
        if "author_generation" not in column_info:
            connection.execute(
                "ALTER TABLE execution_records ADD COLUMN author_generation INTEGER"
            )
        # and again on the resulting shape before the v2 stamp
        column_info = self._record_column_info(connection)
        if not (
            "author_attempt_id" in column_info
            and "author_generation" in column_info
        ) or not _provenance_shape_is_canonical(column_info):
            connection.rollback()
            raise ExecutionStoreError("EXECUTION_SCHEMA_SHAPE_INVALID")
        connection.execute(
            "INSERT INTO execution_store_meta(key, value) VALUES('schema_version', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (EXECUTION_STORE_SCHEMA_VERSION,),
        )
        connection.commit()

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> DurableExecutionRecord:
        try:
            return DurableExecutionRecord(
                execution_id=row["execution_id"],
                job_id=row["job_id"],
                work_order_ref=row["work_order_ref"],
                project_id=row["project_id"],
                worker_id=row["worker_id"],
                backend_id=row["backend_id"],
                agent_ref=row["agent_ref"],
                repo_root=row["repo_root"],
                branch=row["branch"],
                head_before=row["head_before"],
                operation_ref=row["operation_ref"],
                command_fingerprint=row["command_fingerprint"],
                command_summary=row["command_summary"],
                runtime_profile_ref=row["runtime_profile_ref"],
                run_dir_ref=row["run_dir_ref"],
                stdout_ref=row["stdout_ref"],
                stderr_ref=row["stderr_ref"],
                result_ref=row["result_ref"],
                report_ref=row["report_ref"],
                transport_state=TransportState(row["transport_state"]),
                execution_state=ExecutionProcessState(row["execution_state"]),
                pid=row["pid"],
                exit_code=row["exit_code"],
                started_at=row["started_at"],
                finished_at=row["finished_at"],
                version=row["version"],
                author_attempt_id=row["author_attempt_id"],
                author_generation=row["author_generation"],
            )
        except (TypeError, ValueError) as exc:
            raise ExecutionStoreError("EXECUTION_RECORD_INVALID") from exc

    @staticmethod
    def _select_record(connection: sqlite3.Connection, execution_id: str) -> sqlite3.Row:
        row = connection.execute(
            "SELECT execution_id, job_id, work_order_ref, project_id, worker_id, "
            "backend_id, agent_ref, repo_root, branch, head_before, operation_ref, "
            "command_fingerprint, command_summary, runtime_profile_ref, run_dir_ref, "
            "stdout_ref, stderr_ref, result_ref, report_ref, transport_state, "
            "execution_state, pid, exit_code, started_at, finished_at, version, "
            "author_attempt_id, author_generation "
            "FROM execution_records WHERE execution_id = ?",
            (execution_id,),
        ).fetchone()
        if row is None:
            raise ExecutionStoreError("EXECUTION_NOT_FOUND")
        return row

    def _next_sequence(self, connection: sqlite3.Connection, execution_id: str) -> int:
        row = connection.execute(
            "SELECT MAX(sequence_no) AS max_sequence FROM execution_events "
            "WHERE execution_id = ?",
            (execution_id,),
        ).fetchone()
        maximum = row["max_sequence"] if row is not None else None
        return 1 if maximum is None else int(maximum) + 1

    def _insert_event(
        self,
        connection: sqlite3.Connection,
        *,
        record: DurableExecutionRecord,
        event_type: ExecutionEventType,
        evidence_ref: str | None,
    ) -> None:
        _require_optional_text(evidence_ref, "evidence_ref")
        connection.execute(
            "INSERT INTO execution_events("
            "event_id, execution_id, sequence_no, event_type, transport_state, "
            "execution_state, pid, exit_code, started_at, finished_at, evidence_ref"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                self._event_id_factory(),
                record.execution_id,
                self._next_sequence(connection, record.execution_id),
                event_type.value,
                record.transport_state.value,
                record.execution_state.value,
                record.pid,
                record.exit_code,
                record.started_at,
                record.finished_at,
                evidence_ref,
            ),
        )

    def create(self, record: DurableExecutionRecord) -> DurableExecutionRecord:
        if not isinstance(record, DurableExecutionRecord):
            raise ValueError("record must be a DurableExecutionRecord")
        if record.version != 1:
            raise ValueError("new execution record version must be 1")
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                exists = connection.execute(
                    "SELECT 1 FROM execution_records WHERE execution_id = ?",
                    (record.execution_id,),
                ).fetchone()
                if exists is not None:
                    raise ExecutionStoreError("EXECUTION_ALREADY_EXISTS")
                connection.execute(
                    "INSERT INTO execution_records("
                    "execution_id, job_id, work_order_ref, project_id, worker_id, "
                    "backend_id, agent_ref, repo_root, branch, head_before, operation_ref, "
                    "command_fingerprint, command_summary, runtime_profile_ref, run_dir_ref, "
                    "stdout_ref, stderr_ref, result_ref, report_ref, transport_state, "
                    "execution_state, pid, exit_code, started_at, finished_at, version, "
                    "author_attempt_id, author_generation"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        record.execution_id,
                        record.job_id,
                        record.work_order_ref,
                        record.project_id,
                        record.worker_id,
                        record.backend_id,
                        record.agent_ref,
                        record.repo_root,
                        record.branch,
                        record.head_before,
                        record.operation_ref,
                        record.command_fingerprint,
                        record.command_summary,
                        record.runtime_profile_ref,
                        record.run_dir_ref,
                        record.stdout_ref,
                        record.stderr_ref,
                        record.result_ref,
                        record.report_ref,
                        record.transport_state.value,
                        record.execution_state.value,
                        record.pid,
                        record.exit_code,
                        record.started_at,
                        record.finished_at,
                        record.version,
                        record.author_attempt_id,
                        record.author_generation,
                    ),
                )
                self._insert_event(
                    connection,
                    record=record,
                    event_type=ExecutionEventType.CREATED,
                    evidence_ref=None,
                )
                connection.commit()
                return record
            except ExecutionStoreError:
                connection.rollback()
                raise
            except sqlite3.Error as exc:
                connection.rollback()
                raise ExecutionStoreError("EXECUTION_STORE_WRITE_FAILED") from exc

    def get(self, execution_id: str) -> DurableExecutionRecord:
        _require_text(execution_id, "execution_id")
        self.initialize()
        with self._connect() as connection:
            try:
                return self._row_to_record(self._select_record(connection, execution_id))
            except ExecutionStoreError:
                raise
            except sqlite3.Error as exc:
                raise ExecutionStoreError("EXECUTION_STORE_READ_FAILED") from exc

    def find_by_fingerprint(
        self, fingerprint: str
    ) -> tuple[DurableExecutionRecord, ...]:
        if not isinstance(fingerprint, str) or not _SHA256_RE.fullmatch(fingerprint):
            raise ValueError("fingerprint must be lowercase SHA-256 hex")
        self.initialize()
        with self._connect() as connection:
            try:
                rows = connection.execute(
                    "SELECT execution_id, job_id, work_order_ref, project_id, worker_id, "
                    "backend_id, agent_ref, repo_root, branch, head_before, operation_ref, "
                    "command_fingerprint, command_summary, runtime_profile_ref, run_dir_ref, "
                    "stdout_ref, stderr_ref, result_ref, report_ref, transport_state, "
                    "execution_state, pid, exit_code, started_at, finished_at, version, "
                    "author_attempt_id, author_generation "
                    "FROM execution_records WHERE command_fingerprint = ? "
                    "ORDER BY created_at DESC, rowid DESC",
                    (fingerprint,),
                ).fetchall()
                return tuple(self._row_to_record(row) for row in rows)
            except ExecutionStoreError:
                raise
            except sqlite3.Error as exc:
                raise ExecutionStoreError("EXECUTION_STORE_READ_FAILED") from exc

    def _update(
        self,
        execution_id: str,
        *,
        expected_version: int,
        event_type: ExecutionEventType,
        evidence_ref: str | None,
        transform: Callable[[DurableExecutionRecord], DurableExecutionRecord],
    ) -> DurableExecutionRecord:
        _require_text(execution_id, "execution_id")
        _require_positive_int(expected_version, "expected_version")
        _require_optional_text(evidence_ref, "evidence_ref")
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                current = self._row_to_record(self._select_record(connection, execution_id))
                if current.version != expected_version:
                    raise ExecutionStoreError("EXECUTION_VERSION_CONFLICT")
                next_record = transform(current)
                if next_record.execution_id != current.execution_id:
                    raise ExecutionStoreError("EXECUTION_IDENTITY_MUTATION_FORBIDDEN")
                connection.execute(
                    "UPDATE execution_records SET transport_state = ?, execution_state = ?, "
                    "pid = ?, exit_code = ?, started_at = ?, finished_at = ?, version = ?, "
                    "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
                    "WHERE execution_id = ? AND version = ?",
                    (
                        next_record.transport_state.value,
                        next_record.execution_state.value,
                        next_record.pid,
                        next_record.exit_code,
                        next_record.started_at,
                        next_record.finished_at,
                        next_record.version,
                        execution_id,
                        expected_version,
                    ),
                )
                if connection.total_changes < 1:
                    raise ExecutionStoreError("EXECUTION_VERSION_CONFLICT")
                self._insert_event(
                    connection,
                    record=next_record,
                    event_type=event_type,
                    evidence_ref=evidence_ref,
                )
                connection.commit()
                return next_record
            except ExecutionStoreError:
                connection.rollback()
                raise
            except sqlite3.Error as exc:
                connection.rollback()
                raise ExecutionStoreError("EXECUTION_STORE_WRITE_FAILED") from exc

    def set_transport_state(
        self,
        execution_id: str,
        state: TransportState,
        *,
        expected_version: int,
        evidence_ref: str | None = None,
    ) -> DurableExecutionRecord:
        if not isinstance(state, TransportState):
            raise ValueError("state must be a TransportState")
        return self._update(
            execution_id,
            expected_version=expected_version,
            event_type=ExecutionEventType.TRANSPORT_STATE_CHANGED,
            evidence_ref=evidence_ref,
            transform=lambda current: replace(
                current,
                transport_state=state,
                version=current.version + 1,
            ),
        )

    def set_execution_state(
        self,
        execution_id: str,
        state: ExecutionProcessState,
        *,
        expected_version: int,
        evidence_ref: str | None = None,
    ) -> DurableExecutionRecord:
        if not isinstance(state, ExecutionProcessState):
            raise ValueError("state must be an ExecutionProcessState")
        return self._update(
            execution_id,
            expected_version=expected_version,
            event_type=ExecutionEventType.EXECUTION_STATE_CHANGED,
            evidence_ref=evidence_ref,
            transform=lambda current: replace(
                current,
                execution_state=state,
                version=current.version + 1,
            ),
        )

    def set_process_metadata(
        self,
        execution_id: str,
        *,
        pid: int,
        started_at: str | None,
        expected_version: int,
        evidence_ref: str | None = None,
    ) -> DurableExecutionRecord:
        return self._update(
            execution_id,
            expected_version=expected_version,
            event_type=ExecutionEventType.PROCESS_METADATA_UPDATED,
            evidence_ref=evidence_ref,
            transform=lambda current: replace(
                current,
                pid=pid,
                started_at=started_at,
                version=current.version + 1,
            ),
        )

    def set_result_metadata(
        self,
        execution_id: str,
        *,
        exit_code: int,
        finished_at: str,
        expected_version: int,
        evidence_ref: str | None = None,
    ) -> DurableExecutionRecord:
        return self._update(
            execution_id,
            expected_version=expected_version,
            event_type=ExecutionEventType.RESULT_METADATA_UPDATED,
            evidence_ref=evidence_ref,
            transform=lambda current: replace(
                current,
                exit_code=exit_code,
                finished_at=finished_at,
                version=current.version + 1,
            ),
        )

    def list_events(self, execution_id: str) -> tuple[ExecutionEvent, ...]:
        _require_text(execution_id, "execution_id")
        self.initialize()
        with self._connect() as connection:
            try:
                self._select_record(connection, execution_id)
                rows = connection.execute(
                    "SELECT event_id, execution_id, sequence_no, event_type, "
                    "transport_state, execution_state, pid, exit_code, started_at, "
                    "finished_at, evidence_ref, recorded_at FROM execution_events "
                    "WHERE execution_id = ? ORDER BY sequence_no",
                    (execution_id,),
                ).fetchall()
            except ExecutionStoreError:
                raise
            except sqlite3.Error as exc:
                raise ExecutionStoreError("EXECUTION_STORE_READ_FAILED") from exc

        events: list[ExecutionEvent] = []
        try:
            for row in rows:
                events.append(
                    ExecutionEvent(
                        event_id=row["event_id"],
                        execution_id=row["execution_id"],
                        sequence_no=row["sequence_no"],
                        event_type=ExecutionEventType(row["event_type"]),
                        transport_state=(
                            TransportState(row["transport_state"])
                            if row["transport_state"] is not None
                            else None
                        ),
                        execution_state=(
                            ExecutionProcessState(row["execution_state"])
                            if row["execution_state"] is not None
                            else None
                        ),
                        pid=row["pid"],
                        exit_code=row["exit_code"],
                        started_at=row["started_at"],
                        finished_at=row["finished_at"],
                        evidence_ref=row["evidence_ref"],
                        recorded_at=row["recorded_at"],
                    )
                )
        except (TypeError, ValueError) as exc:
            raise ExecutionStoreError("EXECUTION_EVENT_INVALID") from exc
        return tuple(events)

    _RECEIPT_COLUMNS = (
        "receipt_id, execution_id, attempt_id, result_digest, binding_digest, "
        "claim_generation, authority_sha, execution_sha, disposition, "
        "evidence_ref, recorded_at"
    )

    @staticmethod
    def _row_to_receipt(row: sqlite3.Row) -> DurableExecutionReceipt:
        try:
            return DurableExecutionReceipt(
                receipt_id=row["receipt_id"],
                execution_id=row["execution_id"],
                attempt_id=row["attempt_id"],
                result_digest=row["result_digest"],
                binding_digest=row["binding_digest"],
                claim_generation=row["claim_generation"],
                authority_sha=row["authority_sha"],
                execution_sha=row["execution_sha"],
                disposition=ReceiptDisposition(row["disposition"]),
                evidence_ref=row["evidence_ref"],
                recorded_at=row["recorded_at"],
            )
        except (TypeError, ValueError) as exc:
            raise ExecutionStoreError("RECEIPT_RECORD_INVALID") from exc

    def _select_receipt_by_id(
        self, connection: sqlite3.Connection, receipt_id: str
    ) -> sqlite3.Row | None:
        return connection.execute(
            f"SELECT {self._RECEIPT_COLUMNS} FROM execution_receipts "
            "WHERE receipt_id = ?",
            (receipt_id,),
        ).fetchone()

    def _select_receipt_by_identity(
        self, connection: sqlite3.Connection, receipt: DurableExecutionReceipt
    ) -> sqlite3.Row | None:
        return connection.execute(
            f"SELECT {self._RECEIPT_COLUMNS} FROM execution_receipts "
            "WHERE execution_id = ? AND attempt_id = ? AND result_digest = ? "
            "AND binding_digest = ?",
            (
                receipt.execution_id,
                receipt.attempt_id,
                receipt.result_digest,
                receipt.binding_digest,
            ),
        ).fetchone()

    @staticmethod
    def _verify_receipt_agreement(
        receipt: DurableExecutionReceipt, existing: sqlite3.Row
    ) -> None:
        conflicts = (
            ("claim_generation", receipt.claim_generation),
            ("authority_sha", receipt.authority_sha),
            ("execution_sha", receipt.execution_sha),
            ("disposition", receipt.disposition.value),
            ("evidence_ref", receipt.evidence_ref),
        )
        for column, presented in conflicts:
            if existing[column] != presented:
                raise ExecutionStoreError("RECEIPT_CONFLICT")

    def record_receipt(self, receipt: DurableExecutionReceipt) -> DurableExecutionReceipt:
        """Idempotently persist an immutable execution receipt (append-only).

        The contract identity is (execution_id, attempt_id, result digest)
        plus the binding digest; identical evidence converges to the existing
        durable receipt, conflicting immutable facts fail closed, and no API
        rewrites or deletes a stored receipt.
        """
        if not isinstance(receipt, DurableExecutionReceipt):
            raise ValueError("receipt must be a DurableExecutionReceipt")
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                record = self._row_to_record(
                    self._select_record(connection, receipt.execution_id)
                )
                changes_before = connection.total_changes
                connection.execute(
                    "INSERT INTO execution_receipts("
                    "receipt_id, execution_id, attempt_id, result_digest, "
                    "binding_digest, claim_generation, authority_sha, "
                    "execution_sha, disposition, evidence_ref"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(receipt_id) DO NOTHING",
                    (
                        receipt.receipt_id,
                        receipt.execution_id,
                        receipt.attempt_id,
                        receipt.result_digest,
                        receipt.binding_digest,
                        receipt.claim_generation,
                        receipt.authority_sha,
                        receipt.execution_sha,
                        receipt.disposition.value,
                        receipt.evidence_ref,
                    ),
                )
                if connection.total_changes > changes_before:
                    self._insert_event(
                        connection,
                        record=record,
                        event_type=ExecutionEventType.RECEIPT_RECORDED,
                        evidence_ref=receipt.receipt_id,
                    )
                    durable = self._select_receipt_by_id(
                        connection, receipt.receipt_id
                    )
                    if durable is None:
                        raise ExecutionStoreError("EXECUTION_STORE_WRITE_FAILED")
                    connection.commit()
                    return self._row_to_receipt(durable)
                existing = self._select_receipt_by_id(connection, receipt.receipt_id)
                if existing is None:
                    existing = self._select_receipt_by_identity(connection, receipt)
                if existing is None:
                    raise ExecutionStoreError("EXECUTION_STORE_WRITE_FAILED")
                self._verify_receipt_agreement(receipt, existing)
                connection.commit()
                return self._row_to_receipt(existing)
            except ExecutionStoreError:
                connection.rollback()
                raise
            except sqlite3.Error as exc:
                connection.rollback()
                raise ExecutionStoreError("EXECUTION_STORE_WRITE_FAILED") from exc

    def get_receipt(self, receipt_id: str) -> DurableExecutionReceipt:
        if not isinstance(receipt_id, str) or not _SHA256_RE.fullmatch(receipt_id):
            raise ValueError("receipt_id must be lowercase SHA-256 hex")
        self.initialize()
        with self._connect() as connection:
            try:
                row = self._select_receipt_by_id(connection, receipt_id)
                if row is None:
                    raise ExecutionStoreError("RECEIPT_NOT_FOUND")
                return self._row_to_receipt(row)
            except ExecutionStoreError:
                raise
            except sqlite3.Error as exc:
                raise ExecutionStoreError("EXECUTION_STORE_READ_FAILED") from exc
