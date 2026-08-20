from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.domain import TaskState
from a_conductor.execution_record import (
    ExecutionProcessState,
    TransportState,
    new_execution_record,
)
from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.job_store import SQLiteJobStore
from a_conductor.transport_recovery import (
    ExecutionTransportService,
    TransportRecoveryError,
)


def create_claimed_job(store: SQLiteJobStore, *, worker_id: str = "a-worker-01"):
    created = store.create_job(
        job_id="job-001",
        work_order_ref="docs/work-orders/WO-1.md",
        project_id="project-1",
    )
    ready = store.transition(
        "job-001",
        TaskState.READY,
        expected_version=created.version,
    )
    return store.transition(
        "job-001",
        TaskState.CLAIMED,
        expected_version=ready.version,
        worker_id=worker_id,
    )


def create_execution(
    store: SQLiteExecutionStore,
    *,
    worker_id: str = "a-worker-01",
    transport_state: TransportState = TransportState.CONNECTED,
    execution_state: ExecutionProcessState = ExecutionProcessState.RUNNING,
):
    return store.create(
        new_execution_record(
            execution_id="exec-001",
            job_id="job-001",
            work_order_ref="docs/work-orders/WO-1.md",
            project_id="project-1",
            worker_id=worker_id,
            backend_id="serena-local",
            agent_ref="agent:chatgpt",
            repo_root=r"A:\GitHub\example",
            branch="main",
            head_before="a" * 40,
            operation_ref="op:pytest-full",
            command_fingerprint="b" * 64,
            command_summary="full regression",
            runtime_profile_ref="runtime:phase6",
            run_dir_ref="runs/exec-001",
            stdout_ref="runs/exec-001/stdout.log",
            stderr_ref="runs/exec-001/stderr.log",
            result_ref="runs/exec-001/result.json",
            report_ref="runs/exec-001/report.txt",
            transport_state=transport_state,
            execution_state=execution_state,
        )
    )


def open_services(tmp_path: Path):
    database = tmp_path / "control.sqlite"
    jobs = SQLiteJobStore(database)
    executions = SQLiteExecutionStore(database)
    return jobs, executions, ExecutionTransportService(
        execution_store=executions,
        job_store=jobs,
    )


def test_transport_loss_preserves_running_execution_and_claimed_job(tmp_path: Path) -> None:
    jobs, executions, service = open_services(tmp_path)
    claimed = create_claimed_job(jobs)
    running = create_execution(executions)

    outcome = service.mark_lost(
        "exec-001",
        expected_version=running.version,
        evidence_ref="transport:http-502-incident-17",
    )

    assert outcome.changed is True
    assert outcome.record.transport_state is TransportState.LOST
    assert outcome.record.execution_state is ExecutionProcessState.RUNNING
    assert jobs.get_job("job-001") == claimed
    assert jobs.get_job("job-001").state is TaskState.CLAIMED
    assert jobs.get_job("job-001").worker_id == "a-worker-01"


def test_repeated_same_transport_loss_is_idempotent(tmp_path: Path) -> None:
    jobs, executions, service = open_services(tmp_path)
    create_claimed_job(jobs)
    running = create_execution(executions)
    first = service.mark_lost(
        "exec-001",
        expected_version=running.version,
        evidence_ref="transport:http-502-incident-17",
    )
    event_count = len(executions.list_events("exec-001"))

    second = service.mark_lost(
        "exec-001",
        expected_version=first.record.version,
        evidence_ref="transport:http-502-incident-17",
    )

    assert second.changed is False
    assert second.record == first.record
    assert len(executions.list_events("exec-001")) == event_count


def test_transport_connected_after_loss_preserves_process_and_job_claim(tmp_path: Path) -> None:
    jobs, executions, service = open_services(tmp_path)
    claimed = create_claimed_job(jobs)
    running = create_execution(executions)
    lost = service.mark_lost(
        "exec-001",
        expected_version=running.version,
        evidence_ref="transport:lost",
    )

    connected = service.mark_connected(
        "exec-001",
        expected_version=lost.record.version,
        evidence_ref="transport:session-restored",
    )

    assert connected.record.transport_state is TransportState.CONNECTED
    assert connected.record.execution_state is ExecutionProcessState.RUNNING
    assert jobs.get_job("job-001") == claimed


