from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from a_conductor.domain import RecoveryClassification, TaskState
from a_conductor.execution_artifacts import ExecutionArtifactKind, ExecutionArtifactService
from a_conductor.execution_deduplication import (
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
from a_conductor.graph.barriers import FanInChildObservation, evaluate_fan_in_barrier
from a_conductor.graph.dispatch import (
    DispatchGateDecision, GraphDispatchAction, GraphDispatchCoordinator,
    GraphDispatchKey, GraphDispatchMode, GraphDispatchRequest,
    StaticWorkerDispatchModeResolver,
)
from a_conductor.graph.domain import TaskEdge, TaskNode, TaskNodeStatus
from a_conductor.graph.graph import build_graph
from a_conductor.graph.lifecycle_bridge import project_graph_node_states
from a_conductor.graph.ready import compute_ready_set
from a_conductor.graph.scheduler import SelectedAssignment
from a_conductor.job_control import DurableJobControlService
from a_conductor.job_store import SQLiteJobStore
from a_conductor.native_execution import NativeCommandResult
from a_conductor.native_operations import NativeOperationDefinition, NativeOperationKind, WorkerNativeAdapters
from a_conductor.recovery_reconciliation import (
    RecoveryDecision,
    RecoveryReconciliationService,
    RecoveryRepositoryObservation,
)
from a_conductor.transport_recovery import ExecutionTransportService

class RepoObserver:
    def __init__(self, root: Path, *, branch: str = "main") -> None:
        self.root = root
        self.branch = branch

    def observe(self, record):
        return RecoveryRepositoryObservation(
            repo_root=str(self.root.resolve()),
            branch=self.branch,
            head="a" * 40,
            dirty=False,
            error_code=None,
        )


@dataclass
class ChaosHarness:
    graph_id: str
    run_id: str
    node_id: str
    graph: object
    key: GraphDispatchKey
    repo: Path
    jobs: SQLiteJobStore
    executions: SQLiteExecutionStore
    queued: object
    fake: DeterministicFaultExecutor
    transport: ExecutionTransportService
    recovery: RecoveryReconciliationService

    def graph_state(self) -> TaskNodeStatus:
        return project_graph_node_states(
            self.graph, self.graph_id, self.run_id, self.jobs
        )[self.node_id]

def _fingerprint(repo: Path, job_id: str) -> ExecutionFingerprintSpec:
    return ExecutionFingerprintSpec(
        project_id="project-1",
        job_id=job_id,
        work_order_ref="wo:ge10",
        backend_id="fake-local",
        repo_root=str(repo.resolve()),
        branch="main",
        head_before="a" * 40,
        operation_ref="op:graph-chaos",
        runtime_profile_ref="runtime:fake",
        target_argv=("fake-target.exe", "--scenario"),
    )


def _claimed_job(store: SQLiteJobStore, job_id: str):
    state = store.create_job(
        job_id=job_id,
        work_order_ref="wo:ge10",
        project_id="project-1",
    )
    state = store.transition(job_id, TaskState.READY, expected_version=state.version)
    return store.transition(
        job_id,
        TaskState.CLAIMED,
        expected_version=state.version,
        worker_id="a-worker-01",
    )


def _execution(store: SQLiteExecutionStore, repo: Path, job_id: str):
    spec = _fingerprint(repo, job_id)
    return store.create(
        new_execution_record(
            execution_id="exec-1",
            job_id=job_id,
            work_order_ref=spec.work_order_ref,
            project_id=spec.project_id,
            worker_id="a-worker-01",
            backend_id=spec.backend_id,
            agent_ref="agent:ge10",
            repo_root=spec.repo_root,
            branch=spec.branch,
            head_before=spec.head_before,
            operation_ref=spec.operation_ref,            command_fingerprint=compute_execution_fingerprint(spec),
            command_summary="graph chaos",
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


def _harness(
    tmp_path: Path,
    scenario: FaultScenario,
    *,
    observer_branch: str = "main",
    large_stdout_bytes: int = 300_000,
) -> ChaosHarness:
    graph_id, run_id, node_id = "graph-chaos", "run-1", "child"
    graph = build_graph([TaskNode(id=node_id, objective="chaos child")], [])
    key = GraphDispatchKey(graph_id, run_id, node_id)
    repo = tmp_path / "repo"
    repo.mkdir()
    database = tmp_path / "control.sqlite"
    jobs = SQLiteJobStore(database)
    executions = SQLiteExecutionStore(database)
    _claimed_job(jobs, key.job_id)
    queued = _execution(executions, repo, key.job_id)
    fake = DeterministicFaultExecutor(
        store=executions,
        scenario=scenario,
        large_stdout_bytes=large_stdout_bytes,
    )
    transport = ExecutionTransportService(
        execution_store=executions,
        job_store=jobs,
    )
    recovery = RecoveryReconciliationService(
        execution_store=executions,
        transport_service=transport,
        supervised_service=fake,
        repository_observer=RepoObserver(repo, branch=observer_branch),
    )
    return ChaosHarness(
        graph_id=graph_id,
        run_id=run_id,
        node_id=node_id,
        graph=graph,
        key=key,
        repo=repo,
        jobs=jobs,
        executions=executions,
        queued=queued,
        fake=fake,
        transport=transport,
        recovery=recovery,
    )


def _mark_lost(harness: ChaosHarness):
    current = harness.executions.get("exec-1")
    return harness.transport.mark_lost(
        "exec-1",
        expected_version=current.version,
        evidence_ref="transport:graph-chaos",
    ).record


def _reconcile_after_loss(harness: ChaosHarness):
    lost = _mark_lost(harness)
    return harness.recovery.reconcile("exec-1", expected_version=lost.version)

def test_chaos_01_normal_success_does_not_skip_lifecycle_authority(tmp_path: Path) -> None:
    h = _harness(tmp_path, FaultScenario.NORMAL_SUCCESS)
    launch = h.fake.launch("exec-1")
    collected = h.fake.collect("exec-1", expected_version=launch.record.version)
    assert collected.result is not None and collected.result.exit_code == 0
    assert h.fake.actual_start_count == 1
    assert h.graph_state() is TaskNodeStatus.DOING


def test_chaos_02_disconnect_before_launch_never_marks_graph_done(tmp_path: Path) -> None:
    h = _harness(tmp_path, FaultScenario.DISCONNECT_BEFORE_LAUNCH)
    launch = h.fake.launch("exec-1")
    assert launch.never_started and not launch.started
    assert h.fake.actual_start_count == 0
    assert h.graph_state() is TaskNodeStatus.DOING


def test_chaos_03_disconnect_after_launch_monitors_original_once(tmp_path: Path) -> None:
    h = _harness(tmp_path, FaultScenario.DISCONNECT_AFTER_LAUNCH)
    launch = h.fake.launch("exec-1")
    assert launch.transport_lost and launch.process_running
    outcome = _reconcile_after_loss(h)
    assert outcome.decision is RecoveryDecision.MONITOR_ORIGINAL
    assert h.fake.actual_start_count == 1
    assert h.graph_state() is TaskNodeStatus.DOING

def test_chaos_04_disconnect_mid_command_recovers_original_result(tmp_path: Path) -> None:
    h = _harness(tmp_path, FaultScenario.DISCONNECT_MID_COMMAND)
    launch = h.fake.launch("exec-1")
    assert launch.transport_lost
    stdout = h.repo / "runs" / "exec-1" / "stdout.log"
    assert b"partial-output" in stdout.read_bytes()
    lost = _mark_lost(h)
    h.fake.advance("exec-1")
    outcome = h.recovery.reconcile("exec-1", expected_version=lost.version)
    assert outcome.decision is RecoveryDecision.VERIFY_RESULT
    assert b"completed-output" in stdout.read_bytes()
    assert h.fake.actual_start_count == 1
    assert h.graph_state() is TaskNodeStatus.DOING


def test_chaos_05_disconnect_after_completion_recovers_without_relaunch(tmp_path: Path) -> None:
    h = _harness(tmp_path, FaultScenario.DISCONNECT_AFTER_COMPLETION)
    launch = h.fake.launch("exec-1")
    assert launch.result_available and launch.transport_lost
    outcome = _reconcile_after_loss(h)
    assert outcome.decision is RecoveryDecision.VERIFY_RESULT
    assert h.fake.actual_start_count == 1
    assert h.graph_state() is TaskNodeStatus.DOING


def test_chaos_06_delayed_success_requires_explicit_advance(tmp_path: Path) -> None:
    h = _harness(tmp_path, FaultScenario.DELAYED_SUCCESS)
    launch = h.fake.launch("exec-1")
    assert launch.process_running and not launch.result_available
    h.fake.advance("exec-1")
    inspection = h.fake.inspect("exec-1")
    assert inspection.result_available
    assert h.fake.actual_start_count == 1
    assert h.graph_state() is TaskNodeStatus.DOING

def test_chaos_07_large_stdout_stays_durable_and_bounded(tmp_path: Path) -> None:
    h = _harness(tmp_path, FaultScenario.LARGE_STDOUT)
    h.fake.launch("exec-1")
    path = h.repo / "runs" / "exec-1" / "stdout.log"
    assert path.stat().st_size == 300_000
    artifact = ExecutionArtifactService(store=h.executions).read_tail(
        "exec-1", ExecutionArtifactKind.STDOUT, max_bytes=4096
    )
    assert artifact.total_bytes == 300_000
    assert artifact.returned_bytes <= 4096 and artifact.truncated
    assert h.graph_state() is TaskNodeStatus.DOING


def test_chaos_08_nonzero_exit_requires_review_not_retry(tmp_path: Path) -> None:
    h = _harness(tmp_path, FaultScenario.NONZERO_EXIT)
    h.fake.launch("exec-1")
    outcome = _reconcile_after_loss(h)
    assert outcome.decision is RecoveryDecision.REVIEW_FAILURE
    assert outcome.exit_code == 9 and not outcome.retry_permitted
    assert h.fake.actual_start_count == 1
    assert h.graph_state() is TaskNodeStatus.DOING


def test_chaos_09_malformed_result_requires_recovery_without_retry(tmp_path: Path) -> None:
    h = _harness(tmp_path, FaultScenario.MALFORMED_RESULT)
    h.fake.launch("exec-1")
    outcome = _reconcile_after_loss(h)
    assert outcome.decision is RecoveryDecision.RECOVERY_REQUIRED
    assert not outcome.retry_permitted
    assert h.fake.actual_start_count == 1
    assert h.graph_state() is TaskNodeStatus.DOING

def test_chaos_10_unknown_process_requires_recovery_without_blind_retry(tmp_path: Path) -> None:
    h = _harness(tmp_path, FaultScenario.UNKNOWN_PROCESS)
    launch = h.fake.launch("exec-1")
    assert launch.process_state_unknown
    outcome = _reconcile_after_loss(h)
    assert outcome.decision is RecoveryDecision.RECOVERY_REQUIRED
    assert not outcome.retry_permitted
    assert h.fake.actual_start_count == 1
    assert h.graph_state() is TaskNodeStatus.DOING


def test_chaos_11_wrong_repo_identity_blocks_recovery_and_graph_progress(tmp_path: Path) -> None:
    h = _harness(
        tmp_path,
        FaultScenario.DISCONNECT_AFTER_COMPLETION,
        observer_branch="wrong-branch",
    )
    h.fake.launch("exec-1")
    outcome = _reconcile_after_loss(h)
    assert outcome.decision is RecoveryDecision.RECOVERY_BLOCKED
    assert outcome.reason_code == "RECOVERY_BRANCH_MISMATCH"
    assert h.fake.collect_count == 0
    assert h.graph_state() is TaskNodeStatus.DOING


def test_chaos_12_durable_reopen_prevents_same_key_replay(tmp_path: Path) -> None:
    class Verification:
        def __init__(self) -> None:
            self.calls = 0

        def pytest(self, paths=("tests",), *, timeout_seconds=120):
            self.calls += 1
            return NativeCommandResult(
                executable="python.exe", argument_count=3, exit_code=0, timed_out=False,
                stdout="ok", stderr="", stdout_sha256="a" * 64, stderr_sha256="b" * 64,
                stdout_truncated=False, stderr_truncated=False,
            )

        def compileall(self, paths=("src",), *, timeout_seconds=120):
            return self.pytest(paths, timeout_seconds=timeout_seconds)

    class Resolver:
        def __init__(self) -> None:
            self.verification = Verification()

        def resolve(self, worker_id: str):
            return WorkerNativeAdapters(git=object(), verification=self.verification)

    database = tmp_path / "replay.sqlite"
    operation = NativeOperationDefinition(
        operation_ref="op:graph-chaos",
        kind=NativeOperationKind.PYTEST,
        paths=("tests/test_graph_chaos.py",),
        timeout_seconds=30,
    )
    resolver1 = Resolver()
    service1 = DurableJobControlService.open(
        database, operations=(operation,), native_resolver=resolver1
    )
    request = GraphDispatchRequest(
        key=GraphDispatchKey("graph-chaos", "run-replay", "node-1"),
        assignment=SelectedAssignment(node_id="node-1", worker_id="a-worker-01", priority=3),
        project_id="project-1", work_order_ref="wo:ge10",
        operation_ref="op:graph-chaos", dispatch_mode=GraphDispatchMode.PROGRAMMATIC_PUSH,
    )
    modes = StaticWorkerDispatchModeResolver(
        {"a-worker-01": GraphDispatchMode.PROGRAMMATIC_PUSH}
    )
    first = GraphDispatchCoordinator(service=service1, mode_resolver=modes).dispatch(
        request, gate=DispatchGateDecision.allow()
    )
    assert first.action is GraphDispatchAction.EXECUTED
    assert resolver1.verification.calls == 1

    resolver2 = Resolver()
    service2 = DurableJobControlService.open(
        database, operations=(operation,), native_resolver=resolver2
    )
    second = GraphDispatchCoordinator(service=service2, mode_resolver=modes).dispatch(
        request, gate=DispatchGateDecision.allow()
    )
    assert second.action is GraphDispatchAction.EXISTING
    assert second.job.job_id == first.job.job_id
    assert resolver2.verification.calls == 0

def _advance(store: SQLiteJobStore, state, target: TaskState, **kwargs):
    return store.transition(
        state.job_id,
        target,
        expected_version=state.version,
        **kwargs,
    )


def _job_to_complete(store: SQLiteJobStore, job_id: str):
    state = store.create_job(job_id=job_id, work_order_ref="wo:ge10", project_id="project-1")
    state = _advance(store, state, TaskState.READY)
    state = _advance(store, state, TaskState.CLAIMED, worker_id="a-worker-01")
    state = _advance(store, state, TaskState.GATING, worker_id="a-worker-01")
    state = _advance(store, state, TaskState.EXECUTING, worker_id="a-worker-01")
    state = _advance(store, state, TaskState.VERIFYING, worker_id="a-worker-01")
    return _advance(store, state, TaskState.COMPLETE)


def _job_to_recovery(store: SQLiteJobStore, job_id: str):
    state = store.create_job(job_id=job_id, work_order_ref="wo:ge10", project_id="project-1")
    state = _advance(store, state, TaskState.READY)
    state = _advance(store, state, TaskState.CLAIMED, worker_id="a-worker-02")
    state = _advance(store, state, TaskState.GATING, worker_id="a-worker-02")
    return _advance(
        store,
        state,
        TaskState.RECOVERY_NEEDED,
        worker_id="a-worker-02",
        recovery_classification=RecoveryClassification.UNKNOWN,
    )

def _resolve_recovery_to_complete(store: SQLiteJobStore, state):
    state = _advance(store, state, TaskState.BLOCKED)
    state = _advance(store, state, TaskState.READY)
    state = _advance(store, state, TaskState.CLAIMED, worker_id="a-worker-02")
    state = _advance(store, state, TaskState.GATING, worker_id="a-worker-02")
    state = _advance(store, state, TaskState.EXECUTING, worker_id="a-worker-02")
    state = _advance(store, state, TaskState.VERIFYING, worker_id="a-worker-02")
    return _advance(store, state, TaskState.COMPLETE)


def test_chaos_13_fan_in_waits_for_recovery_and_output_evidence(tmp_path: Path) -> None:
    graph_id, run_id = "graph-fanin", "run-1"
    graph = build_graph(
        [
            TaskNode(id="a", objective="a", expected_outputs=("artifact:a",)),
            TaskNode(id="b", objective="b", expected_outputs=("artifact:b",)),
            TaskNode(id="join", objective="join"),
        ],
        [TaskEdge("a", "join"), TaskEdge("b", "join")],
    )
    store = SQLiteJobStore(tmp_path / "control.sqlite")
    key_a = GraphDispatchKey(graph_id, run_id, "a")
    key_b = GraphDispatchKey(graph_id, run_id, "b")
    _job_to_complete(store, key_a.job_id)
    recovering_b = _job_to_recovery(store, key_b.job_id)

    states = project_graph_node_states(graph, graph_id, run_id, store)
    ready = compute_ready_set(graph, states)
    barrier = evaluate_fan_in_barrier(
        graph,
        "join",
        {
            "a": FanInChildObservation("a", True, successful=True, observed_outputs=("artifact:a",)),
            "b": FanInChildObservation("b", False),
        },
    )
    assert states["a"] is TaskNodeStatus.DONE
    assert states["b"] is TaskNodeStatus.BLOCKED
    assert "join" not in ready.ready_ids
    assert not barrier.is_complete and not barrier.is_satisfied

    _resolve_recovery_to_complete(store, recovering_b)
    states = project_graph_node_states(graph, graph_id, run_id, store)
    ready = compute_ready_set(graph, states)
    barrier = evaluate_fan_in_barrier(
        graph,
        "join",
        {
            "a": FanInChildObservation("a", True, successful=True, observed_outputs=("artifact:a",)),
            "b": FanInChildObservation("b", True, successful=True, observed_outputs=("artifact:b",)),
        },
    )
    assert states["a"] is TaskNodeStatus.DONE
    assert states["b"] is TaskNodeStatus.DONE
    assert "join" in ready.ready_ids
    assert barrier.is_complete and barrier.is_satisfied
