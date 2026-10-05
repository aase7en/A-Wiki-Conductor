"""WO-P1-583: caller-side queue-submission dedupe guard (pure policy, no I/O).

Issue #583 proved App Server ``thread/queue/add`` treats
``client_user_message_id`` as correlation data only — no idempotency, no
dedupe (source evidence: #583 comment 5982737256). Interrupted Parent turns
plus queued-submission recovery therefore created two governance bootstrap
mutation owners for one task/claim hotspot.

Missing invariant restored here: for one task/claim intent, at most one
pending governance-bootstrap submission may exist, and a recovery/replay path
must prove no same-intent submission is pending (and no interrupted-turn
side-effect ambiguity) before creating any claim/worktree. Callers MUST
encode the deterministic task key from :func:`queue_submission_task_key` as
the ``client_user_message_id`` of every governance bootstrap submission so
queue equality is meaningful duplicate evidence.

The guard consumes only OBSERVED decoded evidence from the accepted
``codex_goal_api_adapter`` projections. It performs no transport, network,
process, Git, or persistence work, holds no state, defines no retries, and
confers no authority: PROCEED is a policy observation over supplied
evidence, never admission, ownership, completion, or mutation permission.
Unknown or invalid evidence fails closed.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from unicodedata import category

from .codex_goal_api_adapter import MAX_ID_CHARS, QueueEntry, TurnEvidence

TASK_KEY_PREFIX = "awc-tsk-v1:"
MAX_TASK_REF_CHARS = 128
# One call accepts at most this many entries/turns; larger evidence sets are
# rejected typed before scanning so decisions stay bounded (WO contract v2).
MAX_EVIDENCE_ITEMS = 512
_TURN_STATUSES = frozenset({"completed", "interrupted", "failed", "inProgress"})


class QueueSubmissionGuardError(ValueError):
    """Code-only preflight rejection; no request or side effect occurred."""


class GuardAction(Enum):
    PROCEED = "PROCEED"
    DUPLICATE_TASK_SUBMISSION_PENDING = "DUPLICATE_TASK_SUBMISSION_PENDING"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


@dataclass(frozen=True)
class GuardDecision:
    action: GuardAction
    reason_code: str
    duplicate_submission_ids: tuple[str, ...] = ()
    interrupted_turn_ids: tuple[str, ...] = ()


def _plain_identifier(value: object) -> bool:
    # Exact type gate precedes any hashing so hostile subclasses cannot run.
    return (
        type(value) is str and 0 < len(value) <= MAX_ID_CHARS
        and value == value.strip()
        and not any(category(char).startswith("C") for char in value)
    )


def _validated_task_ref(task_ref: object) -> str:
    if (
        type(task_ref) is not str
        or not 0 < len(task_ref) <= MAX_TASK_REF_CHARS
        or task_ref != task_ref.strip()
        or any(category(char).startswith("C") for char in task_ref)
    ):
        raise QueueSubmissionGuardError("QUEUE_GUARD_TASK_REF_INVALID")
    return task_ref


def queue_submission_task_key(task_ref: str) -> str:
    """Deterministic task key for governance bootstrap queue submissions.

    Stable across attempts and sessions; distinct task references get
    distinct keys. This key — not a per-attempt UUID — is what makes App
    Server queue correlation usable as duplicate evidence.
    """
    ref = _validated_task_ref(task_ref)
    digest = hashlib.sha256(ref.encode("utf-8")).hexdigest()[:16]
    return TASK_KEY_PREFIX + digest


def _validated_entries(queue_entries: object) -> tuple[QueueEntry, ...]:
    if type(queue_entries) is not tuple or len(queue_entries) > MAX_EVIDENCE_ITEMS:
        raise QueueSubmissionGuardError("QUEUE_GUARD_EVIDENCE_INVALID")
    seen: set[str] = set()
    for item in queue_entries:
        # Exact type gate: a subclass cannot smuggle hostile field access.
        if type(item) is not QueueEntry:
            raise QueueSubmissionGuardError("QUEUE_GUARD_EVIDENCE_INVALID")
        if (
            not _plain_identifier(item.submission_id)
            or not _plain_identifier(item.client_user_message_id)
            or item.submission_id in seen
        ):
            raise QueueSubmissionGuardError("QUEUE_GUARD_EVIDENCE_INVALID")
        seen.add(item.submission_id)
    return queue_entries


def _validated_turns(turns: object) -> tuple[TurnEvidence, ...]:
    if type(turns) is not tuple or len(turns) > MAX_EVIDENCE_ITEMS:
        raise QueueSubmissionGuardError("QUEUE_GUARD_EVIDENCE_INVALID")
    seen: set[str] = set()
    for item in turns:
        if type(item) is not TurnEvidence:
            raise QueueSubmissionGuardError("QUEUE_GUARD_EVIDENCE_INVALID")
        if (
            not _plain_identifier(item.turn_id)
            # Exact type gate precedes set membership (hash-disabled
            # subclasses must fail typed, never escape as TypeError).
            or type(item.status) is not str
            or item.status not in _TURN_STATUSES
            or item.turn_id in seen
        ):
            raise QueueSubmissionGuardError("QUEUE_GUARD_EVIDENCE_INVALID")
        seen.add(item.turn_id)
    return turns


def _validated_cursor(value: object) -> None:
    # None means the last observed page had no next_cursor; any non-None
    # value must be an exact plain identifier or the evidence is invalid.
    if value is not None and not _plain_identifier(value):
        raise QueueSubmissionGuardError("QUEUE_GUARD_EVIDENCE_INVALID")


def evaluate_bootstrap_guard(
    task_ref: str,
    *,
    queue_entries: tuple[QueueEntry, ...],
    turns: tuple[TurnEvidence, ...],
    queue_evidence_complete: bool,
    turn_evidence_complete: bool,
    queue_next_cursor: str | None = None,
    turn_next_cursor: str | None = None,
) -> GuardDecision:
    """Typed one-owner decision before any governance bootstrap side effect.

    PROCEED requires COMPLETE evidence, not merely OBSERVED evidence: an
    OBSERVED queue/turn listing is one bounded page that may have a
    ``next_cursor``. Evidence counts as complete only when the caller
    attests full pagination AND supplies the last observed page's cursor as
    None. A pending cursor or a False attestation fails closed to
    RECONCILIATION_REQUIRED — a partial scan is never an absence proof.
    Priority: a positively observed duplicate submission outranks
    evidence-incompleteness, which outranks interrupted-turn reconciliation;
    interrupted turn IDs are surfaced alongside whenever present.
    """
    _validated_task_ref(task_ref)
    entries = _validated_entries(queue_entries)
    observed_turns = _validated_turns(turns)
    _validated_cursor(queue_next_cursor)
    _validated_cursor(turn_next_cursor)
    if (type(queue_evidence_complete) is not bool
            or type(turn_evidence_complete) is not bool):
        raise QueueSubmissionGuardError("QUEUE_GUARD_EVIDENCE_INVALID")

    interrupted = tuple(
        evidence.turn_id for evidence in observed_turns
        if evidence.status == "interrupted"
    )
    task_key = queue_submission_task_key(task_ref)
    duplicates = tuple(
        evidence.submission_id for evidence in entries
        if evidence.client_user_message_id == task_key
    )
    if duplicates:
        return GuardDecision(
            GuardAction.DUPLICATE_TASK_SUBMISSION_PENDING,
            "QUEUE_GUARD_DUPLICATE_PENDING",
            duplicate_submission_ids=duplicates,
            interrupted_turn_ids=interrupted,
        )
    if (queue_next_cursor is not None or turn_next_cursor is not None
            or not queue_evidence_complete or not turn_evidence_complete):
        return GuardDecision(
            GuardAction.RECONCILIATION_REQUIRED, "QUEUE_GUARD_EVIDENCE_INCOMPLETE",
            interrupted_turn_ids=interrupted,
        )
    if interrupted:
        return GuardDecision(
            GuardAction.RECONCILIATION_REQUIRED,
            "QUEUE_GUARD_TURN_INTERRUPTED",
            interrupted_turn_ids=interrupted,
        )
    return GuardDecision(GuardAction.PROCEED, "QUEUE_GUARD_CLEAR")
