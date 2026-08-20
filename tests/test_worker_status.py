import pytest

from a_conductor.domain import HealthState, WorkerState
from a_conductor.runtime_safety import (
    PortBindingState,
    ProcessOwnership,
    TunnelBindingState,
)
from a_conductor.worker_status import (
    WorkerStatusObservation,
    evaluate_worker_status,
)


def observation(**overrides) -> WorkerStatusObservation:
    values = {
        "worker_id": "a-worker-01",
        "assigned_project_id": "project-a",
        "project_exists": True,
        "process_ownership": ProcessOwnership.OWNED,
        "pid": 1234,
        "port_binding": PortBindingState.OWNED,
        "tunnel_required": True,
        "tunnel_binding": TunnelBindingState.OWNED,
        "ready": True,
        "project_identity_ok": True,
        "operation_state": WorkerState.READY,
    }
    values.update(overrides)
    return WorkerStatusObservation(**values)


def test_ready_requires_all_observed_readiness_facts() -> None:
    status = evaluate_worker_status(observation())

    assert status.state is HealthState.READY
    assert status.reason_code == "READY"
    assert status.worker_id == "a-worker-01"
    assert status.project_id == "project-a"
    assert status.pid == 1234


def test_busy_is_ready_runtime_with_busy_operation_state() -> None:
    status = evaluate_worker_status(observation(operation_state=WorkerState.BUSY))

    assert status.state is HealthState.BUSY
    assert status.reason_code == "BUSY"


def test_missing_assigned_project_has_highest_identity_precedence() -> None:
    status = evaluate_worker_status(
        observation(
            project_exists=False,
            process_ownership=ProcessOwnership.MISMATCH,
            tunnel_binding=TunnelBindingState.COLLISION,
            port_binding=PortBindingState.COLLISION,
        )
    )

    assert status.state is HealthState.PROJECT_NOT_FOUND
    assert status.reason_code == "PROJECT_NOT_FOUND"


def test_pid_mismatch_precedes_resource_collisions() -> None:
    status = evaluate_worker_status(
        observation(
            process_ownership=ProcessOwnership.MISMATCH,
            tunnel_binding=TunnelBindingState.COLLISION,
            port_binding=PortBindingState.COLLISION,
        )
    )

    assert status.state is HealthState.PID_MISMATCH


def test_tunnel_collision_precedes_port_collision() -> None:
    status = evaluate_worker_status(
        observation(
            tunnel_binding=TunnelBindingState.COLLISION,
            port_binding=PortBindingState.COLLISION,
        )
    )

    assert status.state is HealthState.TUNNEL_COLLISION


def test_port_collision_is_explicit() -> None:
    status = evaluate_worker_status(
        observation(port_binding=PortBindingState.COLLISION)
    )

    assert status.state is HealthState.PORT_IN_USE


def test_unknown_process_ownership_stays_unknown() -> None:
    status = evaluate_worker_status(
        observation(process_ownership=ProcessOwnership.UNKNOWN)
    )

    assert status.state is HealthState.UNKNOWN
    assert status.reason_code == "PROCESS_OWNERSHIP_UNKNOWN"


def test_absent_process_is_stopped() -> None:
    status = evaluate_worker_status(
        observation(
            process_ownership=ProcessOwnership.ABSENT,
            pid=None,
            port_binding=PortBindingState.FREE,
            tunnel_binding=TunnelBindingState.FREE,
            ready=False,
            project_identity_ok=None,
            operation_state=WorkerState.STOPPED,
        )
    )

    assert status.state is HealthState.STOPPED
    assert status.reason_code == "PROCESS_ABSENT"


def test_stale_pid_metadata_is_stopped_without_cleanup_side_effect() -> None:
    status = evaluate_worker_status(
        observation(
            process_ownership=ProcessOwnership.STALE,
            pid=1234,
            port_binding=PortBindingState.FREE,
            tunnel_binding=TunnelBindingState.FREE,
            ready=False,
            project_identity_ok=None,
            operation_state=WorkerState.STOPPED,
        )
    )

    assert status.state is HealthState.STOPPED
    assert status.reason_code == "STALE_PID_METADATA"
    assert status.warnings == ("STALE_PID_METADATA",)


def test_starting_can_be_reported_before_process_is_ready() -> None:
    status = evaluate_worker_status(
        observation(
            process_ownership=ProcessOwnership.ABSENT,
            pid=None,
            port_binding=PortBindingState.FREE,
            tunnel_binding=TunnelBindingState.FREE,
            ready=False,
            project_identity_ok=None,
            operation_state=WorkerState.STARTING,
        )
    )

    assert status.state is HealthState.STARTING


def test_stopping_owned_process_is_stopping() -> None:
    status = evaluate_worker_status(
        observation(operation_state=WorkerState.STOPPING, ready=True)
    )

    assert status.state is HealthState.STOPPING


def test_owned_process_with_missing_health_listener_is_unhealthy() -> None:
    status = evaluate_worker_status(
        observation(port_binding=PortBindingState.FREE, ready=False)
    )

    assert status.state is HealthState.UNHEALTHY
    assert status.reason_code == "HEALTH_PORT_NOT_LISTENING"


def test_unknown_port_observation_stays_unknown() -> None:
    status = evaluate_worker_status(
        observation(port_binding=PortBindingState.UNKNOWN)
    )

    assert status.state is HealthState.UNKNOWN
    assert status.reason_code == "HEALTH_PORT_UNKNOWN"


def test_required_tunnel_must_be_owned_for_ready() -> None:
    status = evaluate_worker_status(
        observation(tunnel_binding=TunnelBindingState.FREE)
    )

    assert status.state is HealthState.UNHEALTHY
    assert status.reason_code == "TUNNEL_NOT_OWNED"


def test_tunnel_can_be_optional_for_non_tunneled_runtime() -> None:
    status = evaluate_worker_status(
        observation(tunnel_required=False, tunnel_binding=TunnelBindingState.FREE)
    )

    assert status.state is HealthState.READY


def test_explicit_not_ready_is_unhealthy() -> None:
    status = evaluate_worker_status(observation(ready=False))

    assert status.state is HealthState.UNHEALTHY
    assert status.reason_code == "READINESS_FAILED"


def test_unknown_readiness_stays_unknown() -> None:
    status = evaluate_worker_status(observation(ready=None))

    assert status.state is HealthState.UNKNOWN
    assert status.reason_code == "READINESS_UNKNOWN"


def test_project_identity_failure_is_explicit() -> None:
    status = evaluate_worker_status(observation(project_identity_ok=False))

    assert status.state is HealthState.PROJECT_IDENTITY_FAILED


def test_unknown_project_identity_prevents_ready() -> None:
    status = evaluate_worker_status(observation(project_identity_ok=None))

    assert status.state is HealthState.UNKNOWN
    assert status.reason_code == "PROJECT_IDENTITY_UNKNOWN"


def test_owned_process_without_assignment_is_unknown() -> None:
    status = evaluate_worker_status(
        observation(assigned_project_id=None, project_exists=None)
    )

    assert status.state is HealthState.UNKNOWN
    assert status.reason_code == "ASSIGNMENT_MISSING"


@pytest.mark.parametrize("worker_id", ["", " ", "\t"])
def test_blank_worker_id_is_rejected(worker_id: str) -> None:
    with pytest.raises(ValueError, match="worker_id must not be blank"):
        observation(worker_id=worker_id)


def test_non_positive_pid_is_rejected_when_present() -> None:
    with pytest.raises(ValueError, match="pid must be >= 1"):
        observation(pid=0)
