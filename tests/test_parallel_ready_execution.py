from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import json
import sqlite3
from threading import Barrier, Event, Lock

import pytest

from a_conductor.claude_code_harness import HarnessDispatch, MutationIntent, TaskPacketFile
from a_conductor.graph.dispatch import (
    DispatchGateDecision,
    GraphDispatchAction,
    GraphDispatchKey,
    GraphDispatchMode,
    GraphDispatchRequest,
    GraphDispatchResult,
)
from a_conductor.domain import TaskState
from a_conductor.job_execution import JobExecutionOutcome
from a_conductor.job_state import new_job_state
from a_conductor.graph.scheduler import SchedulePlan, SelectedAssignment
from a_conductor.parallel_ready_execution import (
    GraphDispatchParallelRunner,
    ParallelReadyExecutor,
    ParallelReadyOutcomeKind,
    ParallelReadyTask,
)
from a_conductor.provider_config_store import ProviderAdmissionKind, ProviderAdmissionRecord, ProviderAdmissionResult, ProviderConfigStoreError, SQLiteProviderConfigStore
from a_conductor.provider_runtime_assembly import build_sqlite_parallel_ready_executor
from a_conductor.provider_execution_authority import (ProviderExecutionRequirement, _provider_authority_ref)
from a_conductor.provider_policy import (
    ProviderPolicyTaskSecurity,
    TaskNetworkPolicy,
    TaskPrivacyClass,
)
from a_conductor.provider_configuration import (
    EgressBoundary,
    HarnessStrategy,
    ProtocolFamily,
    ProviderConfiguration,
    ProviderEndpointConfig,
    ProviderHealth,
    ProviderModelConfiguration,
    ProviderObservation,
    ProviderTrustClass,
    QuotaSnapshot,
)
from a_conductor.worker_lease import (
    LeaseMutationIntent,
    LeaseOutcomeKind,
    SQLiteWorkerLeaseStore,
    WorkerLeaseBroker,
    WorkerLeaseCandidate,
    WorkerLeaseOutcome,
    WorkerLeaseRequest,
)

NOW = datetime(2026, 8, 30, 2, 0, tzinfo=timezone.utc)
HEAD = "a" * 40


def _profile(provider_id: str = "cointh-glm", *, max_concurrency: int = 2) -> ProviderConfiguration:
    return ProviderConfiguration(
        provider_id=provider_id,
        display_name="CoinTH GLM",
        provider_type="proxy",
        protocol_family=ProtocolFamily.ANTHROPIC_MESSAGES,
        endpoint_ref="endpoint-ref:cointh",
        credential_ref="secret-ref:awiki-data/cointh",
        trust_class=ProviderTrustClass.TRUSTED_THIRD_PARTY,
        egress_boundary=EgressBoundary.EXTERNAL_THIRD_PARTY,
        harness_strategies=(HarnessStrategy.CLAUDE_CODE_CLI,),
        max_concurrency=max_concurrency,
        models=(ProviderModelConfiguration("glm-5.3", "GLM 5.3", supported_effort_levels=("MAX",)),),
        enabled=True,
    )


def _observation(
    provider_id: str = "cointh-glm",
    *,
    remaining: int | None = 8,
    with_quota: bool = True,
) -> ProviderObservation:
    quota = None
    if with_quota:
        quota = QuotaSnapshot(
            window_type="5h",
            limit=100,
            used=92 if remaining is not None else None,
            remaining=remaining,
            reset_at="2026-08-30T05:00:00Z",
            reset_in_seconds=10_800,
            unit="credits",
        )
    return ProviderObservation(
        provider_id=provider_id,
        health=ProviderHealth.AVAILABLE,
        observed_at=NOW,
        provenance="quota-preflight:test",
        quota=quota,
    )




