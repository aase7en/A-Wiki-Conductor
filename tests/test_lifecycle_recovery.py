import pytest

from a_conductor.lifecycle import (
    LifecycleAction,
    LifecycleDecision,
    LifecyclePlan,
    LifecycleStep,
)
from a_conductor.lifecycle_executor import LifecycleCheckpoint
from a_conductor.lifecycle_recovery import (
    LifecycleReconciliationAssessment,
    LifecycleResumeDecision,
    plan_lifecycle_resume,
)


def start_plan() -> LifecyclePlan:
    return LifecyclePlan(
        action=LifecycleAction.START,
        decision=LifecycleDecision.PROCEED,
        reason_code="START_ALLOWED",
        steps=(
            LifecycleStep.VERIFY_ASSIGNMENT,
            LifecycleStep.VERIFY_RESOURCES,
            LifecycleStep.RENDER_PROFILE,
            LifecycleStep.PREFLIGHT,
            LifecycleStep.START_OWNED_PROCESS,
            LifecycleStep.WAIT_READY,
            LifecycleStep.VERIFY_PROJECT_IDENTITY,
            LifecycleStep.EMIT_EVIDENCE,
        ),
    )


def checkpoint(
    sequence_no: int,
    step: LifecycleStep,
    *,
    transaction_id: str = "txn-001",
    action: LifecycleAction = LifecycleAction.START,
) -> LifecycleCheckpoint:
    return LifecycleCheckpoint(
        transaction_id=transaction_id,
        sequence_no=sequence_no,
        action=action,
        step=step,
        evidence_ref=f"EVID-{sequence_no}",
    )


def prefix(plan: LifecyclePlan, count: int, *, transaction_id: str = "txn-001") -> tuple[LifecycleCheckpoint, ...]:
    return tuple(
        checkpoint(index, step, transaction_id=transaction_id)
        for index, step in enumerate(plan.steps[:count], start=1)
    )


def test_consistent_empty_journal_resumes_from_first_step() -> None:
    plan = start_plan()

    result = plan_lifecycle_resume(
        transaction_id="txn-001",
        plan=plan,
        checkpoints=(),
        assessment=LifecycleReconciliationAssessment.CONSISTENT_WITH_JOURNAL,
    )

    assert result.decision is LifecycleResumeDecision.RESUME
    assert result.reason_code == "RESUME_FROM_JOURNAL"
    assert result.durable_steps == ()
    assert result.remaining_steps == plan.steps
    assert result.next_step is LifecycleStep.VERIFY_ASSIGNMENT


def test_consistent_partial_prefix_resumes_at_exact_next_step() -> None:
    plan = start_plan()
    checkpoints = prefix(plan, 5)

    result = plan_lifecycle_resume(
        transaction_id="txn-001",
        plan=plan,
        checkpoints=checkpoints,
        assessment=LifecycleReconciliationAssessment.CONSISTENT_WITH_JOURNAL,
    )

    assert result.decision is LifecycleResumeDecision.RESUME
    assert result.durable_steps == plan.steps[:5]
    assert result.remaining_steps == plan.steps[5:]
    assert result.next_step is LifecycleStep.WAIT_READY


def test_consistent_complete_journal_is_complete() -> None:
    plan = start_plan()
    checkpoints = prefix(plan, len(plan.steps))

    result = plan_lifecycle_resume(
        transaction_id="txn-001",
        plan=plan,
        checkpoints=checkpoints,
        assessment=LifecycleReconciliationAssessment.CONSISTENT_WITH_JOURNAL,
    )

    assert result.decision is LifecycleResumeDecision.COMPLETE
    assert result.reason_code == "JOURNAL_COMPLETE"
    assert result.durable_steps == plan.steps
    assert result.remaining_steps == ()
    assert result.next_step is None


@pytest.mark.parametrize(
    ("assessment", "expected_decision", "reason_code"),
    [
        (
            LifecycleReconciliationAssessment.UNKNOWN,
            LifecycleResumeDecision.RECOVERY_REQUIRED,
            "RECONCILIATION_UNKNOWN",
        ),
        (
            LifecycleReconciliationAssessment.MUTATION_AHEAD_OF_JOURNAL,
            LifecycleResumeDecision.RECOVERY_REQUIRED,
            "MUTATION_AHEAD_OF_JOURNAL",
        ),
        (
            LifecycleReconciliationAssessment.UNEXPECTED_DRIFT,
            LifecycleResumeDecision.REFUSE,
            "UNEXPECTED_DRIFT",
        ),
    ],
)
def test_uncertain_ahead_or_drift_state_never_resumes(
    assessment: LifecycleReconciliationAssessment,
    expected_decision: LifecycleResumeDecision,
    reason_code: str,
) -> None:
    plan = start_plan()

    result = plan_lifecycle_resume(
        transaction_id="txn-001",
        plan=plan,
        checkpoints=prefix(plan, 3),
        assessment=assessment,
    )

    assert result.decision is expected_decision
    assert result.reason_code == reason_code
    assert result.next_step is None


