from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier

import pytest

from a_conductor.claude_code_harness import HarnessDispatch, MutationIntent, TaskPacketFile
from a_conductor.control_center import ControlCenterSnapshot, WorkerScreenRow
from a_conductor.domain import WorkerState
from a_conductor.elastic_worker_capacity import (
    ElasticCapacityError,
    ElasticCapacityOutcomeKind,
    ElasticCapacityPolicy,
    ElasticProvisionedWorker,
    ElasticWorkerCapacityCoordinator,
    ProductionElasticExecutionKind,
    ProductionElasticWorkerExecutor,
    SQLiteWorkerProvisioningReservations,
    build_sqlite_elastic_worker_capacity_coordinator,
)
from a_conductor.graph.dispatch import (
    DispatchGateDecision,
    GraphDispatchKey,
    GraphDispatchMode,
    GraphDispatchRequest,
)
from a_conductor.graph.domain import TaskGraph, TaskNode
from a_conductor.graph.ready import compute_ready_set
from a_conductor.graph.scheduler import (
    BlockedReason,
    BlockedReasonKind,
    NodeEligibility,
    SchedulePlan,
    SchedulePolicy,
    SelectedAssignment,
)
from a_conductor.lifecycle import LifecycleAction, LifecycleContext
from a_conductor.parallel_ready_execution import ParallelReadyExecutor
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
from a_conductor.runtime_safety import (
    PortBindingState,
    ProcessOwnership,
    TunnelBindingState,
    WorktreeBindingState,
)
from a_conductor.serena_runtime import ProjectIdentityPolicy, SerenaProjectBinding
from a_conductor.worker_candidate_assembly import (
    GitWorktreeState,
    ParallelReadyNodeContract,
    WorkerCandidateAssembler,
)
from a_conductor.worker_lease import (
    LeaseMutationIntent,
    LeaseOutcomeKind,
    SQLiteWorkerLeaseStore,
    WorkerLeaseBroker,
    WorkerLeaseCandidate,
    WorkerLeaseError,
    WorkerLeaseRequest,
)


NOW = datetime(2026, 8, 31, 2, 0, tzinfo=timezone.utc)
LATER = NOW + timedelta(hours=2)
HEAD = "a" * 40
WORKTREE = r"A:\Repo"
BRANCH = "feat/test"
NEW_WORKER = "a-worker-09"


def _capacity_plan() -> SchedulePlan:
    return SchedulePlan(
        selected=(),
        blocked=(
            BlockedReason("node-1", "capacity: all slots filled", BlockedReasonKind.CAPACITY),
        ),
        capacity_evidence="capacity=0/1 workers_ready=0/0 selected=0 blocked=1",
    )


def _policy() -> ElasticCapacityPolicy:
    return ElasticCapacityPolicy(
        enabled=True,
        max_extra_workers=1,
        permitted_runtime_kinds=("serena-local",),
    )


def _row(worker_id: str) -> WorkerScreenRow:
    return WorkerScreenRow(
        worker_id=worker_id,
        display_name=f"A-Worker {worker_id[-2:]}",
        state=WorkerState.READY,
        runtime_id="runtime-1",
        assignment_id=f"assignment-{worker_id}",
        project_id="project-1",
        project_display_name="Repo",
        project_root_path=WORKTREE,
        mutation_allowed=True,
    )


def _binding() -> SerenaProjectBinding:
    return SerenaProjectBinding(
        project_id="project-1",
        worktree_path=WORKTREE,
        identity_policy=ProjectIdentityPolicy.EXACT,
        expected_branch=BRANCH,
        expected_head=HEAD,
        mutation_allowed=True,
    )


def _context() -> LifecycleContext:
    return LifecycleContext(
        action=LifecycleAction.START,
        assignment_present=True,
        project_exists=True,
        process_ownership=ProcessOwnership.OWNED,
        port_binding=PortBindingState.OWNED,
        tunnel_required=False,
        tunnel_binding=TunnelBindingState.FREE,
        worktree_binding=WorktreeBindingState.OWNED,
        ready=True,
        project_identity_ok=True,
        worker_state=WorkerState.READY,
        active_task=False,
    )


def _git() -> GitWorktreeState:
    return GitWorktreeState(BRANCH, HEAD, "CLEAN")


class MutableControlCenter:
    def __init__(self, *rows: WorkerScreenRow) -> None:
        self._rows = tuple(rows)

    def register(self, row: WorkerScreenRow) -> None:
        self._rows = self._rows + (row,)

    def snapshot(self) -> ControlCenterSnapshot:
        return ControlCenterSnapshot(projects=(), workers=self._rows, online=True)


