from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
import threading
from threading import Barrier, Event, Lock, get_ident

import pytest

from a_conductor.execution_record import (
    DurableExecutionReceipt,
    DurableExecutionRecord,
    ExecutionProcessState,
    ReceiptDisposition,
    TransportState,
    compute_receipt_id,
    new_execution_record,
    new_execution_receipt,
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
        receipt_columns = {row[1] for row in connection.execute("PRAGMA table_info(execution_receipts)")}
    finally:
        connection.close()

    forbidden = {"prompt", "transcript", "command", "argv", "environment", "env", "stdout", "stderr", "token", "secret"}
    assert not (record_columns & forbidden)
    assert not (event_columns & forbidden)
    assert not (receipt_columns & forbidden)


def make_receipt(execution_id: str = "exec-001", **overrides) -> DurableExecutionReceipt:
    values = dict(
        execution_id=execution_id,
        attempt_id="attempt-001",
        result_digest="c" * 64,
        binding_digest="d" * 64,
        claim_generation=3,
        authority_sha="1" * 40,
        execution_sha="2" * 40,
        disposition=ReceiptDisposition.ACCEPTED,
        evidence_ref="evidence:dex-collect-1",
    )
    values.update(overrides)
    return new_execution_receipt(**values)


def receipt_row_count(database: Path) -> int:
    connection = sqlite3.connect(database)
    try:
        return int(
            connection.execute("SELECT COUNT(*) FROM execution_receipts").fetchone()[0]
        )
    finally:
        connection.close()


def receipt_event_count(store: SQLiteExecutionStore, execution_id: str) -> int:
    return sum(
        1
        for event in store.list_events(execution_id)
        if event.event_type is ExecutionEventType.RECEIPT_RECORDED
    )


def test_receipt_round_trip_and_reopen_persists_durable_receipt(tmp_path: Path) -> None:
    database = tmp_path / "executions.sqlite"
    store = SQLiteExecutionStore(database)
    store.create(make_record())

    recorded = store.record_receipt(make_receipt())

    assert recorded.recorded_at
    assert recorded == store.get_receipt(recorded.receipt_id)
    assert recorded == SQLiteExecutionStore(database).get_receipt(recorded.receipt_id)


def test_repeated_identical_receipt_returns_existing_without_duplicates(tmp_path: Path) -> None:
    database = tmp_path / "executions.sqlite"
    store = SQLiteExecutionStore(database)
    store.create(make_record())

    first = store.record_receipt(make_receipt())
    second = store.record_receipt(make_receipt())

    assert second == first
    assert second.recorded_at == first.recorded_at
    assert receipt_row_count(database) == 1
    assert receipt_event_count(store, "exec-001") == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"claim_generation": 4},
        {"authority_sha": "9" * 40},
        {"execution_sha": "8" * 40},
        {"disposition": ReceiptDisposition.QUARANTINED},
        {"evidence_ref": "evidence:dex-collect-2"},
        {"evidence_ref": None},
    ],
)
def test_conflicting_immutable_receipt_facts_fail_closed(
    tmp_path: Path, overrides: dict
) -> None:
    database = tmp_path / "executions.sqlite"
    store = SQLiteExecutionStore(database)
    store.create(make_record())
    original = store.record_receipt(make_receipt())
    events_before = store.list_events("exec-001")

    with pytest.raises(ExecutionStoreError) as exc_info:
        store.record_receipt(make_receipt(**overrides))
    assert exc_info.value.code == "RECEIPT_CONFLICT"

    assert store.get_receipt(original.receipt_id) == original
    assert receipt_row_count(database) == 1
    assert store.list_events("exec-001") == events_before


def test_receipt_for_missing_execution_fails_closed(tmp_path: Path) -> None:
    database = tmp_path / "executions.sqlite"
    store = SQLiteExecutionStore(database)
    store.initialize()

    with pytest.raises(ExecutionStoreError) as exc_info:
        store.record_receipt(make_receipt(execution_id="exec-missing"))
    assert exc_info.value.code == "EXECUTION_NOT_FOUND"
    assert receipt_row_count(database) == 0


