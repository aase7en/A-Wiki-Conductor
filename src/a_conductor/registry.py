"""In-memory Project and reusable A-Worker registry.

The registry deliberately performs no filesystem, Git, process, network, or
persistence I/O. It manages control-plane metadata and deterministic assignment
conflicts only. A-Wiki cross-agent claims remain a separate coordination layer.
"""

from __future__ import annotations

import ntpath
from dataclasses import dataclass, replace

from .domain import Assignment, Project, Worker, WorkerState


class RegistryError(RuntimeError):
    """Base class for control-plane registry failures."""


class DuplicateRegistrationError(RegistryError):
    pass


class AssignmentConflictError(RegistryError):
    pass


class RegistryNotFoundError(RegistryError):
    pass


class WorkerBusyError(RegistryError):
    pass


def windows_worktree_key(path: str) -> str:
    if not isinstance(path, str) or not path.strip():
        raise ValueError("worktree path must not be blank")
    return ntpath.normcase(ntpath.normpath(path.strip()))


@dataclass(frozen=True, slots=True)
class AssignmentRecord:
    assignment: Assignment
    mutation_allowed: bool
    worktree_key: str

    @property
    def assignment_id(self) -> str:
        return self.assignment.assignment_id

    @property
    def worker_id(self) -> str:
        return self.assignment.worker_id

    @property
    def project_id(self) -> str:
        return self.assignment.project_id


@dataclass(frozen=True, slots=True)
class RegistrySnapshot:
    projects: tuple[Project, ...]
    workers: tuple[Worker, ...]
    assignments: tuple[AssignmentRecord, ...]


