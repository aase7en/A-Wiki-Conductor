from __future__ import annotations

from pathlib import Path

from a_conductor.domain import TaskState
from a_conductor.execution_artifacts import ExecutionArtifactKind, ExecutionArtifactService
from a_conductor.execution_deduplication import (
    DuplicateExecutionDecision,
    DuplicateExecutionGuard,
    ExecutionFingerprintSpec,
    compute_execution_fingerprint,
)
from a_conductor.execution_record import (
    ExecutionProcessState,
    TransportState,
    new_execution_record,
)
from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.fault_injection import (
    DeterministicFaultExecutor,
    FaultScenario,
)
from a_conductor.job_store import SQLiteJobStore
from a_conductor.recovery_reconciliation import (
    RecoveryDecision,
    RecoveryReconciliationService,
    RecoveryRepositoryObservation,
)
from a_conductor.transport_recovery import ExecutionTransportService


class ValidRepositoryObserver:
    def __init__(self, *, root: Path, branch: str = "main", head: str = "a" * 40, dirty: bool = False) -> None:
        self.root = root
        self.branch = branch
        self.head = head
        self.dirty = dirty

    def observe(self, record):
        return RecoveryRepositoryObservation(
            repo_root=str(self.root.resolve()),
            branch=self.branch,
            head=self.head,
            dirty=self.dirty,
            error_code=None,
        )


def create_claimed_job(store: SQLiteJobStore):
    created = store.create_job(job_id="job-1", work_order_ref="wo", project_id="project-1")
    ready = store.transition("job-1", TaskState.READY, expected_version=created.version)
    return store.transition(
        "job-1",
        TaskState.CLAIMED,
        expected_version=ready.version,
        worker_id="a-worker-01",
    )


def fingerprint_spec(repo: Path) -> ExecutionFingerprintSpec:
    return ExecutionFingerprintSpec(
        project_id="project-1",
        job_id="job-1",
        work_order_ref="wo",
        backend_id="fake-local",
        repo_root=str(repo.resolve()),
        branch="main",
        head_before="a" * 40,
        operation_ref="op:fault-test",
        runtime_profile_ref="runtime:fake",
        target_argv=("fake-target.exe", "--scenario"),
    )


def create_execution(store: SQLiteExecutionStore, repo: Path):
    spec = fingerprint_spec(repo)
    return store.create(
        new_execution_record(
            execution_id="exec-1",
            job_id=spec.job_id,
            work_order_ref=spec.work_order_ref,
            project_id=spec.project_id,
            worker_id="a-worker-01",
            backend_id=spec.backend_id,
            agent_ref="agent:test",
            repo_root=spec.repo_root,
            branch=spec.branch,
            head_before=spec.head_before,
            operation_ref=spec.operation_ref,
            command_fingerprint=compute_execution_fingerprint(spec),
            command_summary="fault injection",
            runtime_profile_ref=spec.runtime_profile_ref,
            run_dir_ref="runs/exec-1",
            stdout_ref="runs/exec-1/stdout.log",
            stderr_ref="runs/exec-1/stderr.log",
            result_ref="runs/exec-1/result.json",
            report_ref=None,
            transport_state=TransportState.CONNECTED,
            execution_state=ExecutionProcessState.QUEUED,
        )
    )


def harness(tmp_path: Path, scenario: FaultScenario, *, large_stdout_bytes: int = 256 * 1024):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    database = tmp_path / "control.sqlite"
    jobs = SQLiteJobStore(database)
    executions = SQLiteExecutionStore(database)
    create_claimed_job(jobs)
    queued = create_execution(executions, repo)
    fake = DeterministicFaultExecutor(
        store=executions,
        scenario=scenario,
        large_stdout_bytes=large_stdout_bytes,
    )
    transport = ExecutionTransportService(execution_store=executions, job_store=jobs)
    recovery = RecoveryReconciliationService(
        execution_store=executions,
        transport_service=transport,
        supervised_service=fake,
        repository_observer=ValidRepositoryObserver(root=repo),
    )
    return repo, jobs, executions, queued, fake, transport, recovery


