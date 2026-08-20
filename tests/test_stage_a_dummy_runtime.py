from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from a_conductor.domain import WorkerState
from a_conductor.lifecycle import (
    LifecycleAction,
    LifecycleDecision,
    LifecycleStep,
    LifecycleContext,
    plan_lifecycle,
)
from a_conductor.lifecycle_executor import (
    LifecycleCheckpoint,
    LifecycleExecutionState,
    LifecycleExecutor,
    LifecycleStepResult,
)
from a_conductor.lifecycle_journal import SQLiteLifecycleJournal
from a_conductor.runtime_safety import (
    PortBindingState,
    ProcessOwnership,
    TunnelBindingState,
    WorktreeBindingState,
)


HELPER = Path(__file__).parent / "support" / "dummy_runtime.py"


class DummyOwnedBackend:
    """Test-only backend that owns exactly one child process through Popen."""

    def __init__(self, root: Path, marker: str) -> None:
        self.root = root
        self.marker = marker
        self.state_file = root / "dummy-state.json"
        self.profile_file = root / "dummy-profile.txt"
        self.process: subprocess.Popen[str] | None = None
        self.calls: list[LifecycleStep] = []

    def execute_step(self, step: LifecycleStep) -> LifecycleStepResult:
        self.calls.append(step)
        if step in {
            LifecycleStep.VERIFY_ASSIGNMENT,
            LifecycleStep.VERIFY_RESOURCES,
            LifecycleStep.PREFLIGHT,
            LifecycleStep.VERIFY_PROJECT_IDENTITY,
            LifecycleStep.EMIT_EVIDENCE,
            LifecycleStep.CLEAR_ASSIGNMENT,
        }:
            return LifecycleStepResult(True, f"EVID-{step.value}")

        if step is LifecycleStep.RENDER_PROFILE:
            self.root.mkdir(parents=True, exist_ok=True)
            self.profile_file.write_text(self.marker, encoding="utf-8")
            return LifecycleStepResult(True, "EVID-RENDER_PROFILE")

        if step is LifecycleStep.START_OWNED_PROCESS:
            if self.process is not None and self.process.poll() is None:
                return LifecycleStepResult(
                    False,
                    "EVID-DUPLICATE-SPAWN-BLOCKED",
                    "DUMMY_ALREADY_RUNNING",
                )
            self.state_file.unlink(missing_ok=True)
            self.process = subprocess.Popen(
                [
                    sys.executable,
                    str(HELPER),
                    "--state-file",
                    str(self.state_file),
                    "--marker",
                    self.marker,
                ],
                cwd=self.root,
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return LifecycleStepResult(
                True,
                f"EVID-SPAWN-PID-{self.process.pid}",
            )

        if step is LifecycleStep.WAIT_READY:
            state = self._wait_for_state()
            url = f"http://127.0.0.1:{state['port']}/readyz"
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                try:
                    with urlopen(url, timeout=0.25) as response:
                        if response.status == 200:
                            return LifecycleStepResult(True, "EVID-READY")
                except (URLError, OSError, TimeoutError):
                    pass
                time.sleep(0.05)
            return LifecycleStepResult(False, "EVID-NOT-READY", "DUMMY_NOT_READY")

        if step is LifecycleStep.TARGETED_STOP:
            if self.process is None or self.process.poll() is not None:
                return LifecycleStepResult(False, None, "DUMMY_NOT_RUNNING")
            self.process.terminate()
            return LifecycleStepResult(
                True,
                f"EVID-TERMINATE-PID-{self.process.pid}",
            )

        if step is LifecycleStep.WAIT_EXIT:
            if self.process is None:
                return LifecycleStepResult(False, None, "DUMMY_PROCESS_MISSING")
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                return LifecycleStepResult(
                    False,
                    None,
                    "DUMMY_EXIT_TIMEOUT",
                    recovery_required=True,
                )
            return LifecycleStepResult(True, "EVID-EXITED")

        if step is LifecycleStep.VERIFY_RELEASED:
            if self.process is not None and self.process.poll() is None:
                return LifecycleStepResult(
                    False,
                    None,
                    "DUMMY_STILL_RUNNING",
                    recovery_required=True,
                )
            return LifecycleStepResult(True, "EVID-RELEASED")

        raise AssertionError(f"unexpected Stage A step: {step}")

    def _wait_for_state(self) -> dict[str, object]:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if self.state_file.is_file():
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            if self.process is not None and self.process.poll() is not None:
                raise AssertionError("dummy runtime exited before publishing state")
            time.sleep(0.05)
        raise AssertionError("dummy runtime did not publish state")

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def child_pid(self) -> int | None:
        return self.process.pid if self.process is not None else None

    def cleanup_exact_child(self) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # The child object is the exact process created by this harness.
            self.process.kill()
            self.process.wait(timeout=5)


class FailingCheckpointSink:
    def __init__(
        self,
        journal: SQLiteLifecycleJournal,
        fail_on: LifecycleStep,
    ) -> None:
        self.journal = journal
        self.fail_on = fail_on

    def record(self, checkpoint: LifecycleCheckpoint) -> None:
        if checkpoint.step is self.fail_on:
            raise RuntimeError("injected Stage A checkpoint failure")
        self.journal.record(checkpoint)


def start_context(**overrides) -> LifecycleContext:
    values = {
        "action": LifecycleAction.START,
        "assignment_present": True,
        "project_exists": True,
        "process_ownership": ProcessOwnership.ABSENT,
        "port_binding": PortBindingState.FREE,
        "tunnel_required": False,
        "tunnel_binding": TunnelBindingState.FREE,
        "worktree_binding": WorktreeBindingState.AVAILABLE,
        "ready": False,
        "project_identity_ok": None,
        "worker_state": WorkerState.STOPPED,
        "active_task": False,
    }
    values.update(overrides)
    return LifecycleContext(**values)


def stop_context() -> LifecycleContext:
    return LifecycleContext(
        action=LifecycleAction.STOP,
        assignment_present=True,
        project_exists=True,
        process_ownership=ProcessOwnership.OWNED,
        port_binding=PortBindingState.OWNED,
        tunnel_required=False,
        tunnel_binding=TunnelBindingState.FREE,
        worktree_binding=WorktreeBindingState.OWNED,
        ready=True,
        project_identity_ok=True,
        worker_state=WorkerState.READY,
        active_task=False,
    )


def test_stage_a_start_noop_stop_with_real_self_owned_child(tmp_path: Path) -> None:
    backend = DummyOwnedBackend(tmp_path / "runtime", "stage-a-owned-marker")
    journal = SQLiteLifecycleJournal(tmp_path / "journal.sqlite")
    executor = LifecycleExecutor()

    try:
        start_plan = plan_lifecycle(start_context())
        assert start_plan.decision is LifecycleDecision.PROCEED
        start_result = executor.execute(
            start_plan,
            backend,
            journal,
            transaction_id="stage-a-start",
        )

        assert start_result.state is LifecycleExecutionState.COMPLETE
        assert backend.is_running()
        first_pid = backend.child_pid()
        assert first_pid is not None
        assert tuple(item.step for item in journal.load("stage-a-start")) == start_plan.steps

        noop_plan = plan_lifecycle(
            start_context(
                process_ownership=ProcessOwnership.OWNED,
                port_binding=PortBindingState.OWNED,
                ready=True,
                project_identity_ok=True,
                worker_state=WorkerState.READY,
            )
        )
        assert noop_plan.decision is LifecycleDecision.NOOP
        calls_before_noop = tuple(backend.calls)
        noop_result = executor.execute(
            noop_plan,
            backend,
            journal,
            transaction_id="stage-a-noop",
        )
        assert noop_result.state is LifecycleExecutionState.NOOP
        assert tuple(backend.calls) == calls_before_noop
        assert backend.child_pid() == first_pid

        stop_plan = plan_lifecycle(stop_context())
        assert stop_plan.decision is LifecycleDecision.PROCEED
        stop_result = executor.execute(
            stop_plan,
            backend,
            journal,
            transaction_id="stage-a-stop",
        )

        assert stop_result.state is LifecycleExecutionState.COMPLETE
        assert not backend.is_running()
        assert tuple(item.step for item in journal.load("stage-a-stop")) == stop_plan.steps
    finally:
        backend.cleanup_exact_child()


def test_stage_a_checkpoint_failure_after_spawn_enters_recovery_and_halts(
    tmp_path: Path,
) -> None:
    backend = DummyOwnedBackend(tmp_path / "runtime", "stage-a-checkpoint-failure")
    journal = SQLiteLifecycleJournal(tmp_path / "journal.sqlite")
    sink = FailingCheckpointSink(journal, LifecycleStep.START_OWNED_PROCESS)
    executor = LifecycleExecutor()

    try:
        lifecycle_plan = plan_lifecycle(start_context())
        result = executor.execute(
            lifecycle_plan,
            backend,
            sink,
            transaction_id="stage-a-checkpoint-failure",
        )

        assert result.state is LifecycleExecutionState.RECOVERY_REQUIRED
        assert result.reason_code == "CHECKPOINT_PERSISTENCE_FAILED"
        assert result.failed_step is LifecycleStep.START_OWNED_PROCESS
        assert backend.is_running()
        assert LifecycleStep.WAIT_READY not in backend.calls
        persisted = journal.load("stage-a-checkpoint-failure")
        assert tuple(item.step for item in persisted) == lifecycle_plan.steps[:4]
    finally:
        # Recovery cleanup is limited to the exact child Popen created by this test.
        backend.cleanup_exact_child()
