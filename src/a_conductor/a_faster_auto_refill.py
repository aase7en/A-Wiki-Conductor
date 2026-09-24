"""Executable A-Faster auto-refill bridge (WO-P1-549).

Consumes existing utilization/WIP/readiness/scheduler evidence and delegates one
bounded refill through the accepted ParallelReadyExecutor.  It creates no
scheduler, task/claim/lease/provider/retry/review/completion authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Protocol

from .a_faster_utilization_guard import (
    AFasterActivation,
    DEFAULT_MUTABLE_LANES,
    DEFAULT_REVIEW_LANES,
    UtilizationFacts,
    UtilizationVerdict,
    classify_utilization,
)
from .claude_code_harness import MutationIntent
from .elastic_wip_policy import (
    ACTIVE_MUTATION_LIMIT,
    REVIEW_LANE_LIMIT,
    ElasticWipFacts,
    GateState,
    classify_elastic_wip,
)
from .graph.ready import ReadySetResult
from .graph.scheduler import SchedulePlan, SelectedAssignment
from .parallel_ready_execution import (
    ParallelReadyBatchResult,
    ParallelReadyOutcome,
    ParallelReadyOutcomeKind,
    ParallelReadyTask,
)
from .worker_lease import LeaseMutationIntent


_REASON_RE = re.compile(r"[A-Z0-9_]{3,64}")


class RefillLaneKind(str, Enum):
    MUTABLE = "MUTABLE"
    REVIEW = "REVIEW"


class AutoRefillDisposition(str, Enum):
    NO_REFILL_REQUIRED = "NO_REFILL_REQUIRED"
    EXECUTED = "EXECUTED"
    FAIL_CLOSED = "FAIL_CLOSED"


@dataclass(frozen=True, slots=True)
class AutoRefillOutcome:
    node_id: str
    kind: ParallelReadyOutcomeKind
    reason_code: str

@dataclass(frozen=True, slots=True)
class AutoRefillResult:
    disposition: AutoRefillDisposition
    reason_code: str
    selected_node_ids: tuple[str, ...] = ()
    outcomes: tuple[AutoRefillOutcome, ...] = ()


class AutoRefillExecutor(Protocol):
    @property
    def requires_provider_authority(self) -> bool: ...

    @property
    def pre_dispatch_guard_enforced(self) -> bool: ...

    def execute(
        self,
        plan: SchedulePlan,
        tasks_by_node: Mapping[str, ParallelReadyTask],
        *,
        provider_inflight: Mapping[str, int],
        batch_id: str | None = None,
        pre_acquired_admissions: Mapping[str, Any] | None = None,
    ) -> ParallelReadyBatchResult: ...


def _fail(
    reason: str, *, selected_node_ids: tuple[str, ...] = ()
) -> AutoRefillResult:
    return AutoRefillResult(
        AutoRefillDisposition.FAIL_CLOSED,
        reason,
        selected_node_ids=selected_node_ids,
    )

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

def _rederive_policy(
    facts: UtilizationFacts,
    verdict: UtilizationVerdict,
    wip_facts: ElasticWipFacts,
) -> tuple[object | None, str | None]:
    if not isinstance(facts, UtilizationFacts):
        return None, "UTILIZATION_FACTS_INVALID"
    if not isinstance(wip_facts, ElasticWipFacts):
        return None, "ELASTIC_WIP_FACTS_INVALID"
    try:
        expected = classify_utilization(facts)
        wip = classify_elastic_wip(wip_facts)
    except (TypeError, ValueError):
        return None, "REFILL_POLICY_EVIDENCE_INVALID"
    if expected != verdict:
        return None, "UTILIZATION_VERDICT_PROVENANCE_MISMATCH"
    if facts.occupied_mutable_lanes != wip.active_mutation_total:
        return None, "MUTABLE_WIP_EVIDENCE_DRIFT"
    if facts.occupied_review_lanes != wip.review_claimed:
        return None, "REVIEW_WIP_EVIDENCE_DRIFT"
    return wip, None


def _task_authority_ok(task: ParallelReadyTask, lane_kind: RefillLaneKind) -> bool:
    expected_lease = (
        LeaseMutationIntent.MUTATION
        if lane_kind is RefillLaneKind.MUTABLE
        else LeaseMutationIntent.READ_ONLY
    )
    expected_harness = (
        MutationIntent.PROJECT_MUTATION
        if lane_kind is RefillLaneKind.MUTABLE
        else MutationIntent.READ_ONLY
    )
    return (
        task.lease_request.mutation_intent is expected_lease
        and task.harness_dispatch.mutation_intent is expected_harness
        and task.require_quota is True
        and task.provider_requirement is not None
        and task.provider_endpoint is not None
        and task.provider_security is not None
        and task.expected_configuration_generation is not None
    )


def execute_auto_refill(
    *,
    facts: UtilizationFacts,
    verdict: UtilizationVerdict,
    wip_facts: ElasticWipFacts,
    lane_kind: RefillLaneKind,
    ready: ReadySetResult,
    plan: SchedulePlan,
    tasks_by_node: Mapping[str, ParallelReadyTask],
    provider_inflight: Mapping[str, int],
    executor: AutoRefillExecutor,
    batch_id: str | None = None,
    pre_acquired_admissions: Mapping[str, Any] | None = None,
) -> AutoRefillResult:
    """Execute one bounded scheduler-owned refill batch, or fail closed."""

    if not isinstance(verdict, UtilizationVerdict):
        return _fail("UTILIZATION_VERDICT_INVALID")
    if verdict.activation != AFasterActivation.ACTIVE.value:
        return _fail("A_FASTER_NOT_ACTIVE")
    if not isinstance(lane_kind, RefillLaneKind):
        return _fail("REFILL_LANE_KIND_INVALID")
    if not isinstance(ready, ReadySetResult):
        return _fail("READY_SET_EVIDENCE_INVALID")

    wip, policy_error = _rederive_policy(facts, verdict, wip_facts)
    if policy_error is not None:
        return _fail(policy_error)
    assert wip is not None

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
    if target > budget or target > verdict.unused_safe_capacity:
        return _fail("FANOUT_TARGET_EXCEEDS_SAFE_CAPACITY")

    if lane_kind is RefillLaneKind.MUTABLE:
        if wip.contraction_required:
            return _fail("WIP_CONTRACTION_REQUIRED")
        if any(
            gate is not GateState.READY
            for gate in (
                wip_facts.scope_gate,
                wip_facts.claim_gate,
                wip_facts.runtime_gate,
            )
        ):
            return _fail("REFILL_WIP_GATE_NOT_READY")
        mutable_headroom = ACTIVE_MUTATION_LIMIT - wip.active_mutation_after_contraction
        if target > mutable_headroom:
            return _fail("FANOUT_TARGET_EXCEEDS_ACTIVE_MUTATION_HEADROOM")
        base_claim_headroom = ACTIVE_MUTATION_LIMIT - wip.base_claimed
        authorized_claim_refill = (
            base_claim_headroom
            + wip.borrowed_resume_target
            + wip.new_borrow_target
        )
        if target > authorized_claim_refill:
            return _fail("FANOUT_TARGET_EXCEEDS_CLAIM_CAPACITY")
    else:
        review_headroom = REVIEW_LANE_LIMIT - wip.review_claimed
        if target > review_headroom:
            return _fail("FANOUT_TARGET_EXCEEDS_REVIEW_HEADROOM")

    if not isinstance(plan, SchedulePlan):
        return _fail("SCHEDULE_PLAN_INVALID")
    if not isinstance(tasks_by_node, Mapping):
        return _fail("SCHEDULE_TASK_MAPPING_INVALID")
    if not isinstance(provider_inflight, Mapping):
        return _fail("PROVIDER_INFLIGHT_INVALID")
    if not callable(getattr(executor, "execute", None)):
        return _fail("REFILL_EXECUTOR_INVALID")
    if getattr(executor, "requires_provider_authority", False) is not True:
        return _fail("PROVIDER_AUTHORITY_NOT_ENFORCED")
    if getattr(executor, "pre_dispatch_guard_enforced", False) is not True:
        return _fail("PRE_DISPATCH_GUARD_NOT_ENFORCED")

    schedule_nodes = _schedule_nodes(plan)
    if schedule_nodes is None:
        return _fail("SCHEDULE_IDENTITY_INVALID")
    if not set(schedule_nodes).issubset(set(ready.ready_ids)):
        return _fail("SCHEDULE_NOT_IN_READY_SET")
    if set(tasks_by_node) != set(schedule_nodes):
        return _fail("SCHEDULE_TASK_MAPPING_DRIFT")
    if any(
        not isinstance(task, ParallelReadyTask)
        for task in tasks_by_node.values()
    ):
        return _fail("REFILL_TASK_INVALID")
    if any(
        not _task_authority_ok(task, lane_kind)
        for task in tasks_by_node.values()
    ):
        return _fail("REFILL_TASK_AUTHORITY_INCOMPLETE")

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

    bounded_tasks = {
        node_id: tasks_by_node[node_id] for node_id in selected_node_ids
    }
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
        # execute() may have crossed side-effect boundaries; never call this a
        # rejection or grant replay permission.  Exact durable reconciliation
        # owns the next action.
        return _fail(
            "REFILL_EXECUTION_RECONCILE_REQUIRED",
            selected_node_ids=selected_node_ids,
        )

    if not isinstance(batch_result, ParallelReadyBatchResult):
        return _fail(
            "REFILL_RESULT_INVALID",
            selected_node_ids=selected_node_ids,
        )
    if len(batch_result.outcomes) != len(selected_node_ids):
        return _fail(
            "REFILL_RESULT_IDENTITY_MISMATCH",
            selected_node_ids=selected_node_ids,
        )

    projected: list[AutoRefillOutcome] = []
    for expected_node, outcome in zip(selected_node_ids, batch_result.outcomes):
        if not isinstance(outcome, ParallelReadyOutcome):
            return _fail(
                "REFILL_RESULT_INVALID",
                selected_node_ids=selected_node_ids,
            )
        if outcome.node_id != expected_node:
            return _fail(
                "REFILL_RESULT_IDENTITY_MISMATCH",
                selected_node_ids=selected_node_ids,
            )
        if (
            not isinstance(outcome.kind, ParallelReadyOutcomeKind)
            or not isinstance(outcome.reason_code, str)
            or _REASON_RE.fullmatch(outcome.reason_code) is None
        ):
            return _fail(
                "REFILL_RESULT_INVALID",
                selected_node_ids=selected_node_ids,
            )
        projected.append(
            AutoRefillOutcome(
                node_id=outcome.node_id,
                kind=outcome.kind,
                reason_code=outcome.reason_code,
            )
        )

    return AutoRefillResult(
        AutoRefillDisposition.EXECUTED,
        "AUTO_REFILL_EXECUTED",
        selected_node_ids=selected_node_ids,
        outcomes=tuple(projected),
    )
