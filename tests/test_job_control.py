from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.domain import TaskState
from a_conductor.job_control import DurableJobControlService
from a_conductor.job_store import JobEventType, JobStoreError
from a_conductor.native_execution import NativeCommandResult
from a_conductor.native_operations import (
    NativeOperationDefinition,
    NativeOperationKind,
    WorkerNativeAdapters,
)


def result_ok() -> NativeCommandResult:
    return NativeCommandResult(
        executable="python.exe",
        argument_count=5,
        exit_code=0,
        timed_out=False,
        stdout="ephemeral-test-output",
        stderr="",
        stdout_sha256="a" * 64,
        stderr_sha256="b" * 64,
        stdout_truncated=False,
        stderr_truncated=False,
    )


class FakeGit:
    def status_short(self, *, timeout_seconds=10):
        return result_ok()

    def working_diff(self, paths=(), *, timeout_seconds=15):
        return result_ok()

    def cached_diff(self, paths=(), *, timeout_seconds=15):
        return result_ok()


class FakeVerification:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...], int]] = []

    def pytest(self, paths=("tests",), *, timeout_seconds=120):
        self.calls.append(("pytest", tuple(paths), timeout_seconds))
        return result_ok()

    def compileall(self, paths=("src",), *, timeout_seconds=120):
        self.calls.append(("compileall", tuple(paths), timeout_seconds))
        return result_ok()


class FakeResolver:
    def __init__(self) -> None:
        self.verification = FakeVerification()
        self.calls: list[str] = []

    def resolve(self, worker_id: str) -> WorkerNativeAdapters:
        self.calls.append(worker_id)
        return WorkerNativeAdapters(git=FakeGit(), verification=self.verification)


def operation_definitions():
    return (
        NativeOperationDefinition(
            operation_ref="op:pytest-job-control",
            kind=NativeOperationKind.PYTEST,
            paths=("tests/test_job_control.py",),
            timeout_seconds=33,
        ),
    )


def open_service(tmp_path: Path, resolver: FakeResolver | None = None):
    native_resolver = resolver or FakeResolver()
    service = DurableJobControlService.open(
        tmp_path / "control.sqlite",
        operations=operation_definitions(),
        native_resolver=native_resolver,
    )
    return service, native_resolver


def test_bounded_facade_drives_create_ready_claim_gate_and_checkpoint(tmp_path: Path) -> None:
    service, _ = open_service(tmp_path)

    created = service.create_job(
        job_id="job-1",
        work_order_ref="docs/work-orders/WO-1.md",
        project_id="project-1",
    )
    ready = service.mark_ready("job-1", expected_version=created.version)
    claimed = service.claim(
        "job-1", expected_version=ready.version, worker_id="a-worker-01"
    )
    gating = service.gate(
        "job-1", expected_version=claimed.version, worker_id="a-worker-01"
    )
    checkpointed = service.checkpoint(
        "job-1",
        expected_version=gating.version,
        checkpoint_ref="operator:approved",
        evidence_ref="evidence:approval",
    )

    assert created.state is TaskState.NEW
    assert ready.state is TaskState.READY
    assert claimed.state is TaskState.CLAIMED
    assert gating.state is TaskState.GATING
    assert checkpointed.state is TaskState.GATING
    assert checkpointed.version == gating.version + 1
    assert service.get_job("job-1") == checkpointed
    assert service.list_events("job-1")[-1].event_type is JobEventType.CHECKPOINT


def test_every_facade_mutation_uses_expected_version(tmp_path: Path) -> None:
    service, _ = open_service(tmp_path)
    created = service.create_job(job_id="job-1", work_order_ref="wo", project_id="p")
    ready = service.mark_ready("job-1", expected_version=created.version)

    with pytest.raises(JobStoreError) as exc_info:
        service.claim(
            "job-1",
            expected_version=created.version,
            worker_id="a-worker-01",
        )
    assert exc_info.value.code == "JOB_VERSION_CONFLICT"
    assert service.get_job("job-1") == ready


def test_execute_operation_delegates_to_durable_coordinator_and_native_backend(tmp_path: Path) -> None:
    resolver = FakeResolver()
    service, _ = open_service(tmp_path, resolver)
    created = service.create_job(job_id="job-1", work_order_ref="wo", project_id="p")
    ready = service.mark_ready("job-1", expected_version=created.version)
    claimed = service.claim(
        "job-1", expected_version=ready.version, worker_id="a-worker-01"
    )
    gating = service.gate(
        "job-1", expected_version=claimed.version, worker_id="a-worker-01"
    )

    outcome = service.execute_operation(
        "job-1",
        expected_version=gating.version,
        worker_id="a-worker-01",
        operation_ref="op:pytest-job-control",
    )

    assert outcome.success is True
    assert outcome.job.state is TaskState.VERIFYING
    assert resolver.calls == ["a-worker-01"]
    assert resolver.verification.calls == [
        ("pytest", ("tests/test_job_control.py",), 33)
    ]
    assert outcome.evidence_ref is not None
    assert outcome.evidence_ref.startswith("native-evidence:")
    assert b"ephemeral-test-output" not in (tmp_path / "control.sqlite").read_bytes()


def test_reopen_service_reads_same_durable_job_and_events(tmp_path: Path) -> None:
    service, resolver = open_service(tmp_path)
    created = service.create_job(job_id="job-1", work_order_ref="wo", project_id="p")
    ready = service.mark_ready("job-1", expected_version=created.version)

    reopened = DurableJobControlService.open(
        tmp_path / "control.sqlite",
        operations=operation_definitions(),
        native_resolver=resolver,
    )

    assert reopened.get_job("job-1") == ready
    assert len(reopened.list_events("job-1")) == 2


def test_open_requires_control_center_when_no_resolver_is_injected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        DurableJobControlService.open(
            tmp_path / "control.sqlite",
            operations=operation_definitions(),
        )


def test_service_exposes_no_generic_transition_command_scheduler_or_router(tmp_path: Path) -> None:
    service, _ = open_service(tmp_path)
    for forbidden in (
        "transition",
        "run",
        "shell",
        "argv",
        "execute_command",
        "schedule",
        "run_forever",
        "retry",
        "route_worker",
        "route_model",
        "plan",
        "decompose",
    ):
        assert not hasattr(service, forbidden)
