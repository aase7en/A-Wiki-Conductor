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
from .provider_policy import ProviderPolicyTaskSecurity
from .zero_relay import ResultIdentity

_SCHEMA = "zra2-review-v1"
_V2_SCHEMA = "zra2-review-v2"
_V2_RESULT_SCHEMA = "zra2-review-result-v2"
_V2_MAX_RESPONSE_BYTES = 32 * 1024
_V2_MAX_FINDINGS = 64
_V2_MAX_FINDING_CHARS = 2048


_HEAD_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


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



def _v2_text(value: object, code: str, *, max_chars: int = 512) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ZeroRelayReviewTaskError(code)
    if len(value) > max_chars or "\x00" in value or "\r" in value or "\n" in value:
        raise ZeroRelayReviewTaskError(code)
    return value


def _v2_security_payload(security: ProviderPolicyTaskSecurity) -> dict[str, object]:
    if not isinstance(security, ProviderPolicyTaskSecurity):
        raise ZeroRelayReviewTaskError("REVIEW_V2_SECURITY_INVALID")
    return {
        "privacy_class": security.privacy_class.value,
        "network_policy": security.network_policy.value,
        "network_allowlist": list(security.network_allowlist),
        "secret_access": security.secret_access,
    }


def _v2_response_contract_payload() -> dict[str, object]:
    return {
        "schema": _V2_RESULT_SCHEMA,
        "verdicts": ["ACCEPTED", "REJECTED"],
        "max_response_bytes": _V2_MAX_RESPONSE_BYTES,
        "max_findings": _V2_MAX_FINDINGS,
        "max_finding_chars": _V2_MAX_FINDING_CHARS,
    }


def canonical_review_v2_bytes(
    identity: ResultIdentity,
    reviewed_head: str,
    *,
    project_id: str,
    security: ProviderPolicyTaskSecurity,
) -> bytes:
    """Canonical identity-bearing bytes for review protocol v2.

    This does not replace v1. It adds trusted project identity plus the task's
    canonical security policy to the deterministic review identity. Provider/model/
    endpoint/generation runtime facts remain outside these task bytes.
    """
    if not isinstance(identity, ResultIdentity):
        raise ZeroRelayReviewTaskError("INPUT_INVALID")
    head = _reviewed_head(reviewed_head)
    project = _v2_text(project_id, "REVIEW_PROJECT_INVALID", max_chars=128)
    security_payload = _v2_security_payload(security)
    payload = {
        "schema": _V2_SCHEMA,
        "project_id": project,
        "task_contract_ref": identity.task_contract_ref,
        "task_sha256": identity.task_sha256,
        "result_ref": identity.result_ref,
        "result_sha256": identity.result_sha256,
        "attempt_id": identity.attempt_id,
        "generation": identity.generation,
        "author_execution_id": identity.author_execution_id,
        "reviewed_head": head,
        "security": security_payload,
        "response_contract": _v2_response_contract_payload(),
    }
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def deterministic_review_v2_refs(
    identity: ResultIdentity,
    reviewed_head: str,
    *,
    project_id: str,
    security: ProviderPolicyTaskSecurity,
) -> ReviewTaskRefs:
    if not isinstance(identity, ResultIdentity):
        raise ZeroRelayReviewTaskError("INPUT_INVALID")
    digest = hashlib.sha256(
        canonical_review_v2_bytes(
            identity, reviewed_head, project_id=project_id, security=security
        )
    ).hexdigest()
    return ReviewTaskRefs(
        digest=digest,
        contract_ref=f"runs/zra2-review-v2-{digest}.task.json",
        task_path=f"runs/zra2-review-v2-{digest}.md",
        result_ref=f"runs/zra2-review-result-v2-{digest}.json",
    )


