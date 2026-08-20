"""Transport-state mutation with durable job ownership preservation.

Transport health is independent from execution process/result state. This
service validates the existing durable job worker claim before changing only
``TransportState`` on a durable execution record. It performs no reconnect,
retry, relaunch, claim release, job transition, or backend-specific action.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol

from .execution_record import DurableExecutionRecord, TransportState
from .execution_store import ExecutionStoreError
from .job_state import JobRuntimeState
from .job_store import JobStoreError


_EVIDENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")


class TransportRecoveryError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class TransportMutationOutcome:
    record: DurableExecutionRecord
    job: JobRuntimeState
    changed: bool


class ExecutionTransportStore(Protocol):
    def get(self, execution_id: str) -> DurableExecutionRecord: ...

    def set_transport_state(
        self,
        execution_id: str,
        state: TransportState,
        *,
        expected_version: int,
        evidence_ref: str | None = None,
    ) -> DurableExecutionRecord: ...


class JobOwnershipStore(Protocol):
    def get_job(self, job_id: str) -> JobRuntimeState: ...


def _require_positive_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{field_name} must be >= 1")
    return value


def _validate_evidence(
    evidence_ref: str | None,
    *,
    required: bool,
) -> str | None:
    if evidence_ref is None:
        if required:
            raise TransportRecoveryError("TRANSPORT_EVIDENCE_REQUIRED")
        return None
    if not isinstance(evidence_ref, str) or not _EVIDENCE_RE.fullmatch(evidence_ref):
        raise TransportRecoveryError("TRANSPORT_EVIDENCE_INVALID")
    return evidence_ref


class ExecutionTransportService:
    def __init__(
        self,
        *,
        execution_store: ExecutionTransportStore,
        job_store: JobOwnershipStore,
    ) -> None:
        self._execution_store = execution_store
        self._job_store = job_store

    def _load_owned(self, execution_id: str) -> tuple[DurableExecutionRecord, JobRuntimeState]:
        try:
            record = self._execution_store.get(execution_id)
        except ExecutionStoreError as exc:
            if exc.code == "EXECUTION_NOT_FOUND":
                raise TransportRecoveryError("TRANSPORT_EXECUTION_NOT_FOUND") from exc
            raise
        try:
            job = self._job_store.get_job(record.job_id)
        except JobStoreError as exc:
            if exc.code == "JOB_NOT_FOUND":
                raise TransportRecoveryError("TRANSPORT_JOB_NOT_FOUND") from exc
            raise
        if job.project_id != record.project_id:
            raise TransportRecoveryError("TRANSPORT_PROJECT_IDENTITY_MISMATCH")
        if job.worker_id is None:
            raise TransportRecoveryError("TRANSPORT_OWNERSHIP_MISSING")
        if job.worker_id != record.worker_id:
            raise TransportRecoveryError("TRANSPORT_OWNERSHIP_MISMATCH")
        return record, job

    def _mark(
        self,
        execution_id: str,
        target: TransportState,
        *,
        expected_version: int,
        evidence_ref: str | None,
        evidence_required: bool,
    ) -> TransportMutationOutcome:
        if not isinstance(target, TransportState):
            raise ValueError("target must be a TransportState")
        _require_positive_int(expected_version, "expected_version")
        evidence = _validate_evidence(evidence_ref, required=evidence_required)
        record, job = self._load_owned(execution_id)
        if record.version != expected_version:
            raise TransportRecoveryError("TRANSPORT_VERSION_CONFLICT")
        if record.transport_state is target:
            return TransportMutationOutcome(record=record, job=job, changed=False)
        try:
            updated = self._execution_store.set_transport_state(
                execution_id,
                target,
                expected_version=expected_version,
                evidence_ref=evidence,
            )
        except ExecutionStoreError as exc:
            if exc.code == "EXECUTION_VERSION_CONFLICT":
                raise TransportRecoveryError("TRANSPORT_VERSION_CONFLICT") from exc
            raise
        return TransportMutationOutcome(record=updated, job=job, changed=True)

    def mark_connected(
        self,
        execution_id: str,
        *,
        expected_version: int,
        evidence_ref: str | None = None,
    ) -> TransportMutationOutcome:
        return self._mark(
            execution_id,
            TransportState.CONNECTED,
            expected_version=expected_version,
            evidence_ref=evidence_ref,
            evidence_required=False,
        )

    def mark_degraded(
        self,
        execution_id: str,
        *,
        expected_version: int,
        evidence_ref: str | None,
    ) -> TransportMutationOutcome:
        return self._mark(
            execution_id,
            TransportState.DEGRADED,
            expected_version=expected_version,
            evidence_ref=evidence_ref,
            evidence_required=True,
        )

    def mark_lost(
        self,
        execution_id: str,
        *,
        expected_version: int,
        evidence_ref: str | None,
    ) -> TransportMutationOutcome:
        return self._mark(
            execution_id,
            TransportState.LOST,
            expected_version=expected_version,
            evidence_ref=evidence_ref,
            evidence_required=True,
        )

    def mark_unavailable(
        self,
        execution_id: str,
        *,
        expected_version: int,
        evidence_ref: str | None,
    ) -> TransportMutationOutcome:
        return self._mark(
            execution_id,
            TransportState.UNAVAILABLE,
            expected_version=expected_version,
            evidence_ref=evidence_ref,
            evidence_required=True,
        )