def _provider_requirement_for_test(
    database_path: Path, *, node_id: str, security: ProviderPolicyTaskSecurity | None = None
) -> ProviderExecutionRequirement:
    security = security or ProviderPolicyTaskSecurity(
        privacy_class=TaskPrivacyClass.INTERNAL,
        network_policy=TaskNetworkPolicy.ALLOWLISTED,
        network_allowlist=("provider.example",),
        secret_access=False,
    )
    payload = {
        "schema_version": "1.0.0", "task_id": f"task-{node_id}",
        "goal": "bounded provider execution", "risk_class": "HIGH",
        "authority": {"requested_by": "test", "mutation_allowed": False, "human_approval_required": False},
        "target": {"project_id": "a-sunday-conductor", "identity_policy": "EXACT"},
        "scope": {"allowed_files": [], "forbidden_files": [], "allowed_commands": [], "forbidden_commands": []},
        "acceptance": {"criteria": ["typed result"], "verify_commands": [], "review_required": True},
        "security": {"privacy_class": security.privacy_class.value, "network_policy": security.network_policy.value,
                     "network_allowlist": list(security.network_allowlist), "secret_access": security.secret_access},
        "budget": {"max_elapsed_seconds": 600},
        "retry_policy": {"max_attempts": 1, "max_identical_failures": 1, "on_lease_expiry": "RECOVERY_REQUIRED"},
        "escalation": {"conditions": ["SECURITY_BOUNDARY_CHANGE"]}, "required_evidence": ["TEST_RESULT"],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return ProviderExecutionRequirement._from_task_contract_bytes(
        provider_id="cointh-glm", provider_authority_ref=_provider_authority_ref(database_path),
        expected_configuration_generation=1, task_contract_ref=f"docs/tasks/{node_id}.md",
        authority_bytes=raw, authority_sha256=hashlib.sha256(raw).hexdigest(),
        base_operation_ref=f"operation-{node_id}",
    )

def _broker(tmp_path: Path):
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    ids = iter((f"lease-{i}" for i in range(1, 20)))
    return WorkerLeaseBroker(store=store, lease_id_factory=lambda: next(ids), clock=lambda: NOW), store


def _candidate(worker_id: str, worktree: str, branch: str) -> WorkerLeaseCandidate:
    return WorkerLeaseCandidate(
        worker_id=worker_id,
        state="READY",
        reserved=False,
        active_task=False,
        capabilities=("coding",),
        runtime_id=f"runtime-{worker_id}",
        project_id="a-sunday-conductor",
        worktree=worktree,
        branch=branch,
        head=HEAD,
        health_fresh=True,
        ownership_known=True,
        dirty_state="CLEAN",
        mutation_authorized=True,
    )


def _task(
    *,
    node_id: str,
    worker_id: str,
    worktree: str,
    branch: str,
    mutable_scope: tuple[str, ...],
    profile: ProviderConfiguration | None = None,
    observation: ProviderObservation | None = None,
    require_quota: bool = True,
    gate: DispatchGateDecision | None = None,
    provider_database_path: Path | None = None,
) -> ParallelReadyTask:
    requirement = (
        None if provider_database_path is None
        else _provider_requirement_for_test(provider_database_path, node_id=node_id)
    )
    operation_ref = f"operation-{node_id}" if requirement is None else requirement.operation_ref
    assignment = SelectedAssignment(node_id=node_id, worker_id=worker_id)
    graph_key = GraphDispatchKey("graph-aha6", "run-1", node_id)
    graph_dispatch = GraphDispatchRequest(
        key=graph_key,
        assignment=assignment,
        project_id="a-sunday-conductor",
        work_order_ref=f"docs/tasks/{node_id}.md",
        operation_ref=operation_ref,
        dispatch_mode=GraphDispatchMode.PROGRAMMATIC_PUSH,
    )
    lease = WorkerLeaseRequest(
        session_id="session-aha6",
        task_id=f"task-{node_id}",
        project_id="a-sunday-conductor",
        ordered_worker_ids=(worker_id,),
        required_capabilities=("coding",),
        required_runtime_id=f"runtime-{worker_id}",
        worktree=worktree,
        branch=branch,
        expected_head=HEAD,
        mutation_intent=LeaseMutationIntent.MUTATION,
        allowed_scope=mutable_scope,
        forbidden_scope=("secrets/**",),
        mutable_scope=mutable_scope,
        lease_ttl_seconds=600,
    )
    dispatch = HarnessDispatch(
        execution_id=graph_key.job_id,
        task_contract_ref=f"docs/tasks/{node_id}.md",
        project_id="a-sunday-conductor",
        worktree_path=worktree,
        expected_branch=branch,
        expected_head=HEAD,
        provider_id="cointh-glm",
        model_id="glm-5.3",
        harness_strategy=HarnessStrategy.CLAUDE_CODE_CLI,
        mutation_intent=MutationIntent.READ_ONLY,
        timeout_seconds=300,
        max_output_bytes=100_000,
        effort_level="MAX",
    )
    packet = TaskPacketFile(
        task_contract_ref=dispatch.task_contract_ref,
        path=f"{worktree}\\runs\\{node_id}-task.md",
        sha256="b" * 64,
    )
    return ParallelReadyTask(
        assignment=assignment,
        dispatch_request=graph_dispatch,
        dispatch_gate=gate or DispatchGateDecision.allow(evidence_ref="evidence:preflight"),
        lease_request=lease,
        candidates=(_candidate(worker_id, worktree, branch),),
        provider_profile=profile or _profile(),
        provider_observation=observation if observation is not None else _observation(),
        provider_endpoint=(None if requirement is None else ProviderEndpointConfig((profile or _profile()).endpoint_ref, "https://provider.example/v1")),
        provider_security=(None if requirement is None else requirement.provider_security),
        expected_configuration_generation=(None if requirement is None else requirement.expected_configuration_generation),
        provider_requirement=requirement,
        harness_dispatch=dispatch,
        task_packet=packet,
        require_quota=require_quota,
    )


def _successful_dispatch_result(task: ParallelReadyTask, lease, *, evidence_ref: str):
    request = task.dispatch_request
    job = new_job_state(
        job_id=request.key.job_id,
        work_order_ref=request.work_order_ref,
        project_id=request.project_id,
        max_attempts=request.max_attempts,
    )
    job = replace(
        job, state=TaskState.VERIFYING, worker_id=lease.worker_id,
        attempt_count=1, version=2,
    )
    execution = JobExecutionOutcome(True, job, evidence_ref, None, False)
    return GraphDispatchResult(
        GraphDispatchAction.EXECUTED, job, "EXECUTION_REACHED_VERIFYING", execution=execution
    )


def _successful_dispatch_result_for_request(request: GraphDispatchRequest, *, evidence_ref: str):
    job = new_job_state(
        job_id=request.key.job_id,
        work_order_ref=request.work_order_ref,
        project_id=request.project_id,
        max_attempts=request.max_attempts,
    )
    job = replace(
        job, state=TaskState.VERIFYING, worker_id=request.assignment.worker_id,
        attempt_count=1, version=2,
    )
    execution = JobExecutionOutcome(True, job, evidence_ref, None, False)
    return GraphDispatchResult(
        GraphDispatchAction.EXECUTED, job, "EXECUTION_REACHED_VERIFYING", execution=execution
    )


class BarrierRunner:
    def __init__(self, parties: int = 2) -> None:
        self.barrier = Barrier(parties, timeout=3)
        self.lock = Lock()
        self.calls: list[str] = []

    def run(self, task: ParallelReadyTask, lease):
        with self.lock:
            self.calls.append(task.assignment.node_id)
        self.barrier.wait()
        return _successful_dispatch_result(task, lease, evidence_ref=f"evidence:{task.assignment.node_id}")


def test_two_independent_selected_tasks_run_concurrently_and_keep_leases(tmp_path: Path) -> None:
    broker, store = _broker(tmp_path)
    runner = BarrierRunner()
    executor = ParallelReadyExecutor(broker=broker, runner=runner, clock=lambda: NOW)
    left = _task(
        node_id="left",
        worker_id="a-worker-01",
        worktree=r"A:\Work\left",
        branch="feat/left",
        mutable_scope=("src/left.py",),
    )
    right = _task(
        node_id="right",
        worker_id="a-worker-02",
        worktree=r"A:\Work\right",
        branch="feat/right",
        mutable_scope=("src/right.py",),
    )
    plan = SchedulePlan(
        selected=(left.assignment, right.assignment),
        blocked=(),
        capacity_evidence="capacity=2/2",
    )
    result = executor.execute(
        plan,
        {"left": left, "right": right},
        provider_inflight={"cointh-glm": 0},
    )
    assert [item.node_id for item in result.outcomes] == ["left", "right"]
    assert all(item.kind is ParallelReadyOutcomeKind.RUN_COMPLETED for item in result.outcomes)
    assert sorted(runner.calls) == ["left", "right"]
    active = store.list_active()
    assert len(active) == 2
    assert {item.worker_id for item in active} == {"a-worker-01", "a-worker-02"}


def test_provider_capacity_waits_before_lease_or_runner(tmp_path: Path) -> None:
    broker, store = _broker(tmp_path)
    runner = BarrierRunner(parties=1)
    executor = ParallelReadyExecutor(broker=broker, runner=runner, clock=lambda: NOW)
    profile = _profile(max_concurrency=1)
    task = _task(
        node_id="capacity",
        worker_id="a-worker-01",
        worktree=r"A:\Work\capacity",
        branch="feat/capacity",
        mutable_scope=("src/capacity.py",),
        profile=profile,
    )
    plan = SchedulePlan((task.assignment,), (), "capacity=1/1")
    result = executor.execute(
        plan,
        {"capacity": task},
        provider_inflight={"cointh-glm": 1},
    )
    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.PROVIDER_CAPACITY_WAIT
    assert runner.calls == []
    assert store.list_active() == ()


def test_required_quota_missing_waits_before_lease_or_runner(tmp_path: Path) -> None:
    broker, store = _broker(tmp_path)
    runner = BarrierRunner(parties=1)
    executor = ParallelReadyExecutor(broker=broker, runner=runner, clock=lambda: NOW)
    task = _task(
        node_id="quota",
        worker_id="a-worker-01",
        worktree=r"A:\Work\quota",
        branch="feat/quota",
        mutable_scope=("src/quota.py",),
        observation=_observation(with_quota=False),
        require_quota=True,
    )
    plan = SchedulePlan((task.assignment,), (), "capacity=1/1")
    result = executor.execute(
        plan,
        {"quota": task},
        provider_inflight={"cointh-glm": 0},
    )
    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.PROVIDER_QUOTA_WAIT
    assert result.outcomes[0].reason_code == "PROVIDER_QUOTA_UNKNOWN"
    assert runner.calls == []
    assert store.list_active() == ()


def test_nonpositive_quota_waits_before_lease(tmp_path: Path) -> None:
    broker, store = _broker(tmp_path)
    runner = BarrierRunner(parties=1)
    executor = ParallelReadyExecutor(broker=broker, runner=runner, clock=lambda: NOW)
    task = _task(
        node_id="quota-zero",
        worker_id="a-worker-01",
        worktree=r"A:\Work\quota-zero",
        branch="feat/quota-zero",
        mutable_scope=("src/quota_zero.py",),
        observation=_observation(remaining=0),
        require_quota=True,
    )
    plan = SchedulePlan((task.assignment,), (), "capacity=1/1")
    result = executor.execute(
        plan,
        {"quota-zero": task},
        provider_inflight={"cointh-glm": 0},
    )
    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.PROVIDER_QUOTA_WAIT
    assert result.outcomes[0].reason_code == "PROVIDER_QUOTA_EXHAUSTED"
    assert runner.calls == []
    assert store.list_active() == ()


def test_missing_provider_inflight_snapshot_fails_closed(tmp_path: Path) -> None:
    broker, _ = _broker(tmp_path)
    executor = ParallelReadyExecutor(broker=broker, runner=BarrierRunner(parties=1), clock=lambda: NOW)
    task = _task(
        node_id="no-capacity-snapshot",
        worker_id="a-worker-01",
        worktree=r"A:\Work\no-capacity",
        branch="feat/no-capacity",
        mutable_scope=("src/no_capacity.py",),
    )
    plan = SchedulePlan((task.assignment,), (), "capacity=1/1")
    with pytest.raises(ValueError, match="provider_inflight missing"):
        executor.execute(plan, {task.assignment.node_id: task}, provider_inflight={})


def test_existing_lease_requires_reconcile_and_never_replays_runner(tmp_path: Path) -> None:
    broker, store = _broker(tmp_path)
    runner = BarrierRunner(parties=1)
    task = _task(
        node_id="existing",
        worker_id="a-worker-01",
        worktree=r"A:\Work\existing",
        branch="feat/existing",
        mutable_scope=("src/existing.py",),
    )
    first = broker.acquire(task.lease_request, task.candidates)
    assert first.lease is not None
    executor = ParallelReadyExecutor(broker=broker, runner=runner, clock=lambda: NOW)
    plan = SchedulePlan((task.assignment,), (), "capacity=1/1")
    result = executor.execute(
        plan,
        {"existing": task},
        provider_inflight={"cointh-glm": 0},
    )
    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.LEASE_EXISTING_RECONCILE
    assert runner.calls == []
    assert len(store.list_active()) == 1


def test_lease_scope_collision_blocks_second_task_without_replay(tmp_path: Path) -> None:
    broker, store = _broker(tmp_path)
    runner = BarrierRunner(parties=1)
    executor = ParallelReadyExecutor(broker=broker, runner=runner, clock=lambda: NOW)
    left = _task(
        node_id="left-collision",
        worker_id="a-worker-01",
        worktree=r"A:\Work\shared",
        branch="feat/shared",
        mutable_scope=("src/**",),
    )
    right = _task(
        node_id="right-collision",
        worker_id="a-worker-02",
        worktree=r"A:\Work\shared",
        branch="feat/shared",
        mutable_scope=("src/right.py",),
    )
    plan = SchedulePlan((left.assignment, right.assignment), (), "capacity=2/2")
    result = executor.execute(
        plan,
        {left.assignment.node_id: left, right.assignment.node_id: right},
        provider_inflight={"cointh-glm": 0},
    )
    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.RUN_COMPLETED
    assert result.outcomes[1].kind is ParallelReadyOutcomeKind.LEASE_WAIT
    assert runner.calls == ["left-collision"]
    assert len(store.list_active()) == 1


class UnsupportedLeaseOutcomeBroker:
    def acquire(self, request, candidates):
        return WorkerLeaseOutcome("FUTURE_KIND", None, ())


def test_unknown_lease_outcome_fails_closed_as_recovery(tmp_path: Path) -> None:
    runner = BarrierRunner(parties=1)
    executor = ParallelReadyExecutor(
        broker=UnsupportedLeaseOutcomeBroker(),
        runner=runner,
        clock=lambda: NOW,
    )
    task = _task(
        node_id="future-lease-outcome",
        worker_id="a-worker-01",
        worktree=r"A:\\Work\\future-lease-outcome",
        branch="feat/future-lease-outcome",
        mutable_scope=("src/future_lease_outcome.py",),
    )
    plan = SchedulePlan((task.assignment,), (), "capacity=1/1")

    result = executor.execute(
        plan,
        {task.assignment.node_id: task},
        provider_inflight={"cointh-glm": 0},
    )

    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.LEASE_RECOVERY_REQUIRED
    assert result.outcomes[0].reason_code == "LEASE_OUTCOME_UNSUPPORTED"
    assert runner.calls == []


class MissingLeaseSecondBroker:
    def __init__(self, delegate: WorkerLeaseBroker) -> None:
        self.delegate = delegate
        self.calls = 0

    def acquire(self, request, candidates):
        self.calls += 1
        if self.calls == 2:
            return WorkerLeaseOutcome(LeaseOutcomeKind.LEASED, None, ())
        return self.delegate.acquire(request, candidates)


def test_invalid_leased_outcome_is_isolated_and_prior_sibling_still_runs(tmp_path: Path) -> None:
    real_broker, store = _broker(tmp_path)
    broker = MissingLeaseSecondBroker(real_broker)
    runner = BarrierRunner(parties=1)
    executor = ParallelReadyExecutor(broker=broker, runner=runner, clock=lambda: NOW)
    first = _task(
        node_id="valid-first",
        worker_id="a-worker-01",
        worktree=r"A:\\Work\\valid-first",
        branch="feat/valid-first",
        mutable_scope=("src/valid_first.py",),
    )
    second = _task(
        node_id="invalid-second",
        worker_id="a-worker-02",
        worktree=r"A:\\Work\\invalid-second",
        branch="feat/invalid-second",
        mutable_scope=("src/invalid_second.py",),
    )
    plan = SchedulePlan((first.assignment, second.assignment), (), "capacity=2/2")

    result = executor.execute(
        plan,
        {first.assignment.node_id: first, second.assignment.node_id: second},
        provider_inflight={"cointh-glm": 0},
    )

    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.RUN_COMPLETED
    assert result.outcomes[1].kind is ParallelReadyOutcomeKind.LEASE_RECOVERY_REQUIRED
    assert result.outcomes[1].reason_code == "LEASE_RECORD_MISSING"
    assert runner.calls == ["valid-first"]
    assert len(store.list_active()) == 1


class DriftingLeaseBroker:
    def __init__(self, delegate: WorkerLeaseBroker) -> None:
        self.delegate = delegate

    def acquire(self, request, candidates):
        outcome = self.delegate.acquire(request, candidates)
        assert outcome.lease is not None
        return WorkerLeaseOutcome(
            outcome.kind,
            replace(outcome.lease, worker_id="a-worker-drift"),
            outcome.rejections,
        )


def test_drifted_leased_worker_becomes_recovery_without_runner(tmp_path: Path) -> None:
    real_broker, store = _broker(tmp_path)
    broker = DriftingLeaseBroker(real_broker)
    runner = BarrierRunner(parties=1)
    executor = ParallelReadyExecutor(broker=broker, runner=runner, clock=lambda: NOW)
    task = _task(
        node_id="drifted-lease",
        worker_id="a-worker-01",
        worktree=r"A:\\Work\\drifted-lease",
        branch="feat/drifted-lease",
        mutable_scope=("src/drifted_lease.py",),
    )
    plan = SchedulePlan((task.assignment,), (), "capacity=1/1")

    result = executor.execute(
        plan,
        {task.assignment.node_id: task},
        provider_inflight={"cointh-glm": 0},
    )

    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.LEASE_RECOVERY_REQUIRED
    assert result.outcomes[0].reason_code == "LEASE_WORKER_DRIFT"
    assert result.outcomes[0].lease_outcome is not None
    assert runner.calls == []
    assert len(store.list_active()) == 1


class ExplodingRunner:
    def __init__(self) -> None:
        self.calls = 0

    def run(self, task: ParallelReadyTask, lease):
        self.calls += 1
        raise RuntimeError("synthetic transport uncertainty")


def test_runner_exception_is_not_retried_and_lease_remains_active(tmp_path: Path) -> None:
    broker, store = _broker(tmp_path)
    runner = ExplodingRunner()
    executor = ParallelReadyExecutor(broker=broker, runner=runner, clock=lambda: NOW)
    task = _task(
        node_id="explode",
        worker_id="a-worker-01",
        worktree=r"A:\Work\explode",
        branch="feat/explode",
        mutable_scope=("src/explode.py",),
    )
    plan = SchedulePlan((task.assignment,), (), "capacity=1/1")
    result = executor.execute(
        plan,
        {"explode": task},
        provider_inflight={"cointh-glm": 0},
    )
    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.RUNNER_RECOVERY_REQUIRED
    assert result.outcomes[0].reason_code == "RUNNER_EXCEPTION"
    assert runner.calls == 1
    assert len(store.list_active()) == 1


def test_task_mapping_must_exactly_match_selected_plan(tmp_path: Path) -> None:
    broker, _ = _broker(tmp_path)
    executor = ParallelReadyExecutor(broker=broker, runner=BarrierRunner(parties=1), clock=lambda: NOW)
    task = _task(
        node_id="selected",
        worker_id="a-worker-01",
        worktree=r"A:\Work\selected",
        branch="feat/selected",
        mutable_scope=("src/selected.py",),
    )
    plan = SchedulePlan((task.assignment,), (), "capacity=1/1")
    with pytest.raises(ValueError, match="selected task mapping mismatch"):
        executor.execute(plan, {}, provider_inflight={"cointh-glm": 0})


class BarrierGraphCoordinator:
    def __init__(self, parties: int = 2) -> None:
        self.barrier = Barrier(parties, timeout=3)
        self.lock = Lock()
        self.calls: list[tuple[str, str]] = []

    def dispatch(self, request: GraphDispatchRequest, *, gate: DispatchGateDecision):
        assert gate.allowed
        with self.lock:
            self.calls.append((request.key.node_id, request.assignment.worker_id))
        self.barrier.wait()
        return _successful_dispatch_result_for_request(request, evidence_ref=f"evidence:{request.key.node_id}")


def test_graph_dispatch_adapter_runs_selected_jobs_concurrently(tmp_path: Path) -> None:
    broker, store = _broker(tmp_path)
    coordinator = BarrierGraphCoordinator()
    executor = ParallelReadyExecutor(
        broker=broker,
        runner=GraphDispatchParallelRunner(coordinator),
        clock=lambda: NOW,
    )
    tasks = {
        "graph-left": _task(
            node_id="graph-left",
            worker_id="a-worker-01",
            worktree=r"A:\Work\graph-left",
            branch="feat/graph-left",
            mutable_scope=("src/graph_left.py",),
        ),
        "graph-right": _task(
            node_id="graph-right",
            worker_id="a-worker-02",
            worktree=r"A:\Work\graph-right",
            branch="feat/graph-right",
            mutable_scope=("src/graph_right.py",),
        ),
    }
    plan = SchedulePlan(tuple(task.assignment for task in tasks.values()), (), "capacity=2/2")
    result = executor.execute(plan, tasks, provider_inflight={"cointh-glm": 0})
    assert all(item.kind is ParallelReadyOutcomeKind.RUN_COMPLETED for item in result.outcomes)
    assert sorted(coordinator.calls) == [
        ("graph-left", "a-worker-01"),
        ("graph-right", "a-worker-02"),
    ]
    assert len(store.list_active()) == 2


def test_dispatch_gate_denial_blocks_before_lease_and_runner(tmp_path: Path) -> None:
    broker, store = _broker(tmp_path)
    runner = BarrierRunner(parties=1)
    executor = ParallelReadyExecutor(broker=broker, runner=runner, clock=lambda: NOW)
    task = _task(
        node_id="gate-denied",
        worker_id="a-worker-01",
        worktree=r"A:\Work\gate-denied",
        branch="feat/gate-denied",
        mutable_scope=("src/gate_denied.py",),
        gate=DispatchGateDecision.deny("POLICY_DENIED", evidence_ref="evidence:gate"),
    )
    plan = SchedulePlan((task.assignment,), (), "capacity=1/1")
    result = executor.execute(
        plan,
        {"gate-denied": task},
        provider_inflight={"cointh-glm": 0},
    )
    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.DISPATCH_GATE_BLOCKED
    assert result.outcomes[0].reason_code == "POLICY_DENIED"
    assert runner.calls == []
    assert store.list_active() == ()


def test_stale_provider_observation_waits_before_lease(tmp_path: Path) -> None:
    broker, store = _broker(tmp_path)
    runner = BarrierRunner(parties=1)
    executor = ParallelReadyExecutor(broker=broker, runner=runner, clock=lambda: NOW)
    stale = ProviderObservation(
        provider_id="cointh-glm",
        health=ProviderHealth.AVAILABLE,
        observed_at=NOW - timedelta(seconds=301),
        provenance="quota-preflight:stale-test",
        quota=_observation().quota,
    )
    task = _task(
        node_id="stale-provider",
        worker_id="a-worker-01",
        worktree=r"A:\Work\stale-provider",
        branch="feat/stale-provider",
        mutable_scope=("src/stale_provider.py",),
        observation=stale,
    )
    plan = SchedulePlan((task.assignment,), (), "capacity=1/1")
    result = executor.execute(plan, {"stale-provider": task}, provider_inflight={"cointh-glm": 0})
    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.PROVIDER_WAIT
    assert runner.calls == []
    assert store.list_active() == ()


def test_same_batch_honors_provider_max_concurrency_before_second_lease(tmp_path: Path) -> None:
    broker, store = _broker(tmp_path)
    runner = BarrierRunner(parties=1)
    executor = ParallelReadyExecutor(broker=broker, runner=runner, clock=lambda: NOW)
    profile = _profile(max_concurrency=1)
    first = _task(
        node_id="provider-first",
        worker_id="a-worker-01",
        worktree=r"A:\Work\provider-first",
        branch="feat/provider-first",
        mutable_scope=("src/provider_first.py",),
        profile=profile,
    )
    second = _task(
        node_id="provider-second",
        worker_id="a-worker-02",
        worktree=r"A:\Work\provider-second",
        branch="feat/provider-second",
        mutable_scope=("src/provider_second.py",),
        profile=profile,
    )
    plan = SchedulePlan((first.assignment, second.assignment), (), "capacity=2/2")
    result = executor.execute(
        plan,
        {"provider-first": first, "provider-second": second},
        provider_inflight={"cointh-glm": 0},
    )
    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.RUN_COMPLETED
    assert result.outcomes[1].kind is ParallelReadyOutcomeKind.PROVIDER_CAPACITY_WAIT
    assert runner.calls == ["provider-first"]
    active = store.list_active()
    assert len(active) == 1
    assert active[0].task_id == "task-provider-first"


class BlockingAdmissionRunner:
    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()
        self.lock = Lock()
        self.calls: list[str] = []

    def run(self, task: ParallelReadyTask, lease):
        with self.lock:
            self.calls.append(task.assignment.node_id)
        self.started.set()
        assert self.release.wait(timeout=3)
        return _successful_dispatch_result(task, lease, evidence_ref=f"evidence:{task.assignment.node_id}")


def test_provider_global_admission_blocks_concurrent_independent_batch(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    profile = _profile(max_concurrency=1)
    provider_store = SQLiteProviderConfigStore(database)
    provider_store.save_endpoint(ProviderEndpointConfig(profile.endpoint_ref, "https://provider.example/v1"))
    provider_store.save_provider(profile)
    provider_store.save_observation(replace(_observation(with_quota=True), configuration_generation=1))
    left_broker, _ = _broker(tmp_path / "left")
    right_broker, _ = _broker(tmp_path / "right")
    runner = BlockingAdmissionRunner()
    left_executor = build_sqlite_parallel_ready_executor(
        database_path=database, broker=left_broker, runner=runner, clock=lambda: NOW,
    )
    right_executor = build_sqlite_parallel_ready_executor(
        database_path=database, broker=right_broker, runner=runner, clock=lambda: NOW,
    )
    left = _task(
        node_id="global-left",
        worker_id="a-worker-01",
        worktree=r"A:\Work\global-left",
        branch="feat/global-left",
        mutable_scope=("src/global_left.py",),
        profile=profile, provider_database_path=database,
    )
    right = _task(
        node_id="global-right",
        worker_id="a-worker-02",
        worktree=r"A:\Work\global-right",
        branch="feat/global-right",
        mutable_scope=("src/global_right.py",),
        profile=profile, provider_database_path=database,
    )
    left_plan = SchedulePlan((left.assignment,), (), "capacity=1/1")
    right_plan = SchedulePlan((right.assignment,), (), "capacity=1/1")

    def execute(executor, plan, task, batch_id):
        return executor.execute(
            plan,
            {task.assignment.node_id: task},
            provider_inflight={"cointh-glm": 0},
            batch_id=batch_id,
        )
    with ThreadPoolExecutor(max_workers=2) as pool:
        left_future = pool.submit(execute, left_executor, left_plan, left, "batch-left")
        right_future = pool.submit(execute, right_executor, right_plan, right, "batch-right")
        assert runner.started.wait(timeout=3)
        for _ in range(60):
            if left_future.done() or right_future.done():
                break
            Event().wait(0.05)
        assert left_future.done() or right_future.done()
        runner.release.set()
        results = (left_future.result(timeout=3), right_future.result(timeout=3))

    kinds = sorted(result.outcomes[0].kind.value for result in results)
    assert kinds == ["PROVIDER_CAPACITY_WAIT", "RUN_COMPLETED"]
    assert len(runner.calls) == 1


class FailingAdmissionRunner:
    def run(self, task: ParallelReadyTask, lease):
        raise RuntimeError("uncertain transport")


class ReconcileDispatchRunner:
    def run(self, task: ParallelReadyTask, lease):
        job = new_job_state(
            job_id=task.dispatch_request.key.job_id,
            work_order_ref=task.dispatch_request.work_order_ref,
            project_id=task.dispatch_request.project_id,
        )
        job = replace(job, state=TaskState.EXECUTING, worker_id=lease.worker_id, attempt_count=1, version=2)
        return GraphDispatchResult(
            GraphDispatchAction.RECONCILE,
            job,
            "JOB_STATE_EXECUTING",
        )





class InvalidExecutedEvidenceRunner:
    def run(self, task: ParallelReadyTask, lease):
        job = new_job_state(
            job_id=task.dispatch_request.key.job_id,
            work_order_ref=task.dispatch_request.work_order_ref,
            project_id=task.dispatch_request.project_id,
        )
        job = replace(job, state=TaskState.VERIFYING, worker_id=lease.worker_id, attempt_count=1, version=2)
        execution = JobExecutionOutcome(False, job, None, "BACKEND_FAILED", True)
        return GraphDispatchResult(
            GraphDispatchAction.EXECUTED, job, "EXECUTION_REACHED_VERIFYING", execution=execution
        )

class ExecutedDispatchRunner:
    def run(self, task: ParallelReadyTask, lease):
        job = new_job_state(
            job_id=task.dispatch_request.key.job_id,
            work_order_ref=task.dispatch_request.work_order_ref,
            project_id=task.dispatch_request.project_id,
        )
        job = replace(job, state=TaskState.VERIFYING, worker_id=lease.worker_id, attempt_count=1, version=2)
        execution = JobExecutionOutcome(True, job, "evidence:typed-executed", None, False)
        return GraphDispatchResult(
            GraphDispatchAction.EXECUTED, job, "EXECUTION_REACHED_VERIFYING", execution=execution
        )

class TypedDispatchRunner:
    def __init__(self, action: GraphDispatchAction, state: TaskState, reason: str) -> None:
        self.action = action
        self.state = state
        self.reason = reason

    def run(self, task: ParallelReadyTask, lease):
        job = new_job_state(
            job_id=task.dispatch_request.key.job_id,
            work_order_ref=task.dispatch_request.work_order_ref,
            project_id=task.dispatch_request.project_id,
        )
        worker_id = lease.worker_id if self.state in {
            TaskState.CLAIMED, TaskState.GATING, TaskState.EXECUTING,
            TaskState.VERIFYING, TaskState.REVIEW_PENDING, TaskState.CHANGES_REQUIRED,
            TaskState.REPAIRING, TaskState.RECOVERY_NEEDED,
        } else None
        attempt_count = 1 if self.state in {
            TaskState.EXECUTING, TaskState.VERIFYING, TaskState.REVIEW_PENDING,
            TaskState.CHANGES_REQUIRED, TaskState.REPAIRING, TaskState.COMPLETE,
        } else 0
        job = replace(
            job, state=self.state, worker_id=worker_id, attempt_count=attempt_count, version=2
        )
        return GraphDispatchResult(self.action, job, self.reason)


def _execute_typed_dispatch(tmp_path: Path, *, action: GraphDispatchAction, state: TaskState, reason: str):
    database = tmp_path / "control.sqlite"
    profile = _profile(max_concurrency=1)
    SQLiteProviderConfigStore(database).save_provider(profile)
    broker, _ = _broker(tmp_path / "lease-typed-action")
    task = _task(
        node_id="typed-action", worker_id="a-worker-01",
        worktree=r"A:\Work\typed-action", branch="feat/typed-action",
        mutable_scope=("src/typed_action.py",), profile=profile,
    )
    executor = ParallelReadyExecutor(
        broker=broker, runner=TypedDispatchRunner(action, state, reason),
        clock=lambda: NOW, provider_admission_store=SQLiteProviderConfigStore(database),
    )
    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task}, provider_inflight={"cointh-glm": 0},
        batch_id="batch-typed-action",
    )
    return result.outcomes[0], database

