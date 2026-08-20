"""Pure durable-job state policy for A-Conductor.

This module performs no persistence, filesystem, process, network, worker,
Git, scheduler, or model action. It defines the operational state transition
policy used by the durable job store.
"""

from __future__ import annotations

from dataclasses import dataclass

from .domain import RecoveryClassification, TaskState


class JobStateError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


def _require_positive_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{field_name} must be >= 1")
    return value


def _require_nonnegative_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return value


_TERMINAL_STATES = frozenset(
    {TaskState.COMPLETE, TaskState.FAILED, TaskState.CANCELLED}
)

_ALLOWED_TRANSITIONS: dict[TaskState, frozenset[TaskState]] = {
    TaskState.NEW: frozenset(
        {TaskState.PLANNING, TaskState.READY, TaskState.BLOCKED, TaskState.CANCELLED}
    ),
    TaskState.PLANNING: frozenset(
        {TaskState.READY, TaskState.BLOCKED, TaskState.FAILED, TaskState.CANCELLED}
    ),
    TaskState.READY: frozenset(
        {TaskState.CLAIMED, TaskState.BLOCKED, TaskState.CANCELLED}
    ),
    TaskState.CLAIMED: frozenset(
        {TaskState.GATING, TaskState.READY, TaskState.BLOCKED, TaskState.CANCELLED}
    ),
    TaskState.GATING: frozenset(
        {
            TaskState.EXECUTING,
            TaskState.BLOCKED,
            TaskState.RECOVERY_NEEDED,
            TaskState.FAILED,
            TaskState.CANCELLED,
        }
    ),
    TaskState.EXECUTING: frozenset(
        {
            TaskState.VERIFYING,
            TaskState.RECOVERY_NEEDED,
            TaskState.FAILED,
            TaskState.CANCELLED,
        }
    ),
    TaskState.VERIFYING: frozenset(
        {
            TaskState.REVIEW_PENDING,
            TaskState.CHANGES_REQUIRED,
            TaskState.COMPLETE,
            TaskState.RECOVERY_NEEDED,
            TaskState.FAILED,
        }
    ),
    TaskState.REVIEW_PENDING: frozenset(
        {
            TaskState.COMPLETE,
            TaskState.CHANGES_REQUIRED,
            TaskState.BLOCKED,
            TaskState.FAILED,
        }
    ),
    TaskState.CHANGES_REQUIRED: frozenset(
        {TaskState.REPAIRING, TaskState.CANCELLED}
    ),
    TaskState.REPAIRING: frozenset(
        {
            TaskState.VERIFYING,
            TaskState.RECOVERY_NEEDED,
            TaskState.FAILED,
            TaskState.CANCELLED,
        }
    ),
    TaskState.BLOCKED: frozenset(
        {TaskState.READY, TaskState.FAILED, TaskState.CANCELLED}
    ),
}

_RECOVERY_TARGET: dict[RecoveryClassification, TaskState] = {
    RecoveryClassification.NO_MUTATION: TaskState.READY,
    RecoveryClassification.PARTIAL_MUTATION: TaskState.GATING,
    RecoveryClassification.MUTATION_COMPLETE_UNVERIFIED: TaskState.VERIFYING,
    RecoveryClassification.COMPLETE_VERIFIED: TaskState.REVIEW_PENDING,
    RecoveryClassification.UNEXPECTED_DRIFT: TaskState.BLOCKED,
    RecoveryClassification.UNKNOWN: TaskState.BLOCKED,
}

_RELEASE_CLAIM_STATES = frozenset(
    {
        TaskState.READY,
        TaskState.BLOCKED,
        TaskState.COMPLETE,
        TaskState.FAILED,
        TaskState.CANCELLED,
    }
)


