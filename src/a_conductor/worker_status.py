"""Pure normalization of A-Worker runtime observations into UI-safe state.

The evaluator performs no I/O and no recovery actions. It only applies the
precedence rules defined by the runtime-manager contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from .domain import HealthState, WorkerState
from .runtime_safety import (
    PortBindingState,
    ProcessOwnership,
    TunnelBindingState,
)


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


@dataclass(frozen=True, slots=True)
class WorkerStatusObservation:
    worker_id: str
    assigned_project_id: str | None
    project_exists: bool | None
    process_ownership: ProcessOwnership
    pid: int | None
    port_binding: PortBindingState
    tunnel_required: bool
    tunnel_binding: TunnelBindingState
    ready: bool | None
    project_identity_ok: bool | None
    operation_state: WorkerState

    def __post_init__(self) -> None:
        _require_text(self.worker_id, "worker_id")
        if self.assigned_project_id is not None:
            _require_text(self.assigned_project_id, "assigned_project_id")
        if self.pid is not None and (
            not isinstance(self.pid, int)
            or isinstance(self.pid, bool)
            or self.pid < 1
        ):
            raise ValueError("pid must be >= 1")


@dataclass(frozen=True, slots=True)
class WorkerStatus:
    worker_id: str
    project_id: str | None
    pid: int | None
    state: HealthState
    reason_code: str
    warnings: tuple[str, ...] = ()


def _status(
    observation: WorkerStatusObservation,
    state: HealthState,
    reason_code: str,
    *,
    warnings: tuple[str, ...] = (),
) -> WorkerStatus:
    return WorkerStatus(
        worker_id=observation.worker_id,
        project_id=observation.assigned_project_id,
        pid=observation.pid,
        state=state,
        reason_code=reason_code,
        warnings=warnings,
    )


def evaluate_worker_status(observation: WorkerStatusObservation) -> WorkerStatus:
    """Evaluate observed worker state without changing the machine.

    Precedence intentionally favors identity/collision failures over desired
    lifecycle state. Unknown observations never become READY.
    """

    if (
        observation.assigned_project_id is not None
        and observation.project_exists is False
    ):
        return _status(
            observation,
            HealthState.PROJECT_NOT_FOUND,
            "PROJECT_NOT_FOUND",
        )

    if observation.process_ownership is ProcessOwnership.MISMATCH:
        return _status(observation, HealthState.PID_MISMATCH, "PID_MISMATCH")

    if (
        observation.tunnel_required
        and observation.tunnel_binding is TunnelBindingState.COLLISION
    ):
        return _status(
            observation,
            HealthState.TUNNEL_COLLISION,
            "TUNNEL_COLLISION",
        )

    if observation.port_binding is PortBindingState.COLLISION:
        return _status(observation, HealthState.PORT_IN_USE, "PORT_IN_USE")

    if observation.process_ownership is ProcessOwnership.UNKNOWN:
        return _status(
            observation,
            HealthState.UNKNOWN,
            "PROCESS_OWNERSHIP_UNKNOWN",
        )

    if observation.process_ownership in {
        ProcessOwnership.ABSENT,
        ProcessOwnership.STALE,
    }:
        if observation.operation_state is WorkerState.STARTING:
            warnings = (
                ("STALE_PID_METADATA",)
                if observation.process_ownership is ProcessOwnership.STALE
                else ()
            )
            return _status(
                observation,
                HealthState.STARTING,
                "STARTING",
                warnings=warnings,
            )
        if observation.process_ownership is ProcessOwnership.STALE:
            return _status(
                observation,
                HealthState.STOPPED,
                "STALE_PID_METADATA",
                warnings=("STALE_PID_METADATA",),
            )
        return _status(
            observation,
            HealthState.STOPPED,
            "PROCESS_ABSENT",
        )

    if observation.operation_state is WorkerState.STOPPING:
        return _status(observation, HealthState.STOPPING, "STOPPING")

    if observation.assigned_project_id is None:
        return _status(
            observation,
            HealthState.UNKNOWN,
            "ASSIGNMENT_MISSING",
        )

    if observation.project_exists is None:
        return _status(
            observation,
            HealthState.UNKNOWN,
            "PROJECT_EXISTENCE_UNKNOWN",
        )

    if observation.operation_state is WorkerState.STARTING and observation.ready is not True:
        return _status(observation, HealthState.STARTING, "STARTING")

    if observation.port_binding is PortBindingState.UNKNOWN:
        return _status(
            observation,
            HealthState.UNKNOWN,
            "HEALTH_PORT_UNKNOWN",
        )

    if observation.port_binding is PortBindingState.FREE:
        return _status(
            observation,
            HealthState.UNHEALTHY,
            "HEALTH_PORT_NOT_LISTENING",
        )

    if observation.tunnel_required:
        if observation.tunnel_binding is not TunnelBindingState.OWNED:
            return _status(
                observation,
                HealthState.UNHEALTHY,
                "TUNNEL_NOT_OWNED",
            )

    if observation.ready is None:
        return _status(
            observation,
            HealthState.UNKNOWN,
            "READINESS_UNKNOWN",
        )

    if observation.ready is False:
        return _status(
            observation,
            HealthState.UNHEALTHY,
            "READINESS_FAILED",
        )

    if observation.project_identity_ok is False:
        return _status(
            observation,
            HealthState.PROJECT_IDENTITY_FAILED,
            "PROJECT_IDENTITY_FAILED",
        )

    if observation.project_identity_ok is None:
        return _status(
            observation,
            HealthState.UNKNOWN,
            "PROJECT_IDENTITY_UNKNOWN",
        )

    if observation.operation_state is WorkerState.BUSY:
        return _status(observation, HealthState.BUSY, "BUSY")

    return _status(observation, HealthState.READY, "READY")
