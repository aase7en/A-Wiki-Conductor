"""Resilient wiring between native operation adapters and the AC-RES supervisor.

Implements the ``NativeCommandRunner`` protocol so native git/verification
commands execute through the supervised execution service (durable execution
record, duplicate-execution protection, bounded collect) instead of a bare
subprocess call. Transport-loss recovery, retry, and failover decisions stay
outside this module.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from pathlib import Path, PureWindowsPath
from typing import Callable, Protocol, Sequence

from .execution_deduplication import (
    DuplicateExecutionAssessment,
    DuplicateExecutionDecision,
    DuplicateExecutionGuard,
    ExecutionFingerprintSpec,
    compute_execution_fingerprint,
)
from .execution_record import (
    DurableExecutionRecord,
    ExecutionProcessState,
    TransportState,
    new_execution_record,
)
from .execution_store import ExecutionStoreError
from .native_execution import (
    NativeCommandResult,
    NativeCommandSpec,
    NativeExecutionError,
    NativeExecutionScope,
)
from .supervised_execution import (
    SupervisedCollectOutcome,
    SupervisedExecutionError,
    SupervisedInspection,
    SupervisedInspectionState,
    SupervisedLaunchOutcome,
    SupervisedLaunchPlan,
)


_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


class SupervisedLauncher(Protocol):
    def launch(self, plan: SupervisedLaunchPlan) -> SupervisedLaunchOutcome: ...
    def inspect(self, execution_id: str) -> SupervisedInspection: ...
    def collect(self, execution_id: str, *, expected_version: int) -> SupervisedCollectOutcome: ...


class SupervisedExecutionFingerprintStore(Protocol):
    def create(self, record: DurableExecutionRecord) -> DurableExecutionRecord: ...
    def get(self, execution_id: str) -> DurableExecutionRecord: ...
    def find_by_fingerprint(self, fingerprint: str) -> tuple[DurableExecutionRecord, ...]: ...


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ValueError(f"{field_name} must be a non-blank string")
    return value


class SupervisedCommandRunner:
    """Run authorized native commands under durable supervised execution."""

    def __init__(
        self,
        *,
        scope: NativeExecutionScope,
        execution_store: SupervisedExecutionFingerprintStore,
        supervised: SupervisedLauncher,
        job_id: str,
        work_order_ref: str,
        project_id: str,
        worker_id: str,
        backend_id: str,
        branch: str,
        head_before: str,
        runtime_profile_ref: str,
        poll_interval_seconds: float = 0.05,
        sleep_fn: Callable[[float], None] = time.sleep,
        clock_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(scope, NativeExecutionScope):
            raise ValueError("scope must be a NativeExecutionScope")
        for method_name in ("create", "get", "find_by_fingerprint"):
            if not callable(getattr(execution_store, method_name, None)):
                raise ValueError(f"execution_store must provide {method_name}")
        for method_name in ("launch", "inspect", "collect"):
            if not callable(getattr(supervised, method_name, None)):
                raise ValueError(f"supervised must provide {method_name}")
        _require_text(job_id, "job_id")
        _require_text(work_order_ref, "work_order_ref")
        _require_text(project_id, "project_id")
        _require_text(worker_id, "worker_id")
        _require_text(backend_id, "backend_id")
        _require_text(branch, "branch")
        _require_text(head_before, "head_before")
        _require_text(runtime_profile_ref, "runtime_profile_ref")
        if (
            not isinstance(poll_interval_seconds, (int, float))
            or isinstance(poll_interval_seconds, bool)
            or poll_interval_seconds <= 0
        ):
            raise ValueError("poll_interval_seconds must be > 0")
        if not callable(sleep_fn) or not callable(clock_fn):
            raise ValueError("sleep_fn and clock_fn must be callable")
        self._scope = scope
        self._store = execution_store
        self._supervised = supervised
        self._guard = DuplicateExecutionGuard(store=execution_store)
        self._repo_root = Path(scope.root).expanduser().resolve(strict=False)
        self._job_id = job_id
        self._work_order_ref = work_order_ref
        self._project_id = project_id
        self._worker_id = worker_id
        self._backend_id = backend_id
        self._branch = branch
        self._head_before = head_before
        self._runtime_profile_ref = runtime_profile_ref
        self._poll_interval_seconds = float(poll_interval_seconds)
        self._sleep_fn = sleep_fn
        self._clock_fn = clock_fn

    def _validated_argv(self, spec: NativeCommandSpec) -> tuple[str, ...]:
        if isinstance(spec.argv, (str, bytes)) or not isinstance(spec.argv, Sequence):
            raise NativeExecutionError("ARGV_INVALID")
        argv = tuple(spec.argv)
        if not argv:
            raise NativeExecutionError("ARGV_INVALID")
        for argument in argv:
            if not isinstance(argument, str) or not argument or "\x00" in argument:
                raise NativeExecutionError("ARGV_INVALID")
        if not isinstance(spec.mutation_intent, bool):
            raise NativeExecutionError("MUTATION_INTENT_INVALID")
        if spec.mutation_intent and not self._scope.mutation_allowed:
            raise NativeExecutionError("MUTATION_FORBIDDEN")
        executable = PureWindowsPath(argv[0]).name
        allowed = {PureWindowsPath(value).name.casefold() for value in self._scope.allowed_executables}
        if executable.casefold() not in allowed:
            raise NativeExecutionError("EXECUTABLE_NOT_ALLOWED")
        timeout = spec.timeout_seconds
        if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout < 1:
            raise NativeExecutionError("TIMEOUT_INVALID")
        if timeout > self._scope.max_timeout_seconds:
            raise NativeExecutionError("TIMEOUT_INVALID")
        return argv

    def _validated_environment_overrides(
        self, spec: NativeCommandSpec
    ) -> tuple[tuple[str, str], ...]:
        overrides = spec.environment_overrides
        if not isinstance(overrides, tuple):
            raise NativeExecutionError("ENV_OVERRIDE_INVALID")
        allowed = {key.casefold() for key in self._scope.allowed_environment_overrides}
        seen: set[str] = set()
        normalized: list[tuple[str, str]] = []
        for item in overrides:
            if not isinstance(item, tuple) or len(item) != 2:
                raise NativeExecutionError("ENV_OVERRIDE_INVALID")
            key, value = item
            if (
                not isinstance(key, str)
                or not key.strip()
                or "=" in key
                or "\x00" in key
                or not isinstance(value, str)
                or not value
                or "\x00" in value
            ):
                raise NativeExecutionError("ENV_OVERRIDE_INVALID")
            folded = key.casefold()
            if folded not in allowed:
                raise NativeExecutionError("ENV_OVERRIDE_NOT_ALLOWED")
            if folded in seen:
                raise NativeExecutionError("ENV_OVERRIDE_INVALID")
            seen.add(folded)
            normalized.append((key, value))
        return tuple(normalized)

    def _operation_ref(self, argv: tuple[str, ...]) -> str:
        digest = hashlib.sha256("\x00".join(argv).encode("utf-8")).hexdigest()[:16]
        return f"native:{digest}"

    def _fingerprint_spec(self, argv: tuple[str, ...]) -> ExecutionFingerprintSpec:
        return ExecutionFingerprintSpec(
            project_id=self._project_id,
            job_id=self._job_id,
            work_order_ref=self._work_order_ref,
            backend_id=self._backend_id,
            repo_root=str(self._repo_root),
            branch=self._branch,
            head_before=self._head_before,
            operation_ref=self._operation_ref(argv),
            runtime_profile_ref=self._runtime_profile_ref,
            target_argv=argv,
        )

    def fingerprint_for(self, spec: NativeCommandSpec) -> str:
        return compute_execution_fingerprint(self._fingerprint_spec(self._validated_argv(spec)))

    def _failure_result(
        self,
        argv: tuple[str, ...],
        *,
        error_code: str,
    ) -> NativeCommandResult:
        stderr = error_code.encode("utf-8")
        return NativeCommandResult(
            executable=PureWindowsPath(argv[0]).name,
            argument_count=len(argv),
            exit_code=None,
            timed_out=False,
            stdout="",
            stderr=error_code,
            stdout_sha256=_EMPTY_SHA256,
            stderr_sha256=hashlib.sha256(stderr).hexdigest(),
            stdout_truncated=False,
            stderr_truncated=False,
        )

    def _read_artifact(self, path: Path) -> tuple[str, str, bool]:
        try:
            raw = path.read_bytes()
        except FileNotFoundError:
            return "", _EMPTY_SHA256, False
        digest = hashlib.sha256(raw).hexdigest()
        cap = self._scope.max_output_bytes
        truncated = len(raw) > cap
        if truncated:
            raw = raw[-cap:]
        return raw.decode("utf-8", errors="replace"), digest, truncated

    def _mapped_result(
        self,
        argv: tuple[str, ...],
        record: DurableExecutionRecord,
        *,
        exit_code: int,
    ) -> NativeCommandResult:
        stdout, stdout_sha, stdout_truncated = self._read_artifact(
            self._repo_root / record.stdout_ref
        )
        stderr, stderr_sha, stderr_truncated = self._read_artifact(
            self._repo_root / record.stderr_ref
        )
        return NativeCommandResult(
            executable=PureWindowsPath(argv[0]).name,
            argument_count=len(argv),
            exit_code=exit_code,
            timed_out=False,
            stdout=stdout,
            stderr=stderr,
            stdout_sha256=stdout_sha,
            stderr_sha256=stderr_sha,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
        )

    def _poll_until_resolved(
        self, execution_id: str, *, timeout_seconds: int
    ) -> tuple[SupervisedInspection | None, bool]:
        start = self._clock_fn()
        while True:
            try:
                inspection = self._supervised.inspect(execution_id)
            except SupervisedExecutionError:
                return None, False
            if inspection.state is SupervisedInspectionState.RESULT_AVAILABLE:
                return inspection, False
            if inspection.recovery_required:
                return inspection, False
            if self._clock_fn() - start + self._poll_interval_seconds >= timeout_seconds:
                return inspection, True
            self._sleep_fn(self._poll_interval_seconds)

    def run(self, spec: NativeCommandSpec) -> NativeCommandResult:
        if not isinstance(spec, NativeCommandSpec):
            raise NativeExecutionError("SPEC_INVALID")
        argv = self._validated_argv(spec)
        environment_overrides = self._validated_environment_overrides(spec)
        cwd = self._scope.resolve_relative(spec.cwd, must_exist=True)
        if cwd != self._repo_root:
            raise NativeExecutionError("CWD_UNSUPPORTED")

        fingerprint = compute_execution_fingerprint(self._fingerprint_spec(argv))
        assessment: DuplicateExecutionAssessment = self._guard.assess(self._fingerprint_spec(argv))
        if assessment.decision is DuplicateExecutionDecision.BLOCKED_UNKNOWN:
            return self._failure_result(argv, error_code="SUPERVISED_DUPLICATE_BLOCKED")

        execution_id: str | None = None
        if assessment.decision in (
            DuplicateExecutionDecision.ATTACH_RUNNING,
            DuplicateExecutionDecision.REUSE_COMPLETED,
        ):
            if assessment.record is None:
                return self._failure_result(argv, error_code="SUPERVISED_ATTACH_RECORD_MISSING")
            execution_id = assessment.record.execution_id
        else:
            execution_id = f"exec-{uuid.uuid4().hex[:16]}"
            run_rel = f"runs/{execution_id}"
            record = new_execution_record(
                execution_id=execution_id,
                job_id=self._job_id,
                work_order_ref=self._work_order_ref,
                project_id=self._project_id,
                worker_id=self._worker_id,
                backend_id=self._backend_id,
                agent_ref="agent:supervised-native",
                repo_root=str(self._repo_root),
                branch=self._branch,
                head_before=self._head_before,
                operation_ref=self._operation_ref(argv),
                command_fingerprint=fingerprint,
                command_summary=" ".join(argv[:3])[:200],
                runtime_profile_ref=self._runtime_profile_ref,
                run_dir_ref=run_rel,
                stdout_ref=f"{run_rel}/stdout.log",
                stderr_ref=f"{run_rel}/stderr.log",
                result_ref=f"{run_rel}/result.json",
                report_ref=None,
                transport_state=TransportState.CONNECTED,
                execution_state=ExecutionProcessState.QUEUED,
            )
            plan = SupervisedLaunchPlan(
                record=record,
                runtime_root=self._repo_root,
                target_argv=argv,
                target_executable_name=PureWindowsPath(argv[0]).name,
                environment_overrides=environment_overrides,
            )
            try:
                outcome = self._supervised.launch(plan)
            except SupervisedExecutionError as exc:
                return self._failure_result(argv, error_code=f"SUPERVISED_LAUNCH_FAILED:{exc.code}")
            if outcome.recovery_required:
                code = outcome.error_code or "SUPERVISED_LAUNCH_FAILED"
                return self._failure_result(argv, error_code=f"SUPERVISED_LAUNCH_FAILED:{code}")

        inspection, timed_out = self._poll_until_resolved(
            execution_id, timeout_seconds=spec.timeout_seconds
        )
        if inspection is None:
            return self._failure_result(argv, error_code="SUPERVISED_INSPECT_FAILED")
        if timed_out:
            record = self._store.get(execution_id)
            stdout, stdout_sha, stdout_truncated = self._read_artifact(
                self._repo_root / record.stdout_ref
            )
            stderr, stderr_sha, stderr_truncated = self._read_artifact(
                self._repo_root / record.stderr_ref
            )
            return NativeCommandResult(
                executable=PureWindowsPath(argv[0]).name,
                argument_count=len(argv),
                exit_code=None,
                timed_out=True,
                stdout=stdout,
                stderr=stderr,
                stdout_sha256=stdout_sha,
                stderr_sha256=stderr_sha,
                stdout_truncated=stdout_truncated,
                stderr_truncated=stderr_truncated,
            )
        if inspection.recovery_required:
            code = inspection.error_code or "SUPERVISOR_RECOVERY_REQUIRED"
            return self._failure_result(argv, error_code=f"SUPERVISED_RECOVERY_REQUIRED:{code}")

        try:
            current = self._store.get(execution_id)
            collected = self._supervised.collect(
                execution_id,
                expected_version=current.version,
            )
        except ExecutionStoreError:
            return self._failure_result(argv, error_code="SUPERVISED_VERSION_CONFLICT")
        except SupervisedExecutionError as exc:
            return self._failure_result(argv, error_code=f"SUPERVISED_COLLECT_FAILED:{exc.code}")
        if collected.result is None:
            code = collected.error_code or "SUPERVISED_COLLECT_FAILED"
            return self._failure_result(argv, error_code=f"SUPERVISED_COLLECT_FAILED:{code}")
        return self._mapped_result(argv, collected.record, exit_code=collected.result.exit_code)


def build_supervised_native_adapter_resolver(
    *,
    service: object,
    database_path: "Path | str",
    python_executable: str = __import__("sys").executable,
    git_executable: str = "git",
    poll_interval_seconds: float = 0.05,
):
    """Assemble a ControlCenter resolver whose native commands run supervised.

    Enabling point for the resilient path: pass the returned resolver (or set
    ``supervised=True`` on ``DurableJobControlService.open``) to route git and
    verification commands through durable execution records, duplicate
    protection, and bounded collection. The default assembly remains the plain
    subprocess runner until per-job fingerprint identity plumbing lands; the
    static identity below keeps dedup correct per (repo, argv) which is the
    operation-level duplicate dimension.
    """
    import sys

    from .execution_store import SQLiteExecutionStore
    from .native_operation_assembly import ControlCenterNativeAdapterResolver
    from .owned_process import WindowsOwnedProcessController
    from .supervised_execution import SupervisedExecutionService
    from .windows_io import LoopbackReadyzHttpProbe, StrictPowerShellInspectionRunner
    from .windows_observer import WindowsRuntimeObserver

    store = SQLiteExecutionStore(database_path)
    observer = WindowsRuntimeObserver(
        runner=StrictPowerShellInspectionRunner(),
        http_probe=LoopbackReadyzHttpProbe(),
    )
    controller = WindowsOwnedProcessController(observer=observer)
    python_name = PureWindowsPath(python_executable).name
    git_name = PureWindowsPath(git_executable).name
    supervised_service = SupervisedExecutionService(
        store=store,
        controller=controller,
        observer=observer,
        allowed_target_executables=(python_name, git_name),
        python_executable=python_executable,
    )

    def runner_factory(scope: NativeExecutionScope) -> SupervisedCommandRunner:
        return SupervisedCommandRunner(
            scope=scope,
            execution_store=store,
            supervised=supervised_service,
            job_id="job:native-supervised",
            work_order_ref="docs/contracts/resilient-execution-supervisor.md",
            project_id="project:native",
            worker_id="worker:native-supervised",
            backend_id="supervised-native",
            branch="unknown",
            head_before="unknown",
            runtime_profile_ref="runtime:supervised-native",
            poll_interval_seconds=poll_interval_seconds,
        )

    return ControlCenterNativeAdapterResolver(
        service=service,
        git_executable=git_executable,
        python_executable=python_executable,
        runner_factory=runner_factory,
    )
