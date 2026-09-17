from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from a_conductor.execution_record import (
    DurableExecutionRecord,
    ExecutionProcessState,
    TransportState,
    new_execution_record,
)
from a_conductor.execution_store import (
    ExecutionEventType,
    ExecutionStoreError,
    SQLiteExecutionStore,
)


def make_record(execution_id: str = "exec-001", **overrides) -> DurableExecutionRecord:
    values = dict(
        execution_id=execution_id,
        job_id="job-001",
        work_order_ref="docs/work-orders/WO-1.md",
        project_id="project-1",
        worker_id="a-worker-01",
        backend_id="serena-local",
        agent_ref="agent:chatgpt",
        repo_root=r"A:\GitHub\example",
        branch="main",
        head_before="a" * 40,
        operation_ref="op:pytest-focused",
        command_fingerprint="b" * 64,
        command_summary="pytest focused regression",
        runtime_profile_ref="runtime:serena-phase6",
        run_dir_ref="runs/exec-001",
        stdout_ref="runs/exec-001/stdout.log",
        stderr_ref="runs/exec-001/stderr.log",
        result_ref="runs/exec-001/result.json",
        report_ref="runs/exec-001/report.txt",
        transport_state=TransportState.CONNECTED,
        execution_state=ExecutionProcessState.QUEUED,
    )
    values.update(overrides)
    return new_execution_record(**values)


def test_create_get_and_reopen_persists_record(tmp_path: Path) -> None:
    database = tmp_path / "executions.sqlite"
    store = SQLiteExecutionStore(database)
    created = store.create(make_record())

    assert created.version == 1
    assert store.get("exec-001") == created
    assert SQLiteExecutionStore(database).get("exec-001") == created


def test_duplicate_execution_id_is_rejected(tmp_path: Path) -> None:
    store = SQLiteExecutionStore(tmp_path / "executions.sqlite")
    store.create(make_record())
    with pytest.raises(ExecutionStoreError) as exc_info:
        store.create(make_record())
    assert exc_info.value.code == "EXECUTION_ALREADY_EXISTS"


def test_transport_loss_does_not_change_running_execution_state(tmp_path: Path) -> None:
    store = SQLiteExecutionStore(tmp_path / "executions.sqlite")
    created = store.create(make_record(execution_state=ExecutionProcessState.RUNNING))

    lost = store.set_transport_state(
        "exec-001",
        TransportState.LOST,
        expected_version=created.version,
        evidence_ref="evidence:transport-502",
    )

    assert lost.transport_state is TransportState.LOST
    assert lost.execution_state is ExecutionProcessState.RUNNING
    assert lost.version == 2


def test_execution_state_change_does_not_change_transport_state(tmp_path: Path) -> None:
    store = SQLiteExecutionStore(tmp_path / "executions.sqlite")
    created = store.create(make_record(transport_state=TransportState.LOST))

    updated = store.set_execution_state(
        "exec-001",
        ExecutionProcessState.PROCESS_STILL_RUNNING,
        expected_version=created.version,
        evidence_ref="evidence:pid-alive",
    )

    assert updated.transport_state is TransportState.LOST
    assert updated.execution_state is ExecutionProcessState.PROCESS_STILL_RUNNING


def test_stale_writer_is_rejected_without_new_event(tmp_path: Path) -> None:
    store = SQLiteExecutionStore(tmp_path / "executions.sqlite")
    created = store.create(make_record())
    current = store.set_transport_state(
        "exec-001", TransportState.DEGRADED, expected_version=created.version
    )
    before_events = store.list_events("exec-001")

    with pytest.raises(ExecutionStoreError) as exc_info:
        store.set_execution_state(
            "exec-001",
            ExecutionProcessState.STARTING,
            expected_version=created.version,
        )
    assert exc_info.value.code == "EXECUTION_VERSION_CONFLICT"
    assert store.get("exec-001") == current
    assert store.list_events("exec-001") == before_events


