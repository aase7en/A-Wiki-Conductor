from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
from threading import Barrier, Event, Lock

import pytest

from a_conductor.claude_code_harness import HarnessDispatch, MutationIntent, TaskPacketFile
from a_conductor.graph.dispatch import (
    DispatchGateDecision,
    GraphDispatchKey,
    GraphDispatchMode,
    GraphDispatchRequest,
)
from a_conductor.graph.scheduler import SchedulePlan, SelectedAssignment
from a_conductor.parallel_ready_execution import (
    GraphDispatchParallelRunner,
    ParallelReadyExecutor,
    ParallelReadyOutcomeKind,
    ParallelReadyTask,
)
from a_conductor.provider_config_store import ProviderAdmissionKind, ProviderAdmissionResult, SQLiteProviderConfigStore
from a_conductor.provider_runtime_assembly import build_sqlite_parallel_ready_executor
from a_conductor.provider_configuration import (
    EgressBoundary,
    HarnessStrategy,
    ProtocolFamily,
    ProviderConfiguration,
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
) -> ParallelReadyTask:
    assignment = SelectedAssignment(node_id=node_id, worker_id=worker_id)
    graph_key = GraphDispatchKey("graph-aha6", "run-1", node_id)
    graph_dispatch = GraphDispatchRequest(
        key=graph_key,
        assignment=assignment,
        project_id="a-sunday-conductor",
        work_order_ref=f"docs/tasks/{node_id}.md",
        operation_ref=f"operation-{node_id}",
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
        harness_dispatch=dispatch,
        task_packet=packet,
        require_quota=require_quota,
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
        return {"node_id": task.assignment.node_id, "lease_id": lease.lease_id}


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
        return {"job_id": request.key.job_id, "node_id": request.key.node_id}


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
        return {"node_id": task.assignment.node_id, "lease_id": lease.lease_id}


def test_provider_global_admission_blocks_concurrent_independent_batch(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    profile = _profile(max_concurrency=1)
    SQLiteProviderConfigStore(database).save_provider(profile)
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
        profile=profile,
    )
    right = _task(
        node_id="global-right",
        worker_id="a-worker-02",
        worktree=r"A:\Work\global-right",
        branch="feat/global-right",
        mutable_scope=("src/global_right.py",),
        profile=profile,
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