def render_review_v2_task_markdown(
    identity: ResultIdentity,
    reviewed_head: str,
    *,
    project_id: str,
    security: ProviderPolicyTaskSecurity,
) -> str:
    if not isinstance(identity, ResultIdentity):
        raise ZeroRelayReviewTaskError("INPUT_INVALID")
    head = _reviewed_head(reviewed_head)
    project = _v2_text(project_id, "REVIEW_PROJECT_INVALID", max_chars=128)
    refs = deterministic_review_v2_refs(
        identity, head, project_id=project, security=security
    )
    return (
        "# ZRA-2 Independent Review Task - protocol v2\n"
        "\n"
        "This is a READ_ONLY independent review. Do not mutate repository or runtime state.\n"
        f"Project: {project}\n"
        f"Reviewed HEAD: {head}\n"
        f"Review authority contract: {refs.contract_ref}\n"
        f"Semantic result destination: {refs.result_ref}\n"
        "\n"
        "## Exact author result identity\n"
        f"- task_contract_ref: {identity.task_contract_ref}\n"
        f"- task_sha256: {identity.task_sha256}\n"
        f"- result_ref: {identity.result_ref}\n"
        f"- result_sha256: {identity.result_sha256}\n"
        f"- attempt_id: {identity.attempt_id}\n"
        f"- generation: {identity.generation}\n"
        f"- author_execution_id: {identity.author_execution_id}\n"
        "\n"
        "## Required whole response\n"
        "Return JSON only. No Markdown fence, prefix, suffix, explanation, or extra keys.\n"
        f"The response schema is {_V2_RESULT_SCHEMA}. Verdict is exactly ACCEPTED or REJECTED.\n"
        f"Read {refs.contract_ref} and echo metadata.review_prompt_sha256 as review_task_sha256.\n"
        "The exact object keys are: schema, review_contract_ref, reviewed_head, "
        "review_task_sha256, verdict, findings.\n"
        f"Whole response must be <= {_V2_MAX_RESPONSE_BYTES} bytes.\n"
        "findings is a JSON array of bounded plain strings only; findings never grant "
        "ready/merge/retry/complete authority.\n"
        "External merge/release authority remains GPT/A-Sunday Conductor.\n"
    )


