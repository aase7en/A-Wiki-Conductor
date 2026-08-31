from __future__ import annotations

from dataclasses import dataclass

from a_conductor.control_center import ControlCenterSnapshot, WorkerScreenRow
from a_conductor.domain import WorkerState
from a_conductor.lifecycle import LifecycleAction, LifecycleContext
from a_conductor.runtime_safety import (
    PortBindingState,
    ProcessOwnership,
    TunnelBindingState,
    WorktreeBindingState,
)
from a_conductor.serena_runtime import ProjectIdentityPolicy, SerenaProjectBinding
from a_conductor.worker_candidate_assembly import (
    GitWorktreeState,
    WorkerCandidateAssembler,
)
from a_conductor.worker_lease import LeaseMutationIntent, WorkerLease


HEAD = "a" * 40


@dataclass
class FakeControlCenter:
    value: ControlCenterSnapshot

    def snapshot(self) -> ControlCenterSnapshot:
        return self.value


class FakeConfigStore:
    def __init__(self, binding: SerenaProjectBinding | None) -> None:
        self.binding = binding

    def get_project_binding(self, project_id: str):
        if self.binding is not None and self.binding.project_id == project_id:
            return self.binding
        return None


class FakeContextProvider:
    def __init__(self, context: LifecycleContext | Exception) -> None:
        self.context = context

    def observe(self, worker_id: str, action: LifecycleAction) -> LifecycleContext:
        assert action is LifecycleAction.START
        if isinstance(self.context, Exception):
            raise self.context
        return self.context


class FakeGitStateObserver:
    def __init__(self, state: GitWorktreeState | Exception) -> None:
        self.state = state

    def observe(self, worktree: str) -> GitWorktreeState:
        if isinstance(self.state, Exception):
            raise self.state
        return self.state


class FakeLeaseStore:
    def __init__(self, leases: tuple[WorkerLease, ...] = ()) -> None:
        self.leases = leases

    def list_active(self) -> tuple[WorkerLease, ...]:
        return self.leases


class FakeCapabilityResolver:
    def resolve(self, runtime_id: str | None) -> tuple[str, ...]:
        return ("shell", "repo") if runtime_id == "runtime-1" else ()


def row(*, state: WorkerState = WorkerState.READY, mutation_allowed: bool = True):
    return WorkerScreenRow(
        worker_id="a-worker-01",
        display_name="A-Worker 1",
        state=state,
        runtime_id="runtime-1",
        assignment_id="assignment-1",
        project_id="project-1",
        project_display_name="Repo",
        project_root_path=r"A:\Repo",
        mutation_allowed=mutation_allowed,
    )


def snapshot(worker_row=None) -> ControlCenterSnapshot:
    return ControlCenterSnapshot(projects=(), workers=(worker_row or row(),), online=True)


def binding(*, worktree: str = r"A:\Repo") -> SerenaProjectBinding:
    return SerenaProjectBinding(
        project_id="project-1",
        worktree_path=worktree,
        identity_policy=ProjectIdentityPolicy.EXACT,
        expected_branch="feat/test",
        expected_head=HEAD,
        mutation_allowed=True,
    )


def context(
    *,
    ready: bool | None = True,
    ownership: ProcessOwnership = ProcessOwnership.OWNED,
    identity_ok: bool | None = True,
) -> LifecycleContext:
    return LifecycleContext(
        action=LifecycleAction.START,
        assignment_present=True,
        project_exists=True,
        process_ownership=ownership,
        port_binding=PortBindingState.OWNED,
        tunnel_required=False,
        tunnel_binding=TunnelBindingState.FREE,
        worktree_binding=WorktreeBindingState.OWNED,
        ready=ready,
        project_identity_ok=identity_ok,
        worker_state=WorkerState.READY,
        active_task=False,
    )


def lease(*, mutable_scope=("src/**",)) -> WorkerLease:
    return WorkerLease(
        lease_id="lease-1",
        worker_id="a-worker-01",
        session_id="session-1",
        task_id="task-1",
        project_id="project-1",
        runtime_id="runtime-1",
        worktree_key="a:\\repo",
        branch="feat/test",
        expected_head=HEAD,
        required_capabilities=("shell",),
        allowed_scope=("src/**",),
        forbidden_scope=("secrets/**",),
        mutable_scope=tuple(mutable_scope),
        mutation_intent=LeaseMutationIntent.MUTATION,
        acquired_at="2026-08-31T00:00:00Z",
        heartbeat_at="2026-08-31T00:00:00Z",
        lease_ttl_seconds=600,
        expires_at="2026-08-31T00:10:00Z",
    )


