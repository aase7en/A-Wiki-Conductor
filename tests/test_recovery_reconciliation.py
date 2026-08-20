from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from a_conductor.domain import TaskState
from a_conductor.execution_record import (
    ExecutionProcessState,
    TransportState,
    new_execution_record,
)
from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.job_store import SQLiteJobStore
from a_conductor.native_execution import NativeCommandResult
from a_conductor.project_identity import GitReadResult
from a_conductor.recovery_reconciliation import (
    RecoveryDecision,
    RecoveryReconciliationService,
    RecoveryRepositoryObservation,
    StrictRecoveryRepositoryObserver,
)
from a_conductor.supervised_child import SupervisedChildResult
from a_conductor.supervised_execution import (
    SupervisedCollectOutcome,
    SupervisedInspection,
    SupervisedInspectionState,
)
from a_conductor.transport_recovery import ExecutionTransportService


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
    repo_root: Path,
    *,
    worker_id: str = "a-worker-01",
):
    repo_root.mkdir(parents=True, exist_ok=True)
    return store.create(
        new_execution_record(
            execution_id="exec-001",
            job_id="job-001",
            work_order_ref="docs/work-orders/WO-1.md",
            project_id="project-1",
            worker_id=worker_id,
            backend_id="serena-local",
            agent_ref="agent:chatgpt",
            repo_root=str(repo_root.resolve()),
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
            transport_state=TransportState.CONNECTED,
            execution_state=ExecutionProcessState.RUNNING,
        )
    )


class FakeRepositoryObserver:
    def __init__(self, observation: RecoveryRepositoryObservation) -> None:
        self.observation = observation
        self.calls = 0

    def observe(self, record):
        self.calls += 1
        return self.observation


class FakeSupervisedService:
    def __init__(
        self,
        store: SQLiteExecutionStore,
        *,
        inspection_state: SupervisedInspectionState,
        exit_code: int | None = None,
        collect_recovery: bool = False,
    ) -> None:
        self.store = store
        self.inspection_state = inspection_state
        self.exit_code = exit_code
        self.collect_recovery = collect_recovery
        self.inspect_calls = 0
        self.collect_calls = 0

    def inspect(self, execution_id: str) -> SupervisedInspection:
        self.inspect_calls += 1
        return SupervisedInspection(
            execution_id=execution_id,
            state=self.inspection_state,
            supervisor_pid=4242 if self.inspection_state is SupervisedInspectionState.SUPERVISOR_RUNNING else None,
            result_available=self.inspection_state is SupervisedInspectionState.RESULT_AVAILABLE,
            recovery_required=self.inspection_state in {
                SupervisedInspectionState.SUPERVISOR_EXITED_RESULT_MISSING,
                SupervisedInspectionState.RECOVERY_REQUIRED,
            },
            error_code=(
                "SUPERVISOR_EXITED_RESULT_MISSING"
                if self.inspection_state is SupervisedInspectionState.SUPERVISOR_EXITED_RESULT_MISSING
                else "SUPERVISOR_OWNERSHIP_UNKNOWN"
                if self.inspection_state is SupervisedInspectionState.RECOVERY_REQUIRED
                else None
            ),
        )

    def collect(self, execution_id: str, *, expected_version: int) -> SupervisedCollectOutcome:
        self.collect_calls += 1
        record = self.store.get(execution_id)
        assert record.version == expected_version
        if self.collect_recovery:
            recovered = self.store.set_execution_state(
                execution_id,
                ExecutionProcessState.RECOVERY_REQUIRED,
                expected_version=record.version,
                evidence_ref="runs/exec-001/result.json",
            )
            return SupervisedCollectOutcome(
                record=recovered,
                result=None,
                recovery_required=True,
                error_code="RESULT_MALFORMED",
            )
        assert self.exit_code is not None
        result = SupervisedChildResult(
            schema_version=1,
            execution_id=execution_id,
            child_pid=31337,
            exit_code=self.exit_code,
            started_at="2026-08-20T01:00:00Z",
            finished_at="2026-08-20T01:01:00Z",
        )
        with_process = self.store.set_process_metadata(
            execution_id,
            pid=result.child_pid,
            started_at=result.started_at,
            expected_version=record.version,
            evidence_ref="runs/exec-001/result.json",
        )
        with_result = self.store.set_result_metadata(
            execution_id,
            exit_code=result.exit_code,
            finished_at=result.finished_at,
            expected_version=with_process.version,
            evidence_ref="runs/exec-001/result.json",
        )
        final = self.store.set_execution_state(
            execution_id,
            ExecutionProcessState.VERIFICATION_REQUIRED if result.exit_code == 0 else ExecutionProcessState.FAILED,
            expected_version=with_result.version,
            evidence_ref="runs/exec-001/result.json",
        )
        return SupervisedCollectOutcome(
            record=final,
            result=result,
            recovery_required=False,
            error_code=None,
        )


