"""WO-P1-223 RE1 — verdict-blind reviewer execution verification + promotion.

Closes the RE-1 production reachability gap without weakening fail-closed
C1: the accepted ZRA-1 supervised transport durably lands every exit-0
reviewer run in ``VERIFICATION_REQUIRED`` (supervised collect semantics),
while C1 acceptance eligibility requires ``SUCCEEDED``. This module proves
the durable execution truth — exact runtime execution id, artifact refs,
complete non-truncated stdout/report raw bytes, strict ``zcode-report/1``
schema, task packet SHA, response byte count/hash, durable ``exit_code=0``
and source state — and then performs exactly ONE existing-store
version-CAS promotion ``(VERIFICATION_REQUIRED, N) -> (SUCCEEDED, N+1)``.

This verifier is verdict-blind: it NEVER parses semantic review verdicts
and NEVER creates review evidence — C1 (``zero_relay_review_evidence``)
remains the sole semantic authority and its fail-closed behavior is
unchanged. There is no new store, service or lifecycle authority here:
reads go through the existing ``ExecutionArtifactService`` and the
existing execution-store API, and the report vocabulary/slice verification
are reused from the accepted C1 module as-is.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from .execution_artifacts import (
    ExecutionArtifactError,
    ExecutionArtifactKind,
    ExecutionArtifactService,
    MAX_ARTIFACT_READ_BYTES,
)
from .execution_record import DurableExecutionRecord, ExecutionProcessState
from .execution_store import ExecutionEventType, ExecutionStoreError
# Verdict-blind primitives reused from the accepted C1 module (single
# report-vocabulary/slice-verification authority — never re-implemented
# here). C1 imports this package's execution module, so this import order
# is safe only because the execution bridge imports THIS module lazily.
from .zero_relay_review_evidence import (  # noqa: F401 - re-exported authority
    ZeroRelayReviewEvidenceError,
    _parse_zcode_report,
    _verify_complete_artifact,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTITY_HEAD_RE = re.compile(r"^[0-9a-f]{7,64}$")
_PROMOTION_EVIDENCE_PREFIX = "zra2-review-verification"
_PROMOTION_EVIDENCE_PREFIX_V2 = "zra2-review-verification-v2"
_MAX_PROMOTION_EVIDENCE_CHARS = 2048
_MAX_IDENTITY_GENERATION = 10 ** 9
# the only durable source states a promotion may start from: the accepted
# supervised exit-0 terminal state, or an already-promoted replay
_PROMOTABLE_SOURCE_STATES = frozenset(
    {
        ExecutionProcessState.VERIFICATION_REQUIRED,
        ExecutionProcessState.SUCCEEDED,
    }
)


class ZeroRelayReviewVerificationError(RuntimeError):
    """Stable typed failure; never exposes untrusted artifact content."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class VerifiedReviewExecution:
    """Post-verification durable truth: the (possibly promoted) record."""

    record: DurableExecutionRecord
    promoted: bool


# ---------------- strict versioned promotion resource identity (RE2-A) ----
#
# The SUCCEEDED promotion event's evidence_ref may carry the exact original
# resource identity of the reviewer attempt: the original lease/admission
# locators plus every cross-binding fact needed to prove later — by exact id
# and through existing historical APIs — that the pointed-at rows belonged
# to THIS attempt. Bounded, deterministic, unambiguous, fail-closed.


def _identity_invalid() -> ZeroRelayReviewVerificationError:
    return ZeroRelayReviewVerificationError("REVIEW_PROMOTION_IDENTITY_INVALID")


def _require_identity_text(value, field: str, limit: int) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > limit
        or "\x00" in value
    ):
        raise _identity_invalid()
    return value


@dataclass(frozen=True, slots=True)
class ReviewPromotionResourceIdentity:
    """Exact original resource identity persisted at the promotion CAS."""

    execution_id: str
    review_contract_ref: str
    review_task_sha256: str
    worker_id: str
    project_id: str
    repo_root: str
    branch: str
    head: str
    provider_id: str
    model_id: str
    dispatch_execution_id: str
    batch_id: str
    provider_generation: int
    lease_id: str
    lease_session_id: str
    lease_task_id: str
    admission_id: str

    def __post_init__(self) -> None:
        _require_identity_text(self.execution_id, "execution_id", 128)
        _require_identity_text(self.review_contract_ref, "review_contract_ref", 512)
        if not _SHA256_RE.fullmatch(self.review_task_sha256):
            raise _identity_invalid()
        _require_identity_text(self.worker_id, "worker_id", 128)
        _require_identity_text(self.project_id, "project_id", 128)
        _require_identity_text(self.repo_root, "repo_root", 1024)
        _require_identity_text(self.branch, "branch", 256)
        if not _IDENTITY_HEAD_RE.fullmatch(self.head):
            raise _identity_invalid()
        _require_identity_text(self.provider_id, "provider_id", 128)
        _require_identity_text(self.model_id, "model_id", 256)
        _require_identity_text(self.dispatch_execution_id, "dispatch_execution_id", 128)
        _require_identity_text(self.batch_id, "batch_id", 512)
        if (
            isinstance(self.provider_generation, bool)
            or not isinstance(self.provider_generation, int)
            or self.provider_generation < 1
            or self.provider_generation > _MAX_IDENTITY_GENERATION
        ):
            raise _identity_invalid()
        _require_identity_text(self.lease_id, "lease_id", 128)
        _require_identity_text(self.lease_session_id, "lease_session_id", 128)
        _require_identity_text(self.lease_task_id, "lease_task_id", 256)
        _require_identity_text(self.admission_id, "admission_id", 128)


