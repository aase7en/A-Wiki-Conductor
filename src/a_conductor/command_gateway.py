"""WO-P1-603: ACT-1 Command Gateway — pure admission authority (slice A).

Turns one consequential operator command into either a typed ADMIT bound to
the exact existing-authority evidence set, or a typed DENY. Zero side
effects: no I/O, no subprocess, no sockets, no persistence, no retries, no
caches. Existing authorities arrive as an injected frozen bundle
(``GatewayAuthorities``); this module never looks them up, never invokes
them outside ``admit_command``, and never lets an authority exception escape.

Truth rules (WO-P1-603 frozen contract): observed worktree identity is the
only truth (request claims never override observation); scope must be inside
the lease; UNKNOWN dedupe never relaunches; MUTATE requires a fence held by
this claim; read-only actions can never acquire mutation authority; a
malformed request triggers zero authority reads. The evidence digest binds
the admitted tuple so downstream consumers (#498B/D, slice-B dispatch) can
prove they consumed this exact admission — bypassing the gateway implies
nothing and cannot claim guard enforcement.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping, Sequence

from .operator_protocol import (
    OPERATOR_PROTOCOL_VERSION, OperatorAction, OperatorRequest,
)

__all__ = [
    "MutationIntent", "DuplicateDecision", "FenceStatus", "LeaseEvidence",
    "GatewayCommandRequest", "GatewayAuthorities", "GatewayDecision",
    "GatewayAdmission", "admit_command",
]


class MutationIntent(Enum):
    READ_ONLY = "READ_ONLY"
    MUTATE = "MUTATE"


class DuplicateDecision(Enum):
    """Gateway-local view of the execution-dedupe authority outcome."""

    SAFE_TO_LAUNCH = "SAFE_TO_LAUNCH"
    ATTACH_RUNNING = "ATTACH_RUNNING"
    REUSE_COMPLETED = "REUSE_COMPLETED"
    BLOCKED_UNKNOWN = "BLOCKED_UNKNOWN"


class FenceStatus(Enum):
    """Gateway-local view of MSP-2 hotspot fence status for this claim."""

    FENCE_HELD_HERE = "FENCE_HELD_HERE"
    FENCE_OPEN = "FENCE_OPEN"
    FENCE_STALE = "FENCE_STALE"


class GatewayDecision(Enum):
    ADMIT = "ADMIT"
    DENY = "DENY"


# operator.v1 actions partitioned by the authority class they carry.
_MUTATE_ACTIONS = frozenset({
    OperatorAction.JOB_CREATE, OperatorAction.JOB_READY,
    OperatorAction.JOB_CLAIM, OperatorAction.JOB_GATE,
    OperatorAction.JOB_CHECKPOINT, OperatorAction.JOB_EXECUTE,
})
_READ_ONLY_ACTIONS = frozenset({
    OperatorAction.STATUS, OperatorAction.JOB_GET, OperatorAction.JOB_EVENTS,
})

_MAX_REF_CHARS = 256


class _GatewayRuleError(ValueError):
    """Internal typed stop; never escapes admit_command."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


@dataclass(frozen=True)
class LeaseEvidence:
    task_ref: str
    claim_ref: str
    scope: Sequence[str]
    active: bool


@dataclass(frozen=True)
class GatewayCommandRequest:
    request: OperatorRequest
    repo_root: str
    worktree: str
    branch: str
    head_sha: str
    mutation_intent: MutationIntent
    task_ref: str
    claim_ref: str
    fence_ref: str
    requested_scope: Sequence[str]


@dataclass(frozen=True)
class GatewayAuthorities:
    validate_lease: Callable[[str, str, Sequence[str]], LeaseEvidence | None]
    dedupe_decision: Callable[[str], DuplicateDecision]
    observe_worktree: Callable[[str], Mapping[str, str]]
    fence_status: Callable[[str], FenceStatus | None]


@dataclass(frozen=True)
class GatewayAdmission:
    decision: GatewayDecision
    reason_code: str
    action: str
    task_ref: str
    claim_ref: str
    evidence_digest: str

    @property
    def admitted(self) -> bool:
        return self.decision is GatewayDecision.ADMIT


def _plain_ref(value: object) -> bool:
    return (isinstance(value, str) and 0 < len(value) <= _MAX_REF_CHARS
            and value == value.strip()
            and not any(ord(ch) < 32 or ord(ch) == 0x7F for ch in value))


def _validate_shape(request: GatewayCommandRequest) -> None:
    inner = request.request
    if not isinstance(inner, OperatorRequest):
        raise _GatewayRuleError("GATEWAY_REQUEST_MALFORMED")
    if getattr(inner, "protocol_version", None) != OPERATOR_PROTOCOL_VERSION:
        raise _GatewayRuleError("GATEWAY_REQUEST_MALFORMED")
    action = getattr(inner, "action", None)
    if not isinstance(action, OperatorAction):
        raise _GatewayRuleError("GATEWAY_REQUEST_MALFORMED")
    if request.mutation_intent not in MutationIntent:
        raise _GatewayRuleError("GATEWAY_REQUEST_MALFORMED")
    for field in ("repo_root", "branch", "head_sha"):
        if not _plain_ref(getattr(request, field, None)):
            raise _GatewayRuleError("GATEWAY_REQUEST_MALFORMED")
    scope = request.requested_scope
    if (not isinstance(scope, (tuple, list, frozenset))
            or any(not _plain_ref(item) for item in scope)):
        raise _GatewayRuleError("GATEWAY_REQUEST_MALFORMED")
    if request.mutation_intent is MutationIntent.MUTATE:
        # Read-only actions can never carry mutation authority.
        if action in _READ_ONLY_ACTIONS:
            raise _GatewayRuleError("GATEWAY_INTENT_ESCALATION")
        if not _plain_ref(request.task_ref) or not _plain_ref(request.claim_ref):
            raise _GatewayRuleError("GATEWAY_REQUEST_MALFORMED")


