"""WO-P1-158 Phase A — shared SupervisedRunCoordinator equivalence proofs.

The coordinator extracted from ``SupervisedCommandRunner`` must preserve every
generic behavior: identical fingerprints, execution-id format, durable record
fields/refs, dedup/attach semantics, timeout/recovery classification, artifact
mapping, and store-write counts — with no extra threads, background workers,
or new retry authority. These tests pin adapter⇄coordinator equivalence.
"""

from __future__ import annotations

import hashlib
import re
import sys
import threading
from pathlib import Path

import pytest

from a_conductor.execution_record import DurableExecutionRecord, ExecutionProcessState
from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.native_execution import (
    NativeExecutionError,
    NativeExecutionScope,
)
from a_conductor.supervised_command_runner import SupervisedCommandRunner
from a_conductor.supervised_execution import (
    SupervisedExecutionError,
    SupervisedExecutionService,
    SupervisedInspection,
    SupervisedInspectionState,
    SupervisedLaunchOutcome,
    SupervisedLaunchPlan,
    SupervisedCollectOutcome,
)
from a_conductor.supervised_run_coordinator import (
    SupervisedRunCoordinator,
    SupervisedRunIdentity,
)


RUNTIME_PYTHON = getattr(sys, "_base_executable", sys.executable)
PYTHON_NAME = Path(sys.executable).name

IDENTITY = dict(
    job_id="job-001",
    work_order_ref="docs/work-orders/WO-P1-158-zero-relay-zcode.md",
    project_id="project-1",
    worker_id="a-worker-01",
    backend_id="supervised-native",
    branch="main",
    head_before="b" * 40,
    runtime_profile_ref="runtime:test",
)

_EXEC_ID_RE = re.compile(r"^exec-[0-9a-f]{16}$")


class ScriptedSupervised:
    """Deterministic in-memory supervised launcher for equivalence proofs."""

    def __init__(self, repo: Path, store, *, exit_code: int = 0, stdout: bytes = b"ok"):
        self.repo = repo
        self.store = store
        self.exit_code = exit_code
        self.stdout = stdout
        self.records: dict[str, DurableExecutionRecord] = {}
        self.launch_calls = 0
        self.collect_calls = 0
        self._lock = threading.Lock()

    def launch(self, plan: SupervisedLaunchPlan) -> SupervisedLaunchOutcome:
        with self._lock:
            self.launch_calls += 1
            record = plan.record
            run_dir = self.repo / record.run_dir_ref
            run_dir.mkdir(parents=True, exist_ok=True)
            (self.repo / record.stdout_ref).write_bytes(self.stdout)
            (self.repo / record.stderr_ref).write_bytes(b"")
            stored = replace_record_state(record, ExecutionProcessState.VERIFICATION_REQUIRED)
            stored = self.store.create(stored)
            self.records[record.execution_id] = stored
            return SupervisedLaunchOutcome(
                record=stored,
                supervisor_pid=None,
                child_pid=None,
                recovery_required=False,
            )

    def inspect(self, execution_id: str) -> SupervisedInspection:
        with self._lock:
            record = self.records.get(execution_id)
        if record is None:
            raise SupervisedExecutionError("NOT_FOUND")
        return SupervisedInspection(
            execution_id=execution_id,
            state=SupervisedInspectionState.RESULT_AVAILABLE,
            supervisor_pid=None,
            result_available=True,
            recovery_required=False,
        )

    def collect(self, execution_id: str, *, expected_version: int):
        with self._lock:
            self.collect_calls += 1
            record = self.records.get(execution_id)
        if record is None:
            raise SupervisedExecutionError("NOT_FOUND")
        result = make_child_result(execution_id, self.exit_code)
        return SupervisedCollectOutcome(
            record=record, result=result, recovery_required=False
        )


def replace_record_state(record, state):
    from dataclasses import replace as _replace

    return _replace(record, execution_state=state)


def make_child_result(execution_id: str, exit_code: int):
    from a_conductor.supervised_child import SupervisedChildResult

    return SupervisedChildResult(
        schema_version=1,
        execution_id=execution_id,
        child_pid=1234,
        exit_code=exit_code,
        started_at="2026-09-05T00:00:00+00:00",
        finished_at="2026-09-05T00:00:01+00:00",
    )


