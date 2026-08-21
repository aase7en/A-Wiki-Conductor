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
from .local_instances import (
    DEFAULT_INSTANCES_ROOT,
    InstanceHealthState,
    InstanceOrchestrationOutcome,
    InstanceResultCode,
    LocalInstance,
    LocalInstanceOrchestrator,
    connector_name_for_project,
    discover_local_instances,
    instance_health_state,
)
from .persistence import SQLiteRegistryStore
from .runtime_setup import RuntimeSetupError, RuntimeSetupService, SetupReadiness, WorkerSetupDraft
from .serena_config_store import SerenaConfigStoreError, SQLiteSerenaConfigStore
from .worker_serena_settings import WorkerSerenaSettings


class LifecycleCommandService(Protocol):
    def execute(self, worker_id: str, action: LifecycleAction): ...


class DesktopControlService:
    def __init__(
        self,
        *,
        control_center: ControlCenterService,
        lifecycle: LifecycleCommandService,
        runtime_setup: RuntimeSetupService | None = None,
        settings_store: SQLiteSerenaConfigStore | None = None,
        instances_root: str | Path = DEFAULT_INSTANCES_ROOT,
        instance_orchestrator: LocalInstanceOrchestrator | None = None,
    ) -> None:
        self.control_center = control_center
        self.lifecycle = lifecycle
        self.runtime_setup = runtime_setup
        self.settings_store = settings_store
        self.instances_root = instances_root
        self._instance_orchestrator = instance_orchestrator

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
            settings_store=config_store,
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

    def set_instance_tunnel_id(self, instance_name: str, tunnel_id: str) -> Path:
        """Write a validated Tunnel ID into the instance's config dir (in-app setup)."""
        from .local_instances import _TUNNEL_ID_RE

        if not isinstance(instance_name, str) or not instance_name.strip():
            raise SerenaConfigStoreError("INSTANCE_NAME_INVALID")
        candidate = (tunnel_id or "").strip() if isinstance(tunnel_id, str) else ""
        if _TUNNEL_ID_RE.fullmatch(candidate) is None:
            raise SerenaConfigStoreError("TUNNEL_ID_INVALID")
        target = next(
            (item for item in self.instances() if item.name == instance_name), None
        )
        if target is None:
            raise SerenaConfigStoreError("INSTANCE_NOT_FOUND")
        root = Path(self.instances_root).expanduser().resolve(strict=False)
        instance_root = target.instance_root.resolve(strict=False)
        if root not in instance_root.parents:
            raise SerenaConfigStoreError("INSTANCE_OUTSIDE_ROOT")
        config_dir = instance_root / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        tunnel_path = config_dir / "tunnel-id.txt"
        tunnel_path.write_text(candidate + "\n", encoding="utf-8", newline="\n")
        return tunnel_path

    def worker_start_path(self, worker_id: str) -> tuple[str, str | None]:
        """Decide how Start should run for a worker.

        Returns ("connector", <instance name>) when the assigned project has a
        matching connector instance — the user's real tunnel path that works
        without runtime setup — else ("lifecycle", None) when setup is ready,
        else ("blocked", "SETUP_REQUIRED").
        """
        row = next(
            (
                candidate
                for candidate in self.control_center.snapshot().workers
                if candidate.worker_id == worker_id
            ),
            None,
        )
        if row is None or row.project_root_path is None:
            return ("blocked", "NO_ASSIGNMENT")
        try:
            instances = self.instances()
        except Exception:
            instances = ()
        connector = connector_name_for_project(instances, row.project_root_path)
        if connector is not None:
            return ("connector", connector)
        try:
            if self.lifecycle_readiness(worker_id).ready:
                return ("lifecycle", None)
        except Exception:
            pass
        return ("blocked", "SETUP_REQUIRED")

    def _require_settings_store(self) -> SQLiteSerenaConfigStore:
        if self.settings_store is None:
            raise SerenaConfigStoreError("SETTINGS_STORE_NOT_AVAILABLE")
        return self.settings_store

    def worker_settings(self, worker_id: str) -> WorkerSerenaSettings:
        store = self._require_settings_store()
        try:
            settings = store.get_worker_settings(worker_id)
        except SerenaConfigStoreError:
            raise
        except Exception as exc:
            raise SerenaConfigStoreError("SETTINGS_LOAD_FAILED") from exc
        if settings is None:
            return WorkerSerenaSettings(worker_id=worker_id)
        return settings

    def save_worker_settings(self, settings: WorkerSerenaSettings) -> WorkerSerenaSettings:
        if not isinstance(settings, WorkerSerenaSettings):
            raise SerenaConfigStoreError("SETTINGS_INVALID")
        store = self._require_settings_store()
        store.save_worker_settings(settings)
        return settings

    def instances(self) -> tuple[LocalInstance, ...]:
        return discover_local_instances(self.instances_root)

    def instance_states(self) -> tuple[tuple[LocalInstance, InstanceHealthState], ...]:
        return tuple(
            (instance, instance_health_state(instance))
            for instance in self.instances()
        )

    def _orchestrator(self) -> LocalInstanceOrchestrator:
        if self._instance_orchestrator is None:
            self._instance_orchestrator = LocalInstanceOrchestrator(
                instances_root=self.instances_root,
                brain_settings_provider=self._global_brain_provider,
            )
        return self._instance_orchestrator

    def _global_brain_provider(self):
        store = self.settings_store
        if store is None:
            return None
        try:
            return store.get_worker_settings("global-brain")
        except Exception:
            return None

    def instance_action(
        self, instance_name: str, action: str
    ) -> InstanceOrchestrationOutcome:
        if not isinstance(instance_name, str) or not instance_name.strip():
            raise SerenaConfigStoreError("INSTANCE_NAME_INVALID")
        if action not in ("start", "stop"):
            raise SerenaConfigStoreError("INSTANCE_ACTION_INVALID")
        target = next(
            (item for item in self.instances() if item.name == instance_name), None
        )
        if target is None:
            raise SerenaConfigStoreError("INSTANCE_NOT_FOUND")
        orchestrator = self._orchestrator()
        if action == "start":
            return orchestrator.start(target)
        return orchestrator.stop(target)

    def set_instance_autostart(self, instance_name: str, enabled: bool) -> None:
        self._require_settings_store().set_instance_autostart(instance_name, enabled)

    def instance_autostart(self, instance_name: str) -> bool:
        return self._require_settings_store().get_instance_autostart(instance_name)

    def autostart_instance_names(self) -> tuple[str, ...]:
        return self._require_settings_store().list_instance_autostart()
