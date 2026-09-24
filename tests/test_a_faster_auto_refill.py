from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from a_conductor.a_faster_auto_refill import (
    AutoRefillDisposition,
    RefillLaneKind,
    execute_auto_refill as _execute_auto_refill,
)
from a_conductor.a_faster_utilization_guard import (
    AFasterActivation,
    QuotaAdmission,
    UtilizationFacts,
    classify_utilization,
)
from a_conductor.claude_code_harness import MutationIntent
from a_conductor.elastic_wip_policy import ElasticWipFacts, GateState
from a_conductor.graph.domain import TaskGraph, TaskNode
from a_conductor.graph.ready import compute_ready_set
from a_conductor.graph.scheduler import (
    NodeEligibility,
    SchedulePlan,
    SchedulePolicy,
    SelectedAssignment,
)
from a_conductor.parallel_ready_execution import (
    ParallelReadyBatchResult,
    ParallelReadyOutcome,
    ParallelReadyOutcomeKind,
    ParallelReadyTask,
)
from a_conductor.worker_lease import LeaseMutationIntent


class FakeExecutor:
    def __init__(
        self,
        *,
        fail: bool = False,
        mismatch: bool = False,
        provider_authority: bool = True,
        pre_dispatch_guard: bool = True,
    ) -> None:
        self.calls: list[dict[str, object]] = []
        self.fail = fail
        self.mismatch = mismatch
        self.requires_provider_authority = provider_authority
        self.pre_dispatch_guard_enforced = pre_dispatch_guard

    def execute(
        self,
        plan,
        tasks_by_node,
        *,
        provider_inflight,
        batch_id=None,
        pre_acquired_admissions=None,
    ):
        self.calls.append(
            {
                "plan": plan,
                "tasks": dict(tasks_by_node),
                "provider_inflight": dict(provider_inflight),
                "batch_id": batch_id,
                "pre_acquired_admissions": dict(pre_acquired_admissions or {}),
            }
        )
        if self.fail:
            raise RuntimeError("raw provider detail must not escape")
        node_ids = [item.node_id for item in plan.selected]
        if self.mismatch:
            node_ids = ["wrong-node"]
        outcomes = tuple(
            ParallelReadyOutcome(
                node_id=node_id,
                kind=ParallelReadyOutcomeKind.RUN_COMPLETED,
                reason_code="RUNNER_COMPLETED",
                runner_result=object(),
            )
            for node_id in node_ids
        )
        return ParallelReadyBatchResult(outcomes=outcomes)


_POLICY_EVIDENCE: dict[int, tuple[UtilizationFacts, ElasticWipFacts]] = {}


def _verdict(
    *,
    occupied_mutable: int = 1,
    ready_mutable: int = 3,
    occupied_review: int = 1,
    ready_review: int = 0,
):
    facts = UtilizationFacts(
        activation=AFasterActivation.ACTIVE,
        occupied_mutable_lanes=occupied_mutable,
        occupied_review_lanes=occupied_review,
        ready_mutable_candidates=ready_mutable,
        ready_review_candidates=ready_review,
        glm_route_ready=True,
        glm_quota_admission=QuotaAdmission.QUOTA_AVAILABLE,
    )
    verdict = classify_utilization(facts)
    wip = ElasticWipFacts(
        base_active=occupied_mutable,
        review_claimed=occupied_review,
        ready_independent_candidates=ready_mutable,
        scope_gate=GateState.READY,
        claim_gate=GateState.READY,
        runtime_gate=GateState.READY,
    )
    _POLICY_EVIDENCE[id(verdict)] = (facts, wip)
    return verdict


def _ready_for_plan(plan: SchedulePlan):
    graph = TaskGraph()
    for node_id in dict.fromkeys(item.node_id for item in plan.selected):
        graph.add_node(TaskNode(id=node_id, objective=f"ready {node_id}"))
    return compute_ready_set(graph, {})


def execute_auto_refill(**kwargs):
    verdict = kwargs["verdict"]
    facts, wip = _POLICY_EVIDENCE.get(
        id(verdict),
        (
            UtilizationFacts(activation=AFasterActivation.NOT_INVOKED),
            ElasticWipFacts(
                scope_gate=GateState.READY,
                claim_gate=GateState.READY,
                runtime_gate=GateState.READY,
            ),
        ),
    )
    kwargs.setdefault("facts", facts)
    kwargs.setdefault("wip_facts", wip)
    kwargs.setdefault("ready", _ready_for_plan(kwargs["plan"]))
    return _execute_auto_refill(**kwargs)