class StaticBindingStore:
    def get_project_binding(self, project_id: str):
        binding = _binding()
        return binding if binding.project_id == project_id else None


class StaticLifecycle:
    def observe(self, worker_id: str, action: LifecycleAction) -> LifecycleContext:
        assert action is LifecycleAction.START
        return _context()


class StaticGit:
    def observe(self, worktree: str) -> GitWorktreeState:
        return _git()


class StaticCapabilities:
    def resolve(self, runtime_id: str | None) -> tuple[str, ...]:
        return ("shell", "repo") if runtime_id == "runtime-1" else ()


def _assembler(store, center) -> WorkerCandidateAssembler:
    return WorkerCandidateAssembler(
        control_center=center,
        config_store=StaticBindingStore(),
        lifecycle_context_provider=StaticLifecycle(),
        git_state_observer=StaticGit(),
        lease_store=store,
        capability_resolver=StaticCapabilities(),
    )


def _request(session_id: str, task_id: str, worker_id: str) -> WorkerLeaseRequest:
    return WorkerLeaseRequest(
        session_id=session_id,
        task_id=task_id,
        project_id="project-1",
        ordered_worker_ids=(worker_id,),
        required_capabilities=("shell",),
        required_runtime_id=None,
        worktree=WORKTREE,
        branch=BRANCH,
        expected_head=HEAD,
        mutation_intent=LeaseMutationIntent.READ_ONLY,
        lease_ttl_seconds=600,
    )


def _hand_candidate(worker_id: str) -> WorkerLeaseCandidate:
    return WorkerLeaseCandidate(
        worker_id=worker_id,
        state="READY",
        reserved=False,
        active_task=False,
        capabilities=("shell", "repo"),
        runtime_id="runtime-1",
        project_id="project-1",
        worktree=WORKTREE,
        branch=BRANCH,
        head=HEAD,
        health_fresh=True,
        ownership_known=True,
        dirty_state="CLEAN",
        mutation_authorized=True,
    )


def _broker(store) -> WorkerLeaseBroker:
    ids = iter(f"lease-{i}" for i in range(1, 20))
    return WorkerLeaseBroker(
        store=store, lease_id_factory=lambda: next(ids), clock=lambda: NOW
    )


class NullAssembler:
    def assemble(self, worker_id: str):
        raise AssertionError("not used")

    def assemble_for_owner(self, worker_id: str, *, session_id: str, task_id: str):
        raise AssertionError("not used")


class RegisteringProvisioner:
    def __init__(self, center: MutableControlCenter, worker_id: str = NEW_WORKER) -> None:
        self.center = center
        self.worker_id = worker_id
        self.calls = []

    def provision(self, request):
        self.calls.append(request)
        self.center.register(_row(self.worker_id))
        return ElasticProvisionedWorker(self.worker_id, "serena-local")


class FailingProvisioner:
    def __init__(self) -> None:
        self.calls = []

    def provision(self, request):
        self.calls.append(request)
        raise RuntimeError("provision transport lost")


class FakeRunner:
    def __init__(self) -> None:
        self.calls = []

    def run(self, task, lease):
        self.calls.append((task.assignment.node_id, lease.worker_id))
        return {"executed": task.assignment.node_id}


class ExplodingRunner:
    def run(self, task, lease):
        raise RuntimeError("runner lost")


def _coordinator(store, *, provisioner, assembler) -> ElasticWorkerCapacityCoordinator:
    return ElasticWorkerCapacityCoordinator(
        broker=_broker(store),
        reservations=SQLiteWorkerProvisioningReservations(store),
        provisioner=provisioner,
        candidate_assembler=assembler,
        reservation_id_factory=lambda: "reservation-1",
        clock=lambda: NOW,
    )


def _profile() -> ProviderConfiguration:
    return ProviderConfiguration(
        provider_id="cointh-glm",
        display_name="CoinTH GLM",
        provider_type="proxy",
        protocol_family=ProtocolFamily.ANTHROPIC_MESSAGES,
        endpoint_ref="endpoint-ref:cointh",
        credential_ref="secret-ref:awiki-data/cointh",
        trust_class=ProviderTrustClass.TRUSTED_THIRD_PARTY,
        egress_boundary=EgressBoundary.EXTERNAL_THIRD_PARTY,
        harness_strategies=(HarnessStrategy.CLAUDE_CODE_CLI,),
        max_concurrency=2,
        models=(
            ProviderModelConfiguration("glm-5.3", "GLM 5.3", supported_effort_levels=("MAX",)),
        ),
        enabled=True,
    )


