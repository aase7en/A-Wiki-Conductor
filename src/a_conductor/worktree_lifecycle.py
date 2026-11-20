"""WO-P1-417 WTL-1: deterministic, fail-closed, read-only worktree lifecycle
classifier.

This module is a pure classifier over one immutable factual snapshot
(:class:`WtlWorktreeFacts`). It performs no Git access, process observation,
network calls, filesystem I/O, store reads/writes, or cleanup execution, and
holds no state. It reuses the canonical worktree identity seam
(``windows_worktree_key``), the exact process-ownership classification seam
(``classify_process_ownership``), and the durable execution state vocabulary
(``ExecutionProcessState``); it creates no second claim/lease/task/review store
and no cleanup queue.

Only :attr:`WtlLifecycleState.RELEASED_SAFE_TO_ARCHIVE` sets
``cleanup_eligible=True``. Protective evidence outranks permissive evidence,
missing/stale/conflicting facts fail closed to ``EVIDENCE_INCOMPLETE`` (never
to a safe default), and zero durable linkage evidence yields
``UNOWNED_UNKNOWN``. Worktree names, age, and bare PID numbers grant no
authority anywhere in this module.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .execution_record import ExecutionProcessState
from .registry import windows_worktree_key
from .runtime_safety import ProcessObservation, classify_process_ownership

WTL_CLASSIFIER_VERSION = "WTL1-1"

_HEAD_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")
_FINGERPRINT_RE = re.compile(r"^[0-9a-f]{64}$")
_LEASE_STATES = frozenset({"ACTIVE", "RELEASED", "STALE", "QUARANTINED", "UNKNOWN"})
_LIVE_EXECUTION_STATES = frozenset(
    {
        ExecutionProcessState.QUEUED,
        ExecutionProcessState.STARTING,
        ExecutionProcessState.RUNNING,
        ExecutionProcessState.PROCESS_STILL_RUNNING,
    }
)
_UNRESOLVED_EXECUTION_STATES = frozenset(
    {
        ExecutionProcessState.PROCESS_EXITED_UNKNOWN_RESULT,
        ExecutionProcessState.RECOVERY_REQUIRED,
        ExecutionProcessState.VERIFICATION_REQUIRED,
    }
)


class WtlLifecycleState(str, Enum):
    ACTIVE_OWNED = "ACTIVE_OWNED"
    REVIEW_FROZEN = "REVIEW_FROZEN"
    MERGED_NOT_FOLDED = "MERGED_NOT_FOLDED"
    RELEASED_SAFE_TO_ARCHIVE = "RELEASED_SAFE_TO_ARCHIVE"
    DIRTY_PROTECTED = "DIRTY_PROTECTED"
    CLAIM_CONFLICT = "CLAIM_CONFLICT"
    PROCESS_OR_EXECUTION_ACTIVE = "PROCESS_OR_EXECUTION_ACTIVE"
    REMOTE_UNMERGED = "REMOTE_UNMERGED"
    UNOWNED_UNKNOWN = "UNOWNED_UNKNOWN"
    EVIDENCE_INCOMPLETE = "EVIDENCE_INCOMPLETE"


_REASON_STATE: dict[str, WtlLifecycleState] = {
    "PROTECTED_ROOT": WtlLifecycleState.DIRTY_PROTECTED,
    "TRACKED_DIRTY": WtlLifecycleState.DIRTY_PROTECTED,
    "UNTRACKED_BYTES_PRESENT": WtlLifecycleState.DIRTY_PROTECTED,
    "LIVE_EXACT_PROCESS": WtlLifecycleState.PROCESS_OR_EXECUTION_ACTIVE,
    "LIVE_DURABLE_EXECUTION": WtlLifecycleState.PROCESS_OR_EXECUTION_ACTIVE,
    "LEASE_OWNER_CONFLICT": WtlLifecycleState.CLAIM_CONFLICT,
    "ACTIVE_LEASE_OWNED": WtlLifecycleState.ACTIVE_OWNED,
    "REVIEW_FREEZE_EXACT": WtlLifecycleState.REVIEW_FROZEN,
    "OPEN_PR_PRESENT": WtlLifecycleState.REMOTE_UNMERGED,
    "REMOTE_BRANCH_PRESENT": WtlLifecycleState.REMOTE_UNMERGED,
    "UNMERGED_COMMITS_PRESENT": WtlLifecycleState.REMOTE_UNMERGED,
    "MERGED_FOLD_INCOMPLETE": WtlLifecycleState.MERGED_NOT_FOLDED,
    "MERGED_RELEASE_INCOMPLETE": WtlLifecycleState.MERGED_NOT_FOLDED,
    "RELEASE_PROVEN": WtlLifecycleState.RELEASED_SAFE_TO_ARCHIVE,
    "NO_DURABLE_LINKAGE": WtlLifecycleState.UNOWNED_UNKNOWN,
}

_INCOMPLETE_STATE = WtlLifecycleState.EVIDENCE_INCOMPLETE
_EVIDENCE_INCOMPLETE_CODES = (
    "INPUT_FINGERPRINT_MISMATCH",
    "HEAD_UNKNOWN",
    "HEAD_RECHECK_UNKNOWN",
    "HEAD_DRIFT",
    "PROTECTED_ROOT_UNKNOWN",
    "PROCESS_EVIDENCE_UNKNOWN",
    "PROCESS_IDENTITY_STALE",
    "PROCESS_IDENTITY_MISMATCH",
    "PROCESS_IDENTITY_UNKNOWN",
    "EXECUTION_EVIDENCE_UNKNOWN",
    "EXECUTION_OUTCOME_UNRESOLVED",
    "LEASE_EVIDENCE_UNKNOWN",
    "LEASE_STATE_UNKNOWN",
    "LEASE_RECONCILIATION_REQUIRED",
    "LEASE_BINDING_CONFLICT",
    "DIRTY_STATE_UNKNOWN",
    "UNTRACKED_STATE_UNKNOWN",
    "REVIEW_EVIDENCE_UNKNOWN",
    "REVIEW_FREEZE_HEAD_CONFLICT",
    "REVIEW_FREEZE_BINDING_CONFLICT",
    "MERGE_STATUS_UNKNOWN",
    "FOLD_STATUS_UNKNOWN",
    "RELEASE_STATUS_UNKNOWN",
    "OPEN_PR_STATUS_UNKNOWN",
    "REMOTE_BRANCH_STATUS_UNKNOWN",
    "UNMERGED_COMMIT_STATUS_UNKNOWN",
    "MERGE_EVIDENCE_MISSING",
    "REMOTE_EVIDENCE_MISSING",
    "CLASSIFIER_INTERNAL_NO_FINDINGS",
)
for _code in _EVIDENCE_INCOMPLETE_CODES:
    _REASON_STATE[_code] = _INCOMPLETE_STATE

# Deterministic severity precedence (WO-P1-417 evidence precedence): protected
# root first, then exact live process/execution, then claim conflicts, then
# active ownership, then dirty evidence, then review freeze, then remote
# unmerged evidence, then incomplete fold/release, then the positive release
# verdict, then missing-fact incompleteness, and finally zero-linkage
# UNOWNED_UNKNOWN. Rank 9 vs 10/11 encodes that a fully proven release never
# coexists with missing evidence, and incompleteness outranks unowned.
_REASON_RANK: dict[str, int] = {
    "PROTECTED_ROOT": 1,
    "LIVE_EXACT_PROCESS": 2,
    "LIVE_DURABLE_EXECUTION": 2,
    "LEASE_OWNER_CONFLICT": 3,
    "ACTIVE_LEASE_OWNED": 4,
    "TRACKED_DIRTY": 5,
    "UNTRACKED_BYTES_PRESENT": 5,
    "REVIEW_FREEZE_EXACT": 6,
    "OPEN_PR_PRESENT": 7,
    "REMOTE_BRANCH_PRESENT": 7,
    "UNMERGED_COMMITS_PRESENT": 7,
    "MERGED_FOLD_INCOMPLETE": 8,
    "MERGED_RELEASE_INCOMPLETE": 8,
    "RELEASE_PROVEN": 9,
    "NO_DURABLE_LINKAGE": 11,
}
for _code in _EVIDENCE_INCOMPLETE_CODES:
    _REASON_RANK[_code] = 10
# Input-integrity failure outranks every evidence finding: a broken
# fingerprint invalidates all facts, protective ones included, and demands
# re-observation instead of trusting unverified inputs.
_REASON_RANK["INPUT_FINGERPRINT_MISMATCH"] = 0

REASON_CODES = frozenset(_REASON_STATE)


def _text(value: str, field_name: str, *, max_length: int = 512) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if "\x00" in value or "\r" in value or "\n" in value:
        raise ValueError(f"{field_name} is invalid")
    cleaned = value.strip()
    if len(cleaned) > max_length:
        raise ValueError(f"{field_name} is invalid")
    return cleaned


def _optional_text(value: str | None, field_name: str, *, max_length: int = 512) -> str | None:
    if value is None:
        return None
    return _text(value, field_name, max_length=max_length)


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


def _paths(values: tuple[str, ...] | None, field_name: str) -> tuple[str, ...] | None:
    if values is None:
        return None
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{field_name} must be a sequence")
    result = tuple(_text(value, field_name, max_length=1024) for value in values)
    if len(set(result)) != len(result):
        raise ValueError(f"{field_name} must not contain duplicates")
    return result


def _refs(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{field_name} must be a sequence")
    result = tuple(_text(value, field_name, max_length=512) for value in values)
    if len(set(result)) != len(result):
        raise ValueError(f"{field_name} must not contain duplicates")
    return result


def _optional_timestamp(value: str, field_name: str) -> str:
    if not value:
        return ""
    cleaned = _text(value, field_name, max_length=64)
    try:
        parsed = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a timezone-aware ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must be a timezone-aware ISO timestamp")
    return cleaned


def _optional_fingerprint(value: str) -> str:
    if not value:
        return ""
    if not isinstance(value, str) or not _FINGERPRINT_RE.fullmatch(value):
        raise ValueError("input_fingerprint must be lowercase SHA-256 hex")
    return value


def _normalize_worktree_key(value: str, field_name: str) -> str:
    return windows_worktree_key(_text(value, field_name, max_length=1024))


@dataclass(frozen=True, slots=True)
class WtlReason:
    """One typed, ordered classification reason; never an action."""

    code: str
    detail: str = ""

    def __post_init__(self) -> None:
        if self.code not in REASON_CODES:
            raise ValueError("code is not a WTL reason code")
        detail = self.detail if isinstance(self.detail, str) else ""
        if len(detail) > 512 or "\x00" in detail or "\r" in detail or "\n" in detail:
            raise ValueError("detail is invalid")
        object.__setattr__(self, "detail", detail)


@dataclass(frozen=True, slots=True)
class WtlLeaseFact:
    """One durable claim/lease record READ fact bound to a worktree key.

    ``authority`` names the existing store the fact was read from (for example
    ``worker_lease`` or ``job_store``); WTL-1 never writes to any of them.
    """

    lease_id: str
    authority: str
    owner_ref: str
    state: str
    worktree_key: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "lease_id", _text(self.lease_id, "lease_id", max_length=128))
        object.__setattr__(self, "authority", _text(self.authority, "authority", max_length=64))
        object.__setattr__(self, "owner_ref", _text(self.owner_ref, "owner_ref", max_length=256))
        state = _text(self.state, "state", max_length=32).upper()
        if state not in _LEASE_STATES:
            raise ValueError("state is invalid")
        object.__setattr__(self, "state", state)
        object.__setattr__(
            self,
            "worktree_key",
            _normalize_worktree_key(self.worktree_key, "worktree_key"),
        )


@dataclass(frozen=True, slots=True)
class WtlExecutionFact:
    """One durable execution READ fact, reusing the ExecutionProcessState
    vocabulary. The observation layer projects DurableExecutionRecord rows
    into this slim immutable fact; WTL-1 adds no execution store."""

    execution_id: str
    state: ExecutionProcessState
    pid: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "execution_id", _text(self.execution_id, "execution_id", max_length=128)
        )
        if not isinstance(self.state, ExecutionProcessState):
            raise ValueError("state must be an ExecutionProcessState")
        pid = self.pid
        if pid is not None:
            if not isinstance(pid, int) or isinstance(pid, bool) or pid < 1:
                raise ValueError("pid must be >= 1")
            object.__setattr__(self, "pid", pid)


@dataclass(frozen=True, slots=True)
class WtlProcessFact:
    """One exact process-identity READ fact. Identity means more than PID
    existence: ownership is classified from the full ProcessObservation via
    the existing ``classify_process_ownership`` seam."""

    pid: int
    observation: ProcessObservation

    def __post_init__(self) -> None:
        if not isinstance(self.pid, int) or isinstance(self.pid, bool) or self.pid < 1:
            raise ValueError("pid must be >= 1")
        if not isinstance(self.observation, ProcessObservation):
            raise ValueError("observation must be a ProcessObservation")
        object.__setattr__(self, "pid", self.pid)


@dataclass(frozen=True, slots=True)
class WtlReviewFreezeFact:
    """One durable frozen review candidate READ fact bound to an exact head."""

    review_ref: str
    frozen_head: str
    worktree_key: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "review_ref", _text(self.review_ref, "review_ref", max_length=256)
        )
        head = _head(self.frozen_head, "frozen_head")
        if head is None:
            raise ValueError("frozen_head must be a git object id")
        object.__setattr__(self, "frozen_head", head)
        object.__setattr__(
            self,
            "worktree_key",
            _normalize_worktree_key(self.worktree_key, "worktree_key"),
        )


@dataclass(frozen=True, slots=True)
class WtlMergeFoldFact:
    """Merge ancestry + fold/release obligation READ facts.

    ``None`` field values mean the fact is unknown; ``False`` means the
    obligation was observed as not met."""

    merged_into_canonical: bool | None
    fold_complete: bool | None
    release_complete: bool | None
    merge_commit: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "merged_into_canonical",
            _optional_bool(self.merged_into_canonical, "merged_into_canonical"),
        )
        object.__setattr__(
            self, "fold_complete", _optional_bool(self.fold_complete, "fold_complete")
        )
        object.__setattr__(
            self,
            "release_complete",
            _optional_bool(self.release_complete, "release_complete"),
        )
        object.__setattr__(self, "merge_commit", _head(self.merge_commit, "merge_commit"))


@dataclass(frozen=True, slots=True)
class WtlRemoteEvidence:
    """Open PR / remote branch / unmerged-commit READ evidence.

    Any ``None`` value means the remote fact could not be proven; unknown
    remote evidence is always EVIDENCE_INCOMPLETE, never safe."""

    open_pr: bool | None
    remote_branch_present: bool | None
    unmerged_commits: bool | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "open_pr", _optional_bool(self.open_pr, "open_pr"))
        object.__setattr__(
            self,
            "remote_branch_present",
            _optional_bool(self.remote_branch_present, "remote_branch_present"),
        )
        object.__setattr__(
            self,
            "unmerged_commits",
            _optional_bool(self.unmerged_commits, "unmerged_commits"),
        )


@dataclass(frozen=True, slots=True)
class WtlWorktreeFacts:
    """Immutable factual snapshot consumed by
    :func:`classify_worktree_lifecycle`.

    Every ``None`` means the fact is unknown (could not be observed); every
    empty tuple / ``False`` means observed absence. ``head_recheck`` is a
    fresh re-read of HEAD taken after the other collectors ran: equality
    proves the observation is fresh, and any drift invalidates it.
    """

    worktree_path: str
    worktree_key: str
    repo_root: str | None
    branch: str | None
    detached: bool | None
    head: str | None
    head_recheck: str | None
    protected_root: bool | None
    tracked_dirty: bool | None
    untracked_paths: tuple[str, ...] | None
    leases: tuple[WtlLeaseFact, ...] | None
    durable_executions: tuple[WtlExecutionFact, ...] | None
    process_observations: tuple[WtlProcessFact, ...] | None
    review_freezes: tuple[WtlReviewFreezeFact, ...] | None
    merge_fold: WtlMergeFoldFact | None
    remote: WtlRemoteEvidence | None
    durable_task_refs: tuple[str, ...] = ()
    observed_at: str = ""
    input_fingerprint: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "worktree_path",
            _text(self.worktree_path, "worktree_path", max_length=1024),
        )
        object.__setattr__(
            self,
            "worktree_key",
            _normalize_worktree_key(self.worktree_key, "worktree_key"),
        )
        object.__setattr__(
            self, "repo_root", _optional_text(self.repo_root, "repo_root", max_length=1024)
        )
        object.__setattr__(
            self, "branch", _optional_text(self.branch, "branch", max_length=256)
        )
        object.__setattr__(self, "detached", _optional_bool(self.detached, "detached"))
        object.__setattr__(self, "head", _head(self.head, "head"))
        object.__setattr__(self, "head_recheck", _head(self.head_recheck, "head_recheck"))
        object.__setattr__(
            self, "protected_root", _optional_bool(self.protected_root, "protected_root")
        )
        object.__setattr__(
            self, "tracked_dirty", _optional_bool(self.tracked_dirty, "tracked_dirty")
        )
        object.__setattr__(
            self, "untracked_paths", _paths(self.untracked_paths, "untracked_paths")
        )
        self._validate_facts_tuple(self.leases, WtlLeaseFact, "leases", "lease_id")
        self._validate_facts_tuple(
            self.durable_executions, WtlExecutionFact, "durable_executions", "execution_id"
        )
        self._validate_facts_tuple(
            self.process_observations, WtlProcessFact, "process_observations", "pid"
        )
        self._validate_facts_tuple(
            self.review_freezes, WtlReviewFreezeFact, "review_freezes", "review_ref"
        )
        if self.merge_fold is not None and not isinstance(self.merge_fold, WtlMergeFoldFact):
            raise ValueError("merge_fold must be a WtlMergeFoldFact or None")
        if self.remote is not None and not isinstance(self.remote, WtlRemoteEvidence):
            raise ValueError("remote must be a WtlRemoteEvidence or None")
        object.__setattr__(
            self, "durable_task_refs", _refs(self.durable_task_refs, "durable_task_refs")
        )
        object.__setattr__(
            self, "observed_at", _optional_timestamp(self.observed_at, "observed_at")
        )
        object.__setattr__(self, "input_fingerprint", _optional_fingerprint(self.input_fingerprint))

    @staticmethod
    def _validate_facts_tuple(value, item_type, field_name: str, id_field: str) -> None:
        if value is None:
            return
        if isinstance(value, (str, bytes)) or not isinstance(value, tuple):
            raise ValueError(f"{field_name} must be a tuple or None")
        if any(not isinstance(item, item_type) for item in value):
            raise ValueError(f"{field_name} must contain {item_type.__name__} instances")
        ids = [getattr(item, id_field) for item in value]
        if len(set(ids)) != len(ids):
            raise ValueError(f"{field_name} {id_field} values must be unique")


@dataclass(frozen=True, slots=True)
class WtlClassification:
    """Pure classification verdict; carries no cleanup action or side effect."""

    worktree_key: str
    classified_head: str | None
    state: WtlLifecycleState
    cleanup_eligible: bool
    reasons: tuple[WtlReason, ...]
    evidence_refs: tuple[str, ...]
    classifier_version: str
    classified_at: str
    input_fingerprint: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "worktree_key",
            _normalize_worktree_key(self.worktree_key, "worktree_key"),
        )
        classified_head = _head(self.classified_head, "classified_head")
        object.__setattr__(self, "classified_head", classified_head)
        if not isinstance(self.state, WtlLifecycleState):
            raise ValueError("state must be a WtlLifecycleState")
        if not isinstance(self.cleanup_eligible, bool):
            raise ValueError("cleanup_eligible must be bool")
        if self.cleanup_eligible != (self.state is WtlLifecycleState.RELEASED_SAFE_TO_ARCHIVE):
            raise ValueError("cleanup_eligible is true only for RELEASED_SAFE_TO_ARCHIVE")
        if not isinstance(self.reasons, tuple) or any(
            not isinstance(item, WtlReason) for item in self.reasons
        ):
            raise ValueError("reasons must be WtlReason instances")
        refs = _refs(self.evidence_refs, "evidence_refs")
        object.__setattr__(self, "evidence_refs", tuple(sorted(refs)))
        object.__setattr__(
            self,
            "classifier_version",
            _text(self.classifier_version, "classifier_version", max_length=64),
        )
        object.__setattr__(
            self, "classified_at", _optional_timestamp(self.classified_at, "classified_at")
        )
        object.__setattr__(self, "input_fingerprint", _optional_fingerprint(self.input_fingerprint))


def _canonical(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in value.items()}
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _canonical(getattr(value, field.name))
            for field in fields(value)
            if field.name != "input_fingerprint"
        }
    raise TypeError(f"unsupported fingerprint input type: {type(value).__name__}")


def wtl_input_fingerprint(facts: WtlWorktreeFacts) -> str:
    """Deterministic SHA-256 over the full factual snapshot (excluding the
    fingerprint field itself) so any classification is replayable/auditable."""
    if not isinstance(facts, WtlWorktreeFacts):
        raise ValueError("facts must be a WtlWorktreeFacts")
    payload = _canonical(facts)
    rendered = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _has_durable_linkage(facts: WtlWorktreeFacts) -> bool:
    return bool(
        facts.leases
        or facts.durable_executions
        or facts.process_observations
        or facts.review_freezes
        or facts.merge_fold is not None
        or facts.remote is not None
    )


def _classify_head(facts: WtlWorktreeFacts, findings: list[WtlReason]) -> None:
    if facts.head is None:
        findings.append(WtlReason("HEAD_UNKNOWN", "head"))
        return
    if facts.head_recheck is None:
        findings.append(WtlReason("HEAD_RECHECK_UNKNOWN", "head_recheck"))
        return
    if facts.head_recheck != facts.head:
        findings.append(
            WtlReason("HEAD_DRIFT", f"head {facts.head} recheck {facts.head_recheck}")
        )


def _classify_processes(facts: WtlWorktreeFacts, findings: list[WtlReason]) -> None:
    if facts.process_observations is None:
        findings.append(WtlReason("PROCESS_EVIDENCE_UNKNOWN", "process_observations"))
        return
    for fact in facts.process_observations:
        ownership = classify_process_ownership(fact.observation)
        detail = f"pid {fact.pid}"
        if ownership.value == "OWNED":
            findings.append(WtlReason("LIVE_EXACT_PROCESS", detail))
        elif ownership.value == "STALE":
            findings.append(WtlReason("PROCESS_IDENTITY_STALE", detail))
        elif ownership.value == "MISMATCH":
            findings.append(WtlReason("PROCESS_IDENTITY_MISMATCH", detail))
        else:
            findings.append(WtlReason("PROCESS_IDENTITY_UNKNOWN", detail))


def _classify_executions(facts: WtlWorktreeFacts, findings: list[WtlReason]) -> None:
    if facts.durable_executions is None:
        findings.append(WtlReason("EXECUTION_EVIDENCE_UNKNOWN", "durable_executions"))
        return
    for fact in facts.durable_executions:
        detail = f"execution {fact.execution_id}"
        if fact.state in _LIVE_EXECUTION_STATES:
            findings.append(WtlReason("LIVE_DURABLE_EXECUTION", detail))
        elif fact.state in _UNRESOLVED_EXECUTION_STATES:
            findings.append(WtlReason("EXECUTION_OUTCOME_UNRESOLVED", f"{detail} {fact.state.value}"))


def _classify_leases(facts: WtlWorktreeFacts, findings: list[WtlReason]) -> None:
    if facts.leases is None:
        findings.append(WtlReason("LEASE_EVIDENCE_UNKNOWN", "leases"))
        return
    bound: list[WtlLeaseFact] = []
    for fact in facts.leases:
        if fact.worktree_key != facts.worktree_key:
            findings.append(
                WtlReason("LEASE_BINDING_CONFLICT", f"lease {fact.lease_id}")
            )
            continue
        bound.append(fact)
    non_released = [fact for fact in bound if fact.state != "RELEASED"]
    active = [fact for fact in bound if fact.state == "ACTIVE"]
    if len(non_released) > 1:
        conflicting = ",".join(sorted(fact.lease_id for fact in non_released))
        findings.append(WtlReason("LEASE_OWNER_CONFLICT", conflicting))
        return
    if len(active) == 1:
        findings.append(WtlReason("ACTIVE_LEASE_OWNED", f"lease {active[0].lease_id}"))
        return
    for fact in non_released:
        if fact.state == "UNKNOWN":
            findings.append(WtlReason("LEASE_STATE_UNKNOWN", f"lease {fact.lease_id}"))
        elif fact.state in ("STALE", "QUARANTINED"):
            findings.append(
                WtlReason("LEASE_RECONCILIATION_REQUIRED", f"lease {fact.lease_id}")
            )


def _classify_dirty(facts: WtlWorktreeFacts, findings: list[WtlReason]) -> None:
    if facts.tracked_dirty is None:
        findings.append(WtlReason("DIRTY_STATE_UNKNOWN", "tracked_dirty"))
    elif facts.tracked_dirty:
        findings.append(WtlReason("TRACKED_DIRTY", "tracked_dirty"))
    if facts.untracked_paths is None:
        findings.append(WtlReason("UNTRACKED_STATE_UNKNOWN", "untracked_paths"))
    elif facts.untracked_paths:
        sample = ",".join(sorted(facts.untracked_paths)[:4])
        findings.append(WtlReason("UNTRACKED_BYTES_PRESENT", sample))


def _classify_review_freezes(facts: WtlWorktreeFacts, findings: list[WtlReason]) -> None:
    if facts.review_freezes is None:
        # Unknown review-freeze evidence (unavailable/raising collector) is
        # never observed absence: it fails closed to EVIDENCE_INCOMPLETE so a
        # proven release cannot rest on unproven review evidence.
        findings.append(WtlReason("REVIEW_EVIDENCE_UNKNOWN", "review_freezes"))
        return
    for fact in facts.review_freezes:
        detail = f"review {fact.review_ref}"
        if fact.worktree_key != facts.worktree_key:
            findings.append(WtlReason("REVIEW_FREEZE_BINDING_CONFLICT", detail))
        elif facts.head is not None and fact.frozen_head == facts.head:
            findings.append(WtlReason("REVIEW_FREEZE_EXACT", detail))
        else:
            findings.append(
                WtlReason("REVIEW_FREEZE_HEAD_CONFLICT", f"{detail} {fact.frozen_head}")
            )


def _classify_merge_fold(facts: WtlWorktreeFacts, findings: list[WtlReason]) -> None:
    if facts.merge_fold is None:
        return
    merge = facts.merge_fold
    if merge.merged_into_canonical is None:
        findings.append(WtlReason("MERGE_STATUS_UNKNOWN", "merged_into_canonical"))
        return
    if not merge.merged_into_canonical:
        findings.append(WtlReason("UNMERGED_COMMITS_PRESENT", "merged_into_canonical false"))
        return
    if merge.fold_complete is None:
        findings.append(WtlReason("FOLD_STATUS_UNKNOWN", "fold_complete"))
    elif not merge.fold_complete:
        findings.append(WtlReason("MERGED_FOLD_INCOMPLETE", "fold_complete false"))
    if merge.release_complete is None:
        findings.append(WtlReason("RELEASE_STATUS_UNKNOWN", "release_complete"))
    elif not merge.release_complete:
        findings.append(WtlReason("MERGED_RELEASE_INCOMPLETE", "release_complete false"))


def _classify_remote(facts: WtlWorktreeFacts, findings: list[WtlReason]) -> None:
    if facts.remote is None:
        return
    remote = facts.remote
    if remote.open_pr is None:
        findings.append(WtlReason("OPEN_PR_STATUS_UNKNOWN", "open_pr"))
    elif remote.open_pr:
        findings.append(WtlReason("OPEN_PR_PRESENT", "open_pr"))
    if remote.remote_branch_present is None:
        findings.append(WtlReason("REMOTE_BRANCH_STATUS_UNKNOWN", "remote_branch_present"))
    elif remote.remote_branch_present:
        findings.append(WtlReason("REMOTE_BRANCH_PRESENT", "remote_branch_present"))
    if remote.unmerged_commits is None:
        findings.append(WtlReason("UNMERGED_COMMIT_STATUS_UNKNOWN", "unmerged_commits"))
    elif remote.unmerged_commits:
        findings.append(WtlReason("UNMERGED_COMMITS_PRESENT", "unmerged_commits"))


def _evidence_refs(facts: WtlWorktreeFacts) -> tuple[str, ...]:
    refs: set[str] = set(facts.durable_task_refs)
    if facts.leases:
        refs.update(fact.lease_id for fact in facts.leases)
    if facts.durable_executions:
        refs.update(fact.execution_id for fact in facts.durable_executions)
    if facts.review_freezes:
        refs.update(fact.review_ref for fact in facts.review_freezes)
    if facts.merge_fold is not None and facts.merge_fold.merge_commit:
        refs.add(facts.merge_fold.merge_commit)
    return tuple(sorted(refs))


def classify_worktree_lifecycle(facts: WtlWorktreeFacts) -> WtlClassification:
    """Classify one immutable factual snapshot; pure and deterministic.

    The verdict is read-only evidence classification. It never recommends or
    performs cleanup; ``cleanup_eligible`` is True only for
    RELEASED_SAFE_TO_ARCHIVE, which itself requires every release fact to be
    freshly proven on the exact classified HEAD."""

    if not isinstance(facts, WtlWorktreeFacts):
        raise ValueError("facts must be a WtlWorktreeFacts")

    findings: list[WtlReason] = []

    if facts.input_fingerprint != wtl_input_fingerprint(facts):
        findings.append(WtlReason("INPUT_FINGERPRINT_MISMATCH", "input_fingerprint"))

    _classify_head(facts, findings)
    if facts.protected_root is None:
        findings.append(WtlReason("PROTECTED_ROOT_UNKNOWN", "protected_root"))
    elif facts.protected_root:
        findings.append(WtlReason("PROTECTED_ROOT", "canonical or instance root"))
    _classify_processes(facts, findings)
    _classify_executions(facts, findings)
    _classify_leases(facts, findings)
    _classify_dirty(facts, findings)
    _classify_review_freezes(facts, findings)
    _classify_merge_fold(facts, findings)
    _classify_remote(facts, findings)

    linkage = _has_durable_linkage(facts)
    if linkage and facts.merge_fold is None:
        findings.append(WtlReason("MERGE_EVIDENCE_MISSING", "merge_fold"))
    if linkage and facts.remote is None:
        findings.append(WtlReason("REMOTE_EVIDENCE_MISSING", "remote"))
    if not findings and linkage:
        findings.append(WtlReason("RELEASE_PROVEN", f"head {facts.head}"))
    elif not linkage:
        findings.append(WtlReason("NO_DURABLE_LINKAGE", "no durable facts"))

    ordered = tuple(
        dict.fromkeys(
            sorted(
                findings,
                key=lambda item: (
                    _REASON_RANK[item.code],
                    _REASON_STATE[item.code].value,
                    item.code,
                    item.detail,
                ),
            )
        )
    )
    if not ordered:
        ordered = (WtlReason("CLASSIFIER_INTERNAL_NO_FINDINGS"),)

    state = _REASON_STATE[ordered[0].code]
    return WtlClassification(
        worktree_key=facts.worktree_key,
        classified_head=facts.head,
        state=state,
        cleanup_eligible=state is WtlLifecycleState.RELEASED_SAFE_TO_ARCHIVE,
        reasons=ordered,
        evidence_refs=_evidence_refs(facts),
        classifier_version=WTL_CLASSIFIER_VERSION,
        classified_at=facts.observed_at,
        input_fingerprint=facts.input_fingerprint,
    )


__all__ = [
    "WTL_CLASSIFIER_VERSION",
    "REASON_CODES",
    "WtlLifecycleState",
    "WtlReason",
    "WtlLeaseFact",
    "WtlExecutionFact",
    "WtlProcessFact",
    "WtlReviewFreezeFact",
    "WtlMergeFoldFact",
    "WtlRemoteEvidence",
    "WtlWorktreeFacts",
    "WtlClassification",
    "wtl_input_fingerprint",
    "classify_worktree_lifecycle",
]
