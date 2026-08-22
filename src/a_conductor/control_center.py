"""Local application service and immutable Projects/Workers screen model."""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from .domain import Assignment, Project, Worker, WorkerState
from .persistence import PersistenceError
from .registry import (
    AssignmentConflictError,
    ControlPlaneRegistry,
    DuplicateRegistrationError,
    RegistryError,
    RegistryNotFoundError,
    RegistrySnapshot,
    WorkerBusyError,
    windows_worktree_key,
)


class RegistryStore(Protocol):
    def load(self) -> ControlPlaneRegistry: ...

    def save(self, snapshot: RegistrySnapshot) -> None: ...


class ControlCenterError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class WorkerScreenRow:
    worker_id: str
    display_name: str
    state: WorkerState
    runtime_id: str | None
    assignment_id: str | None
    project_id: str | None
    project_display_name: str | None
    project_root_path: str | None
    mutation_allowed: bool | None


@dataclass(frozen=True, slots=True)
class ControlCenterSnapshot:
    projects: tuple[Project, ...]
    workers: tuple[WorkerScreenRow, ...]
    online: bool = True


def _generated_project_id(root_path: str) -> str:
    key = windows_worktree_key(root_path)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    return f"project-{digest}"


def _default_assignment_id() -> str:
    return f"assignment-{uuid.uuid4().hex}"