def mark_lost(transport, executions):
    current = executions.get("exec-1")
    return transport.mark_lost(
        "exec-1",
        expected_version=current.version,
        evidence_ref="transport:fake-disconnect",
    ).record


def test_normal_success_is_collectable_without_transport_failure(tmp_path: Path) -> None:
    _, _, executions, queued, fake, _, _ = harness(tmp_path, FaultScenario.NORMAL_SUCCESS)

    launch = fake.launch(queued.execution_id)
    collected = fake.collect("exec-1", expected_version=launch.record.version)

    assert launch.started is True
    assert launch.transport_lost is False
    assert fake.actual_start_count == 1
    assert collected.recovery_required is False
    assert collected.result is not None and collected.result.exit_code == 0
    assert executions.get("exec-1").execution_state is ExecutionProcessState.VERIFICATION_REQUIRED


def test_disconnect_before_launch_proves_never_started_without_guessing_unknown(tmp_path: Path) -> None:
    _, _, executions, queued, fake, _, _ = harness(tmp_path, FaultScenario.DISCONNECT_BEFORE_LAUNCH)

    launch = fake.launch(queued.execution_id)

    assert launch.transport_lost is True
    assert launch.started is False
    assert launch.never_started is True
    assert launch.process_state_unknown is False
    assert fake.actual_start_count == 0
    assert executions.get("exec-1").execution_state is ExecutionProcessState.QUEUED


def test_disconnect_after_launch_attaches_original_then_recovers_result_without_duplicate(tmp_path: Path) -> None:
    repo, jobs, executions, queued, fake, transport, recovery = harness(
        tmp_path, FaultScenario.DISCONNECT_AFTER_LAUNCH
    )
    claimed = jobs.get_job("job-1")
    launch = fake.launch(queued.execution_id)
    lost = mark_lost(transport, executions)

    duplicate = DuplicateExecutionGuard(store=executions).assess(fingerprint_spec(repo))
    assert duplicate.decision is DuplicateExecutionDecision.ATTACH_RUNNING
    assert fake.actual_start_count == 1
    assert jobs.get_job("job-1") == claimed

    fake.advance("exec-1")
    outcome = recovery.reconcile("exec-1", expected_version=lost.version)

    assert outcome.decision is RecoveryDecision.VERIFY_RESULT
    assert outcome.exit_code == 0
    assert fake.actual_start_count == 1
    assert jobs.get_job("job-1") == claimed


def test_disconnect_mid_command_preserves_partial_output_then_finishes_original(tmp_path: Path) -> None:
    repo, _, executions, queued, fake, transport, recovery = harness(
        tmp_path, FaultScenario.DISCONNECT_MID_COMMAND
    )
    launch = fake.launch(queued.execution_id)
    assert launch.started and launch.transport_lost
    stdout_path = repo / "runs" / "exec-1" / "stdout.log"
    assert b"partial" in stdout_path.read_bytes()
    lost = mark_lost(transport, executions)

    fake.advance("exec-1")
    outcome = recovery.reconcile("exec-1", expected_version=lost.version)

    assert outcome.decision is RecoveryDecision.VERIFY_RESULT
    assert b"completed" in stdout_path.read_bytes()
    assert fake.actual_start_count == 1


def test_disconnect_after_completion_recovers_existing_result_without_relaunch(tmp_path: Path) -> None:
    _, _, executions, queued, fake, transport, recovery = harness(
        tmp_path, FaultScenario.DISCONNECT_AFTER_COMPLETION
    )
    launch = fake.launch(queued.execution_id)
    assert launch.result_available is True
    assert launch.transport_lost is True
    lost = mark_lost(transport, executions)

    outcome = recovery.reconcile("exec-1", expected_version=lost.version)

    assert outcome.decision is RecoveryDecision.VERIFY_RESULT
    assert fake.actual_start_count == 1


def test_delayed_execution_requires_explicit_advance_not_sleep(tmp_path: Path) -> None:
    _, _, _, queued, fake, _, _ = harness(tmp_path, FaultScenario.DELAYED_SUCCESS)
    launch = fake.launch(queued.execution_id)

    assert launch.started is True and launch.process_running is True
    assert fake.inspect("exec-1").state.value == "SUPERVISOR_RUNNING"
    fake.advance("exec-1")
    assert fake.inspect("exec-1").state.value == "RESULT_AVAILABLE"
    assert fake.actual_start_count == 1