def test_concurrent_identical_receipt_writes_converge_to_one_durable_row(
    tmp_path: Path,
) -> None:
    database = tmp_path / "executions.sqlite"
    setup = SQLiteExecutionStore(database)
    setup.create(make_record())

    worker_count = 8
    stores = [SQLiteExecutionStore(database) for _ in range(worker_count)]
    for worker_store in stores:
        worker_store.initialize()
    barrier = threading.Barrier(worker_count)
    results: list[DurableExecutionReceipt | BaseException] = [None] * worker_count

    def ingest(index: int) -> None:
        try:
            barrier.wait()
            results[index] = stores[index].record_receipt(make_receipt())
        except BaseException as exc:  # noqa: BLE001 - collected for assertion
            results[index] = exc

    threads = [
        threading.Thread(target=ingest, args=(index,)) for index in range(worker_count)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    for outcome in results:
        assert not isinstance(outcome, BaseException), outcome
    durable = {outcome for outcome in results}
    assert len(durable) == 1
    assert receipt_row_count(database) == 1
    assert receipt_event_count(setup, "exec-001") == 1


def test_concurrent_conflicting_receipt_races_fail_closed_deterministically(
    tmp_path: Path,
) -> None:
    database = tmp_path / "executions.sqlite"
    setup = SQLiteExecutionStore(database)
    setup.create(make_record())

    worker_count = 8
    stores = [SQLiteExecutionStore(database) for _ in range(worker_count)]
    for worker_store in stores:
        worker_store.initialize()
    barrier = threading.Barrier(worker_count)
    outcomes: list[tuple[str, object]] = [None] * worker_count  # type: ignore[list-item]

    def ingest(index: int) -> None:
        try:
            barrier.wait()
            if index % 2 == 0:
                outcomes[index] = ("ok", stores[index].record_receipt(make_receipt()))
            else:
                outcomes[index] = (
                    "ok",
                    stores[index].record_receipt(make_receipt(claim_generation=4)),
                )
        except ExecutionStoreError as exc:
            outcomes[index] = ("conflict", exc.code)
        except BaseException as exc:  # noqa: BLE001 - collected for assertion
            outcomes[index] = ("error", exc)

    threads = [
        threading.Thread(target=ingest, args=(index,)) for index in range(worker_count)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    successes = [payload for kind, payload in outcomes if kind == "ok"]
    conflicts = [payload for kind, payload in outcomes if kind == "conflict"]
    errors = [payload for kind, payload in outcomes if kind == "error"]
    assert not errors, errors
    assert successes
    assert len(successes) + len(conflicts) == worker_count
    assert len({receipt.recorded_at for receipt in successes}) == 1
    assert set(conflicts) == {"RECEIPT_CONFLICT"}
    assert receipt_row_count(database) == 1
    durable = setup.get_receipt(successes[0].receipt_id)
    assert durable in successes
    assert receipt_event_count(setup, "exec-001") == 1


def test_additive_initialization_on_existing_v1_db_preserves_records_and_events(
    tmp_path: Path,
) -> None:
    # WO-P1-246 fan-in: fresh databases are now created in the v2 shape, so a
    # genuine current-main accepted v1 database (legacy execution_records,
    # DEX execution_receipts support, schema_version 1) is built explicitly.
    # Additive initialization must migrate it to v2 while preserving records
    # and events, and must recreate a missing receipts table without
    # fabricating receipt evidence.
    database = tmp_path / "executions.sqlite"
    _make_main_v1_database(database)

    connection = sqlite3.connect(database)
    try:
        connection.execute("DROP TABLE execution_receipts")
        connection.commit()
    finally:
        connection.close()

    migrated = SQLiteExecutionStore(database)
    migrated.initialize()
    migrated.initialize()

    record = migrated.get("exec-legacy-001")
    assert record.execution_state is ExecutionProcessState.SUCCEEDED
    assert record.author_attempt_id is None
    assert record.author_generation is None
    connection = sqlite3.connect(database)
    try:
        version = connection.execute(
            "SELECT value FROM execution_store_meta WHERE key = 'schema_version'"
        ).fetchone()[0]
        receipt_rows = connection.execute(
            "SELECT COUNT(*) FROM execution_receipts"
        ).fetchone()[0]
    finally:
        connection.close()
    assert version == "2"
    assert receipt_rows == 0
    recorded = migrated.record_receipt(make_receipt(execution_id="exec-legacy-001"))
    assert migrated.get_receipt(recorded.receipt_id) == recorded


def test_distinct_binding_digest_is_distinct_receipt_identity(tmp_path: Path) -> None:
    database = tmp_path / "executions.sqlite"
    store = SQLiteExecutionStore(database)
    store.create(make_record())

    first = store.record_receipt(make_receipt())
    second = store.record_receipt(make_receipt(binding_digest="e" * 64))

    assert second.receipt_id != first.receipt_id
    assert receipt_row_count(database) == 2
    assert store.get_receipt(first.receipt_id) == first
    assert store.get_receipt(second.receipt_id) == second


def test_get_missing_receipt_returns_stable_error_code(tmp_path: Path) -> None:
    store = SQLiteExecutionStore(tmp_path / "executions.sqlite")
    store.initialize()
    with pytest.raises(ExecutionStoreError) as exc_info:
        store.get_receipt("f" * 64)
    assert exc_info.value.code == "RECEIPT_NOT_FOUND"


def test_record_receipt_requires_receipt_model(tmp_path: Path) -> None:
    store = SQLiteExecutionStore(tmp_path / "executions.sqlite")
    with pytest.raises(ValueError):
        store.record_receipt({"receipt_id": "not-a-receipt"})


def test_receipt_persistence_exposes_no_rewrite_or_delete_api(tmp_path: Path) -> None:
    store = SQLiteExecutionStore(tmp_path / "executions.sqlite")
    for forbidden in (
        "update_receipt",
        "delete_receipt",
        "rewrite_receipt",
        "replace_receipt",
    ):
        assert not hasattr(store, forbidden)


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
    assert rows == [("schema_version", "2")]


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
        assert rows == [("schema_version", "2")]


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
            connection.execute("UPDATE execution_records SET author_generation = 2")
        connection.rollback()
        # ... and mixed-NULL provenance shape
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE execution_records SET author_attempt_id = NULL"
            )
        connection.rollback()
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


# --- WO-P1-246 repair: provenance columns are validated by declared shape,
# not by name only. A pre-existing author_attempt_id/author_generation
# column must be canonical (exact declared type TEXT/INTEGER, nullable, no
# default, not PK) before it is accepted, ALTERed around, or stamped v2. ---


def _record_column_info(
    connection: sqlite3.Connection,
) -> dict[str, tuple[str, int, str | None, int]]:
    return {
        row[1]: (row[2], row[3], row[4], row[5])
        for row in connection.execute("PRAGMA table_info(execution_records)")
    }


def _schema_version(connection: sqlite3.Connection) -> str | None:
    row = connection.execute(
        "SELECT value FROM execution_store_meta WHERE key = 'schema_version'"
    ).fetchone()
    return None if row is None else row[0]


def _make_foreign_v1_database(
    database: Path,
    provenance_column_ddl: str,
    *,
    provenance_column_is_pk: bool = False,
    meta_version: str | None = "1",
) -> None:
    """Foreign/manual pre-v2 database: v1 records table plus one
    pre-existing provenance column declared by ``provenance_column_ddl``
    in an arbitrary shape. No rows: these cases fail on schema shape
    before any row is read."""
    ddl = _V1_DDL
    if provenance_column_is_pk:
        # a table may declare only one PRIMARY KEY: demote execution_id so
        # the provenance column can carry it
        ddl = ddl.replace(
            "execution_id TEXT PRIMARY KEY CHECK (trim(execution_id) <> '')",
            "execution_id TEXT CHECK (trim(execution_id) <> '')",
            1,
        )
    ddl = ddl.replace(
        "    version INTEGER NOT NULL CHECK (version >= 1),",
        "    version INTEGER NOT NULL CHECK (version >= 1),\n    "
        + provenance_column_ddl
        + ",",
        1,
    )
    connection = sqlite3.connect(database)
    try:
        connection.executescript(ddl)
        if meta_version is not None:
            connection.execute(
                "INSERT INTO execution_store_meta(key, value) "
                "VALUES('schema_version', ?)",
                (meta_version,),
            )
        connection.commit()
    finally:
        connection.close()


def test_wo246_partial_v1_text_typed_generation_fails_closed_unstamped(
    tmp_path: Path,
) -> None:
    # P2 repro: partial v1 (meta still "1") carrying author_generation
    # declared TEXT. TEXT affinity silently coerces stored generations to
    # text, so stamping this shape v2 makes generation 0 read as text and
    # every record reconstruct as EXECUTION_RECORD_INVALID. The shape must
    # fail closed instead and must never be stamped v2.
    database = tmp_path / "executions.sqlite"
    _make_v1_database(database, meta_version="1")
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "ALTER TABLE execution_records ADD COLUMN author_generation TEXT"
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ExecutionStoreError) as exc_info:
        SQLiteExecutionStore(database).initialize()
    assert exc_info.value.code == "EXECUTION_SCHEMA_SHAPE_INVALID"

    connection = sqlite3.connect(database)
    try:
        assert _schema_version(connection) == "1"
    finally:
        connection.close()