def _task(
    intent: LeaseMutationIntent = LeaseMutationIntent.MUTATION,
    *,
    harness_intent: MutationIntent | None = None,
    require_quota: bool = True,
) -> ParallelReadyTask:
    task = object.__new__(ParallelReadyTask)
    object.__setattr__(
        task,
        "lease_request",
        SimpleNamespace(mutation_intent=intent),
    )
    object.__setattr__(
        task,
        "harness_dispatch",
        SimpleNamespace(
            mutation_intent=(
                harness_intent
                if harness_intent is not None
                else (
                    MutationIntent.PROJECT_MUTATION
                    if intent is LeaseMutationIntent.MUTATION
                    else MutationIntent.READ_ONLY
                )
            )
        ),
    )
    object.__setattr__(task, "require_quota", require_quota)
    object.__setattr__(task, "provider_requirement", object())
    object.__setattr__(task, "provider_endpoint", object())
    object.__setattr__(task, "provider_security", object())
    object.__setattr__(task, "expected_configuration_generation", 1)
    return task


def _plan(*node_ids: str) -> SchedulePlan:
    return SchedulePlan(
        selected=tuple(
            SelectedAssignment(node_id=node_id, worker_id=f"worker-{index}")
            for index, node_id in enumerate(node_ids, start=1)
        ),
        blocked=(),
        capacity_evidence="scheduler-owned",
    )


def test_executes_only_mutable_fanout_target_from_scheduler_plan() -> None:
    executor = FakeExecutor()
    verdict = _verdict(occupied_mutable=1, ready_mutable=3)
    plan = _plan("a", "b", "c")
    tasks = {node: _task() for node in ("a", "b", "c")}

    result = execute_auto_refill(
        verdict=verdict,
        lane_kind=RefillLaneKind.MUTABLE,
        plan=plan,
        tasks_by_node=tasks,
        provider_inflight={"cointh-glm": 0},
        executor=executor,
        batch_id="batch-1",
    )

    assert result.disposition is AutoRefillDisposition.EXECUTED
    assert result.reason_code == "AUTO_REFILL_EXECUTED"
    assert result.selected_node_ids == ("a", "b")
    assert len(executor.calls) == 1
    call = executor.calls[0]
    assert tuple(item.node_id for item in call["plan"].selected) == ("a", "b")
    assert tuple(call["tasks"]) == ("a", "b")
    assert call["batch_id"] == "batch-1"


def test_inactive_or_explanation_only_verdict_never_dispatches() -> None:
    for activation in (
        AFasterActivation.NOT_INVOKED,
        AFasterActivation.EXPLANATION_ONLY,
    ):
        verdict = classify_utilization(
            UtilizationFacts(
                activation=activation,
                ready_mutable_candidates=2,
            )
        )
        executor = FakeExecutor()
        result = execute_auto_refill(
            verdict=verdict,
            lane_kind=RefillLaneKind.MUTABLE,
            plan=_plan("a"),
            tasks_by_node={"a": _task()},
            provider_inflight={"cointh-glm": 0},
            executor=executor,
        )
        assert result.disposition is AutoRefillDisposition.FAIL_CLOSED
        assert result.reason_code == "A_FASTER_NOT_ACTIVE"
        assert executor.calls == []


def test_no_refill_marker_is_a_noop() -> None:
    verdict = _verdict(
        occupied_mutable=3,
        ready_mutable=0,
        occupied_review=1,
        ready_review=0,
    )
    executor = FakeExecutor()
    result = execute_auto_refill(
        verdict=verdict,
        lane_kind=RefillLaneKind.MUTABLE,
        plan=_plan(),
        tasks_by_node={},
        provider_inflight={"cointh-glm": 0},
        executor=executor,
    )
    assert result.disposition is AutoRefillDisposition.NO_REFILL_REQUIRED
    assert result.reason_code == "AUTO_REFILL_NOT_REQUIRED"
    assert executor.calls == []