def test_typed_dispatch_reconcile_retains_provider_admission_and_is_not_completed(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    profile = _profile(max_concurrency=1)
    SQLiteProviderConfigStore(database).save_provider(profile)
    broker, _ = _broker(tmp_path / "lease-typed-reconcile")
    task = _task(
        node_id="typed-dispatch-reconcile",
        worker_id="a-worker-01",
        worktree=r"A:\Work\typed-dispatch-reconcile",
        branch="feat/typed-dispatch-reconcile",
        mutable_scope=("src/typed_reconcile.py",),
        profile=profile,
    )
    executor = ParallelReadyExecutor(
        broker=broker,
        runner=ReconcileDispatchRunner(),
        clock=lambda: NOW,
        provider_admission_store=SQLiteProviderConfigStore(database),
    )
    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task},
        provider_inflight={"cointh-glm": 0},
        batch_id="batch-typed-reconcile",
    )
    outcome = result.outcomes[0]
    assert outcome.kind is ParallelReadyOutcomeKind.RUNNER_RECOVERY_REQUIRED
    assert outcome.reason_code == "JOB_STATE_EXECUTING"
    assert isinstance(outcome.runner_result, GraphDispatchResult)
    with sqlite3.connect(database) as connection:
        rows = connection.execute("SELECT status FROM provider_admissions").fetchall()
    assert rows == [("ACTIVE",)]