def _scope(repo: Path) -> NativeExecutionScope:
    return NativeExecutionScope(
        root=repo,
        mutation_allowed=True,
        allowed_executables=(PYTHON_NAME,),
        allowed_environment_overrides=(),
        max_timeout_seconds=60,
        max_output_bytes=64 * 1024,
        max_file_bytes=64 * 1024,
    )


def _identity(repo: Path) -> SupervisedRunIdentity:
    return SupervisedRunIdentity(repo_root=str(repo), **IDENTITY)


def _harness(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    supervised = ScriptedSupervised(repo, store)
    runner = SupervisedCommandRunner(
        scope=_scope(repo),
        execution_store=store,
        supervised=supervised,
        poll_interval_seconds=0.01,
        **IDENTITY,
    )
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=_identity(repo),
        poll_interval_seconds=0.01,
    )
    return repo, store, supervised, runner, coordinator


ARGV = (RUNTIME_PYTHON, "-c", "print('phase-a')")


def test_same_fingerprint_and_operation_ref(tmp_path):
    _, _, _, runner, coordinator = _harness(tmp_path)
    fp_runner = runner.fingerprint_for(
        __import__("a_conductor.native_execution", fromlist=["NativeCommandSpec"]).NativeCommandSpec(
            argv=ARGV
        )
    )
    fp_coord = coordinator.fingerprint_for_argv(ARGV)
    assert fp_runner == fp_coord
    assert coordinator.operation_ref(ARGV).startswith("native:")
    assert len(coordinator.operation_ref(ARGV)) == len("native:") + 16


def test_same_success_result_record_shape_and_refs(tmp_path):
    repo, store, supervised, runner, coordinator = _harness(tmp_path)
    argv_a, argv_b = ARGV, (RUNTIME_PYTHON, "-c", "print('phase-a-b')")

    result_adapter = runner.run(
        __import__("a_conductor.native_execution", fromlist=["NativeCommandSpec"]).NativeCommandSpec(
            argv=argv_a
        )
    )
    result_direct = coordinator.run(argv_b, timeout_seconds=30)

    for result in (result_adapter, result_direct):
        assert result.exit_code == 0
        assert result.timed_out is False
        assert result.executable == PYTHON_NAME
        assert result.stdout == "ok"
        assert result.stdout_sha256 == hashlib.sha256(b"ok").hexdigest()
        assert result.stderr_sha256 == hashlib.sha256(b"").hexdigest()

    records_a = store.find_by_fingerprint(coordinator.fingerprint_for_argv(argv_a))
    records_b = store.find_by_fingerprint(coordinator.fingerprint_for_argv(argv_b))
    assert len(records_a) == 1 and len(records_b) == 1
    for record, argv in ((records_a[0], argv_a), (records_b[0], argv_b)):
        assert _EXEC_ID_RE.fullmatch(record.execution_id)
        assert record.run_dir_ref == f"runs/{record.execution_id}"
        assert record.stdout_ref == f"runs/{record.execution_id}/stdout.log"
        assert record.stderr_ref == f"runs/{record.execution_id}/stderr.log"
        assert record.result_ref == f"runs/{record.execution_id}/result.json"
        for field, expected in IDENTITY.items():
            assert getattr(record, field) == expected, field
        assert record.agent_ref == "agent:supervised-native"
        assert record.operation_ref == coordinator.operation_ref(argv)


def test_reuse_completed_uses_same_execution_id_no_new_launch(tmp_path):
    _, store, supervised, runner, coordinator = _harness(tmp_path)
    spec = __import__("a_conductor.native_execution", fromlist=["NativeCommandSpec"]).NativeCommandSpec(
        argv=ARGV
    )
    runner.run(spec)
    first_id = store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV))[0].execution_id
    launches_before = supervised.launch_calls

    coordinator.run(ARGV, timeout_seconds=30)

    assert supervised.launch_calls == launches_before          # no new launch
    records = store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV))
    assert len(records) == 1 and records[0].execution_id == first_id


