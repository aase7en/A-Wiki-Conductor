from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.control_center import ControlCenterService
from a_conductor.control_events import SQLiteControlEventLog
from a_conductor.domain import WorkerState
from a_conductor.lifecycle import LifecycleAction
from a_conductor.lifecycle_assembly import (
    ControlCenterAssignmentService,
    LocalLifecycleContextProvider,
    LocalSerenaBackendFactory,
    SQLiteLifecycleEvidenceService,
    build_local_lifecycle_coordinator,
)
from a_conductor.lifecycle_executor import LifecycleExecutionState
from a_conductor.persistence import SQLiteRegistryStore
from a_conductor.project_identity import GitProjectIdentityVerifier
from a_conductor.runtime_safety import (
    PortBindingState,
    ProcessObservation,
    ProcessOwnership,
    TunnelBindingState,
    WorktreeBindingState,
)
from a_conductor.serena_config_store import LocalReferencePath, SQLiteSerenaConfigStore
from a_conductor.serena_lifecycle_backend import SerenaLifecycleBackend, SerenaOperationResult
from a_conductor.serena_runtime import ProjectIdentityPolicy, SerenaProjectBinding, SerenaWorkerConfig
from a_conductor.windows_observer import (
    HealthProbeObservation,
    HealthProbeState,
    PidMetadataObservation,
    PidMetadataStatus,
)


class FakeObserver:
    def __init__(self) -> None:
        self.metadata = PidMetadataObservation(PidMetadataStatus.ABSENT, None)
        self.process = ProcessObservation(True, 4321, True, True, True)
        self.port = PortBindingState.FREE
        self.health = HealthProbeObservation(HealthProbeState.NOT_READY, None, None)

    def read_pid_metadata(self, pid_path: Path):
        return self.metadata

    def observe_process(self, *, pid: int, expected_executable_name: str, expected_profile_marker: str):
        return ProcessObservation(
            True,
            pid,
            self.process.process_exists,
            self.process.executable_matches,
            self.process.profile_matches,
        )

    def observe_port_binding(self, *, port: int, expected_pid: int | None):
        return self.port

    def probe_ready(self, *, health_host: str, health_port: int, timeout_seconds: int):
        return self.health


class FakeIdentityVerifier:
    def __init__(self, success: bool = True) -> None:
        self.success = success
        self.calls = []

    def verify(self, binding):
        self.calls.append(binding.project_id)
        return SerenaOperationResult(
            success=self.success,
            error_code=None if self.success else "PROJECT_IDENTITY_FAILED",
        )


class FakeProcessController:
    def start(self, spec):
        raise AssertionError("must not start in assembly tests")

    def stop(self, spec):
        raise AssertionError("must not stop in assembly tests")


class FakePreflight:
    def run(self, materialized):
        return SerenaOperationResult(success=True)


def setup_configured_service(tmp_path: Path):
    database = tmp_path / "control.sqlite"
    service = ControlCenterService.open(SQLiteRegistryStore(database))
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    project = service.register_project(project_dir, display_name="Project")
    service.assign_project("a-worker-01", project.project_id, mutation_allowed=True)

    root = tmp_path / "worker-01"
    external = tmp_path / "bin"
    external.mkdir()
    executable = external / "tunnel-client.exe"
    executable.write_bytes(b"dummy")
    template = root / "profiles" / "runtime.yaml.template"
    template.parent.mkdir(parents=True)
    template.write_text("tunnel: __TUNNEL_ID__\n", encoding="utf-8")
    home = root / "serena-home"
    home.mkdir(parents=True)
    (home / "serena_config.yml").write_text("test: true\n", encoding="utf-8")

    worker = SerenaWorkerConfig(
        worker_id="a-worker-01",
        runtime_id="runtime-01",
        instance_root=str(root.resolve()),
        serena_home=str(home.resolve()),
        health_host="127.0.0.1",
        health_port=18131,
        tunnel_binding_ref="tunnel-ref-01",
        credential_ref="credential-ref-01",
        runtime_executable_ref=str(executable.resolve()),
        profile_template_ref=str(template.resolve()),
        run_dir=str((root / "run").resolve()),
        log_dir=str((root / "logs").resolve()),
        startup_timeout_seconds=3,
        stop_timeout_seconds=3,
    )
    binding = SerenaProjectBinding(
        project_id=project.project_id,
        worktree_path=str(project_dir.resolve()),
        identity_policy=ProjectIdentityPolicy.NO_GIT,
        expected_branch=None,
        expected_head=None,
        mutation_allowed=True,
    )
    refs = tmp_path / "refs"
    refs.mkdir()
    ref_file = refs / "tunnel-id.txt"
    ref_file.write_text("test-tunnel-id", encoding="utf-8")

    config_store = SQLiteSerenaConfigStore(database)
    config_store.save_worker_config(worker)
    config_store.save_project_binding(binding)
    config_store.save_local_reference(
        LocalReferencePath("tunnel-ref-01", str(ref_file.resolve()), str(refs.resolve()))
    )
    return database, service, config_store, project, worker, binding


