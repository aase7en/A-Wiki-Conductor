"""Explicit durable execution transaction coordinator.

The coordinator has no scheduler, router, retry loop, process/Git/filesystem
implementation, or model integration. It wraps one caller-selected bounded
operation with durable job transitions and checkpoint/evidence metadata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from .domain import RecoveryClassification, TaskState
from .job_state import JobRuntimeState
from .job_store import JobStoreError


_OPERATION_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


class JobExecutionCoordinatorError(RuntimeError):
    def __init__(self, code: str, *, recovery_required: bool = False) -> None:
        self.code = code
        self.recovery_required = bool(recovery_required)
        super().__init__(code)


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


def _require_positive_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{field_name} must be >= 1")
    return value


def _require_optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_text(value, field_name)


def _require_operation_ref(value: str) -> str:
    _require_text(value, "operation_ref")
    if _OPERATION_REF_RE.fullmatch(value) is None:
        raise ValueError("operation_ref must be an opaque identifier")
    return value


@dataclass(frozen=True, slots=True)
class JobBackendResult:
    success: bool
    evidence_ref: str | None = None
    recovery_classification: RecoveryClassification | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.success, bool):
            raise ValueError("success must be a bool")
        _require_optional_text(self.evidence_ref, "evidence_ref")
        if self.recovery_classification is not None and not isinstance(
            self.recovery_classification, RecoveryClassification
        ):
            raise ValueError("recovery_classification must be a RecoveryClassification")
        _require_optional_text(self.error_code, "error_code")
        if self.success:
            if self.evidence_ref is None:
                raise ValueError("successful backend result requires evidence_ref")
            if self.recovery_classification is not None:
                raise ValueError("successful backend result cannot require recovery")
            if self.error_code is not None:
                raise ValueError("successful backend result cannot have error_code")
        elif self.recovery_classification is None:
            raise ValueError("failed backend result requires recovery_classification")


@dataclass(frozen=True, slots=True)
class JobExecutionOutcome:
    success: bool
    job: JobRuntimeState
    evidence_ref: str | None
    error_code: str | None
    recovery_required: bool

    def __post_init__(self) -> None:
        if not isinstance(self.success, bool):
            raise ValueError("success must be a bool")
        if not isinstance(self.job, JobRuntimeState):
            raise ValueError("job must be a JobRuntimeState")
        _require_optional_text(self.evidence_ref, "evidence_ref")
        _require_optional_text(self.error_code, "error_code")
        if not isinstance(self.recovery_required, bool):
            raise ValueError("recovery_required must be a bool")


@dataclass(frozen=True, slots=True)
class JobExecutionContext:
    job_id: str
    work_order_ref: str
    project_id: str
    worker_id: str
    attempt_no: int
    max_attempts: int

    def __post_init__(self) -> None:
        _require_text(self.job_id, "job_id")
        _require_text(self.work_order_ref, "work_order_ref")
        _require_text(self.project_id, "project_id")
        _require_text(self.worker_id, "worker_id")
        _require_positive_int(self.attempt_no, "attempt_no")
        _require_positive_int(self.max_attempts, "max_attempts")
        if self.attempt_no > self.max_attempts:
            raise ValueError("attempt_no cannot exceed max_attempts")


class JobExecutionBackend(Protocol):
    def execute(
        self, operation_ref: str, context: JobExecutionContext
    ) -> JobBackendResult: ...


class DurableJobStore(Protocol):
    def get_job(self, job_id: str) -> JobRuntimeState: ...

    def transition(
        self,
        job_id: str,
        target_state: TaskState,
        *,
        expected_version: int,
        worker_id: str | None = None,
        recovery_classification: RecoveryClassification | None = None,
        evidence_ref: str | None = None,
    ) -> JobRuntimeState: ...

    def checkpoint(
        self,
        job_id: str,
        *,
        checkpoint_ref: str,
        expected_version: int,
        evidence_ref: str | None = None,
    ) -> JobRuntimeState: ...


class DurableJobExecutionCoordinator:
    def __init__(self, *, store: DurableJobStore, backend: JobExecutionBackend) -> None:
        self._store = store
        self._backend = backend

    @staticmethod
    def _check_preconditions(
        job: JobRuntimeState,
        *,
        expected_version: int,
        worker_id: str,
    ) -> None:
        if job.version != expected_version:
            raise JobStoreError("JOB_VERSION_CONFLICT")
        if job.state is not TaskState.GATING:
            raise JobExecutionCoordinatorError("JOB_NOT_GATED")
        if job.worker_id != worker_id:
            raise JobExecutionCoordinatorError("WORKER_CLAIM_MISMATCH")

    def _recover_after_backend(
        self,
        executing: JobRuntimeState,
        *,
        classification: RecoveryClassification,
        evidence_ref: str | None,
        error_code: str,
    ) -> JobExecutionOutcome:
        try:
            recovering = self._store.transition(
                executing.job_id,
                TaskState.RECOVERY_NEEDED,
                expected_version=executing.version,
                worker_id=executing.worker_id,
                recovery_classification=classification,
                evidence_ref=evidence_ref,
            )
        except Exception as exc:
            raise JobExecutionCoordinatorError(
                "DURABLE_RECOVERY_WRITE_FAILED",
                recovery_required=True,
            ) from exc
        return JobExecutionOutcome(
            success=False,
            job=recovering,
            evidence_ref=evidence_ref,
            error_code=error_code,
            recovery_required=True,
        )

    def execute(
        self,
        job_id: str,
        *,
        expected_version: int,
        worker_id: str,
        operation_ref: str,
    ) -> JobExecutionOutcome:
        _require_text(job_id, "job_id")
        _require_positive_int(expected_version, "expected_version")
        _require_text(worker_id, "worker_id")
        operation_ref = _require_operation_ref(operation_ref)

        current = self._store.get_job(job_id)
        self._check_preconditions(
            current,
            expected_version=expected_version,
            worker_id=worker_id,
        )

        # This durable transition is the last gate before external execution.
        # Attempt-budget failures therefore happen before the backend is called.
        executing = self._store.transition(
            job_id,
            TaskState.EXECUTING,
            expected_version=current.version,
            worker_id=worker_id,
        )

        try:
            backend_result = self._backend.execute(
                operation_ref,
                JobExecutionContext(
                    job_id=executing.job_id,
                    work_order_ref=executing.work_order_ref,
                    project_id=executing.project_id,
                    worker_id=worker_id,
                    attempt_no=executing.attempt_count,
                    max_attempts=executing.max_attempts,
                ),
            )
        except Exception:
            return self._recover_after_backend(
                executing,
                classification=RecoveryClassification.UNKNOWN,
                evidence_ref=None,
                error_code="BACKEND_EXECUTION_FAILED",
            )

        if not isinstance(backend_result, JobBackendResult):
            return self._recover_after_backend(
                executing,
                classification=RecoveryClassification.UNKNOWN,
                evidence_ref=None,
                error_code="BACKEND_RESULT_INVALID",
            )

        if not backend_result.success:
            assert backend_result.recovery_classification is not None
            return self._recover_after_backend(
                executing,
                classification=backend_result.recovery_classification,
                evidence_ref=backend_result.evidence_ref,
                error_code=backend_result.error_code or "BACKEND_REPORTED_FAILURE",
            )

        assert backend_result.evidence_ref is not None
        try:
            checkpointed = self._store.checkpoint(
                job_id,
                checkpoint_ref=f"operation:{operation_ref}:complete",
                expected_version=executing.version,
                evidence_ref=backend_result.evidence_ref,
            )
        except Exception as exc:
            raise JobExecutionCoordinatorError(
                "DURABLE_CHECKPOINT_FAILED",
                recovery_required=True,
            ) from exc

        try:
            verifying = self._store.transition(
                job_id,
                TaskState.VERIFYING,
                expected_version=checkpointed.version,
                worker_id=worker_id,
                evidence_ref=backend_result.evidence_ref,
            )
        except Exception as exc:
            raise JobExecutionCoordinatorError(
                "DURABLE_VERIFYING_TRANSITION_FAILED",
                recovery_required=True,
            ) from exc

        return JobExecutionOutcome(
            success=True,
            job=verifying,
            evidence_ref=backend_result.evidence_ref,
            error_code=None,
            recovery_required=False,
        )
