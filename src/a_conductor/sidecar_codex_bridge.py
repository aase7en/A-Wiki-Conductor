"""WO-P1-573 / Issue #573 — A-Sidecar Phase 2 Codex bridge (pure module).

Deterministic control-plane projection/receipt helper that makes the
Phase 0 contract (``docs/contracts/a-sidecar-relay-v1.md``) and the
Phase 1 carrier (``src/a_conductor/sidecar_relay.py``) usable together
for one ordinary sidecar turn. The module itself never talks to Codex:
it performs no socket, HTTP, subprocess, or native IPC operations, and
never opens, reads, or mutates Codex SQLite/session/lock files, not
even read-only. All Codex interaction goes through one caller-injected
transport callable that represents supported Desktop-managed Codex App
Server / native queue APIs; the bridge validates inputs, builds
pointer-only payloads, invokes that seam, and classifies what returns.
It never discovers or probes the surface itself.

Authority model (unchanged by this module):

- A-Conductor remains the sole task/claim/WIP/mutation/review/merge/
  completion authority; A-Relay remains evidence transport only.
- An event is a receipt, never a command. Revalidation rebinds a
  candidate against caller-supplied live binding facts and fails
  closed: the event was never a command.
- Operator/requested target ids are context, never existence proof;
  only the injected transport's observation resolves a target, and
  that observation is transport evidence, not authority.
- ACK receipts are observed-and-folded transport evidence, never
  approval and never completion.
- An ambiguous submission outcome is preserved as uncertainty
  (``DELIVERY_UNKNOWN``) and never retried blindly; durable
  thread/execution evidence must be recovered first
  (codex-nightshift-resume-adapter-v1 precedent).

Durable state goes only through the carrier's public functions
(read/dedupe/order/append); this module adds no second store,
scheduler, task router, claim/lease system, retry engine, review
path, or completion state machine.

Lifecycle (WO §8), projected onto pure helpers:

1. checkpoint recovery — :func:`recover_checkpoint` selects the
   latest ``SIDECAR_CHECKPOINT`` lane binding from events read
   through the carrier (prior-chat memory is never evidence);
2. candidate selection — :func:`select_steer_candidate` picks at
   most one eligible ``CODEX_STEER_REQUEST`` in deterministic
   per-producer carrier order (transport choice, not prioritization
   authority);
3. revalidation — :func:`revalidate_candidate` compares the
   candidate's binding tuple against caller-supplied live facts;
4. surface gate — :func:`validate_surface_version` verifies the
   caller-declared surface descriptor against the caller-supplied
   allowlist/prefix set. The initial proven Desktop-managed App
   Server version ``0.158.0-alpha.2.1`` is recorded here as WO
   evidence (``INITIAL_PROVEN_SURFACE_VERSION``) and is never
   implicit authority: without the caller allowlisting it, nothing
   verifies;
5. pointer projection — :func:`build_steer_projection` produces a
   bounded pointer-only payload (event id, task/claim ids, durable
   evidence refs); the bridge never composes prompts or commands;
6. connector observation + submission —
   :func:`project_steer_candidate` drives the injected transport
   once per phase and classifies the result;
7. receipt — :func:`build_ack_receipt` builds one normal
   ``SIDECAR_RESULT_RECEIPT`` envelope whose ``EVIDENCE_REFS``
   include ``relay-event:<original EVENT_ID>`` plus the durable
   destinations of any harvested result;
   :func:`emit_receipt` appends it through the carrier's public
   append path (the only filesystem write this module can reach);
8. deferral helpers — :func:`build_context_pressure_event` and
   :func:`build_gpt_work_limited_event` build the typed observability
   events for context-pressure / quota-limited deferral.

Failure taxonomy: bridge failures raise :class:`BridgeFailureError`
with exactly the WO §9 code set
(``BRIDGE_SURFACE_UNAVAILABLE``, ``BRIDGE_SURFACE_VERSION_UNVERIFIED``,
``BRIDGE_SURFACE_OFFLINE``, ``BRIDGE_ACTIVE_WRITER``,
``BRIDGE_DUPLICATE_PROJECTION``, ``BRIDGE_AMBIGUOUS_TARGET``,
``BRIDGE_NOT_STEERABLE``, ``BRIDGE_CONTEXT_PRESSURE``,
``BRIDGE_QUOTA_LIMITED``, ``BRIDGE_POINTER_INVALID``). Revalidation
reuses the existing caller-gate codes ``CONTEXT_DRIFT`` /
``CLAIM_CONFLICT``; malformed relay input reuses carrier
``RELAY_*`` codes. All failures are code-only (never echo field
values) and default to fail-closed: no projection, no receipt.

Transport seam contract (caller-injected, treated as untrusted I/O):

- ``transport("observe", {"target_hint": ..., "original_event_id":
  ...})`` must return a mapping with boolean ``reachable``,
  ``target_resolved``, ``active_writer``, ``steerable`` and optional
  safe-text ``thread_id``. Unreachable/garbage maps to
  ``BRIDGE_SURFACE_OFFLINE``; unresolved or unsafe identity maps to
  ``BRIDGE_AMBIGUOUS_TARGET``; ``active_writer`` refuses projection;
  a non-steerable target blocks it;
- ``transport("submit", <pointer-only payload mapping>)`` must return
  a mapping with ``delivery`` in {"DELIVERED", "REJECTED"} plus
  optional safe-text ``thread_id`` / ``queue_ref``. Anything else —
  exceptions included — classifies as ``DELIVERY_UNKNOWN`` and the
  module performs no further submission.

Cross-device rules: WORKTREE/path values are opaque device-tagged
evidence. They are compared as exact text only, never resolved,
normalized, case-folded, or checked against the local device, and a
mismatch fails closed as ``CONTEXT_DRIFT``.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable

from a_conductor import sidecar_relay as sr

STEER_REQUEST_FAMILY = "CODEX_STEER_REQUEST"
CHECKPOINT_FAMILY = "SIDECAR_CHECKPOINT"
RESULT_RECEIPT_FAMILY = "SIDECAR_RESULT_RECEIPT"
CONTEXT_PRESSURE_FAMILY = "CONTEXT_PRESSURE_HIGH"
GPT_WORK_LIMITED_FAMILY = "GPT_WORK_LIMITED"
RELAY_EVENT_REF_PREFIX = "relay-event:"
SIDECAR_SURFACE = "chatgpt-sidecar"

SUPPORTED_SURFACE_KINDS = frozenset({"desktop-app-server", "codex-native-queue"})

INITIAL_PROVEN_SURFACE_VERSION = "0.158.0-alpha.2.1"

BRIDGE_FAILURE_CODES = frozenset(
    {
        "BRIDGE_SURFACE_UNAVAILABLE",
        "BRIDGE_SURFACE_VERSION_UNVERIFIED",
        "BRIDGE_SURFACE_OFFLINE",
        "BRIDGE_ACTIVE_WRITER",
        "BRIDGE_DUPLICATE_PROJECTION",
        "BRIDGE_AMBIGUOUS_TARGET",
        "BRIDGE_NOT_STEERABLE",
        "BRIDGE_CONTEXT_PRESSURE",
        "BRIDGE_QUOTA_LIMITED",
        "BRIDGE_POINTER_INVALID",
    }
)

DELIVERY_DELIVERED = "DELIVERED"
DELIVERY_REJECTED = "REJECTED"
DELIVERY_UNKNOWN = "DELIVERY_UNKNOWN"

_UNSAFE_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co"})
_VERSION_RE = re.compile(r"[0-9A-Za-z][0-9A-Za-z._+-]{0,63}")
_MAX_IDENTITY_TEXT = 256


class BridgeFailureError(RuntimeError):
    """Stable code-only bridge failure; never echoes field values."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class SurfaceDescriptor:
    """Caller-declared supported Codex surface evidence.

    The bridge never probes the device: presence, kind, and version
    are caller/WO-declared evidence validated against the
    caller-supplied accepted version/prefix set only.
    """

    surface_kind: str
    version: str | None = None


