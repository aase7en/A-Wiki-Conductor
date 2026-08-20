from __future__ import annotations

from pathlib import Path

from a_conductor.domain import TaskState
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
from a_conductor.fault_injection import DeterministicFaultExecutor, FaultScenario
from a_conductor.job_store import SQLiteJobStore
from a_conductor.recovery_reconciliation import (
    RecoveryDecision,
    RecoveryReconciliationService,
    RecoveryRepositoryObservation,
)
from a_conductor.serena_runtime import ProjectIdentityPolicy, SerenaProjectBinding
from a_conductor.serena_transport_adapter import (
    SerenaProjectBindingRepositoryObserver,
    SerenaTransportAdapter,
    SerenaTransportEvent,
    SerenaTransportEventKind,
    classify_serena_transport_events,
)
from a_conductor.transport_recovery import ExecutionTransportService


class FactsRepositoryObserver:
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
        backend_id="serena-local",
        repo_root=str(repo.resolve()),
        branch="main",
        head_before="a" * 40,
        operation_ref="op:serena-adapter-test",
        runtime_profile_ref="runtime:serena",
        target_argv=("serena-agent.exe", "--mcp-serve"),
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
            command_summary="serena adapter test",
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


def harness(tmp_path: Path, scenario: FaultScenario = FaultScenario.DISCONNECT_AFTER_LAUNCH):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    database = tmp_path / "control.sqlite"
    jobs = SQLiteJobStore(database)
    executions = SQLiteExecutionStore(database)
    create_claimed_job(jobs)
    queued = create_execution(executions, repo)
    fake = DeterministicFaultExecutor(store=executions, scenario=scenario)
    transport = ExecutionTransportService(execution_store=executions, job_store=jobs)
    adapter = SerenaTransportAdapter(transport_service=transport)
    return repo, jobs, executions, queued, fake, transport, adapter


def binding_for(repo: Path, *, branch: str | None = "main", head: str | None = "a" * 40) -> SerenaProjectBinding:
    return SerenaProjectBinding(
        project_id="project-1",
        worktree_path=str(repo.resolve()),
        identity_policy=ProjectIdentityPolicy.EXACT,
        expected_branch=branch,
        expected_head=head,
        mutation_allowed=False,
    )


def test_single_mcp_502_degrades_transport_only(tmp_path: Path) -> None:
    repo, jobs, executions, queued, fake, _, adapter = harness(tmp_path)
    fake.launch(queued.execution_id)
    version = executions.get("exec-1").version

    outcome = adapter.apply(
        "exec-1",
        [SerenaTransportEvent(SerenaTransportEventKind.MCP_HTTP_502)],
        expected_version=version,
    )

    record = executions.get("exec-1")
    assert outcome is not None and outcome.changed is True
    assert record.transport_state is TransportState.DEGRADED
    assert record.execution_state is ExecutionProcessState.RUNNING
    assert jobs.get_job("job-1").worker_id == "a-worker-01"


def test_repeated_mcp_502_marks_lost(tmp_path: Path) -> None:
    repo, _, executions, queued, fake, _, adapter = harness(tmp_path)
    fake.launch(queued.execution_id)
    version = executions.get("exec-1").version

    outcome = adapter.apply(
        "exec-1",
        [
            SerenaTransportEvent(SerenaTransportEventKind.MCP_HTTP_502),
            SerenaTransportEvent(SerenaTransportEventKind.MCP_HTTP_502),
        ],
        expected_version=version,
    )

    assert outcome is not None and outcome.changed is True
    assert executions.get("exec-1").transport_state is TransportState.LOST


def test_connector_session_terminated_is_immediately_lost(tmp_path: Path) -> None:
    repo, _, executions, queued, fake, _, adapter = harness(tmp_path)
    fake.launch(queued.execution_id)
    version = executions.get("exec-1").version

    outcome = adapter.apply(
        "exec-1",
        [SerenaTransportEvent(SerenaTransportEventKind.CONNECTOR_SESSION_TERMINATED)],
        expected_version=version,
    )

    assert outcome is not None and outcome.changed is True
    assert executions.get("exec-1").transport_state is TransportState.LOST


