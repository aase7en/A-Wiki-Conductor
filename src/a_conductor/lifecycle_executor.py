"""Abstract lifecycle transaction execution with durable checkpoint boundaries.

This module intentionally contains no concrete process, shell, filesystem,
network, or persistence backend. It executes an already-approved symbolic
``LifecyclePlan`` through injected interfaces and stops whenever durable state
cannot safely prove what happened.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .lifecycle import (
    LifecycleAction,
    LifecycleDecision,
    LifecyclePlan,
    LifecycleStep,
)


class LifecycleExecutionState(str, Enum):
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    REFUSED = "REFUSED"
    NOOP = "NOOP"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


@dataclass(frozen=True, slots=True)
class LifecycleStepResult:
    success: bool
    evidence_ref: str | None = None
    error_code: str | None = None
    recovery_required: bool = False


class LifecycleStepBackend(Protocol):
    def execute_step(self, step: LifecycleStep) -> LifecycleStepResult: ...


@dataclass(frozen=True, slots=True)
class LifecycleCheckpoint:
    transaction_id: str
    sequence_no: int
    action: LifecycleAction
    step: LifecycleStep
    evidence_ref: str | None


class LifecycleCheckpointSink(Protocol):
    def record(self, checkpoint: LifecycleCheckpoint) -> None: ...


@dataclass(frozen=True, slots=True)
class LifecycleExecutionResult:
    transaction_id: str
    state: LifecycleExecutionState
    reason_code: str
    completed_steps: tuple[LifecycleStep, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    failed_step: LifecycleStep | None = None


_MUTATING_STEPS = frozenset(
    {
        LifecycleStep.RENDER_PROFILE,
        LifecycleStep.START_OWNED_PROCESS,
        LifecycleStep.TARGETED_STOP,
        LifecycleStep.CLEAR_ASSIGNMENT,
    }
)


def _require_transaction_id(transaction_id: str) -> str:
    if not isinstance(transaction_id, str) or not transaction_id.strip():
        raise ValueError("transaction_id must not be blank")
    return transaction_id


def _non_proceed_result(
    plan: LifecyclePlan,
    transaction_id: str,
) -> LifecycleExecutionResult:
    state_by_decision = {
        LifecycleDecision.REFUSE: LifecycleExecutionState.REFUSED,
        LifecycleDecision.NOOP: LifecycleExecutionState.NOOP,
        LifecycleDecision.RECOVERY_REQUIRED: LifecycleExecutionState.RECOVERY_REQUIRED,
    }
    return LifecycleExecutionResult(
        transaction_id=transaction_id,
        state=state_by_decision[plan.decision],
        reason_code=plan.reason_code,
    )


class LifecycleExecutor:
    """Execute only a previously approved PROCEED plan.

    A step is considered durably complete only after both the backend reports
    success and the corresponding checkpoint is recorded. If checkpointing
    fails after a mutating step, subsequent execution is forbidden because the
    host may have changed while durable state cannot prove that change.
    """

    def execute(
        self,
        plan: LifecyclePlan,
        backend: LifecycleStepBackend,
        checkpoint_sink: LifecycleCheckpointSink,
        *,
        transaction_id: str,
    ) -> LifecycleExecutionResult:
        transaction_id = _require_transaction_id(transaction_id)
        if plan.decision is not LifecycleDecision.PROCEED:
            return _non_proceed_result(plan, transaction_id)

        completed_steps: list[LifecycleStep] = []
        evidence_refs: list[str] = []

        for sequence_no, step in enumerate(plan.steps, start=1):
            try:
                step_result = backend.execute_step(step)
            except Exception:
                return LifecycleExecutionResult(
                    transaction_id=transaction_id,
                    state=(
                        LifecycleExecutionState.RECOVERY_REQUIRED
                        if step in _MUTATING_STEPS
                        else LifecycleExecutionState.FAILED
                    ),
                    reason_code=(
                        "BACKEND_EXECUTION_UNCERTAIN"
                        if step in _MUTATING_STEPS
                        else "BACKEND_EXECUTION_ERROR"
                    ),
                    completed_steps=tuple(completed_steps),
                    evidence_refs=tuple(evidence_refs),
                    failed_step=step,
                )

            if step_result.evidence_ref is not None:
                evidence_refs.append(step_result.evidence_ref)

            if not step_result.success:
                return LifecycleExecutionResult(
                    transaction_id=transaction_id,
                    state=(
                        LifecycleExecutionState.RECOVERY_REQUIRED
                        if step_result.recovery_required
                        else LifecycleExecutionState.FAILED
                    ),
                    reason_code=step_result.error_code or "STEP_FAILED",
                    completed_steps=tuple(completed_steps),
                    evidence_refs=tuple(evidence_refs),
                    failed_step=step,
                )

            checkpoint = LifecycleCheckpoint(
                transaction_id=transaction_id,
                sequence_no=sequence_no,
                action=plan.action,
                step=step,
                evidence_ref=step_result.evidence_ref,
            )
            try:
                checkpoint_sink.record(checkpoint)
            except Exception:
                return LifecycleExecutionResult(
                    transaction_id=transaction_id,
                    state=(
                        LifecycleExecutionState.RECOVERY_REQUIRED
                        if step in _MUTATING_STEPS
                        else LifecycleExecutionState.FAILED
                    ),
                    reason_code=(
                        "CHECKPOINT_PERSISTENCE_FAILED"
                        if step in _MUTATING_STEPS
                        else "CHECKPOINT_FAILED"
                    ),
                    completed_steps=tuple(completed_steps),
                    evidence_refs=tuple(evidence_refs),
                    failed_step=step,
                )

            completed_steps.append(step)

        return LifecycleExecutionResult(
            transaction_id=transaction_id,
            state=LifecycleExecutionState.COMPLETE,
            reason_code="COMPLETE",
            completed_steps=tuple(completed_steps),
            evidence_refs=tuple(evidence_refs),
        )
