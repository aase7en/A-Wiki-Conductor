from dataclasses import FrozenInstanceError

import pytest

from a_conductor.lifecycle import (
    LifecycleAction,
    LifecycleDecision,
    LifecyclePlan,
    LifecycleStep,
)
from a_conductor.lifecycle_executor import (
    LifecycleCheckpoint,
    LifecycleExecutionState,
    LifecycleExecutor,
    LifecycleStepResult,
)


class FakeBackend:
    def __init__(
        self,
        results: dict[LifecycleStep, LifecycleStepResult] | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.results = results or {}
        self.calls: list[LifecycleStep] = []
        self.events = events

    def execute_step(self, step: LifecycleStep) -> LifecycleStepResult:
        self.calls.append(step)
        if self.events is not None:
            self.events.append(f"step:{step.value}")
        return self.results.get(
            step,
            LifecycleStepResult(success=True, evidence_ref=f"EVID-{step.value}"),
        )


class FakeCheckpointSink:
    def __init__(
        self,
        *,
        fail_on: LifecycleStep | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.fail_on = fail_on
        self.records: list[LifecycleCheckpoint] = []
        self.events = events

    def record(self, checkpoint: LifecycleCheckpoint) -> None:
        if self.events is not None:
            self.events.append(f"checkpoint:{checkpoint.step.value}")
        if checkpoint.step is self.fail_on:
            raise RuntimeError("checkpoint sink unavailable")
        self.records.append(checkpoint)


def execute(
    lifecycle_plan: LifecyclePlan,
    backend,
    sink,
    *,
    transaction_id: str = "txn-001",
):
    return LifecycleExecutor().execute(
        lifecycle_plan,
        backend,
        sink,
        transaction_id=transaction_id,
    )


def plan(
    decision: LifecycleDecision = LifecycleDecision.PROCEED,
    *,
    action: LifecycleAction = LifecycleAction.START,
    steps: tuple[LifecycleStep, ...] = (
        LifecycleStep.VERIFY_ASSIGNMENT,
        LifecycleStep.RENDER_PROFILE,
        LifecycleStep.START_OWNED_PROCESS,
        LifecycleStep.WAIT_READY,
        LifecycleStep.EMIT_EVIDENCE,
    ),
    reason_code: str = "START_ALLOWED",
) -> LifecyclePlan:
    return LifecyclePlan(
        action=action,
        decision=decision,
        reason_code=reason_code,
        steps=steps,
    )


@pytest.mark.parametrize(
    ("decision", "expected_state"),
    [
        (LifecycleDecision.REFUSE, LifecycleExecutionState.REFUSED),
        (LifecycleDecision.NOOP, LifecycleExecutionState.NOOP),
        (
            LifecycleDecision.RECOVERY_REQUIRED,
            LifecycleExecutionState.RECOVERY_REQUIRED,
        ),
    ],
)
def test_non_proceed_plan_never_calls_backend_or_checkpoint(
    decision: LifecycleDecision,
    expected_state: LifecycleExecutionState,
) -> None:
    backend = FakeBackend()
    sink = FakeCheckpointSink()

    result = execute(plan(decision), backend, sink)

    assert result.state is expected_state
    assert result.reason_code == "START_ALLOWED"
    assert result.completed_steps == ()
    assert result.evidence_refs == ()
    assert result.failed_step is None
    assert backend.calls == []
    assert sink.records == []


def test_proceed_executes_each_step_then_checkpoints_before_next_step() -> None:
    events: list[str] = []
    backend = FakeBackend(events=events)
    sink = FakeCheckpointSink(events=events)
    lifecycle_plan = plan(
        steps=(
            LifecycleStep.VERIFY_ASSIGNMENT,
            LifecycleStep.RENDER_PROFILE,
            LifecycleStep.PREFLIGHT,
        )
    )

    result = execute(lifecycle_plan, backend, sink)

    assert result.state is LifecycleExecutionState.COMPLETE
    assert result.completed_steps == lifecycle_plan.steps
    assert result.evidence_refs == (
        "EVID-VERIFY_ASSIGNMENT",
        "EVID-RENDER_PROFILE",
        "EVID-PREFLIGHT",
    )
    assert events == [
        "step:VERIFY_ASSIGNMENT",
        "checkpoint:VERIFY_ASSIGNMENT",
        "step:RENDER_PROFILE",
        "checkpoint:RENDER_PROFILE",
        "step:PREFLIGHT",
        "checkpoint:PREFLIGHT",
    ]


def test_checkpoint_records_action_step_and_evidence_ref() -> None:
    backend = FakeBackend()
    sink = FakeCheckpointSink()

    execute(
        plan(action=LifecycleAction.RESTART, steps=(LifecycleStep.TARGETED_STOP,)),
        backend,
        sink,
    )

    assert sink.records == [
        LifecycleCheckpoint(
            transaction_id="txn-001",
            sequence_no=1,
            action=LifecycleAction.RESTART,
            step=LifecycleStep.TARGETED_STOP,
            evidence_ref="EVID-TARGETED_STOP",
        )
    ]


def test_step_failure_halts_later_steps() -> None:
    backend = FakeBackend(
        {
            LifecycleStep.PREFLIGHT: LifecycleStepResult(
                success=False,
                evidence_ref="EVID-PREFLIGHT-FAIL",
                error_code="PREFLIGHT_FAILED",
            )
        }
    )
    sink = FakeCheckpointSink()
    lifecycle_plan = plan(
        steps=(
            LifecycleStep.VERIFY_RESOURCES,
            LifecycleStep.PREFLIGHT,
            LifecycleStep.START_OWNED_PROCESS,
        )
    )

    result = execute(lifecycle_plan, backend, sink)

    assert result.state is LifecycleExecutionState.FAILED
    assert result.reason_code == "PREFLIGHT_FAILED"
    assert result.failed_step is LifecycleStep.PREFLIGHT
    assert result.completed_steps == (LifecycleStep.VERIFY_RESOURCES,)
    assert backend.calls == [
        LifecycleStep.VERIFY_RESOURCES,
        LifecycleStep.PREFLIGHT,
    ]
    assert [item.step for item in sink.records] == [LifecycleStep.VERIFY_RESOURCES]


def test_backend_declared_uncertain_mutation_requires_recovery() -> None:
    backend = FakeBackend(
        {
            LifecycleStep.START_OWNED_PROCESS: LifecycleStepResult(
                success=False,
                evidence_ref="EVID-START-UNCERTAIN",
                error_code="PROCESS_START_UNCERTAIN",
                recovery_required=True,
            )
        }
    )
    sink = FakeCheckpointSink()
    lifecycle_plan = plan(
        steps=(
            LifecycleStep.RENDER_PROFILE,
            LifecycleStep.START_OWNED_PROCESS,
            LifecycleStep.WAIT_READY,
        )
    )

    result = execute(lifecycle_plan, backend, sink)

    assert result.state is LifecycleExecutionState.RECOVERY_REQUIRED
    assert result.reason_code == "PROCESS_START_UNCERTAIN"
    assert result.failed_step is LifecycleStep.START_OWNED_PROCESS
    assert result.completed_steps == (LifecycleStep.RENDER_PROFILE,)
    assert LifecycleStep.WAIT_READY not in backend.calls


def test_checkpoint_failure_after_mutating_step_requires_recovery_and_halts() -> None:
    events: list[str] = []
    backend = FakeBackend(events=events)
    sink = FakeCheckpointSink(
        fail_on=LifecycleStep.START_OWNED_PROCESS,
        events=events,
    )
    lifecycle_plan = plan(
        steps=(
            LifecycleStep.VERIFY_RESOURCES,
            LifecycleStep.START_OWNED_PROCESS,
            LifecycleStep.WAIT_READY,
        )
    )

    result = execute(lifecycle_plan, backend, sink)

    assert result.state is LifecycleExecutionState.RECOVERY_REQUIRED
    assert result.reason_code == "CHECKPOINT_PERSISTENCE_FAILED"
    assert result.failed_step is LifecycleStep.START_OWNED_PROCESS
    assert result.completed_steps == (LifecycleStep.VERIFY_RESOURCES,)
    assert LifecycleStep.WAIT_READY not in backend.calls
    assert events[-1] == "checkpoint:START_OWNED_PROCESS"


def test_checkpoint_failure_after_non_mutating_step_is_failed_not_recovery() -> None:
    backend = FakeBackend()
    sink = FakeCheckpointSink(fail_on=LifecycleStep.VERIFY_ASSIGNMENT)
    lifecycle_plan = plan(
        steps=(
            LifecycleStep.VERIFY_ASSIGNMENT,
            LifecycleStep.RENDER_PROFILE,
        )
    )

    result = execute(lifecycle_plan, backend, sink)

    assert result.state is LifecycleExecutionState.FAILED
    assert result.reason_code == "CHECKPOINT_FAILED"
    assert result.failed_step is LifecycleStep.VERIFY_ASSIGNMENT
    assert result.completed_steps == ()
    assert backend.calls == [LifecycleStep.VERIFY_ASSIGNMENT]


@pytest.mark.parametrize(
    "step",
    [
        LifecycleStep.RENDER_PROFILE,
        LifecycleStep.START_OWNED_PROCESS,
        LifecycleStep.TARGETED_STOP,
        LifecycleStep.CLEAR_ASSIGNMENT,
    ],
)
def test_each_mutating_step_requires_recovery_if_its_checkpoint_fails(
    step: LifecycleStep,
) -> None:
    backend = FakeBackend()
    sink = FakeCheckpointSink(fail_on=step)

    result = execute(plan(steps=(step,)), backend, sink)

    assert result.state is LifecycleExecutionState.RECOVERY_REQUIRED
    assert result.reason_code == "CHECKPOINT_PERSISTENCE_FAILED"
    assert result.failed_step is step


def test_success_with_no_evidence_ref_still_checkpoints_and_completes() -> None:
    backend = FakeBackend(
        {
            LifecycleStep.VERIFY_ASSIGNMENT: LifecycleStepResult(
                success=True,
                evidence_ref=None,
            )
        }
    )
    sink = FakeCheckpointSink()

    result = execute(
        plan(steps=(LifecycleStep.VERIFY_ASSIGNMENT,)),
        backend,
        sink,
    )

    assert result.state is LifecycleExecutionState.COMPLETE
    assert result.evidence_refs == ()
    assert sink.records[0].evidence_ref is None


def test_empty_proceed_plan_completes_without_backend_calls() -> None:
    backend = FakeBackend()
    sink = FakeCheckpointSink()

    result = execute(plan(steps=()), backend, sink)

    assert result.state is LifecycleExecutionState.COMPLETE
    assert result.completed_steps == ()
    assert backend.calls == []
    assert sink.records == []


def test_execution_result_is_immutable() -> None:
    result = execute(plan(steps=()), FakeBackend(), FakeCheckpointSink())

    with pytest.raises(FrozenInstanceError):
        result.reason_code = "mutated"  # type: ignore[misc]


def test_backend_exception_on_non_mutating_step_fails_safely() -> None:
    class ExplodingBackend:
        def execute_step(self, step: LifecycleStep) -> LifecycleStepResult:
            raise RuntimeError("backend transport failed")

    result = execute(
        plan(steps=(LifecycleStep.VERIFY_RESOURCES,)),
        ExplodingBackend(),
        FakeCheckpointSink(),
    )

    assert result.state is LifecycleExecutionState.FAILED
    assert result.reason_code == "BACKEND_EXECUTION_ERROR"
    assert result.failed_step is LifecycleStep.VERIFY_RESOURCES
    assert result.completed_steps == ()


def test_backend_exception_on_mutating_step_requires_recovery() -> None:
    class ExplodingBackend:
        def execute_step(self, step: LifecycleStep) -> LifecycleStepResult:
            raise RuntimeError("mutation outcome unknown")

    result = execute(
        plan(steps=(LifecycleStep.TARGETED_STOP,)),
        ExplodingBackend(),
        FakeCheckpointSink(),
    )

    assert result.state is LifecycleExecutionState.RECOVERY_REQUIRED
    assert result.reason_code == "BACKEND_EXECUTION_UNCERTAIN"
    assert result.failed_step is LifecycleStep.TARGETED_STOP
    assert result.completed_steps == ()


def test_checkpoint_sequence_is_one_based_and_transaction_scoped() -> None:
    sink = FakeCheckpointSink()
    result = execute(
        plan(steps=(LifecycleStep.VERIFY_ASSIGNMENT, LifecycleStep.PREFLIGHT)),
        FakeBackend(),
        sink,
        transaction_id="txn-recovery-42",
    )

    assert result.transaction_id == "txn-recovery-42"
    assert [(item.transaction_id, item.sequence_no) for item in sink.records] == [
        ("txn-recovery-42", 1),
        ("txn-recovery-42", 2),
    ]


def test_blank_transaction_id_is_rejected_before_backend_call() -> None:
    backend = FakeBackend()
    sink = FakeCheckpointSink()

    with pytest.raises(ValueError, match="transaction_id must not be blank"):
        execute(plan(steps=(LifecycleStep.VERIFY_ASSIGNMENT,)), backend, sink, transaction_id=" " )

    assert backend.calls == []
    assert sink.records == []
