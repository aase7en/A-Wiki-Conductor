"""Offline registered-root tests; all databases and effects are fixture-owned."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import test_parallel_ready_execution as helpers
from a_conductor import orchestration_dispatcher as dispatch
from a_conductor import runtime_activation as runtime
from a_conductor.a_faster_utilization_guard import (
    AFasterActivation, QuotaAdmission, UtilizationFacts,
)
from a_conductor.domain import TaskState
from a_conductor.graph.scheduler import SchedulePlan
from a_conductor.job_execution import JobBackendResult
from a_conductor.job_store import SQLiteJobStore
from a_conductor.orchestration import OrchestrationSignal
from a_conductor.orchestration_receiver import AdmittedContext
from a_conductor.pre_dispatch_guard import (
    LiveWorktreeIdentity, PreDispatchGuardDecision, PreDispatchGuardDecisionKind,
)
from a_conductor.provider_config_store import SQLiteProviderConfigStore
from a_conductor.provider_configuration import ProviderEndpointConfig
from a_conductor.worker_lease import (
    LeaseMutationIntent, LeaseOutcomeKind, SQLiteWorkerLeaseStore, WorkerLeaseBroker,
)


def signal(*, trigger="EXPLICIT", kind="ENQUEUE"):
    return OrchestrationSignal("orch-signal.v1", "signal:review", kind,
        "2026-10-27T00:00:00Z", "fixture-root", "a-sunday-conductor",
        {"target": "WORKER_BATCH", "intent_ref": "intent:review", "trigger": trigger,
         "ready_plan_ref": "plan:review", "task_map_ref": "map:review"},
        "task-review", "docs/tasks/review.md")


CONTEXT = AdmittedContext("fixture-root", "a-sunday-conductor", "task-review")


@pytest.fixture
def lane(tmp_path):
    database = tmp_path / "authority.sqlite"
    jobs = SQLiteJobStore(database)
    jobs.initialize()
    providers = SQLiteProviderConfigStore(database)
    profile = helpers._profile(max_concurrency=1)
    providers.save_endpoint(ProviderEndpointConfig(profile.endpoint_ref, "https://provider.example/v1"))
    providers.save_provider(profile)
    providers.save_observation(replace(helpers._observation(), configuration_generation=1))
    leases = SQLiteWorkerLeaseStore(database, hotspot_resolver=lambda _path: "fixture-hotspot")
    leases.list_active()
    task = helpers._task(node_id="review", worker_id="worker-review",
        worktree=str(tmp_path), branch="review", mutable_scope=("src/**",), profile=profile,
        provider_database_path=database)
    task = replace(task, lease_request=replace(task.lease_request,
        task_id="task-review", mutation_intent=LeaseMutationIntent.READ_ONLY, mutable_scope=()))
    jobs.create_job(job_id=task.dispatch_request.key.job_id,
        work_order_ref=task.dispatch_request.work_order_ref,
        project_id=task.dispatch_request.project_id, max_attempts=task.dispatch_request.max_attempts)
    state = SimpleNamespace(task=task, jobs=jobs, providers=providers, leases=leases,
        use_reason=None, after_audit=False, before_audit=False, drift=None,
        calls=0, reads=[], started=Event(), release=Event(), block=False)
    intent = dispatch.WorkerIntent("task-review", "intent:review", "review",
        task.dispatch_request.project_id, ("src/**",))
    facts = UtilizationFacts(activation=AFasterActivation.ACTIVE,
        occupied_mutable_lanes=0, occupied_review_lanes=0,
        ready_mutable_candidates=0, ready_review_candidates=1,
        glm_quota_admission=QuotaAdmission.QUOTA_AVAILABLE, glm_route_ready=True)
    batch = dispatch.WorkerBatch("plan:review", "map:review", "generation:1",
        SchedulePlan(selected=(task.assignment,), blocked=(), capacity_evidence="fixture"), (task,), facts,
        ("evidence:canonical-ready",))
    state.intent, state.batch = intent, batch

    class Authority:
        def read_intent(self, current):
            state.reads.append("intent")
            return state.intent

        def read_batch(self, current):
            state.reads.append("batch")
            return state.batch

        def check(self, task_ref, scope):
            state.reads.append("authority")
            return task_ref == state.intent.task_ref and scope == state.intent.scope

        def check_at_use(self, current, baseline):
            state.reads.append("use")
            if state.drift:
                state.drift()
            return PreDispatchGuardDecision(
                PreDispatchGuardDecisionKind.DENY if state.use_reason else PreDispatchGuardDecisionKind.ALLOW,
                state.use_reason or "PRE_DISPATCH_ALLOWED")

    class Backend:
        def execute(self, operation_ref, context):
            state.calls += 1
            state.started.set()
            if state.block:
                assert state.release.wait(5)
            if state.after_audit:
                state.jobs.checkpoint = Mock(side_effect=RuntimeError("private audit failure"))
            return JobBackendResult(True, "evidence:fixture-result")

    class Observer:
        def observe(self, root):
            state.reads.append("head")
            return LiveWorktreeIdentity(root, "review", state.head)

    state.head = helpers.HEAD
    state.authority = Authority()
    state.make_root = lambda **kwargs: runtime.activate_worker_batch_runtime(
        database_path=database, job_store=jobs, provider_store=providers,
        lease_store=leases, backend=Backend(), authority=state.authority,
        live_worktree_observer=Observer(), trusted_source="fixture-root",
        review_worker_id="worker-review", review_provider_id="cointh-glm",
        clock=lambda: helpers.NOW, **kwargs)
    return state


def test_registered_root_happy_path_durable_ids_and_no_ambient_activation(lane):
    root = lane.make_root()
    assert lane.calls == 0 and lane.reads == []
    outcome = root.handle(signal(trigger="REFILL"), admitted=CONTEXT)
    assert outcome.decision == "DISPATCH_OBSERVED"
    assert outcome.execution_ids == (lane.task.dispatch_request.key.job_id,)
    assert lane.jobs.get_job(outcome.execution_ids[0]).state is TaskState.VERIFYING
    assert lane.calls == 1
    assert {"intent", "batch", "authority", "use", "head"} <= set(lane.reads)
    assert outcome.evidence_refs and not outcome.observability_degraded
    with pytest.raises(FrozenInstanceError):
        outcome.decision = "NO_ACTION"


def test_duplicate_and_repeated_invocation_have_zero_new_effects(lane):
    root = lane.make_root()
    first = root.handle(signal(), admitted=CONTEXT)
    events = lane.jobs.list_events(first.execution_ids[0])
    admissions = lane.providers.list_provider_admissions(provider_id="cointh-glm")
    leases = lane.leases.list_active()
    for _ in range(3):
        repeated = root.handle(signal(), admitted=CONTEXT)
        assert repeated.decision == "NO_ACTION"
        assert repeated.execution_ids == first.execution_ids
    assert lane.calls == 1
    assert lane.jobs.list_events(first.execution_ids[0]) == events
    assert lane.providers.list_provider_admissions(provider_id="cointh-glm") == admissions
    assert lane.leases.list_active() == leases
    # A fresh application instance cannot use signal-ID hygiene as dedup authority.
    cold = lane.make_root().handle(replace(signal(), signal_id="signal:cold"), admitted=CONTEXT)
    assert cold.reason_code == "JOB_ALREADY_VERIFYING"
    assert lane.jobs.list_events(first.execution_ids[0]) == events
    assert lane.providers.list_provider_admissions(provider_id="cointh-glm") == admissions
    assert lane.calls == 1


@pytest.mark.parametrize("task_class", ["mutable", "unknown"])
@pytest.mark.parametrize("trigger", ["REFILL", "EXPLICIT"])
def test_nonreview_denied_before_scheduler_provider_lease(lane, task_class, trigger):
    lane.intent = replace(lane.intent, task_class=task_class)
    lane.authority.read_batch = Mock(side_effect=AssertionError("scheduler effect"))
    lane.providers.acquire_admission = Mock(side_effect=AssertionError("provider effect"))
    lane.leases.list_active = Mock(side_effect=AssertionError("lease effect"))
    outcome = lane.make_root().handle(signal(trigger=trigger), admitted=CONTEXT)
    assert outcome.decision == "DENIED"
    expected = ("CANONICAL_MUTABLE_CLAIM_AUTHORITY_UNAVAILABLE"
                if task_class == "mutable" else "ORCH_WORKER_REVIEW_ONLY")
    assert outcome.reason_code == expected
    lane.authority.read_batch.assert_not_called()
    lane.providers.acquire_admission.assert_not_called()
    lane.leases.list_active.assert_not_called()


@pytest.mark.parametrize("drift", ["claim", "provider", "head", "result", "generation", "lease"])
def test_late_drift_at_use_never_launches(lane, drift):
    if drift == "claim":
        lane.use_reason = "CLAIM_BINDING_DRIFT"
    elif drift == "provider":
        lane.drift = lambda: lane.providers.save_observation(
            replace(helpers._observation(), configuration_generation=99))
    elif drift == "head":
        lane.drift = lambda: setattr(lane, "head", "f" * 40)
    elif drift == "result":
        lane.drift = lambda: lane.jobs.checkpoint(lane.task.dispatch_request.key.job_id,
            expected_version=lane.jobs.get_job(lane.task.dispatch_request.key.job_id).version,
            checkpoint_ref="evidence:late-result")
    elif drift == "generation":
        lane.drift = lambda: setattr(lane, "batch", replace(lane.batch, ready_generation="generation:2"))
    else:
        lane.drift = lambda: lane.leases.release(lane.leases.list_active()[0].lease_id,
            session_id=lane.task.lease_request.session_id, task_id=lane.intent.task_ref,
            released_at=helpers.NOW)
    outcome = lane.make_root().handle(signal(), admitted=CONTEXT)
    assert outcome.decision == "RECONCILIATION_REQUIRED"
    assert lane.calls == 0


def test_two_producers_same_hotspot_atomic_capacity(lane):
    lane.block = True
    left, right = lane.make_root(), lane.make_root()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(left.handle, signal(), admitted=CONTEXT)
        assert lane.started.wait(5)
        second = right.handle(signal(), admitted=CONTEXT)
        assert second.decision in ("NO_ACTION", "RECONCILIATION_REQUIRED", "DENIED")
        lane.release.set()
        result = first.result(timeout=5)
    assert lane.calls == 1
    assert result.execution_ids


@pytest.mark.parametrize("when", ["before", "after"])
def test_required_audit_failure_never_replays(lane, when):
    lane.after_audit = when == "after"
    if when == "before":
        lane.jobs.checkpoint = Mock(side_effect=RuntimeError("private audit failure"))
    root = lane.make_root()
    result = root.handle(signal(), admitted=CONTEXT)
    assert result.decision == "RECONCILIATION_REQUIRED"
    assert lane.calls == (1 if when == "after" else 0)
    if when == "after":
        assert result.execution_ids == (lane.task.dispatch_request.key.job_id,)
        assert result.observability_degraded
        root.handle(signal(), admitted=CONTEXT)
        assert lane.calls == 1


def test_unknown_serialization_fails_closed(lane):
    task = replace(lane.task, provider_profile=helpers._profile(max_concurrency=2))
    lane.batch = replace(lane.batch, tasks=(task,))
    result = lane.make_root().handle(signal(), admitted=CONTEXT)
    assert result.reason_code == "ORCH_WORKER_SERIALIZATION_UNPROVEN"
    assert lane.calls == 0


@pytest.mark.parametrize("occupied,quota", [(1, QuotaAdmission.QUOTA_AVAILABLE),
    (0, QuotaAdmission.QUOTA_UNKNOWN)])
def test_authority_classifier_facts_deny_refill(lane, occupied, quota):
    lane.batch = replace(lane.batch, utilization_facts=replace(lane.batch.utilization_facts,
        occupied_review_lanes=occupied, glm_quota_admission=quota))
    result = lane.make_root().handle(signal(trigger="REFILL"), admitted=CONTEXT)
    assert result.decision in ("DENIED", "RECONCILIATION_REQUIRED")
    assert lane.calls == 0


def test_observer_failure_degrades_without_relaunch(lane):
    publisher = Mock(side_effect=RuntimeError("telemetry lost"))
    root = lane.make_root(publisher=publisher)
    outcome = root.handle(signal(), admitted=CONTEXT)
    assert outcome.decision == "DISPATCH_OBSERVED"
    assert outcome.observability_degraded
    root.handle(signal(), admitted=CONTEXT)
    assert lane.calls == 1


def test_wrong_source_and_caller_admission_cannot_authorize(lane):
    root = lane.make_root()
    result = root.handle(replace(signal(), source_ref="foreign"), admitted=CONTEXT)
    assert result.reason_code == "SIGNAL_SOURCE_MISMATCH"
    assert lane.reads == [] and lane.calls == 0
    result = root.handle(signal(), admitted=True)
    assert result.reason_code == "ADMITTED_CONTEXT_INVALID"
    assert lane.reads == [] and lane.calls == 0


def test_foreign_work_order_cannot_select_task(lane):
    outcome = lane.make_root().handle(replace(signal(), work_order_ref="foreign"), admitted=CONTEXT)
    assert outcome.decision == "RECONCILIATION_REQUIRED"
    assert lane.calls == 0
    assert lane.providers.list_provider_admissions(provider_id="cointh-glm") == ()


def test_backend_use_gate_rejects_late_result_checkpoint(lane):
    original = lane.jobs.transition
    def transition(job_id, target, **kwargs):
        result = original(job_id, target, **kwargs)
        if target is TaskState.EXECUTING:
            lane.jobs.checkpoint(job_id, expected_version=result.version,
                checkpoint_ref="evidence:late-result")
        return result
    lane.jobs.transition = transition
    outcome = lane.make_root().handle(signal(), admitted=CONTEXT)
    assert outcome.decision == "RECONCILIATION_REQUIRED"
    assert lane.calls == 0


def test_canonical_database_identity_mismatch_refused(lane, tmp_path):
    lane.providers.database_path = tmp_path / "foreign.sqlite"
    with pytest.raises(ValueError, match="AUTHORITY_DATABASE_IDENTITY_MISMATCH"):
        lane.make_root()


def test_publisher_cannot_reenter_dispatch(lane):
    outcomes = []
    def publish(_outcome):
        outcomes.append(root.handle(signal(), admitted=CONTEXT))
    root = lane.make_root(publisher=publish)
    result = root.handle(signal(), admitted=CONTEXT)
    assert result.decision == "DISPATCH_OBSERVED"
    assert len(outcomes) == 1
    assert outcomes[0].reason_code == "ORCH_REENTRANT_DENIED"
    assert lane.calls == 1


def test_explicit_review_respects_global_occupancy(lane):
    lane.batch = replace(lane.batch, utilization_facts=replace(lane.batch.utilization_facts,
        occupied_review_lanes=1))
    result = lane.make_root().handle(signal(), admitted=CONTEXT)
    assert result.decision == "DENIED"
    assert result.reason_code == "CAPACITY_EXHAUSTED"
    assert lane.calls == 0


def test_backend_use_gate_after_job_transitions(lane):
    original = lane.jobs.transition
    def transition(job_id, target, **kwargs):
        result = original(job_id, target, **kwargs)
        if target is TaskState.EXECUTING:
            lane.head = "f" * 40
        return result
    lane.jobs.transition = transition
    outcome = lane.make_root().handle(signal(), admitted=CONTEXT)
    assert outcome.decision == "RECONCILIATION_REQUIRED"
    assert lane.calls == 0


def test_distinct_jobs_contend_on_existing_provider_capacity(lane):
    lane.block = True
    left, right = lane.make_root(), lane.make_root()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(left.handle, signal(), admitted=CONTEXT)
        try:
            assert lane.started.wait(5)
            task = helpers._task(node_id="review2", worker_id="worker-review",
                worktree=lane.task.lease_request.worktree, branch="review",
                mutable_scope=("src/**",), profile=lane.task.provider_profile,
                provider_database_path=lane.jobs.database_path)
            task = replace(task, lease_request=replace(task.lease_request,
                mutation_intent=LeaseMutationIntent.READ_ONLY, mutable_scope=()))
            lane.jobs.create_job(job_id=task.dispatch_request.key.job_id,
                work_order_ref=task.dispatch_request.work_order_ref,
                project_id=task.dispatch_request.project_id, max_attempts=task.dispatch_request.max_attempts)
            lane.intent = replace(lane.intent, task_ref="task-review2")
            lane.batch = replace(lane.batch, tasks=(task,), plan=SchedulePlan(
                selected=(task.assignment,), blocked=(), capacity_evidence="fixture"))
            second = right.handle(replace(signal(), task_ref="task-review2",
                work_order_ref=task.dispatch_request.work_order_ref),
                admitted=replace(CONTEXT, task_ref="task-review2"))
            assert second.reason_code == "PROVIDER_CAPACITY_EXHAUSTED"
            assert lane.calls == 1
            assert len(lane.providers.list_provider_admissions(provider_id="cointh-glm")) == 1
            assert len(lane.leases.list_active()) == 1
        finally:
            lane.release.set()
        assert first.result(timeout=5).decision == "DISPATCH_OBSERVED"


@pytest.mark.parametrize("field", ["source_ref", "project_id", "task_ref"])
def test_separate_ingress_mismatch_denies_before_authority_reads(lane, field):
    result = lane.make_root().handle(signal(), admitted=replace(CONTEXT, **{field: "foreign"}))
    assert result.reason_code == "ADMITTED_CONTEXT_MISMATCH"
    assert lane.reads == [] and lane.calls == 0


def test_registered_root_uses_actual_pipeline_and_authority_facts(lane, monkeypatch):
    from a_conductor.orchestration_guards import GuardPipeline
    original = GuardPipeline.evaluate
    calls = []
    def evaluate(self, current, **kwargs):
        result = original(self, current, **kwargs)
        calls.append((current, kwargs, result))
        return result
    monkeypatch.setattr(GuardPipeline, "evaluate", evaluate)
    result = lane.make_root().handle(signal(trigger="REFILL"), admitted=CONTEXT)
    assert result.decision == "DISPATCH_OBSERVED"
    assert len(calls) == 1
    assert calls[0][1]["utilization_facts"] is lane.batch.utilization_facts
    assert calls[0][2].metadata["duplicate"] == {"worker_dedup": "DELEGATED_TO_EXECUTOR_ADMISSION"}
    assert result.evidence_refs == ("evidence:canonical-ready", "evidence:fixture-result")


def test_runtime_registration_does_not_initialize_or_read_stores(lane, monkeypatch):
    for store, methods in ((lane.jobs, ("initialize", "get_job")),
            (lane.providers, ("load_provider_snapshot", "acquire_admission")),
            (lane.leases, ("list_active", "inspect_health"))):
        for method in methods:
            monkeypatch.setattr(store, method, Mock(side_effect=AssertionError("ambient I/O")))
    root = lane.make_root()
    assert callable(root.handle)
    assert lane.reads == [] and lane.calls == 0


def test_existing_worker_lease_caps_review_slot(lane):
    broker = WorkerLeaseBroker(store=lane.leases, lease_id_factory=lambda: "fixture:other-lease",
        clock=lambda: helpers.NOW)
    occupied = broker.acquire(replace(lane.task.lease_request,
        session_id="other-session", task_id="other-task"), lane.task.candidates)
    assert occupied.kind is LeaseOutcomeKind.LEASED
    result = lane.make_root().handle(signal(), admitted=CONTEXT)
    assert result.decision == "RECONCILIATION_REQUIRED"
    assert lane.calls == 0
    assert lane.leases.list_active() == (occupied.lease,)


@pytest.mark.parametrize("drift", ["claim", "provider", "lease", "generation"])
def test_backend_use_revalidates_all_authorities(lane, drift):
    original = lane.jobs.transition
    def transition(job_id, target, **kwargs):
        result = original(job_id, target, **kwargs)
        if target is TaskState.EXECUTING:
            if drift == "claim":
                lane.use_reason = "CLAIM_BINDING_DRIFT"
            elif drift == "provider":
                lane.providers.save_observation(replace(helpers._observation(), configuration_generation=99))
            elif drift == "generation":
                lane.batch = replace(lane.batch, ready_generation="generation:2")
            else:
                lease = lane.leases.list_active()[0]
                lane.leases.release(lease.lease_id, session_id=lease.session_id,
                    task_id=lease.task_id, released_at=helpers.NOW)
        return result
    lane.jobs.transition = transition
    result = lane.make_root().handle(signal(), admitted=CONTEXT)
    assert result.decision == "RECONCILIATION_REQUIRED"
    assert lane.calls == 0