def test_typed_executed_with_failed_execution_evidence_fails_closed(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    profile = _profile(max_concurrency=1)
    SQLiteProviderConfigStore(database).save_provider(profile)
    broker, _ = _broker(tmp_path / "lease-invalid-evidence")
    task = _task(
        node_id="typed-invalid-evidence", worker_id="a-worker-01",
        worktree=r"A:\Work\typed-invalid-evidence", branch="feat/typed-invalid-evidence",
        mutable_scope=("src/typed_invalid_evidence.py",), profile=profile,
    )
    executor = ParallelReadyExecutor(
        broker=broker, runner=InvalidExecutedEvidenceRunner(), clock=lambda: NOW,
        provider_admission_store=SQLiteProviderConfigStore(database),
    )
    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task}, provider_inflight={"cointh-glm": 0},
        batch_id="batch-invalid-evidence",
    )
    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.RUNNER_RECOVERY_REQUIRED
    assert result.outcomes[0].reason_code == "DISPATCH_EXECUTION_EVIDENCE_INVALID"
    with sqlite3.connect(database) as connection:
        rows = connection.execute("SELECT status FROM provider_admissions").fetchall()
    assert rows == [("ACTIVE",)]

def test_typed_executed_with_execution_evidence_releases_admission(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    profile = _profile(max_concurrency=1)
    SQLiteProviderConfigStore(database).save_provider(profile)
    broker, _ = _broker(tmp_path / "lease-typed-executed")
    task = _task(
        node_id="typed-executed", worker_id="a-worker-01",
        worktree=r"A:\Work\typed-executed", branch="feat/typed-executed",
        mutable_scope=("src/typed_executed.py",), profile=profile,
    )
    executor = ParallelReadyExecutor(
        broker=broker, runner=ExecutedDispatchRunner(), clock=lambda: NOW,
        provider_admission_store=SQLiteProviderConfigStore(database),
    )
    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task}, provider_inflight={"cointh-glm": 0},
        batch_id="batch-typed-executed",
    )
    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.RUN_COMPLETED
    with sqlite3.connect(database) as connection:
        rows = connection.execute("SELECT status FROM provider_admissions").fetchall()
    assert rows == [("RELEASED",)]

def test_typed_executed_without_execution_evidence_fails_closed(tmp_path: Path) -> None:
    outcome, database = _execute_typed_dispatch(
        tmp_path, action=GraphDispatchAction.EXECUTED,
        state=TaskState.VERIFYING, reason="EXECUTION_REACHED_VERIFYING",
    )
    assert outcome.kind is ParallelReadyOutcomeKind.RUNNER_RECOVERY_REQUIRED
    assert outcome.reason_code == "DISPATCH_EXECUTION_EVIDENCE_MISSING"
    with sqlite3.connect(database) as connection:
        rows = connection.execute("SELECT status FROM provider_admissions").fetchall()
    assert rows == [("ACTIVE",)]



@pytest.mark.parametrize(
    ("action", "state", "reason"),
    [
        (GraphDispatchAction.BLOCKED, TaskState.BLOCKED, "DISPATCH_BLOCKED"),
        (GraphDispatchAction.OFFERED, TaskState.CLAIMED, "INTERACTIVE_PULL_OFFERED"),
    ],
)
def test_typed_nonexecuting_action_is_recovery_but_releases_capacity(
    tmp_path: Path, action: GraphDispatchAction, state: TaskState, reason: str
) -> None:
    outcome, database = _execute_typed_dispatch(
        tmp_path, action=action, state=state, reason=reason
    )
    assert outcome.kind is ParallelReadyOutcomeKind.RUNNER_RECOVERY_REQUIRED
    assert outcome.reason_code == reason
    with sqlite3.connect(database) as connection:
        rows = connection.execute("SELECT status FROM provider_admissions").fetchall()
    assert rows == [("RELEASED",)]


@pytest.mark.parametrize(
    ("action", "reason", "expected_reason"),
    [
        (GraphDispatchAction.BLOCKED, "DISPATCH_BLOCKED", "DISPATCH_BLOCKED_STATE_INVALID"),
        (GraphDispatchAction.OFFERED, "INTERACTIVE_PULL_OFFERED", "DISPATCH_OFFERED_STATE_INVALID"),
    ],
)
def test_typed_nonexecuting_action_with_executing_state_retains_capacity(
    tmp_path: Path, action: GraphDispatchAction, reason: str, expected_reason: str
) -> None:
    outcome, database = _execute_typed_dispatch(
        tmp_path, action=action, state=TaskState.EXECUTING, reason=reason
    )
    assert outcome.kind is ParallelReadyOutcomeKind.RUNNER_RECOVERY_REQUIRED
    assert outcome.reason_code == expected_reason
    with sqlite3.connect(database) as connection:
        rows = connection.execute("SELECT status FROM provider_admissions").fetchall()
    assert rows == [("ACTIVE",)]

def test_typed_existing_failed_is_not_reported_as_completed(tmp_path: Path) -> None:
    outcome, database = _execute_typed_dispatch(
        tmp_path, action=GraphDispatchAction.EXISTING,
        state=TaskState.FAILED, reason="JOB_ALREADY_FAILED",
    )
    assert outcome.kind is ParallelReadyOutcomeKind.RUNNER_RECOVERY_REQUIRED
    assert outcome.reason_code == "JOB_ALREADY_FAILED"
    with sqlite3.connect(database) as connection:
        rows = connection.execute("SELECT status FROM provider_admissions").fetchall()
    assert rows == [("RELEASED",)]


def test_typed_existing_verifying_is_idempotent_completed_stage(tmp_path: Path) -> None:
    outcome, database = _execute_typed_dispatch(
        tmp_path, action=GraphDispatchAction.EXISTING,
        state=TaskState.VERIFYING, reason="JOB_ALREADY_VERIFYING",
    )
    assert outcome.kind is ParallelReadyOutcomeKind.RUN_COMPLETED
    with sqlite3.connect(database) as connection:
        rows = connection.execute("SELECT status FROM provider_admissions").fetchall()
    assert rows == [("RELEASED",)]

def test_runner_uncertainty_retains_provider_admission_for_reconcile(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    profile = _profile(max_concurrency=1)
    SQLiteProviderConfigStore(database).save_provider(profile)
    broker, _ = _broker(tmp_path / "lease")
    task = _task(
        node_id="uncertain-provider-run",
        worker_id="a-worker-01",
        worktree=r"A:\Work\uncertain-provider-run",
        branch="feat/uncertain-provider-run",
        mutable_scope=("src/uncertain.py",),
        profile=profile,
    )
    executor = ParallelReadyExecutor(
        broker=broker,
        runner=FailingAdmissionRunner(),
        clock=lambda: NOW,
        provider_admission_store=SQLiteProviderConfigStore(database),
    )
    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task},
        provider_inflight={"cointh-glm": 0},
        batch_id="batch-uncertain",
    )
    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.RUNNER_RECOVERY_REQUIRED
    with sqlite3.connect(database) as connection:
        rows = connection.execute("SELECT status FROM provider_admissions").fetchall()
    assert rows == [("ACTIVE",)]


def test_pre_runner_existing_lease_retains_provider_admission_for_reconcile(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    profile = _profile(max_concurrency=1)
    SQLiteProviderConfigStore(database).save_provider(profile)
    broker, _ = _broker(tmp_path / "lease-existing")
    task = _task(
        node_id="provider-before-existing-lease",
        worker_id="a-worker-01",
        worktree=r"A:\Work\provider-before-existing",
        branch="feat/provider-before-existing",
        mutable_scope=("src/existing.py",),
        profile=profile,
    )
    assert broker.acquire(task.lease_request, task.candidates).kind is LeaseOutcomeKind.LEASED
    runner = BarrierRunner(parties=1)
    executor = ParallelReadyExecutor(
        broker=broker,
        runner=runner,
        clock=lambda: NOW,
        provider_admission_store=SQLiteProviderConfigStore(database),
    )
    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task},
        provider_inflight={"cointh-glm": 0},
        batch_id="batch-existing-lease",
    )
    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.LEASE_EXISTING_RECONCILE
    assert runner.calls == []
    with sqlite3.connect(database) as connection:
        rows = connection.execute("SELECT status FROM provider_admissions").fetchall()
    assert rows == [("ACTIVE",)]


class SelectiveExplodingAdmissionStore:
    def __init__(self, delegate, *, explode_execution_id: str) -> None:
        self.delegate = delegate
        self.explode_execution_id = explode_execution_id

    def acquire_admission(self, **kwargs):
        if kwargs["execution_id"] == self.explode_execution_id:
            raise RuntimeError("unexpected admission backend failure")
        return self.delegate.acquire_admission(**kwargs)

    def release_admission(self, admission_id, **kwargs):
        return self.delegate.release_admission(admission_id, **kwargs)


