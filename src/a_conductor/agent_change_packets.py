"""Lease-bound structured change packets for multi-agent implementation lanes.

Models propose complete file replacements. Only this deterministic boundary may
materialize them after identity, lease, scope, and content-precondition checks.
It owns no scheduler, provider, retry loop, Git mutation, or lease lifecycle.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatchcase
from pathlib import PurePosixPath
from typing import Callable, Protocol

from .native_execution import NativeExecutionError, NativeFileSystem
from .registry import windows_worktree_key
from .worker_lease import LeaseHealth, LeaseHealthKind, LeaseMutationIntent, WorkerLeaseError

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_ALLOWED_STATUSES = frozenset({"CHANGES_PROPOSED", "NO_CHANGES", "BLOCKED"})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LeaseHealthReader(Protocol):
    def inspect_health(self, lease_id: str, *, now: object) -> LeaseHealth: ...


class AgentChangeError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _text(value: str, field: str, *, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value or len(value) > max_length:
        raise ValueError(f"{field} is invalid")
    return value.strip()


def _path(value: str) -> str:
    raw = _text(value, "path", max_length=1024).replace("\\", "/")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or ".." in pure.parts or raw.startswith("./"):
        raise ValueError("path is invalid")
    return pure.as_posix()


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatchcase(path, pattern.replace("\\", "/")) for pattern in patterns)


@dataclass(frozen=True, slots=True)
class AgentFileChange:
    path: str
    content: str
    expected_sha256: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _path(self.path))
        if not isinstance(self.content, str):
            raise ValueError("content is invalid")
        if self.expected_sha256 is not None:
            if not _SHA256_RE.fullmatch(self.expected_sha256):
                raise ValueError("expected_sha256 is invalid")
            object.__setattr__(self, "expected_sha256", self.expected_sha256.casefold())


@dataclass(frozen=True, slots=True)
class AgentResultPacket:
    task_id: str
    provider_id: str
    model_id: str
    status: str
    base_head: str
    changes: tuple[AgentFileChange, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_id", _text(self.task_id, "task_id", max_length=128))
        object.__setattr__(self, "provider_id", _text(self.provider_id, "provider_id", max_length=128))
        object.__setattr__(self, "model_id", _text(self.model_id, "model_id", max_length=128))
        if self.status not in _ALLOWED_STATUSES:
            raise ValueError("status is invalid")
        if not re.fullmatch(r"[0-9a-fA-F]{7,64}", self.base_head):
            raise ValueError("base_head is invalid")
        object.__setattr__(self, "base_head", self.base_head.casefold())
        changes = tuple(self.changes)
        if any(not isinstance(item, AgentFileChange) for item in changes):
            raise ValueError("changes are invalid")
        if len({item.path for item in changes}) != len(changes):
            raise ValueError("change paths must be unique")
        if len(changes) > 1:
            raise ValueError("one file change per task is supported")
        if self.status == "CHANGES_PROPOSED" and not changes:
            raise ValueError("changes are required")
        if self.status != "CHANGES_PROPOSED" and changes:
            raise ValueError("changes are forbidden for this status")
        object.__setattr__(self, "changes", changes)
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(_text(item, "evidence_ref", max_length=512) for item in self.evidence_refs),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "status": self.status,
            "base_head": self.base_head,
            "changes": [
                {
                    "path": item.path,
                    "content": item.content,
                    "expected_sha256": item.expected_sha256,
                }
                for item in self.changes
            ],
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class AgentChangeApplyResult:
    changed_paths: tuple[str, ...]


class AgentChangeApplier:
    def __init__(self, *, filesystem: NativeFileSystem, lease_store: LeaseHealthReader,
                 clock: Callable[[], object] = _utc_now) -> None:
        if not isinstance(filesystem, NativeFileSystem):
            raise ValueError("filesystem must be NativeFileSystem")
        if not hasattr(lease_store, "inspect_health"):
            raise ValueError("lease_store must inspect lease health")
        if not callable(clock):
            raise ValueError("clock must be callable")
        self._filesystem = filesystem
        self._lease_store = lease_store
        self._clock = clock

    def apply(
        self,
        packet: AgentResultPacket,
        lease_id: str,
        *,
        session_id: str,
        task_id: str,
        actual_head: str,
    ) -> AgentChangeApplyResult:
        if not isinstance(packet, AgentResultPacket):
            raise ValueError("packet is required")
        try:
            health = self._lease_store.inspect_health(lease_id, now=self._clock())
        except WorkerLeaseError as exc:
            raise AgentChangeError("LEASE_HEALTH_UNAVAILABLE") from exc
        if not isinstance(health, LeaseHealth) or health.kind is not LeaseHealthKind.ACTIVE:
            raise AgentChangeError("LEASE_NOT_ACTIVE")
        lease = health.lease
        if lease.session_id != session_id or lease.task_id != task_id or packet.task_id != task_id:
            raise AgentChangeError("LEASE_OWNER_MISMATCH")
        if windows_worktree_key(str(self._filesystem.root)) != windows_worktree_key(lease.worktree_key):
            raise AgentChangeError("WORKTREE_MISMATCH")
        if lease.mutation_intent is not LeaseMutationIntent.MUTATION:
            raise AgentChangeError("LEASE_NOT_MUTATING")
        if lease.released_at is not None or lease.quarantined_at is not None:
            raise AgentChangeError("LEASE_NOT_ACTIVE")
        expected_head = lease.expected_head.casefold()
        if packet.base_head != expected_head or actual_head.casefold() != expected_head:
            raise AgentChangeError("HEAD_MISMATCH")
        if packet.status != "CHANGES_PROPOSED":
            return AgentChangeApplyResult(())

        # Preflight every change before the first write. This makes policy failures
        # all-or-nothing; NativeFileSystem still provides per-file TOCTOU protection.
        for change in packet.changes:
            if _matches(change.path, lease.forbidden_scope):
                raise AgentChangeError("CHANGE_SCOPE_DENIED")
            if not _matches(change.path, lease.mutable_scope):
                raise AgentChangeError("CHANGE_SCOPE_DENIED")
            try:
                current = self._filesystem.read_text(change.path)
            except NativeExecutionError as exc:
                if exc.code == "PATH_NOT_FOUND":
                    current = None
                else:
                    raise AgentChangeError("CHANGE_PREFLIGHT_FAILED") from exc
            if current is not None and change.expected_sha256 is None:
                raise AgentChangeError("CHANGE_PRECONDITION_REQUIRED")
            if current is None and change.expected_sha256 is not None:
                raise AgentChangeError("CHANGE_PRECONDITION_FAILED")
            if current is not None and current.sha256 != change.expected_sha256:
                raise AgentChangeError("CHANGE_PRECONDITION_FAILED")

        changed: list[str] = []
        try:
            for change in packet.changes:
                result = self._filesystem.write_text(
                    change.path,
                    change.content,
                    expected_sha256=change.expected_sha256,
                )
                changed.append(result.relative_path)
        except NativeExecutionError as exc:
            raise AgentChangeError("CHANGE_APPLY_FAILED") from exc
        return AgentChangeApplyResult(tuple(changed))


def agent_result_from_claude_payload(payload: dict[str, object]) -> AgentResultPacket:
    """Decode the model's inner JSON result from one successful Claude Code envelope."""
    if not isinstance(payload, dict) or payload.get("is_error") is not False:
        raise AgentChangeError("AGENT_RESULT_ENVELOPE_INVALID")
    raw = payload.get("result")
    if not isinstance(raw, str) or not raw.strip():
        raise AgentChangeError("AGENT_RESULT_MISSING")
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AgentChangeError("AGENT_RESULT_JSON_INVALID") from exc
    if not isinstance(decoded, dict):
        raise AgentChangeError("AGENT_RESULT_SCHEMA_INVALID")
    try:
        changes_raw = decoded.get("changes", [])
        if not isinstance(changes_raw, list):
            raise ValueError("changes are invalid")
        changes = tuple(AgentFileChange(**item) for item in changes_raw)
        evidence_raw = decoded.get("evidence_refs", [])
        if not isinstance(evidence_raw, list):
            raise ValueError("evidence refs are invalid")
        return AgentResultPacket(
            task_id=decoded["task_id"], provider_id=decoded["provider_id"],
            model_id=decoded["model_id"], status=decoded["status"],
            base_head=decoded["base_head"], changes=changes,
            evidence_refs=tuple(evidence_raw),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AgentChangeError("AGENT_RESULT_SCHEMA_INVALID") from exc


def _packet_from_mapping(decoded: dict[str, object]) -> AgentResultPacket:
    try:
        changes_raw = decoded.get("changes", [])
        if not isinstance(changes_raw, list):
            raise ValueError("changes are invalid")
        evidence_raw = decoded.get("evidence_refs", [])
        if not isinstance(evidence_raw, list):
            raise ValueError("evidence refs are invalid")
        return AgentResultPacket(
            task_id=decoded["task_id"], provider_id=decoded["provider_id"],
            model_id=decoded["model_id"], status=decoded["status"],
            base_head=decoded["base_head"],
            changes=tuple(AgentFileChange(**item) for item in changes_raw),
            evidence_refs=tuple(evidence_raw),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AgentChangeError("AGENT_RESULT_INVALID") from exc


class AgentResultFileReader:
    def __init__(self, *, filesystem: NativeFileSystem) -> None:
        if not isinstance(filesystem, NativeFileSystem):
            raise ValueError("filesystem must be NativeFileSystem")
        self._filesystem = filesystem

    def read(self, relative_path: str, *, expected_task_id: str,
             expected_provider_id: str, expected_model_id: str) -> AgentResultPacket:
        try:
            raw = self._filesystem.read_text(relative_path).content
            decoded = json.loads(raw)
        except (NativeExecutionError, json.JSONDecodeError) as exc:
            raise AgentChangeError("AGENT_RESULT_FILE_INVALID") from exc
        if not isinstance(decoded, dict):
            raise AgentChangeError("AGENT_RESULT_FILE_INVALID")
        packet = _packet_from_mapping(decoded)
        if packet.task_id != expected_task_id:
            raise AgentChangeError("TASK_MISMATCH")
        if packet.provider_id != expected_provider_id:
            raise AgentChangeError("PROVIDER_MISMATCH")
        if packet.model_id != expected_model_id:
            raise AgentChangeError("MODEL_MISMATCH")
        return packet


def build_human_bridge_prompt(task_ref: str, result_ref: str) -> str:
    task = _text(task_ref, "task_ref", max_length=512)
    result = _text(result_ref, "result_ref", max_length=512)
    return (f"Read {task}. Do only that authorized lane; write the required JSON result "
            f"to {result}. Do not return the result to the human or edit coordination files.")


class AgentProposalDecoder:
    """Validate one successful harness result into a provider-neutral proposal packet."""

    def decode(
        self,
        result,
        *,
        expected_task_id: str | None = None,
        expected_provider_id: str | None = None,
        expected_model_id: str | None = None,
    ) -> AgentResultPacket:
        status = getattr(result, "status", None)
        if getattr(status, "value", status) != "SUCCESS":
            raise AgentChangeError("AGENT_EXECUTION_NOT_SUCCESSFUL")
        payload = getattr(result, "payload", None)
        if not isinstance(payload, dict):
            raise AgentChangeError("AGENT_RESULT_INVALID")
        decoded = payload.get("structured_output")
        if decoded is None:
            raw = payload.get("result")
            if not isinstance(raw, str):
                raise AgentChangeError("AGENT_RESULT_INVALID")
            try:
                decoded = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise AgentChangeError("AGENT_RESULT_INVALID") from exc
        if not isinstance(decoded, dict):
            raise AgentChangeError("AGENT_RESULT_INVALID")
        try:
            changes_raw = decoded.get("changes", [])
            if not isinstance(changes_raw, list):
                raise ValueError("changes are invalid")
            packet = AgentResultPacket(
                task_id=decoded["task_id"],
                provider_id=decoded["provider_id"],
                model_id=decoded["model_id"],
                status=decoded["status"],
                base_head=decoded["base_head"],
                changes=tuple(AgentFileChange(**item) for item in changes_raw),
                evidence_refs=tuple(decoded.get("evidence_refs", [])),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise AgentChangeError("AGENT_RESULT_INVALID") from exc
        if expected_task_id is not None and packet.task_id != expected_task_id:
            raise AgentChangeError("TASK_MISMATCH")
        if expected_provider_id is not None and packet.provider_id != expected_provider_id:
            raise AgentChangeError("PROVIDER_MISMATCH")
        if expected_model_id is not None and packet.model_id != expected_model_id:
            raise AgentChangeError("MODEL_MISMATCH")
        return packet


@dataclass(frozen=True, slots=True)
class AgentRepairRequest:
    task_id: str
    provider_id: str
    model_id: str
    base_head: str
    source_result_ref: str
    result_destination_ref: str
    review_findings: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_id", _text(self.task_id, "task_id", max_length=128))
        object.__setattr__(self, "provider_id", _text(self.provider_id, "provider_id", max_length=128))
        object.__setattr__(self, "model_id", _text(self.model_id, "model_id", max_length=128))
        if not re.fullmatch(r"[0-9a-fA-F]{7,64}", self.base_head):
            raise ValueError("base_head is invalid")
        object.__setattr__(self, "base_head", self.base_head.casefold())
        object.__setattr__(self, "source_result_ref", _text(self.source_result_ref, "source_result_ref", max_length=512))
        object.__setattr__(self, "result_destination_ref", _text(self.result_destination_ref, "result_destination_ref", max_length=512))
        findings = tuple(_text(item, "review_finding", max_length=1024) for item in self.review_findings)
        if not findings:
            raise ValueError("review_findings must not be empty")
        object.__setattr__(self, "review_findings", findings)


def build_repair_task_markdown(request: AgentRepairRequest) -> str:
    if not isinstance(request, AgentRepairRequest):
        raise ValueError("request must be AgentRepairRequest")
    findings = "\n".join(f"- {item}" for item in request.review_findings)
    return (
        f"# Repair task {request.task_id}\n\n"
        f"Provider/model: `{request.provider_id}` / `{request.model_id}`\n"
        f"Base HEAD: `{request.base_head}`\n"
        f"Read prior result: `{request.source_result_ref}`\n"
        f"Write replacement result: `{request.result_destination_ref}`\n\n"
        "## Review findings\n"
        f"{findings}\n\n"
        "Do not broaden scope, change coordination files, merge, publish, or retry outside this repair task.\n"
    )