def test_process_metadata_update_is_versioned(tmp_path: Path) -> None:
    store = SQLiteExecutionStore(tmp_path / "executions.sqlite")
    created = store.create(make_record())

    updated = store.set_process_metadata(
        "exec-001",
        pid=12345,
        started_at="2026-08-20T03:00:00Z",
        expected_version=created.version,
        evidence_ref="evidence:spawn",
    )

    assert updated.pid == 12345
    assert updated.started_at == "2026-08-20T03:00:00Z"
    assert updated.version == 2


def test_result_metadata_update_is_versioned(tmp_path: Path) -> None:
    store = SQLiteExecutionStore(tmp_path / "executions.sqlite")
    created = store.create(make_record(execution_state=ExecutionProcessState.RUNNING))

    updated = store.set_result_metadata(
        "exec-001",
        exit_code=0,
        finished_at="2026-08-20T03:01:00Z",
        expected_version=created.version,
        evidence_ref="evidence:result-json",
    )

    assert updated.exit_code == 0
    assert updated.finished_at == "2026-08-20T03:01:00Z"
    assert updated.execution_state is ExecutionProcessState.RUNNING


def test_identity_fields_remain_immutable_across_updates(tmp_path: Path) -> None:
    store = SQLiteExecutionStore(tmp_path / "executions.sqlite")
    created = store.create(make_record())
    updated = store.set_transport_state(
        "exec-001", TransportState.LOST, expected_version=created.version
    )

    for name in (
        "execution_id",
        "job_id",
        "work_order_ref",
        "project_id",
        "worker_id",
        "backend_id",
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
    ):
        assert getattr(updated, name) == getattr(created, name)


def test_events_are_append_only_and_sequenced(tmp_path: Path) -> None:
    store = SQLiteExecutionStore(tmp_path / "executions.sqlite")
    created = store.create(make_record())
    second = store.set_transport_state(
        "exec-001",
        TransportState.LOST,
        expected_version=created.version,
        evidence_ref="evidence:transport",
    )
    store.set_execution_state(
        "exec-001",
        ExecutionProcessState.PROCESS_STILL_RUNNING,
        expected_version=second.version,
        evidence_ref="evidence:process",
    )

    events = store.list_events("exec-001")
    assert [event.sequence_no for event in events] == [1, 2, 3]
    assert [event.event_type for event in events] == [
        ExecutionEventType.CREATED,
        ExecutionEventType.TRANSPORT_STATE_CHANGED,
        ExecutionEventType.EXECUTION_STATE_CHANGED,
    ]
    assert events[1].evidence_ref == "evidence:transport"
    assert events[2].evidence_ref == "evidence:process"


def test_missing_execution_returns_stable_error_code(tmp_path: Path) -> None:
    store = SQLiteExecutionStore(tmp_path / "executions.sqlite")
    with pytest.raises(ExecutionStoreError) as exc_info:
        store.get("exec-missing")
    assert exc_info.value.code == "EXECUTION_NOT_FOUND"


def test_schema_contains_no_raw_prompt_command_environment_or_output_columns(tmp_path: Path) -> None:
    database = tmp_path / "executions.sqlite"
    store = SQLiteExecutionStore(database)
    store.create(make_record())

    connection = sqlite3.connect(database)
    try:
        record_columns = {row[1] for row in connection.execute("PRAGMA table_info(execution_records)")}
        event_columns = {row[1] for row in connection.execute("PRAGMA table_info(execution_events)")}
    finally:
        connection.close()

    forbidden = {"prompt", "transcript", "command", "argv", "environment", "env", "stdout", "stderr", "token", "secret"}
    assert not (record_columns & forbidden)
    assert not (event_columns & forbidden)


# ---------------- WO-P1-246: author-attempt provenance persistence ----------

_V1_DDL = """
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
    created_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),
    updated_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    )
);
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
"""

_V1_ROW = (
    "INSERT INTO execution_records("
    "execution_id, job_id, work_order_ref, project_id, worker_id, backend_id, "
    "agent_ref, repo_root, branch, head_before, operation_ref, "
    "command_fingerprint, command_summary, runtime_profile_ref, run_dir_ref, "
    "stdout_ref, stderr_ref, result_ref, report_ref, transport_state, "
    "execution_state, pid, exit_code, started_at, finished_at, version"
    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)