def test_missing_or_extra_task_mapping_fails_before_execute() -> None:
    verdict = _verdict(occupied_mutable=1, ready_mutable=2)
    for tasks in ({"a": _task()}, {"a": _task(), "b": _task(), "x": _task()}):
        executor = FakeExecutor()
        result = execute_auto_refill(
            verdict=verdict,
            lane_kind=RefillLaneKind.MUTABLE,
            plan=_plan("a", "b"),
            tasks_by_node=tasks,
            provider_inflight={"cointh-glm": 0},
            executor=executor,
        )
        assert result.disposition is AutoRefillDisposition.FAIL_CLOSED
        assert result.reason_code == "SCHEDULE_TASK_MAPPING_DRIFT"
        assert executor.calls == []


def test_duplicate_schedule_identity_fails_before_execute() -> None:
    verdict = _verdict(occupied_mutable=1, ready_mutable=2)
    duplicate = SchedulePlan(
        selected=(
            SelectedAssignment("a", "worker-1"),
            SelectedAssignment("a", "worker-2"),
        ),
        blocked=(),
        capacity_evidence="scheduler-owned",
    )
    executor = FakeExecutor()
    result = execute_auto_refill(
        verdict=verdict,
        lane_kind=RefillLaneKind.MUTABLE,
        plan=duplicate,
        tasks_by_node={"a": _task()},
        provider_inflight={"cointh-glm": 0},
        executor=executor,
    )
    assert result.disposition is AutoRefillDisposition.FAIL_CLOSED
    assert result.reason_code == "SCHEDULE_IDENTITY_INVALID"
    assert executor.calls == []


def test_scheduler_may_select_less_than_target_without_manufactured_work() -> None:
    verdict = _verdict(occupied_mutable=0, ready_mutable=3)
    executor = FakeExecutor()
    result = execute_auto_refill(
        verdict=verdict,
        lane_kind=RefillLaneKind.MUTABLE,
        plan=_plan("only-safe"),
        tasks_by_node={"only-safe": _task()},
        provider_inflight={"cointh-glm": 0},
        executor=executor,
    )
    assert result.disposition is AutoRefillDisposition.EXECUTED
    assert result.selected_node_ids == ("only-safe",)
    assert len(executor.calls) == 1


def test_review_refill_uses_independent_review_budget_only() -> None:
    verdict = _verdict(
        occupied_mutable=3,
        ready_mutable=0,
        occupied_review=0,
        ready_review=2,
    )
    executor = FakeExecutor()
    result = execute_auto_refill(
        verdict=verdict,
        lane_kind=RefillLaneKind.REVIEW,
        plan=_plan("review-a", "review-b"),
        tasks_by_node={
            "review-a": _task(LeaseMutationIntent.READ_ONLY),
            "review-b": _task(LeaseMutationIntent.READ_ONLY),
        },
        provider_inflight={"cointh-glm": 0},
        executor=executor,
    )
    assert result.disposition is AutoRefillDisposition.EXECUTED
    assert result.selected_node_ids == ("review-a",)
    assert tuple(executor.calls[0]["tasks"]) == ("review-a",)


def test_preacquired_admission_outside_bounded_batch_fails_closed() -> None:
    verdict = _verdict(occupied_mutable=2, ready_mutable=2)
    executor = FakeExecutor()
    result = execute_auto_refill(
        verdict=verdict,
        lane_kind=RefillLaneKind.MUTABLE,
        plan=_plan("a", "b"),
        tasks_by_node={"a": _task(), "b": _task()},
        provider_inflight={"cointh-glm": 0},
        executor=executor,
        pre_acquired_admissions={"b": object()},
    )
    assert result.disposition is AutoRefillDisposition.FAIL_CLOSED
    assert result.reason_code == "PREACQUIRED_ADMISSION_OUTSIDE_REFILL"
    assert executor.calls == []


def test_executor_exception_is_bounded_fail_closed_result() -> None:
    verdict = _verdict(occupied_mutable=2, ready_mutable=1)
    executor = FakeExecutor(fail=True)
    result = execute_auto_refill(
        verdict=verdict,
        lane_kind=RefillLaneKind.MUTABLE,
        plan=_plan("a"),
        tasks_by_node={"a": _task()},
        provider_inflight={"cointh-glm": 0},
        executor=executor,
    )
    assert result.disposition is AutoRefillDisposition.FAIL_CLOSED
    assert result.reason_code == "REFILL_EXECUTION_RECONCILE_REQUIRED"
    assert result.selected_node_ids == ("a",)
    assert "provider detail" not in repr(result)


