from __future__ import annotations

from types import SimpleNamespace

from a_conductor.a_faster_auto_refill import (
    AutoRefillDisposition,
    RefillLaneKind,
    execute_auto_refill,
)
from a_conductor.a_faster_utilization_guard import (
    AFasterActivation,
    UtilizationFacts,
    classify_utilization,
)
from a_conductor.graph.scheduler import SchedulePlan, SelectedAssignment
from a_conductor.parallel_ready_execution import ParallelReadyBatchResult


class FakeExecutor:
    def __init__(self, *, fail: bool = False, mismatch: bool = False) -> None:
        self.calls: list[dict[str, object]] = []
        self.fail = fail
        self.mismatch = mismatch

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
            SimpleNamespace(node_id=node_id) for node_id in node_ids
        )
        return ParallelReadyBatchResult(outcomes=outcomes)


def _verdict(
    *,
    occupied_mutable: int = 1,
    ready_mutable: int = 3,
    occupied_review: int = 1,
    ready_review: int = 0,
):
    return classify_utilization(
        UtilizationFacts(
            activation=AFasterActivation.ACTIVE,
            occupied_mutable_lanes=occupied_mutable,
            occupied_review_lanes=occupied_review,
            ready_mutable_candidates=ready_mutable,
            ready_review_candidates=ready_review,
            glm_route_ready=True,
            glm_quota_admission=__import__(
                "a_conductor.a_faster_utilization_guard",
                fromlist=["QuotaAdmission"],
            ).QuotaAdmission.QUOTA_AVAILABLE,
        )
    )


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
    tasks = {node: object() for node in ("a", "b", "c")}

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
            tasks_by_node={"a": object()},
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
    for tasks in ({"a": object()}, {"a": object(), "b": object(), "x": object()}):
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
        tasks_by_node={"a": object()},
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
        tasks_by_node={"only-safe": object()},
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
        tasks_by_node={"review-a": object(), "review-b": object()},
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
        tasks_by_node={"a": object(), "b": object()},
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
        tasks_by_node={"a": object()},
        provider_inflight={"cointh-glm": 0},
        executor=executor,
    )
    assert result.disposition is AutoRefillDisposition.FAIL_CLOSED
    assert result.reason_code == "REFILL_EXECUTOR_REJECTED"
    assert "provider detail" not in repr(result)


def test_executor_result_identity_mismatch_requires_recovery() -> None:
    verdict = _verdict(occupied_mutable=2, ready_mutable=1)
    executor = FakeExecutor(mismatch=True)
    result = execute_auto_refill(
        verdict=verdict,
        lane_kind=RefillLaneKind.MUTABLE,
        plan=_plan("a"),
        tasks_by_node={"a": object()},
        provider_inflight={"cointh-glm": 0},
        executor=executor,
    )
    assert result.disposition is AutoRefillDisposition.FAIL_CLOSED
    assert result.reason_code == "REFILL_RESULT_IDENTITY_MISMATCH"
