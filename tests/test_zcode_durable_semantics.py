"""Q28 — durable error/recovery/CAS/timeout semantics (restart matrix)."""

from __future__ import annotations

import json

import pytest

from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.supervised_execution import SupervisedExecutionError
from a_conductor.supervised_run_coordinator import SupervisedRunIdentity
from a_conductor.zcode_runner import ZCODE_BACKEND_ID, ZCodeRunError
from tests.test_zcode_runner import (
    BASE_URL,
    BINDING,
    EXEC,
    BUNDLE,
    FS,
    TransportFactory,
    Secrets,
    Selection,
    _packet_file,
    _script,
)
from a_conductor.zcode_runner import ZCodeBackendAdapter, ZCodeTaskPacketIdentity, SupervisedZCodeRunner


def _adapter(tmp_path, *, store, factory=None, secrets=None):
    factory = factory or TransportFactory(_script())
    return ZCodeBackendAdapter(
        transport_factory=factory,
        filesystem=FS(tmp_path),
        execution_store=store,
        selection_source=Selection(),
        expected_binding=BINDING,
        expected_base_url=BASE_URL,
        secret_resolver=secrets or Secrets(),
        secret_reference="secret-ref:zcode-credential",
        packet=ZCodeTaskPacketIdentity.from_task_packet_file(
            _packet_file(tmp_path), trusted_root=str(tmp_path)
        ),
        workspace=str(tmp_path),
        executable=EXEC,
        bundle_js=BUNDLE,
    )


def _identity(tmp_path):
    return SupervisedRunIdentity(
        job_id="j", work_order_ref="WO-P1-158", project_id="p", worker_id="w",
        backend_id=ZCODE_BACKEND_ID, branch="main", head_before="h" * 40,
        runtime_profile_ref="rt", repo_root=str(tmp_path),
    )


def _runner2(tmp_path, *, store, factory=None):
    return SupervisedZCodeRunner(
        task_packet=ZCodeTaskPacketIdentity.from_task_packet_file(
            _packet_file(tmp_path), trusted_root=str(tmp_path)
        ),
        execution_store=store,
        identity=_identity(tmp_path),
        adapter=_adapter(tmp_path, store=store, factory=factory),
        executable=EXEC, bundle_js=BUNDLE, poll_interval_seconds=0.01,
    )


# 1. typed launch error → normalized failure result, no raw traceback
def test_typed_launch_error_normalized(tmp_path):
    from tests.test_zcode_runner import TransportFactory
    store = SQLiteExecutionStore(tmp_path / "q28.sqlite")
    factory = TransportFactory([
        json.dumps({"id": 1, "result": {"session": {"sessionId": "s"}}}),
        json.dumps({"id": 100, "method": "session/requestRuntimePreferences"}),
        json.dumps({"id": 2, "result": {"ok": True}}),
        json.dumps({"method": "session/event", "params": {"type": "turn.failed"}}),
    ])
    runner = _runner2(tmp_path, store=store, factory=factory)
    result = runner.run(operation_ref=None)
    assert "Traceback" not in result.stderr
    assert result.exit_code is None  # failure result, not raise
    assert "TURN_FAILED" in result.stderr


# 2. typed inspect error → recovery path (unknown execution)
def test_typed_inspect_unknown(tmp_path):
    store = SQLiteExecutionStore(tmp_path / "q28.sqlite")
    adapter = _adapter(tmp_path, store=store)
    with pytest.raises(ZCodeRunError):
        adapter.inspect("exec-doesnotexist0000")


# 3. typed collect error → fail closed
def test_typed_collect_unknown(tmp_path):
    store = SQLiteExecutionStore(tmp_path / "q28.sqlite")
    adapter = _adapter(tmp_path, store=store)
    with pytest.raises(ZCodeRunError):
        adapter.collect("exec-doesnotexist0000", expected_version=1)