def test_executor_result_identity_mismatch_requires_recovery() -> None:
    verdict = _verdict(occupied_mutable=2, ready_mutable=1)
    executor = FakeExecutor(mismatch=True)
    result = execute_auto_refill(
        verdict=verdict,
        lane_kind=RefillLaneKind.MUTABLE,
        plan=_plan("a"),
        tasks_by_node={"a": _task()},
        provider_inflight={"cointh-glm": 0},
        executor=executor,
    )
    assert result.disposition is AutoRefillDisposition.FAIL_CLOSED
    assert result.reason_code == "REFILL_RESULT_IDENTITY_MISMATCH"
    assert result.selected_node_ids == ("a",)


def test_task_mapping_values_must_be_parallel_ready_tasks() -> None:
    verdict = _verdict(occupied_mutable=2, ready_mutable=1)
    executor = FakeExecutor()
    result = execute_auto_refill(
        verdict=verdict,
        lane_kind=RefillLaneKind.MUTABLE,
        plan=_plan("a"),
        tasks_by_node={"a": object()},
        provider_inflight={"cointh-glm": 0},
        executor=executor,
    )
    assert result.disposition is AutoRefillDisposition.FAIL_CLOSED
    assert result.reason_code == "REFILL_TASK_INVALID"
    assert executor.calls == []


def test_lane_kind_must_match_task_mutation_intent() -> None:
    mutable_verdict = _verdict(occupied_mutable=2, ready_mutable=1)
    mutable_executor = FakeExecutor()
    mutable_result = execute_auto_refill(
        verdict=mutable_verdict,
        lane_kind=RefillLaneKind.MUTABLE,
        plan=_plan("a"),
        tasks_by_node={"a": _task(LeaseMutationIntent.READ_ONLY)},
        provider_inflight={"cointh-glm": 0},
        executor=mutable_executor,
    )
    assert mutable_result.disposition is AutoRefillDisposition.FAIL_CLOSED
    assert mutable_result.reason_code == "REFILL_TASK_AUTHORITY_INCOMPLETE"
    assert mutable_executor.calls == []

    review_verdict = _verdict(
        occupied_mutable=3,
        ready_mutable=0,
        occupied_review=0,
        ready_review=1,
    )
    review_executor = FakeExecutor()
    review_result = execute_auto_refill(
        verdict=review_verdict,
        lane_kind=RefillLaneKind.REVIEW,
        plan=_plan("review-a"),
        tasks_by_node={"review-a": _task(LeaseMutationIntent.MUTATION)},
        provider_inflight={"cointh-glm": 0},
        executor=review_executor,
    )
    assert review_result.disposition is AutoRefillDisposition.FAIL_CLOSED
    assert review_result.reason_code == "REFILL_TASK_AUTHORITY_INCOMPLETE"
    assert review_executor.calls == []


def _production_entrypoint_fixture(monkeypatch):
    from a_conductor import elastic_worker_capacity as module

    production = object.__new__(module.ProductionElasticWorkerExecutor)
    executor = FakeExecutor()
    production._executor = executor

    graph = TaskGraph()
    for node_id in ("a", "b", "c"):
        graph.add_node(TaskNode(id=node_id, objective=f"task {node_id}"))
    ready = compute_ready_set(graph, {})

    contracts = {
        node_id: SimpleNamespace(
            provider_requirement=object(),
            dispatch_gate=SimpleNamespace(allowed=True),
        )
        for node_id in ("a", "b", "c")
    }
    eligibility = {node_id: NodeEligibility() for node_id in contracts}
    plan = _plan("a", "b", "c")

    monkeypatch.setattr(
        production,
        "_provider_eligibility",
        lambda contract, current: (current, None),
    )
    monkeypatch.setattr(
        production,
        "_supply_snapshot",
        lambda: SimpleNamespace(scheduler_workers=()),
    )
    monkeypatch.setattr(module, "schedule_once", lambda *args, **kwargs: plan)
    monkeypatch.setattr(
        module,
        "assemble_parallel_ready_tasks",
        lambda selected_plan, selected_contracts, supply: {
            item.node_id: _task() for item in selected_plan.selected
        },
    )
    return module, production, executor, graph, ready, contracts, eligibility


