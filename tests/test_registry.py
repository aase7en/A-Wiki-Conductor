import pytest

from a_conductor.domain import Assignment, Project, Worker, WorkerState
from a_conductor.registry import (
    AssignmentConflictError,
    ControlPlaneRegistry,
    DuplicateRegistrationError,
    RegistryNotFoundError,
    WorkerBusyError,
    windows_worktree_key,
)


def project(project_id: str = "project-a", path: str = r"A:\GitHub\Project-A") -> Project:
    return Project(project_id=project_id, display_name=project_id, root_path=path)


def worker(worker_id: str = "a-worker-01", runtime_id: str = "runtime-01") -> Worker:
    return Worker(
        worker_id=worker_id,
        display_name=worker_id,
        runtime_id=runtime_id,
    )


def assignment(
    assignment_id: str,
    worker_id: str,
    project_id: str = "project-a",
    runtime_id: str = "runtime-01",
) -> Assignment:
    return Assignment(
        assignment_id=assignment_id,
        worker_id=worker_id,
        project_id=project_id,
        runtime_id=runtime_id,
    )


def test_project_registration_is_metadata_only_and_accepts_nonexistent_path() -> None:
    registry = ControlPlaneRegistry()
    candidate = project(path=r"Z:\This\Path\Does\Not\Need\To\Exist")

    registry.register_project(candidate)

    assert registry.get_project("project-a") == candidate


def test_duplicate_project_id_is_rejected_not_overwritten() -> None:
    registry = ControlPlaneRegistry()
    registry.register_project(project())

    with pytest.raises(DuplicateRegistrationError, match="project_id"):
        registry.register_project(project(path=r"A:\Other"))

    assert registry.get_project("project-a").root_path == r"A:\GitHub\Project-A"


def test_duplicate_worker_id_is_rejected_not_overwritten() -> None:
    registry = ControlPlaneRegistry()
    registry.register_worker(worker())

    with pytest.raises(DuplicateRegistrationError, match="worker_id"):
        registry.register_worker(
            Worker(worker_id="a-worker-01", display_name="replacement")
        )


def test_windows_worktree_key_is_case_and_separator_insensitive() -> None:
    assert windows_worktree_key(r"A:\GitHub\Project-A\.") == windows_worktree_key(
        "a:/github/project-a"
    )


def test_windows_worktree_key_rejects_blank_path() -> None:
    with pytest.raises(ValueError, match="worktree path must not be blank"):
        windows_worktree_key(" ")


def test_assign_and_release_reuses_same_worker_for_different_project() -> None:
    registry = ControlPlaneRegistry()
    registry.register_worker(worker())
    registry.register_project(project("project-a", r"A:\Repo-A"))
    registry.register_project(project("project-b", r"A:\Repo-B"))

    first = registry.assign(
        assignment("assign-01", "a-worker-01", "project-a"),
        mutation_allowed=True,
    )
    assert first.assignment_id == "assign-01"
    assert registry.get_worker("a-worker-01").assignment_id == "assign-01"

    released = registry.release_worker("a-worker-01")
    assert released.assignment_id is None
    assert released.worker_id == "a-worker-01"
    assert released.runtime_id == "runtime-01"

    second = registry.assign(
        assignment("assign-02", "a-worker-01", "project-b"),
        mutation_allowed=True,
    )
    assert second.project_id == "project-b"
    assert registry.get_worker("a-worker-01").assignment_id == "assign-02"


def test_same_mutating_worktree_cannot_be_assigned_to_two_workers() -> None:
    registry = ControlPlaneRegistry()
    registry.register_project(project("project-a", r"A:\Repo-A"))
    registry.register_worker(worker("a-worker-01", "runtime-01"))
    registry.register_worker(worker("a-worker-02", "runtime-02"))

    registry.assign(
        assignment("assign-01", "a-worker-01", runtime_id="runtime-01"),
        mutation_allowed=True,
    )

    with pytest.raises(AssignmentConflictError, match="mutating worktree"):
        registry.assign(
            assignment("assign-02", "a-worker-02", runtime_id="runtime-02"),
            mutation_allowed=True,
        )