def test_probe_failures_degrade_then_unavailable(tmp_path: Path) -> None:
    assert (
        classify_serena_transport_events(
            [SerenaTransportEvent(SerenaTransportEventKind.HEALTH_PROBE_TIMEOUT)]
        ).target_state
        is TransportState.DEGRADED
    )
    assert (
        classify_serena_transport_events(
            [
                SerenaTransportEvent(SerenaTransportEventKind.HEALTH_PROBE_TIMEOUT),
                SerenaTransportEvent(SerenaTransportEventKind.HEALTH_PROBE_REFUSED),
            ]
        ).target_state
        is TransportState.UNAVAILABLE
    )


def test_healthy_event_reconnects_transport_without_touching_execution(tmp_path: Path) -> None:
    repo, jobs, executions, queued, fake, _, adapter = harness(tmp_path)
    fake.launch(queued.execution_id)
    version = executions.get("exec-1").version
    adapter.apply(
        "exec-1",
        [SerenaTransportEvent(SerenaTransportEventKind.MCP_HTTP_502)],
        expected_version=version,
    )

    degraded = executions.get("exec-1")
    outcome = adapter.apply(
        "exec-1",
        [SerenaTransportEvent(SerenaTransportEventKind.MCP_OK)],
        expected_version=degraded.version,
    )

    record = executions.get("exec-1")
    assert outcome is not None and outcome.changed is True
    assert record.transport_state is TransportState.CONNECTED
    assert record.execution_state is ExecutionProcessState.RUNNING
    assert jobs.get_job("job-1").worker_id == "a-worker-01"


def test_transport_loss_never_mutates_execution_state_or_job_claim(tmp_path: Path) -> None:
    repo, jobs, executions, queued, fake, _, adapter = harness(tmp_path)
    fake.launch(queued.execution_id)
    version = executions.get("exec-1").version

    adapter.apply(
        "exec-1",
        [SerenaTransportEvent(SerenaTransportEventKind.CONNECTOR_SESSION_TERMINATED)],
        expected_version=version,
    )

    record = executions.get("exec-1")
    assert record.transport_state is TransportState.LOST
    assert record.execution_state is ExecutionProcessState.RUNNING
    assert jobs.get_job("job-1").worker_id == "a-worker-01"


def test_empty_window_is_no_mutation(tmp_path: Path) -> None:
    repo, _, executions, queued, fake, _, adapter = harness(tmp_path)
    fake.launch(queued.execution_id)
    version = executions.get("exec-1").version

    assert adapter.apply("exec-1", [], expected_version=version) is None


def test_binding_observer_passes_matching_identity(tmp_path: Path) -> None:
    repo, _, executions, queued, _, _, _ = harness(tmp_path)
    observer = SerenaProjectBindingRepositoryObserver(
        binding=binding_for(repo),
        inner=FactsRepositoryObserver(root=repo),
    )

    observation = observer.observe(executions.get("exec-1"))

    assert observation.error_code is None
    assert observation.branch == "main"
    assert observation.head == "a" * 40


def test_binding_observer_blocks_branch_mismatch(tmp_path: Path) -> None:
    repo, _, executions, _, _, _, _ = harness(tmp_path)
    observer = SerenaProjectBindingRepositoryObserver(
        binding=binding_for(repo, branch="feature/other"),
        inner=FactsRepositoryObserver(root=repo),
    )

    observation = observer.observe(executions.get("exec-1"))

    assert observation.error_code == "SERENA_BINDING_IDENTITY_MISMATCH"


def test_binding_observer_blocks_head_mismatch(tmp_path: Path) -> None:
    repo, _, executions, _, _, _, _ = harness(tmp_path)
    observer = SerenaProjectBindingRepositoryObserver(
        binding=binding_for(repo, head="b" * 40),
        inner=FactsRepositoryObserver(root=repo),
    )

    observation = observer.observe(executions.get("exec-1"))

    assert observation.error_code == "SERENA_BINDING_IDENTITY_MISMATCH"