@pytest.mark.parametrize(
    "provenance_column_ddl",
    [
        "author_attempt_id INTEGER",
        "author_attempt_id TEXT NOT NULL",
        "author_attempt_id TEXT DEFAULT 'foreign'",
        "author_attempt_id TEXT PRIMARY KEY",
        "author_generation TEXT",
        "author_generation REAL",
        "author_generation INTEGER NOT NULL",
        "author_generation INTEGER DEFAULT 0",
        "author_generation INTEGER PRIMARY KEY",
    ],
)
def test_wo246_noncanonical_preexisting_provenance_shapes_fail_closed_unstamped(
    tmp_path: Path, provenance_column_ddl: str
) -> None:
    database = tmp_path / "executions.sqlite"
    _make_foreign_v1_database(
        database,
        provenance_column_ddl,
        provenance_column_is_pk=provenance_column_ddl.endswith("PRIMARY KEY"),
    )

    with pytest.raises(ExecutionStoreError) as exc_info:
        SQLiteExecutionStore(database).initialize()
    assert exc_info.value.code == "EXECUTION_SCHEMA_SHAPE_INVALID"

    connection = sqlite3.connect(database)
    try:
        assert _schema_version(connection) == "1"
    finally:
        connection.close()


def test_wo246_v2_meta_noncanonical_provenance_columns_fail_closed(
    tmp_path: Path,
) -> None:
    # acceptance path: meta already claims 2, but a provenance column is a
    # foreign shape (TEXT-typed generation) — must not be accepted as v2
    database = tmp_path / "executions.sqlite"
    _make_v1_database(database, meta_version="1")
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "ALTER TABLE execution_records ADD COLUMN author_attempt_id TEXT"
        )
        connection.execute(
            "ALTER TABLE execution_records ADD COLUMN author_generation TEXT"
        )
        connection.execute(
            "UPDATE execution_store_meta SET value = '2' "
            "WHERE key = 'schema_version'"
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ExecutionStoreError) as exc_info:
        SQLiteExecutionStore(database).initialize()
    assert exc_info.value.code == "EXECUTION_SCHEMA_SHAPE_INVALID"


