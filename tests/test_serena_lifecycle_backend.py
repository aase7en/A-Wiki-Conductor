from dataclasses import FrozenInstanceError

import pytest

from a_conductor.lifecycle import LifecycleStep
from a_conductor.lifecycle_executor import LifecycleStepResult
from a_conductor.owned_process import (
    OwnedProcessMutationResult,
    OwnedProcessMutationState,
)
from a_conductor.serena_lifecycle_backend import (
    SerenaLifecycleBackend,
    SerenaLifecycleOperations,
    SerenaOperationResult,
)


class FakeOperations:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.results: dict[str, SerenaOperationResult] = {}
        self.start_result = OwnedProcessMutationResult(
            OwnedProcessMutationState.STARTED,
            "STARTED",
            1234,
        )
        self.stop_result = OwnedProcessMutationResult(
            OwnedProcessMutationState.STOPPED,
            "STOPPED",
            1234,
        )

    def _result(self, name: str) -> SerenaOperationResult:
        self.calls.append(name)
        return self.results.get(
            name,
            SerenaOperationResult(success=True, evidence_ref=f"EVID-{name}"),
        )

    def verify_assignment(self) -> SerenaOperationResult:
        return self._result("verify_assignment")

    def verify_resources(self) -> SerenaOperationResult:
        return self._result("verify_resources")

    def render_profile(self) -> SerenaOperationResult:
        return self._result("render_profile")

    def preflight(self) -> SerenaOperationResult:
        return self._result("preflight")

    def start_owned_process(self) -> OwnedProcessMutationResult:
        self.calls.append("start_owned_process")
        return self.start_result

    def wait_ready(self) -> SerenaOperationResult:
        return self._result("wait_ready")

    def verify_project_identity(self) -> SerenaOperationResult:
        return self._result("verify_project_identity")

    def targeted_stop(self) -> OwnedProcessMutationResult:
        self.calls.append("targeted_stop")
        return self.stop_result

    def wait_exit(self) -> SerenaOperationResult:
        return self._result("wait_exit")

    def verify_released(self) -> SerenaOperationResult:
        return self._result("verify_released")

    def clear_assignment(self) -> SerenaOperationResult:
        return self._result("clear_assignment")

    def emit_evidence(self) -> SerenaOperationResult:
        return self._result("emit_evidence")


@pytest.mark.parametrize(
    ("step", "method_name"),
    [
        (LifecycleStep.VERIFY_ASSIGNMENT, "verify_assignment"),
        (LifecycleStep.VERIFY_RESOURCES, "verify_resources"),
        (LifecycleStep.RENDER_PROFILE, "render_profile"),
        (LifecycleStep.PREFLIGHT, "preflight"),
        (LifecycleStep.WAIT_READY, "wait_ready"),
        (LifecycleStep.VERIFY_PROJECT_IDENTITY, "verify_project_identity"),
        (LifecycleStep.WAIT_EXIT, "wait_exit"),
        (LifecycleStep.VERIFY_RELEASED, "verify_released"),
        (LifecycleStep.CLEAR_ASSIGNMENT, "clear_assignment"),
        (LifecycleStep.EMIT_EVIDENCE, "emit_evidence"),
    ],
)
def test_non_process_steps_delegate_exactly_once(step: LifecycleStep, method_name: str) -> None:
    operations = FakeOperations()
    backend = SerenaLifecycleBackend(operations)

    result = backend.execute_step(step)

    assert result == LifecycleStepResult(
        success=True,
        evidence_ref=f"EVID-{method_name}",
    )
    assert operations.calls == [method_name]


def test_operation_failure_preserves_error_and_recovery_flag() -> None:
    operations = FakeOperations()
    operations.results["verify_resources"] = SerenaOperationResult(
        success=False,
        evidence_ref="EVID-resource-failure",
        error_code="PORT_STATE_UNKNOWN",
        recovery_required=True,
    )

    result = SerenaLifecycleBackend(operations).execute_step(LifecycleStep.VERIFY_RESOURCES)

    assert result == LifecycleStepResult(
        success=False,
        evidence_ref="EVID-resource-failure",
        error_code="PORT_STATE_UNKNOWN",
        recovery_required=True,
    )


@pytest.mark.parametrize(
    "state",
    [OwnedProcessMutationState.STARTED, OwnedProcessMutationState.ALREADY_RUNNING],
)
def test_start_owned_process_success_states(state: OwnedProcessMutationState) -> None:
    operations = FakeOperations()
    operations.start_result = OwnedProcessMutationResult(state, state.value, 777)

    result = SerenaLifecycleBackend(operations).execute_step(
        LifecycleStep.START_OWNED_PROCESS
    )

    assert result == LifecycleStepResult(success=True)
    assert operations.calls == ["start_owned_process"]


