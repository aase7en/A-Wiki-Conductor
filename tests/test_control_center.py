from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from a_conductor.control_center import (
    ControlCenterError,
    ControlCenterService,
    ControlCenterSnapshot,
)
from a_conductor.domain import WorkerState
from a_conductor.persistence import PersistenceError, SQLiteRegistryStore


def open_service(tmp_path: Path) -> ControlCenterService:
    return ControlCenterService.open(SQLiteRegistryStore(tmp_path / "control-center.sqlite"))


def test_fresh_store_bootstraps_exactly_three_reusable_workers(tmp_path: Path) -> None:
    service = open_service(tmp_path)
    snapshot = service.snapshot()

    assert [worker.worker_id for worker in snapshot.workers] == [
        "a-worker-01",
        "a-worker-02",
        "a-worker-03",
    ]
    assert [worker.display_name for worker in snapshot.workers] == [
        "A-Worker 1",
        "A-Worker 2",
        "A-Worker 3",
    ]
    assert all(worker.state is WorkerState.STOPPED for worker in snapshot.workers)

    reopened = open_service(tmp_path)
    assert reopened.snapshot() == snapshot


def test_register_project_is_read_only_and_persistent(tmp_path: Path) -> None:
    project_dir = tmp_path / "project-one"
    project_dir.mkdir()
    sentinel = project_dir / "keep.txt"
    sentinel.write_text("unchanged", encoding="utf-8")
    service = open_service(tmp_path)

    project = service.register_project(project_dir, display_name="Project One")

    assert project.display_name == "Project One"
    assert project.root_path == str(project_dir.resolve())
    assert sentinel.read_text(encoding="utf-8") == "unchanged"
    assert not (project_dir / ".git").exists()
    reopened = open_service(tmp_path)
    assert reopened.snapshot().projects[0] == project


def test_generated_project_id_is_deterministic_and_duplicate_root_returns_existing(tmp_path: Path) -> None:
    project_dir = tmp_path / "same-project"
    project_dir.mkdir()
    first = open_service(tmp_path)
    project = first.register_project(project_dir, display_name="First")

    reopened = open_service(tmp_path)
    duplicate = reopened.register_project(project_dir, display_name="Different Name")

    assert duplicate == project
    assert project.project_id.startswith("project-")
    assert len(reopened.snapshot().projects) == 1


def test_missing_project_path_is_rejected_before_persistence(tmp_path: Path) -> None:
    service = open_service(tmp_path)
    with pytest.raises(ControlCenterError) as exc_info:
        service.register_project(tmp_path / "missing", display_name="Missing")
    assert exc_info.value.code == "PROJECT_NOT_FOUND"
    assert service.snapshot().projects == ()