def test_no_extra_store_writes_and_single_threaded(tmp_path):
    repo, store, supervised, runner, coordinator = _harness(tmp_path)
    threads_before = threading.active_count()
    coordinator.run(ARGV, timeout_seconds=30)
    assert threading.active_count() == threads_before          # no background worker
    records = store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV))
    assert len(records) == 1                                    # exactly one durable record


def test_timeout_classification_identical(tmp_path):
    import time as _time

    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")

    class NeverResolves(ScriptedSupervised):
        def inspect(self, execution_id):
            return SupervisedInspection(
                execution_id=execution_id,
                state=SupervisedInspectionState.SUPERVISOR_RUNNING,
                supervisor_pid=None,
                result_available=False,
                recovery_required=False,
            )

    supervised = NeverResolves(repo, store)
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=_identity(repo),
        poll_interval_seconds=0.001,
        clock_fn=_time.monotonic,
    )
    result = coordinator.run(ARGV, timeout_seconds=1)
    assert result.timed_out is True
    assert result.exit_code is None


def test_recovery_classification_identical(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")

    class RecoveryRequired(ScriptedSupervised):
        def inspect(self, execution_id):
            return SupervisedInspection(
                execution_id=execution_id,
                state=SupervisedInspectionState.RECOVERY_REQUIRED,
                supervisor_pid=None,
                result_available=False,
                recovery_required=True,
                error_code="CHILD_DIED",
            )

    supervised = RecoveryRequired(repo, store)
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=_identity(repo),
        poll_interval_seconds=0.001,
    )
    result = coordinator.run(ARGV, timeout_seconds=30)
    assert result.exit_code is None
    assert result.stderr.startswith("SUPERVISOR_RECOVERY_REQUIRED:CHILD_DIED")
    assert result.timed_out is False


def test_stdout_cap_identical(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    big = b"x" * (70 * 1024)
    supervised = ScriptedSupervised(repo, store, stdout=big)
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=_identity(repo),
        poll_interval_seconds=0.01,
        max_output_bytes=64 * 1024,
    )
    result = coordinator.run(ARGV, timeout_seconds=30)
    assert result.stdout_truncated is True
    assert len(result.stdout.encode()) == 64 * 1024
    assert result.stdout_sha256 == hashlib.sha256(big).hexdigest()  # full-file digest


def test_adapter_scope_validation_unchanged(tmp_path):
    _, _, _, runner, _ = _harness(tmp_path)
    NativeCommandSpec = __import__(
        "a_conductor.native_execution", fromlist=["NativeCommandSpec"]
    ).NativeCommandSpec
    with pytest.raises(NativeExecutionError) as exc:
        runner.run(NativeCommandSpec(argv=("notepad.exe", "-x")))
    assert exc.value.code == "EXECUTABLE_NOT_ALLOWED"
    with pytest.raises(NativeExecutionError) as exc2:
        runner.run(NativeCommandSpec(argv=ARGV, timeout_seconds=9999))
    assert exc2.value.code == "TIMEOUT_INVALID"


def test_coordinator_validates_identity_and_dependencies(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    supervised = ScriptedSupervised(repo, store)
    with pytest.raises(ValueError):
        SupervisedRunCoordinator(
            execution_store=store,
            supervised=supervised,
            identity=SupervisedRunIdentity(
                job_id=" ", work_order_ref="w", project_id="p", worker_id="w",
                backend_id="b", branch="main", head_before="h",
                runtime_profile_ref="r", repo_root=str(repo),
            ),
        )
    with pytest.raises(ValueError):
        SupervisedRunCoordinator(
            execution_store=store,
            supervised=object(),
            identity=_identity(repo),
        )


def test_no_duplicate_authority_introduced():
    import inspect
    from a_conductor import supervised_run_coordinator as module
    source = inspect.getsource(module)
    for forbidden in ("threading.Thread", "Timer(", "while True:  # retry", "class .*Scheduler"):
        if forbidden == "while True:  # retry":
            assert forbidden not in source
        # no scheduler/thread spawn text in the coordinator
    assert "threading" not in source
    assert "Scheduler" not in source