def test_wo246_missing_meta_with_noncanonical_shape_is_not_stamped_v2(
    tmp_path: Path,
) -> None:
    # DDL-committed/meta-crash edge with a foreign shape present: the
    # unsafe NOT NULL DEFAULT 0 generation would backfill legacy rows with
    # generation 0. The stamp must require the canonical shape first.
    database = tmp_path / "executions.sqlite"
    _make_v1_database(database, meta_version=None)
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "ALTER TABLE execution_records ADD COLUMN author_attempt_id TEXT"
        )
        connection.execute(
            "ALTER TABLE execution_records ADD COLUMN author_generation "
            "INTEGER NOT NULL DEFAULT 0"
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ExecutionStoreError) as exc_info:
        SQLiteExecutionStore(database).initialize()
    assert exc_info.value.code == "EXECUTION_SCHEMA_SHAPE_INVALID"

    connection = sqlite3.connect(database)
    try:
        assert _schema_version(connection) is None
    finally:
        connection.close()


def test_wo246_partial_migration_repairs_missing_attempt_column(
    tmp_path: Path,
) -> None:
    # symmetric partial state (canonical generation column already
    # present) still migrates and stays NULL/NULL
    database = tmp_path / "executions.sqlite"
    _make_v1_database(database, meta_version="1")
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "ALTER TABLE execution_records ADD COLUMN author_generation INTEGER"
        )
        connection.commit()
    finally:
        connection.close()

    store = SQLiteExecutionStore(database)
    store.initialize()

    connection = sqlite3.connect(database)
    try:
        assert _schema_version(connection) == "2"
        columns = _record_columns(connection)
        assert "author_attempt_id" in columns and "author_generation" in columns
    finally:
        connection.close()
    record = store.get("exec-legacy-001")
    assert record.author_attempt_id is None and record.author_generation is None


