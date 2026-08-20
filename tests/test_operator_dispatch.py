from __future__ import annotations

from dataclasses import replace

from a_conductor.domain import TaskState
from a_conductor.job_execution import JobExecutionOutcome
from a_conductor.job_state import JobRuntimeState
from a_conductor.job_store import JobEvent, JobEventType
from a_conductor.operator_dispatch import dispatch_operator_request
from a_conductor.operator_protocol import OperatorResponse, parse_operator_request


def state(
    *,
    job_id: str = "job-1",
    task_state: TaskState = TaskState.READY,
    version: int = 2,
    worker_id: str | None = None,
) -> JobRuntimeState:
    return JobRuntimeState(
        job_id=job_id,
        work_order_ref="A-Wiki:WO-1",
        project_id="project-1",
        state=task_state,
        worker_id=worker_id,
        attempt_count=1 if task_state in {TaskState.EXECUTING, TaskState.VERIFYING} else 0,
        max_attempts=3,
        recovery_classification=None,
        version=version,
    )


class FakeService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []
        self.current = state()
        self.events: tuple[JobEvent, ...] = ()
        self.outcome = JobExecutionOutcome(
            success=True,
            job=replace(
                self.current,
                state=TaskState.VERIFYING,
                worker_id="a-worker-01",
                attempt_count=1,
                version=5,
            ),
            evidence_ref="native:sha256:abc123",
            error_code=None,
            recovery_required=False,
        )
        self.error: BaseException | None = None

    def _record(self, name: str, *args, **kwargs):
        self.calls.append((name, args, kwargs))
        if self.error is not None:
            raise self.error

    def create_job(self, **kwargs):
        self._record("create_job", **kwargs)
        return replace(
            self.current,
            job_id=kwargs["job_id"],
            work_order_ref=kwargs["work_order_ref"],
            project_id=kwargs["project_id"],
            max_attempts=kwargs["max_attempts"],
            version=1,
            state=TaskState.NEW,
            attempt_count=0,
            worker_id=None,
        )

    def get_job(self, job_id: str):
        self._record("get_job", job_id)
        return replace(self.current, job_id=job_id)

    def list_events(self, job_id: str):
        self._record("list_events", job_id)
        return self.events

    def mark_ready(self, job_id: str, *, expected_version: int):
        self._record("mark_ready", job_id, expected_version=expected_version)
        return replace(self.current, job_id=job_id, state=TaskState.READY, version=expected_version + 1)

    def claim(self, job_id: str, *, expected_version: int, worker_id: str):
        self._record("claim", job_id, expected_version=expected_version, worker_id=worker_id)
        return replace(
            self.current,
            job_id=job_id,
            state=TaskState.CLAIMED,
            worker_id=worker_id,
            version=expected_version + 1,
        )

    def gate(self, job_id: str, *, expected_version: int, worker_id: str):
        self._record("gate", job_id, expected_version=expected_version, worker_id=worker_id)
        return replace(
            self.current,
            job_id=job_id,
            state=TaskState.GATING,
            worker_id=worker_id,
            version=expected_version + 1,
        )

    def checkpoint(
        self,
        job_id: str,
        *,
        expected_version: int,
        checkpoint_ref: str,
        evidence_ref: str | None = None,
    ):
        self._record(
            "checkpoint",
            job_id,
            expected_version=expected_version,
            checkpoint_ref=checkpoint_ref,
            evidence_ref=evidence_ref,
        )
        return replace(self.current, job_id=job_id, version=expected_version + 1)

    def execute_operation(
        self,
        job_id: str,
        *,
        expected_version: int,
        worker_id: str,
        operation_ref: str,
    ):
        self._record(
            "execute_operation",
            job_id,
            expected_version=expected_version,
            worker_id=worker_id,
            operation_ref=operation_ref,
        )
        return self.outcome


class CodedError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(detail)


def request(action: str, **fields):
    return parse_operator_request(
        {"protocol_version": "operator.v1", "action": action, **fields}
    )


def test_status_without_provider_is_explicitly_unavailable() -> None:
    response = dispatch_operator_request(request("status"), service=FakeService())
    assert response == OperatorResponse(ok=False, code="OPERATOR_STATUS_UNAVAILABLE")


def test_status_provider_is_injected_and_returned_verbatim() -> None:
    expected = OperatorResponse(ok=True, code="ONLINE")
    response = dispatch_operator_request(
        request("status"),
        service=FakeService(),
        status_provider=lambda: expected,
    )
    assert response is expected