@pytest.mark.parametrize(
    "state",
    [OwnedProcessMutationState.STOPPED, OwnedProcessMutationState.NOT_RUNNING],
)
def test_targeted_stop_success_states(state: OwnedProcessMutationState) -> None:
    operations = FakeOperations()
    operations.stop_result = OwnedProcessMutationResult(state, state.value, 777)

    result = SerenaLifecycleBackend(operations).execute_step(LifecycleStep.TARGETED_STOP)

    assert result == LifecycleStepResult(success=True)
    assert operations.calls == ["targeted_stop"]


def test_start_refusal_propagates_reason_without_recovery() -> None:
    operations = FakeOperations()
    operations.start_result = OwnedProcessMutationResult(
        OwnedProcessMutationState.REFUSED,
        "PID_MISMATCH",
        777,
    )

    result = SerenaLifecycleBackend(operations).execute_step(
        LifecycleStep.START_OWNED_PROCESS
    )

    assert result == LifecycleStepResult(
        success=False,
        error_code="PID_MISMATCH",
        recovery_required=False,
    )


def test_start_recovery_required_propagates_reason() -> None:
    operations = FakeOperations()
    operations.start_result = OwnedProcessMutationResult(
        OwnedProcessMutationState.RECOVERY_REQUIRED,
        "STALE_PID_METADATA",
        777,
    )

    result = SerenaLifecycleBackend(operations).execute_step(
        LifecycleStep.START_OWNED_PROCESS
    )

    assert result == LifecycleStepResult(
        success=False,
        error_code="STALE_PID_METADATA",
        recovery_required=True,
    )


def test_stop_refusal_propagates_reason_without_recovery() -> None:
    operations = FakeOperations()
    operations.stop_result = OwnedProcessMutationResult(
        OwnedProcessMutationState.REFUSED,
        "PID_MISMATCH",
        777,
    )

    result = SerenaLifecycleBackend(operations).execute_step(LifecycleStep.TARGETED_STOP)

    assert result == LifecycleStepResult(
        success=False,
        error_code="PID_MISMATCH",
        recovery_required=False,
    )


def test_stop_recovery_required_propagates_reason() -> None:
    operations = FakeOperations()
    operations.stop_result = OwnedProcessMutationResult(
        OwnedProcessMutationState.RECOVERY_REQUIRED,
        "PROCESS_STOP_FAILED",
        777,
    )

    result = SerenaLifecycleBackend(operations).execute_step(LifecycleStep.TARGETED_STOP)

    assert result == LifecycleStepResult(
        success=False,
        error_code="PROCESS_STOP_FAILED",
        recovery_required=True,
    )


@pytest.mark.parametrize(
    ("step", "state"),
    [
        (LifecycleStep.START_OWNED_PROCESS, OwnedProcessMutationState.STOPPED),
        (LifecycleStep.TARGETED_STOP, OwnedProcessMutationState.STARTED),
    ],
)
def test_unexpected_owned_process_state_fails_closed(
    step: LifecycleStep,
    state: OwnedProcessMutationState,
) -> None:
    operations = FakeOperations()
    unexpected = OwnedProcessMutationResult(state, state.value, 777)
    if step is LifecycleStep.START_OWNED_PROCESS:
        operations.start_result = unexpected
    else:
        operations.stop_result = unexpected

    result = SerenaLifecycleBackend(operations).execute_step(step)

    assert result.success is False
    assert result.error_code == "UNEXPECTED_OWNED_PROCESS_STATE"
    assert result.recovery_required is True


def test_invalid_step_fails_closed_without_calling_operations() -> None:
    operations = FakeOperations()
    backend = SerenaLifecycleBackend(operations)

    result = backend.execute_step("NOT_A_STEP")  # type: ignore[arg-type]

    assert result == LifecycleStepResult(
        success=False,
        error_code="UNSUPPORTED_LIFECYCLE_STEP",
        recovery_required=False,
    )
    assert operations.calls == []


def test_operation_result_is_frozen() -> None:
    result = SerenaOperationResult(success=True)
    with pytest.raises(FrozenInstanceError):
        result.success = False  # type: ignore[misc]


def test_operations_protocol_is_runtime_checkable() -> None:
    assert isinstance(FakeOperations(), SerenaLifecycleOperations)