class ReleaseExplodingAdmissionStore:
    def __init__(self, delegate) -> None:
        self.delegate = delegate

    def acquire_admission(self, **kwargs):
        return self.delegate.acquire_admission(**kwargs)

    def release_admission(self, admission_id, **kwargs):
        raise RuntimeError("unexpected admission release failure")


def test_unexpected_admission_exception_preserves_sibling_batch_evidence(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    profile = _profile(max_concurrency=2)
    delegate = SQLiteProviderConfigStore(database)
    delegate.save_provider(profile)
    broker, _ = _broker(tmp_path / "leases")
    runner = BarrierRunner(parties=1)
    first = _task(
        node_id="admission-sibling-good", worker_id="a-worker-01",
        worktree=r"A:\Work\admission-good", branch="feat/admission-good",
        mutable_scope=("src/good.py",), profile=profile,
    )
    second = _task(
        node_id="admission-sibling-bad", worker_id="a-worker-02",
        worktree=r"A:\Work\admission-bad", branch="feat/admission-bad",
        mutable_scope=("src/bad.py",), profile=profile,
    )
    store = SelectiveExplodingAdmissionStore(
        delegate,
        explode_execution_id=second.harness_dispatch.execution_id,
    )
    executor = ParallelReadyExecutor(
        broker=broker, runner=runner, clock=lambda: NOW,
        provider_admission_store=store,
    )
    plan = SchedulePlan((first.assignment, second.assignment), (), "capacity=2/2")
    result = executor.execute(
        plan,
        {first.assignment.node_id: first, second.assignment.node_id: second},
        provider_inflight={"cointh-glm": 0},
        batch_id="batch-admission-sibling",
    )

    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.RUN_COMPLETED
    assert result.outcomes[1].kind is ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED
    assert result.outcomes[1].reason_code == "PROVIDER_ADMISSION_EXCEPTION"
    assert runner.calls == ["admission-sibling-good"]


def test_unexpected_admission_release_exception_becomes_typed_recovery(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    profile = _profile(max_concurrency=1)
    delegate = SQLiteProviderConfigStore(database)
    delegate.save_provider(profile)
    broker, _ = _broker(tmp_path / "leases-release")
    task = _task(
        node_id="admission-release-failure", worker_id="a-worker-01",
        worktree=r"A:\Work\admission-release-failure",
        branch="feat/admission-release-failure",
        mutable_scope=("src/release_failure.py",), profile=profile,
    )
    executor = ParallelReadyExecutor(
        broker=broker,
        runner=BarrierRunner(parties=1),
        clock=lambda: NOW,
        provider_admission_store=ReleaseExplodingAdmissionStore(delegate),
    )
    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task},
        provider_inflight={"cointh-glm": 0},
        batch_id="batch-release-failure",
    )

    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED
    assert result.outcomes[0].reason_code == "PROVIDER_ADMISSION_RELEASE_EXCEPTION"
    with sqlite3.connect(database) as connection:
        rows = connection.execute("SELECT status FROM provider_admissions").fetchall()
    assert rows == [("ACTIVE",)]


class UnsafeCodeAdmissionError(RuntimeError):
    code = "unsafe\nprovider-code"


class UnsafeCodeAdmissionStore:
    def acquire_admission(self, **kwargs):
        raise UnsafeCodeAdmissionError("do not expose")

    def release_admission(self, admission_id, **kwargs):
        raise AssertionError("release should not run")


def test_untrusted_admission_exception_code_is_sanitized(tmp_path: Path) -> None:
    broker, _ = _broker(tmp_path / "unsafe-code")
    task = _task(
        node_id="unsafe-admission-code", worker_id="a-worker-01",
        worktree=r"A:\Work\unsafe-admission-code", branch="feat/unsafe-admission-code",
        mutable_scope=("src/unsafe.py",), profile=_profile(max_concurrency=1),
    )
    executor = ParallelReadyExecutor(
        broker=broker, runner=BarrierRunner(parties=1), clock=lambda: NOW,
        provider_admission_store=UnsafeCodeAdmissionStore(),
    )
    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task},
        provider_inflight={"cointh-glm": 0},
        batch_id="batch-unsafe-code",
    )

    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED
    assert result.outcomes[0].reason_code == "PROVIDER_ADMISSION_EXCEPTION"


class ExplodingWorkerLeaseBroker:
    def acquire(self, request, candidates):
        raise RuntimeError("worker lease state uncertain")


class WaitingWorkerLeaseBroker:
    def acquire(self, request, candidates):
        return WorkerLeaseOutcome(LeaseOutcomeKind.WAIT)


class FutureWorkerLeaseBroker:
    def acquire(self, request, candidates):
        return WorkerLeaseOutcome("FUTURE_KIND")


def _admission_statuses(database: Path) -> list[tuple[str]]:
    with sqlite3.connect(database) as connection:
        return connection.execute("SELECT status FROM provider_admissions ORDER BY admission_id").fetchall()


def test_worker_lease_exception_retains_provider_admission_and_batch_evidence(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    profile = _profile(max_concurrency=1)
    SQLiteProviderConfigStore(database).save_provider(profile)
    task = _task(
        node_id="lease-exception", worker_id="a-worker-01",
        worktree=r"A:\Work\lease-exception", branch="feat/lease-exception",
        mutable_scope=("src/lease_exception.py",), profile=profile,
    )
    runner = BarrierRunner(parties=1)
    executor = ParallelReadyExecutor(
        broker=ExplodingWorkerLeaseBroker(), runner=runner, clock=lambda: NOW,
        provider_admission_store=SQLiteProviderConfigStore(database),
    )

    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task}, provider_inflight={"cointh-glm": 0},
        batch_id="batch-lease-exception",
    )

    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.LEASE_RECOVERY_REQUIRED
    assert result.outcomes[0].reason_code == "LEASE_ACQUIRE_EXCEPTION"
    assert runner.calls == []
    assert _admission_statuses(database) == [("ACTIVE",)]


def test_worker_lease_wait_releases_unused_provider_admission(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    profile = _profile(max_concurrency=1)
    SQLiteProviderConfigStore(database).save_provider(profile)
    task = _task(
        node_id="lease-wait-release", worker_id="a-worker-01",
        worktree=r"A:\Work\lease-wait-release", branch="feat/lease-wait-release",
        mutable_scope=("src/lease_wait.py",), profile=profile,
    )
    runner = BarrierRunner(parties=1)
    executor = ParallelReadyExecutor(
        broker=WaitingWorkerLeaseBroker(), runner=runner, clock=lambda: NOW,
        provider_admission_store=SQLiteProviderConfigStore(database),
    )

    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task}, provider_inflight={"cointh-glm": 0},
        batch_id="batch-lease-wait",
    )

    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.LEASE_WAIT
    assert runner.calls == []
    assert _admission_statuses(database) == [("RELEASED",)]


def test_unknown_worker_lease_outcome_retains_provider_admission_for_reconcile(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    profile = _profile(max_concurrency=1)
    SQLiteProviderConfigStore(database).save_provider(profile)
    task = _task(
        node_id="future-lease-provider", worker_id="a-worker-01",
        worktree=r"A:\Work\future-lease-provider", branch="feat/future-lease-provider",
        mutable_scope=("src/future_lease_provider.py",), profile=profile,
    )
    runner = BarrierRunner(parties=1)
    executor = ParallelReadyExecutor(
        broker=FutureWorkerLeaseBroker(), runner=runner, clock=lambda: NOW,
        provider_admission_store=SQLiteProviderConfigStore(database),
    )

    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task}, provider_inflight={"cointh-glm": 0},
        batch_id="batch-future-lease-provider",
    )

    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.LEASE_RECOVERY_REQUIRED
    assert result.outcomes[0].reason_code == "LEASE_OUTCOME_UNSUPPORTED"
    assert runner.calls == []
    assert _admission_statuses(database) == [("ACTIVE",)]


class MalformedAdmissionResultStore:
    def acquire_admission(self, **kwargs):
        return object()

    def release_admission(self, admission_id, **kwargs):
        raise AssertionError("release must not run for malformed admission result")


def test_malformed_admission_result_becomes_typed_recovery(tmp_path: Path) -> None:
    broker, _ = _broker(tmp_path / "malformed-admission")
    task = _task(
        node_id="malformed-admission", worker_id="a-worker-01",
        worktree=r"A:\Work\malformed-admission", branch="feat/malformed-admission",
        mutable_scope=("src/malformed.py",), profile=_profile(max_concurrency=1),
    )
    executor = ParallelReadyExecutor(
        broker=broker, runner=BarrierRunner(parties=1), clock=lambda: NOW,
        provider_admission_store=MalformedAdmissionResultStore(),
    )
    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task},
        provider_inflight={"cointh-glm": 0},
        batch_id="batch-malformed-admission",
    )

    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED
    assert result.outcomes[0].reason_code == "PROVIDER_ADMISSION_OUTCOME_INVALID"


class FutureAdmissionStore(MalformedAdmissionResultStore):
    def acquire_admission(self, **kwargs):
        return ProviderAdmissionResult("FUTURE_KIND", "future-kind", None)


def test_unknown_admission_outcome_kind_fails_closed(tmp_path: Path) -> None:
    broker, _ = _broker(tmp_path / "future-admission")
    task = _task(
        node_id="future-admission", worker_id="a-worker-01",
        worktree=r"A:\Work\future-admission", branch="feat/future-admission",
        mutable_scope=("src/future.py",), profile=_profile(max_concurrency=1),
    )
    executor = ParallelReadyExecutor(
        broker=broker, runner=BarrierRunner(parties=1), clock=lambda: NOW,
        provider_admission_store=FutureAdmissionStore(),
    )
    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task},
        provider_inflight={"cointh-glm": 0},
        batch_id="batch-future-admission",
    )

    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED
    assert result.outcomes[0].reason_code == "PROVIDER_ADMISSION_OUTCOME_UNSUPPORTED"


class UnsafeAdmissionResultStore(MalformedAdmissionResultStore):
    def acquire_admission(self, **kwargs):
        return ProviderAdmissionResult(
            ProviderAdmissionKind.CAPACITY_WAIT,
            "unsafe\ncapacity-code",
            None,
        )


def test_admission_result_reason_code_is_sanitized(tmp_path: Path) -> None:
    broker, _ = _broker(tmp_path / "unsafe-result-code")
    task = _task(
        node_id="unsafe-result-code", worker_id="a-worker-01",
        worktree=r"A:\Work\unsafe-result-code", branch="feat/unsafe-result-code",
        mutable_scope=("src/unsafe_result.py",), profile=_profile(max_concurrency=1),
    )
    executor = ParallelReadyExecutor(
        broker=broker, runner=BarrierRunner(parties=1), clock=lambda: NOW,
        provider_admission_store=UnsafeAdmissionResultStore(),
    )
    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task},
        provider_inflight={"cointh-glm": 0},
        batch_id="batch-unsafe-result-code",
    )
    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.PROVIDER_CAPACITY_WAIT
    assert result.outcomes[0].reason_code == "PROVIDER_CAPACITY_EXHAUSTED"


class InvalidAdmissionRecordStore(MalformedAdmissionResultStore):
    def acquire_admission(self, **kwargs):
        return ProviderAdmissionResult(
            ProviderAdmissionKind.ADMITTED,
            "PROVIDER_ADMITTED",
            object(),
        )