def test_non_proceed_plan_is_not_resumable() -> None:
    plan = LifecyclePlan(
        action=LifecycleAction.START,
        decision=LifecycleDecision.NOOP,
        reason_code="ALREADY_RUNNING",
        steps=(LifecycleStep.EMIT_EVIDENCE,),
    )

    result = plan_lifecycle_resume(
        transaction_id="txn-001",
        plan=plan,
        checkpoints=(),
        assessment=LifecycleReconciliationAssessment.CONSISTENT_WITH_JOURNAL,
    )

    assert result.decision is LifecycleResumeDecision.REFUSE
    assert result.reason_code == "PLAN_NOT_EXECUTABLE"


def test_checkpoint_transaction_mismatch_is_refused() -> None:
    plan = start_plan()

    result = plan_lifecycle_resume(
        transaction_id="txn-001",
        plan=plan,
        checkpoints=prefix(plan, 1, transaction_id="different-txn"),
        assessment=LifecycleReconciliationAssessment.CONSISTENT_WITH_JOURNAL,
    )

    assert result.decision is LifecycleResumeDecision.REFUSE
    assert result.reason_code == "CHECKPOINT_TRANSACTION_MISMATCH"


def test_checkpoint_action_mismatch_is_refused() -> None:
    plan = start_plan()
    checkpoints = (
        checkpoint(1, LifecycleStep.VERIFY_ASSIGNMENT, action=LifecycleAction.STOP),
    )

    result = plan_lifecycle_resume(
        transaction_id="txn-001",
        plan=plan,
        checkpoints=checkpoints,
        assessment=LifecycleReconciliationAssessment.CONSISTENT_WITH_JOURNAL,
    )

    assert result.decision is LifecycleResumeDecision.REFUSE
    assert result.reason_code == "CHECKPOINT_ACTION_MISMATCH"


def test_checkpoint_sequence_gap_is_refused() -> None:
    plan = start_plan()
    checkpoints = (
        checkpoint(1, LifecycleStep.VERIFY_ASSIGNMENT),
        checkpoint(3, LifecycleStep.VERIFY_RESOURCES),
    )

    result = plan_lifecycle_resume(
        transaction_id="txn-001",
        plan=plan,
        checkpoints=checkpoints,
        assessment=LifecycleReconciliationAssessment.CONSISTENT_WITH_JOURNAL,
    )

    assert result.decision is LifecycleResumeDecision.REFUSE
    assert result.reason_code == "CHECKPOINT_SEQUENCE_INVALID"


def test_checkpoint_step_must_match_exact_plan_prefix() -> None:
    plan = start_plan()
    checkpoints = (
        checkpoint(1, LifecycleStep.VERIFY_ASSIGNMENT),
        checkpoint(2, LifecycleStep.PREFLIGHT),
    )

    result = plan_lifecycle_resume(
        transaction_id="txn-001",
        plan=plan,
        checkpoints=checkpoints,
        assessment=LifecycleReconciliationAssessment.CONSISTENT_WITH_JOURNAL,
    )

    assert result.decision is LifecycleResumeDecision.REFUSE
    assert result.reason_code == "CHECKPOINT_PLAN_MISMATCH"


def test_checkpoint_longer_than_plan_is_refused() -> None:
    plan = LifecyclePlan(
        action=LifecycleAction.STOP,
        decision=LifecycleDecision.PROCEED,
        reason_code="STOP_ALLOWED",
        steps=(LifecycleStep.TARGETED_STOP,),
    )
    checkpoints = (
        checkpoint(1, LifecycleStep.TARGETED_STOP, action=LifecycleAction.STOP),
        checkpoint(2, LifecycleStep.WAIT_EXIT, action=LifecycleAction.STOP),
    )

    result = plan_lifecycle_resume(
        transaction_id="txn-001",
        plan=plan,
        checkpoints=checkpoints,
        assessment=LifecycleReconciliationAssessment.CONSISTENT_WITH_JOURNAL,
    )

    assert result.decision is LifecycleResumeDecision.REFUSE
    assert result.reason_code == "CHECKPOINT_PLAN_MISMATCH"


@pytest.mark.parametrize("transaction_id", ["", " ", "\t"])
def test_blank_transaction_id_is_rejected_before_planning(transaction_id: str) -> None:
    with pytest.raises(ValueError, match="transaction_id must not be blank"):
        plan_lifecycle_resume(
            transaction_id=transaction_id,
            plan=start_plan(),
            checkpoints=(),
            assessment=LifecycleReconciliationAssessment.CONSISTENT_WITH_JOURNAL,
        )


def test_resume_result_is_transaction_scoped() -> None:
    result = plan_lifecycle_resume(
        transaction_id="txn-resume-42",
        plan=start_plan(),
        checkpoints=(),
        assessment=LifecycleReconciliationAssessment.CONSISTENT_WITH_JOURNAL,
    )

    assert result.transaction_id == "txn-resume-42"
