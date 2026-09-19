from __future__ import annotations

import pytest

from a_conductor.context_rollover_guard import (
    CheckpointState,
    ContextGuardAction,
    ContextGuardStatus,
    ContextPressure,
    RecoveryPointerState,
    SessionRolloverSnapshot,
    classify_context_rollover,
)
from a_conductor.continuity_guard import (
    ContinuityClassification,
    ContinuityFinding,
    ContinuityVerdict,
    ReconciliationAction,
)


def fresh_continuity() -> ContinuityVerdict:
    return ContinuityVerdict(
        classification=ContinuityClassification.FRESH,
        safe_to_mutate=True,
        findings=(),
        reconciliation_actions=(),
    )


def blocked_continuity() -> ContinuityVerdict:
    finding = ContinuityFinding(
        kind=ContinuityClassification.HEAD_DRIFT,
        reason_code="LOCAL_HEAD_NOT_EXPECTED",
        detail="test drift",
    )
    return ContinuityVerdict(
        classification=ContinuityClassification.HEAD_DRIFT,
        safe_to_mutate=False,
        findings=(finding,),
        reconciliation_actions=(ReconciliationAction.REALIGN_TO_EXPECTED_HEAD,),
    )


def snapshot(**overrides) -> SessionRolloverSnapshot:
    values = {
        "continuity": fresh_continuity(),
        "context_pressure": ContextPressure.NORMAL,
        "checkpoint_state": CheckpointState.CURRENT,
        "mutation_after_checkpoint": False,
        "recovery_pointer_state": RecoveryPointerState.READY,
        "outstanding_execution_count": 0,
        "outstanding_executions_recoverable": None,
    }
    values.update(overrides)
    return SessionRolloverSnapshot(**values)


def test_normal_fresh_current_snapshot_is_green() -> None:
    verdict = classify_context_rollover(snapshot())
    assert verdict.status is ContextGuardStatus.GREEN
    assert verdict.rotation_ready is True
    assert verdict.reason_codes == ()
    assert verdict.actions == (ContextGuardAction.CONTINUE,)


def test_crowded_context_is_yellow_even_when_durable_state_is_ready() -> None:
    verdict = classify_context_rollover(
        snapshot(context_pressure=ContextPressure.CROWDED)
    )
    assert verdict.status is ContextGuardStatus.YELLOW
    assert verdict.rotation_ready is True
    assert verdict.reason_codes == ("CONTEXT_CROWDED",)
    assert verdict.actions == (ContextGuardAction.CHECKPOINT_AT_NEXT_BOUNDARY,)


def test_near_limit_with_rotation_ready_recommends_rotation() -> None:
    verdict = classify_context_rollover(
        snapshot(context_pressure=ContextPressure.NEAR_LIMIT)
    )
    assert verdict.status is ContextGuardStatus.YELLOW
    assert verdict.rotation_ready is True
    assert verdict.reason_codes == ("CONTEXT_NEAR_LIMIT",)
    assert verdict.actions == (ContextGuardAction.ROTATE_SESSION,)


@pytest.mark.parametrize(
    ("checkpoint_state", "expected_reason"),
    [
        (CheckpointState.STALE, "CHECKPOINT_STALE"),
        (CheckpointState.UNKNOWN, "CHECKPOINT_UNKNOWN"),
    ],
)
def test_near_limit_with_bad_checkpoint_is_red(
    checkpoint_state: CheckpointState, expected_reason: str
) -> None:
    verdict = classify_context_rollover(
        snapshot(
            context_pressure=ContextPressure.NEAR_LIMIT,
            checkpoint_state=checkpoint_state,
        )
    )
    assert verdict.status is ContextGuardStatus.RED
    assert verdict.rotation_ready is False
    assert expected_reason in verdict.reason_codes
    assert ContextGuardAction.CHECKPOINT_NOW in verdict.actions


def test_near_limit_with_post_checkpoint_mutation_is_red() -> None:
    verdict = classify_context_rollover(
        snapshot(
            context_pressure=ContextPressure.NEAR_LIMIT,
            mutation_after_checkpoint=True,
        )
    )
    assert verdict.status is ContextGuardStatus.RED
    assert verdict.rotation_ready is False
    assert "MUTATION_AFTER_CHECKPOINT" in verdict.reason_codes
    assert ContextGuardAction.CHECKPOINT_NOW in verdict.actions