@dataclass(frozen=True, slots=True)
class LiveBindingFacts:
    """Caller-supplied live binding facts for revalidation.

    Facts the caller cannot prove live are ``None`` and are skipped;
    every supplied fact must match the candidate event exactly
    (opaque text comparison, no path normalization). The bridge is
    not the source of these facts and never becomes their authority.
    """

    repo: str | None = None
    worktree: str | None = None
    head_sha: str | None = None
    task_id: str | None = None
    claim_id: str | None = None


@dataclass(frozen=True, slots=True)
class SteerProjection:
    """Bounded pointer-only steer payload for one relay event."""

    original_event_id: str
    task_id: str
    claim_id: str
    evidence_refs: tuple[str, ...]

    def to_pointer_mapping(self) -> dict:
        return {
            "EVENT_ID": self.original_event_id,
            "TASK_ID": self.task_id,
            "CLAIM_ID": self.claim_id,
            "EVIDENCE_REFS": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ProjectionOutcome:
    """Classified result of one at-most-once projection attempt."""

    original_event_id: str
    delivery: str
    observed_thread_id: str | None = None
    observed_queue_ref: str | None = None


def _is_safe_text(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    for character in value:
        if unicodedata.category(character) in _UNSAFE_CATEGORIES:
            return False
    return True


def _safe_version(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    if _VERSION_RE.fullmatch(value) is None:
        return None
    return value


def dedupe_events(
    events: Iterable[sr.RelayEnvelope],
) -> tuple[sr.RelayEnvelope, ...]:
    """Deduplicate relay envelopes on EVENT_ID (first occurrence wins).

    The carrier already deduplicates on read; this is the defensive
    consumer boundary required by the contract's at-least-once
    delivery. Non-envelope input fails closed with the carrier code.
    """
    deduped: list[sr.RelayEnvelope] = []
    seen: set[str] = set()
    for envelope in events:
        if not isinstance(envelope, sr.RelayEnvelope):
            raise sr.RelayCarrierError("RELAY_ENVELOPE_INVALID")
        if envelope.event_id not in seen:
            seen.add(envelope.event_id)
            deduped.append(envelope)
    return tuple(deduped)


def recover_checkpoint(
    events: Iterable[sr.RelayEnvelope],
) -> sr.RelayEnvelope | None:
    """Recover the latest ``SIDECAR_CHECKPOINT`` lane binding.

    Deterministic: newest by CREATED_AT instant with EVENT_ID as the
    tie-break, independent of arrival order. Returns ``None`` when
    the log carries no checkpoint.
    """
    checkpoints = [
        envelope
        for envelope in dedupe_events(events)
        if envelope.event_type == CHECKPOINT_FAMILY
    ]
    if not checkpoints:
        return None

    def chronology(envelope: sr.RelayEnvelope) -> tuple[datetime, str]:
        try:
            instant = datetime.fromisoformat(envelope.created_at)
        except ValueError:
            raise sr.RelayCarrierError("RELAY_ENVELOPE_INVALID") from None
        return (instant, envelope.event_id)

    return max(checkpoints, key=chronology)


def select_steer_candidate(
    events: Iterable[sr.RelayEnvelope],
) -> sr.RelayEnvelope | None:
    """Select at most one eligible ``CODEX_STEER_REQUEST`` candidate.

    Deterministic per-producer carrier order (contract §5); the first
    event in that order wins regardless of arrival order. Selection
    is transport choice, not prioritization authority.
    """
    candidates = [
        envelope
        for envelope in dedupe_events(events)
        if envelope.event_type == STEER_REQUEST_FAMILY
    ]
    if not candidates:
        return None
    return sr.order_events(candidates)[0]


def projected_event_ids(
    events: Iterable[sr.RelayEnvelope],
) -> frozenset[str]:
    """Derive already-acknowledged original event ids from the log.

    A ``SIDECAR_RESULT_RECEIPT`` whose ``EVIDENCE_REFS`` carry
    ``relay-event:<EVENT_ID>`` is the durable marker that the original
    event was observed, folded, and already projected; replaying it
    must fail typed instead of double-submitting.
    """
    projected: set[str] = set()
    for envelope in dedupe_events(events):
        if envelope.event_type != RESULT_RECEIPT_FAMILY:
            continue
        for ref in envelope.evidence_refs:
            if ref.startswith(RELAY_EVENT_REF_PREFIX):
                origin = ref[len(RELAY_EVENT_REF_PREFIX) :]
                if origin:
                    projected.add(origin)
    return frozenset(projected)


def revalidate_candidate(
    candidate: sr.RelayEnvelope,
    facts: LiveBindingFacts | None,
) -> None:
    """Rebind one steer candidate against caller-supplied live facts.

    Missing facts fail closed as ``CONTEXT_DRIFT`` (the caller context
    could not be bound); an unbound candidate fails closed as
    ``BRIDGE_POINTER_INVALID``. Each supplied fact must equal the
    event's binding value exactly (opaque text, no normalization);
    repo/worktree/HEAD/task mismatches are ``CONTEXT_DRIFT`` (stale
    or unbound) and a claim mismatch is ``CLAIM_CONFLICT``. The event
    was never a command, so every mismatch simply refuses projection.
    """
    if not isinstance(facts, LiveBindingFacts):
        raise BridgeFailureError("CONTEXT_DRIFT")
    if any(
        getattr(candidate, field) is None
        for field in ("task_id", "claim_id", "repo", "worktree", "head_sha")
    ):
        raise BridgeFailureError("BRIDGE_POINTER_INVALID")
    for field, mismatch_code in (
        ("repo", "CONTEXT_DRIFT"),
        ("worktree", "CONTEXT_DRIFT"),
        ("head_sha", "CONTEXT_DRIFT"),
        ("task_id", "CONTEXT_DRIFT"),
        ("claim_id", "CLAIM_CONFLICT"),
    ):
        live = getattr(facts, field)
        if live is None:
            continue
        if live != getattr(candidate, field):
            raise BridgeFailureError(mismatch_code)


def validate_surface_version(
    surface: SurfaceDescriptor | None,
    *,
    accepted_versions: Iterable[str],
    accepted_prefixes: Iterable[str],
) -> None:
    """Verify the caller-declared surface against the caller allowlist.

    Missing/unsupported surface kinds are ``BRIDGE_SURFACE_UNAVAILABLE``.
    A missing, malformed, or non-allowlisted declared version is
    ``BRIDGE_SURFACE_VERSION_UNVERIFIED``. Version authority is exactly
    the caller-supplied accepted version/prefix set: entries that do
    not match the bounded version grammar are dropped, and an empty or
    fully-malformed allowlist verifies nothing. The module never probes
    private storage and never treats
    ``INITIAL_PROVEN_SURFACE_VERSION`` as implicit authority.
    """
    if not isinstance(surface, SurfaceDescriptor):
        raise BridgeFailureError("BRIDGE_SURFACE_UNAVAILABLE")
    if surface.surface_kind not in SUPPORTED_SURFACE_KINDS:
        raise BridgeFailureError("BRIDGE_SURFACE_UNAVAILABLE")
    declared = _safe_version(surface.version)
    accepted = {
        version
        for version in (_safe_version(item) for item in accepted_versions)
        if version is not None
    }
    prefixes = {
        prefix
        for prefix in (_safe_version(item) for item in accepted_prefixes)
        if prefix is not None
    }
    if declared is None or not accepted and not prefixes:
        raise BridgeFailureError("BRIDGE_SURFACE_VERSION_UNVERIFIED")
    if declared in accepted:
        return
    for prefix in sorted(prefixes):
        if declared.startswith(prefix):
            return
    raise BridgeFailureError("BRIDGE_SURFACE_VERSION_UNVERIFIED")


def build_steer_projection(candidate: sr.RelayEnvelope) -> SteerProjection:
    """Build the bounded pointer-only steer payload for one candidate.

    The payload carries only the original event id, task/claim ids,
    and the candidate's durable evidence refs. A candidate without
    durable evidence pointers, or one whose refs are not durable
    pointers, fails closed as ``BRIDGE_POINTER_INVALID``. No free-form
    or executable body is ever composed.
    """
    refs = tuple(candidate.evidence_refs)
    if not refs or candidate.task_id is None or candidate.claim_id is None:
        raise BridgeFailureError("BRIDGE_POINTER_INVALID")
    for ref in refs:
        if not isinstance(ref, str) or "://" in ref or not ref.strip():
            raise BridgeFailureError("BRIDGE_POINTER_INVALID")
    return SteerProjection(
        original_event_id=candidate.event_id,
        task_id=candidate.task_id,
        claim_id=candidate.claim_id,
        evidence_refs=refs[: sr.MAX_EVIDENCE_REFS],
    )


def _identity_text(mapping: dict, key: str) -> str | None:
    value = mapping.get(key)
    if value is None:
        return None
    if not _is_safe_text(value) or len(value) > _MAX_IDENTITY_TEXT:
        raise BridgeFailureError("BRIDGE_AMBIGUOUS_TARGET")
    return value


def _classify_observation(observation: object) -> str | None:
    """Classify one read-only connector observation.

    Unreachable or malformed observations are ``BRIDGE_SURFACE_OFFLINE``;
    an unresolved or text-unsafe target identity is
    ``BRIDGE_AMBIGUOUS_TARGET``; an active writer refuses projection;
    a non-steerable target blocks it. Returns the observed thread id
    when projection may proceed.
    """
    if not isinstance(observation, dict):
        raise BridgeFailureError("BRIDGE_SURFACE_OFFLINE")
    if observation.get("reachable") is not True:
        raise BridgeFailureError("BRIDGE_SURFACE_OFFLINE")
    if observation.get("target_resolved") is not True:
        raise BridgeFailureError("BRIDGE_AMBIGUOUS_TARGET")
    observed_thread = _identity_text(observation, "thread_id")
    if observation.get("active_writer") is True:
        raise BridgeFailureError("BRIDGE_ACTIVE_WRITER")
    if observation.get("steerable") is not True:
        raise BridgeFailureError("BRIDGE_NOT_STEERABLE")
    return observed_thread


def _submit_delivery(response: object) -> tuple[str, str | None, str | None]:
    """Classify one submission response, preserving uncertainty.

    Only ``DELIVERED`` / ``REJECTED`` with safe-text evidence are
    trusted; every other shape (including exceptions caught by the
    caller of the transport) classifies as ``DELIVERY_UNKNOWN`` so the
    ambiguity is preserved instead of retried.
    """
    if not isinstance(response, dict):
        return (DELIVERY_UNKNOWN, None, None)
    try:
        thread_id = _identity_text(response, "thread_id")
        queue_ref = _identity_text(response, "queue_ref")
    except BridgeFailureError:
        return (DELIVERY_UNKNOWN, None, None)
    delivery = response.get("delivery")
    if delivery == DELIVERY_DELIVERED:
        return (DELIVERY_DELIVERED, thread_id, queue_ref)
    if delivery == DELIVERY_REJECTED:
        return (DELIVERY_REJECTED, thread_id, queue_ref)
    return (DELIVERY_UNKNOWN, None, None)


def project_steer_candidate(
    events: Iterable[sr.RelayEnvelope],
    *,
    facts: LiveBindingFacts | None,
    surface: SurfaceDescriptor | None = None,
    accepted_versions: Iterable[str] = (),
    accepted_prefixes: Iterable[str] = (),
    transport: Callable[[str, dict], object] | None = None,
    target_hint: str | None = None,
    context_pressure: bool = False,
    quota_limited: bool = False,
) -> ProjectionOutcome | None:
    """Run one bounded steer-projection turn over recovered events.

    Gate order (WO §8): deduped recovery, candidate selection, typed
    duplicate refusal on already-acknowledged original EVENT_IDs,
    fail-closed revalidation, context-pressure/quota deferral, surface
    presence + version verification, pointer-only payload build, one
    read-only observation, then at most one submission. Returns
    ``None`` when no eligible candidate exists. The module performs no
    retry of any kind: an uncertain delivery is returned as
    ``DELIVERY_UNKNOWN`` for durable-evidence recovery by the caller.
    """
    deduped = dedupe_events(events)
    candidate = select_steer_candidate(deduped)
    if candidate is None:
        return None
    if candidate.event_id in projected_event_ids(deduped):
        raise BridgeFailureError("BRIDGE_DUPLICATE_PROJECTION")
    revalidate_candidate(candidate, facts)
    if context_pressure:
        raise BridgeFailureError("BRIDGE_CONTEXT_PRESSURE")
    if quota_limited:
        raise BridgeFailureError("BRIDGE_QUOTA_LIMITED")
    if surface is None or transport is None:
        raise BridgeFailureError("BRIDGE_SURFACE_UNAVAILABLE")
    validate_surface_version(
        surface,
        accepted_versions=accepted_versions,
        accepted_prefixes=accepted_prefixes,
    )
    projection = build_steer_projection(candidate)
    hint = target_hint if target_hint is not None else candidate.source_thread_id
    if hint is None or not _is_safe_text(hint) or len(hint) > _MAX_IDENTITY_TEXT:
        raise BridgeFailureError("BRIDGE_AMBIGUOUS_TARGET")
    try:
        observation = transport(
            "observe",
            {
                "target_hint": hint,
                "original_event_id": candidate.event_id,
            },
        )
        observed_thread = _classify_observation(observation)
    except BridgeFailureError:
        raise
    except Exception:
        raise BridgeFailureError("BRIDGE_SURFACE_OFFLINE") from None
    try:
        response = transport("submit", projection.to_pointer_mapping())
    except Exception:
        return ProjectionOutcome(
            original_event_id=candidate.event_id,
            delivery=DELIVERY_UNKNOWN,
        )
    delivery, thread_id, queue_ref = _submit_delivery(response)
    return ProjectionOutcome(
        original_event_id=candidate.event_id,
        delivery=delivery,
        observed_thread_id=thread_id if thread_id is not None else observed_thread,
        observed_queue_ref=queue_ref,
    )


def build_ack_receipt(
    original_event: sr.RelayEnvelope,
    *,
    source_thread_id: str,
    source_turn_id: str,
    created_at: str,
    result_refs: Iterable[str] = (),
    event_id: str | None = None,
) -> sr.RelayEnvelope:
    """Build the observed-and-folded ACK for one relay event.

    One normal ``SIDECAR_RESULT_RECEIPT`` envelope whose
    ``EVIDENCE_REFS`` start with ``relay-event:<original EVENT_ID>``
    followed by the durable destinations of any harvested result. The
    receipt inherits the original event's lane binding, is built and
    validated through the carrier, and means observed and folded —
    never approved, never completed.
    """
    if not isinstance(original_event, sr.RelayEnvelope):
        raise BridgeFailureError("BRIDGE_POINTER_INVALID")
    binding = {
        "TASK_ID": original_event.task_id,
        "CLAIM_ID": original_event.claim_id,
        "REPO": original_event.repo,
        "WORKTREE": original_event.worktree,
        "HEAD_SHA": original_event.head_sha,
    }
    if any(value is None for value in binding.values()):
        raise BridgeFailureError("BRIDGE_POINTER_INVALID")
    refs = [f"{RELAY_EVENT_REF_PREFIX}{original_event.event_id}"]
    for ref in result_refs:
        if not isinstance(ref, str) or "://" in ref or not ref.strip():
            raise BridgeFailureError("BRIDGE_POINTER_INVALID")
        refs.append(ref)
    payload = {
        "EVENT_ID": event_id
        if event_id is not None
        else sr.mint_event_id(SIDECAR_SURFACE),
        "EVENT_TYPE": RESULT_RECEIPT_FAMILY,
        "SOURCE_SURFACE": SIDECAR_SURFACE,
        "SOURCE_THREAD_ID": source_thread_id,
        "SOURCE_TURN_ID": source_turn_id,
        "CREATED_AT": created_at,
        "EVIDENCE_REFS": refs,
    }
    payload.update(binding)
    return sr.envelope_from_mapping(payload)


def emit_receipt(log_path: object, receipt: sr.RelayEnvelope) -> None:
    """Append one receipt through the carrier's public append path.

    This is the module's only reachable filesystem write, and it is
    the carrier's own append semantics (idempotent byte-identical
    redelivery, typed duplicate refusal, append-only JSONL).
    """
    sr.append_event(log_path, receipt)


def _observability_event(
    event_type: str,
    *,
    source_thread_id: str,
    source_turn_id: str,
    created_at: str,
    event_id: str | None,
) -> sr.RelayEnvelope:
    payload = {
        "EVENT_ID": event_id
        if event_id is not None
        else sr.mint_event_id(SIDECAR_SURFACE),
        "EVENT_TYPE": event_type,
        "SOURCE_SURFACE": SIDECAR_SURFACE,
        "SOURCE_THREAD_ID": source_thread_id,
        "SOURCE_TURN_ID": source_turn_id,
        "CREATED_AT": created_at,
    }
    return sr.envelope_from_mapping(payload)


def build_context_pressure_event(
    *,
    source_thread_id: str,
    source_turn_id: str,
    created_at: str,
    event_id: str | None = None,
) -> sr.RelayEnvelope:
    """Build one ``CONTEXT_PRESSURE_HIGH`` deferral event."""
    return _observability_event(
        CONTEXT_PRESSURE_FAMILY,
        source_thread_id=source_thread_id,
        source_turn_id=source_turn_id,
        created_at=created_at,
        event_id=event_id,
    )


def build_gpt_work_limited_event(
    *,
    source_thread_id: str,
    source_turn_id: str,
    created_at: str,
    event_id: str | None = None,
) -> sr.RelayEnvelope:
    """Build one ``GPT_WORK_LIMITED`` deferral event."""
    return _observability_event(
        GPT_WORK_LIMITED_FAMILY,
        source_thread_id=source_thread_id,
        source_turn_id=source_turn_id,
        created_at=created_at,
        event_id=event_id,
    )
