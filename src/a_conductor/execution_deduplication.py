"""Canonical execution fingerprints and duplicate-execution decisions.

This module is a pure decision layer over durable execution metadata. It does
not launch, retry, route, mutate Git, or persist raw target argv.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol, Sequence

from .execution_record import DurableExecutionRecord, ExecutionProcessState


_MAX_TEXT = 1024


class DuplicateExecutionDecision(str, Enum):
    SAFE_TO_LAUNCH = "SAFE_TO_LAUNCH"
    ATTACH_RUNNING = "ATTACH_RUNNING"
    REUSE_COMPLETED = "REUSE_COMPLETED"
    BLOCKED_UNKNOWN = "BLOCKED_UNKNOWN"


def _text(value: str, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or "\x00" in value
        or "\r" in value
        or "\n" in value
        or len(value) > _MAX_TEXT
    ):
        raise ValueError(f"{field_name} is invalid")
    return value.strip()


def _optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _text(value, field_name)


def _normalize_repo_root(value: str) -> str:
    raw = _text(value, "repo_root")
    try:
        path = Path(raw).expanduser().resolve(strict=False)
    except OSError as exc:
        raise ValueError("repo_root is invalid") from exc
    if not path.is_absolute():
        raise ValueError("repo_root must be absolute")
    return str(path).replace("\\", "/").casefold()


def _normalize_argv(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError("target_argv must be a sequence")
    argv = tuple(values)
    if not argv:
        raise ValueError("target_argv must not be empty")
    normalized: list[str] = []
    for index, value in enumerate(argv):
        if (
            not isinstance(value, str)
            or not value
            or "\x00" in value
            or "\r" in value
            or "\n" in value
            or len(value) > _MAX_TEXT
        ):
            raise ValueError(f"target_argv[{index}] is invalid")
        normalized.append(value)
    return tuple(normalized)


@dataclass(frozen=True, slots=True)
class ExecutionFingerprintSpec:
    project_id: str
    job_id: str
    work_order_ref: str
    backend_id: str
    repo_root: str
    branch: str
    head_before: str
    operation_ref: str
    runtime_profile_ref: str | None
    target_argv: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _text(self.project_id, "project_id"))
        object.__setattr__(self, "job_id", _text(self.job_id, "job_id"))
        object.__setattr__(self, "work_order_ref", _text(self.work_order_ref, "work_order_ref"))
        object.__setattr__(self, "backend_id", _text(self.backend_id, "backend_id"))
        object.__setattr__(self, "repo_root", _normalize_repo_root(self.repo_root))
        object.__setattr__(self, "branch", _text(self.branch, "branch"))
        object.__setattr__(self, "head_before", _text(self.head_before, "head_before"))
        object.__setattr__(self, "operation_ref", _text(self.operation_ref, "operation_ref"))
        object.__setattr__(
            self,
            "runtime_profile_ref",
            _optional_text(self.runtime_profile_ref, "runtime_profile_ref"),
        )
        object.__setattr__(self, "target_argv", _normalize_argv(self.target_argv))


def compute_execution_fingerprint(spec: ExecutionFingerprintSpec) -> str:
    if not isinstance(spec, ExecutionFingerprintSpec):
        raise ValueError("spec must be an ExecutionFingerprintSpec")
    payload = {
        "backend_id": spec.backend_id,
        "branch": spec.branch,
        "head_before": spec.head_before,
        "job_id": spec.job_id,
        "operation_ref": spec.operation_ref,
        "project_id": spec.project_id,
        "repo_root": spec.repo_root,
        "runtime_profile_ref": spec.runtime_profile_ref,
        "target_argv": list(spec.target_argv),
        "work_order_ref": spec.work_order_ref,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class DuplicateExecutionAssessment:
    decision: DuplicateExecutionDecision
    fingerprint: str
    record: DurableExecutionRecord | None
    reason_code: str
    retry_authorized: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.decision, DuplicateExecutionDecision):
            raise ValueError("decision must be a DuplicateExecutionDecision")
        if (
            not isinstance(self.fingerprint, str)
            or len(self.fingerprint) != 64
            or any(ch not in "0123456789abcdef" for ch in self.fingerprint)
        ):
            raise ValueError("fingerprint must be lowercase SHA-256 hex")
        if self.record is not None and not isinstance(self.record, DurableExecutionRecord):
            raise ValueError("record must be a DurableExecutionRecord or None")
        _text(self.reason_code, "reason_code")
        if not isinstance(self.retry_authorized, bool):
            raise ValueError("retry_authorized must be a bool")


class ExecutionFingerprintStore(Protocol):
    def find_by_fingerprint(self, fingerprint: str) -> tuple[DurableExecutionRecord, ...]: ...


_LIVE_STATES = frozenset(
    {
        ExecutionProcessState.QUEUED,
        ExecutionProcessState.STARTING,
        ExecutionProcessState.RUNNING,
        ExecutionProcessState.PROCESS_STILL_RUNNING,
    }
)
_COMPLETED_EVIDENCE_STATES = frozenset(
    {
        ExecutionProcessState.VERIFICATION_REQUIRED,
        ExecutionProcessState.SUCCEEDED,
        ExecutionProcessState.FAILED,
    }
)


def _identity_matches(record: DurableExecutionRecord, spec: ExecutionFingerprintSpec) -> bool:
    return (
        record.project_id == spec.project_id
        and record.job_id == spec.job_id
        and record.work_order_ref == spec.work_order_ref
        and record.backend_id == spec.backend_id
        and _normalize_repo_root(record.repo_root) == spec.repo_root
        and record.branch == spec.branch
        and record.head_before == spec.head_before
        and record.operation_ref == spec.operation_ref
        and record.runtime_profile_ref == spec.runtime_profile_ref
    )


class DuplicateExecutionGuard:
    def __init__(self, *, store: ExecutionFingerprintStore) -> None:
        self._store = store

    def assess(self, spec: ExecutionFingerprintSpec) -> DuplicateExecutionAssessment:
        if not isinstance(spec, ExecutionFingerprintSpec):
            raise ValueError("spec must be an ExecutionFingerprintSpec")
        fingerprint = compute_execution_fingerprint(spec)
        matches = self._store.find_by_fingerprint(fingerprint)
        if not matches:
            return DuplicateExecutionAssessment(
                decision=DuplicateExecutionDecision.SAFE_TO_LAUNCH,
                fingerprint=fingerprint,
                record=None,
                reason_code="NO_EQUIVALENT_EXECUTION",
                retry_authorized=False,
            )

        record = matches[0]
        if record.command_fingerprint != fingerprint or not _identity_matches(record, spec):
            return DuplicateExecutionAssessment(
                decision=DuplicateExecutionDecision.BLOCKED_UNKNOWN,
                fingerprint=fingerprint,
                record=record,
                reason_code="DUPLICATE_IDENTITY_MISMATCH",
                retry_authorized=False,
            )
        if record.execution_state in _LIVE_STATES:
            return DuplicateExecutionAssessment(
                decision=DuplicateExecutionDecision.ATTACH_RUNNING,
                fingerprint=fingerprint,
                record=record,
                reason_code="EQUIVALENT_EXECUTION_ACTIVE",
                retry_authorized=False,
            )
        if record.execution_state in _COMPLETED_EVIDENCE_STATES:
            return DuplicateExecutionAssessment(
                decision=DuplicateExecutionDecision.REUSE_COMPLETED,
                fingerprint=fingerprint,
                record=record,
                reason_code="EQUIVALENT_EXECUTION_COMPLETED",
                retry_authorized=False,
            )
        return DuplicateExecutionAssessment(
            decision=DuplicateExecutionDecision.BLOCKED_UNKNOWN,
            fingerprint=fingerprint,
            record=record,
            reason_code="EQUIVALENT_EXECUTION_UNSAFE_STATE",
            retry_authorized=False,
        )