def _evidence_digest(request: GatewayCommandRequest, *, fence_ok: bool,
                     lease_scope: Sequence[str]) -> str:
    parts = [
        OPERATOR_PROTOCOL_VERSION,
        request.request.action.value,
        request.mutation_intent.value,
        request.repo_root, request.branch, request.head_sha,
        request.task_ref, request.claim_ref,
        ";".join(sorted(request.requested_scope)),
        ";".join(sorted(lease_scope)),
        "fence" if fence_ok else "nofence",
    ]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _deny(request: GatewayCommandRequest, reason_code: str) -> GatewayAdmission:
    action = getattr(getattr(request, "request", None), "action", None)
    return GatewayAdmission(
        decision=GatewayDecision.DENY,
        reason_code=reason_code,
        action=action.value if isinstance(action, OperatorAction) else "",
        task_ref=request.task_ref,
        claim_ref=request.claim_ref,
        evidence_digest="",
    )


def admit_command(
    request: GatewayCommandRequest, *, authorities: GatewayAuthorities,
) -> GatewayAdmission:
    """Admit or deny one command. Pure; never raises; zero side effects."""
    try:
        _validate_shape(request)
    except _GatewayRuleError as stop:
        return _deny(request, stop.reason_code)
    except Exception:
        return _deny(request, "GATEWAY_REQUEST_MALFORMED")

    intent = request.mutation_intent
    action: OperatorAction = request.request.action

    if intent is MutationIntent.READ_ONLY:
        # Read-only admission still binds identity so results correlate to an
        # observed world, but touches no lease/fence/dedupe authority.
        digest = _evidence_digest(request, fence_ok=False, lease_scope=())
        return GatewayAdmission(
            decision=GatewayDecision.ADMIT, reason_code="GATEWAY_ADMIT_READ_ONLY",
            action=action.value, task_ref=request.task_ref,
            claim_ref=request.claim_ref, evidence_digest=digest)

    # MUTATE path: every authority failure is a typed deny, never an escape.
    try:
        lease = authorities.validate_lease(
            request.claim_ref, request.task_ref, request.requested_scope)
    except Exception:
        lease = None
    if lease is None:
        return _deny(request, "GATEWAY_CLAIM_MISSING")
    if not getattr(lease, "active", False):
        return _deny(request, "GATEWAY_CLAIM_STALE")
    if (getattr(lease, "task_ref", None) != request.task_ref
            or getattr(lease, "claim_ref", None) != request.claim_ref):
        return _deny(request, "GATEWAY_TASK_MISSING")
    lease_scope = tuple(getattr(lease, "scope", ()) or ())
    if not any(_scope_covers(pattern, item)
               for item in request.requested_scope
               for pattern in lease_scope):
        return _deny(request, "GATEWAY_SCOPE_DRIFT")

    try:
        identity = authorities.observe_worktree(request.repo_root)
    except Exception:
        identity = None
    if not isinstance(identity, Mapping):
        return _deny(request, "GATEWAY_IDENTITY_DRIFT")
    if (identity.get("repo_root") != request.repo_root
            or identity.get("branch") != request.branch
            or identity.get("head_sha") != request.head_sha):
        return _deny(request, "GATEWAY_IDENTITY_DRIFT")

    try:
        dedupe = authorities.dedupe_decision(request.task_ref)
    except Exception:
        dedupe = DuplicateDecision.BLOCKED_UNKNOWN
    if dedupe is not DuplicateDecision.SAFE_TO_LAUNCH:
        # UNKNOWN / already-running / already-completed: never relaunch.
        return _deny(request, "GATEWAY_DUPLICATE_UNKNOWN")

    try:
        fence = authorities.fence_status(request.fence_ref)
    except Exception:
        fence = None
    if fence is None:
        return _deny(request, "GATEWAY_FENCE_MISSING")
    if fence is not FenceStatus.FENCE_HELD_HERE:
        return _deny(request, "GATEWAY_FENCE_STALE")

    digest = _evidence_digest(request, fence_ok=True, lease_scope=lease_scope)
    return GatewayAdmission(
        decision=GatewayDecision.ADMIT, reason_code="GATEWAY_ADMIT_MUTATE",
        action=action.value, task_ref=request.task_ref,
        claim_ref=request.claim_ref, evidence_digest=digest)


def _scope_covers(pattern: str, item: str) -> bool:
    """Bounded glob-free prefix match over path-shaped scope patterns."""
    if pattern == item:
        return True
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return item.startswith(prefix) and "/" in item[len(prefix):]
    return False
