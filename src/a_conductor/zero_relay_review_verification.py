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
import re
from dataclasses import dataclass

from .execution_artifacts import (
    ExecutionArtifactError,
    ExecutionArtifactKind,
    ExecutionArtifactService,
    MAX_ARTIFACT_READ_BYTES,
)
from .execution_record import DurableExecutionRecord, ExecutionProcessState
from .execution_store import ExecutionStoreError
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
_PROMOTION_EVIDENCE_PREFIX = "zra2-review-verification"
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
) -> VerifiedReviewExecution:
    """Verify one durable reviewer execution verdict-blind, then promote.

    Fails closed (typed, no promotion) on: invalid inputs, store read
    faults, caller-record drift against the store, invalid source state,
    nonzero/missing durable exit, missing artifact refs, unreadable /
    truncated / digest-mismatched artifacts, strict report schema or
    identity/binding mismatches, and promotion CAS version conflicts. An
    already-``SUCCEEDED`` record is verified only — zero mutation.
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
    # VERIFICATION_REQUIRED after full verification
    try:
        promoted = execution_store.set_execution_state(
            pinned.execution_id,
            ExecutionProcessState.SUCCEEDED,
            expected_version=pinned.version,
            evidence_ref=f"{_PROMOTION_EVIDENCE_PREFIX}:{pinned.execution_id}",
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
