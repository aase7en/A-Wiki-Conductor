"""WO-P1-583: pure queue-submission dedupe guard; no transport, I/O, or authority.

Encodes the #583 defect regression: one task/claim intent must never admit a
second governance-bootstrap mutation owner while an equivalent queued
submission is pending or turn side effects stay unharvested.
"""
from __future__ import annotations

import dataclasses

import pytest

from a_conductor.codex_goal_api_adapter import QueueEntry, TurnEvidence
from a_conductor.codex_queue_submission_guard import (
    GuardAction, GuardDecision, QueueSubmissionGuardError,
    evaluate_bootstrap_guard, queue_submission_task_key,
)


class StringSubclass(str):
    __hash__ = None


def entry(submission_id="queue-1", correlation="correlation-1"):
    return QueueEntry(submission_id=submission_id, client_user_message_id=correlation)


def turn(turn_id="turn-1", status="completed"):
    return TurnEvidence(turn_id=turn_id, status=status)


def evaluate(
    task_ref="issue:581",
    queue_entries=(),
    turns=(),
    queue_evidence_complete=True,
    turn_evidence_complete=True,
    queue_next_cursor=None,
    turn_next_cursor=None,
):
    return evaluate_bootstrap_guard(
        task_ref,
        queue_entries=tuple(queue_entries),
        turns=tuple(turns),
        queue_evidence_complete=queue_evidence_complete,
        turn_evidence_complete=turn_evidence_complete,
        queue_next_cursor=queue_next_cursor,
        turn_next_cursor=turn_next_cursor,
    )


# --- task key derivation -----------------------------------------------------

@pytest.mark.parametrize("task_ref,expected", [
    ("WO-P1-583", "awc-tsk-v1:17c23344a44f3238"),
    ("issue:581", "awc-tsk-v1:935eae8ca1d52b18"),
])
def test_task_key_pinned_vectors(task_ref, expected):
    assert queue_submission_task_key(task_ref) == expected


def test_task_key_is_deterministic_and_distinct():
    assert queue_submission_task_key("WO-P1-583") == queue_submission_task_key("WO-P1-583")
    assert (queue_submission_task_key("WO-P1-583")
            != queue_submission_task_key("issue:581"))


@pytest.mark.parametrize("task_ref", [
    None, "", "   ", " padded", "padded ", "con\ntrol", "x" * 129, 5, StringSubclass("WO-P1-583"),
])
def test_task_key_rejects_invalid_task_ref(task_ref):
    with pytest.raises(QueueSubmissionGuardError, match="QUEUE_GUARD_TASK_REF_INVALID"):
        queue_submission_task_key(task_ref)


# --- clear evidence -> PROCEED ------------------------------------------------

def test_clear_evidence_proceeds():
    decision = evaluate(queue_entries=[entry("q-foreign", "correlation-1")],
                        turns=[turn("t-1", "completed"), turn("t-2", "inProgress")])
    assert decision.action is GuardAction.PROCEED
    assert decision.reason_code == "QUEUE_GUARD_CLEAR"
    assert decision.duplicate_submission_ids == ()
    assert decision.interrupted_turn_ids == ()


# --- duplicate pending submission ----------------------------------------------

def test_duplicate_pending_submission_blocks():
    key = queue_submission_task_key("issue:581")
    decision = evaluate(queue_entries=[
        entry("q-other", "correlation-1"),
        entry("q-dup", key),
    ])
    assert decision.action is GuardAction.DUPLICATE_TASK_SUBMISSION_PENDING
    assert decision.reason_code == "QUEUE_GUARD_DUPLICATE_PENDING"
    assert decision.duplicate_submission_ids == ("q-dup",)


def test_multiple_duplicates_listed_in_observed_order():
    key = queue_submission_task_key("issue:581")
    decision = evaluate(queue_entries=[entry("q-a", key), entry("q-b", key), entry("q-c", key)])
    assert decision.duplicate_submission_ids == ("q-a", "q-b", "q-c")


def test_foreign_correlation_never_matches():
    decision = evaluate(queue_entries=[entry("q-1", "correlation-1"),
                                       entry("q-2", "awc-tsk-v0:deadbeefdeadbeef")])
    assert decision.action is GuardAction.PROCEED


# --- interrupted turns ----------------------------------------------------------

def test_interrupted_turn_requires_reconciliation():
    decision = evaluate(turns=[turn("t-1", "completed"), turn("t-2", "interrupted")])
    assert decision.action is GuardAction.RECONCILIATION_REQUIRED
    assert decision.reason_code == "QUEUE_GUARD_TURN_INTERRUPTED"
    assert decision.interrupted_turn_ids == ("t-2",)


def test_duplicate_outranks_reconciliation_and_surfaces_interrupted_turns():
    key = queue_submission_task_key("issue:581")
    decision = evaluate(queue_entries=[entry("q-dup", key)],
                        turns=[turn("t-1", "interrupted")])
    assert decision.action is GuardAction.DUPLICATE_TASK_SUBMISSION_PENDING
    assert decision.interrupted_turn_ids == ("t-1",)


# --- incomplete/unknown evidence fails closed ------------------------------------

def test_unattested_queue_evidence_fails_closed():
    decision = evaluate(queue_evidence_complete=False)
    assert decision.action is GuardAction.RECONCILIATION_REQUIRED
    assert decision.reason_code == "QUEUE_GUARD_EVIDENCE_INCOMPLETE"


