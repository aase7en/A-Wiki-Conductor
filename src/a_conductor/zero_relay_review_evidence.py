"""WO-P1-223 C1 - strict semantic validation for direct review v2 results.

This module is intentionally pure at the semantic boundary. It accepts already
captured raw response bytes plus exact trusted expectations and returns a typed
validated result. Durable execution/artifact cross-binding is layered on top;
this parser creates no store, scheduler, provider, lease, retry, or review
lifecycle authority.
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
    ExecutionArtifactSlice,
    MAX_ARTIFACT_READ_BYTES,
)
from .execution_record import DurableExecutionRecord, ExecutionProcessState
from .execution_store import ExecutionStoreError
from .registry import windows_worktree_key
from .zero_relay import ResultIdentity, ReviewDisposition, ReviewEvidence
from .zero_relay_review_execution import DirectReviewExecutionHandoff
from .zero_relay_review_task import DirectReviewRoute
from .zcode_runner import ZCODE_BACKEND_ID

_RESULT_SCHEMA = "zra2-review-result-v2"
_MAX_RESPONSE_BYTES = 32 * 1024
_MAX_FINDINGS = 64
_MAX_FINDING_CHARS = 2048
_HEAD_RE = re.compile(r"^[0-9a-f]{7,64}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_KEYS = frozenset({
    "schema",
    "review_contract_ref",
    "reviewed_head",
    "review_task_sha256",
    "verdict",
    "findings",
})


class ZeroRelayReviewEvidenceError(RuntimeError):
    """Stable typed failure; never exposes untrusted response content."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class _DuplicateKeyError(ValueError):
    pass


class _NonStandardJsonConstant(ValueError):
    pass


def _reject_json_constant(_value: str):
    raise _NonStandardJsonConstant


@dataclass(frozen=True, slots=True)
class _ValidatedDirectReviewResult:
    review_contract_ref: str
    reviewed_head: str
    review_task_sha256: str
    disposition: ReviewDisposition
    findings: tuple[str, ...]


def _pairs_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError
        result[key] = value
    return result


def _expected_text(value: object, code: str, *, max_chars: int = 512) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ZeroRelayReviewEvidenceError(code)
    if len(value) > max_chars or any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise ZeroRelayReviewEvidenceError(code)
    return value


