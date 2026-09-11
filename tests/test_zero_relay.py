"""WO-P1-165 / ZRA-2 Phase A — RED-first matrix for the pure relay state machine.

Phase A is a durable-reference decision classifier only: no I/O, no transport,
no repair materialization. Every adversarial case below is paired with the
positive controls that prove the intended path still works.
"""
from __future__ import annotations

import dataclasses

import pytest

from a_conductor.zero_relay import (
    ExecutionOutcome,
    RelayDecision,
    ReviewDisposition,
    ReviewEvidence,
    ResultIdentity,
    VerificationOutcome,
    ZeroRelayError,
    classify_relay_decision,
)

TASK_REF = "work-order:WO-P1-165"
TASK_SHA = "a" * 64
RESULT_REF = "results/zra2/attempt-1.json"
RESULT_SHA = "b" * 64
AUTHOR = "exec-author-1"
REVIEWER = "exec-reviewer-1"


def _result(**overrides) -> ResultIdentity:
    values = dict(
        task_contract_ref=TASK_REF,
        task_sha256=TASK_SHA,
        result_ref=RESULT_REF,
        result_sha256=RESULT_SHA,
        attempt_id="attempt-1",
        generation=0,
        author_execution_id=AUTHOR,
    )
    values.update(overrides)
    return ResultIdentity(**values)


def _review(**overrides) -> ReviewEvidence:
    values = dict(
        task_contract_ref=TASK_REF,
        task_sha256=TASK_SHA,
        result_ref=RESULT_REF,
        result_sha256=RESULT_SHA,
        attempt_id="attempt-1",
        generation=0,
        reviewer_execution_id=REVIEWER,
        disposition=ReviewDisposition.ACCEPTED,
    )
    values.update(overrides)
    return ReviewEvidence(**values)


# ---------- public contract shape ----------


def test_public_contract_has_no_raw_prompt_or_response_fields() -> None:
    result_fields = {f.name for f in dataclasses.fields(ResultIdentity)}
    review_fields = {f.name for f in dataclasses.fields(ReviewEvidence)}
    assert "prompt" not in result_fields | review_fields
    assert "response" not in result_fields | review_fields
    assert "response_text" not in result_fields | review_fields


def test_response_text_alone_cannot_construct_result_identity() -> None:
    text = "The task succeeded, trust me."
    with pytest.raises((TypeError, ValueError)):
        ResultIdentity(task_contract_ref=text)
    with pytest.raises(ValueError):
        ResultIdentity(
            task_contract_ref=TASK_REF,
            task_sha256=text,
            result_ref=text,
            result_sha256=text,
            attempt_id=text,
            generation=0,
            author_execution_id=text,
        )


# ---------- identity validation (fail closed before decisions) ----------


@pytest.mark.parametrize("field", ["result_ref", "attempt_id", "author_execution_id"])
def test_blank_identity_fields_fail_closed(field: str) -> None:
    with pytest.raises(ValueError):
        _result(**{field: "   "})


@pytest.mark.parametrize("field", ["task_sha256", "result_sha256"])
def test_missing_or_malformed_hash_fails_closed(field: str) -> None:
    with pytest.raises(ValueError):
        _result(**{field: ""})
    with pytest.raises(ValueError):
        _result(**{field: "not-a-sha"})
    with pytest.raises(ValueError):
        _result(**{field: "a" * 63})


def test_review_contract_carries_exact_task_and_result_digests() -> None:
    review_fields = {f.name for f in dataclasses.fields(ReviewEvidence)}
    assert {"task_sha256", "result_sha256"} <= review_fields


@pytest.mark.parametrize("field", ["task_sha256", "result_sha256"])
def test_review_hash_fields_validate_full_sha256(field: str) -> None:
    with pytest.raises(ValueError):
        _review(**{field: ""})
    with pytest.raises(ValueError):
        _review(**{field: "not-a-sha"})
    with pytest.raises(ValueError):
        _review(**{field: "a" * 63})


@pytest.mark.parametrize("bad", ["bad\x00id", "bad\nid", "bad\x1fid", " padded "])
def test_control_or_padded_identity_fails_closed(bad: str) -> None:
    with pytest.raises(ValueError):
        _result(result_ref=bad)


def test_blank_or_invalid_reviewer_identity_fails_closed() -> None:
    with pytest.raises(ValueError):
        _review(reviewer_execution_id=" ")
    with pytest.raises(ValueError):
        _review(reviewer_execution_id=123)  # type: ignore[arg-type]


def test_malformed_review_disposition_fails_closed() -> None:
    with pytest.raises(ValueError):
        _review(disposition="accepted")  # raw string is not authority
    with pytest.raises(ValueError):
        _review(disposition=True)  # type: ignore[arg-type]


