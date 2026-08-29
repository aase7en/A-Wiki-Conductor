"""Desktop-facing facade over ControlCenterService + LifecycleCoordinator.

The facade intentionally exposes only application-level project/assignment and
worker lifecycle methods. It contains no process, tunnel, Git, profile, or
credential implementation.
"""

from __future__ import annotations

import os
import time
from collections import deque
from pathlib import Path
from threading import Lock
from typing import Callable, Protocol

from .control_center import ControlCenterService
from .connector_recovery import (
    ConnectorRecoveryCoordinator,
    ConnectorRecoveryRecord,
    ConnectorRecoveryState,
)
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


A_WIKI_DATA_BACKUP_DIR = Path("L:/My Drive/A-Wiki-Data/backups/a-conductor-instances")


def default_backup_dir() -> Path:
    """Prefer the A-Wiki-Data Drive layer; fall back to the local profile."""
    if A_WIKI_DATA_BACKUP_DIR.is_dir():
        return A_WIKI_DATA_BACKUP_DIR
    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home()
    return base / "A-Conductor" / "instance-backups"


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
        connector_recovery: ConnectorRecoveryCoordinator | None = None,
    ) -> None:
        self.control_center = control_center
        self.lifecycle = lifecycle
        self.runtime_setup = runtime_setup
        self.settings_store = settings_store
        self.instances_root = instances_root
        self._instance_orchestrator = instance_orchestrator
        self._connector_recovery = connector_recovery
        self._pending_instance_starts: set[str] = set()
        self._pending_instance_starts_lock = Lock()
        self._connector_intent_locks_guard = Lock()
        self._connector_intent_locks: dict[str, object] = {}
        self._connector_recovery_events_lock = Lock()
        self._connector_recovery_events: deque[ConnectorRecoveryRecord] = deque(maxlen=64)

    @classmethod
    def open(
        cls,
        database_path: str | Path,
        *,
        coordinator_builder: Callable[..., LifecycleCoordinator] = build_local_lifecycle_coordinator,
        instances_root: str | Path | None = None,
    ) -> "DesktopControlService":
        database = Path(database_path)
        control_center = ControlCenterService.open(SQLiteRegistryStore(database))
        config_store = SQLiteSerenaConfigStore(database)
        lifecycle = coordinator_builder(database, service=control_center)
        runtime_setup = RuntimeSetupService(
            control_center=control_center,
            config_store=config_store,
        )
        resolved_root = (
            Path(instances_root) if instances_root is not None else DEFAULT_INSTANCES_ROOT
        )
        return cls(
            control_center=control_center,
            lifecycle=lifecycle,
            runtime_setup=runtime_setup,
            settings_store=config_store,
            instances_root=resolved_root,
        )

    def snapshot(self):
        return self.control_center.snapshot()

    def operator_graph_ids(self) -> tuple[str, ...]:
        store = self.settings_store
        if store is None:
            return ()
        from .graph.operator_view import list_operator_graph_ids

        return list_operator_graph_ids(store.database_path)

    def operator_graph_snapshot(
        self, graph_id: str, graph_run_id: str | None = None, *, event_limit: int = 20
    ):
        store = self._require_settings_store()
        from .graph.operator_view import read_graph_operator_snapshot

        return read_graph_operator_snapshot(
            store.database_path, graph_id, graph_run_id, event_limit=event_limit
        )

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

    def replace_assignment(
        self,
        worker_id: str,
        project_id: str,
        *,
        mutation_allowed: bool = True,
        runtime_id: str | None = None,
    ):
        return self.control_center.replace_assignment(
            worker_id,
            project_id,
            mutation_allowed=mutation_allowed,
            runtime_id=runtime_id,
        )

    def release_worker(self, worker_id: str):
        return self.control_center.release_worker(worker_id)

    def add_worker(self, display_name: str | None = None):
        return self.control_center.add_worker(display_name)

    def rename_worker(self, worker_id: str, display_name: str):
        return self.control_center.rename_worker(worker_id, display_name)

    def delete_worker(self, worker_id: str):
        return self.control_center.delete_worker(worker_id)

    def get_preference(self, key: str) -> bool | None:
        return self._require_settings_store().get_preference(key)

    def set_preference(self, key: str, value: bool) -> None:
        self._require_settings_store().set_preference(key, value)

    def open_job_control(
        self,
        database_path: str | Path,
        operations,
    ):
        """Open a durable job-control service honoring the supervised preference.

        The `supervised` preference defaults to ON (user decision 2026-08-22):
        native commands run under durable records, duplicate protection, and
        bounded collection. Flipping it off trades durability for raw speed.
        """
        store = self._require_settings_store()
        supervised = store.get_preference("supervised")
        if supervised is None:
            supervised = True
        from .job_control import DurableJobControlService

        return DurableJobControlService.open(
            database_path,
            operations=operations,
            control_center=self.control_center,
            supervised=supervised,
        )

    def start_worker(self, worker_id: str):
        self.apply_worker_settings_to_home(worker_id)
        return self.lifecycle.execute(worker_id, LifecycleAction.START)

    def apply_worker_settings_to_home(self, worker_id: str) -> str:
        """Materialize saved engine settings into the worker's SERENA_HOME.

        Best-effort advisory layer (like the connector brain): result codes are
        returned for logging and never block the lifecycle start.
        """
        if not isinstance(worker_id, str) or not worker_id.strip():
            return "SKIPPED_NO_SETTINGS"
        store = self.settings_store
        if store is None:
            return "SKIPPED_NO_SETTINGS"
        try:
            settings = store.get_worker_settings(worker_id)
        except Exception:
            return "SKIPPED_NO_SETTINGS"
        if settings is None:
            return "SKIPPED_NO_SETTINGS"
        try:
            config = store.get_worker_config(worker_id)
        except Exception:
            config = None
        if config is None:
            return "SKIPPED_NOT_CONFIGURED"
        instance_root = Path(config.instance_root).expanduser().resolve(strict=False)
        serena_home = Path(config.serena_home).expanduser().resolve(strict=False)
        if instance_root not in serena_home.parents:
            return "SKIPPED_TARGET_UNSAFE"
        project_path = settings.project_path
        if project_path is None:
            row = next(
                (
                    candidate
                    for candidate in self.control_center.snapshot().workers
                    if candidate.worker_id == worker_id
                ),
                None,
            )
            project_path = row.project_root_path if row is not None else None
        rendered = settings.render_serena_config(project_path=project_path)
        serena_home.mkdir(parents=True, exist_ok=True)
        temp_path = serena_home / ".serena_config.materialize.tmp"
        temp_path.write_text(rendered, encoding="utf-8", newline="\n")
        os.replace(temp_path, serena_home / "serena_config.yml")
        return "APPLIED"

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

    def rebind_instance(self, instance_name: str, new_project_root: str) -> str:
        """Rebind a connector to a different project (backed up, confined)."""
        from .instance_rebind import rebind_instance_project

        target = next(
            (item for item in self.instances() if item.name == instance_name), None
        )
        if target is None:
            raise SerenaConfigStoreError("INSTANCE_NOT_FOUND")
        try:
            return rebind_instance_project(target, self.instances_root, new_project_root)
        except RuntimeError as exc:
            raise SerenaConfigStoreError(str(exc)) from exc

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

    def stop_all_instances(self) -> list[tuple[str, bool]]:
        """Stop every running connector; one failure never blocks the rest."""
        from .local_instances import instance_health_state

        with self._pending_instance_starts_lock:
            pending_starts = set(self._pending_instance_starts)
        results: list[tuple[str, bool]] = []
        for instance in self.instances():
            force = instance.name in pending_starts
            if not force:
                try:
                    state = instance_health_state(instance)
                except Exception:
                    state = None
                if state is InstanceHealthState.STOPPED:
                    continue
            try:
                outcome = (
                    self._orchestrator().stop(instance, force=True)
                    if force
                    else self.instance_action(instance.name, "stop")
                )
                ok = outcome.result_code in {
                    InstanceResultCode.STOPPED,
                    InstanceResultCode.ALREADY_STOPPED,
                }
                results.append((instance.name, ok))
            except Exception:
                results.append((instance.name, False))
            finally:
                if force:
                    with self._pending_instance_starts_lock:
                        self._pending_instance_starts.discard(instance.name)
        return results

    def create_instance(
        self, name: str, project_path: str | Path, tunnel_id: str | None = None
    ):
        """Materialize a new connector instance from a validated reference."""
        from .instance_create import InstanceCreateError, create_instance, next_health_port

        current = self.instances()
        port = next_health_port(current)
        reference = current[0].instance_root if current else None
        created_root = create_instance(
            self.instances_root,
            name,
            project_path,
            health_port=port,
            tunnel_id=tunnel_id,
            reference_root=reference,
        )
        for instance in self.instances():
            if instance.instance_root == created_root.resolve(strict=False):
                return instance
        raise InstanceCreateError("CREATE_VERIFY_FAILED")

    def instance_states(self) -> tuple[tuple[LocalInstance, InstanceHealthState], ...]:
        return tuple(
            (instance, instance_health_state(instance))
            for instance in self.instances()
        )

    def connector_recovery_record(
        self, instance_name: str
    ) -> ConnectorRecoveryRecord | None:
        store = self.settings_store
        if store is None:
            return None
        try:
            return store.get_connector_recovery(instance_name)
        except (SerenaConfigStoreError, ValueError):
            return None

    def drain_connector_recovery_events(self) -> tuple[ConnectorRecoveryRecord, ...]:
        with self._connector_recovery_events_lock:
            events = tuple(self._connector_recovery_events)
            self._connector_recovery_events.clear()
        return events

    def instance_states_cancellable(
        self, *, cancel_check: Callable[[], bool]
    ) -> tuple[tuple[LocalInstance, InstanceHealthState], ...]:
        """Read connector states and reconcile recovery on the existing health loop."""
        states: list[tuple[LocalInstance, InstanceHealthState]] = []
        for instance in self.instances():
            if cancel_check():
                break
            health = instance_health_state(instance)
            if cancel_check():
                break
            if self.settings_store is not None:
                record = self.reconcile_instance_recovery(
                    instance.name, health, cancel_check=cancel_check
                )
                if cancel_check():
                    break
                if (
                    health is InstanceHealthState.STOPPED
                    and record.state is ConnectorRecoveryState.READY
                ):
                    health = InstanceHealthState.READY
            states.append((instance, health))
        return tuple(states)

    def _orchestrator(self) -> LocalInstanceOrchestrator:
        if self._instance_orchestrator is None:
            self._instance_orchestrator = LocalInstanceOrchestrator(
                instances_root=self.instances_root,
                brain_settings_provider=self._global_brain_provider,
            )
        return self._instance_orchestrator

    def _connector_intent_lock(self, instance_name: str):
        name = instance_name.strip()
        with self._connector_intent_locks_guard:
            lock = self._connector_intent_locks.get(name)
            if lock is None:
                lock = Lock()
                self._connector_intent_locks[name] = lock
            return lock

    def _recovery_orchestrator(self) -> ConnectorRecoveryCoordinator:
        if self._connector_recovery is None:
            store = self._require_settings_store()
            self._connector_recovery = ConnectorRecoveryCoordinator(
                store=store,
                autostart_check=store.get_instance_autostart,
                start_instance=self._start_instance_for_recovery,
                clock_fn=time.time,
            )
        return self._connector_recovery

    def _start_instance_for_recovery(
        self, instance_name: str, *, cancel_check: Callable[[], bool] | None = None
    ) -> InstanceOrchestrationOutcome:
        target = next(
            (item for item in self.instances() if item.name == instance_name), None
        )
        if target is None:
            raise SerenaConfigStoreError("INSTANCE_NOT_FOUND")
        if cancel_check is None:
            return self._orchestrator().start(target)
        return self._orchestrator().start(target, cancel_check=cancel_check)

    def reconcile_instance_recovery(
        self,
        instance_name: str,
        health: InstanceHealthState,
        *,
        reason_code: str = "UNEXPECTED_STOPPED",
        cancel_check: Callable[[], bool] | None = None,
    ) -> ConnectorRecoveryRecord:
        with self._connector_intent_lock(instance_name):
            record = self._recovery_orchestrator().observe(
                instance_name,
                health,
                reason_code=reason_code,
                cancel_check=cancel_check,
            )
            if (
                health is InstanceHealthState.STOPPED
                and record.state is ConnectorRecoveryState.READY
            ):
                with self._connector_recovery_events_lock:
                    self._connector_recovery_events.append(record)
            return record

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
        with self._connector_intent_lock(instance_name):
            orchestrator = self._orchestrator()
            if action == "start":
                if self.settings_store is not None:
                    self._recovery_orchestrator().manual_start(instance_name)
                return orchestrator.start(target)
            if self.settings_store is not None:
                self._recovery_orchestrator().suppress(instance_name)
            return orchestrator.stop(target)

    def instance_action_cancellable(
        self,
        instance_name: str,
        action: str,
        *,
        cancel_check: Callable[[], bool],
    ) -> InstanceOrchestrationOutcome:
        """Run a connector action with cooperative cancellation for startup."""
        if not isinstance(instance_name, str) or not instance_name.strip():
            raise SerenaConfigStoreError("INSTANCE_NAME_INVALID")
        if action not in ("start", "stop"):
            raise SerenaConfigStoreError("INSTANCE_ACTION_INVALID")
        target = next(
            (item for item in self.instances() if item.name == instance_name), None
        )
        if target is None:
            raise SerenaConfigStoreError("INSTANCE_NOT_FOUND")
        with self._connector_intent_lock(instance_name):
            orchestrator = self._orchestrator()
            if action == "start":
                if self.settings_store is not None:
                    self._recovery_orchestrator().manual_start(instance_name)
                with self._pending_instance_starts_lock:
                    self._pending_instance_starts.add(instance_name)
                keep_pending = False
                try:
                    outcome = orchestrator.start(target, cancel_check=cancel_check)
                    keep_pending = (
                        outcome.result_code
                        in {
                            InstanceResultCode.START_CANCELLED,
                            InstanceResultCode.STARTED_NOT_READY,
                        }
                        and outcome.process_launched
                    )
                    return outcome
                finally:
                    if not keep_pending:
                        with self._pending_instance_starts_lock:
                            self._pending_instance_starts.discard(instance_name)
            if self.settings_store is not None:
                self._recovery_orchestrator().suppress(instance_name)
            return orchestrator.stop(target)

    def set_instance_autostart(self, instance_name: str, enabled: bool) -> None:
        self._require_settings_store().set_instance_autostart(instance_name, enabled)

    def instance_autostart(self, instance_name: str) -> bool:
        return self._require_settings_store().get_instance_autostart(instance_name)

    def autostart_instance_names(self) -> tuple[str, ...]:
        return self._require_settings_store().list_instance_autostart()

    def rename_instance(self, instance_name: str, display_name: str) -> str:
        """Store a UI display alias for a connector (folder identity unchanged)."""
        return self._require_settings_store().set_instance_display_name(
            instance_name, display_name
        )

    def instance_aliases(self) -> dict[str, str]:
        store = self._require_settings_store()
        return store.instance_display_names()

    def delete_instance(
        self, instance_name: str, *, backup_dir: str | Path | None = None
    ) -> Path:
        """Stop (if needed), zip-backup, and remove a connector instance."""
        from datetime import datetime

        from .instance_delete import InstanceManageError, zip_directory
        from .local_instances import instance_health_state

        target = next(
            (item for item in self.instances() if item.name == instance_name), None
        )
        if target is None:
            raise InstanceManageError("INSTANCE_NOT_FOUND")

        state = instance_health_state(target)
        if state is not InstanceHealthState.STOPPED:
            try:
                outcome = self.instance_action(instance_name, "stop")
            except Exception as exc:
                raise InstanceManageError("INSTANCE_STOP_REQUIRED") from exc
            if getattr(outcome, "result_code", None) not in (
                InstanceResultCode.STOPPED,
                InstanceResultCode.ALREADY_STOPPED,
            ):
                after = instance_health_state(target)
                if after is not InstanceHealthState.STOPPED:
                    raise InstanceManageError("INSTANCE_STOP_REQUIRED")

        instance_root = target.instance_root.resolve(strict=False)
        root = Path(self.instances_root).resolve(strict=False)
        if root not in instance_root.parents:
            raise InstanceManageError("INSTANCE_OUTSIDE_ROOT")

        if backup_dir is None:
            backup_dir = default_backup_dir()
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        zip_path = zip_directory(
            instance_root, Path(backup_dir) / f"{instance_root.name}-{stamp}.zip"
        )
        if not zip_path.is_file():
            raise InstanceManageError("INSTANCE_BACKUP_FAILED")

        import shutil

        try:
            shutil.rmtree(instance_root)
        except OSError as exc:
            raise InstanceManageError("INSTANCE_DELETE_FAILED") from exc

        store = self.settings_store
        if store is not None:
            try:
                store.clear_instance_flags(instance_name)
                store.clear_instance_display_name(instance_name)
            except Exception:
                pass  # rows are inert once the folder is gone
        return zip_path