def test_unattested_turn_evidence_fails_closed():
    decision = evaluate(turn_evidence_complete=False)
    assert decision.action is GuardAction.RECONCILIATION_REQUIRED
    assert decision.reason_code == "QUEUE_GUARD_EVIDENCE_INCOMPLETE"


def test_partial_queue_pagination_never_proceeds():
    decision = evaluate(queue_next_cursor="page-2")
    assert decision.action is GuardAction.RECONCILIATION_REQUIRED
    assert decision.reason_code == "QUEUE_GUARD_EVIDENCE_INCOMPLETE"


def test_partial_turn_pagination_never_proceeds():
    decision = evaluate(turn_next_cursor="page-2")
    assert decision.action is GuardAction.RECONCILIATION_REQUIRED
    assert decision.reason_code == "QUEUE_GUARD_EVIDENCE_INCOMPLETE"


def test_incomplete_evidence_fails_closed_even_with_clear_page():
    decision = evaluate(queue_entries=[entry("q-foreign", "correlation-1")],
                        queue_next_cursor="page-2")
    assert decision.action is GuardAction.RECONCILIATION_REQUIRED


def test_observed_duplicate_outranks_incomplete_pagination():
    key = queue_submission_task_key("issue:581")
    decision = evaluate(queue_entries=[entry("q-dup", key)], queue_next_cursor="page-2")
    assert decision.action is GuardAction.DUPLICATE_TASK_SUBMISSION_PENDING
    assert decision.duplicate_submission_ids == ("q-dup",)


@pytest.mark.parametrize("cursor", ["", " pad", "con\ntrol", StringSubclass("page-2")])
def test_invalid_cursor_rejected(cursor):
    with pytest.raises(QueueSubmissionGuardError, match="QUEUE_GUARD_EVIDENCE_INVALID"):
        evaluate(queue_next_cursor=cursor)


def test_evidence_overflow_rejected_before_scanning():
    key = queue_submission_task_key("issue:581")
    with pytest.raises(QueueSubmissionGuardError, match="QUEUE_GUARD_EVIDENCE_INVALID"):
        evaluate(queue_entries=[entry(f"q-{i}", key) for i in range(513)])
    with pytest.raises(QueueSubmissionGuardError, match="QUEUE_GUARD_EVIDENCE_INVALID"):
        evaluate(turns=[turn(f"t-{i}", "completed") for i in range(513)])


def test_evidence_boundary_512_accepted():
    decision = evaluate(queue_entries=[entry(f"q-{i}", "correlation-1") for i in range(512)],
                        turns=[turn(f"t-{i}", "completed") for i in range(512)])
    assert decision.action is GuardAction.PROCEED


# --- invalid evidence shapes fail typed -------------------------------------------

@pytest.mark.parametrize("queue_entries", [
    [entry("", "correlation-1")],
    [entry("q-1", "")],
    [entry("q-1", " correlation ")],
    [entry("q-1", "correlation-1"), entry("q-1", "correlation-2")],
    [("q-1", "correlation-1")],
    [QueueEntry(submission_id=StringSubclass("q-1"), client_user_message_id="correlation-1")],
])
def test_invalid_queue_evidence_raises(queue_entries):
    with pytest.raises(QueueSubmissionGuardError, match="QUEUE_GUARD_EVIDENCE_INVALID"):
        evaluate(queue_entries=queue_entries)


@pytest.mark.parametrize("turns", [
    [turn("", "completed")],
    [turn("t-1", "zombified")],
    [turn("t-1", "completed"), turn("t-1", "interrupted")],
    [("t-1", "completed")],
    [TurnEvidence(turn_id=StringSubclass("t-1"), status="completed")],
    [TurnEvidence(turn_id="t-1", status=StringSubclass("completed"))],
])
def test_invalid_turn_evidence_raises(turns):
    with pytest.raises(QueueSubmissionGuardError, match="QUEUE_GUARD_EVIDENCE_INVALID"):
        evaluate(turns=turns)


def test_evaluate_rejects_invalid_task_ref():
    with pytest.raises(QueueSubmissionGuardError, match="QUEUE_GUARD_TASK_REF_INVALID"):
        evaluate(task_ref="")


@pytest.mark.parametrize("kwargs", [
    {"queue_evidence_complete": 1},
    {"turn_evidence_complete": "yes"},
])
def test_evidence_flags_must_be_exact_bools(kwargs):
    with pytest.raises(QueueSubmissionGuardError, match="QUEUE_GUARD_EVIDENCE_INVALID"):
        evaluate(**kwargs)


# --- #583 observed-sequence regression ----------------------------------------------

def test_583_regression_second_bootstrap_attempt_never_proceeds():
    """First attempt enqueued intent X (pending entry exists); recovery turn
    evaluating the same intent must never receive PROCEED."""
    key = queue_submission_task_key("issue:581")
    for attempt_entries in (
        [entry("queue-row-1", key)],
        [entry("queue-row-1", key), entry("queue-row-2", key)],
    ):
        for turns_evidence in ((), (turn("t-1", "interrupted"),)):
            decision = evaluate(queue_entries=attempt_entries, turns=turns_evidence)
            assert decision.action is not GuardAction.PROCEED


# --- decision immutability --------------------------------------------------

def test_decision_is_immutable():
    decision = evaluate()
    with pytest.raises(dataclasses.FrozenInstanceError):
        decision.action = GuardAction.RECONCILIATION_REQUIRED


def test_decision_type_is_frozen_dataclass():
    assert dataclasses.is_dataclass(GuardDecision)
    assert GuardDecision.__dataclass_params__.frozen
