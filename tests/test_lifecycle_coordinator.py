from __future__ import annotations

from dataclasses import replace

import pytest

from a_conductor.domain import WorkerState
from a_conductor.lifecycle import (
    LifecycleAction,
    LifecycleContext,
    LifecycleStep,
)
from a_conductor.lifecycle_coordinator import (
    LifecycleCoordinator,
    LifecycleCoordinatorError,
)
from a_conductor.lifecycle_executor import (
    LifecycleCheckpoint,
    LifecycleExecutionState,
    LifecycleStepResult,
)
from a_conductor.runtime_safety import (
    PortBindingState,
    ProcessOwnership,
    TunnelBindingState,
    WorktreeBindingState,
)


def context_for(action: LifecycleAction) -> LifecycleContext:
    if action is LifecycleAction.START:
        return LifecycleContext(
            action=action,
            worker_state=WorkerState.STOPPED,
            assignment_present=True,
            project_exists=True,
            process_ownership=ProcessOwnership.ABSENT,
            port_binding=PortBindingState.FREE,
            tunnel_required=True,
            tunnel_binding=TunnelBindingState.FREE,
            worktree_binding=WorktreeBindingState.OWNED,
            project_identity_ok=False,
            ready=False,
            active_task=False,
        )
    if action is LifecycleAction.STOP:
        return LifecycleContext(
            action=action,
            worker_state=WorkerState.READY,
            assignment_present=True,
            project_exists=True,
            process_ownership=ProcessOwnership.OWNED,
            port_binding=PortBindingState.OWNED,
            tunnel_required=True,
            tunnel_binding=TunnelBindingState.OWNED,
            worktree_binding=WorktreeBindingState.OWNED,
            project_identity_ok=True,
            ready=True,
            active_task=False,
        )
    if action is LifecycleAction.RESTART:
        return LifecycleContext(
            action=action,
            worker_state=WorkerState.READY,
            assignment_present=True,
            project_exists=True,
            process_ownership=ProcessOwnership.OWNED,
            port_binding=PortBindingState.OWNED,
            tunnel_required=True,
            tunnel_binding=TunnelBindingState.OWNED,
            worktree_binding=WorktreeBindingState.OWNED,
            project_identity_ok=True,
            ready=True,
            active_task=False,
        )
    return LifecycleContext(
        action=action,
        worker_state=WorkerState.STOPPED,
        assignment_present=True,
        project_exists=True,
        process_ownership=ProcessOwnership.ABSENT,
        port_binding=PortBindingState.FREE,
        tunnel_required=True,
        tunnel_binding=TunnelBindingState.FREE,
        worktree_binding=WorktreeBindingState.OWNED,
        project_identity_ok=False,
        ready=False,
        active_task=False,
    )


class FakeContextProvider:
    def __init__(self, context: LifecycleContext) -> None:
        self.context = context
        self.calls = []

    def observe(self, worker_id: str, action: LifecycleAction) -> LifecycleContext:
        self.calls.append((worker_id, action))
        return self.context


class FakeBackend:
    def __init__(self, fail_step: LifecycleStep | None = None, *, recovery: bool = False) -> None:
        self.fail_step = fail_step
        self.recovery = recovery
        self.calls: list[LifecycleStep] = []

    def execute_step(self, step: LifecycleStep) -> LifecycleStepResult:
        self.calls.append(step)
        if step is self.fail_step:
            return LifecycleStepResult(
                success=False,
                error_code="SIMULATED_STEP_FAILURE",
                recovery_required=self.recovery,
            )
        return LifecycleStepResult(success=True, evidence_ref=f"EVID-{step.value}")


class FakeBackendFactory:
    def __init__(self, backend: FakeBackend) -> None:
        self.backend = backend
        self.calls = []

    def create(self, worker_id: str, action: LifecycleAction):
        self.calls.append((worker_id, action))
        return self.backend