def parse_review_v2_response(
    raw: bytes,
    *,
    expected_contract_ref: str,
    expected_reviewed_head: str,
    expected_review_task_sha256: str,
) -> _ValidatedDirectReviewResult:
    """Validate one complete whole-response v2 payload fail-closed.

    ``raw`` must be the exact complete stdout response bytes. Prefix/suffix
    prose, Markdown fences, duplicate JSON keys, aliases and unknown fields are
    rejected. Findings remain non-authoritative evidence strings only.
    """
    if not isinstance(raw, bytes):
        raise ZeroRelayReviewEvidenceError("REVIEW_RESULT_BYTES_INVALID")
    if not raw or len(raw) > _MAX_RESPONSE_BYTES:
        raise ZeroRelayReviewEvidenceError("REVIEW_RESULT_TOO_LARGE")
    contract = _expected_text(expected_contract_ref, "REVIEW_EXPECTED_CONTRACT_INVALID")
    head = _expected_text(expected_reviewed_head, "REVIEW_EXPECTED_HEAD_INVALID", max_chars=64).casefold()
    task_sha = _expected_text(
        expected_review_task_sha256, "REVIEW_EXPECTED_TASK_SHA_INVALID", max_chars=64
    ).casefold()
    if not _HEAD_RE.fullmatch(head):
        raise ZeroRelayReviewEvidenceError("REVIEW_EXPECTED_HEAD_INVALID")
    if not _SHA256_RE.fullmatch(task_sha):
        raise ZeroRelayReviewEvidenceError("REVIEW_EXPECTED_TASK_SHA_INVALID")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ZeroRelayReviewEvidenceError("REVIEW_RESULT_UTF8_INVALID") from exc
    try:
        payload = json.loads(
            text, object_pairs_hook=_pairs_object, parse_constant=_reject_json_constant
        )
    except _DuplicateKeyError as exc:
        raise ZeroRelayReviewEvidenceError("REVIEW_RESULT_DUPLICATE_KEY") from exc
    except _NonStandardJsonConstant as exc:
        raise ZeroRelayReviewEvidenceError("REVIEW_RESULT_JSON_INVALID") from exc
    except json.JSONDecodeError as exc:
        raise ZeroRelayReviewEvidenceError("REVIEW_RESULT_JSON_INVALID") from exc
    if not isinstance(payload, dict):
        raise ZeroRelayReviewEvidenceError("REVIEW_RESULT_ROOT_INVALID")
    if set(payload) != _KEYS:
        raise ZeroRelayReviewEvidenceError("REVIEW_RESULT_KEYS_INVALID")
    if payload.get("schema") != _RESULT_SCHEMA:
        raise ZeroRelayReviewEvidenceError("REVIEW_RESULT_SCHEMA_MISMATCH")
    if payload.get("review_contract_ref") != contract:
        raise ZeroRelayReviewEvidenceError("REVIEW_RESULT_CONTRACT_MISMATCH")
    reviewed_head = payload.get("reviewed_head")
    if not isinstance(reviewed_head, str) or reviewed_head != head:
        raise ZeroRelayReviewEvidenceError("REVIEW_RESULT_HEAD_MISMATCH")
    review_task_sha = payload.get("review_task_sha256")
    if not isinstance(review_task_sha, str) or review_task_sha != task_sha:
        raise ZeroRelayReviewEvidenceError("REVIEW_RESULT_TASK_SHA_MISMATCH")
    verdict = payload.get("verdict")
    if verdict == ReviewDisposition.ACCEPTED.value:
        disposition = ReviewDisposition.ACCEPTED
    elif verdict == ReviewDisposition.REJECTED.value:
        disposition = ReviewDisposition.REJECTED
    else:
        raise ZeroRelayReviewEvidenceError("REVIEW_RESULT_VERDICT_INVALID")
    raw_findings = payload.get("findings")
    if not isinstance(raw_findings, list) or len(raw_findings) > _MAX_FINDINGS:
        raise ZeroRelayReviewEvidenceError("REVIEW_RESULT_FINDINGS_INVALID")
    findings: list[str] = []
    for finding in raw_findings:
        if (
            not isinstance(finding, str)
            or not finding
            or len(finding) > _MAX_FINDING_CHARS
            or "\x00" in finding
            or any(0xD800 <= ord(ch) <= 0xDFFF for ch in finding)
        ):
            raise ZeroRelayReviewEvidenceError("REVIEW_RESULT_FINDINGS_INVALID")
        findings.append(finding)
    return _ValidatedDirectReviewResult(
        review_contract_ref=contract,
        reviewed_head=head,
        review_task_sha256=task_sha,
        disposition=disposition,
        findings=tuple(findings),
    )


_REPORT_REQUIRED = frozenset({
    "schema", "execution_id", "task_packet_sha256",
    "response_bytes", "response_sha256", "session_id",
})
_REPORT_ALLOWED = _REPORT_REQUIRED | frozenset({
    "task_contract_ref", "selection_sha256", "exit_state",
})


def _verify_complete_artifact(
    artifact: ExecutionArtifactSlice,
    *,
    expected_kind: ExecutionArtifactKind,
    execution_id: str,
    artifact_ref: str,
    code_prefix: str,
) -> bytes:
    if not isinstance(artifact, ExecutionArtifactSlice):
        raise ZeroRelayReviewEvidenceError(f"{code_prefix}_SLICE_INVALID")
    if artifact.kind is not expected_kind:
        raise ZeroRelayReviewEvidenceError(f"{code_prefix}_KIND_MISMATCH")
    if artifact.execution_id != execution_id:
        raise ZeroRelayReviewEvidenceError(f"{code_prefix}_EXECUTION_MISMATCH")
    if artifact.artifact_ref != artifact_ref:
        raise ZeroRelayReviewEvidenceError(f"{code_prefix}_REF_MISMATCH")
    if (
        artifact.offset != 0
        or artifact.truncated
        or artifact.returned_bytes != len(artifact.raw)
        or artifact.total_bytes != artifact.returned_bytes
    ):
        raise ZeroRelayReviewEvidenceError(f"{code_prefix}_SLICE_INVALID")
    actual = hashlib.sha256(artifact.raw).hexdigest()
    if artifact.sha256 != actual:
        raise ZeroRelayReviewEvidenceError(f"{code_prefix}_DIGEST_MISMATCH")
    return artifact.raw


