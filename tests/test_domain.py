from dataclasses import FrozenInstanceError

import pytest

from a_conductor.domain import (
    Agent,
    Assignment,
    Capability,
    Execution,
    ExecutionSurfaceTraits,
    HealthState,
    Project,
    Provider,
    RecoveryClassification,
    ReviewOutcome,
    ReviewResult,
    RiskClass,
    Runtime,
    TaskState,
    Worker,
    WorkerState,
)


def test_worker_is_runtime_neutral_and_can_be_unassigned() -> None:
    worker = Worker(worker_id="a-worker-01", display_name="A-Worker 1")

    assert worker.state is WorkerState.STOPPED
    assert worker.runtime_id is None
    assert worker.assignment_id is None
    assert not hasattr(worker, "project_id")


def test_project_and_runtime_are_separate_from_worker_assignment() -> None:
    project = Project(
        project_id="project-a",
        display_name="Project A",
        root_path="C:/projects/project-a",
    )
    runtime = Runtime(runtime_id="runtime-01", runtime_type="semantic-code")
    assignment = Assignment(
        assignment_id="assign-01",
        worker_id="a-worker-01",
        project_id=project.project_id,
        runtime_id=runtime.runtime_id,
    )

    assert assignment.worker_id == "a-worker-01"
    assert assignment.project_id == "project-a"
    assert assignment.runtime_id == "runtime-01"


@pytest.mark.parametrize(
    ("factory", "kwargs"),
    [
        (Project, {"project_id": "   ", "display_name": "Project", "root_path": "C:/repo"}),
        (Worker, {"worker_id": "", "display_name": "Worker"}),
        (Runtime, {"runtime_id": "\t", "runtime_type": "semantic-code"}),
        (Provider, {"provider_id": " ", "provider_type": "local"}),
        (Agent, {"agent_id": "", "provider_id": None, "model_id": None}),
        (
            Assignment,
            {
                "assignment_id": " ",
                "worker_id": "a-worker-01",
                "project_id": "project-a",
                "runtime_id": None,
            },
        ),
        (
            Execution,
            {
                "execution_id": "",
                "task_id": "TASK-001",
                "attempt_no": 1,
                "worker_id": "a-worker-01",
                "runtime_id": None,
            },
        ),
    ],
)
def test_identity_objects_reject_blank_identifiers(factory, kwargs) -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        factory(**kwargs)


def test_execution_attempt_number_must_be_positive() -> None:
    with pytest.raises(ValueError, match="attempt_no must be >= 1"):
        Execution(
            execution_id="exec-01",
            task_id="TASK-001",
            attempt_no=0,
            worker_id="a-worker-01",
            runtime_id=None,
        )


def test_task_state_contains_recovery_and_review_states() -> None:
    assert {state.value for state in TaskState} == {
        "NEW",
        "PLANNING",
        "READY",
        "CLAIMED",
        "GATING",
        "EXECUTING",
        "VERIFYING",
        "REPAIRING",
        "REVIEW_PENDING",
        "CHANGES_REQUIRED",
        "BLOCKED",
        "RECOVERY_NEEDED",
        "COMPLETE",
        "FAILED",
        "CANCELLED",
    }


def test_recovery_classifications_match_core_contract() -> None:
    assert {state.value for state in RecoveryClassification} == {
        "NO_MUTATION",
        "PARTIAL_MUTATION",
        "MUTATION_COMPLETE_UNVERIFIED",
        "COMPLETE_VERIFIED",
        "UNEXPECTED_DRIFT",
        "UNKNOWN",
    }


def test_health_states_include_validated_worker_failure_modes() -> None:
    values = {state.value for state in HealthState}

    assert {
        "READY",
        "STARTING",
        "STOPPED",
        "BUSY",
        "PORT_IN_USE",
        "TUNNEL_COLLISION",
        "PID_MISMATCH",
        "PROJECT_NOT_FOUND",
        "PROJECT_IDENTITY_FAILED",
        "UNHEALTHY",
        "UNKNOWN",
    }.issubset(values)


def test_capabilities_are_generic_not_provider_specific() -> None:
    capability = Capability(name="semantic_navigation")
    runtime = Runtime(
        runtime_id="runtime-01",
        runtime_type="semantic-code",
        capabilities=(capability,),
    )
    provider = Provider(provider_id="provider-local", provider_type="local")
    agent = Agent(
        agent_id="agent-01",
        provider_id=provider.provider_id,
        model_id=None,
        capabilities=(capability,),
    )

    assert runtime.capabilities == (capability,)
    assert agent.capabilities == (capability,)
    assert capability.name == "semantic_navigation"


def test_execution_surface_traits_capture_durability_metadata() -> None:
    traits = ExecutionSurfaceTraits(
        supports_long_running=True,
        supports_resume=True,
        supports_background_execution=False,
        supports_repo_tools=True,
        requires_human_presence=False,
        max_safe_transaction_scope="one work order",
    )

    assert traits.supports_long_running is True
    assert traits.supports_resume is True
    assert traits.max_safe_transaction_scope == "one work order"


def test_review_result_is_structured_and_immutable() -> None:
    result = ReviewResult(
        outcome=ReviewOutcome.CHANGES_REQUIRED,
        summary="Add missing recovery evidence.",
        evidence_refs=("EVID-001",),
    )

    assert result.outcome is ReviewOutcome.CHANGES_REQUIRED
    assert result.evidence_refs == ("EVID-001",)
    with pytest.raises(FrozenInstanceError):
        result.summary = "mutated"  # type: ignore[misc]


def test_core_enums_are_provider_neutral() -> None:
    assert {risk.value for risk in RiskClass} == {
        "LOW",
        "NORMAL",
        "HIGH",
        "HUMAN_REQUIRED",
    }
    assert {outcome.value for outcome in ReviewOutcome} == {
        "PASS",
        "CHANGES_REQUIRED",
        "BLOCKED",
        "ESCALATE",
    }