def _reject_duplicate_json_keys(pairs):
    seen = set()
    for key, _ in pairs:
        if key in seen:
            raise ValueError("duplicate key")
        seen.add(key)
    return dict(pairs)


def build_promotion_evidence_ref(identity: ReviewPromotionResourceIdentity) -> str:
    """Deterministic bounded v2 evidence string for the promotion event."""
    import dataclasses

    if not isinstance(identity, ReviewPromotionResourceIdentity):
        raise _identity_invalid()
    payload = json.dumps(
        dataclasses.asdict(identity),
        sort_keys=True,
        separators=(",", ":"),
    )
    text = f"{_PROMOTION_EVIDENCE_PREFIX_V2}:{payload}"
    if len(text) > _MAX_PROMOTION_EVIDENCE_CHARS:
        raise ZeroRelayReviewVerificationError(
            "REVIEW_PROMOTION_EVIDENCE_MALFORMED"
        )
    return text


def parse_promotion_evidence_ref(text) -> ReviewPromotionResourceIdentity:
    """Strict fail-closed parse of a v2 promotion evidence string."""
    prefix = _PROMOTION_EVIDENCE_PREFIX_V2 + ":"
    if not isinstance(text, str) or not text.startswith(prefix):
        raise ZeroRelayReviewVerificationError(
            "REVIEW_PROMOTION_EVIDENCE_MALFORMED"
        )
    if len(text) > _MAX_PROMOTION_EVIDENCE_CHARS:
        raise ZeroRelayReviewVerificationError(
            "REVIEW_PROMOTION_EVIDENCE_MALFORMED"
        )
    try:
        payload = json.loads(
            text[len(prefix):], object_pairs_hook=_reject_duplicate_json_keys
        )
    except ValueError as exc:
        raise ZeroRelayReviewVerificationError(
            "REVIEW_PROMOTION_EVIDENCE_MALFORMED"
        ) from exc
    if not isinstance(payload, dict):
        raise ZeroRelayReviewVerificationError(
            "REVIEW_PROMOTION_EVIDENCE_MALFORMED"
        )
    expected_keys = set(ReviewPromotionResourceIdentity.__dataclass_fields__)
    if set(payload) != expected_keys:
        raise ZeroRelayReviewVerificationError(
            "REVIEW_PROMOTION_EVIDENCE_MALFORMED"
        )
    try:
        return ReviewPromotionResourceIdentity(**payload)
    except ZeroRelayReviewVerificationError as exc:
        raise ZeroRelayReviewVerificationError(
            "REVIEW_PROMOTION_EVIDENCE_MALFORMED"
        ) from exc


def resolve_promotion_resource_identity(
    execution_store, execution_id: str
) -> ReviewPromotionResourceIdentity | None:
    """Resolve the strict promotion identity from the durable event log.

    Returns None when only legacy promotion evidence exists (the prior
    fail-closed replay path). Exactly one v2 evidence event on the
    SUCCEEDED promotion resolves to the identity; v2-shaped evidence
    anywhere else, or more than one such event, is ambiguity and fails
    closed. Never a new store/service authority: reads go through the
    existing ``list_events`` API only.
    """
    if not isinstance(execution_id, str) or not execution_id.strip():
        raise _identity_invalid()
    if not callable(getattr(execution_store, "list_events", None)):
        raise ZeroRelayReviewVerificationError("REVIEW_VERIFICATION_STORE_INVALID")
    try:
        events = execution_store.list_events(execution_id)
    except ExecutionStoreError as exc:
        raise ZeroRelayReviewVerificationError(
            "REVIEW_PROMOTION_EVIDENCE_READ_FAILED"
        ) from exc
    prefix = _PROMOTION_EVIDENCE_PREFIX_V2 + ":"
    matches = []
    for event in events:
        ref = getattr(event, "evidence_ref", None)
        if not (isinstance(ref, str) and ref.startswith(prefix)):
            continue
        if (
            getattr(event, "event_type", None) is not ExecutionEventType.EXECUTION_STATE_CHANGED
            or getattr(event, "execution_state", None)
            is not ExecutionProcessState.SUCCEEDED
        ):
            raise ZeroRelayReviewVerificationError(
                "REVIEW_PROMOTION_EVIDENCE_AMBIGUOUS"
            )
        matches.append(event)
    if not matches:
        return None
    if len(matches) > 1:
        raise ZeroRelayReviewVerificationError(
            "REVIEW_PROMOTION_EVIDENCE_AMBIGUOUS"
        )
    return parse_promotion_evidence_ref(matches[0].evidence_ref)


