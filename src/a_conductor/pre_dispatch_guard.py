"""WO-P1-498 / 498A — lease-bound launch-time PRE_DISPATCH GUARD.

A small typed/injected guard contract plus a ``WorkerLease``-backed
implementation that revalidates the ACCEPTED baseline lease at the
consequential FRESH supervised launch seam. This closes the TOCTOU gap
between initial ZCode lease admission/assembly and the actual launch:
the lease may have been released, quarantined, gone stale, or its
authority-bearing binding may have drifted since assembly.

Boundaries (498A scope — all reuse, no new authority):

- REUSES the existing ``WorkerLease`` / ``LeaseHealth`` / ``LeaseHealthKind``
  records and the ``inspect_health`` reader shape (the same configured lease
  authority the owner control path uses). The health reader is INJECTED;
- never acquires, re-acquires, releases, heartbeats, or schedules leases;
- opens NO SQLite path / store of its own and adds no table, index,
  scheduler, retry, claim, or dedupe authority;
- is NOT atomic hotspot admission (MSP-2/#475) and claims no
  cross-worktree/cross-device exactly-one-writer semantics;
- guard results are UNTRUSTED authority output: every failure collapses to
  a stable bounded typed reason code, never a raw exception or data leak.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Callable, Protocol

from .project_identity import GitReadOnlyRunner, StrictReadOnlyGitRunner, _same_path
from .worker_lease import (
    LeaseHealth,
    LeaseHealthKind,
    LeaseMutationIntent,
    WorkerLease,
    _mutable_scope_is_authorized,
)


_REASON_RE = re.compile(r"[A-Z0-9_]{3,64}")

_NON_ACTIVE_REASONS = {
    LeaseHealthKind.STALE: "LEASE_STALE",
    LeaseHealthKind.QUARANTINED: "LEASE_QUARANTINED",
    LeaseHealthKind.RELEASED: "LEASE_RELEASED",
    LeaseHealthKind.EXPIRY_UNKNOWN: "LEASE_EXPIRY_UNKNOWN",
}


def _valid_reason(reason: object) -> str | None:
    if isinstance(reason, str) and _REASON_RE.fullmatch(reason):
        return reason
    return None


def is_valid_guard_reason(reason: object) -> bool:
    """Shared bounded reason grammar: untrusted guard output is acceptable
    only as a stable ``[A-Z0-9_]{3,64}`` code with no separators."""
    return _valid_reason(reason) is not None


# ------------- WO-P1-498 / 498A: read-only live Git identity -------------
#
# A lease revalidation and the assembly-time Git context check do not prove
# the repository identity is still current at the consequential launch seam.
# The types below expose a bounded read-only observation of the LIVE repo
# root/branch/HEAD through the SAME accepted fixed-command read-only Git
# runner already used by project identity verification. They add no store,
# lease, claim, scheduler, retry, merge, completion, or atomicity authority,
# and claim no cross-session/cross-process linearization: this is a
# same-process launch-boundary recheck.


def _valid_identity_text(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and not any(char in value for char in ("\x00", "\r", "\n"))
    )


@dataclass(frozen=True, slots=True)
class LiveWorktreeIdentity:
    """Bounded live Git identity observed at the launch seam."""

    repo_root: str
    branch: str
    head: str

    def __post_init__(self) -> None:
        for field_name in ("repo_root", "branch", "head"):
            if not _valid_identity_text(getattr(self, field_name)):
                raise ValueError(
                    f"{field_name} must be non-blank text without control characters"
                )


class LiveWorktreeObservationError(Exception):
    """Typed observer failure; carries a bounded reason code only and never
    retains raw runner output or underlying exceptions."""

    def __init__(self, reason_code: str) -> None:
        reason = _valid_reason(reason_code)
        if reason is None:
            raise ValueError("reason_code is invalid")
        self.reason_code = reason
        super().__init__(reason)


class LiveWorktreeObserver(Protocol):
    """Read-only source of the live repo root, branch and HEAD facts."""

    def observe(self, repo_root: str) -> LiveWorktreeIdentity: ...


class GitLiveWorktreeObserver:
    """Reuse the existing fixed-command read-only Git runner for the live
    identity observation. Only ``show_toplevel`` / ``branch`` / ``head``
    are consumed; no arbitrary subcommand, mutation, or network access."""

    def __init__(self, *, runner: GitReadOnlyRunner | None = None) -> None:
        active_runner = runner or StrictReadOnlyGitRunner()
        for method_name in ("show_toplevel", "branch", "head"):
            if not callable(getattr(active_runner, method_name, None)):
                raise ValueError(f"runner must provide {method_name}")
        self._runner = active_runner

    @staticmethod
    def _read(
        method: Callable[[Path], object], worktree: Path, *, unavailable: str
    ) -> str:
        try:
            result = method(worktree)
        except Exception:
            raise LiveWorktreeObservationError(unavailable) from None
        if getattr(result, "success", None) is not True:
            raise LiveWorktreeObservationError(unavailable)
        stdout = getattr(result, "stdout", None)
        if not _valid_identity_text(stdout):
            raise LiveWorktreeObservationError("GIT_IDENTITY_MALFORMED")
        return stdout.strip()

    def observe(self, repo_root: str) -> LiveWorktreeIdentity:
        if not _valid_identity_text(repo_root):
            raise LiveWorktreeObservationError("WORKTREE_ROOT_UNAVAILABLE")
        try:
            worktree = Path(repo_root).expanduser().resolve(strict=False)
            if not worktree.is_dir():
                raise LiveWorktreeObservationError("WORKTREE_ROOT_UNAVAILABLE")
        except LiveWorktreeObservationError:
            raise
        except Exception:
            raise LiveWorktreeObservationError("WORKTREE_ROOT_UNAVAILABLE") from None

        root = self._read(
            self._runner.show_toplevel, worktree, unavailable="WORKTREE_ROOT_UNAVAILABLE"
        )
        if not Path(root).is_absolute():
            raise LiveWorktreeObservationError("GIT_IDENTITY_MALFORMED")
        branch = self._read(
            self._runner.branch, worktree, unavailable="GIT_IDENTITY_UNAVAILABLE"
        )
        head = self._read(
            self._runner.head, worktree, unavailable="GIT_IDENTITY_UNAVAILABLE"
        )
        try:
            return LiveWorktreeIdentity(repo_root=root, branch=branch, head=head)
        except ValueError:
            raise LiveWorktreeObservationError("GIT_IDENTITY_MALFORMED") from None


def live_worktree_drift_reason(
    observed: LiveWorktreeIdentity,
    *,
    expected_repo_root: str,
    expected_branch: str,
    expected_head: str,
) -> str | None:
    """Return a stable drift code when the observed live identity differs
    from the accepted run binding, or ``None`` when they agree. Expected
    values come from the ACCEPTED assembly identity — never from the
    observation itself."""
    if not isinstance(observed, LiveWorktreeIdentity) or not all(
        _valid_identity_text(value)
        for value in (expected_repo_root, expected_branch, expected_head)
    ):
        return "WORKTREE_IDENTITY_INVALID"
    if not _same_path(observed.repo_root, expected_repo_root):
        return "WORKTREE_ROOT_MISMATCH"
    if observed.branch != expected_branch:
        return "WORKTREE_BRANCH_MISMATCH"
    if observed.head.casefold() != expected_head.casefold():
        return "WORKTREE_HEAD_MISMATCH"
    return None


class PreDispatchGuardDecisionKind(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


@dataclass(frozen=True, slots=True)
class PreDispatchGuardDecision:
    """Stable typed guard output. Reason codes are bounded ``[A-Z0-9_]{3,64}``
    strings only; malformed values fail closed at construction."""

    kind: PreDispatchGuardDecisionKind
    reason_code: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, PreDispatchGuardDecisionKind):
            raise ValueError("kind must be a PreDispatchGuardDecisionKind")
        if _valid_reason(self.reason_code) is None:
            raise ValueError("reason_code is invalid")


class PreDispatchGuard(Protocol):
    """The coordinator's fresh-launch revalidation seam (no payload — the
    guard is fully bound to its accepted baseline at construction)."""

    def check(self) -> PreDispatchGuardDecision: ...


class LeaseHealthReader(Protocol):
    """Reuse of the accepted ``inspect_health`` reader shape (same configured
    lease authority; never a second lease-store abstraction)."""

    def inspect_health(self, lease_id: str, *, now: object) -> LeaseHealth: ...


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WorkerLeasePreDispatchGuard:
    """Launch-time revalidation of one ACCEPTED ``WorkerLease`` baseline.

    Re-reads the lease by ``lease_id`` through the INJECTED health reader
    and requires ACTIVE health plus exact continued agreement on every
    authority-bearing field: worker/session/task/project identity,
    worktree, branch, expected HEAD, mutation intent, baseline
    allowed/forbidden/mutable scope, and the declared requested mutable
    scope. Lifecycle timestamps (heartbeat/expiry advancement) may
    legitimately change; release/quarantine/stale/expiry-uncertainty
    denies.
    """

    def __init__(
        self,
        *,
        health_reader: LeaseHealthReader,
        baseline_lease: WorkerLease,
        requested_mutable_scope: tuple[str, ...] = (),
        clock: Callable[[], object] = _utc_now,
    ) -> None:
        if not callable(getattr(health_reader, "inspect_health", None)):
            raise ValueError("health_reader must provide inspect_health")
        if not isinstance(baseline_lease, WorkerLease):
            raise ValueError("baseline_lease must be a WorkerLease")
        if not isinstance(requested_mutable_scope, tuple):
            requested_mutable_scope = tuple(requested_mutable_scope or ())
        if not callable(clock):
            raise ValueError("clock must be callable")
        self._reader = health_reader
        self._baseline = baseline_lease
        self._requested = requested_mutable_scope
        self._clock = clock

    @property
    def lease_id(self) -> str:
        return self._baseline.lease_id

    def _deny(self, reason: str) -> PreDispatchGuardDecision:
        return PreDispatchGuardDecision(PreDispatchGuardDecisionKind.DENY, reason)

    def check(self) -> PreDispatchGuardDecision:
        try:
            health = self._reader.inspect_health(self._baseline.lease_id, now=self._clock())
        except Exception:
            return self._deny("LEASE_HEALTH_UNAVAILABLE")
        if not isinstance(health, LeaseHealth):
            return self._deny("LEASE_HEALTH_INVALID")
        kind = health.kind
        if kind is not LeaseHealthKind.ACTIVE:
            return self._deny(_NON_ACTIVE_REASONS.get(kind, "LEASE_NOT_ACTIVE"))
        observed = health.lease
        if not isinstance(observed, WorkerLease):
            return self._deny("LEASE_HEALTH_INVALID")
        baseline = self._baseline
        if observed.lease_id != baseline.lease_id:
            return self._deny("LEASE_ID_MISMATCH")
        if observed.worker_id != baseline.worker_id:
            return self._deny("LEASE_WORKER_MISMATCH")
        if observed.session_id != baseline.session_id:
            return self._deny("LEASE_SESSION_MISMATCH")
        if observed.task_id != baseline.task_id:
            return self._deny("LEASE_TASK_MISMATCH")
        if observed.project_id != baseline.project_id:
            return self._deny("LEASE_PROJECT_MISMATCH")
        if observed.worktree_key != baseline.worktree_key:
            return self._deny("LEASE_WORKTREE_MISMATCH")
        if observed.branch != baseline.branch:
            return self._deny("LEASE_BRANCH_MISMATCH")
        if str(observed.expected_head).casefold() != str(baseline.expected_head).casefold():
            return self._deny("LEASE_HEAD_MISMATCH")
        if observed.hotspot_key != baseline.hotspot_key:
            return self._deny("LEASE_HOTSPOT_MISMATCH")
        if frozenset(observed.required_capabilities or ()) != frozenset(
            baseline.required_capabilities or ()
        ):
            return self._deny("LEASE_CAPABILITIES_MISMATCH")
        if observed.runtime_id != baseline.runtime_id:
            return self._deny("LEASE_RUNTIME_MISMATCH")
        if observed.lease_ttl_seconds != baseline.lease_ttl_seconds:
            return self._deny("LEASE_TTL_MISMATCH")
        if observed.mutation_intent is not baseline.mutation_intent:
            return self._deny("LEASE_INTENT_MISMATCH")
        if frozenset(observed.allowed_scope or ()) != frozenset(baseline.allowed_scope or ()):
            return self._deny("LEASE_ALLOWED_SCOPE_MISMATCH")
        if frozenset(observed.forbidden_scope or ()) != frozenset(baseline.forbidden_scope or ()):
            return self._deny("LEASE_FORBIDDEN_SCOPE_MISMATCH")
        if frozenset(observed.mutable_scope or ()) != frozenset(baseline.mutable_scope or ()):
            return self._deny("LEASE_MUTABLE_SCOPE_MISMATCH")
        requested = self._requested
        if requested:
            if not _mutable_scope_is_authorized(observed.allowed_scope or (), requested):
                return self._deny("REQUESTED_SCOPE_NOT_AUTHORIZED")
            if not _mutable_scope_is_authorized(observed.mutable_scope or (), requested):
                return self._deny("REQUESTED_SCOPE_OUTSIDE_MUTABLE")
            forbidden = observed.forbidden_scope or ()
            for expression in requested:
                if expression in forbidden or any(
                    fnmatchcase(expression, pattern) for pattern in forbidden
                ):
                    return self._deny("REQUESTED_SCOPE_FORBIDDEN")
        return PreDispatchGuardDecision(
            PreDispatchGuardDecisionKind.ALLOW, "PRE_DISPATCH_ALLOWED"
        )