def _parse_zcode_report(raw: bytes) -> dict[str, object]:
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ZeroRelayReviewEvidenceError("REVIEW_REPORT_UTF8_INVALID") from exc
    try:
        payload = json.loads(
            text, object_pairs_hook=_pairs_object, parse_constant=_reject_json_constant
        )
    except _DuplicateKeyError as exc:
        raise ZeroRelayReviewEvidenceError("REVIEW_REPORT_DUPLICATE_KEY") from exc
    except _NonStandardJsonConstant as exc:
        raise ZeroRelayReviewEvidenceError("REVIEW_REPORT_JSON_INVALID") from exc
    except json.JSONDecodeError as exc:
        raise ZeroRelayReviewEvidenceError("REVIEW_REPORT_JSON_INVALID") from exc
    if not isinstance(payload, dict):
        raise ZeroRelayReviewEvidenceError("REVIEW_REPORT_ROOT_INVALID")
    keys = set(payload)
    if not _REPORT_REQUIRED.issubset(keys) or not keys.issubset(_REPORT_ALLOWED):
        raise ZeroRelayReviewEvidenceError("REVIEW_REPORT_KEYS_INVALID")
    if payload.get("schema") != "zcode-report/1":
        raise ZeroRelayReviewEvidenceError("REVIEW_REPORT_SCHEMA_MISMATCH")
    return payload


def _bind_author_route(author: ResultIdentity, route: DirectReviewRoute) -> None:
    if not isinstance(author, ResultIdentity) or not isinstance(route, DirectReviewRoute):
        raise ZeroRelayReviewEvidenceError("INPUT_INVALID")
    if (
        route.author_execution_id != author.author_execution_id
        or route.author_result_sha256 != author.result_sha256
        or route.author_attempt_id != author.attempt_id
        or route.author_generation != author.generation
    ):
        raise ZeroRelayReviewEvidenceError("AUTHOR_IDENTITY_MISMATCH")


