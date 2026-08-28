from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import pytest

from a_conductor.control_center import ControlCenterSnapshot, WorkerScreenRow
from a_conductor.domain import WorkerState
from a_conductor.execution_record import (
    DurableExecutionRecord,
    ExecutionProcessState,
    TransportState,
    new_execution_record,
)
from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.native_execution import (
    NativeCommandResult,
    NativeCommandSpec,
    NativeExecutionError,
    NativeExecutionScope,
)
from a_conductor.native_operation_assembly import ControlCenterNativeAdapterResolver
from a_conductor.owned_process import WindowsOwnedProcessController
from a_conductor.supervised_command_runner import SupervisedCommandRunner
from a_conductor.supervised_execution import SupervisedExecutionService
from a_conductor.windows_io import LoopbackReadyzHttpProbe, StrictPowerShellInspectionRunner
from a_conductor.windows_observer import WindowsRuntimeObserver


RUNTIME_PYTHON = getattr(sys, "_base_executable", sys.executable)
PYTHON_NAME = Path(sys.executable).name

IDENTITY = {
    "job_id": "job-001",
    "work_order_ref": "docs/work-orders/WO-P1-047-supervised-command-runner.md",
    "project_id": "project-1",
    "worker_id": "a-worker-01",
    "backend_id": "supervised-native",
    "branch": "main",
    "head_before": "a" * 40,
    "runtime_profile_ref": "runtime:test",
}


class StubSupervised:
    """Strict stub: fails the test if the supervisor is reached unexpectedly."""

    def launch(self, plan):
        raise AssertionError("supervised.launch must not be called")

    def inspect(self, execution_id):
        raise AssertionError("supervised.inspect must not be called")

    def collect(self, execution_id, *, expected_version):
        raise AssertionError("supervised.collect must not be called")


class RecordingRunner:
    def __init__(self) -> None:
        self.specs = []

    def run(self, spec):
        self.specs.append(spec)
        return NativeCommandResult(
            executable=Path(spec.argv[0]).name,
            argument_count=len(tuple(spec.argv)),
            exit_code=0,
            timed_out=False,
            stdout="",
            stderr="",
            stdout_sha256=hashlib.sha256(b"").hexdigest(),
            stderr_sha256=hashlib.sha256(b"").hexdigest(),
            stdout_truncated=False,
            stderr_truncated=False,
        )


def build_scope(repo: Path, *, mutation_allowed: bool = True) -> NativeExecutionScope:
    return NativeExecutionScope(
        root=repo,
        mutation_allowed=mutation_allowed,
        allowed_executables=(PYTHON_NAME,),
        allowed_environment_overrides=(),
        max_timeout_seconds=60,
        max_output_bytes=64 * 1024,
        max_file_bytes=64 * 1024,
    )


def build_harness(tmp_path: Path, **identity_overrides):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    observer = WindowsRuntimeObserver(
        runner=StrictPowerShellInspectionRunner(),
        http_probe=LoopbackReadyzHttpProbe(),
    )
    controller = WindowsOwnedProcessController(observer=observer)
    supervised = SupervisedExecutionService(
        store=store,
        controller=controller,
        observer=observer,
        allowed_target_executables=(PYTHON_NAME,),
        python_executable=RUNTIME_PYTHON,
        startup_poll_attempts=100,
        startup_poll_delay_seconds=0.02,
    )
    identity = dict(IDENTITY)
    identity.update(identity_overrides)
    runner = SupervisedCommandRunner(
        scope=build_scope(repo),
        execution_store=store,
        supervised=supervised,
        poll_interval_seconds=0.02,
        **identity,
    )
    return repo, store, runner


def drain(store: SQLiteExecutionStore, execution_id: str, *, timeout: float = 15.0) -> None:
    """Bounded wait until a durable execution leaves RUNNING/STARTING (releases child handles)."""
    import time as _time

    deadline = _time.monotonic() + timeout
    while _time.monotonic() < deadline:
        if store.get(execution_id).execution_state not in (
            ExecutionProcessState.RUNNING,
            ExecutionProcessState.STARTING,
        ):
            return
        _time.sleep(0.05)


