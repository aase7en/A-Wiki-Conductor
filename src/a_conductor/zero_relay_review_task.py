"""WO-P1-216 / ZRA-2 Phase C0 — review-task provenance + direct route binding.

C0a turns one exact ``zero_relay.ResultIdentity`` into a deterministic,
versioned review identity, a bounded review ``TaskPacketFile``-shaped
markdown task, and one collision-safe persisted artifact through the accepted
``NativeFileSystem`` authority. C0b consumes a validated ``ParallelReadyTask``
whose packet is that exact review task and returns a small immutable direct
review route binding for later Phase C1 consumption.

This module adds NO scheduler, provider store, lease store, retry engine,
review lifecycle, mailbox publisher, or second publication implementation.
"""
from __future__ import annotations

import hashlib
import json
import ntpath
import re
from dataclasses import dataclass

from .native_execution import NativeExecutionError, NativeFileSystem
from .registry import windows_worktree_key
from .zero_relay import ResultIdentity

_SCHEMA = "zra2-review-v1"


_HEAD_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")


def _reviewed_head(value: object) -> str:
    if not isinstance(value, str) or not _HEAD_RE.fullmatch(value):
        raise ZeroRelayReviewTaskError("REVIEW_HEAD_INVALID")
    return value.casefold()


def _expected_content_sha(identity: ResultIdentity, reviewed_head: str) -> tuple[str, str]:
    content = render_review_task_markdown(identity, reviewed_head)
    return content, hashlib.sha256(content.encode("utf-8")).hexdigest()


