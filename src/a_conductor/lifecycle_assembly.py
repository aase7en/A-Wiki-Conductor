"""Local assembly of persisted Control Center state into lifecycle boundaries."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .control_center import ControlCenterError, ControlCenterService, WorkerScreenRow
from .control_events import ControlEventLogError, SQLiteControlEventLog
from .lifecycle import LifecycleAction, LifecycleContext
from .lifecycle_coordinator import LifecycleCoordinator
from .lifecycle_journal import SQLiteLifecycleJournal
from .owned_process import WindowsOwnedProcessController
from .persistence import SQLiteRegistryStore
from .project_identity import GitProjectIdentityVerifier
from .runtime_safety import (
    PortBindingState,
    ProcessOwnership,
    TunnelBindingState,
    WorktreeBindingState,
    classify_process_ownership,
    classify_worktree_binding,
)
from .serena_config_store import SQLiteSerenaConfigStore
from .serena_lifecycle_backend import SerenaLifecycleBackend, SerenaOperationResult
from .serena_materializer import SerenaMaterializationError, SerenaRuntimeMaterializer
from .serena_operations import BoundSerenaLifecycleOperations
from .tunnel_boundaries import (
    LocalFileReferenceStore,
    LocalTunnelOwnershipGuard,
    ReferenceBackedSerenaTokenProvider,
    StrictTunnelClientPreflightService,
)
from .windows_io import LoopbackReadyzHttpProbe, StrictPowerShellInspectionRunner
from .windows_observer import (
    HealthProbeState,
    PidMetadataStatus,
    WindowsRuntimeObserver,
)
from .registry import windows_worktree_key


class LifecycleAssemblyError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ProjectIdentityService(Protocol):
    def verify(self, binding) -> SerenaOperationResult: ...


class PreflightService(Protocol):
    def run(self, materialized) -> SerenaOperationResult: ...


class ProcessController(Protocol):
    def start(self, spec): ...

    def stop(self, spec): ...


def _find_worker_row(service: ControlCenterService, worker_id: str) -> WorkerScreenRow:
    for worker in service.snapshot().workers:
        if worker.worker_id == worker_id:
            return worker
    raise LifecycleAssemblyError("WORKER_NOT_FOUND")


class LocalLifecycleContextProvider:
    def __init__(
        self,
        *,
        service: ControlCenterService,
        config_store: SQLiteSerenaConfigStore,
        observer,
        project_identity_service: ProjectIdentityService,
        materializer: SerenaRuntimeMaterializer | None = None,
    ) -> None:
        self._service = service
        self._config_store = config_store
        self._observer = observer
        self._identity = project_identity_service
        self._materializer = materializer or SerenaRuntimeMaterializer()

    def _unassigned_context(
        self,
        row: WorkerScreenRow,
        action: LifecycleAction,
    ) -> LifecycleContext:
        return LifecycleContext(
            action=action,
            worker_state=row.state,
            assignment_present=False,
            project_exists=False,
            process_ownership=ProcessOwnership.ABSENT,
            port_binding=PortBindingState.FREE,
            tunnel_required=False,
            tunnel_binding=TunnelBindingState.FREE,
            worktree_binding=WorktreeBindingState.AVAILABLE,
            project_identity_ok=None,
            ready=False,
            active_task=False,
        )

    def observe(self, worker_id: str, action: LifecycleAction) -> LifecycleContext:
        snapshot = self._service.snapshot()
        row = next((item for item in snapshot.workers if item.worker_id == worker_id), None)
        if row is None:
            raise LifecycleAssemblyError("WORKER_NOT_FOUND")
        if row.assignment_id is None or row.project_id is None:
            return self._unassigned_context(row, action)

        worker = self._config_store.get_worker_config(worker_id)
        binding = self._config_store.get_project_binding(row.project_id)
        if worker is None:
            raise LifecycleAssemblyError("WORKER_CONFIG_MISSING")
        if binding is None:
            raise LifecycleAssemblyError("PROJECT_BINDING_MISSING")

        project_path = Path(binding.worktree_path).expanduser().resolve(strict=False)
        project_exists = project_path.is_dir()
        try:
            materialized = self._materializer.describe_existing(worker)
        except SerenaMaterializationError as exc:
            raise LifecycleAssemblyError(exc.code) from exc

        metadata = self._observer.read_pid_metadata(materialized.process_spec.pid_path)
        if metadata.status is PidMetadataStatus.ABSENT:
            process_ownership = ProcessOwnership.ABSENT
        elif metadata.status is PidMetadataStatus.INVALID:
            process_ownership = ProcessOwnership.MISMATCH
        elif metadata.status is PidMetadataStatus.UNKNOWN or metadata.pid is None:
            process_ownership = ProcessOwnership.UNKNOWN
        else:
            observation = self._observer.observe_process(
                pid=metadata.pid,
                expected_executable_name=materialized.process_spec.expected_executable_name,
                expected_profile_marker=materialized.process_spec.expected_profile_marker,
            )
            process_ownership = classify_process_ownership(observation)

        expected_pid = (
            metadata.pid
            if process_ownership is ProcessOwnership.OWNED and metadata.pid is not None
            else None
        )
        port_binding = self._observer.observe_port_binding(
            port=worker.health_port,
            expected_pid=expected_pid,
        )

        tunnel_required = worker.tunnel_binding_ref is not None
        if not tunnel_required:
            tunnel_binding = TunnelBindingState.FREE
        else:
            same_ref = [
                config.worker_id
                for config in self._config_store.list_worker_configs()
                if config.tunnel_binding_ref == worker.tunnel_binding_ref
            ]
            if any(owner != worker_id for owner in same_ref):
                tunnel_binding = TunnelBindingState.COLLISION
            elif process_ownership is ProcessOwnership.OWNED:
                tunnel_binding = TunnelBindingState.OWNED
            else:
                tunnel_binding = TunnelBindingState.FREE

        active_mutating_worker_id: str | None = None
        target_key = windows_worktree_key(binding.worktree_path)
        for candidate in snapshot.workers:
            if (
                candidate.assignment_id is not None
                and candidate.project_root_path is not None
                and candidate.mutation_allowed is True
                and windows_worktree_key(candidate.project_root_path) == target_key
            ):
                active_mutating_worker_id = candidate.worker_id
                if candidate.worker_id != worker_id:
                    break
        worktree_binding = classify_worktree_binding(
            worktree_key=target_key,
            active_mutating_worker_id=active_mutating_worker_id,
            requesting_worker_id=worker_id,
        )

        identity_ok: bool | None = None
        if project_exists:
            identity_ok = bool(self._identity.verify(binding).success)

        ready: bool | None = False
        if process_ownership is ProcessOwnership.UNKNOWN or port_binding is PortBindingState.UNKNOWN:
            ready = None
        elif process_ownership is ProcessOwnership.OWNED and port_binding is PortBindingState.OWNED:
            health = self._observer.probe_ready(
                health_host=worker.health_host,
                health_port=worker.health_port,
                timeout_seconds=1,
            )
            if health.state is HealthProbeState.READY:
                ready = True
            elif health.state is HealthProbeState.NOT_READY:
                ready = False
            else:
                ready = None

        return LifecycleContext(
            action=action,
            worker_state=row.state,
            assignment_present=True,
            project_exists=project_exists,
            process_ownership=process_ownership,
            port_binding=port_binding,
            tunnel_required=tunnel_required,
            tunnel_binding=tunnel_binding,
            worktree_binding=worktree_binding,
            project_identity_ok=identity_ok,
            ready=ready,
            active_task=False,
        )


class ControlCenterAssignmentService:
    def __init__(self, service: ControlCenterService) -> None:
        self._service = service

    def clear(self, worker_id: str, project_id: str) -> SerenaOperationResult:
        row = _find_worker_row(self._service, worker_id)
        if row.project_id != project_id:
            return SerenaOperationResult(
                success=False,
                error_code="ASSIGNMENT_IDENTITY_MISMATCH",
                recovery_required=True,
            )
        try:
            self._service.release_worker(worker_id)
        except ControlCenterError as exc:
            return SerenaOperationResult(
                success=False,
                error_code=exc.code,
                recovery_required=True,
            )
        return SerenaOperationResult(success=True)


class SQLiteLifecycleEvidenceService:
    def __init__(self, event_log: SQLiteControlEventLog, action: LifecycleAction) -> None:
        self._event_log = event_log
        self._action = action

    def emit(self, worker_id: str, project_id: str) -> SerenaOperationResult:
        try:
            event = self._event_log.append(self._action.value, worker_id, project_id)
        except ControlEventLogError as exc:
            return SerenaOperationResult(
                success=False,
                error_code=exc.code,
                recovery_required=True,
            )
        return SerenaOperationResult(success=True, evidence_ref=event.event_id)


class LocalSerenaBackendFactory:
    def __init__(
        self,
        *,
        service: ControlCenterService,
        config_store: SQLiteSerenaConfigStore,
        observer,
        process_controller: ProcessController,
        preflight_service: PreflightService,
        project_identity_service: ProjectIdentityService,
        event_log: SQLiteControlEventLog,
        materializer: SerenaRuntimeMaterializer | None = None,
    ) -> None:
        self._service = service
        self._config_store = config_store
        self._observer = observer
        self._process_controller = process_controller
        self._preflight = preflight_service
        self._identity = project_identity_service
        self._event_log = event_log
        self._materializer = materializer or SerenaRuntimeMaterializer()

    def _reference_store(self, worker) -> LocalFileReferenceStore:
        references = self._config_store.list_local_references()
        mapping = {record.reference_id: Path(record.file_path) for record in references}
        roots = tuple(dict.fromkeys(Path(record.allowed_root) for record in references))
        if not roots:
            roots = (Path(worker.instance_root),)
        return LocalFileReferenceStore(mapping, allowed_roots=roots)

    def _tunnel_guard(self, requesting_worker_id: str) -> LocalTunnelOwnershipGuard:
        configs = self._config_store.list_worker_configs()
        groups: dict[str, list[str]] = {}
        for config in configs:
            if config.tunnel_binding_ref is not None:
                groups.setdefault(config.tunnel_binding_ref, []).append(config.worker_id)
        owners: dict[str, str] = {}
        for reference, worker_ids in groups.items():
            other = next((wid for wid in worker_ids if wid != requesting_worker_id), None)
            owners[reference] = other or worker_ids[0]
        return LocalTunnelOwnershipGuard(owners)

    def create(self, worker_id: str, action: LifecycleAction) -> SerenaLifecycleBackend:
        row = _find_worker_row(self._service, worker_id)
        if row.assignment_id is None or row.project_id is None:
            raise LifecycleAssemblyError("ASSIGNMENT_MISSING")
        worker = self._config_store.get_worker_config(worker_id)
        binding = self._config_store.get_project_binding(row.project_id)
        if worker is None:
            raise LifecycleAssemblyError("WORKER_CONFIG_MISSING")
        if binding is None:
            raise LifecycleAssemblyError("PROJECT_BINDING_MISSING")

        operations = BoundSerenaLifecycleOperations(
            worker=worker,
            binding=binding,
            observer=self._observer,
            materializer=self._materializer,
            process_controller=self._process_controller,
            token_provider=ReferenceBackedSerenaTokenProvider(
                self._reference_store(worker)
            ),
            tunnel_guard=self._tunnel_guard(worker_id),
            preflight_service=self._preflight,
            project_identity_service=self._identity,
            assignment_service=ControlCenterAssignmentService(self._service),
            evidence_service=SQLiteLifecycleEvidenceService(self._event_log, action),
        )
        return SerenaLifecycleBackend(operations)


def build_local_lifecycle_coordinator(
    database_path: str | Path,
    *,
    service: ControlCenterService | None = None,
    config_store: SQLiteSerenaConfigStore | None = None,
    observer=None,
    project_identity_service: ProjectIdentityService | None = None,
    process_controller: ProcessController | None = None,
    preflight_service: PreflightService | None = None,
    event_log: SQLiteControlEventLog | None = None,
) -> LifecycleCoordinator:
    database = Path(database_path)
    service = service or ControlCenterService.open(SQLiteRegistryStore(database))
    config_store = config_store or SQLiteSerenaConfigStore(database)
    if observer is None:
        observer = WindowsRuntimeObserver(
            runner=StrictPowerShellInspectionRunner(),
            http_probe=LoopbackReadyzHttpProbe(),
        )
    identity = project_identity_service or GitProjectIdentityVerifier()
    controller = process_controller or WindowsOwnedProcessController(observer=observer)
    preflight = preflight_service or StrictTunnelClientPreflightService()
    events = event_log or SQLiteControlEventLog(database)

    context_provider = LocalLifecycleContextProvider(
        service=service,
        config_store=config_store,
        observer=observer,
        project_identity_service=identity,
    )
    backend_factory = LocalSerenaBackendFactory(
        service=service,
        config_store=config_store,
        observer=observer,
        process_controller=controller,
        preflight_service=preflight,
        project_identity_service=identity,
        event_log=events,
    )
    return LifecycleCoordinator(
        context_provider=context_provider,
        backend_factory=backend_factory,
        checkpoint_sink=SQLiteLifecycleJournal(database),
        state_service=service,
    )