def test_assign_project_persists_and_projects_worker_row(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    service = open_service(tmp_path)
    project = service.register_project(project_dir, display_name="Project")

    assignment = service.assign_project("a-worker-01", project.project_id)
    snapshot = service.snapshot()

    row = next(item for item in snapshot.workers if item.worker_id == "a-worker-01")
    assert row.assignment_id == assignment.assignment_id
    assert row.project_id == project.project_id
    assert row.project_display_name == "Project"
    assert row.project_root_path == str(project_dir.resolve())

    reopened = open_service(tmp_path)
    reopened_row = next(item for item in reopened.snapshot().workers if item.worker_id == "a-worker-01")
    assert reopened_row == row


def test_mutating_same_worktree_on_second_worker_is_rejected(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    service = open_service(tmp_path)
    project = service.register_project(project_dir)
    service.assign_project("a-worker-01", project.project_id, mutation_allowed=True)

    with pytest.raises(ControlCenterError) as exc_info:
        service.assign_project("a-worker-02", project.project_id, mutation_allowed=True)

    assert exc_info.value.code == "ASSIGNMENT_CONFLICT"
    assert next(w for w in service.snapshot().workers if w.worker_id == "a-worker-02").assignment_id is None


def test_read_only_duplicate_worktree_assignment_is_allowed(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    service = open_service(tmp_path)
    project = service.register_project(project_dir)
    service.assign_project("a-worker-01", project.project_id, mutation_allowed=True)

    second = service.assign_project("a-worker-02", project.project_id, mutation_allowed=False)

    assert second.worker_id == "a-worker-02"


def test_release_requires_stopped_worker_and_persists(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    service = open_service(tmp_path)
    project = service.register_project(project_dir)
    service.assign_project("a-worker-01", project.project_id)
    service.set_worker_state("a-worker-01", WorkerState.READY)

    with pytest.raises(ControlCenterError) as exc_info:
        service.release_worker("a-worker-01")
    assert exc_info.value.code == "WORKER_BUSY"

    service.set_worker_state("a-worker-01", WorkerState.STOPPED)
    released = service.release_worker("a-worker-01")
    assert released.assignment_id is None
    assert next(w for w in open_service(tmp_path).snapshot().workers if w.worker_id == "a-worker-01").assignment_id is None


def test_snapshot_is_immutable_and_contains_assignment_projection(tmp_path: Path) -> None:
    service = open_service(tmp_path)
    snapshot = service.snapshot()
    assert isinstance(snapshot, ControlCenterSnapshot)
    with pytest.raises(FrozenInstanceError):
        snapshot.online = False  # type: ignore[misc]


class FailingStore:
    def __init__(self, base: SQLiteRegistryStore) -> None:
        self.base = base
        self.fail_next_save = False

    def load(self):
        return self.base.load()

    def save(self, snapshot) -> None:
        if self.fail_next_save:
            self.fail_next_save = False
            raise PersistenceError("simulated persistence failure")
        self.base.save(snapshot)


def test_failed_save_rolls_back_service_to_last_durable_state(tmp_path: Path) -> None:
    base = SQLiteRegistryStore(tmp_path / "control-center.sqlite")
    store = FailingStore(base)
    service = ControlCenterService.open(store)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    store.fail_next_save = True

    with pytest.raises(ControlCenterError) as exc_info:
        service.register_project(project_dir)

    assert exc_info.value.code == "PERSISTENCE_FAILED"
    assert service.snapshot().projects == ()
    assert ControlCenterService.open(base).snapshot().projects == ()



def test_replace_assignment_preserves_old_assignment_when_new_project_conflicts(tmp_path: Path) -> None:
    service = open_service(tmp_path)
    p1_dir = tmp_path / "p1"
    p2_dir = tmp_path / "p2"
    p1_dir.mkdir()
    p2_dir.mkdir()
    p1 = service.register_project(p1_dir, project_id="p1")
    p2 = service.register_project(p2_dir, project_id="p2")
    service.assign_project("a-worker-01", p1.project_id)
    service.assign_project("a-worker-02", p2.project_id)

    with pytest.raises(ControlCenterError) as exc_info:
        service.replace_assignment("a-worker-01", p2.project_id)

    assert exc_info.value.code == "ASSIGNMENT_CONFLICT"
    w1 = next(w for w in service.snapshot().workers if w.worker_id == "a-worker-01")
    assert w1.project_id == "p1"


def test_replace_assignment_switches_stopped_worker_atomically(tmp_path: Path) -> None:
    service = open_service(tmp_path)
    p1_dir = tmp_path / "p1"
    p2_dir = tmp_path / "p2"
    p1_dir.mkdir()
    p2_dir.mkdir()
    p1 = service.register_project(p1_dir, project_id="p1")
    p2 = service.register_project(p2_dir, project_id="p2")
    service.assign_project("a-worker-01", p1.project_id)

    service.replace_assignment("a-worker-01", p2.project_id)

    w1 = next(w for w in service.snapshot().workers if w.worker_id == "a-worker-01")
    assert w1.project_id == "p2"
    reopened = open_service(tmp_path)
    persisted = next(w for w in reopened.snapshot().workers if w.worker_id == "a-worker-01")
    assert persisted.project_id == "p2"


def test_replace_assignment_rejects_busy_worker_without_losing_old_project(tmp_path: Path) -> None:
    service = open_service(tmp_path)
    p1_dir = tmp_path / "p1-busy"
    p2_dir = tmp_path / "p2-busy"
    p1_dir.mkdir()
    p2_dir.mkdir()
    p1 = service.register_project(p1_dir, project_id="p1-busy")
    p2 = service.register_project(p2_dir, project_id="p2-busy")
    service.assign_project("a-worker-01", p1.project_id)
    service.set_worker_state("a-worker-01", WorkerState.READY)
    with pytest.raises(ControlCenterError) as exc_info:
        service.replace_assignment("a-worker-01", p2.project_id)
    assert exc_info.value.code == "WORKER_BUSY"
    row = next(w for w in service.snapshot().workers if w.worker_id == "a-worker-01")
    assert row.project_id == p1.project_id


def test_replace_assignment_persistence_failure_restores_old_assignment(tmp_path: Path) -> None:
    base = SQLiteRegistryStore(tmp_path / "replace.sqlite")
    store = FailingStore(base)
    service = ControlCenterService.open(store)
    p1_dir = tmp_path / "p1-save"
    p2_dir = tmp_path / "p2-save"
    p1_dir.mkdir()
    p2_dir.mkdir()
    p1 = service.register_project(p1_dir, project_id="p1-save")
    p2 = service.register_project(p2_dir, project_id="p2-save")
    service.assign_project("a-worker-01", p1.project_id)
    store.fail_next_save = True
    with pytest.raises(ControlCenterError) as exc_info:
        service.replace_assignment("a-worker-01", p2.project_id)
    assert exc_info.value.code == "PERSISTENCE_FAILED"
    row = next(w for w in service.snapshot().workers if w.worker_id == "a-worker-01")
    assert row.project_id == p1.project_id
    durable = next(
        w for w in ControlCenterService.open(base).snapshot().workers
        if w.worker_id == "a-worker-01"
    )
    assert durable.project_id == p1.project_id