def valid_repo_observation(repo_root: Path, *, dirty: bool = False):
    return RecoveryRepositoryObservation(
        repo_root=str(repo_root.resolve()),
        branch="main",
        head="a" * 40,
        dirty=dirty,
        error_code=None,
    )


def open_reconciler(
    tmp_path: Path,
    *,
    inspection_state: SupervisedInspectionState,
    exit_code: int | None = None,
    collect_recovery: bool = False,
    repo_observation: RecoveryRepositoryObservation | None = None,
    job_worker_id: str = "a-worker-01",
    execution_worker_id: str = "a-worker-01",
):
    database = tmp_path / "control.sqlite"
    jobs = SQLiteJobStore(database)
    executions = SQLiteExecutionStore(database)
    create_claimed_job(jobs, worker_id=job_worker_id)
    repo_root = tmp_path / "repo"
    running = create_execution(executions, repo_root, worker_id=execution_worker_id)
    transport = ExecutionTransportService(execution_store=executions, job_store=jobs)
    if job_worker_id == execution_worker_id:
        lost = transport.mark_lost(
            "exec-001",
            expected_version=running.version,
            evidence_ref="transport:http-502",
        )
        lost_record = lost.record
    else:
        # Build an already-lost durable state directly so reconnect recovery
        # can prove it re-checks ownership before repo/process inspection.
        lost_record = executions.set_transport_state(
            "exec-001",
            TransportState.LOST,
            expected_version=running.version,
            evidence_ref="transport:http-502",
        )
    observer = FakeRepositoryObserver(repo_observation or valid_repo_observation(repo_root))
    supervised = FakeSupervisedService(
        executions,
        inspection_state=inspection_state,
        exit_code=exit_code,
        collect_recovery=collect_recovery,
    )
    service = RecoveryReconciliationService(
        execution_store=executions,
        transport_service=transport,
        supervised_service=supervised,
        repository_observer=observer,
    )
    return jobs, executions, lost_record, observer, supervised, service, repo_root


def test_running_original_is_monitored_without_relaunch_and_claim_is_preserved(tmp_path: Path) -> None:
    jobs, executions, lost, _, supervised, service, _ = open_reconciler(
        tmp_path,
        inspection_state=SupervisedInspectionState.SUPERVISOR_RUNNING,
    )
    claimed_before = jobs.get_job("job-001")

    outcome = service.reconcile(
        "exec-001",
        expected_version=lost.version,
        transport_evidence_ref="transport:reconnected",
    )

    assert outcome.decision is RecoveryDecision.MONITOR_ORIGINAL
    assert outcome.record.transport_state is TransportState.CONNECTED
    assert outcome.record.execution_state is ExecutionProcessState.PROCESS_STILL_RUNNING
    assert outcome.supervisor_pid == 4242
    assert outcome.retry_permitted is False
    assert supervised.collect_calls == 0
    assert jobs.get_job("job-001") == claimed_before


def test_completed_exit_zero_collects_original_and_requests_verification(tmp_path: Path) -> None:
    _, executions, lost, _, supervised, service, _ = open_reconciler(
        tmp_path,
        inspection_state=SupervisedInspectionState.RESULT_AVAILABLE,
        exit_code=0,
    )

    outcome = service.reconcile("exec-001", expected_version=lost.version)

    assert outcome.decision is RecoveryDecision.VERIFY_RESULT
    assert outcome.record.execution_state is ExecutionProcessState.VERIFICATION_REQUIRED
    assert outcome.exit_code == 0
    assert outcome.retry_permitted is False
    assert supervised.collect_calls == 1
    assert executions.get("exec-001").exit_code == 0


