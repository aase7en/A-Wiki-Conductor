"""Transport-independent supervised subprocess orchestration.

This layer reuses the existing exact-owned-process controller to own one
A-Conductor supervisor helper process. The helper launches the validated target
with ``shell=False`` and persists bounded child PID/result metadata. This module
contains no automatic retry, reconnect, failover, scheduling, routing, or
Serena-specific behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PureWindowsPath
import sys
import time
from typing import Callable, Protocol, Sequence

from .execution_record import (
    DurableExecutionRecord,
    ExecutionProcessState,
    TransportState,
)
from .execution_store import ExecutionStoreError
from .owned_process import (
    OwnedProcessMutationResult,
    OwnedProcessMutationState,
    OwnedProcessSpec,
)
from .runtime_safety import ProcessOwnership, classify_process_ownership
from .supervised_child import SupervisedChildError, SupervisedChildResult, read_supervised_child_result
from .windows_observer import PidMetadataStatus


_FORBIDDEN_SHELL_EXECUTABLES = frozenset(
    {
        "cmd.exe",
        "powershell.exe",
        "pwsh.exe",
        "bash.exe",
        "sh.exe",
        "wsl.exe",
        "cmd",
        "powershell",
        "pwsh",
        "bash",
        "sh",
        "wsl",
    }
)


class SupervisedExecutionError(RuntimeError):
    def __init__(self, code: str, *, recovery_required: bool = False) -> None:
        self.code = code
        self.recovery_required = recovery_required
        super().__init__(code)


class SupervisedInspectionState(str, Enum):
    STARTING = "STARTING"
    SUPERVISOR_RUNNING = "SUPERVISOR_RUNNING"
    RESULT_AVAILABLE = "RESULT_AVAILABLE"
    SUPERVISOR_EXITED_RESULT_MISSING = "SUPERVISOR_EXITED_RESULT_MISSING"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


@dataclass(frozen=True, slots=True)
class SupervisedLaunchPlan:
    record: DurableExecutionRecord
    runtime_root: Path | str
    target_argv: tuple[str, ...]
    target_executable_name: str
    environment_overrides: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.record, DurableExecutionRecord):
            raise ValueError("record must be a DurableExecutionRecord")
        root = Path(self.runtime_root).expanduser().resolve(strict=False)
        if not root.is_dir():
            raise ValueError("runtime_root must be an existing directory")
        object.__setattr__(self, "runtime_root", root)
        if not isinstance(self.target_argv, tuple) or not self.target_argv:
            raise ValueError("target_argv must be a non-empty tuple")
        for index, item in enumerate(self.target_argv):
            if (
                not isinstance(item, str)
                or not item
                or "\x00" in item
                or "\r" in item
                or "\n" in item
            ):
                raise ValueError(f"target_argv[{index}] is invalid")
        if (
            not isinstance(self.target_executable_name, str)
            or not self.target_executable_name.strip()
            or "\x00" in self.target_executable_name
        ):
            raise ValueError("target_executable_name is invalid")
        expected = PureWindowsPath(self.target_argv[0]).name
        if expected.casefold() != self.target_executable_name.strip().casefold():
            raise ValueError("target executable does not match target_argv[0]")
        object.__setattr__(self, "target_executable_name", self.target_executable_name.strip())
        if not isinstance(self.environment_overrides, tuple):
            raise ValueError("environment_overrides must be a tuple")
        for item in self.environment_overrides:
            if not isinstance(item, tuple) or len(item) != 2:
                raise ValueError("environment override must be a key/value tuple")
            key, value = item
            if (
                not isinstance(key, str)
                or not key
                or "\x00" in key
                or not isinstance(value, str)
                or not value
                or "\x00" in value
            ):
                raise ValueError("environment override is invalid")


@dataclass(frozen=True, slots=True)
class SupervisedLaunchOutcome:
    record: DurableExecutionRecord
    supervisor_pid: int | None
    child_pid: int | None
    recovery_required: bool
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class SupervisedInspection:
    execution_id: str
    state: SupervisedInspectionState
    supervisor_pid: int | None
    result_available: bool
    recovery_required: bool
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class SupervisedCollectOutcome:
    record: DurableExecutionRecord
    result: SupervisedChildResult | None
    recovery_required: bool
    error_code: str | None = None


class DurableExecutionStore(Protocol):
    def create(self, record: DurableExecutionRecord) -> DurableExecutionRecord: ...
    def get(self, execution_id: str) -> DurableExecutionRecord: ...
    def set_transport_state(self, execution_id: str, state: TransportState, *, expected_version: int, evidence_ref: str | None = None) -> DurableExecutionRecord: ...
    def set_execution_state(self, execution_id: str, state: ExecutionProcessState, *, expected_version: int, evidence_ref: str | None = None) -> DurableExecutionRecord: ...
    def set_process_metadata(self, execution_id: str, *, pid: int, started_at: str | None, expected_version: int, evidence_ref: str | None = None) -> DurableExecutionRecord: ...
    def set_result_metadata(self, execution_id: str, *, exit_code: int, finished_at: str, expected_version: int, evidence_ref: str | None = None) -> DurableExecutionRecord: ...


class OwnedProcessController(Protocol):
    def start(self, spec: OwnedProcessSpec) -> OwnedProcessMutationResult: ...


class SupervisedProcessObserver(Protocol):
    def read_pid_metadata(self, pid_path: Path): ...
    def observe_process(self, *, pid: int, expected_executable_name: str, expected_profile_marker: str): ...


def _require_positive_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{field_name} must be >= 1")
    return value


def _resolve_ref(root: Path, ref: str | None, field_name: str) -> Path:
    if not isinstance(ref, str) or not ref.strip() or "\x00" in ref:
        raise SupervisedExecutionError(f"{field_name.upper()}_REQUIRED")
    raw = Path(ref)
    if raw.is_absolute():
        raise SupervisedExecutionError("RUNTIME_REF_INVALID")
    candidate = (root / raw).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise SupervisedExecutionError("RUNTIME_REF_OUTSIDE_ROOT") from exc
    return candidate


def _read_pid_file(path: Path) -> int | None:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise SupervisedExecutionError("CHILD_PID_READ_FAILED", recovery_required=True) from exc
    try:
        pid = int(raw)
    except ValueError as exc:
        raise SupervisedExecutionError("CHILD_PID_INVALID", recovery_required=True) from exc
    if pid < 1:
        raise SupervisedExecutionError("CHILD_PID_INVALID", recovery_required=True)
    return pid


class SupervisedExecutionService:
    def __init__(
        self,
        *,
        store: DurableExecutionStore,
        controller: OwnedProcessController,
        observer: SupervisedProcessObserver,
        allowed_target_executables: Sequence[str],
        python_executable: str = sys.executable,
        startup_poll_attempts: int = 3,
        startup_poll_delay_seconds: float = 0.02,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        if isinstance(allowed_target_executables, (str, bytes)):
            raise ValueError("allowed_target_executables must be a sequence")
        allowed: set[str] = set()
        for value in allowed_target_executables:
            if not isinstance(value, str) or not value.strip() or "\x00" in value:
                raise ValueError("allowed target executable is invalid")
            allowed.add(PureWindowsPath(value.strip()).name.casefold())
        if not allowed:
            raise ValueError("allowed_target_executables must not be empty")
        if not isinstance(python_executable, str) or not python_executable.strip() or "\x00" in python_executable:
            raise ValueError("python_executable is invalid")
        _require_positive_int(startup_poll_attempts, "startup_poll_attempts")
        if (
            not isinstance(startup_poll_delay_seconds, (int, float))
            or isinstance(startup_poll_delay_seconds, bool)
            or startup_poll_delay_seconds < 0
        ):
            raise ValueError("startup_poll_delay_seconds must be >= 0")
        self._store = store
        self._controller = controller
        self._observer = observer
        self._allowed_target_executables = frozenset(allowed)
        self._python_executable = python_executable.strip()
        self._python_name = PureWindowsPath(self._python_executable).name
        self._helper_path = Path(__file__).with_name("supervised_child.py").resolve()
        self._startup_poll_attempts = startup_poll_attempts
        self._startup_poll_delay_seconds = float(startup_poll_delay_seconds)
        self._sleep_fn = sleep_fn

    def _validate_plan(self, plan: SupervisedLaunchPlan) -> tuple[Path, Path, Path, Path, Path, Path]:
        if not isinstance(plan, SupervisedLaunchPlan):
            raise ValueError("plan must be a SupervisedLaunchPlan")
        record = plan.record
        if record.version != 1 or record.execution_state is not ExecutionProcessState.QUEUED:
            raise SupervisedExecutionError("EXECUTION_RECORD_NOT_QUEUED")
        if record.transport_state is not TransportState.CONNECTED:
            raise SupervisedExecutionError("TRANSPORT_NOT_CONNECTED")
        repo_root = Path(record.repo_root).expanduser().resolve(strict=False)
        runtime_root = Path(plan.runtime_root).resolve(strict=False)
        if repo_root != runtime_root:
            raise SupervisedExecutionError("RUNTIME_ROOT_IDENTITY_MISMATCH")
        if not repo_root.is_dir():
            raise SupervisedExecutionError("REPO_ROOT_NOT_FOUND")
        target_name = PureWindowsPath(plan.target_executable_name).name.casefold()
        if target_name in _FORBIDDEN_SHELL_EXECUTABLES:
            raise SupervisedExecutionError("TARGET_SHELL_FORBIDDEN")
        if target_name not in self._allowed_target_executables:
            raise SupervisedExecutionError("TARGET_EXECUTABLE_NOT_ALLOWED")
        actual_name = PureWindowsPath(plan.target_argv[0]).name.casefold()
        if actual_name != target_name:
            raise SupervisedExecutionError("TARGET_EXECUTABLE_MISMATCH")

        run_dir = _resolve_ref(runtime_root, record.run_dir_ref, "run_dir_ref")
        stdout_path = _resolve_ref(runtime_root, record.stdout_ref, "stdout_ref")
        stderr_path = _resolve_ref(runtime_root, record.stderr_ref, "stderr_ref")
        result_path = _resolve_ref(runtime_root, record.result_ref, "result_ref")
        for path in (stdout_path, stderr_path, result_path):
            try:
                path.relative_to(run_dir)
            except ValueError as exc:
                raise SupervisedExecutionError("RUNTIME_REF_OUTSIDE_RUN_DIR") from exc
        supervisor_pid_path = run_dir / "supervisor.pid"
        child_pid_path = run_dir / "child.pid"
        return run_dir, stdout_path, stderr_path, result_path, supervisor_pid_path, child_pid_path

    def _build_owned_spec(self, plan: SupervisedLaunchPlan) -> OwnedProcessSpec:
        run_dir, stdout_path, stderr_path, result_path, supervisor_pid_path, child_pid_path = self._validate_plan(plan)
        record = plan.record
        command = (
            self._python_executable,
            str(self._helper_path),
            "--execution-id",
            record.execution_id,
            "--pid-path",
            str(child_pid_path),
            "--result-path",
            str(result_path),
            "--cwd",
            str(Path(record.repo_root).resolve(strict=False)),
            "--",
            *plan.target_argv,
        )
        return OwnedProcessSpec(
            allowed_root=Path(plan.runtime_root),
            cwd=run_dir,
            pid_path=supervisor_pid_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            command=command,
            expected_executable_name=self._python_name,
            expected_profile_marker=record.execution_id,
            environment_overrides=plan.environment_overrides,
        )

    def _mark_recovery(
        self,
        record: DurableExecutionRecord,
        *,
        code: str,
        evidence_ref: str | None = None,
    ) -> DurableExecutionRecord:
        return self._store.set_execution_state(
            record.execution_id,
            ExecutionProcessState.RECOVERY_REQUIRED,
            expected_version=record.version,
            evidence_ref=evidence_ref or f"supervised:{code}",
        )

    def launch(self, plan: SupervisedLaunchPlan) -> SupervisedLaunchOutcome:
        spec = self._build_owned_spec(plan)
        created = self._store.create(plan.record)
        starting = self._store.set_execution_state(
            created.execution_id,
            ExecutionProcessState.STARTING,
            expected_version=created.version,
            evidence_ref="supervised:launch-intent",
        )
        try:
            mutation = self._controller.start(spec)
        except Exception:
            recovered = self._mark_recovery(starting, code="SUPERVISOR_START_EXCEPTION")
            return SupervisedLaunchOutcome(
                record=recovered,
                supervisor_pid=None,
                child_pid=None,
                recovery_required=True,
                error_code="SUPERVISOR_START_EXCEPTION",
            )

        if mutation.state is not OwnedProcessMutationState.STARTED:
            code = (
                "SUPERVISOR_ALREADY_RUNNING"
                if mutation.state is OwnedProcessMutationState.ALREADY_RUNNING
                else mutation.reason_code
            )
            recovered = self._mark_recovery(starting, code=code)
            return SupervisedLaunchOutcome(
                record=recovered,
                supervisor_pid=mutation.pid,
                child_pid=None,
                recovery_required=True,
                error_code=code,
            )
        if mutation.pid is None or mutation.pid < 1:
            recovered = self._mark_recovery(starting, code="SUPERVISOR_PID_MISSING")
            return SupervisedLaunchOutcome(
                record=recovered,
                supervisor_pid=mutation.pid,
                child_pid=None,
                recovery_required=True,
                error_code="SUPERVISOR_PID_MISSING",
            )

        child_pid: int | None = None
        try:
            for attempt in range(self._startup_poll_attempts):
                child_pid = _read_pid_file(spec.pid_path.parent / "child.pid")
                if child_pid is not None:
                    break
                if attempt + 1 < self._startup_poll_attempts and self._startup_poll_delay_seconds:
                    self._sleep_fn(self._startup_poll_delay_seconds)
        except SupervisedExecutionError as exc:
            recovered = self._mark_recovery(starting, code=exc.code)
            return SupervisedLaunchOutcome(
                record=recovered,
                supervisor_pid=mutation.pid,
                child_pid=None,
                recovery_required=True,
                error_code=exc.code,
            )

        if child_pid is None:
            return SupervisedLaunchOutcome(
                record=starting,
                supervisor_pid=mutation.pid,
                child_pid=None,
                recovery_required=False,
                error_code=None,
            )

        with_pid = self._store.set_process_metadata(
            starting.execution_id,
            pid=child_pid,
            started_at=None,
            expected_version=starting.version,
            evidence_ref="supervised:child-pid",
        )
        running = self._store.set_execution_state(
            with_pid.execution_id,
            ExecutionProcessState.RUNNING,
            expected_version=with_pid.version,
            evidence_ref="supervised:running",
        )
        return SupervisedLaunchOutcome(
            record=running,
            supervisor_pid=mutation.pid,
            child_pid=child_pid,
            recovery_required=False,
            error_code=None,
        )

    def _paths_for_record(self, record: DurableExecutionRecord) -> tuple[Path, Path, Path]:
        root = Path(record.repo_root).expanduser().resolve(strict=False)
        run_dir = _resolve_ref(root, record.run_dir_ref, "run_dir_ref")
        result_path = _resolve_ref(root, record.result_ref, "result_ref")
        return run_dir, run_dir / "supervisor.pid", result_path

    def inspect(self, execution_id: str) -> SupervisedInspection:
        record = self._store.get(execution_id)
        _, supervisor_pid_path, result_path = self._paths_for_record(record)
        if result_path.exists():
            return SupervisedInspection(
                execution_id=execution_id,
                state=SupervisedInspectionState.RESULT_AVAILABLE,
                supervisor_pid=None,
                result_available=True,
                recovery_required=False,
            )

        def result_appeared() -> bool:
            # The result file is authoritative: a durable result written while
            # a pid observation was in flight wins over any stale-pid conclusion.
            return result_path.exists()

        metadata = self._observer.read_pid_metadata(supervisor_pid_path)
        if metadata.status is PidMetadataStatus.ABSENT:
            if record.execution_state is ExecutionProcessState.STARTING:
                return SupervisedInspection(
                    execution_id=execution_id,
                    state=SupervisedInspectionState.STARTING,
                    supervisor_pid=None,
                    result_available=False,
                    recovery_required=False,
                )
            if result_appeared():
                return SupervisedInspection(
                    execution_id=execution_id,
                    state=SupervisedInspectionState.RESULT_AVAILABLE,
                    supervisor_pid=None,
                    result_available=True,
                    recovery_required=False,
                )
            return SupervisedInspection(
                execution_id=execution_id,
                state=SupervisedInspectionState.SUPERVISOR_EXITED_RESULT_MISSING,
                supervisor_pid=None,
                result_available=False,
                recovery_required=True,
                error_code="SUPERVISOR_PID_ABSENT",
            )
        if metadata.status is not PidMetadataStatus.VALID or metadata.pid is None:
            if result_appeared():
                return SupervisedInspection(
                    execution_id=execution_id,
                    state=SupervisedInspectionState.RESULT_AVAILABLE,
                    supervisor_pid=None,
                    result_available=True,
                    recovery_required=False,
                )
            return SupervisedInspection(
                execution_id=execution_id,
                state=SupervisedInspectionState.RECOVERY_REQUIRED,
                supervisor_pid=metadata.pid,
                result_available=False,
                recovery_required=True,
                error_code="SUPERVISOR_PID_METADATA_INVALID",
            )
        observation = self._observer.observe_process(
            pid=metadata.pid,
            expected_executable_name=self._python_name,
            expected_profile_marker=record.execution_id,
        )
        ownership = classify_process_ownership(observation)
        if ownership is ProcessOwnership.OWNED:
            return SupervisedInspection(
                execution_id=execution_id,
                state=SupervisedInspectionState.SUPERVISOR_RUNNING,
                supervisor_pid=metadata.pid,
                result_available=False,
                recovery_required=False,
            )
        if result_appeared():
            return SupervisedInspection(
                execution_id=execution_id,
                state=SupervisedInspectionState.RESULT_AVAILABLE,
                supervisor_pid=None,
                result_available=True,
                recovery_required=False,
            )
        if ownership is ProcessOwnership.STALE:
            return SupervisedInspection(
                execution_id=execution_id,
                state=SupervisedInspectionState.SUPERVISOR_EXITED_RESULT_MISSING,
                supervisor_pid=metadata.pid,
                result_available=False,
                recovery_required=True,
                error_code="SUPERVISOR_EXITED_RESULT_MISSING",
            )
        return SupervisedInspection(
            execution_id=execution_id,
            state=SupervisedInspectionState.RECOVERY_REQUIRED,
            supervisor_pid=metadata.pid,
            result_available=False,
            recovery_required=True,
            error_code=f"SUPERVISOR_OWNERSHIP_{ownership.value}",
        )

    def collect(self, execution_id: str, *, expected_version: int) -> SupervisedCollectOutcome:
        record = self._store.get(execution_id)
        if record.version != expected_version:
            raise ExecutionStoreError("EXECUTION_VERSION_CONFLICT")
        _, _, result_path = self._paths_for_record(record)
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
            recovered = self._mark_recovery(
                record,
                code=exc.code,
                evidence_ref=record.result_ref,
            )
            return SupervisedCollectOutcome(
                record=recovered,
                result=None,
                recovery_required=True,
                error_code=exc.code,
            )

        if record.pid is not None and record.pid != result.child_pid:
            recovered = self._mark_recovery(
                record,
                code="RESULT_PID_MISMATCH",
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
        target_state = (
            ExecutionProcessState.VERIFICATION_REQUIRED
            if result.exit_code == 0
            else ExecutionProcessState.FAILED
        )
        final = self._store.set_execution_state(
            execution_id,
            target_state,
            expected_version=with_result.version,
            evidence_ref=record.result_ref,
        )
        return SupervisedCollectOutcome(
            record=final,
            result=result,
            recovery_required=False,
            error_code=None,
        )