def test_job_get_maps_job_state_to_bounded_response() -> None:
    service = FakeService()
    response = dispatch_operator_request(
        request("job.get", job_id="job-9"),
        service=service,
    )
    assert service.calls == [("get_job", ("job-9",), {})]
    assert response.ok is True
    assert response.job_id == "job-9"
    assert response.state == "READY"
    assert response.version == 2
    assert response.attempt_count == 0
    assert response.max_attempts == 3


def test_create_ready_claim_gate_checkpoint_dispatch_exact_methods() -> None:
    service = FakeService()
    cases = [
        request(
            "job.create",
            job_id="job-new",
            work_order_ref="A-Wiki:WO-2",
            project_id="project-2",
            max_attempts=5,
        ),
        request("job.ready", job_id="job-1", expected_version=1),
        request(
            "job.claim",
            job_id="job-1",
            expected_version=2,
            worker_id="a-worker-01",
        ),
        request(
            "job.gate",
            job_id="job-1",
            expected_version=3,
            worker_id="a-worker-01",
        ),
        request(
            "job.checkpoint",
            job_id="job-1",
            expected_version=4,
            checkpoint_ref="checkpoint:one",
            evidence_ref="evidence:one",
        ),
    ]
    for item in cases:
        response = dispatch_operator_request(item, service=service)
        assert response.ok is True
        assert response.job_id is not None

    assert [call[0] for call in service.calls] == [
        "create_job",
        "mark_ready",
        "claim",
        "gate",
        "checkpoint",
    ]


def test_execute_maps_outcome_and_evidence_without_raw_output() -> None:
    service = FakeService()
    response = dispatch_operator_request(
        request(
            "job.execute",
            job_id="job-1",
            expected_version=4,
            worker_id="a-worker-01",
            operation_ref="verify.pytest.ocr",
        ),
        service=service,
    )
    assert service.calls[0][0] == "execute_operation"
    assert response.ok is True
    assert response.state == "VERIFYING"
    assert response.worker_id == "a-worker-01"
    assert response.refs == ("native:sha256:abc123",)


def test_failed_execute_uses_bounded_error_code() -> None:
    service = FakeService()
    service.outcome = JobExecutionOutcome(
        success=False,
        job=replace(
            service.current,
            state=TaskState.RECOVERY_NEEDED,
            worker_id="a-worker-01",
            recovery_classification=__import__(
                "a_conductor.domain", fromlist=["RecoveryClassification"]
            ).RecoveryClassification.UNKNOWN,
            version=5,
        ),
        evidence_ref="evidence:failure",
        error_code="NATIVE_OPERATION_FAILED",
        recovery_required=True,
    )
    response = dispatch_operator_request(
        request(
            "job.execute",
            job_id="job-1",
            expected_version=4,
            worker_id="a-worker-01",
            operation_ref="verify.pytest.ocr",
        ),
        service=service,
    )
    assert response.ok is False
    assert response.code == "NATIVE_OPERATION_FAILED"
    assert response.state == "RECOVERY_NEEDED"
    assert response.refs == ("evidence:failure",)


def test_events_are_capped_to_opaque_refs_only() -> None:
    service = FakeService()
    service.events = tuple(
        JobEvent(
            event_id=f"event-{index}",
            job_id="job-1",
            sequence_no=index + 1,
            event_type=JobEventType.CHECKPOINT,
            from_state=TaskState.EXECUTING,
            to_state=TaskState.EXECUTING,
            worker_id="a-worker-01",
            recovery_classification=None,
            checkpoint_ref=f"checkpoint:{index}",
            evidence_ref=f"evidence:{index}",
            recorded_at="2026-08-20T00:00:00Z",
        )
        for index in range(12)
    )
    response = dispatch_operator_request(
        request("job.events", job_id="job-1"),
        service=service,
        max_event_refs=5,
    )
    assert response.ok is True
    assert response.job_id == "job-1"
    assert len(response.refs) == 5
    assert response.refs[0] == "event-0"
    assert all("checkpoint" not in ref and "evidence" not in ref for ref in response.refs)


def test_coded_service_exception_never_leaks_exception_text() -> None:
    service = FakeService()
    service.error = CodedError("JOB_VERSION_CONFLICT", "super-secret internal detail")
    response = dispatch_operator_request(
        request("job.get", job_id="job-1"),
        service=service,
    )
    assert response == OperatorResponse(ok=False, code="JOB_VERSION_CONFLICT", job_id="job-1")
    assert "super-secret" not in repr(response)


def test_unknown_service_exception_is_sanitized() -> None:
    service = FakeService()
    service.error = RuntimeError("private runtime value")
    response = dispatch_operator_request(
        request("job.get", job_id="job-1"),
        service=service,
    )
    assert response == OperatorResponse(ok=False, code="OPERATOR_INTERNAL_ERROR", job_id="job-1")
    assert "private runtime value" not in repr(response)
