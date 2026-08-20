"""Serena-specific composition for approved lifecycle steps.

This module is deliberately an orchestration adapter, not a host-I/O layer.
Every lifecycle step is delegated to one explicit pre-bound collaborator.
Host mutation remains behind the existing exact-owned process boundary and
checkpoint durability remains owned by :mod:`a_conductor.lifecycle_executor`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .lifecycle import LifecycleStep
from .lifecycle_executor import LifecycleStepResult
from .owned_process import OwnedProcessMutationResult, OwnedProcessMutationState


@dataclass(frozen=True, slots=True)
class SerenaOperationResult:
    success: bool
    evidence_ref: str | None = None
    error_code: str | None = None
    recovery_required: bool = False


@runtime_checkable
class SerenaLifecycleOperations(Protocol):
    def verify_assignment(self) -> SerenaOperationResult: ...

    def verify_resources(self) -> SerenaOperationResult: ...

    def render_profile(self) -> SerenaOperationResult: ...

    def preflight(self) -> SerenaOperationResult: ...

    def start_owned_process(self) -> OwnedProcessMutationResult: ...

    def wait_ready(self) -> SerenaOperationResult: ...

    def verify_project_identity(self) -> SerenaOperationResult: ...

    def targeted_stop(self) -> OwnedProcessMutationResult: ...

    def wait_exit(self) -> SerenaOperationResult: ...

    def verify_released(self) -> SerenaOperationResult: ...

    def clear_assignment(self) -> SerenaOperationResult: ...

    def emit_evidence(self) -> SerenaOperationResult: ...


def _to_step_result(result: SerenaOperationResult) -> LifecycleStepResult:
    return LifecycleStepResult(
        success=result.success,
        evidence_ref=result.evidence_ref,
        error_code=result.error_code,
        recovery_required=result.recovery_required,
    )


def _owned_process_result(
    result: OwnedProcessMutationResult,
    *,
    success_states: frozenset[OwnedProcessMutationState],
) -> LifecycleStepResult:
    if result.state in success_states:
        return LifecycleStepResult(success=True)
    if result.state is OwnedProcessMutationState.REFUSED:
        return LifecycleStepResult(
            success=False,
            error_code=result.reason_code,
            recovery_required=False,
        )
    if result.state is OwnedProcessMutationState.RECOVERY_REQUIRED:
        return LifecycleStepResult(
            success=False,
            error_code=result.reason_code,
            recovery_required=True,
        )
    return LifecycleStepResult(
        success=False,
        error_code="UNEXPECTED_OWNED_PROCESS_STATE",
        recovery_required=True,
    )


class SerenaLifecycleBackend:
    """Map an approved symbolic lifecycle step to one explicit operation."""

    _NON_PROCESS_METHODS = {
        LifecycleStep.VERIFY_ASSIGNMENT: "verify_assignment",
        LifecycleStep.VERIFY_RESOURCES: "verify_resources",
        LifecycleStep.RENDER_PROFILE: "render_profile",
        LifecycleStep.PREFLIGHT: "preflight",
        LifecycleStep.WAIT_READY: "wait_ready",
        LifecycleStep.VERIFY_PROJECT_IDENTITY: "verify_project_identity",
        LifecycleStep.WAIT_EXIT: "wait_exit",
        LifecycleStep.VERIFY_RELEASED: "verify_released",
        LifecycleStep.CLEAR_ASSIGNMENT: "clear_assignment",
        LifecycleStep.EMIT_EVIDENCE: "emit_evidence",
    }

    def __init__(self, operations: SerenaLifecycleOperations) -> None:
        self._operations = operations

    def execute_step(self, step: LifecycleStep) -> LifecycleStepResult:
        if not isinstance(step, LifecycleStep):
            return LifecycleStepResult(
                success=False,
                error_code="UNSUPPORTED_LIFECYCLE_STEP",
            )

        if step is LifecycleStep.START_OWNED_PROCESS:
            return _owned_process_result(
                self._operations.start_owned_process(),
                success_states=frozenset(
                    {
                        OwnedProcessMutationState.STARTED,
                        OwnedProcessMutationState.ALREADY_RUNNING,
                    }
                ),
            )

        if step is LifecycleStep.TARGETED_STOP:
            return _owned_process_result(
                self._operations.targeted_stop(),
                success_states=frozenset(
                    {
                        OwnedProcessMutationState.STOPPED,
                        OwnedProcessMutationState.NOT_RUNNING,
                    }
                ),
            )

        method_name = self._NON_PROCESS_METHODS.get(step)
        if method_name is None:
            return LifecycleStepResult(
                success=False,
                error_code="UNSUPPORTED_LIFECYCLE_STEP",
            )
        operation = getattr(self._operations, method_name)
        return _to_step_result(operation())