def canonical_review_v2_authority_bytes(
    identity: ResultIdentity,
    reviewed_head: str,
    *,
    project_id: str,
    security: ProviderPolicyTaskSecurity,
    prompt_path: str,
    prompt_sha256: str,
    result_ref: str,
) -> bytes:
    if not isinstance(identity, ResultIdentity):
        raise ZeroRelayReviewTaskError("INPUT_INVALID")
    head = _reviewed_head(reviewed_head)
    project = _v2_text(project_id, "REVIEW_PROJECT_INVALID", max_chars=128)
    security_payload = _v2_security_payload(security)
    refs = deterministic_review_v2_refs(
        identity, head, project_id=project, security=security
    )
    prompt = _v2_text(prompt_path, "REVIEW_V2_PROMPT_PATH_INVALID")
    result = _v2_text(result_ref, "REVIEW_V2_RESULT_REF_INVALID")
    if prompt != refs.task_path or result != refs.result_ref:
        raise ZeroRelayReviewTaskError("REVIEW_V2_REF_MISMATCH")
    if not isinstance(prompt_sha256, str) or not _SHA256_RE.fullmatch(prompt_sha256):
        raise ZeroRelayReviewTaskError("REVIEW_V2_PROMPT_SHA_INVALID")
    prompt_sha = prompt_sha256.casefold()
    payload = {
        "schema_version": "1.0.0",
        "task_id": f"zra2-review-v2-{refs.digest}",
        "work_order_ref": refs.contract_ref,
        "goal": "Independently review the exact bound author result and return one strict JSON verdict.",
        "task_type": "independent-review",
        "risk_class": "HIGH",
        "authority": {
            "requested_by": "A-Sunday Conductor",
            "approved_by": None,
            "approval_ref": None,
            "mutation_allowed": False,
            "human_approval_required": False,
        },
        "target": {
            "project_id": project,
            "repository_identity_ref": None,
            "expected_worktree_path": None,
            "expected_branch": None,
            "expected_head": head,
            "identity_policy": "EXACT",
        },
        "scope": {
            "allowed_files": ["**"],
            "forbidden_files": [],
            "allowed_commands": ["read-only repository inspection", "targeted verification"],
            "forbidden_commands": ["repository mutation", "destructive operations"],
            "max_changed_files": 0,
            "max_diff_bytes": 0,
            "scope_growth": "FORBIDDEN",
        },
        "acceptance": {
            "criteria": ["Return one exact zra2-review-result-v2 JSON object."],
            "verify_commands": [],
            "review_required": False,
            "required_review_class": None,
        },
        "security": security_payload,
        "routing": {
            "required_capabilities": ["repository-read", "code-review"],
            "preferred_surface_traits": {
                "supports_long_running": True,
                "supports_resume": True,
                "supports_background_execution": True,
                "supports_repo_tools": True,
                "requires_human_presence": False,
                "max_safe_transaction_scope": "READ_ONLY",
            },
        },
        "budget": {
            "max_elapsed_seconds": 3600,
            "max_input_tokens": None,
            "max_output_tokens": None,
            "max_estimated_cost_usd": None,
        },
        "retry_policy": {
            "max_attempts": 1,
            "max_identical_failures": 1,
            "on_lease_expiry": "RECOVERY_REQUIRED",
        },
        "escalation": {
            "conditions": [
                "ARCHITECTURE_DECISION",
                "SECURITY_BOUNDARY_CHANGE",
                "SCOPE_EXPANSION",
                "IDENTITY_MISMATCH",
                "UNKNOWN_RECOVERY_STATE",
            ],
        },
        "required_evidence": ["REPOSITORY_IDENTITY", "REVIEW_RESULT", "CHECKSUM"],
        "metadata": {
            "review_protocol": _V2_SCHEMA,
            "review_result_schema": _V2_RESULT_SCHEMA,
            "review_identity_digest": refs.digest,
            "task_contract_ref": identity.task_contract_ref,
            "task_sha256": identity.task_sha256,
            "author_result_ref": identity.result_ref,
            "author_result_sha256": identity.result_sha256,
            "author_attempt_id": identity.attempt_id,
            "author_generation": identity.generation,
            "author_execution_id": identity.author_execution_id,
            "reviewed_head": head,
            "review_prompt_path": prompt,
            "review_prompt_sha256": prompt_sha,
            "semantic_result_ref": result,
            "verdicts": ["ACCEPTED", "REJECTED"],
            "max_response_bytes": _V2_MAX_RESPONSE_BYTES,
            "max_findings": _V2_MAX_FINDINGS,
            "max_finding_chars": _V2_MAX_FINDING_CHARS,
        },
    }
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class MaterializedReviewV2Task:
    refs: ReviewTaskRefs
    reviewed_head: str
    project_id: str
    security: ProviderPolicyTaskSecurity
    prompt_sha256: str
    authority_sha256: str
    created_prompt: bool
    created_authority: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "reviewed_head", _reviewed_head(self.reviewed_head))
        object.__setattr__(self, "project_id", _v2_text(self.project_id, "REVIEW_PROJECT_INVALID", max_chars=128))
        if not isinstance(self.security, ProviderPolicyTaskSecurity):
            raise ZeroRelayReviewTaskError("REVIEW_V2_SECURITY_INVALID")
        for value in (self.prompt_sha256, self.authority_sha256):
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ZeroRelayReviewTaskError("REVIEW_V2_SHA_INVALID")
        if not isinstance(self.created_prompt, bool) or not isinstance(self.created_authority, bool):
            raise ZeroRelayReviewTaskError("REVIEW_V2_CREATED_INVALID")


def _v2_publish_exact(
    filesystem: NativeFileSystem,
    *,
    relative_path: str,
    content: str,
    collision_code: str,
) -> tuple[str, bool]:
    raw = content.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    try:
        result = filesystem.create_text_if_absent(relative_path, content)
        created = True
        if (
            result.relative_path != relative_path
            or result.size_bytes != len(raw)
            or result.sha256 != digest
            or getattr(result, "created", None) is not True
        ):
            raise ZeroRelayReviewTaskError("REVIEW_V2_VERIFY_FAILED")
    except NativeExecutionError as exc:
        if exc.code != "FILE_ALREADY_EXISTS":
            raise ZeroRelayReviewTaskError(exc.code) from exc
        created = False
    try:
        read = filesystem.read_text(relative_path)
    except NativeExecutionError as exc:
        raise ZeroRelayReviewTaskError("REVIEW_V2_STATE_UNVERIFIABLE") from exc
    if read.relative_path != relative_path:
        raise ZeroRelayReviewTaskError("REVIEW_V2_VERIFY_FAILED")
    if read.content != content:
        raise ZeroRelayReviewTaskError(collision_code)
    if read.size_bytes != len(raw) or read.sha256 != digest:
        raise ZeroRelayReviewTaskError("REVIEW_V2_VERIFY_FAILED")
    return digest, created