def _bind_record_handoff_route(
    route: DirectReviewRoute,
    handoff: DirectReviewExecutionHandoff,
    record: DurableExecutionRecord,
) -> None:
    if not isinstance(handoff, DirectReviewExecutionHandoff) or not isinstance(record, DurableExecutionRecord):
        raise ZeroRelayReviewEvidenceError("INPUT_INVALID")
    if handoff.runtime_execution_id != record.execution_id:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_ID_MISMATCH")
    if record.execution_id == route.author_execution_id:
        raise ZeroRelayReviewEvidenceError("AUTHOR_REVIEWER_NOT_DISTINCT")
    if handoff.dispatch_execution_id != route.dispatch_execution_id:
        raise ZeroRelayReviewEvidenceError("REVIEW_DISPATCH_IDENTITY_MISMATCH")
    if handoff.review_contract_ref != route.review_contract_ref or record.work_order_ref != route.review_contract_ref:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_CONTRACT_MISMATCH")
    if handoff.supervised_job_id != record.job_id:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_JOB_MISMATCH")
    if handoff.worker_id != route.reviewer_worker_id or record.worker_id != route.reviewer_worker_id:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_WORKER_MISMATCH")
    if handoff.project_id != route.project_id or record.project_id != route.project_id:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_PROJECT_MISMATCH")
    if handoff.provider_id != route.provider_id or handoff.model_id != route.model_id:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_PROVIDER_MODEL_MISMATCH")
    if (
        windows_worktree_key(handoff.repo_root) != windows_worktree_key(route.worktree)
        or windows_worktree_key(record.repo_root) != windows_worktree_key(route.worktree)
    ):
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_WORKTREE_MISMATCH")
    if handoff.branch != route.branch or record.branch != route.branch:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_BRANCH_MISMATCH")
    if handoff.head.casefold() != route.reviewed_head.casefold() or record.head_before.casefold() != route.reviewed_head.casefold():
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_HEAD_MISMATCH")
    if handoff.task_packet_sha256 != route.review_task_sha256:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_TASK_SHA_MISMATCH")
    if handoff.task_packet_path != route.review_task_path:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_TASK_PATH_MISMATCH")
    if handoff.fingerprint != record.command_fingerprint:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_FINGERPRINT_MISMATCH")
    if handoff.record_version != record.version:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_VERSION_MISMATCH")
    if handoff.record_state != record.execution_state.value:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_STATE_MISMATCH")
    if record.backend_id != ZCODE_BACKEND_ID:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_BACKEND_MISMATCH")
    if handoff.exit_code != 0 or record.exit_code != 0:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_EXIT_MISMATCH")
    if handoff.outcome not in {"EXECUTED", "REUSE_COMPLETED"}:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_OUTCOME_INVALID")
    if not handoff.cleanup_terminal or not handoff.lease_released or handoff.admission_status != "RELEASED":
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_CLEANUP_UNPROVEN")
    if handoff.lease_task_id != route.review_contract_ref:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_LEASE_CONTRACT_MISMATCH")
    if record.stdout_ref != handoff.stdout_ref or record.report_ref != handoff.report_ref:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_ARTIFACT_REF_MISMATCH")
    if record.result_ref != handoff.result_ref or record.stderr_ref != handoff.stderr_ref:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_ARTIFACT_REF_MISMATCH")
    if record.execution_state not in {
        ExecutionProcessState.SUCCEEDED,
        ExecutionProcessState.VERIFICATION_REQUIRED,
    }:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_NOT_USABLE")


