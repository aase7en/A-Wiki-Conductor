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
from typing import Callable, Protocol

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
