from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from threading import Barrier, Event, Lock, get_ident

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


def test_initialize_is_safe_for_two_callers_that_both_observe_missing_schema_version(tmp_path: Path) -> None:
    """Deterministically force the historical SELECT-then-INSERT race.

    Both initializers observe no schema-version row before either INSERT. The
    first INSERT is allowed to commit before the second executes, so a plain
    INSERT deterministically raises while an idempotent initialization path
    succeeds for both callers.
    """
    database = tmp_path / "concurrent-init.sqlite"
    select_barrier = Barrier(2)
    insert_lock = Lock()
    winner_committed = Event()
    forced_race_ready = Event()
    winner_ident = {"value": None}

    class CursorProxy:
        def __init__(self, cursor, *, schema_select: bool = False):
            self._cursor = cursor
            self._schema_select = schema_select

        def fetchone(self):
            row = self._cursor.fetchone()
            if self._schema_select:
                select_barrier.wait(timeout=5)
                forced_race_ready.set()
            return row

        def __getattr__(self, name):
            return getattr(self._cursor, name)

    class ConnectionProxy:
        def __init__(self, connection):
            self._connection = connection
            self._saw_schema_insert = False

        def executescript(self, script):
            return self._connection.executescript(script)

        def execute(self, sql, parameters=()):
            normalized = " ".join(sql.upper().split())
            schema_select = (
                "SELECT VALUE FROM EXECUTION_STORE_META" in normalized
                and "SCHEMA_VERSION" in normalized
            )
            schema_insert = (
                "INSERT" in normalized
                and "EXECUTION_STORE_META" in normalized
                and "SCHEMA_VERSION" in normalized
            )
            select_before_insert = schema_select and not self._saw_schema_insert
            if schema_insert:
                self._saw_schema_insert = True
            if schema_insert and forced_race_ready.is_set():
                current = get_ident()
                with insert_lock:
                    if winner_ident["value"] is None:
                        winner_ident["value"] = current
                    winner = winner_ident["value"] == current
                if not winner:
                    assert winner_committed.wait(5), "winner did not commit schema row"
            cursor = self._connection.execute(sql, parameters)
            return CursorProxy(cursor, schema_select=select_before_insert)

        def commit(self):
            self._connection.commit()
            if winner_ident["value"] == get_ident():
                winner_committed.set()

        def rollback(self):
            self._connection.rollback()

        def __getattr__(self, name):
            return getattr(self._connection, name)

    class RacingStore(SQLiteExecutionStore):
        @contextmanager
        def _connect(self):
            with super()._connect() as connection:
                yield ConnectionProxy(connection)

    stores = [RacingStore(database), RacingStore(database)]

    def initialize(store):
        try:
            store.initialize()
            return "OK"
        except ExecutionStoreError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(initialize, stores))

    assert outcomes == ["OK", "OK"]
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT key, value FROM execution_store_meta ORDER BY key"
        ).fetchall()
    assert rows == [("schema_version", "1")]


def test_concurrent_initialize_stress_yields_single_schema_row_per_database(tmp_path: Path) -> None:
    threads = 8
    rounds = 10
    for round_no in range(rounds):
        database = tmp_path / f"stress-init-{round_no}.sqlite"
        stores = [SQLiteExecutionStore(database) for _ in range(threads)]
        start = Barrier(threads)

        def initialize(store):
            start.wait(timeout=5)
            try:
                store.initialize()
                return "OK"
            except ExecutionStoreError as exc:
                return exc.code

        with ThreadPoolExecutor(max_workers=threads) as pool:
            outcomes = list(pool.map(initialize, stores))

        assert outcomes == ["OK"] * threads
        with sqlite3.connect(database) as connection:
            rows = connection.execute(
                "SELECT key, value FROM execution_store_meta ORDER BY key"
            ).fetchall()
        assert rows == [("schema_version", "1")]


def test_initialize_still_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    database = tmp_path / "unsupported.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE execution_store_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO execution_store_meta(key, value) VALUES('schema_version', '999')"
        )
        connection.commit()

    store = SQLiteExecutionStore(database)
    with pytest.raises(ExecutionStoreError) as exc_info:
        store.initialize()
    assert exc_info.value.code == "EXECUTION_SCHEMA_VERSION_UNSUPPORTED"