def test_admitted_result_with_invalid_record_never_starts_runner(tmp_path: Path) -> None:
    broker, _ = _broker(tmp_path / "invalid-admission-record")
    runner = BarrierRunner(parties=1)
    task = _task(
        node_id="invalid-admission-record", worker_id="a-worker-01",
        worktree=r"A:\Work\invalid-admission-record", branch="feat/invalid-admission-record",
        mutable_scope=("src/invalid_record.py",), profile=_profile(max_concurrency=1),
    )
    executor = ParallelReadyExecutor(
        broker=broker, runner=runner, clock=lambda: NOW,
        provider_admission_store=InvalidAdmissionRecordStore(),
    )
    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task},
        provider_inflight={"cointh-glm": 0},
        batch_id="batch-invalid-admission-record",
    )
    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED
    assert result.outcomes[0].reason_code == "PROVIDER_ADMISSION_RECORD_INVALID"
    assert runner.calls == []



def test_production_task_binding_uses_selected_fresh_candidate() -> None:
    from a_conductor.worker_candidate_assembly import (
        ParallelReadyNodeContract,
        WorkerSupplySnapshot,
        assemble_parallel_ready_tasks,
    )

    worktree = r"A:\Work\bound"
    branch = "feat/bound"
    template = _task(
        node_id="bound", worker_id="a-worker-01", worktree=worktree,
        branch=branch, mutable_scope=("src/bound.py",),
    )
    contract = ParallelReadyNodeContract(
        dispatch_key=template.dispatch_request.key,
        project_id=template.dispatch_request.project_id,
        work_order_ref=template.dispatch_request.work_order_ref,
        operation_ref=template.dispatch_request.operation_ref,
        dispatch_gate=template.dispatch_gate,
        lease_request=template.lease_request,
        provider_profile=template.provider_profile,
        provider_observation=template.provider_observation,
        provider_endpoint=ProviderEndpointConfig(
            template.provider_profile.endpoint_ref, "https://provider.example/v1"
        ),
        provider_security=_wo118b_security(),
        expected_configuration_generation=1,
        harness_dispatch=template.harness_dispatch,
        task_packet=template.task_packet,
        require_quota=template.require_quota,
    )
    selected = SelectedAssignment(node_id="bound", worker_id="a-worker-02")
    plan = SchedulePlan(selected=(selected,), blocked=(), capacity_evidence="1/1")
    fresh = _candidate("a-worker-02", worktree, branch)
    supply = WorkerSupplySnapshot(scheduler_workers=(), lease_candidates=(fresh,))

    tasks = assemble_parallel_ready_tasks(plan, {"bound": contract}, supply)
    bound = tasks["bound"]
    assert bound.assignment == selected
    assert bound.candidates == (fresh,)
    assert bound.lease_request.ordered_worker_ids == ("a-worker-02",)
    assert bound.lease_request.required_runtime_id == fresh.runtime_id
    assert bound.dispatch_request.assignment == selected


def test_production_task_binding_fails_closed_when_selected_worker_is_stale() -> None:
    from a_conductor.worker_candidate_assembly import (
        ParallelReadyNodeContract,
        WorkerSupplySnapshot,
        assemble_parallel_ready_tasks,
    )

    template = _task(
        node_id="bound", worker_id="a-worker-01", worktree=r"A:\Work\bound",
        branch="feat/bound", mutable_scope=("src/bound.py",),
    )
    contract = ParallelReadyNodeContract(
        dispatch_key=template.dispatch_request.key,
        project_id=template.dispatch_request.project_id,
        work_order_ref=template.dispatch_request.work_order_ref,
        operation_ref=template.dispatch_request.operation_ref,
        dispatch_gate=template.dispatch_gate,
        lease_request=template.lease_request,
        provider_profile=template.provider_profile,
        provider_observation=template.provider_observation,
        provider_endpoint=ProviderEndpointConfig(
            template.provider_profile.endpoint_ref, "https://provider.example/v1"
        ),
        provider_security=_wo118b_security(),
        expected_configuration_generation=1,
        harness_dispatch=template.harness_dispatch,
        task_packet=template.task_packet,
        require_quota=template.require_quota,
    )
    selected = SelectedAssignment(node_id="bound", worker_id="a-worker-09")
    plan = SchedulePlan(selected=(selected,), blocked=(), capacity_evidence="0/1")
    supply = WorkerSupplySnapshot(
        scheduler_workers=(),
        lease_candidates=(_candidate("a-worker-01", r"A:\Work\bound", "feat/bound"),),
    )
    with pytest.raises(ValueError, match="selected worker missing"):
        assemble_parallel_ready_tasks(plan, {"bound": contract}, supply)



def test_production_elastic_path_reuses_scheduler_broker_and_runner(tmp_path: Path) -> None:
    from a_conductor.elastic_worker_capacity import (
        ElasticCapacityPolicy,
        ElasticProvisionedWorker,
        ElasticWorkerCapacityCoordinator,
        ProductionElasticExecutionKind,
        ProductionElasticWorkerExecutor,
        SQLiteWorkerProvisioningReservations,
    )
    from a_conductor.graph.domain import TaskGraph, TaskNode
    from a_conductor.graph.ready import compute_ready_set
    from a_conductor.graph.scheduler import NodeEligibility, SchedulePolicy, WorkerSnapshot
    from a_conductor.worker_candidate_assembly import (
        ParallelReadyNodeContract,
        WorkerSupplyRecord,
    )

    worktree = r"A:\Repo"
    branch = "feat/test"
    database = tmp_path / "leases.sqlite"
    store = SQLiteWorkerLeaseStore(database)
    ids = iter((f"lease-{i}" for i in range(1, 5)))
    broker = WorkerLeaseBroker(
        store=store, lease_id_factory=lambda: next(ids), clock=lambda: NOW
    )

    fixed_candidate = replace(
        _candidate("a-worker-01", worktree, branch),
        reserved=True,
        active_task=True,
    )
    fixed_record = WorkerSupplyRecord(
        worker_id="a-worker-01",
        scheduler=WorkerSnapshot(
            worker_id="a-worker-01",
            state="READY",
            capabilities=fixed_candidate.capabilities,
            reserved=True,
            project="a-sunday-conductor",
            workspace=worktree,
            mutation_authorized=False,
        ),
        candidate=fixed_candidate,
        reason_code="READY",
    )

    class StatefulAssembler:
        def __init__(self) -> None:
            self.record = None
            self.all_calls = 0
            self.one_calls = []

        def assemble_all(self):
            self.all_calls += 1
            if self.record is None:
                return (fixed_record,)
            blocked = replace(
                self.record,
                scheduler=replace(
                    self.record.scheduler, reserved=True, mutation_authorized=False
                ),
                candidate=replace(
                    self.record.candidate, reserved=True, active_task=True
                ),
            )
            return (fixed_record, blocked)

        def assemble_all_for_owner(self, *, session_id, task_id):
            assert (session_id, task_id) == ("session-aha6", "task-elastic-node")
            return (fixed_record,) if self.record is None else (fixed_record, self.record)

        def assemble(self, worker_id):
            raise AssertionError("generic observation must not bypass provisioning reservation")

        def assemble_for_owner(self, worker_id, *, session_id, task_id):
            self.one_calls.append(worker_id)
            assert (session_id, task_id) == ("session-aha6", "task-elastic-node")
            if self.record is None or self.record.worker_id != worker_id:
                raise RuntimeError("worker not observed")
            return self.record

    assembler = StatefulAssembler()

    class Provisioner:
        def __init__(self) -> None:
            self.calls = []

        def provision(self, request):
            self.calls.append(request)
            fresh = _candidate("a-worker-09", worktree, branch)
            assembler.record = WorkerSupplyRecord(
                worker_id="a-worker-09",
                scheduler=WorkerSnapshot(
                    worker_id="a-worker-09",
                    state="READY",
                    capabilities=fresh.capabilities,
                    reserved=False,
                    project="a-sunday-conductor",
                    workspace=worktree,
                    mutation_authorized=True,
                ),
                candidate=fresh,
                reason_code="READY",
            )
            return ElasticProvisionedWorker("a-worker-09", "serena-local")

    provisioner = Provisioner()
    capacity = ElasticWorkerCapacityCoordinator(
        broker=broker,
        reservations=SQLiteWorkerProvisioningReservations(store),
        provisioner=provisioner,
        candidate_assembler=assembler,
        reservation_id_factory=lambda: "reservation-1",
        clock=lambda: NOW,
    )

    class Runner:
        def __init__(self) -> None:
            self.calls = []

        def run(self, task, lease):
            self.calls.append((task.assignment.node_id, lease.worker_id))
            return _successful_dispatch_result(task, lease, evidence_ref=f"evidence:{task.assignment.node_id}")

    runner = Runner()
    provider_store = SQLiteProviderConfigStore(database)
    configured_provider = _profile()
    provider_store.save_endpoint(
        ProviderEndpointConfig(configured_provider.endpoint_ref, "https://provider.example/v1")
    )
    provider_store.save_provider(configured_provider)
    provider_store.save_observation(
        replace(_observation(with_quota=True), configuration_generation=1)
    )
    executor = ParallelReadyExecutor(
        broker=broker,
        runner=runner,
        clock=lambda: NOW,
        provider_admission_store=provider_store,
    )
    production = ProductionElasticWorkerExecutor(
        candidate_assembler=assembler,
        capacity_coordinator=capacity,
        parallel_executor=executor,
    )

    graph = TaskGraph()
    graph.add_node(
        TaskNode(
            id="elastic-node",
            objective="execute on bounded elastic worker",
            write_set=("src/elastic.py",),
            model_requirement=r"project:a-sunday-conductor|ws:A:\Repo",
        )
    )
    ready = compute_ready_set(graph, {})
    template = _task(
        node_id="elastic-node",
        worker_id="placeholder",
        worktree=worktree,
        branch=branch,
        mutable_scope=("src/elastic.py",),
    )
    requirement = _provider_requirement_for_test(database, node_id="elastic-node")
    contract = ParallelReadyNodeContract(
        dispatch_key=template.dispatch_request.key,
        project_id=template.dispatch_request.project_id,
        work_order_ref=template.dispatch_request.work_order_ref,
        operation_ref=requirement.operation_ref,
        dispatch_gate=template.dispatch_gate,
        lease_request=template.lease_request,
        provider_profile=template.provider_profile,
        provider_observation=template.provider_observation,
        provider_endpoint=ProviderEndpointConfig(
            template.provider_profile.endpoint_ref, "https://provider.example/v1"
        ),
        provider_security=requirement.provider_security,
        expected_configuration_generation=requirement.expected_configuration_generation,
        harness_dispatch=template.harness_dispatch,
        task_packet=template.task_packet,
        require_quota=template.require_quota,
        provider_requirement=requirement,
    )

    result = production.execute_once(
        graph,
        ready,
        {"elastic-node": contract},
        schedule_policy=SchedulePolicy(max_parallel=1),
        provider_inflight={"cointh-glm": 0},
        runtime_kind="serena-local",
        elastic_policy=ElasticCapacityPolicy(
            enabled=True,
            max_extra_workers=1,
            permitted_runtime_kinds=("serena-local",),
        ),
        eligibility={"elastic-node": NodeEligibility()},
        batch_id="batch-elastic",
    )

    assert result.kind is ProductionElasticExecutionKind.ELASTIC_EXECUTED
    assert result.initial_plan.selected == ()
    assert result.initial_plan.blocked[0].kind.value == "CAPACITY"
    assert "workers_ready=0/1" in result.initial_plan.capacity_evidence
    assert result.final_plan is not None
    assert result.final_plan.selected[0].worker_id == "a-worker-09"
    assert runner.calls == [("elastic-node", "a-worker-09")]
    assert provisioner.calls and assembler.one_calls == ["a-worker-09"]
    active = store.list_active()
    assert len(active) == 1 and active[0].worker_id == "a-worker-09"
    reservations = store.list_provisioning_reservations(consuming_only=True)
    assert len(reservations) == 1 and reservations[0].state == "CAPACITY"



