"""Pure lifecycle resume planning from durable checkpoints plus reconciliation.

The journal proves only what was durably checkpointed. A separate reconciliation
assessment must say whether current runtime state is consistent with that
journal before execution may resume.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .lifecycle import LifecycleDecision, LifecyclePlan, LifecycleStep
from .lifecycle_executor import LifecycleCheckpoint


class LifecycleReconciliationAssessment(str, Enum):
    CONSISTENT_WITH_JOURNAL = "CONSISTENT_WITH_JOURNAL"
    MUTATION_AHEAD_OF_JOURNAL = "MUTATION_AHEAD_OF_JOURNAL"
    UNEXPECTED_DRIFT = "UNEXPECTED_DRIFT"
    UNKNOWN = "UNKNOWN"


class LifecycleResumeDecision(str, Enum):
    RESUME = "RESUME"
    COMPLETE = "COMPLETE"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    REFUSE = "REFUSE"


@dataclass(frozen=True, slots=True)
class LifecycleResumePlan:
    transaction_id: str
    decision: LifecycleResumeDecision
    reason_code: str
    durable_steps: tuple[LifecycleStep, ...] = ()
    remaining_steps: tuple[LifecycleStep, ...] = ()
    next_step: LifecycleStep | None = None


def _require_transaction_id(transaction_id: str) -> str:
    if not isinstance(transaction_id, str) or not transaction_id.strip():
        raise ValueError("transaction_id must not be blank")
    return transaction_id


def _result(
    *,
    transaction_id: str,
    decision: LifecycleResumeDecision,
    reason_code: str,
    durable_steps: tuple[LifecycleStep, ...] = (),
    remaining_steps: tuple[LifecycleStep, ...] = (),
) -> LifecycleResumePlan:
    return LifecycleResumePlan(
        transaction_id=transaction_id,
        decision=decision,
        reason_code=reason_code,
        durable_steps=durable_steps,
        remaining_steps=remaining_steps,
        next_step=remaining_steps[0] if remaining_steps else None,
    )


def plan_lifecycle_resume(
    *,
    transaction_id: str,
    plan: LifecyclePlan,
    checkpoints: tuple[LifecycleCheckpoint, ...],
    assessment: LifecycleReconciliationAssessment,
) -> LifecycleResumePlan:
    transaction_id = _require_transaction_id(transaction_id)

    if plan.decision is not LifecycleDecision.PROCEED:
        return _result(
            transaction_id=transaction_id,
            decision=LifecycleResumeDecision.REFUSE,
            reason_code="PLAN_NOT_EXECUTABLE",
        )

    durable_steps: list[LifecycleStep] = []
    if len(checkpoints) > len(plan.steps):
        return _result(
            transaction_id=transaction_id,
            decision=LifecycleResumeDecision.REFUSE,
            reason_code="CHECKPOINT_PLAN_MISMATCH",
        )

    for expected_sequence, checkpoint in enumerate(checkpoints, start=1):
        if checkpoint.transaction_id != transaction_id:
            return _result(
                transaction_id=transaction_id,
                decision=LifecycleResumeDecision.REFUSE,
                reason_code="CHECKPOINT_TRANSACTION_MISMATCH",
            )
        if checkpoint.action is not plan.action:
            return _result(
                transaction_id=transaction_id,
                decision=LifecycleResumeDecision.REFUSE,
                reason_code="CHECKPOINT_ACTION_MISMATCH",
            )
        if checkpoint.sequence_no != expected_sequence:
            return _result(
                transaction_id=transaction_id,
                decision=LifecycleResumeDecision.REFUSE,
                reason_code="CHECKPOINT_SEQUENCE_INVALID",
            )
        expected_step = plan.steps[expected_sequence - 1]
        if checkpoint.step is not expected_step:
            return _result(
                transaction_id=transaction_id,
                decision=LifecycleResumeDecision.REFUSE,
                reason_code="CHECKPOINT_PLAN_MISMATCH",
            )
        durable_steps.append(checkpoint.step)

    durable = tuple(durable_steps)

    if assessment is LifecycleReconciliationAssessment.UNKNOWN:
        return _result(
            transaction_id=transaction_id,
            decision=LifecycleResumeDecision.RECOVERY_REQUIRED,
            reason_code="RECONCILIATION_UNKNOWN",
            durable_steps=durable,
        )
    if assessment is LifecycleReconciliationAssessment.MUTATION_AHEAD_OF_JOURNAL:
        return _result(
            transaction_id=transaction_id,
            decision=LifecycleResumeDecision.RECOVERY_REQUIRED,
            reason_code="MUTATION_AHEAD_OF_JOURNAL",
            durable_steps=durable,
        )
    if assessment is LifecycleReconciliationAssessment.UNEXPECTED_DRIFT:
        return _result(
            transaction_id=transaction_id,
            decision=LifecycleResumeDecision.REFUSE,
            reason_code="UNEXPECTED_DRIFT",
            durable_steps=durable,
        )

    remaining = plan.steps[len(durable) :]
    if not remaining:
        return _result(
            transaction_id=transaction_id,
            decision=LifecycleResumeDecision.COMPLETE,
            reason_code="JOURNAL_COMPLETE",
            durable_steps=durable,
        )

    return _result(
        transaction_id=transaction_id,
        decision=LifecycleResumeDecision.RESUME,
        reason_code="RESUME_FROM_JOURNAL",
        durable_steps=durable,
        remaining_steps=remaining,
    )
