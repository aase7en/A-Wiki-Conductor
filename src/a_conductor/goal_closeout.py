"""WO-P1-166 P0-B3 — GoalCloseout durable completion gate.

A THIN closeout planner/executor composing existing authority only:

- ``TaskState`` + the existing ``REVIEW_PENDING -> COMPLETE`` transition
  (COMPLETE already releases the worker claim in the job-state policy);
- ``SQLiteJobStore`` ordered CHECKPOINT/TRANSITION events with CAS
  ``expected_version`` — the durable job event journal IS the closeout
  journal (no second persistence table);
- ``SQLiteWorkerLeaseStore.release()`` idempotent semantics via an injected
  lease-release port (``already_released`` is reconcile evidence);
- the ContinuityGuard verdict as a fail-closed factual gate (this module
  adds NO I/O to ContinuityGuard);
- LifecycleExecutor/LifecycleRecovery journal discipline as a pattern:
  effect -> durable checkpoint -> only then is a stage complete; an effect
  whose checkpoint is missing is RECOVERY_REQUIRED, never blindly repeated.

Contract order: VERIFY -> DURABLE CHECKPOINT -> blocker/defect
classification -> FOLD (or explicit NOT_REQUIRED) -> LEASE RELEASE ->
COMPLETE. NEXT READY belongs to ZRA-3, not here.

``plan_goal_closeout`` is PURE: no filesystem, Git, GitHub, subprocess,
clock, or database access; deterministic and idempotent on identical facts.
All side effects live in :class:`GoalCloseoutExecutor` over injected ports,
executing ONE next stage per call.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .continuity_guard import ContinuityClassification
from .domain import TaskState

_TEXT_RE = re.compile(r"^[A-Za-z0-9._:/-]{1,256}$")
_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")


class GoalCloseoutError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is invalid")
    return value.strip()


def _optional_sha(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise ValueError(f"{field} is invalid")
    return value.casefold()


class CloseoutDecision(str, Enum):
    VERIFY_CHECKPOINT_REQUIRED = "VERIFY_CHECKPOINT_REQUIRED"
    FOLD_REQUIRED = "FOLD_REQUIRED"
    RELEASE_REQUIRED = "RELEASE_REQUIRED"
    COMPLETE_ALLOWED = "COMPLETE_ALLOWED"
    ALREADY_COMPLETE = "ALREADY_COMPLETE"
    BLOCK = "BLOCK"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    RELOAD_REPLAN = "RELOAD_REPLAN"
    REFUSED = "REFUSED"


class CloseoutStage(str, Enum):
    VERIFY_CHECKPOINT = "VERIFY_CHECKPOINT"
    FOLD = "FOLD"
    RELEASE_LEASE = "RELEASE_LEASE"
    COMPLETE = "COMPLETE"
    DONE = "DONE"


class FoldRequirement(str, Enum):
    REQUIRED = "REQUIRED"
    NOT_REQUIRED = "NOT_REQUIRED"


# conceptual checkpoint family from the P0-B3 contract, with REPLAY-
# SENSITIVE stage authority bound into the identity (GPT1 P1 repair):
# closeout:verify:<task>:<candidate>:<attempt>
# closeout:fold:<task>:<candidate>:<merge-key>:<fold-key>
# closeout:lease-release:<task>:<candidate>:<lease-id>
# closeout:complete:<task>:<candidate>
_STAGE_REF_SEGMENT: dict[CloseoutStage, str] = {
    CloseoutStage.VERIFY_CHECKPOINT: "verify",
    CloseoutStage.FOLD: "fold",
    CloseoutStage.RELEASE_LEASE: "lease-release",
    CloseoutStage.COMPLETE: "complete",
    CloseoutStage.DONE: "done",
}


def closeout_checkpoint_ref(
    stage: CloseoutStage,
    *,
    task_id: str,
    candidate_sha: str,
    attempt_id: str | None = None,
    merge_key: str | None = None,
    fold_key: str | None = None,
    lease_id: str | None = None,
) -> str:
    """Deterministic closeout checkpoint identity binding the stage's OWN
    authority facts — no wall-clock, stable under replay.

    Replay-sensitive stages REQUIRE their authority fields so an old
    attempt / old merge / old lease checkpoint can never satisfy a newer
    closeout transition: VERIFY binds the attempt, FOLD binds the merge +
    fold obligation, RELEASE binds the exact lease id."""
    if not isinstance(stage, CloseoutStage):
        raise ValueError("stage is invalid")
    task = _text(task_id, "task_id")
    sha = _optional_sha(candidate_sha, "candidate_sha")
    if sha is None:
        raise ValueError("candidate_sha is required")
    segment = _STAGE_REF_SEGMENT[stage]
    if stage is CloseoutStage.VERIFY_CHECKPOINT:
        if attempt_id is None:
            raise ValueError("attempt_id is required for verify checkpoints")
        return f"closeout:{segment}:{task}:{sha}:{_text(attempt_id, 'attempt_id')}"
    if stage is CloseoutStage.FOLD:
        if merge_key is None or fold_key is None:
            raise ValueError("merge_key and fold_key are required for fold checkpoints")
        return (
            f"closeout:{segment}:{task}:{sha}:"
            f"{_text(merge_key, 'merge_key')}:{_text(fold_key, 'fold_key')}"
        )
    if stage is CloseoutStage.RELEASE_LEASE:
        if lease_id is None:
            raise ValueError("lease_id is required for lease-release checkpoints")
        return f"closeout:{segment}:{task}:{sha}:{_text(lease_id, 'lease_id')}"
    return f"closeout:{segment}:{task}:{sha}"


# ---------------- immutable facts ----------------

@dataclass(frozen=True, slots=True)
class VerificationEvidence:
    """Identity-bound verification fact — never a bare ``verified=True``."""

    task_id: str
    attempt_id: str
    ok: bool
    checkpoint_ref: str | None
    mutation_version: int | None
    checkpoint_version: int | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_id", _text(self.task_id, "task_id"))
        object.__setattr__(self, "attempt_id", _text(self.attempt_id, "attempt_id"))
        if not isinstance(self.ok, bool):
            raise ValueError("ok must be bool")
        for name in ("mutation_version", "checkpoint_version"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 1):
                raise ValueError(f"{name} is invalid")
        if self.checkpoint_ref is not None:
            object.__setattr__(self, "checkpoint_ref", _text(self.checkpoint_ref, "checkpoint_ref"))


@dataclass(frozen=True, slots=True)
class ReviewEvidence:
    required: bool
    passed: bool | None
    reviewed_sha: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.required, bool):
            raise ValueError("required must be bool")
        if self.passed is not None and not isinstance(self.passed, bool):
            raise ValueError("passed must be bool or None")
        object.__setattr__(self, "reviewed_sha", _optional_sha(self.reviewed_sha, "reviewed_sha"))


@dataclass(frozen=True, slots=True)
class MergeEvidence:
    required: bool
    merged: bool | None
    merge_commit: str | None
    accepted_candidate_sha: str | None
    accepted_candidate_ancestor: bool | None
    post_main_required: bool
    post_main_run_id: str | None
    post_main_success: bool | None
    post_main_merge_commit: str | None

    def __post_init__(self) -> None:
        for name in ("required", "post_main_required"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be bool")
        for name in ("merged", "accepted_candidate_ancestor", "post_main_success"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, bool):
                raise ValueError(f"{name} is invalid")
        for name in ("merge_commit", "post_main_merge_commit"):
            value = getattr(self, name)
            if value is not None and not _TEXT_RE.fullmatch(value):
                raise ValueError(f"{name} is invalid")
        object.__setattr__(
            self, "accepted_candidate_sha",
            _optional_sha(self.accepted_candidate_sha, "accepted_candidate_sha"),
        )
        if self.post_main_run_id is not None:
            object.__setattr__(
                self, "post_main_run_id", _text(self.post_main_run_id, "post_main_run_id")
            )


@dataclass(frozen=True, slots=True)
class FoldEvidence:
    requirement: FoldRequirement
    not_required_reason: str | None = None
    completed: bool | None = None
    bound_task_id: str | None = None
    bound_merge_commit: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.requirement, FoldRequirement):
            raise ValueError("requirement is invalid")
        if self.completed is not None and not isinstance(self.completed, bool):
            raise ValueError("completed is invalid")
        for name in ("not_required_reason", "bound_task_id", "bound_merge_commit"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{name} is invalid")


@dataclass(frozen=True, slots=True)
class LeaseEvidence:
    lease_id: str | None
    state: str | None  # ACTIVE / RELEASED / STALE / QUARANTINED / UNKNOWN / None
    owner_ok: bool

    def __post_init__(self) -> None:
        if self.lease_id is not None:
            object.__setattr__(self, "lease_id", _text(self.lease_id, "lease_id"))
        if self.state is not None:
            state = _text(self.state, "state").upper()
            if state not in {"ACTIVE", "RELEASED", "STALE", "QUARANTINED", "UNKNOWN"}:
                raise ValueError("state is invalid")
            object.__setattr__(self, "state", state)
        if not isinstance(self.owner_ok, bool):
            raise ValueError("owner_ok must be bool")


@dataclass(frozen=True, slots=True)
class OwnershipEvidence:
    known: bool
    conflicting: bool
    transition_in_progress: bool

    def __post_init__(self) -> None:
        for name in ("known", "conflicting", "transition_in_progress"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be bool")


@dataclass(frozen=True, slots=True)
class GoalCloseoutFacts:
    job_id: str
    task_id: str
    attempt_id: str
    state: TaskState
    version: int
    verification: VerificationEvidence
    blocking_findings: tuple[str, ...]
    continuity: ContinuityClassification
    current_candidate_sha: str | None
    review: ReviewEvidence
    merge: MergeEvidence
    fold: FoldEvidence
    lease: LeaseEvidence
    ownership: OwnershipEvidence
    completed_closeout_refs: frozenset[str]

    def __post_init__(self) -> None:
        for name in ("job_id", "task_id", "attempt_id"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if not isinstance(self.state, TaskState):
            raise ValueError("state must be a TaskState")
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise ValueError("version is invalid")
        object.__setattr__(
            self, "current_candidate_sha",
            _optional_sha(self.current_candidate_sha, "current_candidate_sha"),
        )
        if not isinstance(self.verification, VerificationEvidence):
            raise ValueError("verification must be VerificationEvidence")
        findings = tuple(_text(f, "finding") for f in self.blocking_findings)
        object.__setattr__(self, "blocking_findings", findings)
        if not isinstance(self.continuity, ContinuityClassification):
            raise ValueError("continuity must be a ContinuityClassification")
        for name, kind in (
            ("review", ReviewEvidence), ("merge", MergeEvidence),
            ("fold", FoldEvidence), ("lease", LeaseEvidence),
            ("ownership", OwnershipEvidence),
        ):
            if not isinstance(getattr(self, name), kind):
                raise ValueError(f"{name} must be {kind.__name__}")
        refs = frozenset(_text(r, "ref") for r in self.completed_closeout_refs)
        object.__setattr__(self, "completed_closeout_refs", refs)


@dataclass(frozen=True, slots=True)
class GoalCloseoutFinding:
    code: str
    detail: str = ""

    def __post_init__(self) -> None:
        if not _TEXT_RE.fullmatch(self.code):
            raise ValueError("code is invalid")
        detail = self.detail if isinstance(self.detail, str) else ""
        object.__setattr__(self, "detail", detail[:256])


@dataclass(frozen=True, slots=True)
class GoalCloseoutPlan:
    decision: CloseoutDecision
    stage: CloseoutStage
    findings: tuple[GoalCloseoutFinding, ...]
    checkpoint_ref: str | None


def _verify_ref(f: GoalCloseoutFacts) -> str | None:
    if f.current_candidate_sha is None:
        return None
    return closeout_checkpoint_ref(
        CloseoutStage.VERIFY_CHECKPOINT, task_id=f.task_id,
        candidate_sha=f.current_candidate_sha, attempt_id=f.attempt_id,
    )


def _fold_ref(f: GoalCloseoutFacts) -> str | None:
    if f.current_candidate_sha is None:
        return None
    merge_key = f.merge.merge_commit if f.merge.required else "nomerge"
    fold_key = "required"
    return closeout_checkpoint_ref(
        CloseoutStage.FOLD, task_id=f.task_id, candidate_sha=f.current_candidate_sha,
        merge_key=merge_key, fold_key=fold_key,
    )


def _release_ref(f: GoalCloseoutFacts) -> str | None:
    if f.current_candidate_sha is None or f.lease.lease_id is None:
        return None
    return closeout_checkpoint_ref(
        CloseoutStage.RELEASE_LEASE, task_id=f.task_id,
        candidate_sha=f.current_candidate_sha, lease_id=f.lease.lease_id,
    )


def _complete_ref(f: GoalCloseoutFacts) -> str | None:
    if f.current_candidate_sha is None:
        return None
    return closeout_checkpoint_ref(
        CloseoutStage.COMPLETE, task_id=f.task_id, candidate_sha=f.current_candidate_sha,
    )


def plan_goal_closeout(facts: GoalCloseoutFacts) -> GoalCloseoutPlan:
    """PURE deterministic closeout decision over immutable facts."""
    if not isinstance(facts, GoalCloseoutFacts):
        raise ValueError("facts must be GoalCloseoutFacts")

    # terminal states first: idempotent no-op / refusal
    if facts.state is TaskState.COMPLETE:
        return GoalCloseoutPlan(
            CloseoutDecision.ALREADY_COMPLETE, CloseoutStage.DONE, (), None
        )
    if facts.state in (TaskState.FAILED, TaskState.CANCELLED):
        return GoalCloseoutPlan(
            CloseoutDecision.REFUSED, CloseoutStage.DONE,
            (GoalCloseoutFinding("TERMINAL_STATE", facts.state.value),), None
        )

    # verification binding (identity-bound facts, never a bare bool)
    v = facts.verification
    if not v.ok:
        return GoalCloseoutPlan(
            CloseoutDecision.BLOCK, CloseoutStage.VERIFY_CHECKPOINT,
            (GoalCloseoutFinding("VERIFY_EVIDENCE_MISSING", ""),), None,
        )
    if v.task_id != facts.task_id or v.attempt_id != facts.attempt_id:
        return GoalCloseoutPlan(
            CloseoutDecision.BLOCK, CloseoutStage.VERIFY_CHECKPOINT,
            (GoalCloseoutFinding("VERIFY_IDENTITY_MISMATCH", ""),), None,
        )
    if v.checkpoint_version is None:
        # effect observed but not durably checkpointed: record the checkpoint
        return GoalCloseoutPlan(
            CloseoutDecision.VERIFY_CHECKPOINT_REQUIRED, CloseoutStage.VERIFY_CHECKPOINT,
            (), _verify_ref(facts),
        )
    if v.mutation_version is not None and v.mutation_version > v.checkpoint_version:
        return GoalCloseoutPlan(
            CloseoutDecision.RECOVERY_REQUIRED, CloseoutStage.VERIFY_CHECKPOINT,
            (GoalCloseoutFinding("MUTATION_AHEAD_OF_JOURNAL", ""),), None,
        )
    verify_ref = _verify_ref(facts)
    if verify_ref is not None and verify_ref not in facts.completed_closeout_refs:
        return GoalCloseoutPlan(
            CloseoutDecision.VERIFY_CHECKPOINT_REQUIRED, CloseoutStage.VERIFY_CHECKPOINT,
            (), verify_ref,
        )

    # blocker/defect classification
    if facts.blocking_findings:
        return GoalCloseoutPlan(
            CloseoutDecision.BLOCK, CloseoutStage.DONE,
            (GoalCloseoutFinding("BLOCKING_FINDINGS", "; ".join(facts.blocking_findings)[:200]),), None,
        )

    # integration/closeout ownership concurrency (durable facts win)
    o = facts.ownership
    if not o.known:
        return GoalCloseoutPlan(
            CloseoutDecision.BLOCK, CloseoutStage.DONE,
            (GoalCloseoutFinding("OWNERSHIP_UNKNOWN", ""),), None,
        )
    if o.conflicting:
        return GoalCloseoutPlan(
            CloseoutDecision.BLOCK, CloseoutStage.DONE,
            (GoalCloseoutFinding("OWNERSHIP_CONFLICT", ""),), None,
        )
    if o.transition_in_progress:
        return GoalCloseoutPlan(
            CloseoutDecision.BLOCK, CloseoutStage.DONE,
            (GoalCloseoutFinding("OWNERSHIP_TRANSITION_IN_PROGRESS", ""),), None,
        )

    # continuity gate (fail-closed; MERGED_NOT_FOLDED routes to fold below)
    c = facts.continuity
    if c is ContinuityClassification.UNKNOWN:
        return GoalCloseoutPlan(
            CloseoutDecision.RECOVERY_REQUIRED, CloseoutStage.DONE,
            (GoalCloseoutFinding("CONTINUITY_UNKNOWN", ""),), None,
        )
    if c is ContinuityClassification.MERGED_NOT_FOLDED:
        pass  # handled by the fold obligation below (forced REQUIRED)
    elif c is not ContinuityClassification.FRESH:
        return GoalCloseoutPlan(
            CloseoutDecision.BLOCK, CloseoutStage.DONE,
            (GoalCloseoutFinding(f"CONTINUITY_{c.value}", ""),), None,
        )

    # review / exact-SHA binding (no stale-review acceptance)
    if facts.current_candidate_sha is None:
        return GoalCloseoutPlan(
            CloseoutDecision.BLOCK, CloseoutStage.DONE,
            (GoalCloseoutFinding("CANDIDATE_SHA_UNKNOWN", ""),), None,
        )
    r = facts.review
    if r.required:
        if r.passed is None:
            return GoalCloseoutPlan(
                CloseoutDecision.BLOCK, CloseoutStage.DONE,
                (GoalCloseoutFinding("REVIEW_NOT_PERFORMED", ""),), None,
            )
        if r.passed is False:
            return GoalCloseoutPlan(
                CloseoutDecision.BLOCK, CloseoutStage.DONE,
                (GoalCloseoutFinding("REVIEW_CHANGES_REQUIRED", ""),), None,
            )
        if r.reviewed_sha is None or r.reviewed_sha != facts.current_candidate_sha:
            return GoalCloseoutPlan(
                CloseoutDecision.BLOCK, CloseoutStage.DONE,
                (GoalCloseoutFinding("STALE_REVIEW_SHA", ""),), None,
            )

    # merge / post-main exact identities
    m = facts.merge
    if m.required:
        if m.merged is not True or m.merge_commit is None:
            return GoalCloseoutPlan(
                CloseoutDecision.BLOCK, CloseoutStage.DONE,
                (GoalCloseoutFinding("MERGE_NOT_MERGED", ""),), None,
            )
        if m.accepted_candidate_ancestor is not True:
            return GoalCloseoutPlan(
                CloseoutDecision.BLOCK, CloseoutStage.DONE,
                (GoalCloseoutFinding("MERGE_ANCESTRY_MISMATCH", ""),), None,
            )
        if m.accepted_candidate_sha is None or m.accepted_candidate_sha != facts.current_candidate_sha:
            return GoalCloseoutPlan(
                CloseoutDecision.BLOCK, CloseoutStage.DONE,
                (GoalCloseoutFinding("MERGE_CANDIDATE_MISMATCH", ""),), None,
            )
        if m.post_main_required:
            if m.post_main_run_id is None:
                return GoalCloseoutPlan(
                    CloseoutDecision.BLOCK, CloseoutStage.DONE,
                    (GoalCloseoutFinding("POST_MAIN_MISSING", ""),), None,
                )
            if m.post_main_success is None:
                return GoalCloseoutPlan(
                    CloseoutDecision.BLOCK, CloseoutStage.DONE,
                    (GoalCloseoutFinding("POST_MAIN_PENDING", ""),), None,
                )
            if m.post_main_success is False:
                return GoalCloseoutPlan(
                    CloseoutDecision.BLOCK, CloseoutStage.DONE,
                    (GoalCloseoutFinding("POST_MAIN_FAILED", ""),), None,
                )
            if m.post_main_merge_commit != m.merge_commit:
                return GoalCloseoutPlan(
                    CloseoutDecision.BLOCK, CloseoutStage.DONE,
                    (GoalCloseoutFinding("POST_MAIN_IDENTITY_MISMATCH", ""),), None,
                )

    # fold obligation (explicit policy; MERGED_NOT_FOLDED forces REQUIRED)
    required = facts.fold.requirement is FoldRequirement.REQUIRED or (
        c is ContinuityClassification.MERGED_NOT_FOLDED
    )
    if not required:
        if not (facts.fold.not_required_reason or "").strip():
            return GoalCloseoutPlan(
                CloseoutDecision.BLOCK, CloseoutStage.DONE,
                (GoalCloseoutFinding("FOLD_POLICY_REQUIRED", ""),), None,
            )
    else:
        fold_ref = _fold_ref(facts)
        fold_checkpoint_present = fold_ref is not None and fold_ref in facts.completed_closeout_refs
        # CURRENT factual fold binding is validated BEFORE any checkpoint can
        # satisfy the stage (P1-A): a journal ref never overrides a
        # contradictory current task/merge identity.
        fold_identity_ok = facts.fold.bound_task_id == facts.task_id and (
            not m.required or facts.fold.bound_merge_commit == m.merge_commit
        )
        if fold_checkpoint_present:
            if facts.fold.completed is not True:
                # journal claims the fold while current facts say incomplete/
                # unknown -> typed fail-closed conflict.
                return GoalCloseoutPlan(
                    CloseoutDecision.RECOVERY_REQUIRED, CloseoutStage.FOLD,
                    (GoalCloseoutFinding("FOLD_CHECKPOINT_CONTRADICTION", ""),), fold_ref,
                )
            if not fold_identity_ok:
                return GoalCloseoutPlan(
                    CloseoutDecision.RECOVERY_REQUIRED, CloseoutStage.FOLD,
                    (GoalCloseoutFinding("FOLD_IDENTITY_CONTRADICTION", ""),), fold_ref,
                )
            # matching checkpoint + agreeing current facts: satisfied
        elif facts.fold.completed is True:
            if not fold_identity_ok:
                return GoalCloseoutPlan(
                    CloseoutDecision.BLOCK, CloseoutStage.DONE,
                    (GoalCloseoutFinding("FOLD_IDENTITY_MISMATCH", ""),), None,
                )
            # effect claims complete but no durable checkpoint: never repeat blindly
            return GoalCloseoutPlan(
                CloseoutDecision.RECOVERY_REQUIRED, CloseoutStage.FOLD,
                (GoalCloseoutFinding("FOLD_CHECKPOINT_MISSING", ""),), fold_ref,
            )
        else:
            findings: tuple[GoalCloseoutFinding, ...] = ()
            if c is ContinuityClassification.MERGED_NOT_FOLDED:
                findings = (GoalCloseoutFinding("MERGED_NOT_FOLDED", ""),)
            return GoalCloseoutPlan(
                CloseoutDecision.FOLD_REQUIRED, CloseoutStage.FOLD, findings, fold_ref,
            )

    # mutation-lease release (idempotent; RELEASED satisfies)
    lease = facts.lease
    if lease.lease_id is not None:
        if not lease.owner_ok:
            return GoalCloseoutPlan(
                CloseoutDecision.BLOCK, CloseoutStage.DONE,
                (GoalCloseoutFinding("LEASE_OWNER_MISMATCH", lease.lease_id),), None,
            )
        if lease.state in ("STALE", "UNKNOWN"):
            return GoalCloseoutPlan(
                CloseoutDecision.RECOVERY_REQUIRED, CloseoutStage.RELEASE_LEASE,
                (GoalCloseoutFinding("LEASE_STATE_RECOVERY", lease.lease_id),), None,
            )
        if lease.state == "QUARANTINED":
            return GoalCloseoutPlan(
                CloseoutDecision.RECOVERY_REQUIRED, CloseoutStage.RELEASE_LEASE,
                (GoalCloseoutFinding("LEASE_QUARANTINED", lease.lease_id),), None,
            )
        if lease.state == "ACTIVE":
            release_ref = _release_ref(facts)
            if release_ref is not None and release_ref in facts.completed_closeout_refs:
                # journal claims this EXACT lease was released while current
                # authority says ACTIVE: contradiction, never silent COMPLETE
                return GoalCloseoutPlan(
                    CloseoutDecision.RECOVERY_REQUIRED, CloseoutStage.RELEASE_LEASE,
                    (GoalCloseoutFinding("LEASE_RELEASE_CONTRADICTION", lease.lease_id),), release_ref,
                )
            return GoalCloseoutPlan(
                CloseoutDecision.RELEASE_REQUIRED, CloseoutStage.RELEASE_LEASE,
                (), release_ref,
            )
        if lease.state == "RELEASED":
            # P1-B: a RELEASED lease satisfies closeout ONLY when durable
            # evidence binds the exact CURRENT lease-release transition.
            # Missing or old-lease checkpoints stay fail-closed (crash after
            # release before checkpoint is reconciliation, not completion).
            release_ref = _release_ref(facts)
            if release_ref is None or release_ref not in facts.completed_closeout_refs:
                return GoalCloseoutPlan(
                    CloseoutDecision.RECOVERY_REQUIRED, CloseoutStage.RELEASE_LEASE,
                    (GoalCloseoutFinding("LEASE_RELEASE_CHECKPOINT_MISSING", lease.lease_id),), release_ref,
                )

    # every obligation satisfied: only REVIEW_PENDING may complete
    if facts.state is not TaskState.REVIEW_PENDING:
        return GoalCloseoutPlan(
            CloseoutDecision.BLOCK, CloseoutStage.DONE,
            (GoalCloseoutFinding("INVALID_CLOSEOUT_STATE", facts.state.value),), None,
        )
    return GoalCloseoutPlan(
        CloseoutDecision.COMPLETE_ALLOWED, CloseoutStage.COMPLETE,
        (), _complete_ref(facts),
    )


# ---------------- thin executor over injected ports ----------------

@dataclass(frozen=True, slots=True)
class LeaseReleaseOutcome:
    released: bool
    already_released: bool


@dataclass(frozen=True, slots=True)
class FoldOutcome:
    completed: bool | None  # None = UNKNOWN; never treated as success


@dataclass(frozen=True, slots=True)
class FoldRequest:
    task_id: str
    candidate_sha: str
    checkpoint_ref: str


class LeaseReleasePort(Protocol):
    def release(self, lease_id: str) -> LeaseReleaseOutcome: ...


class CloseoutFoldPort(Protocol):
    def fold(self, request: FoldRequest) -> FoldOutcome: ...


class CloseoutJobStorePort(Protocol):
    def checkpoint(self, job_id: str, *, checkpoint_ref: str, expected_version: int,
                   evidence_ref: str | None = None) -> object: ...

    def transition(self, job_id: str, target_state: TaskState, *, expected_version: int,
                   **kwargs) -> object: ...


@dataclass(frozen=True, slots=True)
class GoalCloseoutExecutionResult:
    decision: CloseoutDecision
    stage: CloseoutStage
    detail: str = ""


class GoalCloseoutExecutor:
    """Executes ONE next closeout stage per call over injected ports.

    facts -> plan -> one durable side effect -> checkpoint -> return.
    No internal loop. All job mutations keep the existing CAS
    ``expected_version`` discipline; a version conflict is typed
    RELOAD_REPLAN (caller re-reads durable state and replans) — never a
    blind retry. GoalCloseout holds NO state of its own."""

    def __init__(
        self,
        *,
        job_store: CloseoutJobStorePort,
        lease_release_port: LeaseReleasePort,
        fold_port: CloseoutFoldPort,
    ) -> None:
        for name, port, methods in (
            ("job_store", job_store, ("checkpoint", "transition")),
            ("lease_release_port", lease_release_port, ("release",)),
            ("fold_port", fold_port, ("fold",)),
        ):
            for method in methods:
                if not callable(getattr(port, method, None)):
                    raise ValueError(f"{name} must provide {method}")
        self._store = job_store
        self._leases = lease_release_port
        self._folds = fold_port

    def execute_next(self, facts: GoalCloseoutFacts) -> GoalCloseoutExecutionResult:
        from .job_store import JobStoreError

        plan = plan_goal_closeout(facts)

        if plan.decision is CloseoutDecision.ALREADY_COMPLETE:
            return GoalCloseoutExecutionResult(plan.decision, CloseoutStage.DONE)
        if plan.decision in (
            CloseoutDecision.BLOCK, CloseoutDecision.REFUSED,
            CloseoutDecision.RECOVERY_REQUIRED, CloseoutDecision.RELOAD_REPLAN,
        ):
            return GoalCloseoutExecutionResult(plan.decision, plan.stage,
                                               plan.findings[0].code if plan.findings else "")

        try:
            if plan.decision is CloseoutDecision.VERIFY_CHECKPOINT_REQUIRED:
                self._store.checkpoint(
                    facts.job_id, checkpoint_ref=plan.checkpoint_ref,
                    expected_version=facts.version,
                )
                return GoalCloseoutExecutionResult(plan.decision, CloseoutStage.VERIFY_CHECKPOINT)

            if plan.decision is CloseoutDecision.FOLD_REQUIRED:
                outcome = self._folds.fold(FoldRequest(
                    task_id=facts.task_id,
                    candidate_sha=facts.current_candidate_sha or "",
                    checkpoint_ref=plan.checkpoint_ref or "",
                ))
                if outcome.completed is not True:
                    return GoalCloseoutExecutionResult(
                        CloseoutDecision.RECOVERY_REQUIRED, CloseoutStage.FOLD,
                        "FOLD_OUTCOME_UNKNOWN" if outcome.completed is None else "FOLD_NOT_COMPLETED",
                    )
                try:
                    self._store.checkpoint(
                        facts.job_id, checkpoint_ref=plan.checkpoint_ref,
                        expected_version=facts.version,
                    )
                except JobStoreError:
                    # effect landed but the durable checkpoint failed: recovery
                    return GoalCloseoutExecutionResult(
                        CloseoutDecision.RECOVERY_REQUIRED, CloseoutStage.FOLD,
                        "CHECKPOINT_AFTER_EFFECT_FAILED",
                    )
                return GoalCloseoutExecutionResult(plan.decision, CloseoutStage.FOLD)

            if plan.decision is CloseoutDecision.RELEASE_REQUIRED:
                outcome = self._leases.release(facts.lease.lease_id or "")
                # The port result is evidence, not decoration: only a
                # confirmed release (True, False) or confirmed idempotent
                # release (False, True) may be checkpointed. The canonical
                # SQLiteWorkerLeaseStore.release() never emits anything else
                # without raising; anything else is fail-closed recovery.
                if not isinstance(outcome.released, bool) or not isinstance(outcome.already_released, bool):
                    return GoalCloseoutExecutionResult(
                        CloseoutDecision.RECOVERY_REQUIRED, CloseoutStage.RELEASE_LEASE,
                        "LEASE_RELEASE_OUTCOME_INVALID",
                    )
                if outcome.released and outcome.already_released:
                    return GoalCloseoutExecutionResult(
                        CloseoutDecision.RECOVERY_REQUIRED, CloseoutStage.RELEASE_LEASE,
                        "LEASE_RELEASE_OUTCOME_CONTRADICTORY",
                    )
                if not outcome.released and not outcome.already_released:
                    return GoalCloseoutExecutionResult(
                        CloseoutDecision.RECOVERY_REQUIRED, CloseoutStage.RELEASE_LEASE,
                        "LEASE_RELEASE_NOT_CONFIRMED",
                    )
                try:
                    self._store.checkpoint(
                        facts.job_id, checkpoint_ref=plan.checkpoint_ref,
                        expected_version=facts.version,
                    )
                except JobStoreError:
                    # release may have landed (already_released reconciles later)
                    return GoalCloseoutExecutionResult(
                        CloseoutDecision.RECOVERY_REQUIRED, CloseoutStage.RELEASE_LEASE,
                        "CHECKPOINT_AFTER_EFFECT_FAILED",
                    )
                detail = "ALREADY_RELEASED" if outcome.already_released else ""
                return GoalCloseoutExecutionResult(plan.decision, CloseoutStage.RELEASE_LEASE, detail)

            if plan.decision is CloseoutDecision.COMPLETE_ALLOWED:
                self._store.transition(
                    facts.job_id, TaskState.COMPLETE, expected_version=facts.version,
                    evidence_ref=plan.checkpoint_ref,
                )
                return GoalCloseoutExecutionResult(plan.decision, CloseoutStage.COMPLETE)
        except JobStoreError as exc:
            if str(exc) == "JOB_VERSION_CONFLICT":
                return GoalCloseoutExecutionResult(
                    CloseoutDecision.RELOAD_REPLAN, plan.stage, "JOB_VERSION_CONFLICT"
                )
            raise
        raise GoalCloseoutError("PLAN_STAGE_UNHANDLED")
