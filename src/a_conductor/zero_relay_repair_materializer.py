"""Deterministic ZRA-2 repair task materialization.

This module is intentionally a thin composition seam. It renders the already
validated ``AgentRepairRequest`` through the existing renderer, persists the
exact UTF-8 bytes through ``NativeFileSystem``, and returns the existing
``TaskPacketFile`` identity. It owns no review, retry, scheduler, lease, or
provider lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

from .agent_change_packets import AgentRepairRequest, build_repair_task_markdown
from .claude_code_harness import TaskPacketFile
from .native_execution import (
    NativeExecutionError,
    NativeFileSystem,
    NativeReadResult,
)


_SHA256_RE = re.compile(r"[0-9a-fA-F]{64}")
_REASON_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_SCHEMA = "zra2-repair-materializer/v1"
_PATH_PREFIX = "runs/zra2-repair-"


class RepairTaskMaterializationError(RuntimeError):
    """Stable code-only materialization failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _sha256(value: str, *, code: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise RepairTaskMaterializationError(code)
    return value.casefold()


def _review_reason_id(value: str) -> str:
    if not isinstance(value, str) or not _REASON_ID_RE.fullmatch(value):
        raise RepairTaskMaterializationError("REVIEW_REASON_ID_INVALID")
    return value


@dataclass(frozen=True, slots=True)
class RepairTaskMaterializationRequest:
    repair_request: AgentRepairRequest
    rejected_task_sha256: str
    rejected_result_sha256: str
    review_reason_id: str
    generation: int

    def __post_init__(self) -> None:
        if not isinstance(self.repair_request, AgentRepairRequest):
            raise RepairTaskMaterializationError("REPAIR_REQUEST_INVALID")
        object.__setattr__(
            self,
            "rejected_task_sha256",
            _sha256(
                self.rejected_task_sha256,
                code="REJECTED_TASK_SHA256_INVALID",
            ),
        )
        object.__setattr__(
            self,
            "rejected_result_sha256",
            _sha256(
                self.rejected_result_sha256,
                code="REJECTED_RESULT_SHA256_INVALID",
            ),
        )
        object.__setattr__(
            self,
            "review_reason_id",
            _review_reason_id(self.review_reason_id),
        )
        if isinstance(self.generation, bool) or self.generation != 1 or not isinstance(
            self.generation, int
        ):
            raise RepairTaskMaterializationError("REPAIR_GENERATION_INVALID")


def _identity_digest(
    request: RepairTaskMaterializationRequest,
    *,
    rendered_sha256: str,
) -> str:
    repair = request.repair_request
    document = {
        "schema": _SCHEMA,
        "generation": request.generation,
        "rejected_task_sha256": request.rejected_task_sha256,
        "rejected_result_sha256": request.rejected_result_sha256,
        "review_reason_id": request.review_reason_id,
        "rendered_task_sha256": rendered_sha256,
        "repair_request": {
            "task_id": repair.task_id,
            "provider_id": repair.provider_id,
            "model_id": repair.model_id,
            "base_head": repair.base_head,
            "source_result_ref": repair.source_result_ref,
            "result_destination_ref": repair.result_destination_ref,
            "review_findings": list(repair.review_findings),
        },
    }
    encoded = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _packet_from_read(
    read: NativeReadResult,
    *,
    path: str,
    content: str,
    content_sha256: str,
    task_contract_ref: str,
    content_mismatch_code: str,
) -> TaskPacketFile:
    encoded = content.encode("utf-8")
    if read.relative_path != path:
        raise RepairTaskMaterializationError("REPAIR_TASK_VERIFY_FAILED")
    if read.content != content:
        raise RepairTaskMaterializationError(content_mismatch_code)
    if read.size_bytes != len(encoded) or read.sha256 != content_sha256:
        raise RepairTaskMaterializationError("REPAIR_TASK_VERIFY_FAILED")
    return TaskPacketFile(
        task_contract_ref=task_contract_ref,
        path=path,
        sha256=content_sha256,
    )


def _read_existing(
    filesystem: NativeFileSystem,
    *,
    path: str,
    content: str,
    content_sha256: str,
    task_contract_ref: str,
) -> TaskPacketFile | None:
    try:
        read = filesystem.read_text(path)
    except NativeExecutionError as exc:
        if exc.code == "PATH_NOT_FOUND":
            return None
        raise
    return _packet_from_read(
        read,
        path=path,
        content=content,
        content_sha256=content_sha256,
        task_contract_ref=task_contract_ref,
        content_mismatch_code="REPAIR_TASK_COLLISION",
    )


def materialize_repair_task(
    request: RepairTaskMaterializationRequest,
    *,
    filesystem: NativeFileSystem,
) -> TaskPacketFile:
    """Materialize exactly one deterministic generation-1 repair task packet."""

    if not isinstance(request, RepairTaskMaterializationRequest):
        raise RepairTaskMaterializationError("MATERIALIZATION_REQUEST_INVALID")
    if not isinstance(filesystem, NativeFileSystem):
        raise RepairTaskMaterializationError("FILESYSTEM_INVALID")

    content = build_repair_task_markdown(request.repair_request)
    content_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
    identity_sha256 = _identity_digest(request, rendered_sha256=content_sha256)
    path = f"{_PATH_PREFIX}{identity_sha256}.md"
    task_contract_ref = f"zra2-repair-v1:{identity_sha256}"

    existing = _read_existing(
        filesystem,
        path=path,
        content=content,
        content_sha256=content_sha256,
        task_contract_ref=task_contract_ref,
    )
    if existing is not None:
        return existing

    try:
        written = filesystem.create_text_if_absent(path, content)
    except NativeExecutionError as exc:
        if exc.code != "FILE_ALREADY_EXISTS":
            raise
        raced = _read_existing(
            filesystem,
            path=path,
            content=content,
            content_sha256=content_sha256,
            task_contract_ref=task_contract_ref,
        )
        if raced is None:
            raise RepairTaskMaterializationError("REPAIR_TASK_VERIFY_FAILED") from exc
        return raced

    if (
        written.relative_path != path
        or written.size_bytes != len(content.encode("utf-8"))
        or written.sha256 != content_sha256
    ):
        raise RepairTaskMaterializationError("REPAIR_TASK_VERIFY_FAILED")

    verified = filesystem.read_text(path)
    return _packet_from_read(
        verified,
        path=path,
        content=content,
        content_sha256=content_sha256,
        task_contract_ref=task_contract_ref,
        content_mismatch_code="REPAIR_TASK_VERIFY_FAILED",
    )
