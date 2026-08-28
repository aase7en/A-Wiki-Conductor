from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.domain import RecoveryClassification, TaskState
from a_conductor.job_execution import (
    DurableJobExecutionCoordinator,
    JobBackendResult,
    JobExecutionContext,
    JobExecutionCoordinatorError,
    JobExecutionOutcome,
)
from a_conductor.job_state import JobStateError
from a_conductor.job_store import JobEventType, JobStoreError, SQLiteJobStore


class FakeBackend:
    def __init__(self, result: JobBackendResult | None = None) -> None:
        self.result = result or JobBackendResult(success=True, evidence_ref="evidence-ok")
        self.calls: list[tuple[str, str]] = []
        self.error: BaseException | None = None

    def execute(
        self, operation_ref: str, context: JobExecutionContext
    ) -> JobBackendResult:
        self.calls.append((operation_ref, context.worker_id))
        if self.error is not None:
            raise self.error
        return self.result


def prepare_gating(tmp_path: Path, *, max_attempts: int = 3):
    store = SQLiteJobStore(tmp_path / "control.sqlite")
    job = store.create_job(
        job_id="job-1",
        work_order_ref="docs/work-orders/WO-1.md",
        project_id="project-1",
        max_attempts=max_attempts,
    )
    ready = store.transition("job-1", TaskState.READY, expected_version=job.version)
    claimed = store.transition(
        "job-1",
        TaskState.CLAIMED,
        expected_version=ready.version,
        worker_id="a-worker-01",
    )
    gating = store.transition("job-1", TaskState.GATING, expected_version=claimed.version)
    return store, gating


def test_success_result_requires_evidence_and_failure_requires_recovery_classification() -> None:
    with pytest.raises(ValueError):
        JobBackendResult(success=True)
    with pytest.raises(ValueError):
        JobBackendResult(success=True, evidence_ref="e", recovery_classification=RecoveryClassification.UNKNOWN)
    with pytest.raises(ValueError):
        JobBackendResult(success=False, evidence_ref="e")


def test_operation_ref_must_be_opaque_identifier_not_raw_command(tmp_path: Path) -> None:
    store, gating = prepare_gating(tmp_path)
    backend = FakeBackend()
    coordinator = DurableJobExecutionCoordinator(store=store, backend=backend)

    with pytest.raises(ValueError):
        coordinator.execute(
            "job-1",
            expected_version=gating.version,
            worker_id="a-worker-01",
            operation_ref="python -m pytest",
        )
    assert backend.calls == []


class InvalidResultBackend:
    def execute(self, operation_ref: str, context: JobExecutionContext):
        return object()


def test_invalid_backend_result_becomes_unknown_recovery(tmp_path: Path) -> None:
    store, gating = prepare_gating(tmp_path)
    coordinator = DurableJobExecutionCoordinator(store=store, backend=InvalidResultBackend())

    outcome = coordinator.execute(
        "job-1",
        expected_version=gating.version,
        worker_id="a-worker-01",
        operation_ref="op:invalid-result",
    )

    assert outcome.success is False
    assert outcome.error_code == "BACKEND_RESULT_INVALID"
    assert outcome.job.state is TaskState.RECOVERY_NEEDED
    assert outcome.job.recovery_classification is RecoveryClassification.UNKNOWN


def test_stale_version_does_not_invoke_backend(tmp_path: Path) -> None:
    store, gating = prepare_gating(tmp_path)
    backend = FakeBackend()
    coordinator = DurableJobExecutionCoordinator(store=store, backend=backend)

    with pytest.raises(JobStoreError) as exc_info:
        coordinator.execute(
            "job-1",
            expected_version=gating.version - 1,
            worker_id="a-worker-01",
            operation_ref="op:test",
        )
    assert exc_info.value.code == "JOB_VERSION_CONFLICT"
    assert backend.calls == []


