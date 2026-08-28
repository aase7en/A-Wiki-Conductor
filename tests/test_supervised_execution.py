from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from a_conductor.execution_record import (
    ExecutionProcessState,
    TransportState,
    new_execution_record,
)
from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.owned_process import (
    OwnedProcessMutationResult,
    OwnedProcessMutationState,
)
from a_conductor.runtime_safety import ProcessObservation
from a_conductor.supervised_execution import (
    SupervisedCollectOutcome,
    SupervisedExecutionError,
    SupervisedExecutionService,
    SupervisedInspectionState,
    SupervisedLaunchPlan,
)
from a_conductor.windows_observer import PidMetadataObservation, PidMetadataStatus


PYTHON_NAME = Path(sys.executable).name


def make_record(runtime_root: Path, execution_id: str = "exec-001"):
    run_rel = f"runs/{execution_id}"
    return new_execution_record(
        execution_id=execution_id,
        job_id="job-001",
        work_order_ref="docs/work-orders/WO-1.md",
        project_id="project-1",
        worker_id="a-worker-01",
        backend_id="local-supervised",
        agent_ref="agent:test",
        repo_root=str(runtime_root.resolve()),
        branch="main",
        head_before="a" * 40,
        operation_ref="op:supervised-test",
        command_fingerprint="b" * 64,
        command_summary="supervised python test",
        runtime_profile_ref="runtime:test",
        run_dir_ref=run_rel,
        stdout_ref=f"{run_rel}/stdout.log",
        stderr_ref=f"{run_rel}/stderr.log",
        result_ref=f"{run_rel}/result.json",
        report_ref=None,
        transport_state=TransportState.CONNECTED,
        execution_state=ExecutionProcessState.QUEUED,
    )


class FakeController:
    def __init__(
        self,
        result: OwnedProcessMutationResult | None = None,
        *,
        child_pid: int | None = 2222,
    ) -> None:
        self.result = result or OwnedProcessMutationResult(
            OwnedProcessMutationState.STARTED,
            "STARTED",
            1111,
        )
        self.child_pid = child_pid
        self.start_calls = []

    def start(self, spec):
        self.start_calls.append(spec)
        if self.result.state is OwnedProcessMutationState.STARTED:
            spec.pid_path.parent.mkdir(parents=True, exist_ok=True)
            spec.pid_path.write_text(f"{self.result.pid}\n", encoding="utf-8")
            if self.child_pid is not None:
                (spec.pid_path.parent / "child.pid").write_text(
                    f"{self.child_pid}\n",
                    encoding="utf-8",
                )
        return self.result


class FakeObserver:
    def __init__(self, *, owned: bool = True, process_exists: bool | None = True) -> None:
        self.owned = owned
        self.process_exists = process_exists
        self.observe_calls = []

    def read_pid_metadata(self, pid_path: Path) -> PidMetadataObservation:
        if not pid_path.exists():
            return PidMetadataObservation(PidMetadataStatus.ABSENT, None)
        try:
            pid = int(pid_path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return PidMetadataObservation(PidMetadataStatus.INVALID, None)
        return PidMetadataObservation(PidMetadataStatus.VALID, pid)

    def observe_process(self, *, pid: int, expected_executable_name: str, expected_profile_marker: str):
        self.observe_calls.append((pid, expected_executable_name, expected_profile_marker))
        return ProcessObservation(
            pid_metadata_present=True,
            pid=pid,
            process_exists=self.process_exists,
            executable_matches=self.owned if self.process_exists else None,
            profile_matches=self.owned if self.process_exists else None,
        )


def make_service(tmp_path: Path, controller: FakeController | None = None, observer: FakeObserver | None = None):
    store = SQLiteExecutionStore(tmp_path / "executions.sqlite")
    service = SupervisedExecutionService(
        store=store,
        controller=controller or FakeController(),
        observer=observer or FakeObserver(),
        allowed_target_executables=(PYTHON_NAME,),
        python_executable=sys.executable,
        startup_poll_attempts=2,
    )
    return service, store


def make_plan(tmp_path: Path, *, secret_arg: str = "SAFE_ARG") -> SupervisedLaunchPlan:
    return SupervisedLaunchPlan(
        record=make_record(tmp_path),
        runtime_root=tmp_path,
        target_argv=(sys.executable, "-c", secret_arg),
        target_executable_name=PYTHON_NAME,
    )


def write_result(tmp_path: Path, *, execution_id: str = "exec-001", child_pid: int = 2222, exit_code: int = 0):
    path = tmp_path / "runs" / execution_id / "result.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "execution_id": execution_id,
                "child_pid": child_pid,
                "exit_code": exit_code,
                "started_at": "2026-08-20T03:00:00Z",
                "finished_at": "2026-08-20T03:01:00Z",
            }
        ),
        encoding="utf-8",
    )
    return path