def test_nonzero_result_is_recovered_as_failure_review_not_automatic_retry(tmp_path: Path) -> None:
    _, _, executions, queued, fake, transport, recovery = harness(tmp_path, FaultScenario.NONZERO_EXIT)
    fake.launch(queued.execution_id)
    lost = mark_lost(transport, executions)

    outcome = recovery.reconcile("exec-1", expected_version=lost.version)

    assert outcome.decision is RecoveryDecision.REVIEW_FAILURE
    assert outcome.exit_code == 9
    assert outcome.retry_permitted is False
    assert fake.actual_start_count == 1


def test_malformed_result_becomes_recovery_required_without_second_launch(tmp_path: Path) -> None:
    _, _, executions, queued, fake, transport, recovery = harness(tmp_path, FaultScenario.MALFORMED_RESULT)
    fake.launch(queued.execution_id)
    lost = mark_lost(transport, executions)

    outcome = recovery.reconcile("exec-1", expected_version=lost.version)

    assert outcome.decision is RecoveryDecision.RECOVERY_REQUIRED
    assert outcome.retry_permitted is False
    assert fake.actual_start_count == 1


def test_unknown_process_state_is_distinct_from_never_started_and_requires_recovery(tmp_path: Path) -> None:
    _, _, executions, queued, fake, transport, recovery = harness(tmp_path, FaultScenario.UNKNOWN_PROCESS)
    launch = fake.launch(queued.execution_id)
    assert launch.started is True
    assert launch.never_started is False
    assert launch.process_state_unknown is True
    lost = mark_lost(transport, executions)

    outcome = recovery.reconcile("exec-1", expected_version=lost.version)

    assert outcome.decision is RecoveryDecision.RECOVERY_REQUIRED
    assert outcome.retry_permitted is False
    assert fake.actual_start_count == 1


def test_wrong_repo_identity_blocks_recovery_before_result_or_mutation(tmp_path: Path) -> None:
    repo, _, executions, queued, fake, transport, _ = harness(
        tmp_path, FaultScenario.DISCONNECT_AFTER_COMPLETION
    )
    fake.launch(queued.execution_id)
    lost = mark_lost(transport, executions)
    wrong = RecoveryReconciliationService(
        execution_store=executions,
        transport_service=transport,
        supervised_service=fake,
        repository_observer=ValidRepositoryObserver(root=repo, branch="wrong-branch"),
    )

    outcome = wrong.reconcile("exec-1", expected_version=lost.version)

    assert outcome.decision is RecoveryDecision.RECOVERY_BLOCKED
    assert outcome.reason_code == "RECOVERY_BRANCH_MISMATCH"
    assert fake.collect_count == 0
    assert fake.actual_start_count == 1


def test_large_stdout_remains_full_on_disk_while_artifact_response_is_bounded(tmp_path: Path) -> None:
    repo, _, executions, queued, fake, _, _ = harness(
        tmp_path, FaultScenario.LARGE_STDOUT, large_stdout_bytes=300_000
    )
    fake.launch(queued.execution_id)
    path = repo / "runs" / "exec-1" / "stdout.log"
    assert path.stat().st_size == 300_000

    artifact = ExecutionArtifactService(store=executions).read_tail(
        "exec-1", ExecutionArtifactKind.STDOUT, max_bytes=4096
    )

    assert artifact.total_bytes == 300_000
    assert artifact.returned_bytes <= 4096
    assert artifact.truncated is True
    assert fake.actual_start_count == 1


def test_fake_rejects_second_launch_of_same_started_execution(tmp_path: Path) -> None:
    _, _, _, queued, fake, _, _ = harness(tmp_path, FaultScenario.DISCONNECT_AFTER_LAUNCH)
    fake.launch(queued.execution_id)

    try:
        fake.launch(queued.execution_id)
    except RuntimeError as exc:
        assert str(exc) == "FAKE_EXECUTION_ALREADY_STARTED"
    else:
        raise AssertionError("duplicate fake launch was accepted")
    assert fake.actual_start_count == 1