@dataclass(frozen=True, slots=True)
class JobRuntimeState:
    job_id: str
    work_order_ref: str
    project_id: str
    state: TaskState
    worker_id: str | None
    attempt_count: int
    max_attempts: int
    recovery_classification: RecoveryClassification | None
    version: int

    def __post_init__(self) -> None:
        _require_text(self.job_id, "job_id")
        _require_text(self.work_order_ref, "work_order_ref")
        _require_text(self.project_id, "project_id")
        if not isinstance(self.state, TaskState):
            raise ValueError("state must be a TaskState")
        if self.worker_id is not None:
            _require_text(self.worker_id, "worker_id")
        _require_nonnegative_int(self.attempt_count, "attempt_count")
        _require_positive_int(self.max_attempts, "max_attempts")
        if self.attempt_count > self.max_attempts:
            raise ValueError("attempt_count must not exceed max_attempts")
        _require_positive_int(self.version, "version")
        if self.recovery_classification is not None and not isinstance(
            self.recovery_classification, RecoveryClassification
        ):
            raise ValueError("recovery_classification must be a RecoveryClassification")
        if self.state is TaskState.RECOVERY_NEEDED:
            if self.recovery_classification is None:
                raise ValueError("RECOVERY_NEEDED requires recovery_classification")
        elif self.recovery_classification is not None:
            raise ValueError("recovery_classification is valid only for RECOVERY_NEEDED")


@dataclass(frozen=True, slots=True)
class JobTransitionPlan:
    target_state: TaskState
    worker_id: str | None
    attempt_count: int
    recovery_classification: RecoveryClassification | None


def new_job_state(
    *,
    job_id: str,
    work_order_ref: str,
    project_id: str,
    max_attempts: int = 3,
) -> JobRuntimeState:
    return JobRuntimeState(
        job_id=job_id,
        work_order_ref=work_order_ref,
        project_id=project_id,
        state=TaskState.NEW,
        worker_id=None,
        attempt_count=0,
        max_attempts=max_attempts,
        recovery_classification=None,
        version=1,
    )


def plan_job_transition(
    current: JobRuntimeState,
    target_state: TaskState,
    *,
    worker_id: str | None = None,
    recovery_classification: RecoveryClassification | None = None,
) -> JobTransitionPlan:
    if not isinstance(current, JobRuntimeState):
        raise ValueError("current must be a JobRuntimeState")
    if not isinstance(target_state, TaskState):
        raise ValueError("target_state must be a TaskState")
    if worker_id is not None:
        _require_text(worker_id, "worker_id")
    if recovery_classification is not None and not isinstance(
        recovery_classification, RecoveryClassification
    ):
        raise ValueError("recovery_classification must be a RecoveryClassification")

    if current.state in _TERMINAL_STATES:
        raise JobStateError("JOB_TERMINAL")

    next_recovery: RecoveryClassification | None = None
    next_worker = current.worker_id
    next_attempt_count = current.attempt_count

    if current.state is TaskState.RECOVERY_NEEDED:
        assert current.recovery_classification is not None
        expected_target = _RECOVERY_TARGET[current.recovery_classification]
        if target_state is not expected_target:
            raise JobStateError("RECOVERY_TRANSITION_INVALID")
        if worker_id is not None and current.worker_id is not None and worker_id != current.worker_id:
            raise JobStateError("WORKER_CLAIM_CONFLICT")
    else:
        allowed = _ALLOWED_TRANSITIONS.get(current.state, frozenset())
        if target_state not in allowed:
            raise JobStateError("JOB_TRANSITION_INVALID")

        if target_state is TaskState.CLAIMED:
            if worker_id is None:
                raise JobStateError("WORKER_ID_REQUIRED")
            next_worker = worker_id
        elif worker_id is not None:
            if current.worker_id is None or worker_id != current.worker_id:
                raise JobStateError("WORKER_CLAIM_CONFLICT")

        if target_state is TaskState.RECOVERY_NEEDED:
            if recovery_classification is None:
                raise JobStateError("RECOVERY_CLASSIFICATION_REQUIRED")
            next_recovery = recovery_classification
        elif recovery_classification is not None:
            raise JobStateError("RECOVERY_CLASSIFICATION_NOT_ALLOWED")

    if target_state is TaskState.EXECUTING:
        if next_attempt_count >= current.max_attempts:
            raise JobStateError("ATTEMPT_BUDGET_EXHAUSTED")
        next_attempt_count += 1

    if target_state in _RELEASE_CLAIM_STATES:
        next_worker = None

    return JobTransitionPlan(
        target_state=target_state,
        worker_id=next_worker,
        attempt_count=next_attempt_count,
        recovery_classification=next_recovery,
    )