_V1_ROW_VALUES = (
    "exec-legacy-001",
    "job-001",
    "docs/work-orders/WO-1.md",
    "project-1",
    "a-worker-01",
    "serena-local",
    "agent:chatgpt",
    r"A:\GitHub\example",
    "main",
    "a" * 40,
    "op:pytest-focused",
    "b" * 64,
    "pytest focused regression",
    "runtime:serena-phase6",
    "runs/exec-legacy-001",
    "runs/exec-legacy-001/stdout.log",
    "runs/exec-legacy-001/stderr.log",
    "runs/exec-legacy-001/result.json",
    "runs/exec-legacy-001/report.txt",
    "CONNECTED",
    "SUCCEEDED",
    4242,
    0,
    "2026-08-20T03:00:00Z",
    "2026-08-20T03:01:00Z",
    3,
)


def _make_v1_database(database: Path, *, meta_version: str | None = "1") -> sqlite3.Connection:
    connection = sqlite3.connect(database)
    try:
        connection.executescript(_V1_DDL)
        if meta_version is not None:
            connection.execute(
                "INSERT INTO execution_store_meta(key, value) VALUES('schema_version', ?)",
                (meta_version,),
            )
        connection.execute(_V1_ROW, _V1_ROW_VALUES)
        connection.commit()
    finally:
        connection.close()
    return sqlite3.connect(database)


def _record_columns(connection: sqlite3.Connection) -> set[str]:
    return {row[1] for row in connection.execute("PRAGMA table_info(execution_records)")}


def test_wo246_fresh_store_is_schema_v2_with_nullable_provenance_columns(tmp_path: Path) -> None:
    database = tmp_path / "executions.sqlite"
    store = SQLiteExecutionStore(database)
    store.create(make_record(author_attempt_id="author-attempt-v1:" + "0" * 32,
                             author_generation=0))

    connection = sqlite3.connect(database)
    try:
        assert connection.execute(
            "SELECT value FROM execution_store_meta WHERE key = 'schema_version'"
        ).fetchone()[0] == "2"
        columns = _record_columns(connection)
        assert "author_attempt_id" in columns and "author_generation" in columns

        # fresh-table DDL CHECKs reject invalid generation at SQL level
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(_V1_ROW, _V1_ROW_VALUES)
            connection.execute(
                "UPDATE execution_records SET author_generation = 2"
            )
            connection.commit()
        connection.rollback()
        # ... and mixed-NULL provenance shape
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE execution_records SET author_attempt_id = NULL"
            )
            connection.commit()
    finally:
        connection.close()

    fetched = store.get("exec-001")
    assert fetched.author_attempt_id == "author-attempt-v1:" + "0" * 32
    assert fetched.author_generation == 0


def test_wo246_v1_store_migrates_to_v2_preserving_every_row_value(tmp_path: Path) -> None:
    database = tmp_path / "executions.sqlite"
    _make_v1_database(database, meta_version="1")

    store = SQLiteExecutionStore(database)
    store.initialize()

    connection = sqlite3.connect(database)
    try:
        assert connection.execute(
            "SELECT value FROM execution_store_meta WHERE key = 'schema_version'"
        ).fetchone()[0] == "2"
        row = connection.execute(
            "SELECT " + ", ".join(
                name for name in (
                    "execution_id, job_id, work_order_ref, project_id, worker_id, "
                    "backend_id, agent_ref, repo_root, branch, head_before, operation_ref, "
                    "command_fingerprint, command_summary, runtime_profile_ref, run_dir_ref, "
                    "stdout_ref, stderr_ref, result_ref, report_ref, transport_state, "
                    "execution_state, pid, exit_code, started_at, finished_at, version"
                ).split(", ")
            ) + " FROM execution_records WHERE execution_id = 'exec-legacy-001'"
        ).fetchone()
    finally:
        connection.close()
    assert row == _V1_ROW_VALUES

    record = store.get("exec-legacy-001")
    assert record.execution_state is ExecutionProcessState.SUCCEEDED
    assert record.version == 3