def compose_direct_review_evidence(
    *,
    author: ResultIdentity,
    route: DirectReviewRoute,
    handoff: DirectReviewExecutionHandoff,
    record: DurableExecutionRecord,
    stdout: ExecutionArtifactSlice,
    report: ExecutionArtifactSlice,
) -> ReviewEvidence:
    """Cross-bind WO225 route + WO226 handoff + durable runtime artifacts.

    This consumes immutable evidence only. It creates no execution, lease,
    provider, scheduler, retry, mailbox, or store authority.
    """
    _bind_author_route(author, route)
    _bind_record_handoff_route(route, handoff, record)
    if record.stdout_ref is None or record.report_ref is None:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_ARTIFACT_REF_MISSING")
    stdout_raw = _verify_complete_artifact(
        stdout,
        expected_kind=ExecutionArtifactKind.STDOUT,
        execution_id=record.execution_id,
        artifact_ref=record.stdout_ref,
        code_prefix="REVIEW_STDOUT",
    )
    if len(stdout_raw) > _MAX_RESPONSE_BYTES:
        raise ZeroRelayReviewEvidenceError("REVIEW_RESULT_TOO_LARGE")
    report_raw = _verify_complete_artifact(
        report,
        expected_kind=ExecutionArtifactKind.REPORT,
        execution_id=record.execution_id,
        artifact_ref=record.report_ref,
        code_prefix="REVIEW_REPORT",
    )
    payload = _parse_zcode_report(report_raw)
    if payload.get("execution_id") != record.execution_id:
        raise ZeroRelayReviewEvidenceError("REVIEW_REPORT_EXECUTION_MISMATCH")
    if payload.get("task_packet_sha256") != route.review_task_sha256:
        raise ZeroRelayReviewEvidenceError("REVIEW_REPORT_TASK_SHA_MISMATCH")
    if "task_contract_ref" in payload and payload.get("task_contract_ref") != route.review_contract_ref:
        raise ZeroRelayReviewEvidenceError("REVIEW_REPORT_CONTRACT_MISMATCH")
    response_bytes = payload.get("response_bytes")
    if isinstance(response_bytes, bool) or not isinstance(response_bytes, int) or response_bytes != len(stdout_raw):
        raise ZeroRelayReviewEvidenceError("REVIEW_REPORT_RESPONSE_BYTES_MISMATCH")
    stdout_sha = hashlib.sha256(stdout_raw).hexdigest()
    if payload.get("response_sha256") != stdout_sha:
        raise ZeroRelayReviewEvidenceError("REVIEW_REPORT_RESPONSE_SHA_MISMATCH")
    if "exit_state" in payload:
        if payload.get("exit_state") == "EXIT_PENDING":
            raise ZeroRelayReviewEvidenceError("REVIEW_REPORT_EXIT_PENDING")
        raise ZeroRelayReviewEvidenceError("REVIEW_REPORT_EXIT_STATE_INVALID")
    validated = parse_review_v2_response(
        stdout_raw,
        expected_contract_ref=route.review_contract_ref,
        expected_reviewed_head=route.reviewed_head,
        expected_review_task_sha256=route.review_task_sha256,
    )
    if (
        validated.disposition is ReviewDisposition.ACCEPTED
        and record.execution_state is not ExecutionProcessState.SUCCEEDED
    ):
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_NOT_ACCEPTANCE_ELIGIBLE")
    return ReviewEvidence(
        task_contract_ref=author.task_contract_ref,
        task_sha256=author.task_sha256,
        result_ref=author.result_ref,
        result_sha256=author.result_sha256,
        attempt_id=author.attempt_id,
        generation=author.generation,
        reviewer_execution_id=record.execution_id,
        disposition=validated.disposition,
    )



def compose_direct_review_evidence_from_store(
    *,
    author: ResultIdentity,
    route: DirectReviewRoute,
    handoff: DirectReviewExecutionHandoff,
    store,
) -> ReviewEvidence:
    """Read one stable durable execution snapshot and compose review evidence.

    The caller supplies only the accepted route/handoff plus the existing
    execution-store authority. Record and artifact bytes are obtained through
    the accepted store/artifact APIs and are re-pinned after capture so a
    terminal-state/version rollover cannot be hidden by caller-created values.
    """
    if not callable(getattr(store, "get", None)):
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_STORE_INVALID")
    if not isinstance(handoff, DirectReviewExecutionHandoff):
        raise ZeroRelayReviewEvidenceError("INPUT_INVALID")
    execution_id = handoff.runtime_execution_id
    try:
        before = store.get(execution_id)
    except ExecutionStoreError as exc:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_STORE_READ_FAILED") from exc
    if not isinstance(before, DurableExecutionRecord):
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_RECORD_INVALID")

    artifacts = ExecutionArtifactService(store=store)
    try:
        stdout = artifacts.read_chunk(
            execution_id,
            ExecutionArtifactKind.STDOUT,
            offset=0,
            max_bytes=MAX_ARTIFACT_READ_BYTES,
        )
        report = artifacts.read_chunk(
            execution_id,
            ExecutionArtifactKind.REPORT,
            offset=0,
            max_bytes=MAX_ARTIFACT_READ_BYTES,
        )
    except (ExecutionArtifactError, ExecutionStoreError, ValueError) as exc:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_ARTIFACT_READ_FAILED") from exc

    try:
        after = store.get(execution_id)
    except ExecutionStoreError as exc:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_STORE_READ_FAILED") from exc
    if not isinstance(after, DurableExecutionRecord):
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_RECORD_INVALID")
    if before != after:
        raise ZeroRelayReviewEvidenceError("REVIEW_EXECUTION_RECORD_DRIFT")

    return compose_direct_review_evidence(
        author=author,
        route=route,
        handoff=handoff,
        record=after,
        stdout=stdout,
        report=report,
    )