def test_wo246_fresh_and_migrated_provenance_declared_shape_is_canonical(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "fresh.sqlite"
    SQLiteExecutionStore(fresh).create(make_record())

    migrated = tmp_path / "migrated.sqlite"
    _make_v1_database(migrated, meta_version="1")
    SQLiteExecutionStore(migrated).initialize()

    for database in (fresh, migrated):
        connection = sqlite3.connect(database)
        try:
            info = _record_column_info(connection)
        finally:
            connection.close()
        assert info["author_attempt_id"] == ("TEXT", 0, None, 0)
        assert info["author_generation"] == ("INTEGER", 0, None, 0)


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


# --- WO-P1-246 repair: concurrent first-initialize / fresh-stamp race.
# Two initialize() callers can both observe schema_version absent on a
# fresh v2-shaped database and then race on the stamp INSERT into
# execution_store_meta. Mirrors the WO-P1-242 job_store precedent
# deterministically. ---


def test_wo246_concurrent_first_initialize_converges_on_schema_v2(
    tmp_path: Path,
) -> None:
    """Deterministically force the historical SELECT-then-INSERT race.

    Both initializers observe no schema_version row before either stamps;
    the winner's INSERT is allowed to commit before the loser's executes,
    so a plain INSERT deterministically raises IntegrityError ->
    EXECUTION_STORE_INIT_FAILED for the loser, while an idempotent stamp
    path converges for both callers on schema_version 2.
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

        def __iter__(self):
            return iter(self._cursor)

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
    assert rows == [("schema_version", "2")]


def test_wo246_stale_fresh_stamp_never_overwrites_conflicting_non_2_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # complement to the convergence repro: if a conflicting non-2 value
    # lands between the racing absent-read and the stamp, the initializer
    # must fail closed on the foreign value, never overwrite it with 2
    database = tmp_path / "conflicting-stamp.sqlite"
    SQLiteExecutionStore(database).initialize()

    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "UPDATE execution_store_meta SET value = '3' "
            "WHERE key = 'schema_version'"
        )
        connection.commit()
    finally:
        connection.close()

    real_schema_version = SQLiteExecutionStore._schema_version
    stale_read_used = {"value": False}

    def stale_absent_then_real(connection: sqlite3.Connection):
        if not stale_read_used["value"]:
            stale_read_used["value"] = True  # the racing read saw no row
            return None
        return real_schema_version(connection)

    monkeypatch.setattr(
        SQLiteExecutionStore,
        "_schema_version",
        staticmethod(stale_absent_then_real),
    )
    loser = SQLiteExecutionStore(database)
    with pytest.raises(ExecutionStoreError) as exc_info:
        loser.initialize()
    assert exc_info.value.code == "EXECUTION_SCHEMA_VERSION_UNSUPPORTED"
    monkeypatch.undo()

    connection = sqlite3.connect(database)
    try:
        assert connection.execute(
            "SELECT value FROM execution_store_meta WHERE key = 'schema_version'"
        ).fetchone()[0] == "3"
    finally:
        connection.close()


# ---- WO-P1-246 fan-in: current-main v1 (receipt-capable) DB integration ----
# The accepted current-main v1 shape differs from the legacy WO246 _V1_DDL
# fixture: it carries DEX execution_receipts support. Migration must cover
# BOTH shapes and never delete or rewrite receipt evidence.

_MAIN_V1_RECEIPTS_DDL = """
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


def _legacy_receipt_id() -> str:
    return compute_receipt_id(
        execution_id="exec-legacy-001",
        attempt_id="dex-attempt-001",
        result_digest="c" * 64,
        binding_digest="d" * 64,
    )


def _make_main_v1_database(database: Path) -> None:
    """A genuine current-main accepted v1 database: legacy execution_records
    shape (no provenance columns), DEX execution_receipts support, and
    schema_version 1, holding one record, one durable receipt, and its
    RECEIPT_RECORDED event."""
    connection = sqlite3.connect(database)
    try:
        connection.executescript(_V1_DDL)
        connection.executescript(_MAIN_V1_RECEIPTS_DDL)
        connection.execute(
            "INSERT INTO execution_store_meta(key, value) "
            "VALUES('schema_version', '1')"
        )
        connection.execute(_V1_ROW, _V1_ROW_VALUES)
        connection.execute(
            "INSERT INTO execution_receipts("
            "receipt_id, execution_id, attempt_id, result_digest, binding_digest, "
            "claim_generation, authority_sha, execution_sha, disposition, "
            "evidence_ref"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                _legacy_receipt_id(),
                "exec-legacy-001",
                "dex-attempt-001",
                "c" * 64,
                "d" * 64,
                3,
                "1" * 40,
                "2" * 40,
                "ACCEPTED",
                "evidence:dex-collect-legacy",
            ),
        )
        connection.execute(
            "INSERT INTO execution_events("
            "event_id, execution_id, sequence_no, event_type, evidence_ref"
            ") VALUES ('evt-legacy-receipt-1', 'exec-legacy-001', 1, "
            "'RECEIPT_RECORDED', ?)",
            (_legacy_receipt_id(),),
        )
        connection.commit()
    finally:
        connection.close()