class FakeCheckpointSink:
    def __init__(self) -> None:
        self.records: list[LifecycleCheckpoint] = []

    def record(self, checkpoint: LifecycleCheckpoint) -> None:
        self.records.append(checkpoint)


class FakeStateService:
    def __init__(self, *, fail_on: WorkerState | None = None) -> None:
        self.fail_on = fail_on
        self.calls: list[tuple[str, WorkerState]] = []

    def set_worker_state(self, worker_id: str, state: WorkerState):
        self.calls.append((worker_id, state))
        if state is self.fail_on:
            raise RuntimeError("state persistence failed")
        return object()


def coordinator(action: LifecycleAction, *, backend=None, state_service=None, context=None):
    context_provider = FakeContextProvider(context or context_for(action))
    backend = backend or FakeBackend()
    backend_factory = FakeBackendFactory(backend)
    state_service = state_service or FakeStateService()
    sink = FakeCheckpointSink()
    instance = LifecycleCoordinator(
        context_provider=context_provider,
        backend_factory=backend_factory,
        checkpoint_sink=sink,
        state_service=state_service,
        transaction_id_factory=lambda: "tx-001",
    )
    return instance, context_provider, backend_factory, state_service, sink


def test_start_proceed_transitions_starting_then_ready_and_checkpoints() -> None:
    instance, provider, factory, states, sink = coordinator(LifecycleAction.START)

    result = instance.execute("a-worker-01", LifecycleAction.START)

    assert result.state is LifecycleExecutionState.COMPLETE
    assert result.transaction_id == "tx-001"
    assert provider.calls == [("a-worker-01", LifecycleAction.START)]
    assert states.calls == [
        ("a-worker-01", WorkerState.STARTING),
        ("a-worker-01", WorkerState.READY),
    ]
    assert factory.calls == [("a-worker-01", LifecycleAction.START)]
    assert len(sink.records) == len(result.completed_steps)
    assert all(record.transaction_id == "tx-001" for record in sink.records)


def test_stop_proceed_transitions_stopping_then_stopped() -> None:
    instance, _, _, states, _ = coordinator(LifecycleAction.STOP)
    result = instance.execute("a-worker-01", LifecycleAction.STOP)
    assert result.state is LifecycleExecutionState.COMPLETE
    assert states.calls == [
        ("a-worker-01", WorkerState.STOPPING),
        ("a-worker-01", WorkerState.STOPPED),
    ]


def test_restart_proceed_transitions_starting_then_ready() -> None:
    instance, _, _, states, _ = coordinator(LifecycleAction.RESTART)
    result = instance.execute("a-worker-01", LifecycleAction.RESTART)
    assert result.state is LifecycleExecutionState.COMPLETE
    assert states.calls == [
        ("a-worker-01", WorkerState.STARTING),
        ("a-worker-01", WorkerState.READY),
    ]


def test_refused_plan_leaves_state_unchanged_and_skips_backend_factory() -> None:
    refused_context = replace(
        context_for(LifecycleAction.START),
        assignment_present=False,
    )
    instance, _, factory, states, sink = coordinator(
        LifecycleAction.START,
        context=refused_context,
    )

    result = instance.execute("a-worker-01", LifecycleAction.START)

    assert result.state is LifecycleExecutionState.REFUSED
    assert states.calls == []
    assert factory.calls == []
    assert sink.records == []


def test_noop_start_sets_ready_without_backend_factory() -> None:
    noop = LifecycleContext(
        action=LifecycleAction.START,
        worker_state=WorkerState.READY,
        assignment_present=True,
        project_exists=True,
        process_ownership=ProcessOwnership.OWNED,
        port_binding=PortBindingState.OWNED,
        tunnel_required=True,
        tunnel_binding=TunnelBindingState.OWNED,
        worktree_binding=WorktreeBindingState.OWNED,
        project_identity_ok=True,
        ready=True,
        active_task=False,
    )
    instance, _, factory, states, _ = coordinator(LifecycleAction.START, context=noop)
    result = instance.execute("a-worker-01", LifecycleAction.START)
    assert result.state is LifecycleExecutionState.NOOP
    assert factory.calls == []
    assert states.calls == [("a-worker-01", WorkerState.READY)]