def test_production_execute_once_uses_a_faster_refill_target(monkeypatch) -> None:
    (
        module,
        production,
        executor,
        graph,
        ready,
        contracts,
        eligibility,
    ) = _production_entrypoint_fixture(monkeypatch)

    verdict = _verdict(occupied_mutable=1, ready_mutable=3)
    facts, wip = _POLICY_EVIDENCE[id(verdict)]
    result = production.execute_once(
        graph,
        ready,
        contracts,
        schedule_policy=SchedulePolicy(max_parallel=3),
        provider_inflight={"cointh-glm": 0},
        runtime_kind="serena-local",
        elastic_policy=module.ElasticCapacityPolicy(
            enabled=False,
            max_extra_workers=0,
            permitted_runtime_kinds=(),
        ),
        eligibility=eligibility,
        batch_id="batch-production-refill",
        a_faster_facts=facts,
        a_faster_verdict=verdict,
        a_faster_wip_facts=wip,
        a_faster_lane_kind=RefillLaneKind.MUTABLE,
    )

    assert result.kind is module.ProductionElasticExecutionKind.FIXED_POOL_EXECUTED
    assert len(executor.calls) == 1
    assert tuple(
        item.node_id for item in executor.calls[0]["plan"].selected
    ) == ("a", "b")
    assert result.batch_result is not None
    assert tuple(item.node_id for item in result.batch_result.outcomes) == ("a", "b")


def test_production_execute_once_legacy_path_remains_unbounded_by_a_faster(
    monkeypatch,
) -> None:
    (
        module,
        production,
        executor,
        graph,
        ready,
        contracts,
        eligibility,
    ) = _production_entrypoint_fixture(monkeypatch)

    result = production.execute_once(
        graph,
        ready,
        contracts,
        schedule_policy=SchedulePolicy(max_parallel=3),
        provider_inflight={"cointh-glm": 0},
        runtime_kind="serena-local",
        elastic_policy=module.ElasticCapacityPolicy(
            enabled=False,
            max_extra_workers=0,
            permitted_runtime_kinds=(),
        ),
        eligibility=eligibility,
        batch_id="batch-production-legacy",
    )

    assert result.kind is module.ProductionElasticExecutionKind.FIXED_POOL_EXECUTED
    assert len(executor.calls) == 1
    assert tuple(
        item.node_id for item in executor.calls[0]["plan"].selected
    ) == ("a", "b", "c")


def test_production_execute_once_rejects_partial_a_faster_context() -> None:
    from a_conductor import elastic_worker_capacity as module

    production = object.__new__(module.ProductionElasticWorkerExecutor)
    graph = TaskGraph()
    ready = compute_ready_set(graph, {})
    result = production.execute_once(
        graph,
        ready,
        {},
        schedule_policy=SchedulePolicy(max_parallel=1),
        provider_inflight={},
        runtime_kind="serena-local",
        elastic_policy=module.ElasticCapacityPolicy(
            enabled=False,
            max_extra_workers=0,
            permitted_runtime_kinds=(),
        ),
        eligibility={},
        a_faster_verdict=_verdict(occupied_mutable=3, ready_mutable=0),
    )

    assert result.kind is module.ProductionElasticExecutionKind.RECOVERY_REQUIRED
    assert result.reason_code == "A_FASTER_REFILL_CONTEXT_INCOMPLETE"

def test_forged_utilization_verdict_cannot_widen_or_change_fanout() -> None:
    verdict = _verdict(occupied_mutable=1, ready_mutable=2)
    facts, wip = _POLICY_EVIDENCE[id(verdict)]
    forged = replace(verdict, fanout_target_mutable=1)
    plan = _plan("a", "b")
    executor = FakeExecutor()

    result = _execute_auto_refill(
        facts=facts,
        verdict=forged,
        wip_facts=wip,
        lane_kind=RefillLaneKind.MUTABLE,
        ready=_ready_for_plan(plan),
        plan=plan,
        tasks_by_node={"a": _task(), "b": _task()},
        provider_inflight={"cointh-glm": 0},
        executor=executor,
    )

    assert result.disposition is AutoRefillDisposition.FAIL_CLOSED
    assert result.reason_code == "UTILIZATION_VERDICT_PROVENANCE_MISMATCH"
    assert executor.calls == []