def test_binding_observer_blocks_worktree_mismatch(tmp_path: Path) -> None:
    repo, _, executions, _, _, _, _ = harness(tmp_path)
    other = repo.parent / "other-worktree"
    observer = SerenaProjectBindingRepositoryObserver(
        binding=binding_for(other),
        inner=FactsRepositoryObserver(root=repo),
    )

    observation = observer.observe(executions.get("exec-1"))

    assert observation.error_code == "SERENA_BINDING_WORKTREE_MISMATCH"


def test_non_exact_policy_skips_binding_enforcement(tmp_path: Path) -> None:
    repo, _, executions, _, _, _, _ = harness(tmp_path)
    observer = SerenaProjectBindingRepositoryObserver(
        binding=SerenaProjectBinding(
            project_id="project-1",
            worktree_path=str(repo.resolve()),
            identity_policy=ProjectIdentityPolicy.READ_ONLY_DISCOVERY,
            expected_branch="feature/other",
            expected_head="b" * 40,
        ),
        inner=FactsRepositoryObserver(root=repo),
    )

    observation = observer.observe(executions.get("exec-1"))

    assert observation.error_code is None


def test_integrated_adapter_recovery_recovers_without_relaunch(tmp_path: Path) -> None:
    repo, jobs, executions, queued, fake, transport, adapter = harness(tmp_path)
    claimed = jobs.get_job("job-1")
    fake.launch(queued.execution_id)
    version = executions.get("exec-1").version

    lost = adapter.apply(
        "exec-1",
        [SerenaTransportEvent(SerenaTransportEventKind.CONNECTOR_SESSION_TERMINATED)],
        expected_version=version,
    )
    assert lost is not None and executions.get("exec-1").transport_state is TransportState.LOST

    duplicate = DuplicateExecutionGuard(store=executions).assess(fingerprint_spec(repo))
    assert duplicate.decision is DuplicateExecutionDecision.ATTACH_RUNNING
    assert fake.actual_start_count == 1

    fake.advance("exec-1")
    recovery = RecoveryReconciliationService(
        execution_store=executions,
        transport_service=transport,
        supervised_service=fake,
        repository_observer=SerenaProjectBindingRepositoryObserver(
            binding=binding_for(repo),
            inner=FactsRepositoryObserver(root=repo),
        ),
    )
    outcome = recovery.reconcile("exec-1", expected_version=lost.record.version)

    assert outcome.decision is RecoveryDecision.VERIFY_RESULT
    assert outcome.exit_code == 0
    assert fake.actual_start_count == 1
    assert jobs.get_job("job-1") == claimed


def test_integrated_binding_mismatch_blocks_recovery_before_collect(tmp_path: Path) -> None:
    repo, _, executions, queued, fake, transport, adapter = harness(tmp_path)
    fake.launch(queued.execution_id)
    version = executions.get("exec-1").version

    lost = adapter.apply(
        "exec-1",
        [SerenaTransportEvent(SerenaTransportEventKind.CONNECTOR_SESSION_TERMINATED)],
        expected_version=version,
    )
    assert lost is not None

    recovery = RecoveryReconciliationService(
        execution_store=executions,
        transport_service=transport,
        supervised_service=fake,
        repository_observer=SerenaProjectBindingRepositoryObserver(
            binding=binding_for(repo, branch="feature/other"),
            inner=FactsRepositoryObserver(root=repo),
        ),
    )
    outcome = recovery.reconcile("exec-1", expected_version=lost.record.version)

    assert outcome.decision is RecoveryDecision.RECOVERY_BLOCKED
    assert outcome.reason_code == "SERENA_BINDING_IDENTITY_MISMATCH"
    assert fake.collect_count == 0
    assert fake.actual_start_count == 1


def test_adapter_rejects_invalid_thresholds_and_events(tmp_path: Path) -> None:
    repo, _, _, _, _, transport, _ = harness(tmp_path)
    try:
        SerenaTransportAdapter(transport_service=transport, lost_after=0)
    except ValueError:
        pass
    else:
        raise AssertionError("lost_after=0 was accepted")
    adapter = SerenaTransportAdapter(transport_service=transport)
    try:
        SerenaTransportEvent("not-a-kind")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid event kind was accepted")
