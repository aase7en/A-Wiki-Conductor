"""Executable A-Faster auto-refill bridge (WO-P1-549).

This module closes the utilization-policy-to-execution seam without becoming a
scheduler or authority. It consumes an accepted A-Faster utilization verdict,
an already scheduler-owned SchedulePlan, and the existing ParallelReadyExecutor.
All lease, provider, dedupe, dispatch, and PRE_DISPATCH authority remains in
those existing components.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Protocol

from .a_faster_utilization_guard import (
    AFasterActivation,
    DEFAULT_MUTABLE_LANES,
    DEFAULT_REVIEW_LANES,
    UtilizationVerdict,
)
from .graph.scheduler import SchedulePlan, SelectedAssignment
from .parallel_ready_execution import (
    ParallelReadyBatchResult,
    ParallelReadyTask,
)


class RefillLaneKind(str, Enum):
    """The existing global WIP pool being refilled."""

    MUTABLE = "MUTABLE"
    REVIEW = "REVIEW"


class AutoRefillDisposition(str, Enum):
    """Bounded projection of one refill attempt; never lifecycle authority."""

    NO_REFILL_REQUIRED = "NO_REFILL_REQUIRED"
    EXECUTED = "EXECUTED"
    FAIL_CLOSED = "FAIL_CLOSED"


@dataclass(frozen=True, slots=True)
class AutoRefillResult:
    disposition: AutoRefillDisposition
    reason_code: str
    selected_node_ids: tuple[str, ...] = ()
    batch_result: ParallelReadyBatchResult | None = None


class AutoRefillExecutor(Protocol):
    """Narrow structural view of the accepted ParallelReadyExecutor seam."""

    def execute(
        self,
        plan: SchedulePlan,
        tasks_by_node: Mapping[str, ParallelReadyTask],
        *,
        provider_inflight: Mapping[str, int],
        batch_id: str | None = None,
        pre_acquired_admissions: Mapping[str, Any] | None = None,
    ) -> ParallelReadyBatchResult: ...


def _fail(reason: str) -> AutoRefillResult:
    return AutoRefillResult(AutoRefillDisposition.FAIL_CLOSED, reason)


def _noop(reason: str) -> AutoRefillResult:
    return AutoRefillResult(AutoRefillDisposition.NO_REFILL_REQUIRED, reason)


def _target_for(
    verdict: UtilizationVerdict, lane_kind: RefillLaneKind
) -> tuple[int, int]:
    if lane_kind is RefillLaneKind.MUTABLE:
        return verdict.fanout_target_mutable, DEFAULT_MUTABLE_LANES
    return verdict.fanout_target_review, DEFAULT_REVIEW_LANES


def _schedule_nodes(plan: SchedulePlan) -> tuple[str, ...] | None:
    nodes: list[str] = []
    workers: set[str] = set()
    for assignment in plan.selected:
        if not isinstance(assignment, SelectedAssignment):
            return None
        node_id = assignment.node_id
        worker_id = assignment.worker_id
        if (
            not isinstance(node_id, str)
            or not node_id.strip()
            or node_id in nodes
            or not isinstance(worker_id, str)
            or not worker_id.strip()
            or worker_id in workers
        ):
            return None
        nodes.append(node_id)
        workers.add(worker_id)
    return tuple(nodes)


def execute_auto_refill(
    *,
    verdict: UtilizationVerdict,
    lane_kind: RefillLaneKind,
    plan: SchedulePlan,
    tasks_by_node: Mapping[str, ParallelReadyTask],
    provider_inflight: Mapping[str, int],
    executor: AutoRefillExecutor,
    batch_id: str | None = None,
    pre_acquired_admissions: Mapping[str, Any] | None = None,
) -> AutoRefillResult:
    """Execute at most one scheduler-owned refill batch.

    The bridge never discovers READY work and never retries. The scheduler has
    already chosen assignments; this function only bounds that immutable plan to
    the accepted A-Faster FANOUT_TARGET before delegating to the existing
    ParallelReadyExecutor.
    """

    if not isinstance(verdict, UtilizationVerdict):
        return _fail("UTILIZATION_VERDICT_INVALID")
    if verdict.activation != AFasterActivation.ACTIVE.value:
        return _fail("A_FASTER_NOT_ACTIVE")
    if not isinstance(lane_kind, RefillLaneKind):
        return _fail("REFILL_LANE_KIND_INVALID")

    if not verdict.auto_refill_required:
        if verdict.fanout_target != 0:
            return _fail("UTILIZATION_VERDICT_INCONSISTENT")
        return _noop("AUTO_REFILL_NOT_REQUIRED")
    if verdict.fanout_target <= 0:
        return _fail("UTILIZATION_VERDICT_INCONSISTENT")

    target, budget = _target_for(verdict, lane_kind)
    if not isinstance(target, int) or isinstance(target, bool) or target < 0:
        return _fail("FANOUT_TARGET_INVALID")
    if target == 0:
        return _noop(f"NO_{lane_kind.value}_FANOUT_TARGET")
    if target > budget:
        return _fail("FANOUT_TARGET_EXCEEDS_GLOBAL_WIP")

    if not isinstance(plan, SchedulePlan):
        return _fail("SCHEDULE_PLAN_INVALID")
    if not isinstance(tasks_by_node, Mapping):
        return _fail("SCHEDULE_TASK_MAPPING_INVALID")
    if not isinstance(provider_inflight, Mapping):
        return _fail("PROVIDER_INFLIGHT_INVALID")
    if not callable(getattr(executor, "execute", None)):
        return _fail("REFILL_EXECUTOR_INVALID")

    schedule_nodes = _schedule_nodes(plan)
    if schedule_nodes is None:
        return _fail("SCHEDULE_IDENTITY_INVALID")
    if set(tasks_by_node) != set(schedule_nodes):
        return _fail("SCHEDULE_TASK_MAPPING_DRIFT")

    selected = tuple(plan.selected[: min(target, len(plan.selected))])
    selected_node_ids = tuple(item.node_id for item in selected)
    if not selected:
        return _fail("SCHEDULER_NO_SELECTED_WORK")

    admissions = pre_acquired_admissions
    if admissions is not None:
        if not isinstance(admissions, Mapping):
            return _fail("PREACQUIRED_ADMISSION_MAPPING_INVALID")
        if not set(admissions).issubset(set(selected_node_ids)):
            return _fail("PREACQUIRED_ADMISSION_OUTSIDE_REFILL")

    bounded_tasks = {node_id: tasks_by_node[node_id] for node_id in selected_node_ids}
    bounded_plan = SchedulePlan(
        selected=selected,
        blocked=plan.blocked,
        capacity_evidence=plan.capacity_evidence,
    )
    try:
        batch_result = executor.execute(
            bounded_plan,
            bounded_tasks,
            provider_inflight=provider_inflight,
            batch_id=batch_id,
            pre_acquired_admissions=admissions,
        )
    except Exception:
        # The existing executor owns detailed recovery evidence. This bridge
        # deliberately returns only a stable bounded code and never leaks raw
        # provider/secret/process exception text.
        return _fail("REFILL_EXECUTOR_REJECTED")

    if not isinstance(batch_result, ParallelReadyBatchResult):
        return _fail("REFILL_RESULT_INVALID")
    result_nodes = tuple(
        getattr(outcome, "node_id", None) for outcome in batch_result.outcomes
    )
    if result_nodes != selected_node_ids:
        return _fail("REFILL_RESULT_IDENTITY_MISMATCH")

    return AutoRefillResult(
        AutoRefillDisposition.EXECUTED,
        "AUTO_REFILL_EXECUTED",
        selected_node_ids=selected_node_ids,
        batch_result=batch_result,
    )
