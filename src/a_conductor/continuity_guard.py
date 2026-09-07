"""P0-B1 pure continuity classification for A-Conductor (WO-P1-166).

This module is a deterministic, side-effect-free classifier over one immutable
factual snapshot of continuity evidence. It performs no Git access, network
calls, subprocess execution, filesystem writes, provider dispatch, lease
acquisition/release, scheduling, or projection writes, and it holds no state.
Durable factual authority (Git heads, job state, lease records) always outranks
human-readable projections such as CURRENT-WORK.md, handoff.md, or COLLAB.md.

Only a fully proven-compatible snapshot classifies as FRESH. Any non-FRESH
finding denies mutation; UNKNOWN always fails closed and never degrades to an
optimistic default. The classifier reuses the existing write-conflict seam
(``write_sets_overlap``) and the canonical worktree identity seam
(``windows_worktree_key``); it creates no second scheduler, store, claim, or
lease authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from .domain import TaskState
from .graph.analyze import write_sets_overlap
from .registry import windows_worktree_key

_HEAD_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")
_DIRTY_STATES = frozenset({"CLEAN", "DIRTY", "UNKNOWN"})
_LEASE_STATES = frozenset({"ACTIVE", "RELEASED", "QUARANTINED", "STALE", "UNKNOWN"})
_TERMINAL_JOB_STATES = frozenset(
    {TaskState.COMPLETE, TaskState.FAILED, TaskState.CANCELLED}
)


class ContinuityClassification(str, Enum):
    FRESH = "FRESH"
    STALE_LOCAL_CHECKOUT = "STALE_LOCAL_CHECKOUT"
    HEAD_DRIFT = "HEAD_DRIFT"
    WORKTREE_DIRTY_OR_UNKNOWN = "WORKTREE_DIRTY_OR_UNKNOWN"
    CLAIM_CONFLICT = "CLAIM_CONFLICT"
    SSOT_DRIFT = "SSOT_DRIFT"
    MERGED_NOT_FOLDED = "MERGED_NOT_FOLDED"
    RECONCILE_REQUIRED = "RECONCILE_REQUIRED"
    UNKNOWN = "UNKNOWN"


class ReconciliationAction(str, Enum):
    RECOVER_MISSING_FACTS = "RECOVER_MISSING_FACTS"
    RESOLVE_CLAIM_CONFLICT = "RESOLVE_CLAIM_CONFLICT"
    REALIGN_TO_EXPECTED_HEAD = "REALIGN_TO_EXPECTED_HEAD"
    UPDATE_FROM_AUTHORITATIVE_REMOTE = "UPDATE_FROM_AUTHORITATIVE_REMOTE"
    RECONCILE_WORKTREE_STATE = "RECONCILE_WORKTREE_STATE"
    COMPLETE_MERGE_FOLD = "COMPLETE_MERGE_FOLD"
    RUN_DETERMINISTIC_RECONCILIATION = "RUN_DETERMINISTIC_RECONCILIATION"
    REFRESH_PROJECTION = "REFRESH_PROJECTION"


REASON_CODES = frozenset(
    {
        "EXPECTED_HEAD_UNKNOWN",
        "LOCAL_HEAD_UNKNOWN",
        "REMOTE_HEAD_UNKNOWN",
        "JOB_STATE_UNKNOWN",
        "LEASE_STATE_UNKNOWN",
        "LOCAL_HEAD_NOT_EXPECTED",
        "LOCAL_HEAD_NOT_REMOTE",
        "WORKTREE_DIRTY",
        "DIRTY_STATE_UNKNOWN",
        "OWNERSHIP_UNKNOWN",
        "LEASE_OWNER_CONFLICT",
        "MUTABLE_SCOPE_OVERLAP",
        "JOB_TERMINAL",
        "LEASE_RECONCILIATION_REQUIRED",
        "RECOVERY_TRANSITION_REQUIRED",
        "FOLD_NOT_COMPLETE",
        "FOLD_STATUS_UNKNOWN",
        "RELEASE_NOT_COMPLETE",
        "RELEASE_STATUS_UNKNOWN",
        "PROJECTION_HEAD_CONTRADICTS_FACTS",
        "PROJECTION_BRANCH_CONTRADICTS_FACTS",
        "PROJECTION_CLAIMS_CONTRADICTS_FACTS",
    }
)

# Deterministic severity precedence for primary-classification selection and
# finding ordering. UNKNOWN first: missing facts invalidate every other check.
_PRECEDENCE: tuple[ContinuityClassification, ...] = (
    ContinuityClassification.UNKNOWN,
    ContinuityClassification.CLAIM_CONFLICT,
    ContinuityClassification.HEAD_DRIFT,
    ContinuityClassification.STALE_LOCAL_CHECKOUT,
    ContinuityClassification.WORKTREE_DIRTY_OR_UNKNOWN,
    ContinuityClassification.MERGED_NOT_FOLDED,
    ContinuityClassification.RECONCILE_REQUIRED,
    ContinuityClassification.SSOT_DRIFT,
)
_PRECEDENCE_INDEX = {
    kind: index for index, kind in enumerate(_PRECEDENCE)
}
_ACTION_BY_KIND: dict[ContinuityClassification, ReconciliationAction] = {
    ContinuityClassification.UNKNOWN: ReconciliationAction.RECOVER_MISSING_FACTS,
    ContinuityClassification.CLAIM_CONFLICT: ReconciliationAction.RESOLVE_CLAIM_CONFLICT,
    ContinuityClassification.HEAD_DRIFT: ReconciliationAction.REALIGN_TO_EXPECTED_HEAD,
    ContinuityClassification.STALE_LOCAL_CHECKOUT: (
        ReconciliationAction.UPDATE_FROM_AUTHORITATIVE_REMOTE
    ),
    ContinuityClassification.WORKTREE_DIRTY_OR_UNKNOWN: (
        ReconciliationAction.RECONCILE_WORKTREE_STATE
    ),
    ContinuityClassification.MERGED_NOT_FOLDED: ReconciliationAction.COMPLETE_MERGE_FOLD,
    ContinuityClassification.RECONCILE_REQUIRED: (
        ReconciliationAction.RUN_DETERMINISTIC_RECONCILIATION
    ),
    ContinuityClassification.SSOT_DRIFT: ReconciliationAction.REFRESH_PROJECTION,
}


def _text(value: str, field_name: str, *, max_length: int = 512) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if "\x00" in value or "\r" in value or "\n" in value:
        raise ValueError(f"{field_name} is invalid")
    cleaned = value.strip()
    if len(cleaned) > max_length:
        raise ValueError(f"{field_name} is invalid")
    return cleaned


def _head(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    cleaned = _text(value, field_name, max_length=64)
    if not _HEAD_RE.fullmatch(cleaned):
        raise ValueError(f"{field_name} must be a git object id")
    return cleaned.casefold()


def _optional_bool(value: bool | None, field_name: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be bool or None")
    return value


def _scope(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{field_name} must be a sequence")
    result = tuple(_text(value, field_name, max_length=512) for value in values)
    if len(set(result)) != len(result):
        raise ValueError(f"{field_name} must not contain duplicates")
    return result


@dataclass(frozen=True, slots=True)
class ContinuityFinding:
    kind: ContinuityClassification
    reason_code: str
    detail: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ContinuityClassification):
            raise ValueError("kind must be a ContinuityClassification")
        if self.reason_code not in REASON_CODES:
            raise ValueError("reason_code is invalid")
        detail = self.detail if isinstance(self.detail, str) else ""
        if len(detail) > 512 or "\x00" in detail or "\r" in detail or "\n" in detail:
            raise ValueError("detail is invalid")
        object.__setattr__(self, "detail", detail)


@dataclass(frozen=True, slots=True)
class LeaseFact:
    """One observed worker-capacity lease as durable fact input."""

    lease_id: str
    session_id: str
    task_id: str
    worktree_key: str
    mutable_scope: tuple[str, ...] = ()
    state: str = "ACTIVE"

    def __post_init__(self) -> None:
        object.__setattr__(self, "lease_id", _text(self.lease_id, "lease_id", max_length=128))
        object.__setattr__(self, "session_id", _text(self.session_id, "session_id", max_length=128))
        object.__setattr__(self, "task_id", _text(self.task_id, "task_id", max_length=256))
        object.__setattr__(self, "worktree_key", _text(self.worktree_key, "worktree_key", max_length=512))
        object.__setattr__(self, "mutable_scope", _scope(self.mutable_scope, "mutable_scope"))
        state = _text(self.state, "state", max_length=32).upper()
        if state not in _LEASE_STATES:
            raise ValueError("state is invalid")
        object.__setattr__(self, "state", state)


@dataclass(frozen=True, slots=True)
class JobFact:
    """The durable job bound to this lane, if one exists.

    ``state`` is None when the bound job exists but its state could not be
    observed; that is missing critical evidence, not a job-less lane.
    """

    job_id: str
    state: TaskState | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "job_id", _text(self.job_id, "job_id", max_length=128))
        if self.state is not None and not isinstance(self.state, TaskState):
            raise ValueError("state must be a TaskState or None")


@dataclass(frozen=True, slots=True)
class MergeFoldFact:
    """An accepted merge whose fold/release obligations apply to this lane."""

    merge_commit: str
    fold_complete: bool | None = None
    release_complete: bool | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "merge_commit", _head(self.merge_commit, "merge_commit") or "")
        object.__setattr__(self, "fold_complete", _optional_bool(self.fold_complete, "fold_complete"))
        object.__setattr__(
            self, "release_complete", _optional_bool(self.release_complete, "release_complete")
        )


@dataclass(frozen=True, slots=True)
class ProjectionClaim:
    """What one human-readable projection asserts; compared against facts.

    None means the projection does not assert that fact. An asserted value is
    never authority; it can only agree with or contradict durable facts.
    """

    source: str
    asserted_head: str | None = None
    asserted_branch: str | None = None
    asserted_active_lease_ids: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _text(self.source, "source", max_length=128))
        object.__setattr__(self, "asserted_head", _head(self.asserted_head, "asserted_head"))
        if self.asserted_branch is not None:
            object.__setattr__(
                self, "asserted_branch", _text(self.asserted_branch, "asserted_branch", max_length=256)
            )
        if self.asserted_active_lease_ids is not None:
            object.__setattr__(
                self,
                "asserted_active_lease_ids",
                tuple(
                    _text(item, "asserted_active_lease_id", max_length=128)
                    for item in self.asserted_active_lease_ids
                ),
            )


@dataclass(frozen=True, slots=True)
class ContinuitySnapshot:
    """Immutable factual projection consumed by :func:`classify_continuity`."""

    worktree: str
    branch: str
    session_id: str
    task_id: str
    expected_head: str | None
    local_head: str | None
    remote_head: str | None
    dirty_state: str | None
    ownership_known: bool
    mutable_scope: tuple[str, ...] = ()
    leases: tuple[LeaseFact, ...] = ()
    job: JobFact | None = None
    merge_fold: MergeFoldFact | None = None
    projections: tuple[ProjectionClaim, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "worktree", _text(self.worktree, "worktree", max_length=1024))
        object.__setattr__(self, "branch", _text(self.branch, "branch", max_length=256))
        object.__setattr__(self, "session_id", _text(self.session_id, "session_id", max_length=128))
        object.__setattr__(self, "task_id", _text(self.task_id, "task_id", max_length=256))
        object.__setattr__(self, "expected_head", _head(self.expected_head, "expected_head"))
        object.__setattr__(self, "local_head", _head(self.local_head, "local_head"))
        object.__setattr__(self, "remote_head", _head(self.remote_head, "remote_head"))
        if self.dirty_state is not None:
            dirty = _text(self.dirty_state, "dirty_state", max_length=16).upper()
            if dirty not in _DIRTY_STATES:
                raise ValueError("dirty_state is invalid")
            object.__setattr__(self, "dirty_state", dirty)
        if not isinstance(self.ownership_known, bool):
            raise ValueError("ownership_known must be bool")
        object.__setattr__(self, "mutable_scope", _scope(self.mutable_scope, "mutable_scope"))
        leases = tuple(self.leases)
        if any(not isinstance(item, LeaseFact) for item in leases):
            raise ValueError("leases must be LeaseFact instances")
        if len({item.lease_id for item in leases}) != len(leases):
            raise ValueError("lease_id must be unique within a snapshot")
        object.__setattr__(self, "leases", leases)
        if self.job is not None and not isinstance(self.job, JobFact):
            raise ValueError("job must be a JobFact or None")
        if self.merge_fold is not None and not isinstance(self.merge_fold, MergeFoldFact):
            raise ValueError("merge_fold must be a MergeFoldFact or None")
        projections = tuple(self.projections)
        if any(not isinstance(item, ProjectionClaim) for item in projections):
            raise ValueError("projections must be ProjectionClaim instances")
        if len({item.source for item in projections}) != len(projections):
            raise ValueError("projection source must be unique within a snapshot")
        object.__setattr__(self, "projections", projections)


@dataclass(frozen=True, slots=True)
class ContinuityVerdict:
    classification: ContinuityClassification
    safe_to_mutate: bool
    findings: tuple[ContinuityFinding, ...]
    reconciliation_actions: tuple[ReconciliationAction, ...]


def _lease_fences_snapshot(snapshot: ContinuitySnapshot, lease: LeaseFact) -> bool:
    try:
        same_worktree = (
            windows_worktree_key(snapshot.worktree)
            == windows_worktree_key(lease.worktree_key)
        )
    except ValueError:
        return True
    if same_worktree:
        return True
    return write_sets_overlap(snapshot.mutable_scope, lease.mutable_scope)


def _classify_leases(snapshot: ContinuitySnapshot, findings: list[ContinuityFinding]) -> None:
    owner_key = (snapshot.session_id, snapshot.task_id)
    for lease in sorted(snapshot.leases, key=lambda item: item.lease_id):
        own = (lease.session_id, lease.task_id) == owner_key
        if lease.state == "RELEASED":
            continue
        if lease.state == "UNKNOWN":
            if own or _lease_fences_snapshot(snapshot, lease):
                findings.append(
                    ContinuityFinding(
                        ContinuityClassification.UNKNOWN,
                        "LEASE_STATE_UNKNOWN",
                        f"lease {lease.lease_id}",
                    )
                )
            continue
        fences = _lease_fences_snapshot(snapshot, lease)
        if lease.state == "ACTIVE":
            if own:
                continue
            if not fences:
                continue
            same_worktree = (
                windows_worktree_key(snapshot.worktree)
                == windows_worktree_key(lease.worktree_key)
            )
            reason = "LEASE_OWNER_CONFLICT" if same_worktree else "MUTABLE_SCOPE_OVERLAP"
            findings.append(
                ContinuityFinding(
                    ContinuityClassification.CLAIM_CONFLICT,
                    reason,
                    f"lease {lease.lease_id}",
                )
            )
            continue
        # STALE / QUARANTINED: deterministic reconciliation residue.
        if own or fences:
            findings.append(
                ContinuityFinding(
                    ContinuityClassification.RECONCILE_REQUIRED,
                    "LEASE_RECONCILIATION_REQUIRED",
                    f"lease {lease.lease_id}",
                )
            )


def classify_continuity(snapshot: ContinuitySnapshot) -> ContinuityVerdict:
    """Classify one immutable factual snapshot; pure and deterministic."""
    if not isinstance(snapshot, ContinuitySnapshot):
        raise ValueError("snapshot must be a ContinuitySnapshot")

    findings: list[ContinuityFinding] = []

    if snapshot.expected_head is None:
        findings.append(
            ContinuityFinding(ContinuityClassification.UNKNOWN, "EXPECTED_HEAD_UNKNOWN", "expected_head")
        )
    if snapshot.local_head is None:
        findings.append(
            ContinuityFinding(ContinuityClassification.UNKNOWN, "LOCAL_HEAD_UNKNOWN", "local_head")
        )
    if snapshot.remote_head is None:
        findings.append(
            ContinuityFinding(ContinuityClassification.UNKNOWN, "REMOTE_HEAD_UNKNOWN", "remote_head")
        )
    if snapshot.job is not None and snapshot.job.state is None:
        findings.append(
            ContinuityFinding(
                ContinuityClassification.UNKNOWN, "JOB_STATE_UNKNOWN", f"job {snapshot.job.job_id}"
            )
        )

    if (
        snapshot.local_head is not None
        and snapshot.expected_head is not None
        and snapshot.local_head != snapshot.expected_head
    ):
        findings.append(
            ContinuityFinding(
                ContinuityClassification.HEAD_DRIFT,
                "LOCAL_HEAD_NOT_EXPECTED",
                f"local {snapshot.local_head} expected {snapshot.expected_head}",
            )
        )
    if (
        snapshot.local_head is not None
        and snapshot.remote_head is not None
        and snapshot.local_head != snapshot.remote_head
    ):
        findings.append(
            ContinuityFinding(
                ContinuityClassification.STALE_LOCAL_CHECKOUT,
                "LOCAL_HEAD_NOT_REMOTE",
                f"local {snapshot.local_head} remote {snapshot.remote_head}",
            )
        )

    if snapshot.dirty_state is None or snapshot.dirty_state == "UNKNOWN":
        findings.append(
            ContinuityFinding(
                ContinuityClassification.WORKTREE_DIRTY_OR_UNKNOWN, "DIRTY_STATE_UNKNOWN", "dirty_state"
            )
        )
    elif snapshot.dirty_state == "DIRTY":
        findings.append(
            ContinuityFinding(
                ContinuityClassification.WORKTREE_DIRTY_OR_UNKNOWN, "WORKTREE_DIRTY", "dirty_state"
            )
        )
    if not snapshot.ownership_known:
        findings.append(
            ContinuityFinding(
                ContinuityClassification.WORKTREE_DIRTY_OR_UNKNOWN, "OWNERSHIP_UNKNOWN", "ownership_known"
            )
        )

    _classify_leases(snapshot, findings)

    if snapshot.job is not None and snapshot.job.state is not None:
        if snapshot.job.state is TaskState.RECOVERY_NEEDED:
            findings.append(
                ContinuityFinding(
                    ContinuityClassification.RECONCILE_REQUIRED,
                    "RECOVERY_TRANSITION_REQUIRED",
                    f"job {snapshot.job.job_id}",
                )
            )
        elif snapshot.job.state in _TERMINAL_JOB_STATES:
            findings.append(
                ContinuityFinding(
                    ContinuityClassification.CLAIM_CONFLICT,
                    "JOB_TERMINAL",
                    f"job {snapshot.job.job_id} {snapshot.job.state.value}",
                )
            )

    if snapshot.merge_fold is not None:
        if snapshot.merge_fold.fold_complete is None:
            findings.append(
                ContinuityFinding(
                    ContinuityClassification.MERGED_NOT_FOLDED, "FOLD_STATUS_UNKNOWN", "fold_complete"
                )
            )
        elif not snapshot.merge_fold.fold_complete:
            findings.append(
                ContinuityFinding(
                    ContinuityClassification.MERGED_NOT_FOLDED, "FOLD_NOT_COMPLETE", "fold_complete"
                )
            )
        if snapshot.merge_fold.release_complete is None:
            findings.append(
                ContinuityFinding(
                    ContinuityClassification.MERGED_NOT_FOLDED,
                    "RELEASE_STATUS_UNKNOWN",
                    "release_complete",
                )
            )
        elif not snapshot.merge_fold.release_complete:
            findings.append(
                ContinuityFinding(
                    ContinuityClassification.MERGED_NOT_FOLDED,
                    "RELEASE_NOT_COMPLETE",
                    "release_complete",
                )
            )

    actual_active_lease_ids = frozenset(
        lease.lease_id for lease in snapshot.leases if lease.state == "ACTIVE"
    )
    for claim in sorted(snapshot.projections, key=lambda item: item.source):
        if (
            claim.asserted_head is not None
            and snapshot.local_head is not None
            and claim.asserted_head != snapshot.local_head
        ):
            findings.append(
                ContinuityFinding(
                    ContinuityClassification.SSOT_DRIFT,
                    "PROJECTION_HEAD_CONTRADICTS_FACTS",
                    f"projection {claim.source}",
                )
            )
        if claim.asserted_branch is not None and claim.asserted_branch != snapshot.branch:
            findings.append(
                ContinuityFinding(
                    ContinuityClassification.SSOT_DRIFT,
                    "PROJECTION_BRANCH_CONTRADICTS_FACTS",
                    f"projection {claim.source}",
                )
            )
        if claim.asserted_active_lease_ids is not None and (
            frozenset(claim.asserted_active_lease_ids) != actual_active_lease_ids
        ):
            findings.append(
                ContinuityFinding(
                    ContinuityClassification.SSOT_DRIFT,
                    "PROJECTION_CLAIMS_CONTRADICTS_FACTS",
                    f"projection {claim.source}",
                )
            )

    ordered = tuple(
        dict.fromkeys(
            sorted(
                findings,
                key=lambda item: (
                    _PRECEDENCE_INDEX[item.kind],
                    item.reason_code,
                    item.detail,
                ),
            )
        )
    )
    classification = ordered[0].kind if ordered else ContinuityClassification.FRESH
    if classification is ContinuityClassification.FRESH:
        actions: tuple[ReconciliationAction, ...] = ()
    else:
        present_kinds = {finding.kind for finding in ordered}
        actions = tuple(
            _ACTION_BY_KIND[kind] for kind in _PRECEDENCE if kind in present_kinds
        )
    return ContinuityVerdict(
        classification=classification,
        safe_to_mutate=classification is ContinuityClassification.FRESH,
        findings=ordered,
        reconciliation_actions=actions,
    )
