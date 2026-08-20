from __future__ import annotations

import sys
from pathlib import Path

import pytest

from a_conductor.control_center import (
    ControlCenterService,
    ControlCenterSnapshot,
    WorkerScreenRow,
)
from a_conductor.domain import Project, WorkerState
from a_conductor.native_adapters import NativeGitReadAdapter, NativeVerificationAdapter
from a_conductor.native_operation_assembly import ControlCenterNativeAdapterResolver
from a_conductor.native_operations import NativeOperationError
from a_conductor.persistence import SQLiteRegistryStore


class FakeService:
    def __init__(self, snapshot: ControlCenterSnapshot) -> None:
        self.current = snapshot
        self.calls = 0

    def snapshot(self) -> ControlCenterSnapshot:
        self.calls += 1
        return self.current


def snapshot_for(
    root: Path,
    *,
    worker_id: str = "a-worker-01",
    assigned: bool = True,
    mutation_allowed: bool | None = True,
) -> ControlCenterSnapshot:
    project = Project("project-1", "Project", str(root.resolve()))
    row = WorkerScreenRow(
        worker_id,
        "A-Worker 1",
        WorkerState.STOPPED,
        "runtime-1",
        "assignment-1" if assigned else None,
        project.project_id if assigned else None,
        project.display_name if assigned else None,
        project.root_path if assigned else None,
        mutation_allowed if assigned else None,
    )
    return ControlCenterSnapshot(projects=(project,), workers=(row,), online=True)


def test_resolve_builds_exact_scope_from_fresh_assignment(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    service = FakeService(snapshot_for(project, mutation_allowed=True))
    captured = []
    git_marker = object()
    verify_marker = object()

    resolver = ControlCenterNativeAdapterResolver(
        service=service,
        git_executable="git.exe",
        python_executable=sys.executable,
        git_adapter_factory=lambda scope: captured.append(("git", scope)) or git_marker,
        verification_adapter_factory=lambda scope: captured.append(("verify", scope)) or verify_marker,
    )

    adapters = resolver.resolve("a-worker-01")

    assert adapters.git is git_marker
    assert adapters.verification is verify_marker
    assert service.calls == 1
    assert len(captured) == 2
    git_scope = captured[0][1]
    verify_scope = captured[1][1]
    assert git_scope == verify_scope
    assert Path(git_scope.root) == project.resolve()
    assert git_scope.mutation_allowed is True
    assert git_scope.allowed_executables == ("git.exe", Path(sys.executable).name)
    assert git_scope.allowed_environment_overrides == ()


def test_read_only_assignment_is_preserved_exactly(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    service = FakeService(snapshot_for(project, mutation_allowed=False))
    captured = []
    resolver = ControlCenterNativeAdapterResolver(
        service=service,
        git_adapter_factory=lambda scope: captured.append(scope) or object(),
        verification_adapter_factory=lambda scope: object(),
    )

    resolver.resolve("a-worker-01")

    assert captured[0].mutation_allowed is False


def test_unknown_worker_and_unassigned_worker_have_no_fallback(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    service = FakeService(snapshot_for(project, assigned=False))
    resolver = ControlCenterNativeAdapterResolver(service=service)

    with pytest.raises(NativeOperationError) as exc_info:
        resolver.resolve("a-worker-02")
    assert exc_info.value.code == "WORKER_NOT_FOUND"

    with pytest.raises(NativeOperationError) as exc_info:
        resolver.resolve("a-worker-01")
    assert exc_info.value.code == "WORKER_ASSIGNMENT_MISSING"


def test_missing_mutation_authority_is_refused(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    service = FakeService(snapshot_for(project, mutation_allowed=None))
    resolver = ControlCenterNativeAdapterResolver(service=service)

    with pytest.raises(NativeOperationError) as exc_info:
        resolver.resolve("a-worker-01")
    assert exc_info.value.code == "MUTATION_AUTHORITY_MISSING"


def test_missing_project_root_fails_before_adapter_construction(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    service = FakeService(snapshot_for(missing))
    calls = []
    resolver = ControlCenterNativeAdapterResolver(
        service=service,
        git_adapter_factory=lambda scope: calls.append(scope) or object(),
        verification_adapter_factory=lambda scope: calls.append(scope) or object(),
    )

    with pytest.raises(NativeOperationError) as exc_info:
        resolver.resolve("a-worker-01")
    assert exc_info.value.code == "ROOT_NOT_FOUND"
    assert calls == []


def test_resolver_does_not_cache_assignment_across_reassignment(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    service = FakeService(snapshot_for(first, mutation_allowed=True))
    captured = []
    resolver = ControlCenterNativeAdapterResolver(
        service=service,
        git_adapter_factory=lambda scope: captured.append(scope) or object(),
        verification_adapter_factory=lambda scope: object(),
    )

    resolver.resolve("a-worker-01")
    service.current = snapshot_for(second, mutation_allowed=False)
    resolver.resolve("a-worker-01")

    assert service.calls == 2
    assert Path(captured[0].root) == first.resolve()
    assert captured[0].mutation_allowed is True
    assert Path(captured[1].root) == second.resolve()
    assert captured[1].mutation_allowed is False


def test_default_factories_build_only_read_and_verification_adapters(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    service = ControlCenterService.open(SQLiteRegistryStore(database))
    project = tmp_path / "project"
    project.mkdir()
    registered = service.register_project(project, display_name="Project")
    service.assign_project("a-worker-01", registered.project_id, mutation_allowed=True)
    before = service.snapshot()

    resolver = ControlCenterNativeAdapterResolver(service=service)
    adapters = resolver.resolve("a-worker-01")

    assert isinstance(adapters.git, NativeGitReadAdapter)
    assert isinstance(adapters.verification, NativeVerificationAdapter)
    assert not hasattr(adapters, "git_transaction")
    assert not hasattr(adapters, "process")
    assert service.snapshot() == before


def test_scope_limits_are_explicit_and_bounded(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    service = FakeService(snapshot_for(project))
    captured = []
    resolver = ControlCenterNativeAdapterResolver(
        service=service,
        max_timeout_seconds=90,
        max_output_bytes=4096,
        max_file_bytes=8192,
        git_adapter_factory=lambda scope: captured.append(scope) or object(),
        verification_adapter_factory=lambda scope: object(),
    )

    resolver.resolve("a-worker-01")

    scope = captured[0]
    assert scope.max_timeout_seconds == 90
    assert scope.max_output_bytes == 4096
    assert scope.max_file_bytes == 8192