@pytest.mark.skipif(os.name != "nt", reason="Windows supervised integration")
def test_fast_command_collects_real_result_with_durable_evidence(tmp_path: Path) -> None:
    repo, store, runner = build_harness(tmp_path)

    result = runner.run(
        NativeCommandSpec(argv=(RUNTIME_PYTHON, "-c", "print('hello-supervised')"))
    )

    assert result.exit_code == 0
    assert result.timed_out is False
    assert "hello-supervised" in result.stdout
    assert result.stdout_sha256 == hashlib.sha256(result.stdout.encode("utf-8")).hexdigest()
    assert result.executable == PYTHON_NAME
    assert result.argument_count == 3

    records = store.find_by_fingerprint(runner.fingerprint_for(NativeCommandSpec(argv=(RUNTIME_PYTHON, "-c", "print('hello-supervised')"))))
    assert len(records) == 1
    record = records[0]
    assert record.execution_state is ExecutionProcessState.VERIFICATION_REQUIRED
    stdout_path = repo / record.stdout_ref
    assert stdout_path.is_file()
    assert b"hello-supervised" in stdout_path.read_bytes()


@pytest.mark.skipif(os.name != "nt", reason="Windows supervised integration")
def test_nonzero_exit_maps_to_failure_with_real_exit_code(tmp_path: Path) -> None:
    _, store, runner = build_harness(tmp_path)

    result = runner.run(
        NativeCommandSpec(argv=(RUNTIME_PYTHON, "-c", "import sys; sys.exit(7)"))
    )

    assert result.exit_code == 7
    assert result.timed_out is False
    records = store.find_by_fingerprint(runner.fingerprint_for(NativeCommandSpec(argv=(RUNTIME_PYTHON, "-c", "import sys; sys.exit(7)"))))
    assert records[0].execution_state is ExecutionProcessState.FAILED


@pytest.mark.skipif(os.name != "nt", reason="Windows supervised integration")
def test_timeout_leaves_durable_running_execution_then_retry_attaches(tmp_path: Path) -> None:
    release = tmp_path / "release-child"
    child_code = (
        "import time; from pathlib import Path; "
        f"p=Path({str(release)!r}); "
        "[time.sleep(0.05) for _ in iter(p.exists, True)]; "
        "print('attach-marker')"
    )
    # The child waits for an explicit test signal instead of a fixed sleep.
    # This keeps the timeout assertion deterministic even when hosted-runner
    # process startup/inspection latency exceeds a few seconds.
    argv = (RUNTIME_PYTHON, "-c", child_code)
    repo, store, runner = build_harness(tmp_path)

    first = runner.run(NativeCommandSpec(argv=argv, timeout_seconds=1))

    assert first.timed_out is True
    assert first.exit_code is None
    fingerprint = runner.fingerprint_for(NativeCommandSpec(argv=argv))
    running_records = store.find_by_fingerprint(fingerprint)
    assert len(running_records) == 1
    assert running_records[0].execution_state is ExecutionProcessState.RUNNING

    release.write_text("release", encoding="utf-8")
    second = runner.run(NativeCommandSpec(argv=argv, timeout_seconds=30))

    assert second.timed_out is False
    assert second.exit_code == 0
    assert "attach-marker" in second.stdout
    assert len(store.find_by_fingerprint(fingerprint)) == 1
    assert store.get(running_records[0].execution_id).execution_state is ExecutionProcessState.VERIFICATION_REQUIRED