def test_wo246_fanin_main_v1_receipt_db_migrates_preserving_receipt_evidence(
    tmp_path: Path,
) -> None:
    database = tmp_path / "executions.sqlite"
    _make_main_v1_database(database)

    def snapshot() -> tuple:
        connection = sqlite3.connect(database)
        try:
            receipts = connection.execute(
                "SELECT receipt_id, execution_id, attempt_id, result_digest, "
                "binding_digest, claim_generation, authority_sha, execution_sha, "
                "disposition, evidence_ref, recorded_at "
                "FROM execution_receipts ORDER BY receipt_id"
            ).fetchall()
            events = connection.execute(
                "SELECT execution_id, sequence_no, event_type, evidence_ref, "
                "recorded_at FROM execution_events "
                "ORDER BY execution_id, sequence_no"
            ).fetchall()
            return receipts, events
        finally:
            connection.close()

    receipts_before, events_before = snapshot()

    store = SQLiteExecutionStore(database)
    store.initialize()
    store.initialize()

    receipts_after, events_after = snapshot()
    assert receipts_after == receipts_before
    assert events_after == events_before

    connection = sqlite3.connect(database)
    try:
        assert connection.execute(
            "SELECT value FROM execution_store_meta WHERE key = 'schema_version'"
        ).fetchone()[0] == "2"
        columns = _record_columns(connection)
    finally:
        connection.close()
    assert {"author_attempt_id", "author_generation"} <= columns

    record = store.get("exec-legacy-001")
    assert record.author_attempt_id is None
    assert record.author_generation is None

    durable = store.get_receipt(_legacy_receipt_id())
    assert durable.attempt_id == "dex-attempt-001"
    assert durable.claim_generation == 3

    replay = store.record_receipt(durable)
    assert replay == durable
    assert receipt_row_count(database) == 1
    assert receipt_event_count(store, "exec-legacy-001") == 1

    with pytest.raises(ExecutionStoreError) as exc_info:
        store.record_receipt(
            make_receipt(
                execution_id="exec-legacy-001",
                attempt_id="dex-attempt-001",
                result_digest="c" * 64,
                binding_digest="d" * 64,
                claim_generation=4,
                authority_sha="1" * 40,
                execution_sha="2" * 40,
                evidence_ref="evidence:dex-collect-legacy",
            )
        )
    assert exc_info.value.code == "RECEIPT_CONFLICT"
    assert receipt_row_count(database) == 1


