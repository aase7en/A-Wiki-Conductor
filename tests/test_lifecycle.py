import pytest

from a_conductor.domain import WorkerState
from a_conductor.lifecycle import (
    LifecycleAction,
    LifecycleContext,
    LifecycleDecision,
    LifecycleStep,
    plan_lifecycle,
)
from a_conductor.runtime_safety import (
    PortBindingState,
    ProcessOwnership,
    TunnelBindingState,
    WorktreeBindingState,
)


def context(action: LifecycleAction, **overrides) -> LifecycleContext:
    values = {
        "action": action,
        "assignment_present": True,
        "project_exists": True,
        "process_ownership": ProcessOwnership.ABSENT,
        "port_binding": PortBindingState.FREE,
        "tunnel_required": True,
        "tunnel_binding": TunnelBindingState.FREE,
        "worktree_binding": WorktreeBindingState.AVAILABLE,
        "ready": False,
        "project_identity_ok": None,
        "worker_state": WorkerState.STOPPED,
        "active_task": False,
    }
    values.update(overrides)
    return LifecycleContext(**values)


def test_start_proceeds_only_from_reconciled_free_resources() -> None:
    plan = plan_lifecycle(context(LifecycleAction.START))

    assert plan.decision is LifecycleDecision.PROCEED
    assert plan.reason_code == "START_ALLOWED"
    assert plan.steps == (
        LifecycleStep.VERIFY_ASSIGNMENT,
        LifecycleStep.VERIFY_RESOURCES,
        LifecycleStep.RENDER_PROFILE,
        LifecycleStep.PREFLIGHT,
        LifecycleStep.START_OWNED_PROCESS,
        LifecycleStep.WAIT_READY,
        LifecycleStep.VERIFY_PROJECT_IDENTITY,
        LifecycleStep.EMIT_EVIDENCE,
    )


def test_start_missing_assignment_or_project_is_refused() -> None:
    assert plan_lifecycle(
        context(LifecycleAction.START, assignment_present=False)
    ).reason_code == "ASSIGNMENT_MISSING"
    assert plan_lifecycle(
        context(LifecycleAction.START, project_exists=False)
    ).reason_code == "PROJECT_NOT_FOUND"
    assert plan_lifecycle(
        context(LifecycleAction.START, project_exists=None)
    ).reason_code == "PROJECT_EXISTENCE_UNKNOWN"


def test_start_refuses_worktree_tunnel_and_port_collisions() -> None:
    assert plan_lifecycle(
        context(LifecycleAction.START, worktree_binding=WorktreeBindingState.CONFLICT)
    ).reason_code == "WORKTREE_CONFLICT"
    assert plan_lifecycle(
        context(LifecycleAction.START, tunnel_binding=TunnelBindingState.COLLISION)
    ).reason_code == "TUNNEL_COLLISION"
    assert plan_lifecycle(
        context(LifecycleAction.START, port_binding=PortBindingState.COLLISION)
    ).reason_code == "PORT_IN_USE"


@pytest.mark.parametrize(
    ("ownership", "decision", "reason"),
    [
        (ProcessOwnership.MISMATCH, LifecycleDecision.REFUSE, "PID_MISMATCH"),
        (ProcessOwnership.UNKNOWN, LifecycleDecision.REFUSE, "PROCESS_OWNERSHIP_UNKNOWN"),
        (ProcessOwnership.STALE, LifecycleDecision.RECOVERY_REQUIRED, "STALE_PID_METADATA"),
    ],
)
def test_start_never_blindly_retries_uncertain_process_state(
    ownership: ProcessOwnership,
    decision: LifecycleDecision,
    reason: str,
) -> None:
    plan = plan_lifecycle(context(LifecycleAction.START, process_ownership=ownership))

    assert plan.decision is decision
    assert plan.reason_code == reason
    assert LifecycleStep.START_OWNED_PROCESS not in plan.steps


def test_start_owned_healthy_runtime_is_idempotent_noop() -> None:
    plan = plan_lifecycle(
        context(
            LifecycleAction.START,
            process_ownership=ProcessOwnership.OWNED,
            port_binding=PortBindingState.OWNED,
            tunnel_binding=TunnelBindingState.OWNED,
            ready=True,
            project_identity_ok=True,
            worker_state=WorkerState.READY,
        )
    )

    assert plan.decision is LifecycleDecision.NOOP
    assert plan.reason_code == "ALREADY_RUNNING"
    assert plan.steps == (LifecycleStep.EMIT_EVIDENCE,)


def test_start_owned_but_not_verified_requires_recovery_not_duplicate_spawn() -> None:
    plan = plan_lifecycle(
        context(
            LifecycleAction.START,
            process_ownership=ProcessOwnership.OWNED,
            port_binding=PortBindingState.OWNED,
            tunnel_binding=TunnelBindingState.OWNED,
            ready=False,
            project_identity_ok=None,
        )
    )

    assert plan.decision is LifecycleDecision.RECOVERY_REQUIRED
    assert plan.reason_code == "OWNED_RUNTIME_NOT_READY"
    assert LifecycleStep.START_OWNED_PROCESS not in plan.steps


