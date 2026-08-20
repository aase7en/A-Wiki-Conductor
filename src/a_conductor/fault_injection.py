"""Deterministic fake executor for resilient-execution fault tests.

This is test support, not a production execution backend. It uses explicit
scenario transitions and temp-repository durable refs; no threads, timers,
network calls, or real worker/tunnel mutations are performed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol

from .execution_record import DurableExecutionRecord, ExecutionProcessState
from .execution_store import ExecutionStoreError
from .supervised_child import (
    SUPERVISED_RESULT_SCHEMA_VERSION,
    SupervisedChildError,
    SupervisedChildResult,
    read_supervised_child_result,
)
from .supervised_execution import (
    SupervisedCollectOutcome,
    SupervisedInspection,
    SupervisedInspectionState,
)


class FaultScenario(str, Enum):
    NORMAL_SUCCESS = "NORMAL_SUCCESS"
    DISCONNECT_BEFORE_LAUNCH = "DISCONNECT_BEFORE_LAUNCH"
    DISCONNECT_AFTER_LAUNCH = "DISCONNECT_AFTER_LAUNCH"
    DISCONNECT_MID_COMMAND = "DISCONNECT_MID_COMMAND"
    DISCONNECT_AFTER_COMPLETION = "DISCONNECT_AFTER_COMPLETION"
    DELAYED_SUCCESS = "DELAYED_SUCCESS"
    LARGE_STDOUT = "LARGE_STDOUT"
    NONZERO_EXIT = "NONZERO_EXIT"
    MALFORMED_RESULT = "MALFORMED_RESULT"
    UNKNOWN_PROCESS = "UNKNOWN_PROCESS"


@dataclass(frozen=True, slots=True)
class FakeLaunchObservation:
    record: DurableExecutionRecord
    started: bool
    transport_lost: bool
    process_running: bool
    result_available: bool
    never_started: bool
    process_state_unknown: bool


@dataclass(slots=True)
class _FakeInstance:
    scenario: FaultScenario
    started: bool = False
    running: bool = False
    completed: bool = False
    result_available: bool = False
    unknown_process: bool = False
    child_pid: int | None = None


class FaultExecutionStore(Protocol):
    def get(self, execution_id: str) -> DurableExecutionRecord: ...

    def set_execution_state(
        self,
        execution_id: str,
        state: ExecutionProcessState,
        *,
        expected_version: int,
        evidence_ref: str | None = None,
    ) -> DurableExecutionRecord: ...

    def set_process_metadata(
        self,
        execution_id: str,
        *,
        pid: int,
        started_at: str | None,
        expected_version: int,
        evidence_ref: str | None = None,
    ) -> DurableExecutionRecord: ...

    def set_result_metadata(
        self,
        execution_id: str,
        *,
        exit_code: int,
        finished_at: str,
        expected_version: int,
        evidence_ref: str | None = None,
    ) -> DurableExecutionRecord: ...


_STARTED_AT = "2026-08-20T00:00:00Z"
_FINISHED_AT = "2026-08-20T00:01:00Z"


def _under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


class DeterministicFaultExecutor:
    """Scenario-driven fake implementing the supervised inspect/collect shape."""

    def __init__(
        self,
        *,
        store: FaultExecutionStore,
        scenario: FaultScenario,
        large_stdout_bytes: int = 256 * 1024,
    ) -> None:
        if not isinstance(scenario, FaultScenario):
            raise ValueError("scenario must be a FaultScenario")
        if (
            not isinstance(large_stdout_bytes, int)
            or isinstance(large_stdout_bytes, bool)
            or large_stdout_bytes < 1
        ):
            raise ValueError("large_stdout_bytes must be >= 1")
        self._store = store
        self._scenario = scenario
        self._large_stdout_bytes = large_stdout_bytes
        self._instances: dict[str, _FakeInstance] = {}
        self.actual_start_count = 0
        self.collect_count = 0

    @staticmethod
    def _paths(record: DurableExecutionRecord) -> tuple[Path, Path, Path, Path]:
        if (
            record.run_dir_ref is None
            or record.stdout_ref is None
            or record.stderr_ref is None
            or record.result_ref is None
        ):
            raise RuntimeError("FAKE_RUNTIME_REFS_REQUIRED")
        root = Path(record.repo_root).expanduser().resolve(strict=False)
        if not root.is_dir():
            raise RuntimeError("FAKE_REPO_NOT_FOUND")
        run_dir = (root / record.run_dir_ref).resolve(strict=False)
        stdout = (root / record.stdout_ref).resolve(strict=False)
        stderr = (root / record.stderr_ref).resolve(strict=False)
        result = (root / record.result_ref).resolve(strict=False)
        if not _under(run_dir, root) or any(
            not _under(path, run_dir) for path in (stdout, stderr, result)
        ):
            raise RuntimeError("FAKE_RUNTIME_REF_OUTSIDE_RUN_DIR")
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir, stdout, stderr, result

    @staticmethod
    def _write_result(
        result_path: Path,
        *,
        execution_id: str,
        child_pid: int,
        exit_code: int,
    ) -> None:
        result = SupervisedChildResult(
            schema_version=SUPERVISED_RESULT_SCHEMA_VERSION,
            execution_id=execution_id,
            child_pid=child_pid,
            exit_code=exit_code,
            started_at=_STARTED_AT,
            finished_at=_FINISHED_AT,
        )
        payload = json.dumps(
            result.as_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        result_path.write_bytes(payload)

    def _complete(self, execution_id: str, instance: _FakeInstance) -> None:
        record = self._store.get(execution_id)
        _, stdout, stderr, result = self._paths(record)
        stderr.write_bytes(b"")
        if instance.scenario is FaultScenario.DISCONNECT_MID_COMMAND:
            with stdout.open("ab") as handle:
                handle.write(b"completed-output\n")
        elif instance.scenario is FaultScenario.LARGE_STDOUT:
            stdout.write_bytes(b"X" * self._large_stdout_bytes)
        elif not stdout.exists():
            stdout.write_bytes(b"fake-output\n")

        assert instance.child_pid is not None
        if instance.scenario is FaultScenario.MALFORMED_RESULT:
            result.write_bytes(b'{"malformed":')
        else:
            exit_code = 9 if instance.scenario is FaultScenario.NONZERO_EXIT else 0
            self._write_result(
                result,
                execution_id=execution_id,
                child_pid=instance.child_pid,
                exit_code=exit_code,
            )
        instance.running = False
        instance.completed = True
        instance.result_available = True

    def launch(self, execution_id: str) -> FakeLaunchObservation:
        if not isinstance(execution_id, str) or not execution_id.strip():
            raise ValueError("execution_id must not be blank")
        existing = self._instances.get(execution_id)
        if existing is not None and existing.started:
            raise RuntimeError("FAKE_EXECUTION_ALREADY_STARTED")
        record = self._store.get(execution_id)
        if record.execution_state is not ExecutionProcessState.QUEUED:
            raise RuntimeError("FAKE_EXECUTION_NOT_QUEUED")

        instance = existing or _FakeInstance(self._scenario)
        self._instances[execution_id] = instance
        if self._scenario is FaultScenario.DISCONNECT_BEFORE_LAUNCH:
            return FakeLaunchObservation(
                record=record,
                started=False,
                transport_lost=True,
                process_running=False,
                result_available=False,
                never_started=True,
                process_state_unknown=False,
            )

        instance.started = True
        instance.running = True
        instance.child_pid = 41000 + self.actual_start_count + 1
        self.actual_start_count += 1
        running = self._store.set_execution_state(
            execution_id,
            ExecutionProcessState.RUNNING,
            expected_version=record.version,
            evidence_ref="fault:started",
        )
        running = self._store.set_process_metadata(
            execution_id,
            pid=instance.child_pid,
            started_at=_STARTED_AT,
            expected_version=running.version,
            evidence_ref="fault:pid",
        )
        _, stdout, stderr, _ = self._paths(running)
        stderr.write_bytes(b"")

        if self._scenario is FaultScenario.DISCONNECT_MID_COMMAND:
            stdout.write_bytes(b"partial-output\n")
        elif self._scenario is not FaultScenario.LARGE_STDOUT:
            stdout.write_bytes(b"fake-output\n")

        if self._scenario is FaultScenario.UNKNOWN_PROCESS:
            instance.unknown_process = True
        immediate = self._scenario in {
            FaultScenario.NORMAL_SUCCESS,
            FaultScenario.DISCONNECT_AFTER_COMPLETION,
            FaultScenario.LARGE_STDOUT,
            FaultScenario.NONZERO_EXIT,
            FaultScenario.MALFORMED_RESULT,
        }
        if immediate:
            self._complete(execution_id, instance)

        transport_lost = self._scenario in {
            FaultScenario.DISCONNECT_AFTER_LAUNCH,
            FaultScenario.DISCONNECT_MID_COMMAND,
            FaultScenario.DISCONNECT_AFTER_COMPLETION,
            FaultScenario.UNKNOWN_PROCESS,
        }
        return FakeLaunchObservation(
            record=self._store.get(execution_id),
            started=True,
            transport_lost=transport_lost,
            process_running=instance.running,
            result_available=instance.result_available,
            never_started=False,
            process_state_unknown=instance.unknown_process,
        )

    def advance(self, execution_id: str) -> None:
        instance = self._instances.get(execution_id)
        if instance is None or not instance.started:
            raise RuntimeError("FAKE_EXECUTION_NOT_STARTED")
        if instance.completed:
            return
        if instance.unknown_process:
            raise RuntimeError("FAKE_PROCESS_STATE_UNKNOWN")
        if instance.scenario not in {
            FaultScenario.DISCONNECT_AFTER_LAUNCH,
            FaultScenario.DISCONNECT_MID_COMMAND,
            FaultScenario.DELAYED_SUCCESS,
        }:
            raise RuntimeError("FAKE_SCENARIO_NOT_ADVANCEABLE")
        self._complete(execution_id, instance)

    def inspect(self, execution_id: str) -> SupervisedInspection:
        instance = self._instances.get(execution_id)
        if instance is None or not instance.started:
            return SupervisedInspection(
                execution_id=execution_id,
                state=SupervisedInspectionState.STARTING,
                supervisor_pid=None,
                result_available=False,
                recovery_required=False,
            )
        if instance.unknown_process:
            return SupervisedInspection(
                execution_id=execution_id,
                state=SupervisedInspectionState.RECOVERY_REQUIRED,
                supervisor_pid=instance.child_pid,
                result_available=False,
                recovery_required=True,
                error_code="FAKE_PROCESS_STATE_UNKNOWN",
            )
        if instance.result_available:
            return SupervisedInspection(
                execution_id=execution_id,
                state=SupervisedInspectionState.RESULT_AVAILABLE,
                supervisor_pid=None,
                result_available=True,
                recovery_required=False,
            )
        if instance.running:
            return SupervisedInspection(
                execution_id=execution_id,
                state=SupervisedInspectionState.SUPERVISOR_RUNNING,
                supervisor_pid=instance.child_pid,
                result_available=False,
                recovery_required=False,
            )
        return SupervisedInspection(
            execution_id=execution_id,
            state=SupervisedInspectionState.SUPERVISOR_EXITED_RESULT_MISSING,
            supervisor_pid=instance.child_pid,
            result_available=False,
            recovery_required=True,
            error_code="FAKE_RESULT_MISSING",
        )

    def collect(self, execution_id: str, *, expected_version: int) -> SupervisedCollectOutcome:
        self.collect_count += 1
        record = self._store.get(execution_id)
        if record.version != expected_version:
            raise ExecutionStoreError("EXECUTION_VERSION_CONFLICT")
        _, _, _, result_path = self._paths(record)
        try:
            result = read_supervised_child_result(
                result_path,
                expected_execution_id=execution_id,
            )
        except SupervisedChildError as exc:
            if exc.code == "RESULT_NOT_AVAILABLE":
                return SupervisedCollectOutcome(
                    record=record,
                    result=None,
                    recovery_required=False,
                    error_code=exc.code,
                )
            recovered = self._store.set_execution_state(
                execution_id,
                ExecutionProcessState.RECOVERY_REQUIRED,
                expected_version=record.version,
                evidence_ref=record.result_ref,
            )
            return SupervisedCollectOutcome(
                record=recovered,
                result=None,
                recovery_required=True,
                error_code=exc.code,
            )

        if record.pid is not None and record.pid != result.child_pid:
            recovered = self._store.set_execution_state(
                execution_id,
                ExecutionProcessState.RECOVERY_REQUIRED,
                expected_version=record.version,
                evidence_ref=record.result_ref,
            )
            return SupervisedCollectOutcome(
                record=recovered,
                result=result,
                recovery_required=True,
                error_code="RESULT_PID_MISMATCH",
            )
        with_process = self._store.set_process_metadata(
            execution_id,
            pid=result.child_pid,
            started_at=result.started_at,
            expected_version=record.version,
            evidence_ref=record.result_ref,
        )
        with_result = self._store.set_result_metadata(
            execution_id,
            exit_code=result.exit_code,
            finished_at=result.finished_at,
            expected_version=with_process.version,
            evidence_ref=record.result_ref,
        )
        final = self._store.set_execution_state(
            execution_id,
            ExecutionProcessState.VERIFICATION_REQUIRED
            if result.exit_code == 0
            else ExecutionProcessState.FAILED,
            expected_version=with_result.version,
            evidence_ref=record.result_ref,
        )
        return SupervisedCollectOutcome(
            record=final,
            result=result,
            recovery_required=False,
            error_code=None,
        )