def test_context_provider_observes_stopped_assigned_worker(tmp_path: Path) -> None:
    _, service, config_store, _, worker, _ = setup_configured_service(tmp_path)
    observer = FakeObserver()
    provider = LocalLifecycleContextProvider(
        service=service,
        config_store=config_store,
        observer=observer,
        project_identity_service=FakeIdentityVerifier(),
    )

    context = provider.observe("a-worker-01", LifecycleAction.START)

    assert context.action is LifecycleAction.START
    assert context.worker_state is WorkerState.STOPPED
    assert context.assignment_present is True
    assert context.project_exists is True
    assert context.process_ownership is ProcessOwnership.ABSENT
    assert context.port_binding is PortBindingState.FREE
    assert context.tunnel_required is True
    assert context.tunnel_binding is TunnelBindingState.FREE
    assert context.worktree_binding is WorktreeBindingState.OWNED
    assert context.ready is False
    assert context.project_identity_ok is True
    assert context.active_task is False


def test_context_provider_marks_owned_ready_runtime(tmp_path: Path) -> None:
    _, service, config_store, _, _, _ = setup_configured_service(tmp_path)
    service.set_worker_state("a-worker-01", WorkerState.READY)
    observer = FakeObserver()
    observer.metadata = PidMetadataObservation(PidMetadataStatus.VALID, 4321)
    observer.port = PortBindingState.OWNED
    observer.health = HealthProbeObservation(HealthProbeState.READY, 200, None)
    provider = LocalLifecycleContextProvider(
        service=service,
        config_store=config_store,
        observer=observer,
        project_identity_service=FakeIdentityVerifier(),
    )

    context = provider.observe("a-worker-01", LifecycleAction.STOP)

    assert context.process_ownership is ProcessOwnership.OWNED
    assert context.port_binding is PortBindingState.OWNED
    assert context.tunnel_binding is TunnelBindingState.OWNED
    assert context.ready is True


def test_duplicate_tunnel_reference_is_collision(tmp_path: Path) -> None:
    _, service, config_store, _, first, _ = setup_configured_service(tmp_path)
    second_root = tmp_path / "worker-02"
    second = SerenaWorkerConfig(
        worker_id="a-worker-02",
        runtime_id="runtime-02",
        instance_root=str(second_root.resolve()),
        serena_home=str((second_root / "serena-home").resolve()),
        health_host="127.0.0.1",
        health_port=18132,
        tunnel_binding_ref=first.tunnel_binding_ref,
        credential_ref="credential-ref-02",
        runtime_executable_ref=first.runtime_executable_ref,
        profile_template_ref=first.profile_template_ref,
        run_dir=str((second_root / "run").resolve()),
        log_dir=str((second_root / "logs").resolve()),
        startup_timeout_seconds=3,
        stop_timeout_seconds=3,
    )
    config_store.save_worker_config(second)
    provider = LocalLifecycleContextProvider(
        service=service,
        config_store=config_store,
        observer=FakeObserver(),
        project_identity_service=FakeIdentityVerifier(),
    )
    context = provider.observe("a-worker-01", LifecycleAction.START)
    assert context.tunnel_binding is TunnelBindingState.COLLISION


def test_backend_factory_builds_serena_backend_from_persisted_metadata(tmp_path: Path) -> None:
    database, service, config_store, _, _, _ = setup_configured_service(tmp_path)
    factory = LocalSerenaBackendFactory(
        service=service,
        config_store=config_store,
        observer=FakeObserver(),
        process_controller=FakeProcessController(),
        preflight_service=FakePreflight(),
        project_identity_service=FakeIdentityVerifier(),
        event_log=SQLiteControlEventLog(database),
    )

    backend = factory.create("a-worker-01", LifecycleAction.START)

    assert isinstance(backend, SerenaLifecycleBackend)
    assert backend.execute_step.__self__ is backend


def test_assignment_service_delegates_release_to_control_center(tmp_path: Path) -> None:
    _, service, _, project, _, _ = setup_configured_service(tmp_path)
    adapter = ControlCenterAssignmentService(service)
    result = adapter.clear("a-worker-01", project.project_id)
    assert result.success is True
    row = next(w for w in service.snapshot().workers if w.worker_id == "a-worker-01")
    assert row.assignment_id is None


def test_assignment_service_refuses_project_identity_mismatch(tmp_path: Path) -> None:
    _, service, _, _, _, _ = setup_configured_service(tmp_path)
    adapter = ControlCenterAssignmentService(service)

    result = adapter.clear("a-worker-01", "wrong-project-id")

    assert result == SerenaOperationResult(
        success=False,
        error_code="ASSIGNMENT_IDENTITY_MISMATCH",
        recovery_required=True,
    )
    row = next(w for w in service.snapshot().workers if w.worker_id == "a-worker-01")
    assert row.assignment_id is not None


def test_evidence_service_returns_append_only_event_ref(tmp_path: Path) -> None:
    log = SQLiteControlEventLog(
        tmp_path / "control.sqlite",
        event_id_factory=lambda: "event-assembly-1",
    )
    service = SQLiteLifecycleEvidenceService(log, LifecycleAction.START)
    result = service.emit("a-worker-01", "project-1")
    assert result == SerenaOperationResult(success=True, evidence_ref="event-assembly-1")
    assert log.get("event-assembly-1").event_type == "START"


def test_local_coordinator_builder_refuses_unassigned_worker_without_backend(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    service = ControlCenterService.open(SQLiteRegistryStore(database))
    config_store = SQLiteSerenaConfigStore(database)
    coordinator = build_local_lifecycle_coordinator(
        database,
        service=service,
        config_store=config_store,
        observer=FakeObserver(),
        project_identity_service=FakeIdentityVerifier(),
        process_controller=FakeProcessController(),
        preflight_service=FakePreflight(),
    )

    result = coordinator.execute("a-worker-01", LifecycleAction.START)

    assert result.state is LifecycleExecutionState.REFUSED
    assert result.reason_code == "ASSIGNMENT_MISSING"
