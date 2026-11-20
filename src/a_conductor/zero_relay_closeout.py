"""WO-P1-205 Phase D: bind exact author/review evidence to existing closeout.

This module is intentionally a thin composition seam. It creates no store,
review lifecycle, retry loop, external-effect authority, or completion state
machine. The existing supervised execution, Phase-C review, relay classifier,
and ProductionGoalCloseoutFacade remain the authorities.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

from .execution_artifacts import (
    MAX_ARTIFACT_READ_BYTES,
    ExecutionArtifactError,
    ExecutionArtifactKind,
    ExecutionArtifactService,
)
from .execution_record import DurableExecutionRecord
from .execution_store import ExecutionStoreError
from .goal_closeout_assembly import ProductionCloseoutResult
from .supervised_child import SUPERVISED_RESULT_SCHEMA_VERSION, SupervisedChildResult
from .supervised_run_coordinator import (
    SupervisedRunOutcome,
    SupervisedRunOutcomeKind,
)
from .zero_relay import (
    ExecutionOutcome,
    RelayDecision,
    RelayOutcome,
    ResultIdentity,
    ReviewEvidence,
    VerificationOutcome,
    ZeroRelayError,
    classify_relay_decision,
)
from .zero_relay_author_provenance import (
    AuthorProvenanceError,
    compose_result_identity,
)
from .zero_relay_review_evidence import (
    ZeroRelayReviewEvidenceError,
    _verify_complete_artifact,
    compose_direct_review_evidence_from_store,
)
from .zero_relay_review_execution import DirectReviewExecutionHandoff
from .zero_relay_review_task import DirectReviewRoute
from .zero_relay_review_verification import (
    ZeroRelayReviewVerificationError,
    verify_review_execution_for_promotion,
)
from .zcode_runner import ZCODE_BACKEND_ID


_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_RESULT_KEYS = frozenset(
    {
        "schema_version",
        "execution_id",
        "child_pid",
        "exit_code",
        "started_at",
        "finished_at",
    }
)
_ACCEPTABLE_AUTHOR_KINDS = frozenset(
    {
        SupervisedRunOutcomeKind.FRESH,
        SupervisedRunOutcomeKind.ATTACH_RUNNING,
        SupervisedRunOutcomeKind.REUSE_COMPLETED,
    }
)


class ZeroRelayCloseoutError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class CloseoutFacadePort(Protocol):
    def next_stage(self, job_id: str) -> ProductionCloseoutResult: ...


@dataclass(frozen=True, slots=True)
class ZeroRelayCloseoutResult:
    result_identity: ResultIdentity
    review_evidence: ReviewEvidence
    relay_outcome: RelayOutcome
    closeout_result: ProductionCloseoutResult


def _text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ZeroRelayCloseoutError(f"{field_name.upper()}_INVALID")
    return value.strip()


def _sha(value: str, field_name: str) -> str:
    text = _text(value, field_name).lower()
    if not _SHA_RE.fullmatch(text):
        raise ZeroRelayCloseoutError(f"{field_name.upper()}_INVALID")
    return text


def _strict_pairs(pairs):
    document = {}
    for key, value in pairs:
        if key in document:
            raise ZeroRelayCloseoutError("AUTHOR_RESULT_INVALID")
        document[key] = value
    return document


def _reject_constant(_value: str):
    raise ZeroRelayCloseoutError("AUTHOR_RESULT_INVALID")


def _parse_result_bytes(raw: bytes, *, execution_id: str) -> SupervisedChildResult:
    try:
        text = raw.decode("utf-8", errors="strict")
        payload = json.loads(
            text,
            object_pairs_hook=_strict_pairs,
            parse_constant=_reject_constant,
        )
    except ZeroRelayCloseoutError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ZeroRelayCloseoutError("AUTHOR_RESULT_INVALID") from exc
    if not isinstance(payload, dict) or set(payload) != _RESULT_KEYS:
        raise ZeroRelayCloseoutError("AUTHOR_RESULT_INVALID")
    try:
        result = SupervisedChildResult(
            schema_version=payload["schema_version"],
            execution_id=payload["execution_id"],
            child_pid=payload["child_pid"],
            exit_code=payload["exit_code"],
            started_at=payload["started_at"],
            finished_at=payload["finished_at"],
        )
    except (TypeError, ValueError) as exc:
        raise ZeroRelayCloseoutError("AUTHOR_RESULT_INVALID") from exc
    if result.schema_version != SUPERVISED_RESULT_SCHEMA_VERSION:
        raise ZeroRelayCloseoutError("AUTHOR_RESULT_INVALID")
    if result.execution_id != execution_id:
        raise ZeroRelayCloseoutError("AUTHOR_RESULT_EXECUTION_MISMATCH")
    if result.exit_code != 0:
        raise ZeroRelayCloseoutError("AUTHOR_RESULT_EXIT_NONZERO")
    return result


def _compose_author_and_review(
    *,
    execution_id: str,
    execution_store,
    expected_job_id: str,
    expected_author_worker_id: str,
    expected_task_contract_ref: str,
    expected_task_sha256: str,
    expected_candidate_sha: str,
    review_route: DirectReviewRoute,
    review_handoff: DirectReviewExecutionHandoff,
) -> tuple[ResultIdentity, ReviewEvidence, RelayOutcome]:
    if not callable(getattr(execution_store, "get", None)):
        raise ZeroRelayCloseoutError("EXECUTION_STORE_INVALID")
    try:
        record = execution_store.get(execution_id)
    except ExecutionStoreError as exc:
        raise ZeroRelayCloseoutError("AUTHOR_EXECUTION_RECORD_UNAVAILABLE") from exc
    if not isinstance(record, DurableExecutionRecord) or record.execution_id != execution_id:
        raise ZeroRelayCloseoutError("AUTHOR_EXECUTION_RECORD_INVALID")
    if (
        record.job_id != expected_job_id
        or record.worker_id != expected_author_worker_id
        or record.work_order_ref != expected_task_contract_ref
        or record.project_id != review_route.project_id
        or record.branch != review_route.branch
        or record.head_before != expected_candidate_sha
        or record.backend_id != ZCODE_BACKEND_ID
    ):
        raise ZeroRelayCloseoutError("AUTHOR_EXECUTION_IDENTITY_MISMATCH")

    if record.result_ref is None:
        raise ZeroRelayCloseoutError("AUTHOR_RESULT_REF_MISSING")

    artifacts = ExecutionArtifactService(store=execution_store)
    try:
        result_slice = artifacts.read_chunk(
            execution_id,
            ExecutionArtifactKind.RESULT,
            offset=0,
            max_bytes=MAX_ARTIFACT_READ_BYTES,
        )
        result_raw = _verify_complete_artifact(
            result_slice,
            expected_kind=ExecutionArtifactKind.RESULT,
            execution_id=execution_id,
            artifact_ref=record.result_ref,
            code_prefix="AUTHOR_RESULT",
        )
    except (ExecutionArtifactError, ExecutionStoreError, ValueError) as exc:
        raise ZeroRelayCloseoutError("AUTHOR_RESULT_ARTIFACT_READ_FAILED") from exc
    except ZeroRelayReviewEvidenceError as exc:
        raise ZeroRelayCloseoutError(f"AUTHOR_RESULT_ARTIFACT_INVALID:{exc.code}") from exc

    _parse_result_bytes(result_raw, execution_id=execution_id)

    try:
        identity = compose_result_identity(
            record=record,
            task_contract_ref=expected_task_contract_ref,
            task_sha256=expected_task_sha256,
            result_ref=record.result_ref,
            result_sha256=result_slice.sha256,
        )
    except AuthorProvenanceError as exc:
        raise ZeroRelayCloseoutError(f"AUTHOR_PROVENANCE_INVALID:{exc.code}") from exc
    if identity.generation != 0:
        raise ZeroRelayCloseoutError("AUTHOR_REPAIR_LINEAGE_UNAVAILABLE")

    try:
        verified = verify_review_execution_for_promotion(
            execution_store=execution_store,
            record=record,
            expected_task_packet_sha256=expected_task_sha256,
            expected_contract_ref=expected_task_contract_ref,
        )
    except ZeroRelayReviewVerificationError as exc:
        raise ZeroRelayCloseoutError(f"AUTHOR_VERIFICATION_FAILED:{exc.code}") from exc
    promoted = verified.record
    if (
        promoted.execution_id != execution_id
        or promoted.result_ref != record.result_ref
        or promoted.author_attempt_id != record.author_attempt_id
        or promoted.author_generation != record.author_generation
    ):
        raise ZeroRelayCloseoutError("AUTHOR_EXECUTION_IDENTITY_MISMATCH")


    try:
        review = compose_direct_review_evidence_from_store(
            author=identity,
            route=review_route,
            handoff=review_handoff,
            store=execution_store,
        )
    except ZeroRelayReviewEvidenceError as exc:
        raise ZeroRelayCloseoutError(f"REVIEW_EVIDENCE_INVALID:{exc.code}") from exc

    try:
        relay = classify_relay_decision(
            identity,
            execution_outcome=ExecutionOutcome.SUCCEEDED,
            verification_outcome=VerificationOutcome.VERIFIED,
            review=review,
        )
    except ZeroRelayError as exc:
        raise ZeroRelayCloseoutError(f"RELAY_CLASSIFICATION_FAILED:{exc.code}") from exc
    return identity, review, relay


def compose_zero_relay_closeout(
    *,
    author_outcome: SupervisedRunOutcome,
    execution_store,
    expected_task_contract_ref: str,
    expected_task_sha256: str,
    expected_author_worker_id: str,
    review_route: DirectReviewRoute,
    review_handoff: DirectReviewExecutionHandoff,
    expected_candidate_sha: str,
    closeout_facade: CloseoutFacadePort,
    job_id: str,
) -> ZeroRelayCloseoutResult:
    """Validate one exact accepted author/reviewer pair and advance one stage."""

    if not isinstance(author_outcome, SupervisedRunOutcome):
        raise ZeroRelayCloseoutError("AUTHOR_OUTCOME_INVALID")
    if (
        author_outcome.kind not in _ACCEPTABLE_AUTHOR_KINDS
        or author_outcome.execution_id is None
        or author_outcome.native.timed_out
        or author_outcome.native.exit_code != 0
    ):
        raise ZeroRelayCloseoutError("AUTHOR_EXECUTION_NOT_ACCEPTABLE")
    if not isinstance(review_route, DirectReviewRoute):
        raise ZeroRelayCloseoutError("REVIEW_ROUTE_INVALID")
    if not isinstance(review_handoff, DirectReviewExecutionHandoff):
        raise ZeroRelayCloseoutError("REVIEW_HANDOFF_INVALID")

    candidate_sha = _sha(expected_candidate_sha, "candidate_sha")
    author_worker_id = _text(expected_author_worker_id, "author_worker_id")
    if review_route.reviewed_head != candidate_sha:
        raise ZeroRelayCloseoutError("CANDIDATE_SHA_MISMATCH")
    if review_handoff.head != candidate_sha:
        raise ZeroRelayCloseoutError("REVIEW_HANDOFF_CANDIDATE_SHA_MISMATCH")
    if review_route.author_execution_id != author_outcome.execution_id:
        raise ZeroRelayCloseoutError("AUTHOR_EXECUTION_IDENTITY_MISMATCH")
    facade_candidate = getattr(closeout_facade, "_candidate_sha", None)
    if facade_candidate != candidate_sha:
        raise ZeroRelayCloseoutError("CLOSEOUT_CANDIDATE_SHA_MISMATCH")
    if not callable(getattr(closeout_facade, "next_stage", None)):
        raise ZeroRelayCloseoutError("CLOSEOUT_FACADE_INVALID")

    expected_job_id = _text(job_id, "job_id")
    task_contract_ref = _text(expected_task_contract_ref, "task_contract_ref")
    task_sha = _text(expected_task_sha256, "task_sha256").lower()

    identity, review, relay = _compose_author_and_review(
        execution_id=author_outcome.execution_id,
        execution_store=execution_store,
        expected_job_id=expected_job_id,
        expected_author_worker_id=author_worker_id,
        expected_task_contract_ref=task_contract_ref,
        expected_task_sha256=task_sha,
        expected_candidate_sha=candidate_sha,
        review_route=review_route,
        review_handoff=review_handoff,
    )
    if identity.generation != 0:
        raise ZeroRelayCloseoutError("AUTHOR_REPAIR_LINEAGE_UNAVAILABLE")
    if relay.decision is not RelayDecision.ACCEPTED:
        raise ZeroRelayCloseoutError("RELAY_NOT_ACCEPTED")

    closeout = closeout_facade.next_stage(expected_job_id)
    if not isinstance(closeout, ProductionCloseoutResult):
        raise ZeroRelayCloseoutError("CLOSEOUT_RESULT_INVALID")
    return ZeroRelayCloseoutResult(
        result_identity=identity,
        review_evidence=review,
        relay_outcome=relay,
        closeout_result=closeout,
    )
