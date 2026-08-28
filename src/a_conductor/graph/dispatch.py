"""GE-7 / AHA-4 durable graph-dispatch adapter.

This module is a thin orchestration layer over existing durable job control.
It owns no scheduler, lifecycle, store, retry loop, process runner, or
execution-dedup implementation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol

from ..domain import TaskState
from ..job_execution import (
    JobExecutionCoordinatorError,
    JobExecutionOutcome,
)
from ..job_state import JobRuntimeState, JobStateError
from ..job_store import JobEvent, JobStoreError
from .scheduler import SelectedAssignment


def _text(value: str, field: str, *, max_length: int) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or "\x00" in value
        or "\r" in value
        or "\n" in value
        or len(value) > max_length
    ):
        raise ValueError(f"{field} is invalid")
    return value.strip()

class GraphDispatchError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = _text(code, "code", max_length=128)
        super().__init__(self.code)


class GraphDispatchMode(str, Enum):
    INTERACTIVE_PULL = "INTERACTIVE_PULL"
    PROGRAMMATIC_PUSH = "PROGRAMMATIC_PUSH"

class WorkerDispatchModeResolver(Protocol):
    def resolve(self, worker_id: str) -> GraphDispatchMode | None: ...


class StaticWorkerDispatchModeResolver:
    def __init__(self, modes: Mapping[str, GraphDispatchMode]) -> None:
        if not isinstance(modes, Mapping):
            raise ValueError("modes must be a mapping")
        copied: dict[str, GraphDispatchMode] = {}
        for worker_id, mode in modes.items():
            worker_id = _text(worker_id, "worker_id", max_length=128)
            if not isinstance(mode, GraphDispatchMode):
                raise ValueError("dispatch mode must be GraphDispatchMode")
            copied[worker_id] = mode
        self._modes = copied

    def resolve(self, worker_id: str) -> GraphDispatchMode | None:
        worker_id = _text(worker_id, "worker_id", max_length=128)
        return self._modes.get(worker_id)

@dataclass(frozen=True, slots=True)
class GraphDispatchKey:
    graph_id: str
    graph_run_id: str
    node_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "graph_id", _text(self.graph_id, "graph_id", max_length=256))
        object.__setattr__(
            self, "graph_run_id", _text(self.graph_run_id, "graph_run_id", max_length=256)
        )
        object.__setattr__(self, "node_id", _text(self.node_id, "node_id", max_length=256))

    @property
    def job_id(self) -> str:
        payload = json.dumps(
            {"graph_id": self.graph_id, "graph_run_id": self.graph_run_id, "node_id": self.node_id},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return f"graph-dispatch-{hashlib.sha256(payload).hexdigest()}"


@dataclass(frozen=True, slots=True)
class GraphDispatchRequest:
    key: GraphDispatchKey
    assignment: SelectedAssignment
    project_id: str
    work_order_ref: str
    operation_ref: str
    dispatch_mode: GraphDispatchMode
    max_attempts: int = 3
    def __post_init__(self) -> None:
        if not isinstance(self.key, GraphDispatchKey):
            raise ValueError("key must be a GraphDispatchKey")
        if not isinstance(self.assignment, SelectedAssignment):
            raise ValueError("assignment must be a SelectedAssignment")
        if self.assignment.node_id != self.key.node_id:
            raise ValueError("assignment node must match dispatch key")
        object.__setattr__(self, "project_id", _text(self.project_id, "project_id", max_length=128))
        object.__setattr__(
            self, "work_order_ref", _text(self.work_order_ref, "work_order_ref", max_length=512)
        )
        object.__setattr__(
            self, "operation_ref", _text(self.operation_ref, "operation_ref", max_length=128)
        )
        if not isinstance(self.dispatch_mode, GraphDispatchMode):
            raise ValueError("dispatch_mode must be GraphDispatchMode")
        if (
            not isinstance(self.max_attempts, int)
            or isinstance(self.max_attempts, bool)
            or self.max_attempts < 1
        ):
            raise ValueError("max_attempts must be >= 1")


@dataclass(frozen=True, slots=True)
class DispatchGateDecision:
    allowed: bool
    reason_code: str
    evidence_ref: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.allowed, bool):
            raise ValueError("allowed must be bool")
        object.__setattr__(self, "reason_code", _text(self.reason_code, "reason_code", max_length=128))
        if self.evidence_ref is not None:
            object.__setattr__(
                self, "evidence_ref", _text(self.evidence_ref, "evidence_ref", max_length=512)
            )

    @classmethod
    def allow(
        cls, *, evidence_ref: str | None = None
    ) -> "DispatchGateDecision":
        return cls(True, "ALLOW", evidence_ref)
    @classmethod
    def deny(
        cls, reason_code: str, *, evidence_ref: str | None = None
    ) -> "DispatchGateDecision":
        return cls(False, reason_code, evidence_ref)


class GraphDispatchAction(str, Enum):
    EXECUTED = "EXECUTED"
    OFFERED = "OFFERED"
    BLOCKED = "BLOCKED"
    EXISTING = "EXISTING"
    RECONCILE = "RECONCILE"


@dataclass(frozen=True, slots=True)
class GraphDispatchResult:
    action: GraphDispatchAction
    job: JobRuntimeState
    reason_code: str
    execution: JobExecutionOutcome | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.action, GraphDispatchAction):
            raise ValueError("action must be GraphDispatchAction")
        if not isinstance(self.job, JobRuntimeState):
            raise ValueError("job must be JobRuntimeState")
        _text(self.reason_code, "reason_code", max_length=128)
        if self.execution is not None and not isinstance(
            self.execution, JobExecutionOutcome
        ):
            raise ValueError("execution must be JobExecutionOutcome or None")


class DurableGraphDispatchPort(Protocol):
    def create_job(
        self, *, job_id: str, work_order_ref: str, project_id: str, max_attempts: int = 3
    ) -> JobRuntimeState: ...

    def get_job(self, job_id: str) -> JobRuntimeState: ...

    def list_events(self, job_id: str) -> tuple[JobEvent, ...]: ...

    def checkpoint(
        self,
        job_id: str,
        *,
        expected_version: int,
        checkpoint_ref: str,
        evidence_ref: str | None = None,
    ) -> JobRuntimeState: ...

    def mark_ready(self, job_id: str, *, expected_version: int) -> JobRuntimeState: ...

    def claim(
        self, job_id: str, *, expected_version: int, worker_id: str
    ) -> JobRuntimeState: ...

    def block(
        self,
        job_id: str,
        *,
        expected_version: int,
        worker_id: str,
        evidence_ref: str | None = None,
    ) -> JobRuntimeState: ...

    def gate(
        self,
        job_id: str,
        *,
        expected_version: int,
        worker_id: str,
        evidence_ref: str | None = None,
    ) -> JobRuntimeState: ...

    def execute_operation(
        self,
        job_id: str,
        *,
        expected_version: int,
        worker_id: str,
        operation_ref: str,
    ) -> JobExecutionOutcome: ...


_EXISTING_STATES = frozenset(
    {TaskState.VERIFYING, TaskState.REVIEW_PENDING, TaskState.COMPLETE, TaskState.FAILED, TaskState.CANCELLED}
)
_RECONCILE_STATES = frozenset(
    {TaskState.EXECUTING, TaskState.RECOVERY_NEEDED, TaskState.CHANGES_REQUIRED, TaskState.REPAIRING, TaskState.PLANNING}
)
_DISPATCH_META_PREFIX = "graph-dispatch-meta:"


def _dispatch_metadata_ref(request: GraphDispatchRequest) -> str:
    payload = {
        "graph_id": request.key.graph_id,
        "graph_run_id": request.key.graph_run_id,
        "node_id": request.key.node_id,
        "project_id": request.project_id,
        "work_order_ref": request.work_order_ref,
        "operation_ref": request.operation_ref,
        "dispatch_mode": request.dispatch_mode.value,
        "max_attempts": request.max_attempts,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return f"{_DISPATCH_META_PREFIX}{hashlib.sha256(encoded).hexdigest()}"


class GraphDispatchCoordinator:
    def __init__(
        self,
        *,
        service: DurableGraphDispatchPort,
        mode_resolver: WorkerDispatchModeResolver,
    ) -> None:
        if not callable(getattr(mode_resolver, "resolve", None)):
            raise ValueError("mode_resolver must provide resolve")
        self._service = service
        self._mode_resolver = mode_resolver
    def _load_or_create(self, request: GraphDispatchRequest) -> JobRuntimeState:
        job_id = request.key.job_id
        try:
            job = self._service.get_job(job_id)
        except JobStoreError as exc:
            if exc.code != "JOB_NOT_FOUND":
                raise
            try:
                job = self._service.create_job(
                    job_id=job_id,
                    work_order_ref=request.work_order_ref,
                    project_id=request.project_id,
                    max_attempts=request.max_attempts,
                )
            except JobStoreError as create_exc:
                if create_exc.code != "JOB_ALREADY_EXISTS":
                    raise
                job = self._service.get_job(job_id)
        if (
            job.work_order_ref != request.work_order_ref
            or job.project_id != request.project_id
            or job.max_attempts != request.max_attempts
        ):
            raise GraphDispatchError("DISPATCH_JOB_IDENTITY_MISMATCH")
        return self._ensure_metadata(request, job)

    def _ensure_metadata(
        self, request: GraphDispatchRequest, job: JobRuntimeState
    ) -> JobRuntimeState:
        expected_ref = _dispatch_metadata_ref(request)
        metadata_refs = tuple(
            event.checkpoint_ref
            for event in self._service.list_events(job.job_id)
            if event.checkpoint_ref is not None
            and event.checkpoint_ref.startswith(_DISPATCH_META_PREFIX)
        )
        if metadata_refs:
            if len(metadata_refs) != 1:
                raise GraphDispatchError("DISPATCH_METADATA_AMBIGUOUS")
            if metadata_refs[0] != expected_ref:
                raise GraphDispatchError("DISPATCH_JOB_IDENTITY_MISMATCH")
            return self._service.get_job(job.job_id)
        if job.state is not TaskState.NEW:
            raise GraphDispatchError("DISPATCH_METADATA_MISSING")
        return self._service.checkpoint(
            job.job_id,
            expected_version=job.version,
            checkpoint_ref=expected_ref,
        )

    def _reconcile(self, request: GraphDispatchRequest, reason_code: str) -> GraphDispatchResult:
        latest = self._service.get_job(request.key.job_id)
        return GraphDispatchResult(
            GraphDispatchAction.RECONCILE,
            latest,
            reason_code,
        )

    @staticmethod
    def _assert_worker(job: JobRuntimeState, worker_id: str) -> None:
        if job.worker_id is not None and job.worker_id != worker_id:
            raise GraphDispatchError("WORKER_CLAIM_CONFLICT")

    def dispatch(
        self,
        request: GraphDispatchRequest,
        *,
        gate: DispatchGateDecision,
    ) -> GraphDispatchResult:
        if not isinstance(request, GraphDispatchRequest):
            raise ValueError("request must be GraphDispatchRequest")
        if not isinstance(gate, DispatchGateDecision):
            raise ValueError("gate must be DispatchGateDecision")
        worker_id = request.assignment.worker_id
        resolved_mode = self._mode_resolver.resolve(worker_id)
        if resolved_mode is None:
            raise GraphDispatchError("DISPATCH_MODE_UNKNOWN")
        if not isinstance(resolved_mode, GraphDispatchMode):
            raise GraphDispatchError("DISPATCH_MODE_INVALID")
        if request.dispatch_mode is not resolved_mode:
            raise GraphDispatchError("DISPATCH_MODE_MISMATCH")
        try:
            job = self._load_or_create(request)

            if job.state in _EXISTING_STATES:
                return GraphDispatchResult(
                    GraphDispatchAction.EXISTING,
                    job,
                    f"JOB_ALREADY_{job.state.value}",
                )
            if job.state in _RECONCILE_STATES:
                return GraphDispatchResult(
                    GraphDispatchAction.RECONCILE,
                    job,
                    f"JOB_STATE_{job.state.value}",
                )

            if job.state is TaskState.BLOCKED:
                if not gate.allowed:
                    return GraphDispatchResult(
                        GraphDispatchAction.BLOCKED, job, gate.reason_code
                    )
                job = self._service.mark_ready(
                    job.job_id, expected_version=job.version
                )
            elif job.state is TaskState.NEW:
                job = self._service.mark_ready(
                    job.job_id, expected_version=job.version
                )

            if job.state is TaskState.READY:
                job = self._service.claim(
                    job.job_id,
                    expected_version=job.version,
                    worker_id=worker_id,
                )

            self._assert_worker(job, worker_id)
            if job.state not in {TaskState.CLAIMED, TaskState.GATING}:
                return GraphDispatchResult(
                    GraphDispatchAction.RECONCILE,
                    job,
                    f"JOB_STATE_{job.state.value}",
                )

            if not gate.allowed:
                blocked = self._service.block(
                    job.job_id,
                    expected_version=job.version,
                    worker_id=worker_id,
                    evidence_ref=gate.evidence_ref,
                )
                return GraphDispatchResult(
                    GraphDispatchAction.BLOCKED,
                    blocked,
                    gate.reason_code,
                )
            if request.dispatch_mode is GraphDispatchMode.INTERACTIVE_PULL:
                return GraphDispatchResult(
                    GraphDispatchAction.OFFERED,
                    job,
                    "INTERACTIVE_PULL_OFFERED",
                )

            if job.state is TaskState.CLAIMED:
                job = self._service.gate(
                    job.job_id,
                    expected_version=job.version,
                    worker_id=worker_id,
                    evidence_ref=gate.evidence_ref,
                )

            outcome = self._service.execute_operation(
                job.job_id,
                expected_version=job.version,
                worker_id=worker_id,
                operation_ref=request.operation_ref,
            )
            if outcome.success:
                return GraphDispatchResult(
                    GraphDispatchAction.EXECUTED,
                    outcome.job,
                    "EXECUTION_REACHED_VERIFYING",
                    execution=outcome,
                )
            return GraphDispatchResult(
                GraphDispatchAction.RECONCILE,
                outcome.job,
                outcome.error_code or "EXECUTION_RECONCILE_REQUIRED",
                execution=outcome,
            )
        except JobStoreError as exc:
            if exc.code == "JOB_VERSION_CONFLICT":
                return self._reconcile(request, exc.code)
            raise
        except JobExecutionCoordinatorError as exc:
            if exc.recovery_required:
                return self._reconcile(request, exc.code)
            raise
        except JobStateError as exc:
            return self._reconcile(request, exc.code)