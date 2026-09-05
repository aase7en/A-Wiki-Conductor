"""Shared supervised run orchestration authority (WO-P1-158 Phase A).

One coordinator owns the durable supervised run lifecycle used by every
supervised backend: execution fingerprint, duplicate-execution guard,
execution-record creation, run-directory identity, launch, poll/timeout,
collect/version CAS, and bounded stdout/stderr artifact mapping.

``SupervisedCommandRunner`` is a behavior-preserving adapter over this
coordinator (spec/scope validation + delegation). Future supervised
backends (e.g. the ZCode app-server runner) reuse this coordinator instead
of duplicating its lifecycle. No scheduler, retry engine, store, or thread
authority is added here.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Callable, Protocol

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
from .native_execution import NativeCommandResult
from .supervised_execution import (
    SupervisedCollectOutcome,
    SupervisedExecutionError,
    SupervisedInspection,
    SupervisedInspectionState,
    SupervisedLaunchOutcome,
    SupervisedLaunchPlan,
)


_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
_MAX_TRANSIENT_UNKNOWN_OBSERVATIONS = 3


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


@dataclass(frozen=True, slots=True)
class SupervisedRunIdentity:
    """Durable identity bundle bound into every run this coordinator makes."""

    job_id: str
    work_order_ref: str
    project_id: str
    worker_id: str
    backend_id: str
    branch: str
    head_before: str
    runtime_profile_ref: str
    repo_root: str

    def __post_init__(self) -> None:
        for name in (
            "job_id",
            "work_order_ref",
            "project_id",
            "worker_id",
            "backend_id",
            "branch",
            "head_before",
            "runtime_profile_ref",
            "repo_root",
        ):
            _require_text(getattr(self, name), name)


class SupervisedRunCoordinator:
    """Own the fingerprint/dedup/launch/poll/collect lifecycle for one backend."""

    def __init__(
        self,
        *,
        execution_store: SupervisedExecutionFingerprintStore,
        supervised: SupervisedLauncher,
        identity: SupervisedRunIdentity,
        agent_ref: str = "agent:supervised-native",
        poll_interval_seconds: float = 0.05,
        sleep_fn: Callable[[float], None] = time.sleep,
        clock_fn: Callable[[], float] = time.monotonic,
        max_output_bytes: int = 64 * 1024,
    ) -> None:
        for method_name in ("create", "get", "find_by_fingerprint"):
            if not callable(getattr(execution_store, method_name, None)):
                raise ValueError(f"execution_store must provide {method_name}")
        for method_name in ("launch", "inspect", "collect"):
            if not callable(getattr(supervised, method_name, None)):
                raise ValueError(f"supervised must provide {method_name}")
        if not isinstance(identity, SupervisedRunIdentity):
            raise ValueError("identity must be a SupervisedRunIdentity")
        _require_text(agent_ref, "agent_ref")
        if (
            not isinstance(poll_interval_seconds, (int, float))
            or isinstance(poll_interval_seconds, bool)
            or poll_interval_seconds <= 0
        ):
            raise ValueError("poll_interval_seconds must be > 0")
        if not callable(sleep_fn) or not callable(clock_fn):
            raise ValueError("sleep_fn and clock_fn must be callable")
        if isinstance(max_output_bytes, bool) or not isinstance(max_output_bytes, int) or max_output_bytes < 1:
            raise ValueError("max_output_bytes must be positive")
        self._store = execution_store
        self._supervised = supervised
        self._guard = DuplicateExecutionGuard(store=execution_store)
        self._identity = identity
        self._agent_ref = agent_ref
        self._repo_root = Path(identity.repo_root).expanduser().resolve(strict=False)
        self._poll_interval_seconds = float(poll_interval_seconds)
        self._sleep_fn = sleep_fn
        self._clock_fn = clock_fn
        self._max_output_bytes = max_output_bytes

    @property
    def identity(self) -> SupervisedRunIdentity:
        return self._identity

    def operation_ref(self, argv: tuple[str, ...]) -> str:
        digest = hashlib.sha256("\x00".join(argv).encode("utf-8")).hexdigest()[:16]
        return f"native:{digest}"

    def fingerprint_spec(self, argv: tuple[str, ...]) -> ExecutionFingerprintSpec:
        return ExecutionFingerprintSpec(
            project_id=self._identity.project_id,
            job_id=self._identity.job_id,
            work_order_ref=self._identity.work_order_ref,
            backend_id=self._identity.backend_id,
            repo_root=str(self._repo_root),
            branch=self._identity.branch,
            head_before=self._identity.head_before,
            operation_ref=self.operation_ref(argv),
            runtime_profile_ref=self._identity.runtime_profile_ref,
            target_argv=argv,
        )

    def fingerprint_for_argv(self, argv: tuple[str, ...]) -> str:
        return compute_execution_fingerprint(self.fingerprint_spec(argv))

    def _failure_result(self, argv: tuple[str, ...], *, error_code: str) -> NativeCommandResult:
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
        cap = self._max_output_bytes
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
        consecutive_unknown = 0
        while True:
            try:
                inspection = self._supervised.inspect(execution_id)
            except SupervisedExecutionError:
                return None, False
            if inspection.state is SupervisedInspectionState.RESULT_AVAILABLE:
                return inspection, False
            # A caller deadline covers inspection latency too. A late transient
            # recovery classification must not turn an elapsed caller timeout
            # into a false non-timeout result; durable execution state remains
            # available for the next attach/recovery attempt.
            if self._clock_fn() - start + self._poll_interval_seconds >= timeout_seconds:
                return inspection, True
            if inspection.recovery_required:
                if inspection.error_code != "SUPERVISOR_OWNERSHIP_UNKNOWN":
                    return inspection, False
                consecutive_unknown += 1
                if consecutive_unknown >= _MAX_TRANSIENT_UNKNOWN_OBSERVATIONS:
                    return inspection, False
            else:
                consecutive_unknown = 0
            self._sleep_fn(self._poll_interval_seconds)

    def run(
        self,
        argv: tuple[str, ...],
        *,
        environment_overrides: tuple[tuple[str, str], ...] = (),
        timeout_seconds: int,
    ) -> NativeCommandResult:
        fingerprint = compute_execution_fingerprint(self.fingerprint_spec(argv))
        assessment: DuplicateExecutionAssessment = self._guard.assess(self.fingerprint_spec(argv))
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
                job_id=self._identity.job_id,
                work_order_ref=self._identity.work_order_ref,
                project_id=self._identity.project_id,
                worker_id=self._identity.worker_id,
                backend_id=self._identity.backend_id,
                agent_ref=self._agent_ref,
                repo_root=str(self._repo_root),
                branch=self._identity.branch,
                head_before=self._identity.head_before,
                operation_ref=self.operation_ref(argv),
                command_fingerprint=fingerprint,
                command_summary=" ".join(argv[:3])[:200],
                runtime_profile_ref=self._identity.runtime_profile_ref,
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
            execution_id, timeout_seconds=timeout_seconds
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
            return self._failure_result(argv, error_code=f"SUPERVISOR_RECOVERY_REQUIRED:{code}")

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