class ControlPlaneRegistry:
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._workers: dict[str, Worker] = {}
        self._assignments: dict[str, AssignmentRecord] = {}

    @classmethod
    def with_default_workers(cls, *, size: int = 3) -> "ControlPlaneRegistry":
        if not isinstance(size, int) or isinstance(size, bool) or size < 1:
            raise ValueError("size must be >= 1")
        registry = cls()
        for index in range(1, size + 1):
            registry.register_worker(
                Worker(
                    worker_id=f"a-worker-{index:02d}",
                    display_name=f"A-Worker {index}",
                )
            )
        return registry

    def register_project(self, project: Project) -> Project:
        if project.project_id in self._projects:
            raise DuplicateRegistrationError(
                f"project_id already registered: {project.project_id}"
            )
        self._projects[project.project_id] = project
        return project

    def register_worker(self, worker: Worker) -> Worker:
        if worker.worker_id in self._workers:
            raise DuplicateRegistrationError(
                f"worker_id already registered: {worker.worker_id}"
            )
        if worker.assignment_id is not None:
            raise ValueError("worker must be registered without an assignment")
        self._workers[worker.worker_id] = worker
        return worker

    def get_project(self, project_id: str) -> Project:
        try:
            return self._projects[project_id]
        except KeyError:
            raise RegistryNotFoundError(f"project_id not found: {project_id}") from None

    def get_worker(self, worker_id: str) -> Worker:
        try:
            return self._workers[worker_id]
        except KeyError:
            raise RegistryNotFoundError(f"worker_id not found: {worker_id}") from None

    def assign(
        self,
        assignment: Assignment,
        *,
        mutation_allowed: bool = True,
    ) -> Assignment:
        worker = self.get_worker(assignment.worker_id)
        project = self.get_project(assignment.project_id)

        if assignment.assignment_id in self._assignments:
            raise DuplicateRegistrationError(
                f"assignment_id already registered: {assignment.assignment_id}"
            )
        if worker.assignment_id is not None:
            raise AssignmentConflictError(
                f"worker already assigned: {worker.worker_id}"
            )
        if (
            worker.runtime_id is not None
            and assignment.runtime_id is not None
            and worker.runtime_id != assignment.runtime_id
        ):
            raise AssignmentConflictError(
                f"runtime mismatch for worker {worker.worker_id}"
            )

        worktree_key = windows_worktree_key(project.root_path)
        if mutation_allowed:
            for record in self._assignments.values():
                if (
                    record.mutation_allowed
                    and record.worktree_key == worktree_key
                    and record.worker_id != worker.worker_id
                ):
                    raise AssignmentConflictError(
                        "mutating worktree already assigned to another worker"
                    )

        record = AssignmentRecord(
            assignment=assignment,
            mutation_allowed=bool(mutation_allowed),
            worktree_key=worktree_key,
        )
        self._assignments[assignment.assignment_id] = record
        self._workers[worker.worker_id] = replace(
            worker,
            assignment_id=assignment.assignment_id,
        )
        return assignment

    def replace_assignment(
        self,
        assignment: Assignment,
        *,
        mutation_allowed: bool = True,
    ) -> Assignment:
        """Atomically replace a STOPPED worker assignment after full validation."""
        worker = self.get_worker(assignment.worker_id)
        project = self.get_project(assignment.project_id)
        if worker.state is not WorkerState.STOPPED:
            raise WorkerBusyError(
                f"busy worker assignment cannot be replaced until STOPPED: {worker.worker_id}"
            )
        if worker.assignment_id is None:
            return self.assign(assignment, mutation_allowed=mutation_allowed)
        if assignment.assignment_id in self._assignments:
            raise DuplicateRegistrationError(
                f"assignment_id already registered: {assignment.assignment_id}"
            )
        if (
            worker.runtime_id is not None
            and assignment.runtime_id is not None
            and worker.runtime_id != assignment.runtime_id
        ):
            raise AssignmentConflictError(
                f"runtime mismatch for worker {worker.worker_id}"
            )
        worktree_key = windows_worktree_key(project.root_path)
        if mutation_allowed:
            for record in self._assignments.values():
                if (
                    record.worker_id != worker.worker_id
                    and record.mutation_allowed
                    and record.worktree_key == worktree_key
                ):
                    raise AssignmentConflictError(
                        "mutating worktree already assigned to another worker"
                    )
        old_assignment_id = worker.assignment_id
        record = AssignmentRecord(
            assignment=assignment,
            mutation_allowed=bool(mutation_allowed),
            worktree_key=worktree_key,
        )
        self._assignments.pop(old_assignment_id, None)
        self._assignments[assignment.assignment_id] = record
        self._workers[worker.worker_id] = replace(
            worker, assignment_id=assignment.assignment_id
        )
        return assignment

    def release_worker(self, worker_id: str) -> Worker:
        worker = self.get_worker(worker_id)
        if worker.state is not WorkerState.STOPPED:
            raise WorkerBusyError(
                f"busy worker cannot be released until STOPPED: {worker_id}"
            )
        if worker.assignment_id is None:
            return worker

        self._assignments.pop(worker.assignment_id, None)
        released = replace(worker, assignment_id=None)
        self._workers[worker_id] = released
        return released

    def set_worker_state(self, worker_id: str, state: WorkerState) -> Worker:
        worker = self.get_worker(worker_id)
        updated = replace(worker, state=state)
        self._workers[worker_id] = updated
        return updated

    def rename_worker(self, worker_id: str, display_name: str) -> Worker:
        worker = self.get_worker(worker_id)
        if not isinstance(display_name, str) or not display_name.strip():
            raise ValueError("display_name must not be blank")
        updated = replace(worker, display_name=display_name.strip())
        self._workers[worker_id] = updated
        return updated

    def unregister_worker(self, worker_id: str) -> Worker:
        worker = self.get_worker(worker_id)
        if worker.assignment_id is not None:
            raise WorkerBusyError(
                f"assigned worker cannot be deleted: {worker_id}"
            )
        if worker.state is not WorkerState.STOPPED:
            raise WorkerBusyError(
                f"busy worker cannot be deleted until STOPPED: {worker_id}"
            )
        del self._workers[worker_id]
        return worker

    def snapshot(self) -> RegistrySnapshot:
        return RegistrySnapshot(
            projects=tuple(
                self._projects[key] for key in sorted(self._projects)
            ),
            workers=tuple(
                self._workers[key] for key in sorted(self._workers)
            ),
            assignments=tuple(
                self._assignments[key] for key in sorted(self._assignments)
            ),
        )