def test_read_only_assignment_can_share_worktree_with_mutating_assignment() -> None:
    registry = ControlPlaneRegistry()
    registry.register_project(project("project-a", r"A:\Repo-A"))
    registry.register_worker(worker("a-worker-01", "runtime-01"))
    registry.register_worker(worker("a-worker-02", "runtime-02"))

    registry.assign(
        assignment("assign-01", "a-worker-01", runtime_id="runtime-01"),
        mutation_allowed=True,
    )
    shared = registry.assign(
        assignment("assign-02", "a-worker-02", runtime_id="runtime-02"),
        mutation_allowed=False,
    )

    assert shared.assignment_id == "assign-02"


def test_worker_cannot_receive_second_assignment_until_released() -> None:
    registry = ControlPlaneRegistry()
    registry.register_project(project("project-a", r"A:\Repo-A"))
    registry.register_project(project("project-b", r"A:\Repo-B"))
    registry.register_worker(worker())
    registry.assign(assignment("assign-01", "a-worker-01", "project-a"))

    with pytest.raises(AssignmentConflictError, match="worker already assigned"):
        registry.assign(assignment("assign-02", "a-worker-01", "project-b"))


def test_assignment_runtime_must_match_stable_worker_runtime_when_both_present() -> None:
    registry = ControlPlaneRegistry()
    registry.register_project(project())
    registry.register_worker(worker(runtime_id="stable-runtime"))

    with pytest.raises(AssignmentConflictError, match="runtime mismatch"):
        registry.assign(
            assignment(
                "assign-01",
                "a-worker-01",
                runtime_id="different-runtime",
            )
        )


def test_unknown_worker_or_project_is_explicit() -> None:
    registry = ControlPlaneRegistry()
    registry.register_worker(worker())

    with pytest.raises(RegistryNotFoundError, match="project_id"):
        registry.assign(assignment("assign-01", "a-worker-01", "missing"))

    with pytest.raises(RegistryNotFoundError, match="worker_id"):
        registry.get_worker("missing")


def test_busy_worker_cannot_be_released() -> None:
    registry = ControlPlaneRegistry()
    registry.register_project(project())
    registry.register_worker(worker())
    registry.assign(assignment("assign-01", "a-worker-01"))
    registry.set_worker_state("a-worker-01", WorkerState.BUSY)

    with pytest.raises(WorkerBusyError, match="busy worker"):
        registry.release_worker("a-worker-01")

    assert registry.get_worker("a-worker-01").assignment_id == "assign-01"


def test_release_is_idempotent_for_free_non_busy_worker() -> None:
    registry = ControlPlaneRegistry()
    registry.register_worker(worker())

    first = registry.release_worker("a-worker-01")
    second = registry.release_worker("a-worker-01")

    assert first.assignment_id is None
    assert second.assignment_id is None


def test_snapshot_is_deterministic_and_does_not_expose_mutable_dicts() -> None:
    registry = ControlPlaneRegistry()
    registry.register_project(project("project-b", r"A:\Repo-B"))
    registry.register_project(project("project-a", r"A:\Repo-A"))
    registry.register_worker(worker("a-worker-02", "runtime-02"))
    registry.register_worker(worker("a-worker-01", "runtime-01"))

    snapshot = registry.snapshot()

    assert tuple(item.project_id for item in snapshot.projects) == (
        "project-a",
        "project-b",
    )
    assert tuple(item.worker_id for item in snapshot.workers) == (
        "a-worker-01",
        "a-worker-02",
    )
    assert isinstance(snapshot.projects, tuple)
    assert isinstance(snapshot.workers, tuple)
    assert isinstance(snapshot.assignments, tuple)


def test_initial_three_worker_pool_uses_approved_product_names() -> None:
    registry = ControlPlaneRegistry.with_default_workers(size=3)
    snapshot = registry.snapshot()

    assert [(item.worker_id, item.display_name) for item in snapshot.workers] == [
        ("a-worker-01", "A-Worker 1"),
        ("a-worker-02", "A-Worker 2"),
        ("a-worker-03", "A-Worker 3"),
    ]


def test_default_worker_pool_size_must_be_positive() -> None:
    with pytest.raises(ValueError, match="size must be >= 1"):
        ControlPlaneRegistry.with_default_workers(size=0)