def test_completed_nonzero_collects_original_and_routes_to_failure_review(tmp_path: Path) -> None:
    _, _, lost, _, _, service, _ = open_reconciler(
        tmp_path,
        inspection_state=SupervisedInspectionState.RESULT_AVAILABLE,
        exit_code=7,
    )

    outcome = service.reconcile("exec-001", expected_version=lost.version)

    assert outcome.decision is RecoveryDecision.REVIEW_FAILURE
    assert outcome.record.execution_state is ExecutionProcessState.FAILED
    assert outcome.exit_code == 7
    assert outcome.retry_permitted is False


def test_missing_result_after_supervisor_exit_becomes_recovery_required_without_retry(tmp_path: Path) -> None:
    _, executions, lost, _, supervised, service, _ = open_reconciler(
        tmp_path,
        inspection_state=SupervisedInspectionState.SUPERVISOR_EXITED_RESULT_MISSING,
    )

    outcome = service.reconcile("exec-001", expected_version=lost.version)

    assert outcome.decision is RecoveryDecision.RECOVERY_REQUIRED
    assert outcome.retry_permitted is False
    assert outcome.record.execution_state is ExecutionProcessState.RECOVERY_REQUIRED
    assert supervised.collect_calls == 0
    assert executions.get("exec-001").execution_state is ExecutionProcessState.RECOVERY_REQUIRED


def test_malformed_result_becomes_recovery_required_without_retry(tmp_path: Path) -> None:
    _, _, lost, _, supervised, service, _ = open_reconciler(
        tmp_path,
        inspection_state=SupervisedInspectionState.RESULT_AVAILABLE,
        collect_recovery=True,
    )

    outcome = service.reconcile("exec-001", expected_version=lost.version)

    assert outcome.decision is RecoveryDecision.RECOVERY_REQUIRED
    assert outcome.reason_code == "RESULT_MALFORMED"
    assert outcome.retry_permitted is False
    assert supervised.collect_calls == 1


def test_repository_root_mismatch_blocks_before_process_inspection(tmp_path: Path) -> None:
    bad = RecoveryRepositoryObservation(
        repo_root=str((tmp_path / "wrong").resolve()),
        branch="main",
        head="a" * 40,
        dirty=False,
        error_code=None,
    )
    _, _, lost, _, supervised, service, _ = open_reconciler(
        tmp_path,
        inspection_state=SupervisedInspectionState.SUPERVISOR_RUNNING,
        repo_observation=bad,
    )

    outcome = service.reconcile("exec-001", expected_version=lost.version)

    assert outcome.decision is RecoveryDecision.RECOVERY_BLOCKED
    assert outcome.reason_code == "RECOVERY_REPO_ROOT_MISMATCH"
    assert supervised.inspect_calls == 0
    assert outcome.retry_permitted is False


def test_branch_or_head_mismatch_blocks_before_process_inspection(tmp_path: Path) -> None:
    for branch, head, code in (
        ("other", "a" * 40, "RECOVERY_BRANCH_MISMATCH"),
        ("main", "c" * 40, "RECOVERY_HEAD_MISMATCH"),
    ):
        case = tmp_path / code
        observation = RecoveryRepositoryObservation(
            repo_root=str((case / "repo").resolve()),
            branch=branch,
            head=head,
            dirty=False,
            error_code=None,
        )
        _, _, lost, _, supervised, service, _ = open_reconciler(
            case,
            inspection_state=SupervisedInspectionState.SUPERVISOR_RUNNING,
            repo_observation=observation,
        )
        outcome = service.reconcile("exec-001", expected_version=lost.version)
        assert outcome.decision is RecoveryDecision.RECOVERY_BLOCKED
        assert outcome.reason_code == code
        assert supervised.inspect_calls == 0