def test_wo246_legacy_rows_emerge_as_none_none_with_no_backfill(tmp_path: Path) -> None:
    database = tmp_path / "executions.sqlite"
    _make_v1_database(database, meta_version="1")
    store = SQLiteExecutionStore(database)
    store.initialize()

    record = store.get("exec-legacy-001")
    assert record.author_attempt_id is None
    assert record.author_generation is None


def test_wo246_migration_is_idempotent(tmp_path: Path) -> None:
    database = tmp_path / "executions.sqlite"
    _make_v1_database(database, meta_version="1")
    store = SQLiteExecutionStore(database)
    store.initialize()
    first = store.get("exec-legacy-001")
    store.initialize()  # second initialize must be a no-op migration

    connection = sqlite3.connect(database)
    try:
        assert connection.execute(
            "SELECT value FROM execution_store_meta WHERE key = 'schema_version'"
        ).fetchone()[0] == "2"
        columns = _record_columns(connection)
        assert "author_attempt_id" in columns and "author_generation" in columns
    finally:
        connection.close()
    assert store.get("exec-legacy-001") == first


def test_wo246_partial_migration_repairs_missing_column(tmp_path: Path) -> None:
    database = tmp_path / "executions.sqlite"
    _make_v1_database(database, meta_version="1")
    connection = sqlite3.connect(database)
    try:
        # foreign/manual partial state: one provenance column already added,
        # meta still v1
        connection.execute("ALTER TABLE execution_records ADD COLUMN author_attempt_id TEXT")
        connection.commit()
    finally:
        connection.close()

    store = SQLiteExecutionStore(database)
    store.initialize()

    connection = sqlite3.connect(database)
    try:
        assert connection.execute(
            "SELECT value FROM execution_store_meta WHERE key = 'schema_version'"
        ).fetchone()[0] == "2"
        columns = _record_columns(connection)
        assert "author_attempt_id" in columns and "author_generation" in columns
    finally:
        connection.close()
    record = store.get("exec-legacy-001")
    assert record.author_attempt_id is None and record.author_generation is None


def test_wo246_tables_without_meta_row_migrate_by_column_shape(tmp_path: Path) -> None:
    database = tmp_path / "executions.sqlite"
    # DDL-committed / meta-write crash edge: tables + rows exist, no meta row
    _make_v1_database(database, meta_version=None)

    store = SQLiteExecutionStore(database)
    store.initialize()

    connection = sqlite3.connect(database)
    try:
        assert connection.execute(
            "SELECT value FROM execution_store_meta WHERE key = 'schema_version'"
        ).fetchone()[0] == "2"
        assert "author_attempt_id" in _record_columns(connection)
    finally:
        connection.close()
    assert store.get("exec-legacy-001").author_attempt_id is None


def test_wo246_unsupported_or_invalid_schema_shape_fails_closed(tmp_path: Path) -> None:
    # unsupported future version
    database = tmp_path / "future.sqlite"
    _make_v1_database(database, meta_version="3")
    with pytest.raises(ExecutionStoreError) as exc_info:
        SQLiteExecutionStore(database).initialize()
    assert exc_info.value.code == "EXECUTION_SCHEMA_VERSION_UNSUPPORTED"

    # v2 meta but a provenance column is missing (inconsistent shape)
    database = tmp_path / "half.sqlite"
    _make_v1_database(database, meta_version="1")
    connection = sqlite3.connect(database)
    try:
        connection.execute("ALTER TABLE execution_records ADD COLUMN author_attempt_id TEXT")
        connection.execute(
            "UPDATE execution_store_meta SET value = '2' WHERE key = 'schema_version'"
        )
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ExecutionStoreError) as exc_info:
        SQLiteExecutionStore(database).initialize()
    assert exc_info.value.code == "EXECUTION_SCHEMA_SHAPE_INVALID"

    # v1 meta but a core column is missing (unrecognized shape)
    database = tmp_path / "broken.sqlite"
    _make_v1_database(database, meta_version="1")
    connection = sqlite3.connect(database)
    try:
        connection.execute("ALTER TABLE execution_records DROP COLUMN report_ref")
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ExecutionStoreError) as exc_info:
        SQLiteExecutionStore(database).initialize()
    assert exc_info.value.code == "EXECUTION_SCHEMA_SHAPE_INVALID"