def _observation(*, available: bool = True) -> ProviderObservation:
    quota = QuotaSnapshot(
        window_type="5h",
        limit=100,
        used=10,
        remaining=90,
        reset_at="2026-08-31T05:00:00Z",
        reset_in_seconds=10_800,
        unit="credits",
    )
    return ProviderObservation(
        provider_id="cointh-glm",
        health=ProviderHealth.AVAILABLE if available else ProviderHealth.UNAVAILABLE,
        observed_at=NOW,
        provenance="quota-preflight:test",
        quota=quota,
    )


def _contract(*, available: bool = True) -> ParallelReadyNodeContract:
    node_id = "n1"
    graph_key = GraphDispatchKey("graph-wo120", "run-1", node_id)
    dispatch_request = GraphDispatchRequest(
        key=graph_key,
        assignment=SelectedAssignment(node_id=node_id, worker_id=NEW_WORKER),
        project_id="project-1",
        work_order_ref=f"docs/tasks/{node_id}.md",
        operation_ref=f"operation-{node_id}",
        dispatch_mode=GraphDispatchMode.PROGRAMMATIC_PUSH,
    )
    lease = WorkerLeaseRequest(
        session_id="owner-s",
        task_id="task-n1",
        project_id="project-1",
        ordered_worker_ids=(NEW_WORKER,),
        required_capabilities=("shell",),
        required_runtime_id="runtime-1",
        worktree=WORKTREE,
        branch=BRANCH,
        expected_head=HEAD,
        mutation_intent=LeaseMutationIntent.MUTATION,
        allowed_scope=("src/**",),
        forbidden_scope=("secrets/**",),
        mutable_scope=("src/x.py",),
        lease_ttl_seconds=600,
    )
    dispatch = HarnessDispatch(
        execution_id=graph_key.job_id,
        task_contract_ref=f"docs/tasks/{node_id}.md",
        project_id="project-1",
        worktree_path=WORKTREE,
        expected_branch=BRANCH,
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
        path=f"{WORKTREE}\\runs\\{node_id}-task.md",
        sha256="b" * 64,
    )
    return ParallelReadyNodeContract(
        dispatch_key=graph_key,
        project_id="project-1",
        work_order_ref=dispatch.task_contract_ref,
        operation_ref=f"operation-{node_id}",
        dispatch_gate=DispatchGateDecision.allow(evidence_ref="evidence:preflight"),
        lease_request=lease,
        provider_profile=_profile(),
        provider_observation=_observation(available=available),
        harness_dispatch=dispatch,
        task_packet=packet,
        require_quota=False,
    )


def _graph() -> TaskGraph:
    graph = TaskGraph()
    graph.add_node(
        TaskNode(
            id="n1",
            objective="execute on bounded elastic worker",
            write_set=("src/x.py",),
            model_requirement=r"project:project-1|ws:A:\Repo",
        )
    )
    return graph


def _execute(tmp_path: Path, *, assembler_factory, provisioner_factory=None, runner=None):
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    center = MutableControlCenter()
    assembler = assembler_factory(store, center)
    provisioner = (
        provisioner_factory(center)
        if provisioner_factory is not None
        else RegisteringProvisioner(center)
    )
    coordinator = _coordinator(store, provisioner=provisioner, assembler=assembler)
    executor = ProductionElasticWorkerExecutor(
        candidate_assembler=assembler,
        capacity_coordinator=coordinator,
        parallel_executor=ParallelReadyExecutor(
            broker=_broker(store), runner=runner or FakeRunner(), clock=lambda: NOW
        ),
    )
    result = executor.execute_once(
        _graph(),
        compute_ready_set(_graph(), {}),
        {"n1": _contract()},
        schedule_policy=SchedulePolicy(max_parallel=1),
        provider_inflight={"cointh-glm": 0},
        runtime_kind="serena-local",
        elastic_policy=_policy(),
        eligibility={"n1": NodeEligibility()},
        batch_id=None,
    )
    return result, store


# ---------------------------------------------------------------------------
# Slice A — successful CAPACITY keeps consuming max_extra_workers
# ---------------------------------------------------------------------------


