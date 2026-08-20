from __future__ import annotations

import pytest

from a_conductor.domain import RecoveryClassification, TaskState
from a_conductor.job_state import (
    JobRuntimeState,
    JobStateError,
    JobTransitionPlan,
    new_job_state,
    plan_job_transition,
)


def make_state(
    state: TaskState,
    *,
    worker_id: str | None = None,
    attempt_count: int = 0,
    max_attempts: int = 3,
    recovery: RecoveryClassification | None = None,
    version: int = 1,
) -> JobRuntimeState:
    return JobRuntimeState(
        job_id="job-1",
        work_order_ref="docs/work-orders/WO-1.md",
        project_id="project-1",
        state=state,
        worker_id=worker_id,
        attempt_count=attempt_count,
        max_attempts=max_attempts,
        recovery_classification=recovery,
        version=version,
    )


def test_new_job_state_is_payload_free_and_versioned() -> None:
    job = new_job_state(
        job_id="job-1",
        work_order_ref="docs/work-orders/WO-1.md",
        project_id="project-1",
        max_attempts=4,
    )

    assert job.state is TaskState.NEW
    assert job.worker_id is None
    assert job.attempt_count == 0
    assert job.max_attempts == 4
    assert job.recovery_classification is None
    assert job.version == 1
    assert not hasattr(job, "prompt")
    assert not hasattr(job, "payload")
    assert not hasattr(job, "transcript")


def test_ready_to_claimed_requires_worker_id() -> None:
    ready = make_state(TaskState.READY)

    with pytest.raises(JobStateError) as exc_info:
        plan_job_transition(ready, TaskState.CLAIMED)
    assert exc_info.value.code == "WORKER_ID_REQUIRED"

    plan = plan_job_transition(ready, TaskState.CLAIMED, worker_id="a-worker-01")
    assert plan == JobTransitionPlan(
        target_state=TaskState.CLAIMED,
        worker_id="a-worker-01",
        attempt_count=0,
        recovery_classification=None,
    )


def test_operational_transitions_preserve_claim_and_reject_claim_switch() -> None:
    claimed = make_state(TaskState.CLAIMED, worker_id="a-worker-01")
    gating = plan_job_transition(claimed, TaskState.GATING)
    assert gating.worker_id == "a-worker-01"

    with pytest.raises(JobStateError) as exc_info:
        plan_job_transition(claimed, TaskState.GATING, worker_id="a-worker-02")
    assert exc_info.value.code == "WORKER_CLAIM_CONFLICT"


def test_returning_ready_or_blocked_releases_worker_claim() -> None:
    claimed = make_state(TaskState.CLAIMED, worker_id="a-worker-01")
    assert plan_job_transition(claimed, TaskState.READY).worker_id is None

    gating = make_state(TaskState.GATING, worker_id="a-worker-01")
    assert plan_job_transition(gating, TaskState.BLOCKED).worker_id is None


def test_entering_executing_increments_attempt_and_enforces_budget() -> None:
    gating = make_state(
        TaskState.GATING,
        worker_id="a-worker-01",
        attempt_count=1,
        max_attempts=2,
    )
    plan = plan_job_transition(gating, TaskState.EXECUTING)
    assert plan.attempt_count == 2

    exhausted = make_state(
        TaskState.GATING,
        worker_id="a-worker-01",
        attempt_count=2,
        max_attempts=2,
    )
    with pytest.raises(JobStateError) as exc_info:
        plan_job_transition(exhausted, TaskState.EXECUTING)
    assert exc_info.value.code == "ATTEMPT_BUDGET_EXHAUSTED"


def test_recovery_needed_requires_explicit_classification() -> None:
    executing = make_state(TaskState.EXECUTING, worker_id="a-worker-01", attempt_count=1)

    with pytest.raises(JobStateError) as exc_info:
        plan_job_transition(executing, TaskState.RECOVERY_NEEDED)
    assert exc_info.value.code == "RECOVERY_CLASSIFICATION_REQUIRED"

    plan = plan_job_transition(
        executing,
        TaskState.RECOVERY_NEEDED,
        recovery_classification=RecoveryClassification.PARTIAL_MUTATION,
    )
    assert plan.recovery_classification is RecoveryClassification.PARTIAL_MUTATION
    assert plan.worker_id == "a-worker-01"


@pytest.mark.parametrize(
    ("classification", "target"),
    [
        (RecoveryClassification.NO_MUTATION, TaskState.READY),
        (RecoveryClassification.PARTIAL_MUTATION, TaskState.GATING),
        (RecoveryClassification.MUTATION_COMPLETE_UNVERIFIED, TaskState.VERIFYING),
        (RecoveryClassification.COMPLETE_VERIFIED, TaskState.REVIEW_PENDING),
        (RecoveryClassification.UNEXPECTED_DRIFT, TaskState.BLOCKED),
        (RecoveryClassification.UNKNOWN, TaskState.BLOCKED),
    ],
)
def test_recovery_resume_is_classification_specific(
    classification: RecoveryClassification,
    target: TaskState,
) -> None:
    recovering = make_state(
        TaskState.RECOVERY_NEEDED,
        worker_id="a-worker-01",
        attempt_count=1,
        recovery=classification,
    )

    plan = plan_job_transition(recovering, target)

    assert plan.target_state is target
    assert plan.recovery_classification is None
    if target in {TaskState.READY, TaskState.BLOCKED}:
        assert plan.worker_id is None
    else:
        assert plan.worker_id == "a-worker-01"


def test_recovery_resume_refuses_wrong_target() -> None:
    recovering = make_state(
        TaskState.RECOVERY_NEEDED,
        worker_id="a-worker-01",
        recovery=RecoveryClassification.UNKNOWN,
    )

    with pytest.raises(JobStateError) as exc_info:
        plan_job_transition(recovering, TaskState.READY)
    assert exc_info.value.code == "RECOVERY_TRANSITION_INVALID"


@pytest.mark.parametrize("terminal", [TaskState.COMPLETE, TaskState.FAILED, TaskState.CANCELLED])
def test_terminal_states_cannot_transition(terminal: TaskState) -> None:
    terminal_job = make_state(terminal)
    with pytest.raises(JobStateError) as exc_info:
        plan_job_transition(terminal_job, TaskState.READY)
    assert exc_info.value.code == "JOB_TERMINAL"


def test_invalid_normal_transition_is_refused() -> None:
    ready = make_state(TaskState.READY)
    with pytest.raises(JobStateError) as exc_info:
        plan_job_transition(ready, TaskState.COMPLETE)
    assert exc_info.value.code == "JOB_TRANSITION_INVALID"


def test_runtime_state_validates_budget_version_and_recovery_shape() -> None:
    with pytest.raises(ValueError):
        make_state(TaskState.READY, attempt_count=4, max_attempts=3)
    with pytest.raises(ValueError):
        make_state(TaskState.READY, version=0)
    with pytest.raises(ValueError):
        make_state(TaskState.READY, recovery=RecoveryClassification.UNKNOWN)
    with pytest.raises(ValueError):
        make_state(TaskState.RECOVERY_NEEDED, recovery=None)