# 4/5. restart reconstructs from durable store + artifacts
def test_restart_with_result_present_collects(tmp_path):
    store = SQLiteExecutionStore(tmp_path / "q28.sqlite")
    runner = _runner2(tmp_path, store=store)
    result = runner.run(operation_ref=None)
    assert result.exit_code == 0
    # fresh process: brand-new runner+adapter share only the durable store
    fresh_adapter = _adapter(tmp_path, store=store)
    from a_conductor.supervised_execution import (
        SupervisedInspectionState,
    )
    inspection = fresh_adapter.inspect(result.__class__ and _last_exec_id(store))
    assert inspection.state is SupervisedInspectionState.RESULT_AVAILABLE


def _last_exec_id(store):
    # derive the single execution id from the store
    import sqlite3
    con = sqlite3.connect(store.database_path)
    row = con.execute("SELECT execution_id FROM execution_records LIMIT 1").fetchone()
    con.close()
    return row[0]


class SQLiteExecutionPath(SQLiteExecutionStore):
    def __init__(self, tmp_path):
        super().__init__(tmp_path / "q28b.sqlite")


# 6. missing result after restart → recovery, not replay
def test_restart_missing_result_recovery_not_replay(tmp_path):
    store = SQLiteExecutionPath(tmp_path)
    adapter = _adapter(tmp_path, store=store)
    # no run happened; fabricate a record via a completed run then delete result
    runner = _runner2(tmp_path, store=store)
    runner.run(operation_ref=None)
    from pathlib import Path
    record = store.get(_last_exec_id(store))
    (Path(record.repo_root) / record.result_ref).unlink()
    fresh = _adapter(tmp_path, store=store)
    inspection = fresh.inspect(record.execution_id)
    assert inspection.recovery_required is True  # no result -> recovery
    assert not inspection.result_available


# 9/10. version CAS conflict → fail closed
def test_collect_version_conflict_fails_closed(tmp_path):
    store = SQLiteExecutionPath(tmp_path)
    runner = _runner2(tmp_path, store=store)
    runner.run(operation_ref=None)
    record = store.get(_last_exec_id(store))
    adapter = _adapter(tmp_path, store=store)
    with pytest.raises(SupervisedExecutionError) as exc:
        adapter.collect(record.execution_id, expected_version=record.version + 5)
    assert "ZCODE_VERSION_CONFLICT" in str(exc.value)


def test_collect_matching_version_succeeds(tmp_path):
    store = SQLiteExecutionPath(tmp_path)
    runner = _runner2(tmp_path, store=store)
    runner.run(operation_ref=None)
    record = store.get(_last_exec_id(store))
    adapter = _adapter(tmp_path, store=store)
    outcome = adapter.collect(record.execution_id, expected_version=record.version)
    assert outcome.result is not None


# 14. UNKNOWN never fabricates result (durable artifact check)
def test_unknown_never_fabricates_result(tmp_path):
    store = SQLiteExecutionPath(tmp_path)
    from tests.test_zcode_runner import TransportFactory
    failing = TransportFactory([
        json.dumps({"id": 1, "result": {"session": {"sessionId": "s"}}}),
        json.dumps({"id": 100, "method": "session/requestRuntimePreferences"}),
        json.dumps({"id": 2, "result": {"ok": True}}),
        json.dumps({"method": "session/event", "params": {"type": "turn.failed"}}),
    ])
    runner = _runner2(tmp_path, store=store, factory=failing)
    result = runner.run(operation_ref=None)
    assert result.exit_code is None
    record = store.get(_last_exec_id(store))
    from pathlib import Path
    assert not (Path(record.repo_root) / record.result_ref).exists()


# ZCodeRunError is a SupervisedExecutionError (shared-coordinator mapping)
def test_zcode_error_is_supervised_error():
    assert issubclass(ZCodeRunError, SupervisedExecutionError)
    err = ZCodeRunError("ZCODE_TEST_CODE")
    assert err.code == "ZCODE_TEST_CODE"
    assert err.recovery_required is True