class ControlCenterService:
    def __init__(
        self,
        *,
        store: RegistryStore,
        registry: ControlPlaneRegistry,
        assignment_id_factory: Callable[[], str] = _default_assignment_id,
    ) -> None:
        self._store = store
        self._registry = registry
        self._assignment_id_factory = assignment_id_factory

    @classmethod
    def open(
        cls,
        store: RegistryStore,
        *,
        assignment_id_factory: Callable[[], str] = _default_assignment_id,
    ) -> "ControlCenterService":
        try:
            registry = store.load()
        except PersistenceError as exc:
            raise ControlCenterError("PERSISTENCE_FAILED") from exc
        snapshot = registry.snapshot()
        if not snapshot.workers:
            if snapshot.projects or snapshot.assignments:
                raise ControlCenterError("REGISTRY_WORKERS_MISSING")
            registry = ControlPlaneRegistry.with_default_workers(size=3)
            try:
                store.save(registry.snapshot())
            except PersistenceError as exc:
                raise ControlCenterError("PERSISTENCE_FAILED") from exc
        return cls(
            store=store,
            registry=registry,
            assignment_id_factory=assignment_id_factory,
        )

    def _restore_durable_after_failure(self, cause: Exception) -> None:
        try:
            self._registry = self._store.load()
        except Exception as restore_exc:
            raise ControlCenterError("PERSISTENCE_RECOVERY_FAILED") from restore_exc
        raise ControlCenterError("PERSISTENCE_FAILED") from cause

    def _save(self) -> None:
        try:
            self._store.save(self._registry.snapshot())
        except PersistenceError as exc:
            self._restore_durable_after_failure(exc)

    def register_project(
        self,
        root_path: str | Path,
        *,
        display_name: str | None = None,
        project_id: str | None = None,
    ) -> Project:
        try:
            root = Path(root_path).expanduser().resolve(strict=False)
            exists = root.is_dir()
        except OSError:
            exists = False
            root = Path(root_path)
        if not exists:
            raise ControlCenterError("PROJECT_NOT_FOUND")
        normalized_key = windows_worktree_key(str(root))
        for existing in self._registry.snapshot().projects:
            if windows_worktree_key(existing.root_path) == normalized_key:
                return existing

        name = display_name.strip() if isinstance(display_name, str) and display_name.strip() else root.name
        identifier = project_id.strip() if isinstance(project_id, str) and project_id.strip() else _generated_project_id(str(root))
        project = Project(
            project_id=identifier,
            display_name=name or identifier,
            root_path=str(root),
        )
        try:
            self._registry.register_project(project)
        except DuplicateRegistrationError as exc:
            raise ControlCenterError("DUPLICATE_REGISTRATION") from exc
        self._save()
        return project

    def assign_project(
        self,
        worker_id: str,
        project_id: str,
        *,
        mutation_allowed: bool = True,
        runtime_id: str | None = None,
    ) -> Assignment:
        assignment = Assignment(
            assignment_id=self._assignment_id_factory(),
            worker_id=worker_id,
            project_id=project_id,
            runtime_id=runtime_id,
        )
        try:
            self._registry.assign(
                assignment,
                mutation_allowed=mutation_allowed,
            )
        except AssignmentConflictError as exc:
            raise ControlCenterError("ASSIGNMENT_CONFLICT") from exc
        except RegistryNotFoundError as exc:
            raise ControlCenterError("REGISTRY_NOT_FOUND") from exc
        except DuplicateRegistrationError as exc:
            raise ControlCenterError("DUPLICATE_REGISTRATION") from exc
        self._save()
        return assignment

    def set_worker_state(self, worker_id: str, state: WorkerState):
        try:
            worker = self._registry.set_worker_state(worker_id, state)
        except RegistryNotFoundError as exc:
            raise ControlCenterError("REGISTRY_NOT_FOUND") from exc
        self._save()
        return worker

    def release_worker(self, worker_id: str):
        try:
            worker = self._registry.release_worker(worker_id)
        except WorkerBusyError as exc:
            raise ControlCenterError("WORKER_BUSY") from exc
        except RegistryNotFoundError as exc:
            raise ControlCenterError("REGISTRY_NOT_FOUND") from exc
        self._save()
        return worker

    def add_worker(self, display_name: str | None = None) -> Worker:
        """Register a new worker slot with the next free a-worker-NN id."""
        numbers = []
        for worker in self._registry.snapshot().workers:
            suffix = re.search(r"-(\d+)$", worker.worker_id)
            if suffix:
                numbers.append(int(suffix.group(1)))
        number = max(numbers, default=0) + 1
        name = (
            display_name.strip()
            if isinstance(display_name, str) and display_name.strip()
            else f"A-Worker {number}"
        )
        worker = Worker(
            worker_id=f"a-worker-{number:02d}",
            display_name=name,
        )
        try:
            registered = self._registry.register_worker(worker)
        except DuplicateRegistrationError as exc:
            raise ControlCenterError("DUPLICATE_REGISTRATION") from exc
        self._save()
        return registered

    def rename_worker(self, worker_id: str, display_name: str) -> Worker:
        """Rename a worker's display name (worker_id stays stable)."""
        try:
            worker = self._registry.rename_worker(worker_id, display_name)
        except RegistryNotFoundError as exc:
            raise ControlCenterError("REGISTRY_NOT_FOUND") from exc
        except ValueError as exc:
            raise ControlCenterError("WORKER_NAME_INVALID") from exc
        self._save()
        return worker

    def delete_worker(self, worker_id: str) -> Worker:
        """Remove a worker slot; only unassigned STOPPED workers may go."""
        try:
            worker = self._registry.unregister_worker(worker_id)
        except RegistryNotFoundError as exc:
            raise ControlCenterError("REGISTRY_NOT_FOUND") from exc
        except WorkerBusyError as exc:
            raise ControlCenterError("WORKER_BUSY") from exc
        self._save()
        return worker

    def snapshot(self) -> ControlCenterSnapshot:
        raw = self._registry.snapshot()
        assignments = {record.assignment_id: record for record in raw.assignments}
        projects = {project.project_id: project for project in raw.projects}
        workers: list[WorkerScreenRow] = []
        for worker in raw.workers:
            record = assignments.get(worker.assignment_id) if worker.assignment_id else None
            project = projects.get(record.project_id) if record is not None else None
            workers.append(
                WorkerScreenRow(
                    worker_id=worker.worker_id,
                    display_name=worker.display_name,
                    state=worker.state,
                    runtime_id=worker.runtime_id,
                    assignment_id=worker.assignment_id,
                    project_id=project.project_id if project else None,
                    project_display_name=project.display_name if project else None,
                    project_root_path=project.root_path if project else None,
                    mutation_allowed=record.mutation_allowed if record else None,
                )
            )
        return ControlCenterSnapshot(
            projects=raw.projects,
            workers=tuple(workers),
            online=True,
        )