def test_scheduler_plan_must_be_subset_of_exact_ready_set() -> None:
    verdict = _verdict(occupied_mutable=2, ready_mutable=1)
    facts, wip = _POLICY_EVIDENCE[id(verdict)]
    plan = _plan("a")
    other = _plan("different")
    executor = FakeExecutor()

    result = _execute_auto_refill(
        facts=facts,
        verdict=verdict,
        wip_facts=wip,
        lane_kind=RefillLaneKind.MUTABLE,
        ready=_ready_for_plan(other),
        plan=plan,
        tasks_by_node={"a": _task()},
        provider_inflight={"cointh-glm": 0},
        executor=executor,
    )

    assert result.disposition is AutoRefillDisposition.FAIL_CLOSED
    assert result.reason_code == "SCHEDULE_NOT_IN_READY_SET"
    assert executor.calls == []

def test_mutable_refill_requires_existing_wip_claim_gates_ready() -> None:
    verdict = _verdict(occupied_mutable=1, ready_mutable=2)
    facts, wip = _POLICY_EVIDENCE[id(verdict)]
    blocked_wip = replace(wip, claim_gate=GateState.BLOCKED)
    plan = _plan("a", "b")
    executor = FakeExecutor()

    result = _execute_auto_refill(
        facts=facts,
        verdict=verdict,
        wip_facts=blocked_wip,
        lane_kind=RefillLaneKind.MUTABLE,
        ready=_ready_for_plan(plan),
        plan=plan,
        tasks_by_node={"a": _task(), "b": _task()},
        provider_inflight={"cointh-glm": 0},
        executor=executor,
    )

    assert result.disposition is AutoRefillDisposition.FAIL_CLOSED
    assert result.reason_code == "REFILL_WIP_GATE_NOT_READY"
    assert executor.calls == []

def test_task_requires_matching_harness_intent_and_material_quota() -> None:
    verdict = _verdict(occupied_mutable=2, ready_mutable=1)
    plan = _plan("a")

    for task in (
        _task(harness_intent=MutationIntent.READ_ONLY),
        _task(require_quota=False),
    ):
        executor = FakeExecutor()
        result = execute_auto_refill(
            verdict=verdict,
            lane_kind=RefillLaneKind.MUTABLE,
            plan=plan,
            tasks_by_node={"a": task},
            provider_inflight={"cointh-glm": 0},
            executor=executor,
        )
        assert result.disposition is AutoRefillDisposition.FAIL_CLOSED
        assert result.reason_code == "REFILL_TASK_AUTHORITY_INCOMPLETE"
        assert executor.calls == []

def test_bridge_requires_provider_authority_and_pre_dispatch_guard() -> None:
    verdict = _verdict(occupied_mutable=2, ready_mutable=1)
    plan = _plan("a")

    missing_provider = FakeExecutor(provider_authority=False)
    result = execute_auto_refill(
        verdict=verdict,
        lane_kind=RefillLaneKind.MUTABLE,
        plan=plan,
        tasks_by_node={"a": _task()},
        provider_inflight={"cointh-glm": 0},
        executor=missing_provider,
    )
    assert result.reason_code == "PROVIDER_AUTHORITY_NOT_ENFORCED"
    assert missing_provider.calls == []

    missing_guard = FakeExecutor(pre_dispatch_guard=False)
    result = execute_auto_refill(
        verdict=verdict,
        lane_kind=RefillLaneKind.MUTABLE,
        plan=plan,
        tasks_by_node={"a": _task()},
        provider_inflight={"cointh-glm": 0},
        executor=missing_guard,
    )
    assert result.reason_code == "PRE_DISPATCH_GUARD_NOT_ENFORCED"
    assert missing_guard.calls == []


def test_bridge_projects_result_without_raw_runner_or_admission_objects() -> None:
    verdict = _verdict(occupied_mutable=2, ready_mutable=1)
    result = execute_auto_refill(
        verdict=verdict,
        lane_kind=RefillLaneKind.MUTABLE,
        plan=_plan("a"),
        tasks_by_node={"a": _task()},
        provider_inflight={"cointh-glm": 0},
        executor=FakeExecutor(),
    )

    assert result.disposition is AutoRefillDisposition.EXECUTED
    assert not hasattr(result, "batch_result")
    assert len(result.outcomes) == 1
    assert not hasattr(result.outcomes[0], "runner_result")
    assert result.outcomes[0].reason_code == "RUNNER_COMPLETED"
