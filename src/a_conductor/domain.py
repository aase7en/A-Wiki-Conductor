"""Provider-neutral core domain types for A-Conductor.

This module intentionally contains no process, network, persistence, provider,
or runtime-engine integration. It models the stable language defined by
``docs/contracts/core-domain.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TaskState(str, Enum):
    NEW = "NEW"
    PLANNING = "PLANNING"
    READY = "READY"
    CLAIMED = "CLAIMED"
    GATING = "GATING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    REPAIRING = "REPAIRING"
    REVIEW_PENDING = "REVIEW_PENDING"
    CHANGES_REQUIRED = "CHANGES_REQUIRED"
    BLOCKED = "BLOCKED"
    RECOVERY_NEEDED = "RECOVERY_NEEDED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RecoveryClassification(str, Enum):
    NO_MUTATION = "NO_MUTATION"
    PARTIAL_MUTATION = "PARTIAL_MUTATION"
    MUTATION_COMPLETE_UNVERIFIED = "MUTATION_COMPLETE_UNVERIFIED"
    COMPLETE_VERIFIED = "COMPLETE_VERIFIED"
    UNEXPECTED_DRIFT = "UNEXPECTED_DRIFT"
    UNKNOWN = "UNKNOWN"


class ReviewOutcome(str, Enum):
    PASS = "PASS"
    CHANGES_REQUIRED = "CHANGES_REQUIRED"
    BLOCKED = "BLOCKED"
    ESCALATE = "ESCALATE"


class RiskClass(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"


class WorkerState(str, Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    READY = "READY"
    BUSY = "BUSY"
    STOPPING = "STOPPING"
    ERROR = "ERROR"


class HealthState(str, Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    READY = "READY"
    BUSY = "BUSY"
    STOPPING = "STOPPING"
    ERROR = "ERROR"
    PORT_IN_USE = "PORT_IN_USE"
    TUNNEL_COLLISION = "TUNNEL_COLLISION"
    PID_MISMATCH = "PID_MISMATCH"
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    PROJECT_IDENTITY_FAILED = "PROJECT_IDENTITY_FAILED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


def _require_optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_text(value, field_name)


@dataclass(frozen=True, slots=True)
class Capability:
    name: str
    version: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.name, "name")
        _require_optional_text(self.version, "version")


@dataclass(frozen=True, slots=True)
class Project:
    project_id: str
    display_name: str
    root_path: str

    def __post_init__(self) -> None:
        _require_text(self.project_id, "project_id")
        _require_text(self.display_name, "display_name")
        _require_text(self.root_path, "root_path")


@dataclass(frozen=True, slots=True)
class Runtime:
    runtime_id: str
    runtime_type: str
    capabilities: tuple[Capability, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.runtime_id, "runtime_id")
        _require_text(self.runtime_type, "runtime_type")
        object.__setattr__(self, "capabilities", tuple(self.capabilities))


@dataclass(frozen=True, slots=True)
class Worker:
    worker_id: str
    display_name: str
    runtime_id: str | None = None
    assignment_id: str | None = None
    state: WorkerState = WorkerState.STOPPED

    def __post_init__(self) -> None:
        _require_text(self.worker_id, "worker_id")
        _require_text(self.display_name, "display_name")
        _require_optional_text(self.runtime_id, "runtime_id")
        _require_optional_text(self.assignment_id, "assignment_id")


@dataclass(frozen=True, slots=True)
class Provider:
    provider_id: str
    provider_type: str
    display_name: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.provider_id, "provider_id")
        _require_text(self.provider_type, "provider_type")
        _require_optional_text(self.display_name, "display_name")


@dataclass(frozen=True, slots=True)
class Agent:
    agent_id: str
    provider_id: str | None
    model_id: str | None
    capabilities: tuple[Capability, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.agent_id, "agent_id")
        _require_optional_text(self.provider_id, "provider_id")
        _require_optional_text(self.model_id, "model_id")
        object.__setattr__(self, "capabilities", tuple(self.capabilities))


@dataclass(frozen=True, slots=True)
class Assignment:
    assignment_id: str
    worker_id: str
    project_id: str
    runtime_id: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.assignment_id, "assignment_id")
        _require_text(self.worker_id, "worker_id")
        _require_text(self.project_id, "project_id")
        _require_optional_text(self.runtime_id, "runtime_id")


@dataclass(frozen=True, slots=True)
class Execution:
    execution_id: str
    task_id: str
    attempt_no: int
    worker_id: str
    runtime_id: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.execution_id, "execution_id")
        _require_text(self.task_id, "task_id")
        _require_text(self.worker_id, "worker_id")
        _require_optional_text(self.runtime_id, "runtime_id")
        if self.attempt_no < 1:
            raise ValueError("attempt_no must be >= 1")


@dataclass(frozen=True, slots=True)
class ExecutionSurfaceTraits:
    supports_long_running: bool = False
    supports_resume: bool = False
    supports_background_execution: bool = False
    supports_repo_tools: bool = False
    requires_human_presence: bool = True
    max_safe_transaction_scope: str | None = None

    def __post_init__(self) -> None:
        _require_optional_text(
            self.max_safe_transaction_scope,
            "max_safe_transaction_scope",
        )


@dataclass(frozen=True, slots=True)
class ReviewResult:
    outcome: ReviewOutcome
    summary: str
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.summary, str):
            raise ValueError("summary must be a string")
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        for index, evidence_ref in enumerate(self.evidence_refs):
            _require_text(evidence_ref, f"evidence_refs[{index}]")
