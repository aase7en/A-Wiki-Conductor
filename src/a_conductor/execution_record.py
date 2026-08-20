"""Pure durable execution record model for transport-independent supervision.

This module contains no persistence, process, network, retry, reconnect, Git,
worker lifecycle, or backend integration. Transport health and execution
process/result state are intentionally independent dimensions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MAX_SUMMARY_CHARS = 256
_MAX_TEXT_CHARS = 1024


class TransportState(str, Enum):
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    LOST = "LOST"
    UNAVAILABLE = "UNAVAILABLE"


class ExecutionProcessState(str, Enum):
    QUEUED = "QUEUED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    PROCESS_STILL_RUNNING = "PROCESS_STILL_RUNNING"
    PROCESS_EXITED_UNKNOWN_RESULT = "PROCESS_EXITED_UNKNOWN_RESULT"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    VERIFICATION_REQUIRED = "VERIFICATION_REQUIRED"


def _require_text(value: str, field_name: str, *, max_chars: int = _MAX_TEXT_CHARS) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if "\x00" in value or "\r" in value or "\n" in value:
        raise ValueError(f"{field_name} must be a single-line text value")
    if len(value) > max_chars:
        raise ValueError(f"{field_name} exceeds maximum length")
    return value


def _require_optional_text(
    value: str | None,
    field_name: str,
    *,
    max_chars: int = _MAX_TEXT_CHARS,
) -> str | None:
    if value is None:
        return None
    return _require_text(value, field_name, max_chars=max_chars)


def _require_positive_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{field_name} must be >= 1")
    return value


def _require_optional_pid(value: int | None) -> int | None:
    if value is None:
        return None
    return _require_positive_int(value, "pid")


def _require_optional_exit_code(value: int | None) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("exit_code must be an integer")
    return value


@dataclass(frozen=True, slots=True)
class DurableExecutionRecord:
    execution_id: str
    job_id: str
    work_order_ref: str
    project_id: str
    worker_id: str
    backend_id: str
    agent_ref: str | None
    repo_root: str
    branch: str
    head_before: str
    operation_ref: str
    command_fingerprint: str
    command_summary: str
    runtime_profile_ref: str | None
    run_dir_ref: str | None
    stdout_ref: str | None
    stderr_ref: str | None
    result_ref: str | None
    report_ref: str | None
    transport_state: TransportState
    execution_state: ExecutionProcessState
    pid: int | None = None
    exit_code: int | None = None
    started_at: str | None = None
    finished_at: str | None = None
    version: int = 1

    def __post_init__(self) -> None:
        _require_text(self.execution_id, "execution_id")
        _require_text(self.job_id, "job_id")
        _require_text(self.work_order_ref, "work_order_ref")
        _require_text(self.project_id, "project_id")
        _require_text(self.worker_id, "worker_id")
        _require_text(self.backend_id, "backend_id")
        _require_optional_text(self.agent_ref, "agent_ref")
        _require_text(self.repo_root, "repo_root")
        _require_text(self.branch, "branch")
        _require_text(self.head_before, "head_before")
        _require_text(self.operation_ref, "operation_ref")
        if not isinstance(self.command_fingerprint, str) or not _SHA256_RE.fullmatch(
            self.command_fingerprint
        ):
            raise ValueError("command_fingerprint must be lowercase SHA-256 hex")
        _require_text(
            self.command_summary,
            "command_summary",
            max_chars=_MAX_SUMMARY_CHARS,
        )
        _require_optional_text(self.runtime_profile_ref, "runtime_profile_ref")
        _require_optional_text(self.run_dir_ref, "run_dir_ref")
        _require_optional_text(self.stdout_ref, "stdout_ref")
        _require_optional_text(self.stderr_ref, "stderr_ref")
        _require_optional_text(self.result_ref, "result_ref")
        _require_optional_text(self.report_ref, "report_ref")
        if not isinstance(self.transport_state, TransportState):
            raise ValueError("transport_state must be a TransportState")
        if not isinstance(self.execution_state, ExecutionProcessState):
            raise ValueError("execution_state must be an ExecutionProcessState")
        _require_optional_pid(self.pid)
        _require_optional_exit_code(self.exit_code)
        _require_optional_text(self.started_at, "started_at")
        _require_optional_text(self.finished_at, "finished_at")
        _require_positive_int(self.version, "version")


def new_execution_record(
    *,
    execution_id: str,
    job_id: str,
    work_order_ref: str,
    project_id: str,
    worker_id: str,
    backend_id: str,
    agent_ref: str | None,
    repo_root: str,
    branch: str,
    head_before: str,
    operation_ref: str,
    command_fingerprint: str,
    command_summary: str,
    runtime_profile_ref: str | None,
    run_dir_ref: str | None,
    stdout_ref: str | None,
    stderr_ref: str | None,
    result_ref: str | None,
    report_ref: str | None,
    transport_state: TransportState,
    execution_state: ExecutionProcessState = ExecutionProcessState.QUEUED,
    pid: int | None = None,
    exit_code: int | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> DurableExecutionRecord:
    return DurableExecutionRecord(
        execution_id=execution_id,
        job_id=job_id,
        work_order_ref=work_order_ref,
        project_id=project_id,
        worker_id=worker_id,
        backend_id=backend_id,
        agent_ref=agent_ref,
        repo_root=repo_root,
        branch=branch,
        head_before=head_before,
        operation_ref=operation_ref,
        command_fingerprint=command_fingerprint,
        command_summary=command_summary,
        runtime_profile_ref=runtime_profile_ref,
        run_dir_ref=run_dir_ref,
        stdout_ref=stdout_ref,
        stderr_ref=stderr_ref,
        result_ref=result_ref,
        report_ref=report_ref,
        transport_state=transport_state,
        execution_state=execution_state,
        pid=pid,
        exit_code=exit_code,
        started_at=started_at,
        finished_at=finished_at,
        version=1,
    )