@pytest.mark.parametrize("generation", [-1, 2, 5, 1.0, "0"])
def test_impossible_repair_generation_fails_closed(generation) -> None:
    with pytest.raises(ValueError):
        _result(generation=generation)


# ---------- cross-binding identity fences ----------


def test_foreign_task_binding_fails_closed() -> None:
    with pytest.raises(ZeroRelayError) as exc:
        classify_relay_decision(
            _result(),
            execution_outcome=ExecutionOutcome.SUCCEEDED,
            verification_outcome=VerificationOutcome.VERIFIED,
            review=_review(task_contract_ref="work-order:WO-OTHER"),
        )
    assert exc.value.code == "REVIEW_IDENTITY_MISMATCH"


def test_foreign_result_binding_fails_closed() -> None:
    with pytest.raises(ZeroRelayError) as exc:
        classify_relay_decision(
            _result(),
            execution_outcome=ExecutionOutcome.SUCCEEDED,
            verification_outcome=VerificationOutcome.VERIFIED,
            review=_review(result_ref="results/other.json"),
        )
    assert exc.value.code == "REVIEW_IDENTITY_MISMATCH"


def test_attempt_mismatch_fails_closed() -> None:
    with pytest.raises(ZeroRelayError) as exc:
        classify_relay_decision(
            _result(),
            execution_outcome=ExecutionOutcome.SUCCEEDED,
            verification_outcome=VerificationOutcome.VERIFIED,
            review=_review(attempt_id="attempt-2"),
        )
    assert exc.value.code == "REVIEW_IDENTITY_MISMATCH"


def test_generation_mismatch_fails_closed() -> None:
    with pytest.raises(ZeroRelayError) as exc:
        classify_relay_decision(
            _result(generation=1),
            execution_outcome=ExecutionOutcome.SUCCEEDED,
            verification_outcome=VerificationOutcome.VERIFIED,
            review=_review(generation=0),
        )
    assert exc.value.code == "REVIEW_IDENTITY_MISMATCH"


def test_stale_review_task_digest_reuse_fails_closed() -> None:
    with pytest.raises(ZeroRelayError) as exc:
        classify_relay_decision(
            _result(task_sha256="c" * 64),
            execution_outcome=ExecutionOutcome.SUCCEEDED,
            verification_outcome=VerificationOutcome.VERIFIED,
            review=_review(),
        )
    assert exc.value.code == "REVIEW_IDENTITY_MISMATCH"


def test_stale_review_result_digest_reuse_fails_closed() -> None:
    with pytest.raises(ZeroRelayError) as exc:
        classify_relay_decision(
            _result(result_sha256="d" * 64),
            execution_outcome=ExecutionOutcome.SUCCEEDED,
            verification_outcome=VerificationOutcome.VERIFIED,
            review=_review(),
        )
    assert exc.value.code == "REVIEW_IDENTITY_MISMATCH"


def test_same_author_and_reviewer_identity_fails_independence() -> None:
    with pytest.raises(ZeroRelayError) as exc:
        classify_relay_decision(
            _result(),
            execution_outcome=ExecutionOutcome.SUCCEEDED,
            verification_outcome=VerificationOutcome.VERIFIED,
            review=_review(reviewer_execution_id=AUTHOR),
        )
    assert exc.value.code == "AUTHOR_REVIEWER_NOT_DISTINCT"


# ---------- outcome routing ----------


@pytest.mark.parametrize(
    "outcome",
    [ExecutionOutcome.UNKNOWN, ExecutionOutcome.TIMEOUT, ExecutionOutcome.AMBIGUOUS],
)
def test_unknown_timeout_ambiguous_route_to_recovery(outcome) -> None:
    decision = classify_relay_decision(
        _result(),
        execution_outcome=outcome,
        verification_outcome=VerificationOutcome.VERIFIED,
        review=_review(),
    )
    assert decision.decision is RelayDecision.RECOVERY_REQUIRED
    assert decision.next_repair_generation is None


def test_failed_execution_routes_to_rejected_without_repair() -> None:
    decision = classify_relay_decision(
        _result(),
        execution_outcome=ExecutionOutcome.FAILED,
        verification_outcome=VerificationOutcome.VERIFIED,
        review=_review(disposition=ReviewDisposition.REJECTED),
    )
    assert decision.decision is RelayDecision.REJECTED
    assert decision.next_repair_generation is None