def test_launch_persists_record_uses_owned_supervisor_and_returns_without_collect(tmp_path: Path) -> None:
    controller = FakeController(child_pid=2222)
    service, store = make_service(tmp_path, controller=controller)
    secret_arg = "RAW_ARG_SHOULD_NOT_BE_IN_SQLITE"

    outcome = service.launch(make_plan(tmp_path, secret_arg=secret_arg))

    assert outcome.record.execution_state is ExecutionProcessState.RUNNING
    assert outcome.record.pid == 2222
    assert outcome.supervisor_pid == 1111
    assert outcome.child_pid == 2222
    assert len(controller.start_calls) == 1
    spec = controller.start_calls[0]
    assert spec.expected_profile_marker == "exec-001"
    assert "exec-001" in spec.command
    assert secret_arg in spec.command
    assert spec.stdout_path == (tmp_path / "runs/exec-001/stdout.log").resolve()
    assert spec.stderr_path == (tmp_path / "runs/exec-001/stderr.log").resolve()
    assert secret_arg.encode() not in (tmp_path / "executions.sqlite").read_bytes()
    assert store.get("exec-001") == outcome.record
    assert not (tmp_path / "runs/exec-001/result.json").exists()


def test_launch_rejects_shell_intermediary_before_controller(tmp_path: Path) -> None:
    controller = FakeController()
    store = SQLiteExecutionStore(tmp_path / "executions.sqlite")
    service = SupervisedExecutionService(
        store=store,
        controller=controller,
        observer=FakeObserver(),
        allowed_target_executables=("cmd.exe",),
        python_executable=sys.executable,
    )
    plan = SupervisedLaunchPlan(
        record=make_record(tmp_path),
        runtime_root=tmp_path,
        target_argv=("cmd.exe", "/c", "echo unsafe"),
        target_executable_name="cmd.exe",
    )
    with pytest.raises(SupervisedExecutionError) as exc_info:
        service.launch(plan)
    assert exc_info.value.code == "TARGET_SHELL_FORBIDDEN"
    assert controller.start_calls == []


def test_controller_recovery_result_never_blind_retries(tmp_path: Path) -> None:
    controller = FakeController(
        OwnedProcessMutationResult(
            OwnedProcessMutationState.RECOVERY_REQUIRED,
            "PID_METADATA_UNKNOWN",
            None,
        ),
        child_pid=None,
    )
    service, store = make_service(tmp_path, controller=controller)

    outcome = service.launch(make_plan(tmp_path))

    assert outcome.record.execution_state is ExecutionProcessState.RECOVERY_REQUIRED
    assert outcome.recovery_required is True
    assert len(controller.start_calls) == 1
    assert store.get("exec-001") == outcome.record


def test_inspect_running_supervisor_does_not_launch(tmp_path: Path) -> None:
    controller = FakeController(child_pid=None)
    observer = FakeObserver(owned=True, process_exists=True)
    service, _ = make_service(tmp_path, controller=controller, observer=observer)
    service.launch(make_plan(tmp_path))
    launch_call_count = len(controller.start_calls)

    inspection = service.inspect("exec-001")

    assert inspection.state is SupervisedInspectionState.SUPERVISOR_RUNNING
    assert len(controller.start_calls) == launch_call_count
    assert observer.observe_calls[-1][2] == "exec-001"


def test_inspect_prefers_durable_result_evidence(tmp_path: Path) -> None:
    controller = FakeController(child_pid=2222)
    service, _ = make_service(tmp_path, controller=controller, observer=FakeObserver(process_exists=False))
    service.launch(make_plan(tmp_path))
    write_result(tmp_path)

    inspection = service.inspect("exec-001")

    assert inspection.state is SupervisedInspectionState.RESULT_AVAILABLE


def test_inspect_stale_supervisor_without_result_requires_recovery(tmp_path: Path) -> None:
    controller = FakeController(child_pid=2222)
    observer = FakeObserver(owned=True, process_exists=False)
    service, _ = make_service(tmp_path, controller=controller, observer=observer)
    service.launch(make_plan(tmp_path))

    inspection = service.inspect("exec-001")

    assert inspection.state is SupervisedInspectionState.SUPERVISOR_EXITED_RESULT_MISSING
    assert inspection.recovery_required is True


def test_collect_zero_exit_updates_metadata_then_requires_verification(tmp_path: Path) -> None:
    service, store = make_service(tmp_path)
    launched = service.launch(make_plan(tmp_path))
    write_result(tmp_path, child_pid=2222, exit_code=0)

    outcome: SupervisedCollectOutcome = service.collect(
        "exec-001",
        expected_version=launched.record.version,
    )

    assert outcome.recovery_required is False
    assert outcome.error_code is None
    assert outcome.record.pid == 2222
    assert outcome.record.exit_code == 0
    assert outcome.record.started_at == "2026-08-20T03:00:00Z"
    assert outcome.record.finished_at == "2026-08-20T03:01:00Z"
    assert outcome.record.execution_state is ExecutionProcessState.VERIFICATION_REQUIRED
    assert store.get("exec-001") == outcome.record


