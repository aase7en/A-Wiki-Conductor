"""Recovery reconciliation after transport restoration.

This module never launches or retries work. It composes the existing transport
ownership gate, supervised execution inspection/collection, durable execution
store, and read-only Git observers to classify the exact next safe action.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Protocol

from .execution_record import DurableExecutionRecord, ExecutionProcessState
from .execution_store import ExecutionStoreError
from .native_adapters import NativeGitReadAdapter
from .native_execution import NativeExecutionError, NativeExecutionScope
from .project_identity import GitReadOnlyRunner, StrictReadOnlyGitRunner
from .supervised_execution import (
    SupervisedCollectOutcome,
    SupervisedInspection,
    SupervisedInspectionState,
)
from .transport_recovery import (
    ExecutionTransportService,
    TransportMutationOutcome,
    TransportRecoveryError,
)


class RecoveryDecision(str, Enum):
    MONITOR_ORIGINAL = "MONITOR_ORIGINAL"
    VERIFY_RESULT = "VERIFY_RESULT"
    REVIEW_FAILURE = "REVIEW_FAILURE"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    RECOVERY_BLOCKED = "RECOVERY_BLOCKED"


@dataclass(frozen=True, slots=True)
class RecoveryRepositoryObservation:
    repo_root: str
    branch: str | None
    head: str | None
    dirty: bool | None
    error_code: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.repo_root, str) or not self.repo_root.strip():
            raise ValueError("repo_root must not be blank")
        for value, field_name in (
            (self.branch, "branch"),
            (self.head, "head"),
            (self.error_code, "error_code"),
        ):
            if value is not None and (
                not isinstance(value, str)
                or not value.strip()
                or "\x00" in value
                or "\r" in value
                or "\n" in value
            ):
                raise ValueError(f"{field_name} must be safe single-line text")
        if self.dirty is not None and not isinstance(self.dirty, bool):
            raise ValueError("dirty must be bool or None")


@dataclass(frozen=True, slots=True)
class RecoveryReconciliationOutcome:
    decision: RecoveryDecision
    record: DurableExecutionRecord
    reason_code: str
    supervisor_pid: int | None = None
    exit_code: int | None = None
    retry_permitted: bool = False
    transport_changed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.decision, RecoveryDecision):
            raise ValueError("decision must be a RecoveryDecision")
        if not isinstance(self.record, DurableExecutionRecord):
            raise ValueError("record must be a DurableExecutionRecord")
        if (
            not isinstance(self.reason_code, str)
            or not self.reason_code.strip()
            or "\x00" in self.reason_code
            or "\r" in self.reason_code
            or "\n" in self.reason_code
        ):
            raise ValueError("reason_code must be safe single-line text")
        if self.supervisor_pid is not None and (
            not isinstance(self.supervisor_pid, int)
            or isinstance(self.supervisor_pid, bool)
            or self.supervisor_pid < 1
        ):
            raise ValueError("supervisor_pid must be >= 1")
        if self.exit_code is not None and (
            not isinstance(self.exit_code, int) or isinstance(self.exit_code, bool)
        ):
            raise ValueError("exit_code must be an integer")
        if not isinstance(self.retry_permitted, bool):
            raise ValueError("retry_permitted must be a bool")
        if not isinstance(self.transport_changed, bool):
            raise ValueError("transport_changed must be a bool")


class RecoveryExecutionStore(Protocol):
    def get(self, execution_id: str) -> DurableExecutionRecord: ...

    def set_execution_state(
        self,
        execution_id: str,
        state: ExecutionProcessState,
        *,
        expected_version: int,
        evidence_ref: str | None = None,
    ) -> DurableExecutionRecord: ...


class RecoverySupervisedService(Protocol):
    def inspect(self, execution_id: str) -> SupervisedInspection: ...

    def collect(
        self,
        execution_id: str,
        *,
        expected_version: int,
    ) -> SupervisedCollectOutcome: ...


class RecoveryRepositoryObserver(Protocol):
    def observe(self, record: DurableExecutionRecord) -> RecoveryRepositoryObservation: ...


class GitStatusAdapter(Protocol):
    def status_short(self, *, timeout_seconds: int = 10): ...


StatusAdapterFactory = Callable[[NativeExecutionScope], GitStatusAdapter]


def _same_path(left: str | Path, right: str | Path) -> bool:
    try:
        a = str(Path(left).expanduser().resolve(strict=False)).casefold()
        b = str(Path(right).expanduser().resolve(strict=False)).casefold()
    except OSError:
        return False
    return a == b


class StrictRecoveryRepositoryObserver:
    """Collect bounded read-only root/branch/HEAD/dirty facts for recovery."""

    def __init__(
        self,
        *,
        git_runner: GitReadOnlyRunner | None = None,
        status_adapter_factory: StatusAdapterFactory | None = None,
    ) -> None:
        self._git_runner = git_runner or StrictReadOnlyGitRunner()
        self._status_adapter_factory = status_adapter_factory or (
            lambda scope: NativeGitReadAdapter(scope)
        )

    def observe(self, record: DurableExecutionRecord) -> RecoveryRepositoryObservation:
        if not isinstance(record, DurableExecutionRecord):
            raise ValueError("record must be a DurableExecutionRecord")
        worktree = Path(record.repo_root).expanduser().resolve(strict=False)
        if not worktree.is_dir():
            return RecoveryRepositoryObservation(
                repo_root=str(worktree),
                branch=None,
                head=None,
                dirty=None,
                error_code="RECOVERY_REPO_NOT_FOUND",
            )

        root = self._git_runner.show_toplevel(worktree)
        if not root.success or not root.stdout.strip():
            return RecoveryRepositoryObservation(
                repo_root=str(worktree),
                branch=None,
                head=None,
                dirty=None,
                error_code="RECOVERY_GIT_ROOT_OBSERVATION_FAILED",
            )
        branch = self._git_runner.branch(worktree)
        if not branch.success or not branch.stdout.strip():
            return RecoveryRepositoryObservation(
                repo_root=root.stdout,
                branch=None,
                head=None,
                dirty=None,
                error_code="RECOVERY_GIT_BRANCH_OBSERVATION_FAILED",
            )
        head = self._git_runner.head(worktree)
        if not head.success or not head.stdout.strip():
            return RecoveryRepositoryObservation(
                repo_root=root.stdout,
                branch=branch.stdout,
                head=None,
                dirty=None,
                error_code="RECOVERY_GIT_HEAD_OBSERVATION_FAILED",
            )

        try:
            scope = NativeExecutionScope(
                root=worktree,
                mutation_allowed=False,
                allowed_executables=("git",),
            )
            status = self._status_adapter_factory(scope).status_short()
        except (NativeExecutionError, OSError, ValueError):
            return RecoveryRepositoryObservation(
                repo_root=root.stdout,
                branch=branch.stdout,
                head=head.stdout,
                dirty=None,
                error_code="RECOVERY_GIT_STATUS_OBSERVATION_FAILED",
            )
        if status.timed_out or status.exit_code != 0:
            return RecoveryRepositoryObservation(
                repo_root=root.stdout,
                branch=branch.stdout,
                head=head.stdout,
                dirty=None,
                error_code="RECOVERY_GIT_STATUS_OBSERVATION_FAILED",
            )
        return RecoveryRepositoryObservation(
            repo_root=root.stdout,
            branch=branch.stdout,
            head=head.stdout,
            dirty=bool(status.stdout.strip()),
            error_code=None,
        )


class RecoveryReconciliationService:
    def __init__(
        self,
        *,
        execution_store: RecoveryExecutionStore,
        transport_service: ExecutionTransportService,
        supervised_service: RecoverySupervisedService,
        repository_observer: RecoveryRepositoryObserver,
    ) -> None:
        self._execution_store = execution_store
        self._transport_service = transport_service
        self._supervised_service = supervised_service
        self._repository_observer = repository_observer

    @staticmethod
    def _outcome(
        decision: RecoveryDecision,
        record: DurableExecutionRecord,
        reason_code: str,
        *,
        supervisor_pid: int | None = None,
        exit_code: int | None = None,
        transport_changed: bool = False,
    ) -> RecoveryReconciliationOutcome:
        return RecoveryReconciliationOutcome(
            decision=decision,
            record=record,
            reason_code=reason_code,
            supervisor_pid=supervisor_pid,
            exit_code=exit_code,
            retry_permitted=False,
            transport_changed=transport_changed,
        )

    def _mark_recovery_required(
        self,
        record: DurableExecutionRecord,
        *,
        reason_code: str,
        transport_changed: bool,
    ) -> RecoveryReconciliationOutcome:
        current = record
        if current.execution_state is not ExecutionProcessState.RECOVERY_REQUIRED:
            try:
                current = self._execution_store.set_execution_state(
                    current.execution_id,
                    ExecutionProcessState.RECOVERY_REQUIRED,
                    expected_version=current.version,
                    evidence_ref=None,
                )
            except ExecutionStoreError:
                return self._outcome(
                    RecoveryDecision.RECOVERY_BLOCKED,
                    record,
                    "RECOVERY_EXECUTION_STATE_CONFLICT",
                    transport_changed=transport_changed,
                )
        return self._outcome(
            RecoveryDecision.RECOVERY_REQUIRED,
            current,
            reason_code,
            transport_changed=transport_changed,
        )

    def reconcile(
        self,
        execution_id: str,
        *,
        expected_version: int,
        transport_evidence_ref: str | None = None,
    ) -> RecoveryReconciliationOutcome:
        if not isinstance(execution_id, str) or not execution_id.strip():
            raise ValueError("execution_id must not be blank")
        if (
            not isinstance(expected_version, int)
            or isinstance(expected_version, bool)
            or expected_version < 1
        ):
            raise ValueError("expected_version must be >= 1")

        try:
            base = self._execution_store.get(execution_id)
        except ExecutionStoreError as exc:
            raise RuntimeError(exc.code) from exc

        try:
            connected: TransportMutationOutcome = self._transport_service.mark_connected(
                execution_id,
                expected_version=expected_version,
                evidence_ref=transport_evidence_ref,
            )
        except TransportRecoveryError as exc:
            return self._outcome(
                RecoveryDecision.RECOVERY_BLOCKED,
                base,
                exc.code,
            )
        record = connected.record

        repository = self._repository_observer.observe(record)
        if repository.error_code is not None:
            return self._outcome(
                RecoveryDecision.RECOVERY_BLOCKED,
                record,
                repository.error_code,
                transport_changed=connected.changed,
            )
        if not _same_path(repository.repo_root, record.repo_root):
            return self._outcome(
                RecoveryDecision.RECOVERY_BLOCKED,
                record,
                "RECOVERY_REPO_ROOT_MISMATCH",
                transport_changed=connected.changed,
            )
        if repository.branch != record.branch:
            return self._outcome(
                RecoveryDecision.RECOVERY_BLOCKED,
                record,
                "RECOVERY_BRANCH_MISMATCH",
                transport_changed=connected.changed,
            )
        if repository.head != record.head_before:
            return self._outcome(
                RecoveryDecision.RECOVERY_BLOCKED,
                record,
                "RECOVERY_HEAD_MISMATCH",
                transport_changed=connected.changed,
            )

        inspection = self._supervised_service.inspect(execution_id)
        if inspection.state is SupervisedInspectionState.SUPERVISOR_RUNNING:
            current = record
            if current.execution_state is not ExecutionProcessState.PROCESS_STILL_RUNNING:
                try:
                    current = self._execution_store.set_execution_state(
                        execution_id,
                        ExecutionProcessState.PROCESS_STILL_RUNNING,
                        expected_version=current.version,
                        evidence_ref=None,
                    )
                except ExecutionStoreError:
                    return self._outcome(
                        RecoveryDecision.RECOVERY_BLOCKED,
                        record,
                        "RECOVERY_EXECUTION_STATE_CONFLICT",
                        transport_changed=connected.changed,
                    )
            return self._outcome(
                RecoveryDecision.MONITOR_ORIGINAL,
                current,
                "ORIGINAL_PROCESS_STILL_RUNNING",
                supervisor_pid=inspection.supervisor_pid,
                transport_changed=connected.changed,
            )

        if inspection.state is SupervisedInspectionState.STARTING:
            return self._outcome(
                RecoveryDecision.MONITOR_ORIGINAL,
                record,
                "ORIGINAL_PROCESS_STARTING",
                transport_changed=connected.changed,
            )

        if inspection.state is SupervisedInspectionState.RESULT_AVAILABLE:
            collected = self._supervised_service.collect(
                execution_id,
                expected_version=record.version,
            )
            if collected.recovery_required:
                return self._outcome(
                    RecoveryDecision.RECOVERY_REQUIRED,
                    collected.record,
                    collected.error_code or "RECOVERY_RESULT_UNKNOWN",
                    transport_changed=connected.changed,
                )
            if collected.result is None:
                return self._mark_recovery_required(
                    collected.record,
                    reason_code=collected.error_code or "RECOVERY_RESULT_NOT_AVAILABLE",
                    transport_changed=connected.changed,
                )
            if repository.dirty is None:
                return self._outcome(
                    RecoveryDecision.RECOVERY_BLOCKED,
                    collected.record,
                    "RECOVERY_DIRTY_STATE_UNKNOWN",
                    exit_code=collected.result.exit_code,
                    transport_changed=connected.changed,
                )
            if repository.dirty:
                return self._outcome(
                    RecoveryDecision.RECOVERY_BLOCKED,
                    collected.record,
                    "RECOVERY_DIRTY_WORKTREE",
                    exit_code=collected.result.exit_code,
                    transport_changed=connected.changed,
                )
            if collected.result.exit_code == 0:
                return self._outcome(
                    RecoveryDecision.VERIFY_RESULT,
                    collected.record,
                    "ORIGINAL_RESULT_EXIT_ZERO",
                    exit_code=0,
                    transport_changed=connected.changed,
                )
            return self._outcome(
                RecoveryDecision.REVIEW_FAILURE,
                collected.record,
                "ORIGINAL_RESULT_NONZERO",
                exit_code=collected.result.exit_code,
                transport_changed=connected.changed,
            )

        if inspection.state in {
            SupervisedInspectionState.SUPERVISOR_EXITED_RESULT_MISSING,
            SupervisedInspectionState.RECOVERY_REQUIRED,
        }:
            return self._mark_recovery_required(
                record,
                reason_code=inspection.error_code or "RECOVERY_PROCESS_RESULT_UNKNOWN",
                transport_changed=connected.changed,
            )

        return self._mark_recovery_required(
            record,
            reason_code="RECOVERY_INSPECTION_UNKNOWN",
            transport_changed=connected.changed,
        )