def test_job_must_be_gated_and_worker_claim_must_match(tmp_path: Path) -> None:
    store = SQLiteJobStore(tmp_path / "control.sqlite")
    job = store.create_job(job_id="job-1", work_order_ref="wo", project_id="p")
    ready = store.transition("job-1", TaskState.READY, expected_version=job.version)
    backend = FakeBackend()
    coordinator = DurableJobExecutionCoordinator(store=store, backend=backend)

    with pytest.raises(JobExecutionCoordinatorError) as exc_info:
        coordinator.execute(
            "job-1",
            expected_version=ready.version,
            worker_id="a-worker-01",
            operation_ref="op:test",
        )
    assert exc_info.value.code == "JOB_NOT_GATED"
    assert backend.calls == []

    claimed = store.transition(
        "job-1", TaskState.CLAIMED, expected_version=ready.version, worker_id="a-worker-01"
    )
    gating = store.transition("job-1", TaskState.GATING, expected_version=claimed.version)
    with pytest.raises(JobExecutionCoordinatorError) as exc_info:
        coordinator.execute(
            "job-1",
            expected_version=gating.version,
            worker_id="a-worker-02",
            operation_ref="op:test",
        )
    assert exc_info.value.code == "WORKER_CLAIM_MISMATCH"
    assert backend.calls == []


def test_successful_execution_checkpoints_then_moves_to_verifying(tmp_path: Path) -> None:
    store, gating = prepare_gating(tmp_path)
    backend = FakeBackend(JobBackendResult(success=True, evidence_ref="evidence-run-1"))
    coordinator = DurableJobExecutionCoordinator(store=store, backend=backend)

    outcome = coordinator.execute(
        "job-1",
        expected_version=gating.version,
        worker_id="a-worker-01",
        operation_ref="op:pytest-targeted",
    )

    assert outcome == JobExecutionOutcome(
        success=True,
        job=store.get_job("job-1"),
        evidence_ref="evidence-run-1",
        error_code=None,
        recovery_required=False,
    )
    assert outcome.job.state is TaskState.VERIFYING
    assert outcome.job.attempt_count == 1
    assert backend.calls == [("op:pytest-targeted", "a-worker-01")]
    events = store.list_events("job-1")
    assert [event.event_type for event in events[-3:]] == [
        JobEventType.TRANSITION,
        JobEventType.CHECKPOINT,
        JobEventType.TRANSITION,
    ]
    assert events[-2].checkpoint_ref == "operation:op:pytest-targeted:complete"
    assert events[-2].evidence_ref == "evidence-run-1"
    assert events[-1].to_state is TaskState.VERIFYING


def test_reported_backend_failure_moves_to_recovery_needed(tmp_path: Path) -> None:
    store, gating = prepare_gating(tmp_path)
    backend = FakeBackend(
        JobBackendResult(
            success=False,
            evidence_ref="evidence-failed",
            recovery_classification=RecoveryClassification.PARTIAL_MUTATION,
        )
    )
    coordinator = DurableJobExecutionCoordinator(store=store, backend=backend)

    outcome = coordinator.execute(
        "job-1",
        expected_version=gating.version,
        worker_id="a-worker-01",
        operation_ref="op:mutating-step",
    )

    assert outcome.success is False
    assert outcome.error_code == "BACKEND_REPORTED_FAILURE"
    assert outcome.recovery_required is True
    assert outcome.job.state is TaskState.RECOVERY_NEEDED
    assert outcome.job.recovery_classification is RecoveryClassification.PARTIAL_MUTATION
    assert outcome.evidence_ref == "evidence-failed"


def test_unexpected_backend_exception_is_reduced_to_unknown_recovery(tmp_path: Path) -> None:
    store, gating = prepare_gating(tmp_path)
    backend = FakeBackend()
    backend.error = RuntimeError("super-secret-backend-detail")
    coordinator = DurableJobExecutionCoordinator(store=store, backend=backend)

    outcome = coordinator.execute(
        "job-1",
        expected_version=gating.version,
        worker_id="a-worker-01",
        operation_ref="op:explode",
    )

    assert outcome.success is False
    assert outcome.error_code == "BACKEND_EXECUTION_FAILED"
    assert outcome.recovery_required is True
    assert outcome.job.recovery_classification is RecoveryClassification.UNKNOWN
    assert "super-secret-backend-detail" not in repr(outcome)
    assert b"super-secret-backend-detail" not in (tmp_path / "control.sqlite").read_bytes()


