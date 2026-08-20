"""Application-level lifecycle coordination.

The coordinator is the single application boundary that converts a fresh
runtime observation into a pure lifecycle plan, executes that plan through the
checkpointed executor, and persists the resulting worker state. It contains no
host I/O, Serena assembly, Git, network, or persistence implementation itself.
"""

from __future__ import annotations

import uuid
from typing import Callable, Protocol

from .domain import WorkerState
from .lifecycle import (
    LifecycleAction,
    LifecycleContext,
    LifecycleDecision,
    LifecyclePlan,
    plan_lifecycle,
)
from .lifecycle_executor import (
    LifecycleCheckpointSink,
    LifecycleExecutionResult,
    LifecycleExecutionState,
    LifecycleExecutor,
    LifecycleStep,
    LifecycleStepBackend,
    LifecycleStepResult,
)


class LifecycleContextProvider(Protocol):
    def observe(
        self,
        worker_id: str,
        action: LifecycleAction,
    ) -> LifecycleContext: ...


class LifecycleBackendFactory(Protocol):
    def create(
        self,
        worker_id: str,
        action: LifecycleAction,
    ) -> LifecycleStepBackend: ...


class WorkerStateService(Protocol):
    def set_worker_state(self, worker_id: str, state: WorkerState): ...


class LifecycleCoordinatorError(RuntimeError):
    def __init__(self, code: str, *, recovery_required: bool = False) -> None:
        self.code = code
        self.recovery_required = bool(recovery_required)
        super().__init__(code)


class _NonProceedBackend:
    """Sentinel backend; the executor must never call it for non-PROCEED plans."""

    def execute_step(self, step: LifecycleStep) -> LifecycleStepResult:
        raise AssertionError(f"non-proceed plan attempted backend step: {step.value}")


def _default_transaction_id() -> str:
    return f"lifecycle-{uuid.uuid4().hex}"


def _pre_execution_state(action: LifecycleAction) -> WorkerState | None:
    if action in {LifecycleAction.START, LifecycleAction.RESTART}:
        return WorkerState.STARTING
    if action is LifecycleAction.STOP:
        return WorkerState.STOPPING
    return None


def _successful_state(action: LifecycleAction) -> WorkerState:
    if action in {LifecycleAction.START, LifecycleAction.RESTART}:
        return WorkerState.READY
    return WorkerState.STOPPED


class LifecycleCoordinator:
    def __init__(
        self,
        *,
        context_provider: LifecycleContextProvider,
        backend_factory: LifecycleBackendFactory,
        checkpoint_sink: LifecycleCheckpointSink,
        state_service: WorkerStateService,
        planner: Callable[[LifecycleContext], LifecyclePlan] = plan_lifecycle,
        executor: LifecycleExecutor | None = None,
        transaction_id_factory: Callable[[], str] = _default_transaction_id,
    ) -> None:
        self._context_provider = context_provider
        self._backend_factory = backend_factory
        self._checkpoint_sink = checkpoint_sink
        self._state_service = state_service
        self._planner = planner
        self._executor = executor or LifecycleExecutor()
        self._transaction_id_factory = transaction_id_factory

    def _transaction_id(self) -> str:
        try:
            transaction_id = self._transaction_id_factory()
        except Exception as exc:
            raise LifecycleCoordinatorError("TRANSACTION_ID_INVALID") from exc
        if not isinstance(transaction_id, str) or not transaction_id.strip():
            raise LifecycleCoordinatorError("TRANSACTION_ID_INVALID")
        return transaction_id.strip()

    def _persist_state(
        self,
        worker_id: str,
        state: WorkerState,
        *,
        recovery_required: bool,
    ) -> None:
        try:
            self._state_service.set_worker_state(worker_id, state)
        except Exception as exc:
            raise LifecycleCoordinatorError(
                "WORKER_STATE_PERSISTENCE_FAILED",
                recovery_required=recovery_required,
            ) from exc

    def _observe_and_plan(
        self,
        worker_id: str,
        action: LifecycleAction,
    ) -> LifecyclePlan:
        try:
            context = self._context_provider.observe(worker_id, action)
        except Exception as exc:
            raise LifecycleCoordinatorError("LIFECYCLE_CONTEXT_UNAVAILABLE") from exc
        if not isinstance(context, LifecycleContext) or context.action is not action:
            raise LifecycleCoordinatorError("LIFECYCLE_CONTEXT_INVALID")
        try:
            return self._planner(context)
        except Exception as exc:
            raise LifecycleCoordinatorError("LIFECYCLE_PLAN_FAILED") from exc

    def execute(
        self,
        worker_id: str,
        action: LifecycleAction,
    ) -> LifecycleExecutionResult:
        if not isinstance(worker_id, str) or not worker_id.strip():
            raise LifecycleCoordinatorError("WORKER_ID_INVALID")
        if not isinstance(action, LifecycleAction):
            raise LifecycleCoordinatorError("LIFECYCLE_ACTION_INVALID")

        transaction_id = self._transaction_id()
        plan = self._observe_and_plan(worker_id, action)

        if plan.decision is not LifecycleDecision.PROCEED:
            result = self._executor.execute(
                plan,
                _NonProceedBackend(),
                self._checkpoint_sink,
                transaction_id=transaction_id,
            )
            if result.state is LifecycleExecutionState.REFUSED:
                return result
            if result.state is LifecycleExecutionState.NOOP:
                self._persist_state(
                    worker_id,
                    _successful_state(action),
                    recovery_required=False,
                )
                return result
            if result.state is LifecycleExecutionState.RECOVERY_REQUIRED:
                self._persist_state(
                    worker_id,
                    WorkerState.ERROR,
                    recovery_required=True,
                )
                return result
            return result

        pre_state = _pre_execution_state(action)
        if pre_state is not None:
            self._persist_state(
                worker_id,
                pre_state,
                recovery_required=False,
            )

        try:
            backend = self._backend_factory.create(worker_id, action)
        except Exception as exc:
            try:
                self._persist_state(
                    worker_id,
                    WorkerState.ERROR,
                    recovery_required=False,
                )
            except LifecycleCoordinatorError:
                pass
            raise LifecycleCoordinatorError("LIFECYCLE_BACKEND_UNAVAILABLE") from exc

        result = self._executor.execute(
            plan,
            backend,
            self._checkpoint_sink,
            transaction_id=transaction_id,
        )

        if result.state in {
            LifecycleExecutionState.COMPLETE,
            LifecycleExecutionState.NOOP,
        }:
            final_state = _successful_state(action)
        elif result.state in {
            LifecycleExecutionState.FAILED,
            LifecycleExecutionState.RECOVERY_REQUIRED,
        }:
            final_state = WorkerState.ERROR
        else:
            return result

        self._persist_state(
            worker_id,
            final_state,
            recovery_required=True,
        )
        return result