def test_dirty_worktree_after_successful_collection_blocks_automatic_continuation(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    observation = valid_repo_observation(repo_root, dirty=True)
    _, _, lost, _, supervised, service, _ = open_reconciler(
        tmp_path,
        inspection_state=SupervisedInspectionState.RESULT_AVAILABLE,
        exit_code=0,
        repo_observation=observation,
    )

    outcome = service.reconcile("exec-001", expected_version=lost.version)

    assert supervised.collect_calls == 1
    assert outcome.record.execution_state is ExecutionProcessState.VERIFICATION_REQUIRED
    assert outcome.decision is RecoveryDecision.RECOVERY_BLOCKED
    assert outcome.reason_code == "RECOVERY_DIRTY_WORKTREE"
    assert outcome.retry_permitted is False


def test_worker_ownership_mismatch_blocks_before_repo_or_process_inspection(tmp_path: Path) -> None:
    _, _, lost, observer, supervised, service, _ = open_reconciler(
        tmp_path,
        inspection_state=SupervisedInspectionState.SUPERVISOR_RUNNING,
        job_worker_id="a-worker-02",
        execution_worker_id="a-worker-01",
    )

    outcome = service.reconcile("exec-001", expected_version=lost.version)

    assert outcome.decision is RecoveryDecision.RECOVERY_BLOCKED
    assert outcome.reason_code == "TRANSPORT_OWNERSHIP_MISMATCH"
    assert observer.calls == 0
    assert supervised.inspect_calls == 0


def test_reconciler_exposes_no_retry_relaunch_or_repo_mutation_surface(tmp_path: Path) -> None:
    _, _, _, _, _, service, _ = open_reconciler(
        tmp_path,
        inspection_state=SupervisedInspectionState.SUPERVISOR_RUNNING,
    )
    for forbidden in (
        "retry",
        "relaunch",
        "launch",
        "reset",
        "clean",
        "stash",
        "checkout",
        "switch",
        "commit",
        "push",
        "failover",
    ):
        assert not hasattr(service, forbidden)


class FakeGitRunner:
    def __init__(self, root: Path, *, branch: str = "main", head: str = "a" * 40) -> None:
        self.root = root
        self.branch_name = branch
        self.head_sha = head

    def show_toplevel(self, worktree: Path) -> GitReadResult:
        return GitReadResult(True, str(self.root.resolve()), "")

    def branch(self, worktree: Path) -> GitReadResult:
        return GitReadResult(True, self.branch_name, "")

    def head(self, worktree: Path) -> GitReadResult:
        return GitReadResult(True, self.head_sha, "")

    def is_ancestor(self, worktree: Path, ancestor: str) -> GitReadResult:
        return GitReadResult(True, "", "")


class FakeStatusAdapter:
    def __init__(self, stdout: str = "") -> None:
        self.stdout = stdout

    def status_short(self, *, timeout_seconds: int = 10) -> NativeCommandResult:
        return NativeCommandResult(
            executable="git",
            argument_count=3,
            exit_code=0,
            timed_out=False,
            stdout=self.stdout,
            stderr="",
            stdout_sha256="d" * 64,
            stderr_sha256="e" * 64,
            stdout_truncated=False,
            stderr_truncated=False,
        )


def test_strict_repository_observer_reuses_read_only_git_identity_and_status(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    record = new_execution_record(
        execution_id="exec-observe",
        job_id="job-observe",
        work_order_ref="wo",
        project_id="project",
        worker_id="worker",
        backend_id="backend",
        agent_ref=None,
        repo_root=str(repo.resolve()),
        branch="main",
        head_before="a" * 40,
        operation_ref="op:status",
        command_fingerprint="f" * 64,
        command_summary="observe repo",
        runtime_profile_ref=None,
        run_dir_ref=None,
        stdout_ref=None,
        stderr_ref=None,
        result_ref=None,
        report_ref=None,
        transport_state=TransportState.CONNECTED,
        execution_state=ExecutionProcessState.RUNNING,
    )
    observer = StrictRecoveryRepositoryObserver(
        git_runner=FakeGitRunner(repo),
        status_adapter_factory=lambda scope: FakeStatusAdapter(" M tracked.txt\n"),
    )

    observation = observer.observe(record)

    assert observation.error_code is None
    assert Path(observation.repo_root).resolve() == repo.resolve()
    assert observation.branch == "main"
    assert observation.head == "a" * 40
    assert observation.dirty is True