def test_succeeded_verified_without_review_fails_closed() -> None:
    with pytest.raises(ZeroRelayError) as exc:
        classify_relay_decision(
            _result(),
            execution_outcome=ExecutionOutcome.SUCCEEDED,
            verification_outcome=VerificationOutcome.VERIFIED,
            review=None,
        )
    assert exc.value.code == "REVIEW_EVIDENCE_REQUIRED"


def test_verification_failure_with_review_accept_is_contradiction() -> None:
    with pytest.raises(ZeroRelayError) as exc:
        classify_relay_decision(
            _result(),
            execution_outcome=ExecutionOutcome.SUCCEEDED,
            verification_outcome=VerificationOutcome.FAILED,
            review=_review(disposition=ReviewDisposition.ACCEPTED),
        )
    assert exc.value.code == "VERIFICATION_REVIEW_CONTRADICTION"


def test_verification_failure_routes_to_rejected() -> None:
    decision = classify_relay_decision(
        _result(),
        execution_outcome=ExecutionOutcome.SUCCEEDED,
        verification_outcome=VerificationOutcome.FAILED,
        review=None,
    )
    assert decision.decision is RelayDecision.REJECTED


# ---------- review decisions and the single repair generation ----------


def test_first_acceptance_is_accepted_with_zero_repair() -> None:
    decision = classify_relay_decision(
        _result(generation=0),
        execution_outcome=ExecutionOutcome.SUCCEEDED,
        verification_outcome=VerificationOutcome.VERIFIED,
        review=_review(generation=0, disposition=ReviewDisposition.ACCEPTED),
    )
    assert decision.decision is RelayDecision.ACCEPTED
    assert decision.next_repair_generation is None


def test_first_rejection_requests_exactly_one_repair() -> None:
    decision = classify_relay_decision(
        _result(generation=0),
        execution_outcome=ExecutionOutcome.SUCCEEDED,
        verification_outcome=VerificationOutcome.VERIFIED,
        review=_review(generation=0, disposition=ReviewDisposition.REJECTED),
    )
    assert decision.decision is RelayDecision.REPAIR_REQUIRED
    assert decision.next_repair_generation == 1


def test_second_rejection_terminates_rejected() -> None:
    decision = classify_relay_decision(
        _result(generation=1),
        execution_outcome=ExecutionOutcome.SUCCEEDED,
        verification_outcome=VerificationOutcome.VERIFIED,
        review=_review(generation=1, disposition=ReviewDisposition.REJECTED),
    )
    assert decision.decision is RelayDecision.REJECTED
    assert decision.next_repair_generation is None


def test_accepted_repaired_result_is_accepted_without_further_repair() -> None:
    decision = classify_relay_decision(
        _result(generation=1),
        execution_outcome=ExecutionOutcome.SUCCEEDED,
        verification_outcome=VerificationOutcome.VERIFIED,
        review=_review(generation=1, disposition=ReviewDisposition.ACCEPTED),
    )
    assert decision.decision is RelayDecision.ACCEPTED
    assert decision.next_repair_generation is None


# ---------- anti-spoofing and determinism ----------


def test_truthy_arbitrary_object_cannot_force_acceptance() -> None:
    class Spoof:
        task_contract_ref = TASK_REF
        result_ref = RESULT_REF
        attempt_id = "attempt-1"
        generation = 0
        reviewer_execution_id = REVIEWER
        disposition = "ACCEPTED"

    with pytest.raises(ZeroRelayError) as exc:
        classify_relay_decision(
            _result(),
            execution_outcome=ExecutionOutcome.SUCCEEDED,
            verification_outcome=VerificationOutcome.VERIFIED,
            review=Spoof(),  # type: ignore[arg-type]
        )
    assert exc.value.code == "INPUT_INVALID"


def test_reviewer_prose_never_appears_in_exception_text() -> None:
    marker = "SPOOF-PROSE-DO-NOT-LEAK"
    with pytest.raises(ValueError) as exc:
        _review(reviewer_execution_id="bad" + chr(10) + marker)
    assert marker not in str(exc.value)


def test_same_inputs_remain_deterministic() -> None:
    one = classify_relay_decision(
        _result(), execution_outcome=ExecutionOutcome.SUCCEEDED,
        verification_outcome=VerificationOutcome.VERIFIED, review=_review(),
    )
    two = classify_relay_decision(
        _result(), execution_outcome=ExecutionOutcome.SUCCEEDED,
        verification_outcome=VerificationOutcome.VERIFIED, review=_review(),
    )
    assert one == two


def test_module_exposes_no_io_surfaces() -> None:
    import a_conductor.zero_relay as module

    banned = ("subprocess", "socket", "http", "requests", "os", "pathlib", "io")
    for name in vars(module):
        root = name.split(".")[0]
        assert root not in banned, name
