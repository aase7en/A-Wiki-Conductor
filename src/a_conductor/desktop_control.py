"""Desktop-facing facade over ControlCenterService + LifecycleCoordinator.

The facade intentionally exposes only application-level project/assignment and
worker lifecycle methods. It contains no process, tunnel, Git, profile, or
credential implementation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol

from .control_center import ControlCenterService
from .lifecycle import LifecycleAction
from .lifecycle_assembly import build_local_lifecycle_coordinator
from .lifecycle_coordinator import LifecycleCoordinator
from .persistence import SQLiteRegistryStore


class LifecycleCommandService(Protocol):
    def execute(self, worker_id: str, action: LifecycleAction): ...


class DesktopControlService:
    def __init__(
        self,
        *,
        control_center: ControlCenterService,
        lifecycle: LifecycleCommandService,
    ) -> None:
        self.control_center = control_center
        self.lifecycle = lifecycle

    @classmethod
    def open(
        cls,
        database_path: str | Path,
        *,
        coordinator_builder: Callable[..., LifecycleCoordinator] = build_local_lifecycle_coordinator,
    ) -> "DesktopControlService":
        database = Path(database_path)
        control_center = ControlCenterService.open(SQLiteRegistryStore(database))
        lifecycle = coordinator_builder(database, service=control_center)
        return cls(control_center=control_center, lifecycle=lifecycle)

    def snapshot(self):
        return self.control_center.snapshot()

    def register_project(self, root_path, *, display_name=None, project_id=None):
        return self.control_center.register_project(
            root_path,
            display_name=display_name,
            project_id=project_id,
        )

    def assign_project(
        self,
        worker_id: str,
        project_id: str,
        *,
        mutation_allowed: bool = True,
        runtime_id: str | None = None,
    ):
        return self.control_center.assign_project(
            worker_id,
            project_id,
            mutation_allowed=mutation_allowed,
            runtime_id=runtime_id,
        )

    def release_worker(self, worker_id: str):
        return self.control_center.release_worker(worker_id)

    def start_worker(self, worker_id: str):
        return self.lifecycle.execute(worker_id, LifecycleAction.START)

    def stop_worker(self, worker_id: str):
        return self.lifecycle.execute(worker_id, LifecycleAction.STOP)

    def restart_worker(self, worker_id: str):
        return self.lifecycle.execute(worker_id, LifecycleAction.RESTART)