def test_production_elastic_requires_scheduler_eligibility_before_provisioning(tmp_path: Path) -> None:
    from a_conductor.elastic_worker_capacity import (
        ElasticCapacityPolicy,
        ElasticWorkerCapacityCoordinator,
        ProductionElasticExecutionKind,
        ProductionElasticWorkerExecutor,
        SQLiteWorkerProvisioningReservations,
    )
    from a_conductor.graph.domain import TaskGraph, TaskNode
    from a_conductor.graph.ready import compute_ready_set
    from a_conductor.graph.scheduler import SchedulePolicy
    from a_conductor.worker_candidate_assembly import ParallelReadyNodeContract

    class EmptyAssembler:
        def assemble_all(self):
            return ()

        def assemble_all_for_owner(self, *, session_id, task_id):
            return ()

        def assemble(self, worker_id):
            raise AssertionError("no worker should be provisioned")

        def assemble_for_owner(self, worker_id, *, session_id, task_id):
            raise AssertionError("no worker should be provisioned")

    class ExplodingProvisioner:
        def __init__(self) -> None:
            self.calls = []

        def provision(self, request):
            self.calls.append(request)
            raise AssertionError("provisioning must not run without eligibility evidence")

    assembler = EmptyAssembler()
    provisioner = ExplodingProvisioner()
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    broker = WorkerLeaseBroker(
        store=store, lease_id_factory=lambda: "lease-1", clock=lambda: NOW
    )
    capacity = ElasticWorkerCapacityCoordinator(
        broker=broker,
        reservations=SQLiteWorkerProvisioningReservations(store),
        provisioner=provisioner,
        candidate_assembler=assembler,
        reservation_id_factory=lambda: "reservation-1",
        clock=lambda: NOW,
    )
    executor = ParallelReadyExecutor(
        broker=broker,
        runner=BarrierRunner(parties=1),
        clock=lambda: NOW,
    )
    production = ProductionElasticWorkerExecutor(
        candidate_assembler=assembler,
        capacity_coordinator=capacity,
        parallel_executor=executor,
    )
    graph = TaskGraph()
    graph.add_node(TaskNode(id="node", objective="bounded task"))
    ready = compute_ready_set(graph, {})
    template = _task(
        node_id="node", worker_id="placeholder", worktree=r"A:\Repo",
        branch="feat/test", mutable_scope=("src/x.py",),
    )
    contract = ParallelReadyNodeContract(
        dispatch_key=template.dispatch_request.key,
        project_id=template.dispatch_request.project_id,
        work_order_ref=template.dispatch_request.work_order_ref,
        operation_ref=template.dispatch_request.operation_ref,
        dispatch_gate=template.dispatch_gate,
        lease_request=template.lease_request,
        provider_profile=template.provider_profile,
        provider_observation=template.provider_observation,
        provider_endpoint=ProviderEndpointConfig(
            template.provider_profile.endpoint_ref, "https://provider.example/v1"
        ),
        provider_security=_wo118b_security(),
        expected_configuration_generation=1,
        harness_dispatch=template.harness_dispatch,
        task_packet=template.task_packet,
        require_quota=template.require_quota,
    )

    result = production.execute_once(
        graph,
        ready,
        {"node": contract},
        schedule_policy=SchedulePolicy(max_parallel=1),
        provider_inflight={"cointh-glm": 0},
        runtime_kind="serena-local",
        elastic_policy=ElasticCapacityPolicy(
            enabled=True,
            max_extra_workers=1,
            permitted_runtime_kinds=("serena-local",),
        ),
    )
    assert result.kind is ProductionElasticExecutionKind.RECOVERY_REQUIRED
    assert result.reason_code == "SCHEDULER_ELIGIBILITY_EVIDENCE_MISSING"
    assert provisioner.calls == []
    assert store.list_provisioning_reservations(consuming_only=True) == ()


# WO-P1-121: post-merge dispatch-evidence safety regressions.
class _Wo121ReturnRunner:
    def __init__(self, factory):
        self._factory = factory

    def run(self, task: ParallelReadyTask, lease):
        return self._factory(task, lease)


def _wo121_job(
    task: ParallelReadyTask,
    lease,
    state: TaskState,
    *,
    job_id: str | None = None,
    project_id: str | None = None,
    work_order_ref: str | None = None,
    worker_id: str | None | object = ...,
    max_attempts: int | None = None,
):
    request = task.dispatch_request
    job = new_job_state(
        job_id=job_id or request.key.job_id,
        work_order_ref=work_order_ref or request.work_order_ref,
        project_id=project_id or request.project_id,
        max_attempts=max_attempts or request.max_attempts,
    )
    bound_states = {TaskState.CLAIMED, TaskState.GATING, TaskState.EXECUTING,
                    TaskState.VERIFYING, TaskState.REVIEW_PENDING,
                    TaskState.CHANGES_REQUIRED, TaskState.REPAIRING}
    resolved_worker = lease.worker_id if state in bound_states else None
    if worker_id is not ...:
        resolved_worker = worker_id
    attempt_count = 1 if state in {TaskState.EXECUTING, TaskState.VERIFYING,
                                   TaskState.REVIEW_PENDING, TaskState.CHANGES_REQUIRED,
                                   TaskState.REPAIRING, TaskState.COMPLETE} else 0
    return replace(job, state=state, worker_id=resolved_worker,
                   attempt_count=attempt_count, version=2)


def _run_wo121_result(tmp_path: Path, factory, *, node_id: str):
    database = tmp_path / f"{node_id}.sqlite"
    profile = _profile(max_concurrency=1)
    store = SQLiteProviderConfigStore(database)
    store.save_provider(profile)
    broker, _ = _broker(tmp_path / f"lease-{node_id}")
    task = _task(
        node_id=node_id,
        worker_id="a-worker-01",
        worktree=fr"A:\Work\{node_id}",
        branch=f"fix/{node_id}",
        mutable_scope=(f"src/{node_id}.py",),
        profile=profile,
    )
    executor = ParallelReadyExecutor(
        broker=broker,
        runner=_Wo121ReturnRunner(factory),
        clock=lambda: NOW,
        provider_admission_store=store,
    )
    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {node_id: task},
        provider_inflight={profile.provider_id: 0},
        batch_id=f"batch-{node_id}",
    )
    outcome = result.outcomes[0]
    assert outcome.provider_admission is not None
    current = store.get_admission(outcome.provider_admission.admission_id)
    next_admission = store.acquire_admission(
        provider_id=profile.provider_id,
        execution_id=f"next-{node_id}",
        batch_id=f"next-batch-{node_id}",
        expected_max_concurrency=1,
        now=NOW,
        ttl_seconds=600,
    )
    return outcome, current, next_admission


@pytest.mark.parametrize("returned", [None, {"status": "unknown"}], ids=["none", "dict"])
def test_wo121_unsupported_normal_return_retains_provider_admission(tmp_path: Path, returned) -> None:
    outcome, admission, next_admission = _run_wo121_result(
        tmp_path, lambda task, lease: returned, node_id=f"unsupported-{type(returned).__name__}"
    )
    assert outcome.kind is ParallelReadyOutcomeKind.RUNNER_RECOVERY_REQUIRED
    assert outcome.reason_code == "DISPATCH_RESULT_UNSUPPORTED"
    assert admission is not None and admission.status == "ACTIVE"
    assert next_admission.kind is ProviderAdmissionKind.CAPACITY_WAIT


@pytest.mark.parametrize(
    "drift",
    ["job_id", "project_id", "work_order_ref", "worker_id", "max_attempts"],
)
def test_wo121_foreign_or_drifted_executed_evidence_retains_admission(
    tmp_path: Path, drift: str
) -> None:
    def factory(task, lease):
        kwargs = {}
        if drift == "job_id":
            kwargs["job_id"] = "foreign-job"
        elif drift == "project_id":
            kwargs["project_id"] = "foreign-project"
        elif drift == "work_order_ref":
            kwargs["work_order_ref"] = "docs/work-orders/foreign.md"
        elif drift == "worker_id":
            kwargs["worker_id"] = "a-worker-99"
        elif drift == "max_attempts":
            kwargs["max_attempts"] = task.dispatch_request.max_attempts + 1
        job = _wo121_job(task, lease, TaskState.VERIFYING, **kwargs)
        execution = JobExecutionOutcome(True, job, "evidence:foreign", None, False)
        return GraphDispatchResult(
            GraphDispatchAction.EXECUTED,
            job,
            "EXECUTION_REACHED_VERIFYING",
            execution=execution,
        )

    outcome, admission, next_admission = _run_wo121_result(
        tmp_path, factory, node_id=f"identity-{drift}"
    )
    assert outcome.kind is ParallelReadyOutcomeKind.RUNNER_RECOVERY_REQUIRED
    assert outcome.reason_code == "DISPATCH_RESULT_IDENTITY_MISMATCH"
    assert admission is not None and admission.status == "ACTIVE"
    assert next_admission.kind is ProviderAdmissionKind.CAPACITY_WAIT


@pytest.mark.parametrize(
    ("action", "state"),
    [
        (GraphDispatchAction.EXISTING, TaskState.VERIFYING),
        (GraphDispatchAction.BLOCKED, TaskState.BLOCKED),
        (GraphDispatchAction.OFFERED, TaskState.CLAIMED),
    ],
)
def test_wo121_nonexecuted_action_rejects_nested_execution_evidence(
    tmp_path: Path, action: GraphDispatchAction, state: TaskState
) -> None:
    def factory(task, lease):
        job = _wo121_job(task, lease, state)
        execution = JobExecutionOutcome(False, job, None, "EXECUTION_UNCERTAIN", True)
        return GraphDispatchResult(action, job, "CONTROL_RESULT", execution=execution)

    outcome, admission, next_admission = _run_wo121_result(
        tmp_path, factory, node_id=f"nested-{action.value.lower()}"
    )
    assert outcome.kind is ParallelReadyOutcomeKind.RUNNER_RECOVERY_REQUIRED
    assert outcome.reason_code == "DISPATCH_NONEXECUTION_EVIDENCE_INVALID"
    assert admission is not None and admission.status == "ACTIVE"
    assert next_admission.kind is ProviderAdmissionKind.CAPACITY_WAIT


def test_wo121_valid_executed_evidence_still_completes_and_releases(tmp_path: Path) -> None:
    def factory(task, lease):
        job = _wo121_job(task, lease, TaskState.VERIFYING)
        execution = JobExecutionOutcome(True, job, "evidence:wo121-valid", None, False)
        return GraphDispatchResult(
            GraphDispatchAction.EXECUTED,
            job,
            "EXECUTION_REACHED_VERIFYING",
            execution=execution,
        )

    outcome, admission, next_admission = _run_wo121_result(
        tmp_path, factory, node_id="valid-executed"
    )
    assert outcome.kind is ParallelReadyOutcomeKind.RUN_COMPLETED
    assert admission is not None and admission.status == "RELEASED"
    assert next_admission.kind is ProviderAdmissionKind.ADMITTED


