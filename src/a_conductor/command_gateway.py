"""WO-P1-603: ACT-1 Command Gateway — pure admission authority (slice A).

Turns one consequential operator command into either a typed ADMIT bound to
the exact existing-authority evidence set, or a typed DENY. Zero side
effects: no I/O, no subprocess, no sockets, no persistence, no retries, no
caches. Existing authorities arrive as an injected frozen bundle
(``GatewayAuthorities``); this module never looks them up, never invokes
them outside ``admit_command``, and never lets ANY exception escape.

Truth rules (WO-P1-603 frozen contract, hardened after independent R3
review round 1):
- effective intent is DERIVED from the operator action class, never from
  the caller's label — a mutate-class action labeled READ_ONLY (or the
  reverse) is an INTENT_ESCALATION deny;
- observed worktree identity (repo_root/worktree/branch/head_sha) is the
  only truth; request claims never override observation;
- requested scope must be UNIVERSALLY covered by the lease scope, with
  component-boundary matching and traversal/absolute rejection;
- authority results are revalidated (exact bool lease.active, plain
  fence_ref) — hostile or malformed evidence fails closed;
- an authority callback that RAISES yields GATEWAY_AUTHORITY_ERROR; one
  that returns absent/stale evidence yields the specific typed deny;
- the evidence digest hashes a canonical length-safe serialization of every
  bound field (request identity fields included), so distinct evidence sets
  cannot collide;
- UNKNOWN dedupe never relaunches; MUTATE requires a fence held here;
- bypassing the gateway implies nothing: only consuming an ADMIT's exact
  digest can claim gateway admission downstream.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping, Sequence

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


# operator.v1 actions partitioned by the authority class they carry. The
# effective intent is derived from THIS table — a caller's label can never
# upgrade or downgrade an action across the authority boundary.
_MUTATE_ACTIONS = frozenset({
    OperatorAction.JOB_CREATE, OperatorAction.JOB_READY,
    OperatorAction.JOB_CLAIM, OperatorAction.JOB_GATE,
    OperatorAction.JOB_CHECKPOINT, OperatorAction.JOB_EXECUTE,
})
_READ_ONLY_ACTIONS = frozenset({
    OperatorAction.STATUS, OperatorAction.JOB_GET, OperatorAction.JOB_EVENTS,
})

_IDENTITY_FIELDS = ("repo_root", "worktree", "branch", "head_sha")
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
    # Surrogate code points are rejected everywhere: ensure_ascii JSON
    # serializes lone surrogates and their escape sequences identically,
    # which would break evidence-digest binding (Sol round-2 P2).
    return (type(value) is str and 0 < len(value) <= _MAX_REF_CHARS
            and value == value.strip()
            and not any(ord(ch) < 32 or ord(ch) == 0x7F for ch in value)
            and not any(0xD800 <= ord(ch) <= 0xDFFF for ch in value))


def _scope_item_safe(item: object) -> bool:
    """Relative, traversal-free, component-clean path-shaped scope item."""
    if not _plain_ref(item):
        return False
    text: str = item  # type: ignore[assignment]
    if text.startswith("/") or text.startswith("\\") or ":" in text:
        return False
    parts = text.replace("\\", "/").split("/")
    return all(part not in ("", ".", "..") for part in parts)


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
    for field in _IDENTITY_FIELDS:
        if not _plain_ref(getattr(request, field, None)):
            raise _GatewayRuleError("GATEWAY_REQUEST_MALFORMED")
    scope = request.requested_scope
    if (not isinstance(scope, (tuple, list, frozenset))
            or any(not _scope_item_safe(item) for item in scope)):
        raise _GatewayRuleError("GATEWAY_REQUEST_MALFORMED")
    effective_mutate = action in _MUTATE_ACTIONS
    labeled_mutate = request.mutation_intent is MutationIntent.MUTATE
    if effective_mutate != labeled_mutate:
        # The caller's label contradicts the action's authority class:
        # neither direction of relabeling may cross the boundary.
        raise _GatewayRuleError("GATEWAY_INTENT_ESCALATION")
    if labeled_mutate:
        if not _plain_ref(request.task_ref) or not _plain_ref(request.claim_ref):
            raise _GatewayRuleError("GATEWAY_REQUEST_MALFORMED")
    elif not isinstance(request.task_ref, str) or not isinstance(request.claim_ref, str):
        # READ_ONLY still requires string fields (may be empty).
        raise _GatewayRuleError("GATEWAY_REQUEST_MALFORMED")


def _deny(request: GatewayCommandRequest, reason_code: str) -> GatewayAdmission:
    # Reading ANY untrusted attribute can raise (hostile property objects),
    # so every projection here is individually bounded; _deny never raises.
    try:
        action = getattr(getattr(request, "request", None), "action", None)
    except Exception:
        action = None
    try:
        task_ref = getattr(request, "task_ref", "")
    except Exception:
        task_ref = ""
    try:
        claim_ref = getattr(request, "claim_ref", "")
    except Exception:
        claim_ref = ""
    return GatewayAdmission(
        decision=GatewayDecision.DENY,
        reason_code=reason_code,
        action=action.value if isinstance(action, OperatorAction) else "",
        task_ref=task_ref if isinstance(task_ref, str) else "",
        claim_ref=claim_ref if isinstance(claim_ref, str) else "",
        evidence_digest="",
    )


def _evidence_parts(request: GatewayCommandRequest, *, fence_ok: bool,
                    lease_scope: Sequence[str]) -> list[Any]:
    inner = request.request
    return [
        OPERATOR_PROTOCOL_VERSION,
        inner.action.value,
        request.mutation_intent.value,
        request.repo_root, request.worktree, request.branch, request.head_sha,
        request.task_ref, request.claim_ref, request.fence_ref,
        inner.job_id, inner.operation_ref, inner.evidence_ref,
        inner.checkpoint_ref, inner.work_order_ref, inner.project_id,
        inner.worker_id, inner.expected_version, inner.max_attempts,
        sorted(request.requested_scope),
        sorted(lease_scope),
        "fence" if fence_ok else "nofence",
    ]


def _evidence_digest(request: GatewayCommandRequest, *, fence_ok: bool,
                     lease_scope: Sequence[str]) -> str:
    # Canonical JSON serialization: every field present, string escaping
    # prevents separator-injection collisions, sorted lists are stable.
    payload = json.dumps(
        _evidence_parts(request, fence_ok=fence_ok, lease_scope=lease_scope),
        sort_keys=False, ensure_ascii=True, separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _scope_covers(pattern: object, item: str) -> bool:
    """Component-boundary coverage; traversal was rejected at validation."""
    if type(pattern) is not str or not _scope_item_safe(pattern):
        return False  # hostile lease scope item never covers anything
    if pattern == item:
        return True
    if pattern.endswith("/**"):
        prefix = pattern[:-2]  # keep the trailing slash: "src/x/" boundary
        return item.startswith(prefix)
    return False


def admit_command(
    request: GatewayCommandRequest, *, authorities: GatewayAuthorities,
) -> GatewayAdmission:
    """Admit or deny one command. Pure; never raises; zero side effects."""
    try:
        return _admit_inner(request, authorities=authorities)
    except _GatewayRuleError as stop:
        return _deny(request, stop.reason_code)
    except Exception:
        # Unknown malformed shape (including None/foreign objects): the
        # outer boundary is fail-closed, never an escape.
        return _deny(request, "GATEWAY_REQUEST_MALFORMED")


def _admit_inner(
    request: GatewayCommandRequest, *, authorities: GatewayAuthorities,
) -> GatewayAdmission:
    _validate_shape(request)
    action: OperatorAction = request.request.action

    if action in _READ_ONLY_ACTIONS:
        digest = _evidence_digest(request, fence_ok=False, lease_scope=())
        return GatewayAdmission(
            decision=GatewayDecision.ADMIT,
            reason_code="GATEWAY_ADMIT_READ_ONLY",
            action=action.value, task_ref=request.task_ref,
            claim_ref=request.claim_ref, evidence_digest=digest)

    # ---- MUTATE path: a callback that RAISES, or returns evidence whose
    # processing itself raises, is GATEWAY_AUTHORITY_ERROR (WO row h);
    # absent/stale-but-well-formed evidence gets its specific typed deny.
    try:
        lease = authorities.validate_lease(
            request.claim_ref, request.task_ref, request.requested_scope)
        if isinstance(lease, LeaseEvidence):
            # Touch every consumed field here so hostile evidence objects
            # fail inside this boundary, not during later digest work.
            _ = bool(lease.active), str(lease.task_ref), str(lease.claim_ref)
            _ = tuple(lease.scope)
    except Exception:
        return _deny(request, "GATEWAY_AUTHORITY_ERROR")
    if not isinstance(lease, LeaseEvidence):
        return _deny(request, "GATEWAY_CLAIM_MISSING")
    try:
        if type(lease.active) is not bool:  # exact bool: "False"/1 never pass
            return _deny(request, "GATEWAY_CLAIM_STALE")
        if not lease.active:
            return _deny(request, "GATEWAY_CLAIM_STALE")
        if (lease.task_ref != request.task_ref
                or lease.claim_ref != request.claim_ref):
            return _deny(request, "GATEWAY_TASK_MISSING")
        lease_scope = tuple(lease.scope)
    except Exception:
        # Hostile evidence objects (raising __eq__/iterators) are authority
        # failures, not shape problems (Sol round-2 P2).
        return _deny(request, "GATEWAY_AUTHORITY_ERROR")
    if any(not _scope_item_safe(item) for item in lease_scope):
        return _deny(request, "GATEWAY_SCOPE_DRIFT")
    # UNIVERSAL coverage: every requested item must be inside the lease.
    if not all(any(_scope_covers(pattern, item) for pattern in lease_scope)
               for item in request.requested_scope):
        return _deny(request, "GATEWAY_SCOPE_DRIFT")

    try:
        identity = authorities.observe_worktree(request.repo_root)
        observed = {}
        if isinstance(identity, Mapping):
            for field in _IDENTITY_FIELDS:
                observed[field] = identity.get(field)
    except Exception:
        # Hostile evidence (e.g. a mapping whose .get raises) is an
        # authority-produced failure, not a drift observation.
        return _deny(request, "GATEWAY_AUTHORITY_ERROR")
    if not isinstance(identity, Mapping):
        return _deny(request, "GATEWAY_IDENTITY_DRIFT")
    if any(not _plain_ref(observed[field]) for field in _IDENTITY_FIELDS):
        return _deny(request, "GATEWAY_IDENTITY_DRIFT")
    if any(observed[field] != getattr(request, field)
           for field in _IDENTITY_FIELDS):
        return _deny(request, "GATEWAY_IDENTITY_DRIFT")

    try:
        dedupe = authorities.dedupe_decision(request.task_ref)
    except Exception:
        return _deny(request, "GATEWAY_AUTHORITY_ERROR")
    if dedupe is not DuplicateDecision.SAFE_TO_LAUNCH:
        # UNKNOWN / already-running / already-completed: never relaunch.
        return _deny(request, "GATEWAY_DUPLICATE_UNKNOWN")

    if not _plain_ref(request.fence_ref):
        return _deny(request, "GATEWAY_FENCE_MISSING")
    try:
        fence = authorities.fence_status(request.fence_ref)
    except Exception:
        return _deny(request, "GATEWAY_AUTHORITY_ERROR")
    if fence is None:
        return _deny(request, "GATEWAY_FENCE_MISSING")
    if fence is not FenceStatus.FENCE_HELD_HERE:
        return _deny(request, "GATEWAY_FENCE_STALE")

    digest = _evidence_digest(request, fence_ok=True, lease_scope=lease_scope)
    return GatewayAdmission(
        decision=GatewayDecision.ADMIT, reason_code="GATEWAY_ADMIT_MUTATE",
        action=action.value, task_ref=request.task_ref,
        claim_ref=request.claim_ref, evidence_digest=digest)