def _require_store(execution_store) -> None:
    if not callable(getattr(execution_store, "get", None)) or not callable(
        getattr(execution_store, "set_execution_state", None)
    ):
        raise ZeroRelayReviewVerificationError("REVIEW_VERIFICATION_STORE_INVALID")


def verify_review_execution_for_promotion(
    *,
    execution_store,
    record: DurableExecutionRecord,
    expected_task_packet_sha256: str,
    expected_contract_ref: str,
    resource_identity: ReviewPromotionResourceIdentity | None = None,
) -> VerifiedReviewExecution:
    """Verify one durable reviewer execution verdict-blind, then promote.

    Fails closed (typed, no promotion) on: invalid inputs, store read
    faults, caller-record drift against the store, invalid source state,
    nonzero/missing durable exit, missing artifact refs, unreadable /
    truncated / digest-mismatched artifacts, strict report schema or
    identity/binding mismatches, and promotion CAS version conflicts. An
    already-``SUCCEEDED`` record is verified only — zero mutation.

    ``resource_identity`` (RE2-A, optional): when supplied it must be a
    valid strict identity bound to this exact record/task/contract, and the
    promotion event then carries the strict versioned v2 evidence payload.
    Direct callers without the new input keep the legacy evidence format
    and behavior unchanged.
    """
    if not isinstance(record, DurableExecutionRecord):
        raise ZeroRelayReviewVerificationError("REVIEW_VERIFICATION_RECORD_INVALID")
    _require_store(execution_store)
    if (
        not isinstance(expected_task_packet_sha256, str)
        or not _SHA256_RE.fullmatch(expected_task_packet_sha256.strip().lower())
    ):
        raise ZeroRelayReviewVerificationError(
            "REVIEW_VERIFICATION_EXPECTED_TASK_SHA_INVALID"
        )
    if (
        not isinstance(expected_contract_ref, str)
        or not expected_contract_ref.strip()
    ):
        raise ZeroRelayReviewVerificationError(
            "REVIEW_VERIFICATION_EXPECTED_CONTRACT_INVALID"
        )
    if resource_identity is not None:
        if not isinstance(resource_identity, ReviewPromotionResourceIdentity):
            raise _identity_invalid()
        if (
            resource_identity.execution_id != record.execution_id
            or resource_identity.review_task_sha256
            != expected_task_packet_sha256.strip().lower()
            or resource_identity.review_contract_ref != expected_contract_ref.strip()
        ):
            raise ZeroRelayReviewVerificationError(
                "REVIEW_VERIFICATION_IDENTITY_MISMATCH"
            )

    # pin the durable truth first: the store row for the exact runtime
    # execution id must equal the caller's snapshot (no rollover midpoint)
    try:
        pinned = execution_store.get(record.execution_id)
    except ExecutionStoreError as exc:
        if exc.code == "EXECUTION_NOT_FOUND":
            raise ZeroRelayReviewVerificationError(
                "REVIEW_VERIFICATION_RECORD_NOT_FOUND"
            ) from exc
        raise ZeroRelayReviewVerificationError(
            "REVIEW_VERIFICATION_STORE_READ_FAILED"
        ) from exc
    if not isinstance(pinned, DurableExecutionRecord) or pinned != record:
        raise ZeroRelayReviewVerificationError("REVIEW_VERIFICATION_RECORD_DRIFT")
    if pinned.execution_state not in _PROMOTABLE_SOURCE_STATES:
        raise ZeroRelayReviewVerificationError(
            "REVIEW_VERIFICATION_SOURCE_STATE_INVALID"
        )
    if (
        isinstance(pinned.exit_code, bool)
        or not isinstance(pinned.exit_code, int)
        or pinned.exit_code != 0
    ):
        raise ZeroRelayReviewVerificationError("REVIEW_VERIFICATION_EXIT_NONZERO")
    if pinned.stdout_ref is None or pinned.report_ref is None:
        raise ZeroRelayReviewVerificationError("REVIEW_VERIFICATION_ARTIFACT_REF_MISSING")

    # capture the complete artifacts through the existing bounded service
    artifacts = ExecutionArtifactService(store=execution_store)
    try:
        stdout = artifacts.read_chunk(
            pinned.execution_id,
            ExecutionArtifactKind.STDOUT,
            offset=0,
            max_bytes=MAX_ARTIFACT_READ_BYTES,
        )
        report = artifacts.read_chunk(
            pinned.execution_id,
            ExecutionArtifactKind.REPORT,
            offset=0,
            max_bytes=MAX_ARTIFACT_READ_BYTES,
        )
    except (ExecutionArtifactError, ExecutionStoreError, ValueError) as exc:
        raise ZeroRelayReviewVerificationError(
            "REVIEW_VERIFICATION_ARTIFACT_READ_FAILED"
        ) from exc

    # complete non-truncated slices + strict report schema (accepted C1
    # primitives — same function objects, zero vocabulary drift)
    try:
        stdout_raw = _verify_complete_artifact(
            stdout,
            expected_kind=ExecutionArtifactKind.STDOUT,
            execution_id=pinned.execution_id,
            artifact_ref=pinned.stdout_ref,
            code_prefix="REVIEW_STDOUT",
        )
        report_raw = _verify_complete_artifact(
            report,
            expected_kind=ExecutionArtifactKind.REPORT,
            execution_id=pinned.execution_id,
            artifact_ref=pinned.report_ref,
            code_prefix="REVIEW_REPORT",
        )
        payload = _parse_zcode_report(report_raw)
    except ZeroRelayReviewEvidenceError as exc:
        raise ZeroRelayReviewVerificationError(exc.code) from exc

    # report <-> runtime execution / task / response cross-binding
    if payload.get("execution_id") != pinned.execution_id:
        raise ZeroRelayReviewVerificationError("REVIEW_REPORT_EXECUTION_MISMATCH")
    if payload.get("task_packet_sha256") != expected_task_packet_sha256.strip().lower():
        raise ZeroRelayReviewVerificationError("REVIEW_REPORT_TASK_SHA_MISMATCH")
    if "task_contract_ref" in payload and payload.get("task_contract_ref") != (
        expected_contract_ref.strip()
    ):
        raise ZeroRelayReviewVerificationError("REVIEW_REPORT_CONTRACT_MISMATCH")
    response_bytes = payload.get("response_bytes")
    if (
        isinstance(response_bytes, bool)
        or not isinstance(response_bytes, int)
        or response_bytes != len(stdout_raw)
    ):
        raise ZeroRelayReviewVerificationError("REVIEW_REPORT_RESPONSE_BYTES_MISMATCH")
    if payload.get("response_sha256") != hashlib.sha256(stdout_raw).hexdigest():
        raise ZeroRelayReviewVerificationError("REVIEW_REPORT_RESPONSE_SHA_MISMATCH")
    if "exit_state" in payload:
        # the durable record is already terminal; a report that still
        # claims a non-terminal exit state contradicts that truth
        if payload.get("exit_state") == "EXIT_PENDING":
            raise ZeroRelayReviewVerificationError("REVIEW_REPORT_EXIT_PENDING")
        raise ZeroRelayReviewVerificationError("REVIEW_REPORT_EXIT_STATE_INVALID")

    # already-promoted replay: verification only, ZERO mutation
    if pinned.execution_state is ExecutionProcessState.SUCCEEDED:
        return VerifiedReviewExecution(record=pinned, promoted=False)

    # exactly ONE existing-store version-CAS promotion from
    # VERIFICATION_REQUIRED after full verification. The evidence_ref is
    # the legacy bounded marker, or — when the caller supplied the strict
    # resource identity (RE2-A) — the deterministic v2 payload persisting
    # the exact original lease/admission locators before any cleanup.
    evidence_ref = (
        build_promotion_evidence_ref(resource_identity)
        if resource_identity is not None
        else f"{_PROMOTION_EVIDENCE_PREFIX}:{pinned.execution_id}"
    )
    try:
        promoted = execution_store.set_execution_state(
            pinned.execution_id,
            ExecutionProcessState.SUCCEEDED,
            expected_version=pinned.version,
            evidence_ref=evidence_ref,
        )
    except ExecutionStoreError as exc:
        if exc.code == "EXECUTION_VERSION_CONFLICT":
            raise ZeroRelayReviewVerificationError(
                "REVIEW_PROMOTION_VERSION_CONFLICT"
            ) from exc
        raise ZeroRelayReviewVerificationError("REVIEW_PROMOTION_FAILED") from exc
    if (
        not isinstance(promoted, DurableExecutionRecord)
        or promoted.execution_state is not ExecutionProcessState.SUCCEEDED
        or promoted.version != pinned.version + 1
        or promoted.exit_code != pinned.exit_code
    ):
        raise ZeroRelayReviewVerificationError("REVIEW_PROMOTION_RESULT_INVALID")
    return VerifiedReviewExecution(record=promoted, promoted=True)