def test_wo121_foreign_existing_evidence_retains_admission(tmp_path: Path) -> None:
    def factory(task, lease):
        job = _wo121_job(
            task, lease, TaskState.VERIFYING,
            job_id="foreign-existing-job", project_id="foreign-project",
        )
        return GraphDispatchResult(GraphDispatchAction.EXISTING, job, "JOB_ALREADY_VERIFYING")

    outcome, admission, next_admission = _run_wo121_result(
        tmp_path, factory, node_id="foreign-existing"
    )
    assert outcome.kind is ParallelReadyOutcomeKind.RUNNER_RECOVERY_REQUIRED
    assert outcome.reason_code == "DISPATCH_RESULT_IDENTITY_MISMATCH"
    assert admission is not None and admission.status == "ACTIVE"
    assert next_admission.kind is ProviderAdmissionKind.CAPACITY_WAIT


def test_wo121_malformed_lane_preserves_valid_sibling_completion(tmp_path: Path) -> None:
    database = tmp_path / "siblings.sqlite"
    profile = _profile(max_concurrency=2)
    store = SQLiteProviderConfigStore(database)
    store.save_provider(profile)
    broker, _ = _broker(tmp_path / "sibling-leases")
    bad = _task(node_id="bad-sibling", worker_id="a-worker-01",
                worktree=r"A:\Work\bad-sibling", branch="fix/bad-sibling",
                mutable_scope=("src/bad.py",), profile=profile)
    good = _task(node_id="good-sibling", worker_id="a-worker-02",
                 worktree=r"A:\Work\good-sibling", branch="fix/good-sibling",
                 mutable_scope=("src/good.py",), profile=profile)

    class Runner:
        def run(self, task, lease):
            if task.assignment.node_id == "bad-sibling":
                return None
            return _successful_dispatch_result(task, lease, evidence_ref="evidence:good-sibling")

    executor = ParallelReadyExecutor(broker=broker, runner=Runner(), clock=lambda: NOW,
                                     provider_admission_store=store)
    result = executor.execute(
        SchedulePlan((bad.assignment, good.assignment), (), "capacity=2/2"),
        {"bad-sibling": bad, "good-sibling": good},
        provider_inflight={profile.provider_id: 0}, batch_id="batch-siblings",
    )
    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.RUNNER_RECOVERY_REQUIRED
    assert result.outcomes[1].kind is ParallelReadyOutcomeKind.RUN_COMPLETED
    assert store.get_admission(result.outcomes[0].provider_admission.admission_id).status == "ACTIVE"
    assert store.get_admission(result.outcomes[1].provider_admission.admission_id).status == "RELEASED"


def test_wo121_generic_runner_completion_remains_supported_without_provider_admission(tmp_path: Path) -> None:
    broker, _ = _broker(tmp_path / "generic-no-admission")
    task = _task(
        node_id="generic-no-admission",
        worker_id="a-worker-01",
        worktree=r"A:\Work\generic-no-admission",
        branch="fix/generic-no-admission",
        mutable_scope=("src/generic.py",),
    )
    returned = {"stage": "runner-complete"}
    executor = ParallelReadyExecutor(
        broker=broker,
        runner=_Wo121ReturnRunner(lambda task, lease: returned),
        clock=lambda: NOW,
    )
    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task},
        provider_inflight={task.provider_profile.provider_id: 0},
        batch_id="batch-generic-no-admission",
    )
    outcome = result.outcomes[0]
    assert outcome.kind is ParallelReadyOutcomeKind.RUN_COMPLETED
    assert outcome.reason_code == "RUNNER_COMPLETED"
    assert outcome.runner_result == returned
    assert outcome.provider_admission is None


class _WO118BNoLeaseBroker:
    def __init__(self) -> None:
        self.calls = 0

    def acquire(self, request, candidates):
        self.calls += 1
        raise AssertionError("worker lease must not be reached")


class _WO118BRecordingAdmissionStore:
    def __init__(self, delegate: SQLiteProviderConfigStore, *, bump_after_admit: bool = False) -> None:
        self.delegate = delegate
        self.acquire_calls: list[dict[str, object]] = []
        self.bump_after_admit = bump_after_admit
        self.bump_error_code: str | None = None

    def load_provider_snapshot(self, provider_id: str):
        return self.delegate.load_provider_snapshot(provider_id)

    def acquire_admission(self, **kwargs):
        self.acquire_calls.append(dict(kwargs))
        result = self.delegate.acquire_admission(**kwargs)
        if self.bump_after_admit:
            current = self.delegate.load_provider_snapshot(kwargs["provider_id"])
            assert current is not None and current.generation is not None
            edited = ProviderConfiguration(**{
                **current.profile.as_dict(),
                "display_name": "Generation changed after admission",
            })
            try:
                self.delegate.save_provider(edited, expected_generation=current.generation)
            except ProviderConfigStoreError as exc:
                self.bump_error_code = exc.code
            else:
                self.bump_error_code = "UNEXPECTED_WRITE_ALLOWED"
        return result

    def release_admission(self, admission_id, **kwargs):
        return self.delegate.release_admission(admission_id, **kwargs)


def _wo118b_security(*, secret: bool = False) -> ProviderPolicyTaskSecurity:
    return ProviderPolicyTaskSecurity(
        privacy_class=TaskPrivacyClass.SECRET if secret else TaskPrivacyClass.INTERNAL,
        network_policy=TaskNetworkPolicy.ALLOWLISTED,
        network_allowlist=("provider.example",),
        secret_access=secret,
    )


def _wo118b_authorized_task(tmp_path: Path, *, secret: bool = False) -> tuple[ParallelReadyTask, SQLiteProviderConfigStore]:
    database = tmp_path / "provider-authority.sqlite"
    store = SQLiteProviderConfigStore(database)
    configured = _profile(max_concurrency=1)
    endpoint = ProviderEndpointConfig(configured.endpoint_ref, "https://provider.example/v1")
    store.save_endpoint(endpoint)
    store.save_provider(configured)
    observed = replace(_observation(with_quota=False), configuration_generation=1)
    store.save_observation(observed)
    task = _task(
        node_id="wo118b-authority",
        worker_id="a-worker-01",
        worktree=r"A:\Work\wo118b-authority",
        branch="feat/wo118b-authority",
        mutable_scope=("src/authority.py",),
        profile=configured,
        observation=observed,
        require_quota=False,
    )
    task = replace(
        task,
        provider_endpoint=endpoint,
        provider_security=_wo118b_security(secret=secret),
        expected_configuration_generation=1,
    )
    return task, store


def test_wo118b_secret_policy_denial_precedes_admission_and_worker_lease(tmp_path: Path) -> None:
    task, delegate = _wo118b_authorized_task(tmp_path, secret=True)
    admission = _WO118BRecordingAdmissionStore(delegate)
    broker = _WO118BNoLeaseBroker()
    executor = ParallelReadyExecutor(
        broker=broker,
        runner=BarrierRunner(parties=1),
        clock=lambda: NOW,
        provider_admission_store=admission,
    )

    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task},
        provider_inflight={task.provider_profile.provider_id: 0},
        batch_id="wo118b-policy-denied",
    )

    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.DISPATCH_GATE_BLOCKED
    assert result.outcomes[0].reason_code == "SECRET_TASK_EXTERNAL_DENIED"
    assert admission.acquire_calls == []
    assert broker.calls == 0


def test_wo118b_generation_drift_precedes_admission_and_worker_lease(tmp_path: Path) -> None:
    task, delegate = _wo118b_authorized_task(tmp_path)
    snapshot = delegate.load_provider_snapshot(task.provider_profile.provider_id)
    assert snapshot is not None and snapshot.generation == 1
    delegate.save_provider(
        ProviderConfiguration(**{**snapshot.profile.as_dict(), "display_name": "Edited"}),
        expected_generation=1,
    )
    admission = _WO118BRecordingAdmissionStore(delegate)
    broker = _WO118BNoLeaseBroker()
    executor = ParallelReadyExecutor(
        broker=broker,
        runner=BarrierRunner(parties=1),
        clock=lambda: NOW,
        provider_admission_store=admission,
    )

    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task},
        provider_inflight={task.provider_profile.provider_id: 0},
        batch_id="wo118b-generation-stale",
    )

    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.PROVIDER_WAIT
    assert result.outcomes[0].reason_code == "PROVIDER_CONFIGURATION_STALE"
    assert admission.acquire_calls == []
    assert broker.calls == 0


def test_wo118b_admission_fence_blocks_generation_write_until_unused_release(tmp_path: Path) -> None:
    task, delegate = _wo118b_authorized_task(tmp_path)
    admission = _WO118BRecordingAdmissionStore(delegate, bump_after_admit=True)
    broker = WaitingWorkerLeaseBroker()
    executor = ParallelReadyExecutor(
        broker=broker,
        runner=BarrierRunner(parties=1),
        clock=lambda: NOW,
        provider_admission_store=admission,
    )

    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task},
        provider_inflight={task.provider_profile.provider_id: 0},
        batch_id="wo118b-admission-fence",
    )

    assert admission.bump_error_code == "PROVIDER_CONFIGURATION_IN_USE"
    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.LEASE_WAIT
    assert admission.acquire_calls[0]["expected_configuration_generation"] == 1
    assert _admission_statuses(delegate.database_path) == [("RELEASED",)]



class _WO118BForgedAdmissionStore:
    def __init__(self, delegate: SQLiteProviderConfigStore, *, forge_release: bool = False) -> None:
        self.delegate = delegate
        self.forge_release = forge_release

    def load_provider_snapshot(self, provider_id: str):
        return self.delegate.load_provider_snapshot(provider_id)

    def acquire_admission(self, **kwargs):
        result = self.delegate.acquire_admission(**kwargs)
        if self.forge_release:
            return result
        record = result.admission
        assert record is not None
        return ProviderAdmissionResult(
            ProviderAdmissionKind.ADMITTED, result.reason_code,
            replace(record, provider_id="provider-foreign"),
        )

    def release_admission(self, admission_id, **kwargs):
        if not self.forge_release:
            raise AssertionError("foreign admission must never be released via forged identity")
        record = self.delegate.get_admission(admission_id)
        assert record is not None
        return record


def test_wo118b_foreign_admission_record_never_reaches_worker_lease(tmp_path: Path) -> None:
    task, delegate = _wo118b_authorized_task(tmp_path)
    broker = _WO118BNoLeaseBroker()
    executor = ParallelReadyExecutor(
        broker=broker, runner=BarrierRunner(parties=1), clock=lambda: NOW,
        provider_admission_store=_WO118BForgedAdmissionStore(delegate),
    )
    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task},
        provider_inflight={task.provider_profile.provider_id: 0},
        batch_id="wo118b-forged-admission",
    )
    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED
    assert result.outcomes[0].reason_code == "PROVIDER_ADMISSION_IDENTITY_MISMATCH"
    assert broker.calls == 0
    assert _admission_statuses(delegate.database_path) == [("ACTIVE",)]


def test_wo118b_release_requires_exact_released_record(tmp_path: Path) -> None:
    task, delegate = _wo118b_authorized_task(tmp_path)
    executor = ParallelReadyExecutor(
        broker=WaitingWorkerLeaseBroker(), runner=BarrierRunner(parties=1), clock=lambda: NOW,
        provider_admission_store=_WO118BForgedAdmissionStore(delegate, forge_release=True),
    )
    result = executor.execute(
        SchedulePlan((task.assignment,), (), "capacity=1/1"),
        {task.assignment.node_id: task},
        provider_inflight={task.provider_profile.provider_id: 0},
        batch_id="wo118b-forged-release",
    )
    assert result.outcomes[0].kind is ParallelReadyOutcomeKind.PROVIDER_ADMISSION_RECOVERY_REQUIRED
    assert result.outcomes[0].reason_code == "PROVIDER_ADMISSION_RELEASE_INVALID"
    assert _admission_statuses(delegate.database_path) == [("ACTIVE",)]