class ZeroRelayReviewTaskError(RuntimeError):
    """Stable typed failure; never echoes arbitrary input text."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class ReviewTaskRefs:
    digest: str
    contract_ref: str
    task_path: str
    result_ref: str


def canonical_review_bytes(identity: ResultIdentity, reviewed_head: str) -> bytes:
    if not isinstance(identity, ResultIdentity):
        raise ZeroRelayReviewTaskError("INPUT_INVALID")
    head = _reviewed_head(reviewed_head)
    payload = {
        "schema": _SCHEMA,
        "task_contract_ref": identity.task_contract_ref,
        "task_sha256": identity.task_sha256,
        "result_ref": identity.result_ref,
        "result_sha256": identity.result_sha256,
        "attempt_id": identity.attempt_id,
        "generation": identity.generation,
        "author_execution_id": identity.author_execution_id,
        "reviewed_head": head,
    }
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def deterministic_review_refs(identity: ResultIdentity, reviewed_head: str) -> ReviewTaskRefs:
    if not isinstance(identity, ResultIdentity):
        raise ZeroRelayReviewTaskError("INPUT_INVALID")
    digest = hashlib.sha256(canonical_review_bytes(identity, reviewed_head)).hexdigest()
    return ReviewTaskRefs(
        digest=digest,
        contract_ref=f"{_SCHEMA}:{digest}",
        task_path=f"runs/zra2-review-{digest}.md",
        result_ref=f"runs/zra2-review-result-{digest}.json",
    )


def render_review_task_markdown(identity: ResultIdentity, reviewed_head: str) -> str:
    if not isinstance(identity, ResultIdentity):
        raise ZeroRelayReviewTaskError("INPUT_INVALID")
    head = _reviewed_head(reviewed_head)
    refs = deterministic_review_refs(identity, head)
    return (
        "# ZRA-2 Independent Review Task\n"
        "\n"
        "Review the following accepted author result. This task is read-only.\n"
        "\n"
        "## Author result identity (exact)\n"
        f"- task contract ref: {identity.task_contract_ref}\n"
        f"- task sha256: {identity.task_sha256}\n"
        f"- result ref: {identity.result_ref}\n"
        f"- result sha256: {identity.result_sha256}\n"
        f"- attempt: {identity.attempt_id}\n"
        f"- repair generation: {identity.generation}\n"
        f"- author execution id: {identity.author_execution_id}\n"
        f"- reviewed head: {head}\n"
        f"- review identity: {refs.contract_ref}\n"
        "\n"
        "## Reviewer requirements\n"
        "- The reviewer execution MUST be independent from the author execution\n"
        "  identity above; identical execution ids are invalid.\n"
        "- Review target MUST be the exact reviewed HEAD bound above; ambient\n"
        "  repository state is not authority.\n"
        "- Bounded verdict vocabulary expected downstream: ACCEPTED or REJECTED\n"
        "  per the ZRA-2 Phase-A decision contract.\n"
        "- Reviewer prose is evidence only, never merge or completion authority.\n"
        "- External gates (merge/release) remain GPT/Conductor authority.\n"
    )


@dataclass(frozen=True, slots=True)
class MaterializedReviewTask:
    refs: ReviewTaskRefs
    reviewed_head: str
    persisted_sha256: str
    created: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "reviewed_head", _reviewed_head(self.reviewed_head))
        if not re.fullmatch(r"[0-9a-f]{64}", self.persisted_sha256):
            raise ZeroRelayReviewTaskError("REVIEW_TASK_SHA_INVALID")
        if not isinstance(self.created, bool):
            raise ZeroRelayReviewTaskError("REVIEW_TASK_CREATED_INVALID")


def _verify_persisted_review_task(
    filesystem: NativeFileSystem,
    *,
    refs: ReviewTaskRefs,
    content: str,
    content_sha256: str,
    content_mismatch_code: str,
) -> None:
    encoded = content.encode("utf-8")
    try:
        read = filesystem.read_text(refs.task_path)
    except NativeExecutionError as exc:
        raise ZeroRelayReviewTaskError("REVIEW_TASK_STATE_UNVERIFIABLE") from exc
    if read.relative_path != refs.task_path:
        raise ZeroRelayReviewTaskError("REVIEW_TASK_VERIFY_FAILED")
    if read.content != content:
        raise ZeroRelayReviewTaskError(content_mismatch_code)
    if read.size_bytes != len(encoded) or read.sha256 != content_sha256:
        raise ZeroRelayReviewTaskError("REVIEW_TASK_VERIFY_FAILED")


def materialize_review_task(
    filesystem: NativeFileSystem,
    identity: ResultIdentity,
    reviewed_head: str,
) -> MaterializedReviewTask:
    if not isinstance(filesystem, NativeFileSystem):
        raise ZeroRelayReviewTaskError("FILESYSTEM_INVALID")
    if not isinstance(identity, ResultIdentity):
        raise ZeroRelayReviewTaskError("INPUT_INVALID")
    head = _reviewed_head(reviewed_head)
    refs = deterministic_review_refs(identity, head)
    content, content_sha256 = _expected_content_sha(identity, head)
    encoded = content.encode("utf-8")
    try:
        result = filesystem.create_text_if_absent(refs.task_path, content)
    except NativeExecutionError as exc:
        if exc.code != "FILE_ALREADY_EXISTS":
            raise ZeroRelayReviewTaskError(exc.code) from exc
        _verify_persisted_review_task(
            filesystem,
            refs=refs,
            content=content,
            content_sha256=content_sha256,
            content_mismatch_code="REVIEW_TASK_COLLISION",
        )
        return MaterializedReviewTask(
            refs=refs,
            reviewed_head=head,
            persisted_sha256=content_sha256,
            created=False,
        )

    if (
        result.relative_path != refs.task_path
        or result.size_bytes != len(encoded)
        or result.sha256 != content_sha256
        or getattr(result, "created", None) is not True
    ):
        raise ZeroRelayReviewTaskError("REVIEW_TASK_VERIFY_FAILED")

    _verify_persisted_review_task(
        filesystem,
        refs=refs,
        content=content,
        content_sha256=content_sha256,
        content_mismatch_code="REVIEW_TASK_VERIFY_FAILED",
    )
    return MaterializedReviewTask(
        refs=refs,
        reviewed_head=head,
        persisted_sha256=content_sha256,
        created=True,
    )


@dataclass(frozen=True, slots=True)
class DirectReviewRoute:
    """Immutable C0b binding of one validated READ-only review dispatch.

    Phase C1 (WO201) consumes this after the reviewer execution and durable
    record exist; this value is NOT ``ReviewEvidence``.
    """

    role: str
    mutation_intent: str
    review_contract_ref: str
    review_task_path: str
    review_task_sha256: str
    review_result_ref: str
    author_execution_id: str
    author_result_sha256: str
    author_attempt_id: str
    author_generation: int
    author_digest: str
    reviewer_worker_id: str
    dispatch_execution_id: str
    provider_id: str
    model_id: str
    project_id: str
    worktree: str
    branch: str
    reviewed_head: str

    def __post_init__(self) -> None:
        if self.role != "independent-review" or self.mutation_intent != "READ_ONLY":
            raise ZeroRelayReviewTaskError("REVIEW_ROUTE_INVALID")


def bind_direct_review_route(
    route_task,
    review: MaterializedReviewTask,
    *,
    author: ResultIdentity,
    filesystem: NativeFileSystem,
) -> DirectReviewRoute:
    from .claude_code_harness import MutationIntent
    from .parallel_ready_execution import ParallelReadyTask
    from .worker_lease import LeaseMutationIntent

    if not isinstance(route_task, ParallelReadyTask):
        raise ZeroRelayReviewTaskError("INPUT_INVALID")
    if not isinstance(review, MaterializedReviewTask) or not isinstance(author, ResultIdentity):
        raise ZeroRelayReviewTaskError("INPUT_INVALID")
    if not isinstance(filesystem, NativeFileSystem):
        raise ZeroRelayReviewTaskError("FILESYSTEM_INVALID")

    packet = route_task.task_packet
    dispatch = route_task.harness_dispatch
    route_head = _reviewed_head(dispatch.expected_head)
    if review.reviewed_head != route_head:
        raise ZeroRelayReviewTaskError("REVIEW_HEAD_MISMATCH")

    expected_refs = deterministic_review_refs(author, route_head)
    if expected_refs != review.refs:
        raise ZeroRelayReviewTaskError("AUTHOR_IDENTITY_MISMATCH")
    expected_content, expected_sha256 = _expected_content_sha(author, route_head)
    if review.persisted_sha256 != expected_sha256:
        raise ZeroRelayReviewTaskError("REVIEW_TASK_VERIFY_FAILED")

    if windows_worktree_key(str(filesystem.root)) != windows_worktree_key(dispatch.worktree_path):
        raise ZeroRelayReviewTaskError("REVIEW_FILESYSTEM_ROOT_MISMATCH")

    expected_packet_path = ntpath.join(
        dispatch.worktree_path, *review.refs.task_path.split("/")
    )
    if windows_worktree_key(packet.path) != windows_worktree_key(expected_packet_path):
        raise ZeroRelayReviewTaskError("REVIEW_PACKET_PATH_MISMATCH")
    if (
        packet.task_contract_ref != review.refs.contract_ref
        or packet.sha256 != expected_sha256
    ):
        raise ZeroRelayReviewTaskError("REVIEW_PACKET_MISMATCH")
    if dispatch.task_contract_ref != review.refs.contract_ref:
        raise ZeroRelayReviewTaskError("REVIEW_DISPATCH_CONTRACT_MISMATCH")
    if dispatch.mutation_intent is not MutationIntent.READ_ONLY:
        raise ZeroRelayReviewTaskError("REVIEW_ROUTE_NOT_READ_ONLY")
    lease = route_task.lease_request
    if lease.mutation_intent is not LeaseMutationIntent.READ_ONLY:
        raise ZeroRelayReviewTaskError("REVIEW_LEASE_NOT_READ_ONLY")
    if lease.task_id != review.refs.contract_ref:
        raise ZeroRelayReviewTaskError("REVIEW_LEASE_TASK_MISMATCH")
    if not dispatch.expected_branch:
        raise ZeroRelayReviewTaskError("REVIEW_BRANCH_MISSING")
    if dispatch.evidence_destination_ref != review.refs.result_ref:
        raise ZeroRelayReviewTaskError("REVIEW_DESTINATION_MISMATCH")
    if dispatch.execution_id == author.author_execution_id:
        raise ZeroRelayReviewTaskError("AUTHOR_REVIEWER_NOT_DISTINCT")

    _verify_persisted_review_task(
        filesystem,
        refs=review.refs,
        content=expected_content,
        content_sha256=expected_sha256,
        content_mismatch_code="REVIEW_TASK_VERIFY_FAILED",
    )

    return DirectReviewRoute(
        role="independent-review",
        mutation_intent="READ_ONLY",
        review_contract_ref=review.refs.contract_ref,
        review_task_path=packet.path,
        review_task_sha256=expected_sha256,
        review_result_ref=review.refs.result_ref,
        author_execution_id=author.author_execution_id,
        author_result_sha256=author.result_sha256,
        author_attempt_id=author.attempt_id,
        author_generation=author.generation,
        author_digest=review.refs.digest,
        reviewer_worker_id=route_task.assignment.worker_id,
        dispatch_execution_id=dispatch.execution_id,
        provider_id=dispatch.provider_id,
        model_id=dispatch.model_id,
        project_id=dispatch.project_id,
        worktree=dispatch.worktree_path,
        branch=dispatch.expected_branch,
        reviewed_head=route_head,
    )