def test_wo246_malformed_persisted_provenance_reconstructs_invalid(tmp_path: Path) -> None:
    from a_conductor.execution_store import EXECUTION_STORE_SCHEMA_VERSION

    assert EXECUTION_STORE_SCHEMA_VERSION == "2"

    database = tmp_path / "executions.sqlite"
    _make_v1_database(database, meta_version="1")
    # migrated legacy tables carry no CHECKs: raw tampering is representable
    store = SQLiteExecutionStore(database)
    store.initialize()

    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "UPDATE execution_records SET author_attempt_id = 'author-attempt-v1:"
            + "0" * 32 + "' WHERE execution_id = 'exec-legacy-001'"
        )
        connection.commit()  # mixed NULL: attempt present, generation NULL
    finally:
        connection.close()
    with pytest.raises(ExecutionStoreError) as exc_info:
        store.get("exec-legacy-001")
    assert exc_info.value.code == "EXECUTION_RECORD_INVALID"

    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "UPDATE execution_records SET author_generation = 0 "
            "WHERE execution_id = 'exec-legacy-001'"
        )
        connection.commit()
    finally:
        connection.close()
    assert store.get("exec-legacy-001").author_generation == 0

    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "UPDATE execution_records SET author_generation = 5 "
            "WHERE execution_id = 'exec-legacy-001'"
        )
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ExecutionStoreError) as exc_info:
        store.get("exec-legacy-001")
    assert exc_info.value.code == "EXECUTION_RECORD_INVALID"


def test_wo246_record_layer_rejects_mixed_or_out_of_range_pair(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        make_record(author_attempt_id="author-attempt-v1:" + "0" * 32)
    with pytest.raises(ValueError):
        make_record(author_generation=0)
    with pytest.raises(ValueError):
        make_record(author_attempt_id="author-attempt-v1:" + "0" * 32, author_generation=2)
    with pytest.raises(ValueError):
        make_record(author_attempt_id="author-attempt-v1:" + "0" * 32, author_generation=True)
    with pytest.raises(ValueError):
        make_record(author_attempt_id="   ", author_generation=0)
    with pytest.raises(ValueError):
        make_record(author_attempt_id="two\nlines", author_generation=1)
    # both None remains the valid legacy shape
    record = make_record()
    assert record.author_attempt_id is None and record.author_generation is None


def test_wo246_mutations_preserve_provenance_pair(tmp_path: Path) -> None:
    store = SQLiteExecutionStore(tmp_path / "executions.sqlite")
    attempt = "author-attempt-v1:" + "1" * 32
    created = store.create(
        make_record(author_attempt_id=attempt, author_generation=0)
    )
    updated = store.set_transport_state(
        "exec-001", TransportState.LOST, expected_version=created.version
    )
    updated = store.set_execution_state(
        "exec-001", ExecutionProcessState.PROCESS_STILL_RUNNING,
        expected_version=updated.version,
    )
    updated = store.set_process_metadata(
        "exec-001", pid=999, started_at="2026-09-17T00:00:00Z",
        expected_version=updated.version,
    )
    updated = store.set_result_metadata(
        "exec-001", exit_code=0, finished_at="2026-09-17T00:00:01Z",
        expected_version=updated.version,
    )
    assert updated.author_attempt_id == attempt
    assert updated.author_generation == 0
    reopened = SQLiteExecutionStore(tmp_path / "executions.sqlite").get("exec-001")
    assert reopened.author_attempt_id == attempt
    assert reopened.author_generation == 0