def test_store_level_capacity_reservation_still_consumes_budget(tmp_path: Path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    first = store.acquire_provisioning_reservation(
        reservation_id="r-1",
        session_id="s-1",
        task_id="t-1",
        runtime_kind="serena-local",
        max_extra_workers=1,
        now=NOW,
    )
    assert first.kind.value == "ACQUIRED"
    store.transition_provisioning_reservation(
        "r-1", session_id="s-1", task_id="t-1", state="PROVISIONED",
        now=NOW, worker_id=NEW_WORKER,
    )
    store.transition_provisioning_reservation(
        "r-1", session_id="s-1", task_id="t-1", state="CAPACITY",
        now=NOW, worker_id=NEW_WORKER,
    )
    second = store.acquire_provisioning_reservation(
        reservation_id="r-2",
        session_id="s-2",
        task_id="t-2",
        runtime_kind="serena-local",
        max_extra_workers=1,
        now=NOW,
    )
    assert second.kind.value == "LIMIT_WAIT"


# ---------------------------------------------------------------------------
# Slice B — single-store composition invariant
# ---------------------------------------------------------------------------


def test_executor_rejects_mismatched_supply_authority(tmp_path: Path) -> None:
    store_a = SQLiteWorkerLeaseStore(tmp_path / "authority-a.sqlite")
    store_b = SQLiteWorkerLeaseStore(tmp_path / "authority-b.sqlite")
    coordinator = _coordinator(
        store_a, provisioner=FailingProvisioner(), assembler=NullAssembler()
    )
    with pytest.raises(ValueError, match="ELASTIC_SUPPLY_AUTHORITY_MISMATCH"):
        ProductionElasticWorkerExecutor(
            candidate_assembler=_assembler(store_b, MutableControlCenter()),
            capacity_coordinator=coordinator,
            parallel_executor=ParallelReadyExecutor(
                broker=_broker(store_a), runner=FakeRunner(), clock=lambda: NOW
            ),
        )
    ProductionElasticWorkerExecutor(
        candidate_assembler=_assembler(store_a, MutableControlCenter()),
        capacity_coordinator=coordinator,
        parallel_executor=ParallelReadyExecutor(
            broker=_broker(store_a), runner=FakeRunner(), clock=lambda: NOW
        ),
    )


def test_sanctioned_builder_rejects_mismatched_assembler_authority(tmp_path: Path) -> None:
    store_b = SQLiteWorkerLeaseStore(tmp_path / "authority-b.sqlite")
    with pytest.raises(ValueError, match="ELASTIC_SUPPLY_AUTHORITY_MISMATCH"):
        build_sqlite_elastic_worker_capacity_coordinator(
            database_path=tmp_path / "authority-a.sqlite",
            provisioner=FailingProvisioner(),
            candidate_assembler=_assembler(store_b, MutableControlCenter()),
            lease_id_factory=lambda: "lease-1",
            reservation_id_factory=lambda: "reservation-1",
            clock=lambda: NOW,
        )


# ---------------------------------------------------------------------------
# Slice C — direct provisioning cannot bypass eligibility evidence
# ---------------------------------------------------------------------------


def test_direct_provisioning_requires_eligibility_evidence(tmp_path: Path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    provisioner = RegisteringProvisioner(MutableControlCenter())
    coordinator = _coordinator(
        store, provisioner=provisioner, assembler=_assembler(store, MutableControlCenter())
    )
    with pytest.raises(TypeError):
        coordinator.provision_ready(
            _capacity_plan(),
            _request("owner-s", "owner-t", NEW_WORKER),
            runtime_kind="serena-local",
            policy=_policy(),
        )
    missing = coordinator.provision_ready(
        _capacity_plan(),
        _request("owner-s", "owner-t", NEW_WORKER),
        runtime_kind="serena-local",
        policy=_policy(),
        eligibility=None,
    )
    assert missing.kind is ElasticCapacityOutcomeKind.RECOVERY_REQUIRED
    assert missing.reason_code == "SCHEDULER_ELIGIBILITY_EVIDENCE_MISSING"
    partial = coordinator.provision_ready(
        _capacity_plan(),
        _request("owner-s", "owner-t", NEW_WORKER),
        runtime_kind="serena-local",
        policy=_policy(),
        eligibility={},
    )
    assert partial.kind is ElasticCapacityOutcomeKind.RECOVERY_REQUIRED
    assert partial.reason_code == "SCHEDULER_ELIGIBILITY_EVIDENCE_MISSING"
    refused = coordinator.provision_ready(
        _capacity_plan(),
        _request("owner-s", "owner-t", NEW_WORKER),
        runtime_kind="serena-local",
        policy=_policy(),
        eligibility={"node-1": NodeEligibility(gate_refused=True)},
    )
    assert refused.kind is ElasticCapacityOutcomeKind.NOT_CAPACITY_FAILURE
    assert refused.reason_code == "SCHEDULER_ELIGIBILITY_REFUSED"
    assert provisioner.calls == []
    assert store.list_provisioning_reservations(consuming_only=True) == ()


# ---------------------------------------------------------------------------
# Slice D — post-PROVISIONED_READY uncertainty persists RECOVERY_REQUIRED
# ---------------------------------------------------------------------------


class FailingOwnerReobserveAssembler:
    def __init__(self, inner) -> None:
        self.inner = inner

    def assemble_all(self):
        return self.inner.assemble_all()

    def assemble_all_for_owner(self, *, session_id, task_id):
        raise RuntimeError("full reobservation lost")

    def assemble(self, worker_id):
        return self.inner.assemble(worker_id)

    def assemble_for_owner(self, worker_id, *, session_id, task_id):
        return self.inner.assemble_for_owner(worker_id, session_id=session_id, task_id=task_id)


class EmptyOwnerReobserveAssembler(FailingOwnerReobserveAssembler):
    def assemble_all_for_owner(self, *, session_id, task_id):
        return ()


def test_full_reobservation_failure_marks_reservation_recovery(tmp_path: Path) -> None:
    result, store = _execute(
        tmp_path,
        assembler_factory=lambda store, center: FailingOwnerReobserveAssembler(
            _assembler(store, center)
        ),
    )
    assert result.kind is ProductionElasticExecutionKind.RECOVERY_REQUIRED
    assert result.reason_code == "PROVISIONED_WORKER_FULL_REOBSERVATION_FAILED"
    reservations = store.list_provisioning_reservations(consuming_only=True)
    assert len(reservations) == 1 and reservations[0].state == "RECOVERY_REQUIRED"


def test_reschedule_drift_marks_reservation_recovery(tmp_path: Path) -> None:
    result, store = _execute(
        tmp_path,
        assembler_factory=lambda store, center: EmptyOwnerReobserveAssembler(
            _assembler(store, center)
        ),
    )
    assert result.kind is ProductionElasticExecutionKind.RECOVERY_REQUIRED
    assert result.reason_code == "PROVISIONED_WORKER_RESCHEDULE_DRIFT"
    reservations = store.list_provisioning_reservations(consuming_only=True)
    assert len(reservations) == 1 and reservations[0].state == "RECOVERY_REQUIRED"


def test_runner_failure_marks_reservation_recovery(tmp_path: Path) -> None:
    result, store = _execute(
        tmp_path,
        assembler_factory=_assembler,
        runner=ExplodingRunner(),
    )
    assert result.kind is ProductionElasticExecutionKind.RECOVERY_REQUIRED
    assert result.reason_code == "PARALLEL_READY_RECOVERY_REQUIRED"
    reservations = store.list_provisioning_reservations(consuming_only=True)
    assert len(reservations) == 1 and reservations[0].state == "RECOVERY_REQUIRED"


def test_provider_wait_after_provisioning_marks_reservation_recovery(tmp_path: Path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    center = MutableControlCenter()
    assembler = _assembler(store, center)
    coordinator = _coordinator(
        store, provisioner=RegisteringProvisioner(center), assembler=assembler
    )
    executor = ProductionElasticWorkerExecutor(
        candidate_assembler=assembler,
        capacity_coordinator=coordinator,
        parallel_executor=ParallelReadyExecutor(
            broker=_broker(store), runner=FakeRunner(), clock=lambda: NOW
        ),
    )
    graph = _graph()
    result = executor.execute_once(
        graph,
        compute_ready_set(graph, {}),
        {"n1": _contract(available=False)},
        schedule_policy=SchedulePolicy(max_parallel=1),
        provider_inflight={"cointh-glm": 0},
        runtime_kind="serena-local",
        elastic_policy=_policy(),
        eligibility={"n1": NodeEligibility()},
        batch_id=None,
    )
    assert result.kind is ProductionElasticExecutionKind.WAIT
    assert result.reason_code == "PARALLEL_READY_WAIT"
    reservations = store.list_provisioning_reservations(consuming_only=True)
    assert len(reservations) == 1 and reservations[0].state == "RECOVERY_REQUIRED"


# ---------------------------------------------------------------------------
# Slice E — publication / mark-provisioned interleaving cannot steal the worker
# ---------------------------------------------------------------------------


def test_store_refuses_foreign_lease_on_owner_provisioned_worker(tmp_path: Path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    store.acquire_provisioning_reservation(
        reservation_id="r-1", session_id="owner-s", task_id="owner-t",
        runtime_kind="serena-local", max_extra_workers=1, now=NOW,
    )
    store.transition_provisioning_reservation(
        "r-1", session_id="owner-s", task_id="owner-t", state="PROVISIONED",
        now=NOW, worker_id=NEW_WORKER,
    )
    broker = _broker(store)
    rival = broker.acquire(
        _request("rival-s", "rival-t", NEW_WORKER), (_hand_candidate(NEW_WORKER),)
    )
    assert rival.kind is LeaseOutcomeKind.WAIT
    owner = broker.acquire(
        _request("owner-s", "owner-t", NEW_WORKER), (_hand_candidate(NEW_WORKER),)
    )
    assert owner.kind is LeaseOutcomeKind.LEASED


def test_store_mark_provisioned_refuses_foreign_active_lease(tmp_path: Path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    store.acquire_provisioning_reservation(
        reservation_id="r-1", session_id="owner-s", task_id="owner-t",
        runtime_kind="serena-local", max_extra_workers=1, now=NOW,
    )
    rival = _broker(store).acquire(
        _request("rival-s", "rival-t", NEW_WORKER), (_hand_candidate(NEW_WORKER),)
    )
    assert rival.kind is LeaseOutcomeKind.LEASED
    with pytest.raises(WorkerLeaseError, match="PROVISIONING_WORKER_LEASE_CONFLICT"):
        store.transition_provisioning_reservation(
            "r-1", session_id="owner-s", task_id="owner-t", state="PROVISIONED",
            now=NOW, worker_id=NEW_WORKER,
        )


def test_publication_before_mark_provisioned_cannot_be_stolen(tmp_path: Path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    center = MutableControlCenter()
    assembler = _assembler(store, center)
    published = Barrier(2, timeout=10)
    go = Barrier(2, timeout=10)
    observed_reserved: list[bool] = []

    class InterleavingProvisioner:
        def __init__(self) -> None:
            self.calls = []

        def provision(self, request):
            self.calls.append(request)
            center.register(_row(NEW_WORKER))
            published.wait(timeout=10)
            go.wait(timeout=10)
            return ElasticProvisionedWorker(NEW_WORKER, "serena-local")

    provisioner = InterleavingProvisioner()
    coordinator = _coordinator(store, provisioner=provisioner, assembler=assembler)
    broker = _broker(store)

    def rival():
        published.wait(timeout=10)
        record = assembler.assemble(NEW_WORKER)
        observed_reserved.append(record.candidate.reserved)
        go.wait(timeout=10)
        return broker.acquire(
            _request("rival-s", "rival-t", NEW_WORKER), (record.candidate,)
        )

    with ThreadPoolExecutor(max_workers=1) as pool:
        rival_future = pool.submit(rival)
        owner_outcome = coordinator.provision_ready(
            _capacity_plan(),
            _request("owner-s", "owner-t", NEW_WORKER),
            runtime_kind="serena-local",
            policy=_policy(),
            eligibility={"node-1": NodeEligibility()},
        )
        rival_outcome = rival_future.result()

    assert observed_reserved == [False], (
        "rival must have observed the published worker as free inside the "
        "publication-before-mark window for this interleaving to be meaningful"
    )
    steal = (
        rival_outcome.kind is LeaseOutcomeKind.LEASED
        and owner_outcome.kind is ElasticCapacityOutcomeKind.PROVISIONED_READY
    )
    assert not steal, "rival leased the provisioned worker while the owner handoff was in flight"
    if owner_outcome.kind is ElasticCapacityOutcomeKind.PROVISIONED_READY:
        assert rival_outcome.kind is LeaseOutcomeKind.WAIT
    else:
        assert owner_outcome.kind is ElasticCapacityOutcomeKind.RECOVERY_REQUIRED
        assert owner_outcome.reason_code == "PROVISIONING_WORKER_LEASE_CONFLICT"
        assert rival_outcome.kind is LeaseOutcomeKind.LEASED


# ---------------------------------------------------------------------------
# Slice F — typed stale failure-residue reconcile
# ---------------------------------------------------------------------------


def _acquired(store, *, reservation_id="r-1", session_id="s-1", task_id="t-1"):
    result = store.acquire_provisioning_reservation(
        reservation_id=reservation_id,
        session_id=session_id,
        task_id=task_id,
        runtime_kind="serena-local",
        max_extra_workers=1,
        now=NOW,
    )
    assert result.kind.value == "ACQUIRED"
    return result


def test_reconcile_releases_stale_active_reservation_and_frees_budget(tmp_path: Path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    _acquired(store)
    record = store.reconcile_stale_provisioning(
        "r-1", session_id="s-1", task_id="t-1", now=LATER, stale_after_seconds=3600
    )
    assert record.state == "RELEASED"
    second = store.acquire_provisioning_reservation(
        reservation_id="r-2", session_id="s-2", task_id="t-2",
        runtime_kind="serena-local", max_extra_workers=1, now=LATER,
    )
    assert second.kind.value == "ACQUIRED"


def test_reconcile_refuses_fresh_reservation(tmp_path: Path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    _acquired(store)
    with pytest.raises(WorkerLeaseError, match="PROVISIONING_NOT_STALE"):
        store.reconcile_stale_provisioning(
            "r-1", session_id="s-1", task_id="t-1",
            now=NOW + timedelta(seconds=60), stale_after_seconds=3600,
        )


def test_reconcile_refuses_wrong_owner(tmp_path: Path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    _acquired(store)
    with pytest.raises(WorkerLeaseError, match="PROVISIONING_OWNER_MISMATCH"):
        store.reconcile_stale_provisioning(
            "r-1", session_id="other-s", task_id="t-1", now=LATER, stale_after_seconds=3600
        )


def test_reconcile_never_retires_capacity_by_age(tmp_path: Path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    _acquired(store)
    store.transition_provisioning_reservation(
        "r-1", session_id="s-1", task_id="t-1", state="PROVISIONED",
        now=NOW, worker_id=NEW_WORKER,
    )
    store.transition_provisioning_reservation(
        "r-1", session_id="s-1", task_id="t-1", state="CAPACITY",
        now=NOW, worker_id=NEW_WORKER,
    )
    with pytest.raises(WorkerLeaseError, match="PROVISIONING_CAPACITY_RETIREMENT_FORBIDDEN"):
        store.reconcile_stale_provisioning(
            "r-1", session_id="s-1", task_id="t-1", now=LATER, stale_after_seconds=3600
        )


def test_reconcile_refuses_provisioned_worker_with_active_lease(tmp_path: Path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    _acquired(store)
    store.transition_provisioning_reservation(
        "r-1", session_id="s-1", task_id="t-1", state="PROVISIONED",
        now=NOW, worker_id=NEW_WORKER,
    )
    leased = _broker(store).acquire(
        _request("s-1", "t-1", NEW_WORKER), (_hand_candidate(NEW_WORKER),)
    )
    assert leased.kind is LeaseOutcomeKind.LEASED
    with pytest.raises(WorkerLeaseError, match="PROVISIONING_WORKER_IN_USE"):
        store.reconcile_stale_provisioning(
            "r-1", session_id="s-1", task_id="t-1", now=LATER, stale_after_seconds=3600
        )


def test_reconcile_releases_stale_provisioned_and_recovery_residue(tmp_path: Path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    _acquired(store, reservation_id="r-1")
    store.transition_provisioning_reservation(
        "r-1", session_id="s-1", task_id="t-1", state="PROVISIONED",
        now=NOW, worker_id=NEW_WORKER,
    )
    released = store.reconcile_stale_provisioning(
        "r-1", session_id="s-1", task_id="t-1", now=LATER, stale_after_seconds=3600,
        worker_decommissioned=True,
    )
    assert released.state == "RELEASED"
    again = store.reconcile_stale_provisioning(
        "r-1", session_id="s-1", task_id="t-1", now=LATER, stale_after_seconds=3600
    )
    assert again.state == "RELEASED"

    _acquired(store, reservation_id="r-2", session_id="s-2", task_id="t-2")
    store.transition_provisioning_reservation(
        "r-2", session_id="s-2", task_id="t-2", state="RECOVERY_REQUIRED", now=NOW
    )
    recovered = store.reconcile_stale_provisioning(
        "r-2", session_id="s-2", task_id="t-2", now=LATER, stale_after_seconds=3600
    )
    assert recovered.state == "RELEASED"


def test_adapter_reconcile_maps_typed_errors(tmp_path: Path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    reservations = SQLiteWorkerProvisioningReservations(store)
    _acquired(store)
    with pytest.raises(ElasticCapacityError, match="PROVISIONING_NOT_STALE"):
        reservations.reconcile_stale(
            "r-1", session_id="s-1", task_id="t-1",
            now=NOW + timedelta(seconds=60), stale_after_seconds=3600,
        )


# ---------------------------------------------------------------------------
# Repair 002 — Blocker A: bound residue needs decommission evidence
# ---------------------------------------------------------------------------


def test_reconcile_refuses_bound_worker_without_decommission_evidence(
    tmp_path: Path,
) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    _acquired(store)
    store.transition_provisioning_reservation(
        "r-1", session_id="s-1", task_id="t-1", state="PROVISIONED",
        now=NOW, worker_id=NEW_WORKER,
    )
    with pytest.raises(
        WorkerLeaseError, match="PROVISIONING_WORKER_DECOMMISSION_EVIDENCE_REQUIRED"
    ):
        store.reconcile_stale_provisioning(
            "r-1", session_id="s-1", task_id="t-1",
            now=LATER, stale_after_seconds=3600,
        )
    second = store.acquire_provisioning_reservation(
        reservation_id="r-2", session_id="s-2", task_id="t-2",
        runtime_kind="serena-local", max_extra_workers=1, now=LATER,
    )
    assert second.kind.value == "LIMIT_WAIT", "bound residue must keep consuming budget"

    third = store.acquire_provisioning_reservation(
        reservation_id="r-3", session_id="s-3", task_id="t-3",
        runtime_kind="serena-local", max_extra_workers=3, now=NOW,
    )
    assert third.kind.value == "ACQUIRED"
    store.transition_provisioning_reservation(
        "r-3", session_id="s-3", task_id="t-3", state="RECOVERY_REQUIRED",
        now=NOW, worker_id="a-worker-10",
    )
    with pytest.raises(
        WorkerLeaseError, match="PROVISIONING_WORKER_DECOMMISSION_EVIDENCE_REQUIRED"
    ):
        store.reconcile_stale_provisioning(
            "r-3", session_id="s-3", task_id="t-3",
            now=LATER, stale_after_seconds=3600,
        )
    still_bound = store.acquire_provisioning_reservation(
        reservation_id="r-4", session_id="s-4", task_id="t-4",
        runtime_kind="serena-local", max_extra_workers=2, now=LATER,
    )
    assert still_bound.kind.value == "LIMIT_WAIT", (
        "bound recovery residue must keep consuming budget too"
    )


def test_reconcile_releases_bound_residue_only_with_decommission_evidence(
    tmp_path: Path,
) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    _acquired(store)
    store.transition_provisioning_reservation(
        "r-1", session_id="s-1", task_id="t-1", state="PROVISIONED",
        now=NOW, worker_id=NEW_WORKER,
    )
    released = store.reconcile_stale_provisioning(
        "r-1", session_id="s-1", task_id="t-1",
        now=LATER, stale_after_seconds=3600, worker_decommissioned=True,
    )
    assert released.state == "RELEASED"
    second = store.acquire_provisioning_reservation(
        reservation_id="r-2", session_id="s-2", task_id="t-2",
        runtime_kind="serena-local", max_extra_workers=1, now=LATER,
    )
    assert second.kind.value == "ACQUIRED"


# ---------------------------------------------------------------------------
# Repair 002 — Blocker B: mark_provisioned conflict persists recovery state
# ---------------------------------------------------------------------------


def test_mark_provisioned_conflict_persists_recovery_state(tmp_path: Path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    center = MutableControlCenter()
    assembler = _assembler(store, center)
    coordinator = _coordinator(
        store, provisioner=RegisteringProvisioner(center), assembler=assembler
    )
    rival = _broker(store).acquire(
        _request("rival-s", "rival-t", NEW_WORKER), (_hand_candidate(NEW_WORKER),)
    )
    assert rival.kind is LeaseOutcomeKind.LEASED
    outcome = coordinator.provision_ready(
        _capacity_plan(),
        _request("owner-s", "owner-t", NEW_WORKER),
        runtime_kind="serena-local",
        policy=_policy(),
        eligibility={"node-1": NodeEligibility()},
    )
    assert outcome.kind is ElasticCapacityOutcomeKind.RECOVERY_REQUIRED
    assert outcome.reason_code == "PROVISIONING_WORKER_LEASE_CONFLICT"
    reservations = store.list_provisioning_reservations(consuming_only=True)
    assert len(reservations) == 1
    assert reservations[0].state == "RECOVERY_REQUIRED", (
        "durable state must explain replay-unsafety instead of remaining ACTIVE"
    )