def _v2_read_optional(filesystem: NativeFileSystem, relative_path: str):
    try:
        return filesystem.read_text(relative_path)
    except NativeExecutionError as exc:
        if exc.code in {"PATH_NOT_FOUND", "FILE_NOT_FOUND"}:
            return None
        raise ZeroRelayReviewTaskError("REVIEW_V2_STATE_UNVERIFIABLE") from exc


def materialize_review_v2_task(
    filesystem: NativeFileSystem,
    identity: ResultIdentity,
    reviewed_head: str,
    *,
    project_id: str,
    security: ProviderPolicyTaskSecurity,
) -> MaterializedReviewV2Task:
    if not isinstance(filesystem, NativeFileSystem):
        raise ZeroRelayReviewTaskError("FILESYSTEM_INVALID")
    if not isinstance(identity, ResultIdentity):
        raise ZeroRelayReviewTaskError("INPUT_INVALID")
    head = _reviewed_head(reviewed_head)
    project = _v2_text(project_id, "REVIEW_PROJECT_INVALID", max_chars=128)
    _v2_security_payload(security)
    refs = deterministic_review_v2_refs(
        identity, head, project_id=project, security=security
    )
    preexisting_prompt = _v2_read_optional(filesystem, refs.task_path)
    preexisting_authority = _v2_read_optional(filesystem, refs.contract_ref)
    if preexisting_authority is not None and preexisting_prompt is None:
        # The first prompt read may race an exact publisher that completes the
        # canonical prompt->authority pair before our authority read. Re-read
        # only; never create the missing prompt while adjudicating this state.
        preexisting_prompt = _v2_read_optional(filesystem, refs.task_path)
        if preexisting_prompt is None:
            raise ZeroRelayReviewTaskError("REVIEW_V2_AUTHORITY_WITHOUT_PROMPT")
    prompt = render_review_v2_task_markdown(
        identity, head, project_id=project, security=security
    )
    prompt_sha, created_prompt = _v2_publish_exact(
        filesystem,
        relative_path=refs.task_path,
        content=prompt,
        collision_code="REVIEW_V2_PROMPT_COLLISION",
    )
    authority = canonical_review_v2_authority_bytes(
        identity,
        head,
        project_id=project,
        security=security,
        prompt_path=refs.task_path,
        prompt_sha256=prompt_sha,
        result_ref=refs.result_ref,
    ).decode("utf-8")
    authority_sha, created_authority = _v2_publish_exact(
        filesystem,
        relative_path=refs.contract_ref,
        content=authority,
        collision_code="REVIEW_V2_AUTHORITY_COLLISION",
    )
    return MaterializedReviewV2Task(
        refs=refs,
        reviewed_head=head,
        project_id=project,
        security=security,
        prompt_sha256=prompt_sha,
        authority_sha256=authority_sha,
        created_prompt=created_prompt,
        created_authority=created_authority,
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


@dataclass(frozen=True, slots=True)
class DirectReviewV2Route(DirectReviewRoute):
    """Review-v2 route carrying the complete immutable author identity.

    V1 remains the original ``DirectReviewRoute`` shape. C1 requires this v2
    extension so caller-supplied author fields cannot be rebound after the
    canonical review task was materialized and routed.
    """

    author_task_contract_ref: str
    author_task_sha256: str
    author_result_ref: str

    def __post_init__(self) -> None:
        DirectReviewRoute.__post_init__(self)
        _v2_text(self.author_task_contract_ref, "REVIEW_V2_AUTHOR_CONTRACT_INVALID")
        _v2_text(self.author_result_ref, "REVIEW_V2_AUTHOR_RESULT_REF_INVALID")
        if not isinstance(self.author_task_sha256, str) or not _SHA256_RE.fullmatch(
            self.author_task_sha256
        ):
            raise ZeroRelayReviewTaskError("REVIEW_V2_AUTHOR_TASK_SHA_INVALID")


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



def _verify_persisted_review_v2_task(
    filesystem: NativeFileSystem,
    *,
    review: MaterializedReviewV2Task,
    author: ResultIdentity,
    reviewed_head: str,
) -> str:
    expected_refs = deterministic_review_v2_refs(
        author,
        reviewed_head,
        project_id=review.project_id,
        security=review.security,
    )
    if expected_refs != review.refs:
        raise ZeroRelayReviewTaskError("AUTHOR_IDENTITY_MISMATCH")
    prompt = render_review_v2_task_markdown(
        author,
        reviewed_head,
        project_id=review.project_id,
        security=review.security,
    )
    prompt_raw = prompt.encode("utf-8")
    prompt_sha = hashlib.sha256(prompt_raw).hexdigest()
    if review.prompt_sha256 != prompt_sha:
        raise ZeroRelayReviewTaskError("REVIEW_V2_PROMPT_SHA_MISMATCH")
    try:
        prompt_read = filesystem.read_text(review.refs.task_path)
    except NativeExecutionError as exc:
        raise ZeroRelayReviewTaskError("REVIEW_V2_STATE_UNVERIFIABLE") from exc
    if prompt_read.relative_path != review.refs.task_path:
        raise ZeroRelayReviewTaskError("REVIEW_V2_VERIFY_FAILED")
    if prompt_read.content != prompt:
        raise ZeroRelayReviewTaskError("REVIEW_V2_PROMPT_COLLISION")
    if prompt_read.size_bytes != len(prompt_raw) or prompt_read.sha256 != prompt_sha:
        raise ZeroRelayReviewTaskError("REVIEW_V2_VERIFY_FAILED")

    authority = canonical_review_v2_authority_bytes(
        author,
        reviewed_head,
        project_id=review.project_id,
        security=review.security,
        prompt_path=review.refs.task_path,
        prompt_sha256=prompt_sha,
        result_ref=review.refs.result_ref,
    ).decode("utf-8")
    authority_raw = authority.encode("utf-8")
    authority_sha = hashlib.sha256(authority_raw).hexdigest()
    if review.authority_sha256 != authority_sha:
        raise ZeroRelayReviewTaskError("REVIEW_V2_AUTHORITY_SHA_MISMATCH")
    try:
        authority_read = filesystem.read_text(review.refs.contract_ref)
    except NativeExecutionError as exc:
        raise ZeroRelayReviewTaskError("REVIEW_V2_STATE_UNVERIFIABLE") from exc
    if authority_read.relative_path != review.refs.contract_ref:
        raise ZeroRelayReviewTaskError("REVIEW_V2_VERIFY_FAILED")
    if authority_read.content != authority:
        raise ZeroRelayReviewTaskError("REVIEW_V2_AUTHORITY_COLLISION")
    if authority_read.size_bytes != len(authority_raw) or authority_read.sha256 != authority_sha:
        raise ZeroRelayReviewTaskError("REVIEW_V2_VERIFY_FAILED")
    return prompt_sha


def bind_direct_review_v2_route(
    route_task,
    review: MaterializedReviewV2Task,
    *,
    author: ResultIdentity,
    filesystem: NativeFileSystem,
) -> DirectReviewV2Route:
    """Bind review-v2 publication to the existing provider/dispatch authorities.

    This function mints no provider, lease, dispatch, execution, or review
    lifecycle state. It only cross-checks an already-validated ParallelReadyTask
    against the persisted v2 prompt/authority pair before returning the same
    immutable DirectReviewRoute consumed by WO223 C1.
    """
    from .claude_code_harness import MutationIntent
    from .parallel_ready_execution import ParallelReadyTask
    from .worker_lease import LeaseMutationIntent
    from .zcode_runner import ZCodeRunError, ZCodeTaskPacketIdentity

    if not isinstance(route_task, ParallelReadyTask):
        raise ZeroRelayReviewTaskError("INPUT_INVALID")
    if not isinstance(review, MaterializedReviewV2Task) or not isinstance(author, ResultIdentity):
        raise ZeroRelayReviewTaskError("INPUT_INVALID")
    if not isinstance(filesystem, NativeFileSystem):
        raise ZeroRelayReviewTaskError("FILESYSTEM_INVALID")

    packet = route_task.task_packet
    dispatch = route_task.harness_dispatch
    route_head = _reviewed_head(dispatch.expected_head)
    if review.reviewed_head != route_head:
        raise ZeroRelayReviewTaskError("REVIEW_HEAD_MISMATCH")
    if review.project_id != dispatch.project_id:
        raise ZeroRelayReviewTaskError("REVIEW_V2_PROJECT_MISMATCH")

    prompt_sha = _verify_persisted_review_v2_task(
        filesystem, review=review, author=author, reviewed_head=route_head
    )
    if windows_worktree_key(str(filesystem.root)) != windows_worktree_key(dispatch.worktree_path):
        raise ZeroRelayReviewTaskError("REVIEW_FILESYSTEM_ROOT_MISMATCH")
    expected_packet_path = ntpath.join(
        dispatch.worktree_path, *review.refs.task_path.split("/")
    )
    if windows_worktree_key(packet.path) != windows_worktree_key(expected_packet_path):
        raise ZeroRelayReviewTaskError("REVIEW_PACKET_PATH_MISMATCH")
    if packet.task_contract_ref != review.refs.contract_ref or packet.sha256 != prompt_sha:
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

    requirement = route_task.provider_requirement
    if (
        requirement is None
        or route_task.provider_endpoint is None
        or route_task.provider_security is None
        or route_task.expected_configuration_generation is None
    ):
        raise ZeroRelayReviewTaskError("REVIEW_V2_PROVIDER_AUTHORITY_MISSING")
    if route_task.provider_security != review.security or requirement.provider_security != review.security:
        raise ZeroRelayReviewTaskError("REVIEW_V2_PROVIDER_SECURITY_MISMATCH")
    if requirement.task_contract_ref != review.refs.contract_ref:
        raise ZeroRelayReviewTaskError("REVIEW_V2_PROVIDER_CONTRACT_MISMATCH")
    if requirement.authority_sha256 != review.authority_sha256:
        raise ZeroRelayReviewTaskError("REVIEW_V2_PROVIDER_AUTHORITY_MISMATCH")
    if requirement.expected_configuration_generation != route_task.expected_configuration_generation:
        raise ZeroRelayReviewTaskError("REVIEW_V2_PROVIDER_GENERATION_MISMATCH")
    if route_task.dispatch_request.work_order_ref != review.refs.contract_ref:
        raise ZeroRelayReviewTaskError("REVIEW_V2_WORK_ORDER_MISMATCH")
    if route_task.dispatch_request.operation_ref != requirement.operation_ref:
        raise ZeroRelayReviewTaskError("REVIEW_V2_PROVIDER_OPERATION_MISMATCH")
    try:
        packet_identity = ZCodeTaskPacketIdentity.from_task_packet_file(
            packet, trusted_root=dispatch.worktree_path
        )
    except ZCodeRunError as exc:
        raise ZeroRelayReviewTaskError("REVIEW_V2_PACKET_IDENTITY_INVALID") from exc
    if requirement.base_operation_ref != packet_identity.canonical_operation_ref():
        raise ZeroRelayReviewTaskError("REVIEW_V2_PROVIDER_OPERATION_MISMATCH")

    return DirectReviewV2Route(
        role="independent-review",
        mutation_intent="READ_ONLY",
        review_contract_ref=review.refs.contract_ref,
        review_task_path=packet.path,
        review_task_sha256=prompt_sha,
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
        author_task_contract_ref=author.task_contract_ref,
        author_task_sha256=author.task_sha256,
        author_result_ref=author.result_ref,
    )
