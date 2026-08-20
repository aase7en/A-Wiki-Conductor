"""Transport-neutral dispatch from bounded operator requests to job control.

The dispatcher is intentionally structural: it does not import the concrete
P1-038 job-control implementation. It contains no SQL, network, Telegram,
Discord, subprocess, planner, router, or generic transition surface.
"""

from __future__ import annotations

import re
from typing import Callable, Protocol

from .job_execution import JobExecutionOutcome
from .job_state import JobRuntimeState
from .job_store import JobEvent
from .operator_protocol import OperatorAction, OperatorRequest, OperatorResponse


_SAFE_CODE_RE = re.compile(r"^[A-Za-z0-9._/@:-]{1,160}$")


class OperatorJobControl(Protocol):
    def create_job(
        self,
        *,
        job_id: str,
        work_order_ref: str,
        project_id: str,
        max_attempts: int = 3,
    ) -> JobRuntimeState: ...

    def get_job(self, job_id: str) -> JobRuntimeState: ...

    def list_events(self, job_id: str) -> tuple[JobEvent, ...]: ...

    def mark_ready(self, job_id: str, *, expected_version: int) -> JobRuntimeState: ...

    def claim(
        self,
        job_id: str,
        *,
        expected_version: int,
        worker_id: str,
    ) -> JobRuntimeState: ...

    def gate(
        self,
        job_id: str,
        *,
        expected_version: int,
        worker_id: str,
    ) -> JobRuntimeState: ...

    def checkpoint(
        self,
        job_id: str,
        *,
        expected_version: int,
        checkpoint_ref: str,
        evidence_ref: str | None = None,
    ) -> JobRuntimeState: ...

    def execute_operation(
        self,
        job_id: str,
        *,
        expected_version: int,
        worker_id: str,
        operation_ref: str,
    ) -> JobExecutionOutcome: ...


StatusProvider = Callable[[], OperatorResponse]


def _response_from_job(
    job: JobRuntimeState,
    *,
    ok: bool = True,
    code: str = "OK",
    refs: tuple[str, ...] = (),
) -> OperatorResponse:
    return OperatorResponse(
        ok=ok,
        code=code,
        job_id=job.job_id,
        state=job.state.value,
        version=job.version,
        worker_id=job.worker_id,
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        refs=refs,
    )


def _safe_error_code(exc: BaseException) -> str:
    value = getattr(exc, "code", None)
    if isinstance(value, str) and _SAFE_CODE_RE.fullmatch(value) and not value.startswith("-"):
        return value
    return "OPERATOR_INTERNAL_ERROR"


def _require_event_ref_limit(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > 100:
        raise ValueError("max_event_refs must be between 0 and 100")
    return value


def dispatch_operator_request(
    request: OperatorRequest,
    *,
    service: OperatorJobControl,
    status_provider: StatusProvider | None = None,
    max_event_refs: int = 20,
) -> OperatorResponse:
    if not isinstance(request, OperatorRequest):
        raise TypeError("request must be an OperatorRequest")
    max_event_refs = _require_event_ref_limit(max_event_refs)

    if request.action is OperatorAction.STATUS:
        if status_provider is None:
            return OperatorResponse(ok=False, code="OPERATOR_STATUS_UNAVAILABLE")
        try:
            response = status_provider()
            if not isinstance(response, OperatorResponse):
                return OperatorResponse(ok=False, code="OPERATOR_INTERNAL_ERROR")
            return response
        except BaseException as exc:
            return OperatorResponse(ok=False, code=_safe_error_code(exc))

    try:
        if request.action is OperatorAction.JOB_GET:
            return _response_from_job(service.get_job(request.job_id))

        if request.action is OperatorAction.JOB_EVENTS:
            events = service.list_events(request.job_id)
            refs = tuple(event.event_id for event in events[:max_event_refs])
            return OperatorResponse(ok=True, code="OK", job_id=request.job_id, refs=refs)

        if request.action is OperatorAction.JOB_CREATE:
            job = service.create_job(
                job_id=request.job_id,
                work_order_ref=request.work_order_ref,
                project_id=request.project_id,
                max_attempts=request.max_attempts,
            )
            return _response_from_job(job)

        if request.action is OperatorAction.JOB_READY:
            job = service.mark_ready(
                request.job_id,
                expected_version=request.expected_version,
            )
            return _response_from_job(job)

        if request.action is OperatorAction.JOB_CLAIM:
            job = service.claim(
                request.job_id,
                expected_version=request.expected_version,
                worker_id=request.worker_id,
            )
            return _response_from_job(job)

        if request.action is OperatorAction.JOB_GATE:
            job = service.gate(
                request.job_id,
                expected_version=request.expected_version,
                worker_id=request.worker_id,
            )
            return _response_from_job(job)

        if request.action is OperatorAction.JOB_CHECKPOINT:
            job = service.checkpoint(
                request.job_id,
                expected_version=request.expected_version,
                checkpoint_ref=request.checkpoint_ref,
                evidence_ref=request.evidence_ref,
            )
            return _response_from_job(job)

        if request.action is OperatorAction.JOB_EXECUTE:
            outcome = service.execute_operation(
                request.job_id,
                expected_version=request.expected_version,
                worker_id=request.worker_id,
                operation_ref=request.operation_ref,
            )
            if not isinstance(outcome, JobExecutionOutcome):
                return OperatorResponse(
                    ok=False,
                    code="OPERATOR_INTERNAL_ERROR",
                    job_id=request.job_id,
                )
            refs = (outcome.evidence_ref,) if outcome.evidence_ref is not None else ()
            return _response_from_job(
                outcome.job,
                ok=outcome.success,
                code=(
                    "OK"
                    if outcome.success
                    else outcome.error_code or "JOB_EXECUTION_FAILED"
                ),
                refs=refs,
            )

        return OperatorResponse(
            ok=False,
            code="OPERATOR_ACTION_UNSUPPORTED",
            job_id=request.job_id,
        )
    except BaseException as exc:
        return OperatorResponse(
            ok=False,
            code=_safe_error_code(exc),
            job_id=request.job_id,
        )
