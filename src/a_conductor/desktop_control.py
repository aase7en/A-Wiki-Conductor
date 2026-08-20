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
from .runtime_setup import RuntimeSetupError, RuntimeSetupService, SetupReadiness, WorkerSetupDraft
from .serena_config_store import SQLiteSerenaConfigStore


class LifecycleCommandService(Protocol):
    def execute(self, worker_id: str, action: LifecycleAction): ...


class DesktopControlService:
    def __init__(
        self,
        *,
        control_center: ControlCenterService,
        lifecycle: LifecycleCommandService,
        runtime_setup: RuntimeSetupService | None = None,
    ) -> None:
        self.control_center = control_center
        self.lifecycle = lifecycle
        self.runtime_setup = runtime_setup

    @classmethod
    def open(
        cls,
        database_path: str | Path,
        *,
        coordinator_builder: Callable[..., LifecycleCoordinator] = build_local_lifecycle_coordinator,
    ) -> "DesktopControlService":
        database = Path(database_path)
        control_center = ControlCenterService.open(SQLiteRegistryStore(database))
        config_store = SQLiteSerenaConfigStore(database)
        lifecycle = coordinator_builder(database, service=control_center)
        runtime_setup = RuntimeSetupService(
            control_center=control_center,
            config_store=config_store,
        )
        return cls(
            control_center=control_center,
            lifecycle=lifecycle,
            runtime_setup=runtime_setup,
        )

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

    def _require_runtime_setup(self) -> RuntimeSetupService:
        if self.runtime_setup is None:
            raise RuntimeSetupError("RUNTIME_SETUP_NOT_AVAILABLE")
        return self.runtime_setup

    def worker_setup(self, worker_id: str) -> WorkerSetupDraft:
        return self._require_runtime_setup().worker_setup(worker_id)

    def save_worker_setup(
        self,
        draft: WorkerSetupDraft,
        *,
        serena_config_source=None,
    ) -> WorkerSetupDraft:
        return self._require_runtime_setup().save_worker_setup(
            draft,
            serena_config_source=serena_config_source,
        )

    def capture_exact_project_identity(self, worker_id: str):
        return self._require_runtime_setup().capture_exact_project_identity(worker_id)

    def save_no_git_project_identity(self, worker_id: str):
        return self._require_runtime_setup().save_no_git_project_identity(worker_id)

    def lifecycle_readiness(self, worker_id: str) -> SetupReadiness:
        return self._require_runtime_setup().lifecycle_readiness(worker_id)
