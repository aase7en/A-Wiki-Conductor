"""Pure lifecycle decision policy for A-Conductor worker runtimes.

This module returns symbolic plans only. It never starts, stops, cleans up, or
renders anything on the host machine.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .domain import WorkerState
from .runtime_safety import (
    PortBindingState,
    ProcessOwnership,
    TunnelBindingState,
    WorktreeBindingState,
)


class LifecycleAction(str, Enum):
    START = "START"
    STOP = "STOP"
    RESTART = "RESTART"
    RELEASE = "RELEASE"


class LifecycleDecision(str, Enum):
    PROCEED = "PROCEED"
    NOOP = "NOOP"
    REFUSE = "REFUSE"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


class LifecycleStep(str, Enum):
    VERIFY_ASSIGNMENT = "VERIFY_ASSIGNMENT"
    VERIFY_RESOURCES = "VERIFY_RESOURCES"
    RENDER_PROFILE = "RENDER_PROFILE"
    PREFLIGHT = "PREFLIGHT"
    START_OWNED_PROCESS = "START_OWNED_PROCESS"
    WAIT_READY = "WAIT_READY"
    VERIFY_PROJECT_IDENTITY = "VERIFY_PROJECT_IDENTITY"
    TARGETED_STOP = "TARGETED_STOP"
    WAIT_EXIT = "WAIT_EXIT"
    VERIFY_RELEASED = "VERIFY_RELEASED"
    CLEAR_ASSIGNMENT = "CLEAR_ASSIGNMENT"
    EMIT_EVIDENCE = "EMIT_EVIDENCE"


@dataclass(frozen=True, slots=True)
class LifecycleContext:
    action: LifecycleAction
    assignment_present: bool
    project_exists: bool | None
    process_ownership: ProcessOwnership
    port_binding: PortBindingState
    tunnel_required: bool
    tunnel_binding: TunnelBindingState
    worktree_binding: WorktreeBindingState
    ready: bool | None
    project_identity_ok: bool | None
    worker_state: WorkerState
    active_task: bool


@dataclass(frozen=True, slots=True)
class LifecyclePlan:
    action: LifecycleAction
    decision: LifecycleDecision
    reason_code: str
    steps: tuple[LifecycleStep, ...] = ()


def _plan(
    context: LifecycleContext,
    decision: LifecycleDecision,
    reason_code: str,
    *steps: LifecycleStep,
) -> LifecyclePlan:
    return LifecyclePlan(
        action=context.action,
        decision=decision,
        reason_code=reason_code,
        steps=tuple(steps),
    )


def _assignment_guard(context: LifecycleContext) -> LifecyclePlan | None:
    if not context.assignment_present:
        return _plan(context, LifecycleDecision.REFUSE, "ASSIGNMENT_MISSING")
    if context.project_exists is False:
        return _plan(context, LifecycleDecision.REFUSE, "PROJECT_NOT_FOUND")
    if context.project_exists is None:
        return _plan(
            context,
            LifecycleDecision.REFUSE,
            "PROJECT_EXISTENCE_UNKNOWN",
        )
    if context.worktree_binding is WorktreeBindingState.CONFLICT:
        return _plan(context, LifecycleDecision.REFUSE, "WORKTREE_CONFLICT")
    return None


def _ownership_uncertainty(context: LifecycleContext) -> LifecyclePlan | None:
    if context.process_ownership is ProcessOwnership.MISMATCH:
        return _plan(context, LifecycleDecision.REFUSE, "PID_MISMATCH")
    if context.process_ownership is ProcessOwnership.UNKNOWN:
        return _plan(
            context,
            LifecycleDecision.REFUSE,
            "PROCESS_OWNERSHIP_UNKNOWN",
        )
    if context.process_ownership is ProcessOwnership.STALE:
        return _plan(
            context,
            LifecycleDecision.RECOVERY_REQUIRED,
            "STALE_PID_METADATA",
        )
    return None


def _start_resource_guard(context: LifecycleContext) -> LifecyclePlan | None:
    if (
        context.tunnel_required
        and context.tunnel_binding is TunnelBindingState.COLLISION
    ):
        return _plan(context, LifecycleDecision.REFUSE, "TUNNEL_COLLISION")
    if context.port_binding is PortBindingState.COLLISION:
        return _plan(context, LifecycleDecision.REFUSE, "PORT_IN_USE")
    if context.port_binding is PortBindingState.UNKNOWN:
        return _plan(
            context,
            LifecycleDecision.RECOVERY_REQUIRED,
            "PORT_STATE_UNKNOWN",
        )
    if context.port_binding is PortBindingState.OWNED:
        return _plan(
            context,
            LifecycleDecision.RECOVERY_REQUIRED,
            "PORT_STILL_OWNED",
        )
    if (
        context.tunnel_required
        and context.tunnel_binding is TunnelBindingState.OWNED
    ):
        return _plan(
            context,
            LifecycleDecision.RECOVERY_REQUIRED,
            "TUNNEL_STILL_OWNED",
        )
    return None


def _start_steps() -> tuple[LifecycleStep, ...]:
    return (
        LifecycleStep.VERIFY_ASSIGNMENT,
        LifecycleStep.VERIFY_RESOURCES,
        LifecycleStep.RENDER_PROFILE,
        LifecycleStep.PREFLIGHT,
        LifecycleStep.START_OWNED_PROCESS,
        LifecycleStep.WAIT_READY,
        LifecycleStep.VERIFY_PROJECT_IDENTITY,
        LifecycleStep.EMIT_EVIDENCE,
    )


def _plan_start(context: LifecycleContext) -> LifecyclePlan:
    guard = _assignment_guard(context)
    if guard is not None:
        return guard

    ownership = _ownership_uncertainty(context)
    if ownership is not None:
        return ownership

    if context.process_ownership is ProcessOwnership.OWNED:
        if (
            context.tunnel_required
            and context.tunnel_binding is TunnelBindingState.COLLISION
        ):
            return _plan(context, LifecycleDecision.REFUSE, "TUNNEL_COLLISION")
        if context.port_binding is PortBindingState.COLLISION:
            return _plan(context, LifecycleDecision.REFUSE, "PORT_IN_USE")
        tunnel_ok = (
            not context.tunnel_required
            or context.tunnel_binding is TunnelBindingState.OWNED
        )
        if (
            context.port_binding is PortBindingState.OWNED
            and tunnel_ok
            and context.ready is True
            and context.project_identity_ok is True
        ):
            return _plan(
                context,
                LifecycleDecision.NOOP,
                "ALREADY_RUNNING",
                LifecycleStep.EMIT_EVIDENCE,
            )
        return _plan(
            context,
            LifecycleDecision.RECOVERY_REQUIRED,
            "OWNED_RUNTIME_NOT_READY",
            LifecycleStep.EMIT_EVIDENCE,
        )

    resource_guard = _start_resource_guard(context)
    if resource_guard is not None:
        return resource_guard
    return _plan(
        context,
        LifecycleDecision.PROCEED,
        "START_ALLOWED",
        *_start_steps(),
    )


def _plan_stop(context: LifecycleContext) -> LifecyclePlan:
    ownership = _ownership_uncertainty(context)
    if ownership is not None:
        return ownership
    if context.process_ownership is ProcessOwnership.ABSENT:
        return _plan(
            context,
            LifecycleDecision.NOOP,
            "NOT_RUNNING",
            LifecycleStep.EMIT_EVIDENCE,
        )
    return _plan(
        context,
        LifecycleDecision.PROCEED,
        "STOP_ALLOWED",
        LifecycleStep.TARGETED_STOP,
        LifecycleStep.WAIT_EXIT,
        LifecycleStep.VERIFY_RELEASED,
        LifecycleStep.EMIT_EVIDENCE,
    )


def _plan_restart(context: LifecycleContext) -> LifecyclePlan:
    guard = _assignment_guard(context)
    if guard is not None:
        return guard

    ownership = _ownership_uncertainty(context)
    if ownership is not None:
        return ownership

    if context.tunnel_required and context.tunnel_binding is TunnelBindingState.COLLISION:
        return _plan(context, LifecycleDecision.REFUSE, "TUNNEL_COLLISION")
    if context.port_binding is PortBindingState.COLLISION:
        return _plan(context, LifecycleDecision.REFUSE, "PORT_IN_USE")

    if context.process_ownership is ProcessOwnership.ABSENT:
        resource_guard = _start_resource_guard(context)
        if resource_guard is not None:
            return resource_guard
        return _plan(
            context,
            LifecycleDecision.PROCEED,
            "RESTART_AS_START_ALLOWED",
            *_start_steps(),
        )

    return _plan(
        context,
        LifecycleDecision.PROCEED,
        "RESTART_ALLOWED",
        LifecycleStep.TARGETED_STOP,
        LifecycleStep.WAIT_EXIT,
        LifecycleStep.VERIFY_RELEASED,
        LifecycleStep.VERIFY_RESOURCES,
        LifecycleStep.RENDER_PROFILE,
        LifecycleStep.PREFLIGHT,
        LifecycleStep.START_OWNED_PROCESS,
        LifecycleStep.WAIT_READY,
        LifecycleStep.VERIFY_PROJECT_IDENTITY,
        LifecycleStep.EMIT_EVIDENCE,
    )


def _plan_release(context: LifecycleContext) -> LifecyclePlan:
    if context.active_task:
        return _plan(context, LifecycleDecision.REFUSE, "ACTIVE_TASK")

    ownership = _ownership_uncertainty(context)
    if ownership is not None:
        return ownership
    if context.process_ownership is ProcessOwnership.OWNED:
        return _plan(context, LifecycleDecision.REFUSE, "WORKER_NOT_STOPPED")
    if context.worker_state is not WorkerState.STOPPED:
        return _plan(context, LifecycleDecision.REFUSE, "WORKER_NOT_STOPPED")

    resources_released = context.port_binding is PortBindingState.FREE and (
        not context.tunnel_required
        or context.tunnel_binding is TunnelBindingState.FREE
    )
    if not resources_released:
        return _plan(
            context,
            LifecycleDecision.RECOVERY_REQUIRED,
            "RESOURCES_NOT_RELEASED",
        )

    if not context.assignment_present:
        return _plan(
            context,
            LifecycleDecision.NOOP,
            "ALREADY_FREE",
            LifecycleStep.EMIT_EVIDENCE,
        )

    return _plan(
        context,
        LifecycleDecision.PROCEED,
        "RELEASE_ALLOWED",
        LifecycleStep.CLEAR_ASSIGNMENT,
        LifecycleStep.EMIT_EVIDENCE,
    )


def plan_lifecycle(context: LifecycleContext) -> LifecyclePlan:
    if context.action is LifecycleAction.START:
        return _plan_start(context)
    if context.action is LifecycleAction.STOP:
        return _plan_stop(context)
    if context.action is LifecycleAction.RESTART:
        return _plan_restart(context)
    if context.action is LifecycleAction.RELEASE:
        return _plan_release(context)
    raise ValueError(f"unsupported lifecycle action: {context.action!r}")