def test_retry_budget_failure_happens_before_second_backend_invocation(tmp_path: Path) -> None:
    store, gating = prepare_gating(tmp_path, max_attempts=1)
    first_backend = FakeBackend(
        JobBackendResult(
            success=False,
            recovery_classification=RecoveryClassification.NO_MUTATION,
        )
    )
    first = DurableJobExecutionCoordinator(store=store, backend=first_backend)
    failed = first.execute(
        "job-1",
        expected_version=gating.version,
        worker_id="a-worker-01",
        operation_ref="op:first",
    )
    ready = store.transition("job-1", TaskState.READY, expected_version=failed.job.version)
    claimed = store.transition(
        "job-1", TaskState.CLAIMED, expected_version=ready.version, worker_id="a-worker-01"
    )
    gating_again = store.transition("job-1", TaskState.GATING, expected_version=claimed.version)

    second_backend = FakeBackend()
    second = DurableJobExecutionCoordinator(store=store, backend=second_backend)
    with pytest.raises(JobStateError) as exc_info:
        second.execute(
            "job-1",
            expected_version=gating_again.version,
            worker_id="a-worker-01",
            operation_ref="op:second",
        )
    assert exc_info.value.code == "ATTEMPT_BUDGET_EXHAUSTED"
    assert second_backend.calls == []


class CheckpointFailingStore:
    def __init__(self, inner: SQLiteJobStore) -> None:
        self.inner = inner

    def get_job(self, job_id: str):
        return self.inner.get_job(job_id)

    def transition(self, *args, **kwargs):
        return self.inner.transition(*args, **kwargs)

    def checkpoint(self, *args, **kwargs):
        raise JobStoreError("SIMULATED_CHECKPOINT_FAILURE")


def test_persistence_failure_after_backend_is_explicit_recovery_required(tmp_path: Path) -> None:
    inner, gating = prepare_gating(tmp_path)
    backend = FakeBackend(JobBackendResult(success=True, evidence_ref="evidence-mutated"))
    coordinator = DurableJobExecutionCoordinator(
        store=CheckpointFailingStore(inner),
        backend=backend,
    )

    with pytest.raises(JobExecutionCoordinatorError) as exc_info:
        coordinator.execute(
            "job-1",
            expected_version=gating.version,
            worker_id="a-worker-01",
            operation_ref="op:after-mutation",
        )

    assert exc_info.value.code == "DURABLE_CHECKPOINT_FAILED"
    assert exc_info.value.recovery_required is True
    assert backend.calls == [("op:after-mutation", "a-worker-01")]
    assert inner.get_job("job-1").state is TaskState.EXECUTING


def test_coordinator_has_no_scheduler_retry_loop_or_router_surface(tmp_path: Path) -> None:
    store, _ = prepare_gating(tmp_path)
    coordinator = DurableJobExecutionCoordinator(store=store, backend=FakeBackend())
    for forbidden in (
        "start_background",
        "schedule",
        "run_forever",
        "retry",
        "route_worker",
        "route_model",
        "plan",
        "decompose",
    ):
        assert not hasattr(coordinator, forbidden)


class ContextCapturingBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, JobExecutionContext]] = []

    def execute(
        self,
        operation_ref: str,
        context: JobExecutionContext,
    ) -> JobBackendResult:
        self.calls.append((operation_ref, context))
        return JobBackendResult(success=True, evidence_ref="evidence-context")


def test_backend_receives_durable_execution_context_after_attempt_starts(tmp_path: Path) -> None:
    store, gating = prepare_gating(tmp_path)
    backend = ContextCapturingBackend()
    coordinator = DurableJobExecutionCoordinator(store=store, backend=backend)

    outcome = coordinator.execute(
        "job-1",
        expected_version=gating.version,
        worker_id="a-worker-01",
        operation_ref="op:context",
    )

    assert outcome.success is True
    assert backend.calls == [(
        "op:context",
        JobExecutionContext(
            job_id="job-1",
            work_order_ref="docs/work-orders/WO-1.md",
            project_id="project-1",
            worker_id="a-worker-01",
            attempt_no=1,
            max_attempts=3,
        ),
    )]