def assembler(
    *,
    worker_row=None,
    project_binding=None,
    lifecycle=None,
    git_state=None,
    leases=(),
):
    return WorkerCandidateAssembler(
        control_center=FakeControlCenter(snapshot(worker_row)),
        config_store=FakeConfigStore(project_binding or binding()),
        lifecycle_context_provider=FakeContextProvider(lifecycle or context()),
        git_state_observer=FakeGitStateObserver(
            git_state or GitWorktreeState("feat/test", HEAD, "CLEAN")
        ),
        lease_store=FakeLeaseStore(tuple(leases)),
        capability_resolver=FakeCapabilityResolver(),
    )


def test_ready_clean_worker_uses_live_git_and_becomes_scheduler_and_lease_candidate() -> None:
    record = assembler().assemble("a-worker-01")

    assert record.reason_code == "READY"
    assert record.scheduler.state == "READY"
    assert record.scheduler.workspace == r"A:\Repo"
    assert record.scheduler.capabilities == ("shell", "repo")
    assert record.scheduler.mutation_authorized is True
    assert record.candidate.branch == "feat/test"
    assert record.candidate.head == HEAD
    assert record.candidate.dirty_state == "CLEAN"
    assert record.candidate.health_fresh is True
    assert record.candidate.ownership_known is True


def test_dirty_worktree_uses_live_dirty_evidence_and_disables_mutation_authority() -> None:
    record = assembler(
        git_state=GitWorktreeState("feat/test", HEAD, "DIRTY")
    ).assemble("a-worker-01")

    assert record.reason_code == "READY_DIRTY"
    assert record.scheduler.state == "READY"
    assert record.scheduler.mutation_authorized is False
    assert record.candidate.dirty_state == "DIRTY"
    assert record.candidate.mutation_authorized is True


def test_actual_git_identity_is_not_replaced_by_persisted_expected_identity() -> None:
    actual_head = "b" * 40
    record = assembler(
        git_state=GitWorktreeState("feat/drift", actual_head, "CLEAN")
    ).assemble("a-worker-01")

    assert record.candidate.branch == "feat/drift"
    assert record.candidate.head == actual_head
    assert record.scheduler.workspace == r"A:\Repo"


def test_active_worker_lease_marks_reserved_active_and_occupied_scope() -> None:
    record = assembler(leases=(lease(),)).assemble("a-worker-01")

    assert record.scheduler.reserved is True
    assert record.candidate.reserved is True
    assert record.candidate.active_task is True
    assert record.candidate.occupied_mutable_scopes == (("src/**",),)


def test_binding_root_drift_fails_closed_without_using_project_row_as_truth() -> None:
    record = assembler(project_binding=binding(worktree=r"A:\Other")).assemble(
        "a-worker-01"
    )

    assert record.reason_code == "PROJECT_BINDING_DRIFT"
    assert record.scheduler.state == "UNKNOWN"
    assert record.scheduler.mutation_authorized is False
    assert record.candidate.health_fresh is False
    assert record.candidate.dirty_state == "UNKNOWN"


def test_unknown_runtime_or_git_observation_fails_closed_per_worker() -> None:
    unknown = assembler(
        lifecycle=context(ready=None, ownership=ProcessOwnership.UNKNOWN, identity_ok=None)
    ).assemble("a-worker-01")
    assert unknown.scheduler.state == "UNKNOWN"
    assert unknown.candidate.health_fresh is False
    assert unknown.candidate.ownership_known is False

    failed_git = assembler(git_state=RuntimeError("boom")).assemble("a-worker-01")
    assert failed_git.reason_code == "GIT_OBSERVATION_FAILED"
    assert failed_git.scheduler.state == "UNKNOWN"
    assert failed_git.candidate.head is None


def test_assemble_all_is_failure_isolated_and_keeps_one_record_per_worker() -> None:
    broken = WorkerScreenRow(
        worker_id="a-worker-02",
        display_name="A-Worker 2",
        state=WorkerState.READY,
        runtime_id=None,
        assignment_id=None,
        project_id=None,
        project_display_name=None,
        project_root_path=None,
        mutation_allowed=None,
    )
    center = FakeControlCenter(
        ControlCenterSnapshot(projects=(), workers=(row(), broken), online=True)
    )
    service = WorkerCandidateAssembler(
        control_center=center,
        config_store=FakeConfigStore(binding()),
        lifecycle_context_provider=FakeContextProvider(context()),
        git_state_observer=FakeGitStateObserver(GitWorktreeState("feat/test", HEAD, "CLEAN")),
        lease_store=FakeLeaseStore(),
        capability_resolver=FakeCapabilityResolver(),
    )

    records = service.assemble_all()
    assert [item.worker_id for item in records] == ["a-worker-01", "a-worker-02"]
    assert records[0].reason_code == "READY"
    assert records[1].reason_code == "ASSIGNMENT_MISSING"
    assert records[1].scheduler.state == "UNKNOWN"
