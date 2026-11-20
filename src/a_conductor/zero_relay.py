"""WO-P1-165 / ZRA-2 Phase A — pure durable-reference decision state machine.

This module classifies one verified durable execution/result identity plus its
deterministic verification outcome and independent review evidence into the
ZRA-2 terminal decisions:

    ACCEPTED | REPAIR_REQUIRED | REJECTED | RECOVERY_REQUIRED

It is intentionally PURE: no provider, Git, review transport, file, process,
network, or clock I/O, and no scheduler/store/lease/retry authority. Raw
prompt or response text is never an authority field. Every ambiguous,
malformed, or mismatched input fails closed with a stable typed error before
any decision is produced.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_MAX_IDENTITY_LENGTH = 256


class ZeroRelayError(RuntimeError):
    """Stable typed failure; never echoes arbitrary input text."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _identity_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field} is invalid")
    if len(value) > _MAX_IDENTITY_LENGTH:
        raise ValueError(f"{field} is invalid")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise ValueError(f"{field} is invalid")
    return value


def _sha256_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field} is invalid")
    return value


def _generation(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value not in (0, 1):
        raise ValueError("generation is invalid")
    return value


class ExecutionOutcome(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    TIMEOUT = "TIMEOUT"
    AMBIGUOUS = "AMBIGUOUS"


class VerificationOutcome(str, Enum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


class ReviewDisposition(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class RelayDecision(str, Enum):
    ACCEPTED = "ACCEPTED"
    REPAIR_REQUIRED = "REPAIR_REQUIRED"
    REJECTED = "REJECTED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


@dataclass(frozen=True, slots=True)
class ResultIdentity:
    """Exact durable execution/result binding (authority vocabulary only)."""

    task_contract_ref: str
    task_sha256: str
    result_ref: str
    result_sha256: str
    attempt_id: str
    generation: int
    author_execution_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "task_contract_ref",
            _identity_text(self.task_contract_ref, "task_contract_ref"),
        )
        object.__setattr__(self, "task_sha256", _sha256_text(self.task_sha256, "task_sha256"))
        object.__setattr__(self, "result_ref", _identity_text(self.result_ref, "result_ref"))
        object.__setattr__(self, "result_sha256", _sha256_text(self.result_sha256, "result_sha256"))
        object.__setattr__(self, "attempt_id", _identity_text(self.attempt_id, "attempt_id"))
        object.__setattr__(self, "generation", _generation(self.generation))
        object.__setattr__(
            self, "author_execution_id",
            _identity_text(self.author_execution_id, "author_execution_id"),
        )


@dataclass(frozen=True, slots=True)
class ReviewEvidence:
    """Independent review outcome bound to the exact reviewed identity."""

    task_contract_ref: str
    task_sha256: str
    result_ref: str
    result_sha256: str
    attempt_id: str
    generation: int
    reviewer_execution_id: str
    disposition: ReviewDisposition

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "task_contract_ref",
            _identity_text(self.task_contract_ref, "task_contract_ref"),
        )
        object.__setattr__(self, "task_sha256", _sha256_text(self.task_sha256, "task_sha256"))
        object.__setattr__(self, "result_ref", _identity_text(self.result_ref, "result_ref"))
        object.__setattr__(self, "result_sha256", _sha256_text(self.result_sha256, "result_sha256"))
        object.__setattr__(self, "attempt_id", _identity_text(self.attempt_id, "attempt_id"))
        object.__setattr__(self, "generation", _generation(self.generation))
        object.__setattr__(
            self, "reviewer_execution_id",
            _identity_text(self.reviewer_execution_id, "reviewer_execution_id"),
        )
        if not isinstance(self.disposition, ReviewDisposition):
            raise ValueError("disposition is invalid")


@dataclass(frozen=True, slots=True)
class RelayOutcome:
    """Terminal decision plus, only for REPAIR_REQUIRED, the exact next
    repair generation (always 1)."""

    decision: RelayDecision
    next_repair_generation: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.decision, RelayDecision):
            raise ValueError("decision is invalid")
        if self.decision is RelayDecision.REPAIR_REQUIRED:
            if self.next_repair_generation != 1:
                raise ValueError("next_repair_generation is invalid")
        elif self.next_repair_generation is not None:
            raise ValueError("next_repair_generation is invalid")


def _enum_or_error(value: object, enum_cls, code: str):
    if isinstance(value, enum_cls):
        return value
    raise ZeroRelayError(code)


def classify_relay_decision(
    result: ResultIdentity,
    *,
    execution_outcome: ExecutionOutcome,
    verification_outcome: VerificationOutcome,
    review: ReviewEvidence | None = None,
) -> RelayOutcome:
    """Pure ZRA-2 Phase-A classifier.

    Decision order: typed inputs -> identity cross-binding -> execution
    recovery routing -> verification/review combination. The same exact
    durable inputs always yield the same outcome; ambiguity never repairs.
    """
    if not isinstance(result, ResultIdentity):
        raise ZeroRelayError("INPUT_INVALID")
    execution = _enum_or_error(execution_outcome, ExecutionOutcome, "INPUT_INVALID")
    verification = _enum_or_error(verification_outcome, VerificationOutcome, "INPUT_INVALID")
    if review is not None and not isinstance(review, ReviewEvidence):
        raise ZeroRelayError("INPUT_INVALID")

    if review is not None:
        if (
            review.task_contract_ref != result.task_contract_ref
            or review.task_sha256 != result.task_sha256
            or review.result_ref != result.result_ref
            or review.result_sha256 != result.result_sha256
            or review.attempt_id != result.attempt_id
            or review.generation != result.generation
        ):
            raise ZeroRelayError("REVIEW_IDENTITY_MISMATCH")
        if review.reviewer_execution_id == result.author_execution_id:
            raise ZeroRelayError("AUTHOR_REVIEWER_NOT_DISTINCT")

    if execution in (ExecutionOutcome.UNKNOWN, ExecutionOutcome.TIMEOUT, ExecutionOutcome.AMBIGUOUS):
        return RelayOutcome(RelayDecision.RECOVERY_REQUIRED, None)

    if execution is ExecutionOutcome.FAILED:
        return RelayOutcome(RelayDecision.REJECTED, None)

    # execution SUCCEEDED
    if verification is VerificationOutcome.FAILED:
        if review is not None and review.disposition is ReviewDisposition.ACCEPTED:
            raise ZeroRelayError("VERIFICATION_REVIEW_CONTRADICTION")
        return RelayOutcome(RelayDecision.REJECTED, None)

    if review is None:
        raise ZeroRelayError("REVIEW_EVIDENCE_REQUIRED")

    if review.disposition is ReviewDisposition.ACCEPTED:
        return RelayOutcome(RelayDecision.ACCEPTED, None)

    if result.generation == 0:
        return RelayOutcome(RelayDecision.REPAIR_REQUIRED, 1)
    return RelayOutcome(RelayDecision.REJECTED, None)
