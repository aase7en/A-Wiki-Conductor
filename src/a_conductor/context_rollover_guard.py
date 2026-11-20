"""Pure session/context rollover guard for A-Sunday Conductor (WO-P1-369).

This module does not measure ChatGPT tokens and never fabricates a remaining
context percentage.  It consumes explicit session-pressure evidence plus the
existing ContinuityGuard verdict and durable-recovery facts.

The result is advisory session-safety policy only.  It never grants mutation
authority, writes checkpoints, dispatches work, or creates durable state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .continuity_guard import ContinuityClassification, ContinuityVerdict


class ContextPressure(str, Enum):
    NORMAL = "NORMAL"
    CROWDED = "CROWDED"
    NEAR_LIMIT = "NEAR_LIMIT"
    UNKNOWN = "UNKNOWN"


class CheckpointState(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class RecoveryPointerState(str, Enum):
    READY = "READY"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"


class ContextGuardStatus(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class ContextGuardAction(str, Enum):
    RECONCILE_CONTINUITY = "RECONCILE_CONTINUITY"
    RECOVER_OUTSTANDING_EXECUTIONS = "RECOVER_OUTSTANDING_EXECUTIONS"
    CHECKPOINT_NOW = "CHECKPOINT_NOW"
    REFRESH_RECOVERY_POINTER = "REFRESH_RECOVERY_POINTER"
    CHECKPOINT_AT_NEXT_BOUNDARY = "CHECKPOINT_AT_NEXT_BOUNDARY"
    ROTATE_SESSION = "ROTATE_SESSION"
    CONTINUE = "CONTINUE"


_REASON_ORDER: tuple[str, ...] = (
    "CONTINUITY_NOT_FRESH",
    "OUTSTANDING_EXECUTIONS_UNRECOVERABLE",
    "OUTSTANDING_EXECUTIONS_RECOVERY_UNKNOWN",
    "CHECKPOINT_UNKNOWN",
    "CHECKPOINT_STALE",
    "MUTATION_AFTER_CHECKPOINT",
    "RECOVERY_POINTER_UNKNOWN",
    "RECOVERY_POINTER_MISSING",
    "CONTEXT_NEAR_LIMIT",
    "CONTEXT_PRESSURE_UNKNOWN",
    "CONTEXT_CROWDED",
)
_ACTION_ORDER: tuple[ContextGuardAction, ...] = (
    ContextGuardAction.RECONCILE_CONTINUITY,
    ContextGuardAction.RECOVER_OUTSTANDING_EXECUTIONS,
    ContextGuardAction.CHECKPOINT_NOW,
    ContextGuardAction.REFRESH_RECOVERY_POINTER,
    ContextGuardAction.CHECKPOINT_AT_NEXT_BOUNDARY,
    ContextGuardAction.ROTATE_SESSION,
    ContextGuardAction.CONTINUE,
)


@dataclass(frozen=True, slots=True)
class SessionRolloverSnapshot:
    continuity: ContinuityVerdict
    context_pressure: ContextPressure
    checkpoint_state: CheckpointState
    mutation_after_checkpoint: bool
    recovery_pointer_state: RecoveryPointerState
    outstanding_execution_count: int
    outstanding_executions_recoverable: bool | None

    def __post_init__(self) -> None:
        if not isinstance(self.continuity, ContinuityVerdict):
            raise ValueError("continuity must be a ContinuityVerdict")
        if not isinstance(self.context_pressure, ContextPressure):
            raise ValueError("context_pressure must be a ContextPressure")
        if not isinstance(self.checkpoint_state, CheckpointState):
            raise ValueError("checkpoint_state must be a CheckpointState")
        if not isinstance(self.recovery_pointer_state, RecoveryPointerState):
            raise ValueError("recovery_pointer_state must be a RecoveryPointerState")
        if type(self.mutation_after_checkpoint) is not bool:
            raise ValueError("mutation_after_checkpoint must be bool")
        count = self.outstanding_execution_count
        if type(count) is not int or count < 0:
            raise ValueError("outstanding_execution_count must be a non-negative int")
        recoverable = self.outstanding_executions_recoverable
        if recoverable is not None and type(recoverable) is not bool:
            raise ValueError(
                "outstanding_executions_recoverable must be bool or None"
            )


@dataclass(frozen=True, slots=True)
class ContextGuardVerdict:
    status: ContextGuardStatus
    rotation_ready: bool
    reason_codes: tuple[str, ...]
    actions: tuple[ContextGuardAction, ...]


def _continuity_is_fresh(verdict: ContinuityVerdict) -> bool:
    return (
        verdict.classification is ContinuityClassification.FRESH
        and verdict.safe_to_mutate is True
    )


def _ordered_reasons(present: set[str]) -> tuple[str, ...]:
    return tuple(reason for reason in _REASON_ORDER if reason in present)


def _ordered_actions(
    present: set[ContextGuardAction],
) -> tuple[ContextGuardAction, ...]:
    return tuple(action for action in _ACTION_ORDER if action in present)
def classify_context_rollover(
    snapshot: SessionRolloverSnapshot,
) -> ContextGuardVerdict:
    """Return a deterministic GREEN/YELLOW/RED session-rollover verdict."""

    if not isinstance(snapshot, SessionRolloverSnapshot):
        raise ValueError("snapshot must be a SessionRolloverSnapshot")

    reasons: set[str] = set()
    actions: set[ContextGuardAction] = set()

    continuity_fresh = _continuity_is_fresh(snapshot.continuity)
    if not continuity_fresh:
        reasons.add("CONTINUITY_NOT_FRESH")
        actions.add(ContextGuardAction.RECONCILE_CONTINUITY)

    if snapshot.outstanding_execution_count > 0:
        if snapshot.outstanding_executions_recoverable is False:
            reasons.add("OUTSTANDING_EXECUTIONS_UNRECOVERABLE")
            actions.add(ContextGuardAction.RECOVER_OUTSTANDING_EXECUTIONS)
        elif snapshot.outstanding_executions_recoverable is None:
            reasons.add("OUTSTANDING_EXECUTIONS_RECOVERY_UNKNOWN")
            actions.add(ContextGuardAction.RECOVER_OUTSTANDING_EXECUTIONS)

    if snapshot.checkpoint_state is CheckpointState.UNKNOWN:
        reasons.add("CHECKPOINT_UNKNOWN")
        actions.add(ContextGuardAction.CHECKPOINT_NOW)
    elif snapshot.checkpoint_state is CheckpointState.STALE:
        reasons.add("CHECKPOINT_STALE")
        actions.add(ContextGuardAction.CHECKPOINT_NOW)

    if snapshot.mutation_after_checkpoint:
        reasons.add("MUTATION_AFTER_CHECKPOINT")
        actions.add(ContextGuardAction.CHECKPOINT_NOW)
    if snapshot.recovery_pointer_state is RecoveryPointerState.UNKNOWN:
        reasons.add("RECOVERY_POINTER_UNKNOWN")
        actions.add(ContextGuardAction.REFRESH_RECOVERY_POINTER)
    elif snapshot.recovery_pointer_state is RecoveryPointerState.MISSING:
        reasons.add("RECOVERY_POINTER_MISSING")
        actions.add(ContextGuardAction.REFRESH_RECOVERY_POINTER)

    executions_recoverable = (
        snapshot.outstanding_execution_count == 0
        or snapshot.outstanding_executions_recoverable is True
    )
    # Rotation readiness is a durability property, not mutation authority.
    # A non-FRESH continuity state may still be safely handed to a new session
    # when the current checkpoint captured it and all recovery pointers exist.
    # The new session remains fail-closed for mutation until it reconciles.
    rotation_ready = (
        snapshot.checkpoint_state is CheckpointState.CURRENT
        and not snapshot.mutation_after_checkpoint
        and snapshot.recovery_pointer_state is RecoveryPointerState.READY
        and executions_recoverable
    )

    pressure = snapshot.context_pressure
    if pressure is ContextPressure.NEAR_LIMIT:
        reasons.add("CONTEXT_NEAR_LIMIT")
    elif pressure is ContextPressure.UNKNOWN:
        reasons.add("CONTEXT_PRESSURE_UNKNOWN")
    elif pressure is ContextPressure.CROWDED:
        reasons.add("CONTEXT_CROWDED")

    hard_red = (
        not continuity_fresh
        or (
            snapshot.outstanding_execution_count > 0
            and snapshot.outstanding_executions_recoverable is not True
        )
        or (pressure is ContextPressure.NEAR_LIMIT and not rotation_ready)
    )
    if hard_red:
        status = ContextGuardStatus.RED
    elif pressure is not ContextPressure.NORMAL or not rotation_ready:
        status = ContextGuardStatus.YELLOW
    else:
        status = ContextGuardStatus.GREEN

    if pressure is ContextPressure.NEAR_LIMIT and rotation_ready:
        actions.add(ContextGuardAction.ROTATE_SESSION)

    if status is ContextGuardStatus.GREEN:
        actions.add(ContextGuardAction.CONTINUE)
    elif (
        pressure in {ContextPressure.CROWDED, ContextPressure.UNKNOWN}
        and ContextGuardAction.CHECKPOINT_NOW not in actions
        and ContextGuardAction.REFRESH_RECOVERY_POINTER not in actions
        and ContextGuardAction.RECOVER_OUTSTANDING_EXECUTIONS not in actions
        and ContextGuardAction.RECONCILE_CONTINUITY not in actions
    ):
        actions.add(ContextGuardAction.CHECKPOINT_AT_NEXT_BOUNDARY)

    return ContextGuardVerdict(
        status=status,
        rotation_ready=rotation_ready,
        reason_codes=_ordered_reasons(reasons),
        actions=_ordered_actions(actions),
    )