def test_recovery_required_plan_sets_error_without_backend_factory() -> None:
    stale = context_for(LifecycleAction.START)
    stale = LifecycleContext(
        action=stale.action,
        worker_state=stale.worker_state,
        assignment_present=stale.assignment_present,
        project_exists=stale.project_exists,
        process_ownership=ProcessOwnership.STALE,
        port_binding=stale.port_binding,
        tunnel_required=stale.tunnel_required,
        tunnel_binding=stale.tunnel_binding,
        worktree_binding=stale.worktree_binding,
        project_identity_ok=stale.project_identity_ok,
        ready=stale.ready,
        active_task=stale.active_task,
    )
    instance, _, factory, states, _ = coordinator(LifecycleAction.START, context=stale)
    result = instance.execute("a-worker-01", LifecycleAction.START)
    assert result.state is LifecycleExecutionState.RECOVERY_REQUIRED
    assert factory.calls == []
    assert states.calls == [("a-worker-01", WorkerState.ERROR)]


def test_failed_execution_sets_worker_error() -> None:
    backend = FakeBackend(fail_step=LifecycleStep.VERIFY_RESOURCES)
    instance, _, _, states, _ = coordinator(LifecycleAction.START, backend=backend)
    result = instance.execute("a-worker-01", LifecycleAction.START)
    assert result.state is LifecycleExecutionState.FAILED
    assert states.calls[-1] == ("a-worker-01", WorkerState.ERROR)


def test_recovery_execution_sets_worker_error() -> None:
    backend = FakeBackend(
        fail_step=LifecycleStep.RENDER_PROFILE,
        recovery=True,
    )
    instance, _, _, states, _ = coordinator(LifecycleAction.START, backend=backend)
    result = instance.execute("a-worker-01", LifecycleAction.START)
    assert result.state is LifecycleExecutionState.RECOVERY_REQUIRED
    assert states.calls[-1] == ("a-worker-01", WorkerState.ERROR)


def test_pre_execution_state_persistence_failure_stops_before_backend() -> None:
    state_service = FakeStateService(fail_on=WorkerState.STARTING)
    instance, _, factory, states, sink = coordinator(
        LifecycleAction.START,
        state_service=state_service,
    )
    with pytest.raises(LifecycleCoordinatorError) as exc_info:
        instance.execute("a-worker-01", LifecycleAction.START)
    assert exc_info.value.code == "WORKER_STATE_PERSISTENCE_FAILED"
    assert exc_info.value.recovery_required is False
    assert factory.calls == []
    assert sink.records == []


def test_final_state_persistence_failure_requires_recovery() -> None:
    state_service = FakeStateService(fail_on=WorkerState.READY)
    instance, _, _, _, sink = coordinator(
        LifecycleAction.START,
        state_service=state_service,
    )
    with pytest.raises(LifecycleCoordinatorError) as exc_info:
        instance.execute("a-worker-01", LifecycleAction.START)
    assert exc_info.value.code == "WORKER_STATE_PERSISTENCE_FAILED"
    assert exc_info.value.recovery_required is True
    assert sink.records


def test_transaction_id_must_be_non_blank() -> None:
    instance, *_ = coordinator(LifecycleAction.START)
    instance._transaction_id_factory = lambda: ""  # type: ignore[attr-defined]
    with pytest.raises(LifecycleCoordinatorError) as exc_info:
        instance.execute("a-worker-01", LifecycleAction.START)
    assert exc_info.value.code == "TRANSACTION_ID_INVALID"


def test_coordinator_error_is_frozen_in_recovery_flag_semantics() -> None:
    error = LifecycleCoordinatorError("X", recovery_required=True)
    assert error.recovery_required is True