def test_collect_nonzero_exit_marks_failed_without_rerun(tmp_path: Path) -> None:
    controller = FakeController()
    service, _ = make_service(tmp_path, controller=controller)
    launched = service.launch(make_plan(tmp_path))
    write_result(tmp_path, exit_code=7)
    launch_calls = len(controller.start_calls)

    outcome = service.collect("exec-001", expected_version=launched.record.version)

    assert outcome.record.execution_state is ExecutionProcessState.FAILED
    assert outcome.record.exit_code == 7
    assert len(controller.start_calls) == launch_calls


def test_collect_malformed_result_marks_recovery_required_and_never_reruns(tmp_path: Path) -> None:
    controller = FakeController()
    service, _ = make_service(tmp_path, controller=controller)
    launched = service.launch(make_plan(tmp_path))
    path = tmp_path / "runs/exec-001/result.json"
    path.write_text('{"execution_id":"exec-001","argv":["bad"]}', encoding="utf-8")
    launch_calls = len(controller.start_calls)

    outcome = service.collect("exec-001", expected_version=launched.record.version)

    assert outcome.recovery_required is True
    assert outcome.error_code == "RESULT_INVALID"
    assert outcome.record.execution_state is ExecutionProcessState.RECOVERY_REQUIRED
    assert len(controller.start_calls) == launch_calls


def test_collect_wrong_execution_id_marks_recovery_required(tmp_path: Path) -> None:
    service, _ = make_service(tmp_path)
    launched = service.launch(make_plan(tmp_path))
    write_result(tmp_path, execution_id="exec-other")
    wrong = tmp_path / "runs/exec-other/result.json"
    expected = tmp_path / "runs/exec-001/result.json"
    expected.write_bytes(wrong.read_bytes())

    outcome = service.collect("exec-001", expected_version=launched.record.version)

    assert outcome.recovery_required is True
    assert outcome.error_code == "RESULT_EXECUTION_MISMATCH"


def test_target_executable_must_be_allowlisted_and_match_argv(tmp_path: Path) -> None:
    controller = FakeController()
    service, _ = make_service(tmp_path, controller=controller)
    plan = SupervisedLaunchPlan(
        record=make_record(tmp_path),
        runtime_root=tmp_path,
        target_argv=("not-python.exe", "--version"),
        target_executable_name="not-python.exe",
    )
    with pytest.raises(SupervisedExecutionError) as exc_info:
        service.launch(plan)
    assert exc_info.value.code == "TARGET_EXECUTABLE_NOT_ALLOWED"
    assert controller.start_calls == []


def test_inspect_prefers_result_written_while_supervisor_was_exiting(tmp_path: Path) -> None:
    """A result file that appears concurrently with a stale supervisor observation wins.

    Real-world race (2026-08-20, supervised command runner wiring): the pid
    observation is slow; the helper writes result.json and exits while the
    observer is still running, so the entry-time result check missed it and a
    stale-PID conclusion was returned even though the result existed.
    """

    class LateResultObserver(FakeObserver):
        def observe_process(self, **kwargs):
            observation = super().observe_process(**kwargs)
            write_result(tmp_path)
            return observation

    service, _ = make_service(tmp_path, observer=LateResultObserver(process_exists=False))
    service.launch(make_plan(tmp_path))

    inspection = service.inspect("exec-001")

    assert inspection.state is SupervisedInspectionState.RESULT_AVAILABLE
    assert inspection.result_available is True
    assert inspection.recovery_required is False


def test_launch_forwards_environment_overrides_to_owned_process(tmp_path: Path) -> None:
    controller = FakeController(child_pid=2222)
    service, _ = make_service(tmp_path, controller=controller)
    overrides = (
        ("ANTHROPIC_BASE_URL", "https://provider.example/v1"),
        ("ANTHROPIC_AUTH_TOKEN", "secret-token-value"),
    )
    plan = SupervisedLaunchPlan(
        record=make_record(tmp_path),
        runtime_root=tmp_path,
        target_argv=(sys.executable, "-c", "pass"),
        target_executable_name=PYTHON_NAME,
        environment_overrides=overrides,
    )

    service.launch(plan)

    assert len(controller.start_calls) == 1
    assert controller.start_calls[0].environment_overrides == overrides
    assert b"secret-token-value" not in (tmp_path / "executions.sqlite").read_bytes()


def test_launch_plan_repr_masks_environment_override_values(tmp_path: Path) -> None:
    secret = "secret-token-value"
    plan = SupervisedLaunchPlan(
        record=make_record(tmp_path),
        runtime_root=tmp_path,
        target_argv=(sys.executable, "-c", "pass"),
        target_executable_name=PYTHON_NAME,
        environment_overrides=(("ANTHROPIC_AUTH_TOKEN", secret),),
    )

    assert secret not in repr(plan)