def test_wo246_fanin_legacy_v1_db_without_receipts_gains_empty_receipts_table(
    tmp_path: Path,
) -> None:
    database = tmp_path / "executions.sqlite"
    _make_v1_database(database, meta_version="1")

    store = SQLiteExecutionStore(database)
    store.initialize()

    assert receipt_row_count(database) == 0
    record = store.get("exec-legacy-001")
    assert record.author_attempt_id is None
    assert record.author_generation is None
    recorded = store.record_receipt(
        make_receipt(execution_id="exec-legacy-001", attempt_id="dex-new-001")
    )
    assert store.get_receipt(recorded.receipt_id) == recorded


def test_wo246_fanin_author_provenance_and_dex_receipt_stay_distinct(
    tmp_path: Path,
) -> None:
    database = tmp_path / "executions.sqlite"
    store = SQLiteExecutionStore(database)
    store.create(
        make_record(
            execution_id="exec-001",
            author_attempt_id="author-attempt-v1:" + "1" * 32,
            author_generation=1,
        )
    )

    receipt = store.record_receipt(
        make_receipt(attempt_id="dex-attempt-9", claim_generation=7)
    )

    fetched = store.get("exec-001")
    assert fetched.author_attempt_id == "author-attempt-v1:" + "1" * 32
    assert fetched.author_generation == 1

    durable = store.get_receipt(receipt.receipt_id)
    assert durable.attempt_id == "dex-attempt-9"
    assert durable.claim_generation == 7
    assert durable.execution_id == fetched.execution_id

    updated = store.set_transport_state(
        "exec-001", TransportState.LOST, expected_version=fetched.version
    )
    assert updated.author_attempt_id == fetched.author_attempt_id
    assert updated.author_generation == fetched.author_generation
    assert store.get_receipt(receipt.receipt_id) == durable

    second = store.record_receipt(
        make_receipt(attempt_id="dex-attempt-10", claim_generation=8)
    )
    assert second.receipt_id != receipt.receipt_id
    assert receipt_row_count(database) == 2
    assert store.get("exec-001").author_attempt_id == "author-attempt-v1:" + "1" * 32