def test_start_absent_process_with_leftover_owned_resource_requires_recovery() -> None:
    assert plan_lifecycle(
        context(LifecycleAction.START, port_binding=PortBindingState.OWNED)
    ).reason_code == "PORT_STILL_OWNED"
    assert plan_lifecycle(
        context(LifecycleAction.START, tunnel_binding=TunnelBindingState.OWNED)
    ).reason_code == "TUNNEL_STILL_OWNED"


def test_stop_absent_is_noop_stale_is_recovery_mismatch_is_refused() -> None:
    absent = plan_lifecycle(context(LifecycleAction.STOP))
    stale = plan_lifecycle(
        context(LifecycleAction.STOP, process_ownership=ProcessOwnership.STALE)
    )
    mismatch = plan_lifecycle(
        context(LifecycleAction.STOP, process_ownership=ProcessOwnership.MISMATCH)
    )

    assert (absent.decision, absent.reason_code) == (
        LifecycleDecision.NOOP,
        "NOT_RUNNING",
    )
    assert (stale.decision, stale.reason_code) == (
        LifecycleDecision.RECOVERY_REQUIRED,
        "STALE_PID_METADATA",
    )
    assert (mismatch.decision, mismatch.reason_code) == (
        LifecycleDecision.REFUSE,
        "PID_MISMATCH",
    )


def test_stop_owned_process_produces_targeted_symbolic_steps_only() -> None:
    plan = plan_lifecycle(
        context(LifecycleAction.STOP, process_ownership=ProcessOwnership.OWNED)
    )

    assert plan.decision is LifecycleDecision.PROCEED
    assert plan.steps == (
        LifecycleStep.TARGETED_STOP,
        LifecycleStep.WAIT_EXIT,
        LifecycleStep.VERIFY_RELEASED,
        LifecycleStep.EMIT_EVIDENCE,
    )


def test_restart_owned_process_requires_proven_ownership_and_valid_assignment() -> None:
    plan = plan_lifecycle(
        context(
            LifecycleAction.RESTART,
            process_ownership=ProcessOwnership.OWNED,
            port_binding=PortBindingState.OWNED,
            tunnel_binding=TunnelBindingState.OWNED,
            ready=False,
            project_identity_ok=False,
        )
    )

    assert plan.decision is LifecycleDecision.PROCEED
    assert plan.steps[0] is LifecycleStep.TARGETED_STOP
    assert LifecycleStep.VERIFY_RELEASED in plan.steps
    assert LifecycleStep.START_OWNED_PROCESS in plan.steps


def test_restart_unknown_ownership_is_refused() -> None:
    plan = plan_lifecycle(
        context(LifecycleAction.RESTART, process_ownership=ProcessOwnership.UNKNOWN)
    )

    assert plan.decision is LifecycleDecision.REFUSE
    assert LifecycleStep.TARGETED_STOP not in plan.steps
    assert LifecycleStep.START_OWNED_PROCESS not in plan.steps


def test_release_active_task_or_running_worker_is_refused() -> None:
    assert plan_lifecycle(
        context(LifecycleAction.RELEASE, active_task=True)
    ).reason_code == "ACTIVE_TASK"
    assert plan_lifecycle(
        context(
            LifecycleAction.RELEASE,
            process_ownership=ProcessOwnership.OWNED,
            worker_state=WorkerState.READY,
        )
    ).reason_code == "WORKER_NOT_STOPPED"


def test_release_stale_or_unreleased_resources_requires_recovery() -> None:
    stale = plan_lifecycle(
        context(LifecycleAction.RELEASE, process_ownership=ProcessOwnership.STALE)
    )
    port = plan_lifecycle(
        context(LifecycleAction.RELEASE, port_binding=PortBindingState.OWNED)
    )
    tunnel = plan_lifecycle(
        context(LifecycleAction.RELEASE, tunnel_binding=TunnelBindingState.OWNED)
    )

    assert stale.decision is LifecycleDecision.RECOVERY_REQUIRED
    assert port.reason_code == "RESOURCES_NOT_RELEASED"
    assert tunnel.reason_code == "RESOURCES_NOT_RELEASED"


def test_release_free_worker_is_noop() -> None:
    plan = plan_lifecycle(
        context(LifecycleAction.RELEASE, assignment_present=False)
    )

    assert plan.decision is LifecycleDecision.NOOP
    assert plan.reason_code == "ALREADY_FREE"


def test_release_stopped_reconciled_assignment_can_proceed() -> None:
    plan = plan_lifecycle(context(LifecycleAction.RELEASE))

    assert plan.decision is LifecycleDecision.PROCEED
    assert plan.steps == (
        LifecycleStep.CLEAR_ASSIGNMENT,
        LifecycleStep.EMIT_EVIDENCE,
    )


def test_lifecycle_plan_contains_symbolic_steps_not_commands() -> None:
    plan = plan_lifecycle(context(LifecycleAction.START))

    assert all(isinstance(step, LifecycleStep) for step in plan.steps)
    assert not any("powershell" in step.value.lower() for step in plan.steps)