def test_transport_unavailable_does_not_reclassify_verified_execution(tmp_path: Path) -> None:
    jobs, executions, service = open_services(tmp_path)
    create_claimed_job(jobs)
    verified = create_execution(
        executions,
        execution_state=ExecutionProcessState.VERIFICATION_REQUIRED,
    )

    unavailable = service.mark_unavailable(
        "exec-001",
        expected_version=verified.version,
        evidence_ref="transport:backend-unavailable",
    )

    assert unavailable.record.transport_state is TransportState.UNAVAILABLE
    assert unavailable.record.execution_state is ExecutionProcessState.VERIFICATION_REQUIRED


def test_worker_claim_mismatch_blocks_transport_mutation(tmp_path: Path) -> None:
    jobs, executions, service = open_services(tmp_path)
    create_claimed_job(jobs, worker_id="a-worker-01")
    execution = create_execution(executions, worker_id="a-worker-02")

    with pytest.raises(TransportRecoveryError) as exc_info:
        service.mark_lost(
            "exec-001",
            expected_version=execution.version,
            evidence_ref="transport:lost",
        )
    assert exc_info.value.code == "TRANSPORT_OWNERSHIP_MISMATCH"
    assert executions.get("exec-001") == execution


def test_unclaimed_job_blocks_transport_mutation(tmp_path: Path) -> None:
    jobs, executions, service = open_services(tmp_path)
    created = jobs.create_job(
        job_id="job-001",
        work_order_ref="wo",
        project_id="project-1",
    )
    jobs.transition("job-001", TaskState.READY, expected_version=created.version)
    execution = create_execution(executions)

    with pytest.raises(TransportRecoveryError) as exc_info:
        service.mark_lost(
            "exec-001",
            expected_version=execution.version,
            evidence_ref="transport:lost",
        )
    assert exc_info.value.code == "TRANSPORT_OWNERSHIP_MISSING"
    assert executions.get("exec-001") == execution


def test_project_identity_mismatch_blocks_transport_mutation(tmp_path: Path) -> None:
    jobs, executions, service = open_services(tmp_path)
    create_claimed_job(jobs)
    record = new_execution_record(
        execution_id="exec-001",
        job_id="job-001",
        work_order_ref="wo",
        project_id="different-project",
        worker_id="a-worker-01",
        backend_id="serena-local",
        agent_ref=None,
        repo_root=r"A:\GitHub\example",
        branch="main",
        head_before="a" * 40,
        operation_ref="op:test",
        command_fingerprint="b" * 64,
        command_summary="test",
        runtime_profile_ref=None,
        run_dir_ref=None,
        stdout_ref=None,
        stderr_ref=None,
        result_ref=None,
        report_ref=None,
        transport_state=TransportState.CONNECTED,
        execution_state=ExecutionProcessState.RUNNING,
    )
    execution = executions.create(record)

    with pytest.raises(TransportRecoveryError) as exc_info:
        service.mark_degraded(
            "exec-001",
            expected_version=execution.version,
            evidence_ref="transport:degraded",
        )
    assert exc_info.value.code == "TRANSPORT_PROJECT_IDENTITY_MISMATCH"


def test_negative_transport_state_requires_opaque_single_line_evidence(tmp_path: Path) -> None:
    jobs, executions, service = open_services(tmp_path)
    create_claimed_job(jobs)
    execution = create_execution(executions)

    for evidence in (None, "", "HTTP 502\nAuthorization: secret", "x" * 257):
        with pytest.raises(TransportRecoveryError) as exc_info:
            service.mark_lost(
                "exec-001",
                expected_version=execution.version,
                evidence_ref=evidence,
            )
        assert exc_info.value.code in {
            "TRANSPORT_EVIDENCE_REQUIRED",
            "TRANSPORT_EVIDENCE_INVALID",
        }
    assert executions.get("exec-001") == execution


def test_connected_evidence_may_be_omitted(tmp_path: Path) -> None:
    jobs, executions, service = open_services(tmp_path)
    create_claimed_job(jobs)
    lost = create_execution(executions, transport_state=TransportState.LOST)

    outcome = service.mark_connected(
        "exec-001",
        expected_version=lost.version,
    )

    assert outcome.record.transport_state is TransportState.CONNECTED


def test_service_exposes_no_release_retry_relaunch_or_reconnect_loop(tmp_path: Path) -> None:
    jobs, executions, service = open_services(tmp_path)
    for forbidden in (
        "release",
        "release_claim",
        "retry",
        "rerun",
        "relaunch",
        "reconnect",
        "run_forever",
        "route_worker",
        "cancel_job",
    ):
        assert not hasattr(service, forbidden)