def test_blocked_duplicate_returns_failure_without_launch(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    argv = (RUNTIME_PYTHON, "-c", "print('blocked')")
    spec = NativeCommandSpec(argv=argv)
    scope = build_scope(repo)
    runner = SupervisedCommandRunner(
        scope=scope,
        execution_store=store,
        supervised=StubSupervised(),
        **IDENTITY,
    )
    fingerprint = runner.fingerprint_for(spec)
    run_rel = "runs/conflicting"
    store.create(
        new_execution_record(
            execution_id="exec-conflict",
            job_id="job-OTHER",
            work_order_ref="docs/work-orders/WO-OTHER.md",
            project_id="project-1",
            worker_id="a-worker-02",
            backend_id="supervised-native",
            agent_ref="agent:test",
            repo_root=str(repo.resolve()),
            branch="main",
            head_before="a" * 40,
            operation_ref="native:conflicting",
            command_fingerprint=fingerprint,
            command_summary="conflicting live execution",
            runtime_profile_ref="runtime:test",
            run_dir_ref=run_rel,
            stdout_ref=f"{run_rel}/stdout.log",
            stderr_ref=f"{run_rel}/stderr.log",
            result_ref=f"{run_rel}/result.json",
            report_ref=None,
            transport_state=TransportState.CONNECTED,
            execution_state=ExecutionProcessState.RUNNING,
        )
    )

    result = runner.run(spec)

    assert result.exit_code is None
    assert result.timed_out is False
    assert result.stderr == "SUPERVISED_DUPLICATE_BLOCKED"
    assert store.get("exec-conflict").execution_state is ExecutionProcessState.RUNNING


def test_validation_gates_still_enforced_before_launch(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    runner = SupervisedCommandRunner(
        scope=NativeExecutionScope(
            root=repo,
            mutation_allowed=False,
            allowed_executables=(PYTHON_NAME,),
            allowed_environment_overrides=(),
            max_timeout_seconds=10,
        ),
        execution_store=store,
        supervised=StubSupervised(),
        **IDENTITY,
    )

    with pytest.raises(NativeExecutionError) as mutation_error:
        runner.run(
            NativeCommandSpec(argv=(PYTHON_NAME, "-m", "pytest"), mutation_intent=True)
        )
    assert mutation_error.value.code == "MUTATION_FORBIDDEN"

    with pytest.raises(NativeExecutionError) as allowlist_error:
        runner.run(NativeCommandSpec(argv=("notepad.exe", "readme.txt")))
    assert allowlist_error.value.code == "EXECUTABLE_NOT_ALLOWED"

    with pytest.raises(NativeExecutionError) as timeout_error:
        runner.run(NativeCommandSpec(argv=(PYTHON_NAME, "-c", "pass"), timeout_seconds=999))
    assert timeout_error.value.code == "TIMEOUT_INVALID"

    allowed_runner = SupervisedCommandRunner(
        scope=build_scope(repo),
        execution_store=store,
        supervised=StubSupervised(),
        **IDENTITY,
    )
    (repo / "nested").mkdir()
    with pytest.raises(NativeExecutionError) as cwd_error:
        allowed_runner.run(
            NativeCommandSpec(argv=(PYTHON_NAME, "-c", "pass"), cwd="nested")
        )
    assert cwd_error.value.code == "CWD_UNSUPPORTED"


def test_resolver_runner_factory_injects_into_adapters(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    recording = RecordingRunner()

    class SnapshotProvider:
        def snapshot(self) -> ControlCenterSnapshot:
            return ControlCenterSnapshot(
                projects=(),
                workers=(
                    WorkerScreenRow(
                        worker_id="a-worker-01",
                        display_name="A-Worker 1",
                        state=WorkerState.READY,
                        runtime_id="runtime-1",
                        assignment_id="assignment-1",
                        project_id="project-1",
                        project_display_name="Repo",
                        project_root_path=str(repo.resolve()),
                        mutation_allowed=True,
                    ),
                ),
                online=True,
            )

    resolver = ControlCenterNativeAdapterResolver(
        service=SnapshotProvider(),
        runner_factory=lambda scope: recording,
    )

    adapters = resolver.resolve("a-worker-01")

    result = adapters.git.status_short(timeout_seconds=5)

    assert result.exit_code == 0
    assert len(recording.specs) == 1
    assert Path(recording.specs[0].argv[0]).name.startswith("git")