def test_unknown_context_pressure_never_returns_green() -> None:
    verdict = classify_context_rollover(
        snapshot(context_pressure=ContextPressure.UNKNOWN)
    )
    assert verdict.status is ContextGuardStatus.YELLOW
    assert verdict.reason_codes == ("CONTEXT_PRESSURE_UNKNOWN",)


def test_nonfresh_continuity_dominates_context_signal() -> None:
    verdict = classify_context_rollover(snapshot(continuity=blocked_continuity()))
    assert verdict.status is ContextGuardStatus.RED
    assert verdict.rotation_ready is False
    assert verdict.reason_codes[0] == "CONTINUITY_NOT_FRESH"
    assert verdict.actions[0] is ContextGuardAction.RECONCILE_CONTINUITY

def test_missing_task_recovery_pointer_is_yellow_until_near_limit() -> None:
    normal = classify_context_rollover(
        snapshot(recovery_pointer_state=RecoveryPointerState.MISSING)
    )
    urgent = classify_context_rollover(
        snapshot(
            context_pressure=ContextPressure.NEAR_LIMIT,
            recovery_pointer_state=RecoveryPointerState.MISSING,
        )
    )
    assert normal.status is ContextGuardStatus.YELLOW
    assert urgent.status is ContextGuardStatus.RED
    assert normal.rotation_ready is False
    assert ContextGuardAction.REFRESH_RECOVERY_POINTER in normal.actions


@pytest.mark.parametrize("recoverable", [False, None])
def test_unrecoverable_outstanding_execution_is_red(
    recoverable: bool | None,
) -> None:
    verdict = classify_context_rollover(
        snapshot(
            outstanding_execution_count=2,
            outstanding_executions_recoverable=recoverable,
        )
    )
    assert verdict.status is ContextGuardStatus.RED
    assert verdict.rotation_ready is False
    assert ContextGuardAction.RECOVER_OUTSTANDING_EXECUTIONS in verdict.actions


def test_recoverable_outstanding_executions_can_remain_green() -> None:
    verdict = classify_context_rollover(
        snapshot(
            outstanding_execution_count=3,
            outstanding_executions_recoverable=True,
        )
    )
    assert verdict.status is ContextGuardStatus.GREEN
    assert verdict.rotation_ready is True


def test_same_snapshot_is_idempotent() -> None:
    item = snapshot(
        context_pressure=ContextPressure.CROWDED,
        checkpoint_state=CheckpointState.STALE,
        recovery_pointer_state=RecoveryPointerState.UNKNOWN,
    )
    assert classify_context_rollover(item) == classify_context_rollover(item)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"context_pressure": "NORMAL"},
        {"checkpoint_state": "CURRENT"},
        {"recovery_pointer_state": "READY"},
        {"mutation_after_checkpoint": 1},
        {"outstanding_execution_count": -1},
        {"outstanding_execution_count": True},
        {
            "outstanding_execution_count": 1,
            "outstanding_executions_recoverable": "yes",
        },
    ],
)
def test_invalid_inputs_are_rejected(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        snapshot(**kwargs)


def test_combined_findings_have_stable_reason_and_action_order() -> None:
    verdict = classify_context_rollover(
        snapshot(
            context_pressure=ContextPressure.NEAR_LIMIT,
            checkpoint_state=CheckpointState.UNKNOWN,
            mutation_after_checkpoint=True,
            recovery_pointer_state=RecoveryPointerState.UNKNOWN,
        )
    )
    assert verdict.status is ContextGuardStatus.RED
    assert verdict.reason_codes == (
        "CHECKPOINT_UNKNOWN",
        "MUTATION_AFTER_CHECKPOINT",
        "RECOVERY_POINTER_UNKNOWN",
        "CONTEXT_NEAR_LIMIT",
    )
    assert verdict.actions == (
        ContextGuardAction.CHECKPOINT_NOW,
        ContextGuardAction.REFRESH_RECOVERY_POINTER,
    )
