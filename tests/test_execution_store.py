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
    database = tmp_path / "executions.sqlite"
    store = SQLiteExecutionStore(database)
    created = store.create(make_record())
    updated = store.set_transport_state(
        "exec-001", TransportState.LOST, expected_version=created.version
    )
    events_before = store.list_events("exec-001")

    connection = sqlite3.connect(database)
    try:
        connection.execute("DROP TABLE execution_receipts")
        connection.commit()
    finally:
        connection.close()

    migrated = SQLiteExecutionStore(database)
    migrated.initialize()
    migrated.initialize()

    assert migrated.get("exec-001") == updated
    assert migrated.list_events("exec-001") == events_before
    connection = sqlite3.connect(database)
    try:
        version = connection.execute(
            "SELECT value FROM execution_store_meta WHERE key = 'schema_version'"
        ).fetchone()[0]
    finally:
        connection.close()
    assert version == "1"
    recorded = migrated.record_receipt(make_receipt())
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
