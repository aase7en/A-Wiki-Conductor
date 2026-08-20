from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.owned_process import (
    OwnedProcessMutationResult,
    OwnedProcessMutationState,
)
from a_conductor.runtime_safety import PortBindingState, ProcessObservation
from a_conductor.serena_lifecycle_backend import SerenaOperationResult
from a_conductor.serena_materializer import SerenaRuntimeMaterializer
from a_conductor.serena_operations import BoundSerenaLifecycleOperations
from a_conductor.serena_runtime import (
    ProjectIdentityPolicy,
    SerenaProjectBinding,
    SerenaWorkerConfig,
)
from a_conductor.windows_observer import (
    HealthProbeObservation,
    HealthProbeState,
    PidMetadataObservation,
    PidMetadataStatus,
)


def make_worker(tmp_path: Path, *, startup_timeout_seconds: int = 2) -> SerenaWorkerConfig:
    root = tmp_path / "worker"
    home = root / "serena-home"
    home.mkdir(parents=True, exist_ok=True)
    (home / "serena_config.yml").write_text("test: true\n", encoding="utf-8")
    external = tmp_path / "external"
    external.mkdir(parents=True, exist_ok=True)
    executable = external / "tunnel-client.exe"
    executable.write_bytes(b"test")
    template = external / "runtime.yaml.template"
    template.write_text(
        "tunnel: __TUNNEL_ID__\nproject: __PROJECT_PATH__\n",
        encoding="utf-8",
    )
    return SerenaWorkerConfig(
        worker_id="a-worker-test",
        runtime_id="runtime-test",
        instance_root=str(root),
        serena_home=str(home),
        health_host="127.0.0.1",
        health_port=18101,
        tunnel_binding_ref="binding-ref",
        credential_ref="credential-ref",
        runtime_executable_ref=str(executable),
        profile_template_ref=str(template),
        run_dir=str(root / "run"),
        log_dir=str(root / "logs"),
        startup_timeout_seconds=startup_timeout_seconds,
        stop_timeout_seconds=3,
    )


def make_binding(tmp_path: Path, *, create: bool = True) -> SerenaProjectBinding:
    worktree = tmp_path / "project"
    if create:
        worktree.mkdir(parents=True, exist_ok=True)
    return SerenaProjectBinding(
        project_id="project-test",
        worktree_path=str(worktree),
        identity_policy=ProjectIdentityPolicy.EXACT,
        expected_branch="main",
        expected_head="abc123",
        mutation_allowed=True,
    )


class FakeObserver:
    def __init__(self) -> None:
        self.metadata = PidMetadataObservation(PidMetadataStatus.ABSENT, None)
        self.process = ProcessObservation(True, 4321, True, True, True)
        self.port_states = [PortBindingState.FREE]
        self.health_states = [
            HealthProbeObservation(HealthProbeState.READY, 200, None)
        ]
        self.calls: list[tuple[str, object]] = []

    def read_pid_metadata(self, pid_path: Path) -> PidMetadataObservation:
        self.calls.append(("pid", pid_path))
        return self.metadata

    def observe_process(self, *, pid: int, expected_executable_name: str, expected_profile_marker: str):
        self.calls.append(("process", pid))
        return ProcessObservation(
            True,
            pid,
            self.process.process_exists,
            self.process.executable_matches,
            self.process.profile_matches,
        )

    def observe_port_binding(self, *, port: int, expected_pid: int | None):
        self.calls.append(("port", (port, expected_pid)))
        if len(self.port_states) > 1:
            return self.port_states.pop(0)
        return self.port_states[0]

    def probe_ready(self, *, health_host: str, health_port: int, timeout_seconds: int):
        self.calls.append(("ready", (health_host, health_port, timeout_seconds)))
        if len(self.health_states) > 1:
            return self.health_states.pop(0)
        return self.health_states[0]


class FakeProcessController:
    def __init__(self) -> None:
        self.start_result = OwnedProcessMutationResult(
            OwnedProcessMutationState.STARTED, "STARTED", 4321
        )
        self.stop_result = OwnedProcessMutationResult(
            OwnedProcessMutationState.STOPPED, "STOPPED", 4321
        )
        self.starts = []
        self.stops = []

    def start(self, spec):
        self.starts.append(spec)
        return self.start_result

    def stop(self, spec):
        self.stops.append(spec)
        return self.stop_result


class FakeTokenProvider:
    def __init__(self, values: dict[str, str]) -> None:
        self.values = values
        self.calls = 0
        self.raise_error = False

    def resolve(self, worker, binding):
        self.calls += 1
        if self.raise_error:
            raise RuntimeError("secret tunnel token should not leak")
        return dict(self.values)


class FakeBoundary:
    def __init__(self, result: SerenaOperationResult | None = None) -> None:
        self.result = result or SerenaOperationResult(success=True)
        self.calls = []

    def verify_available(self, worker):
        self.calls.append(("available", worker.worker_id))
        return self.result

    def verify_released(self, worker):
        self.calls.append(("released", worker.worker_id))
        return self.result

    def run(self, materialized):
        self.calls.append(("preflight", materialized.profile_path))
        return self.result

    def verify(self, binding):
        self.calls.append(("identity", binding.project_id))
        return self.result

    def clear(self, worker_id: str, project_id: str):
        self.calls.append(("clear", worker_id, project_id))
        return self.result

    def emit(self, worker_id: str, project_id: str):
        self.calls.append(("emit", worker_id, project_id))
        return self.result


def build_operations(tmp_path: Path, *, create_project: bool = True, clock=None):
    worker = make_worker(tmp_path)
    binding = make_binding(tmp_path, create=create_project)
    observer = FakeObserver()
    controller = FakeProcessController()
    tokens = FakeTokenProvider(
        {
            "__TUNNEL_ID__": "test-tunnel-id",
            "__PROJECT_PATH__": str(Path(binding.worktree_path).resolve()),
        }
    )
    tunnel = FakeBoundary()
    preflight = FakeBoundary()
    identity = FakeBoundary()
    assignment = FakeBoundary()
    evidence = FakeBoundary()
    operations = BoundSerenaLifecycleOperations(
        worker=worker,
        binding=binding,
        observer=observer,
        materializer=SerenaRuntimeMaterializer(),
        process_controller=controller,
        token_provider=tokens,
        tunnel_guard=tunnel,
        preflight_service=preflight,
        project_identity_service=identity,
        assignment_service=assignment,
        evidence_service=evidence,
        monotonic=clock,
        sleeper=lambda _: None,
    )
    return (
        operations,
        worker,
        binding,
        observer,
        controller,
        tokens,
        tunnel,
        preflight,
        identity,
        assignment,
        evidence,
    )


def test_verify_assignment_missing_project_fails_without_mutation(tmp_path: Path) -> None:
    operations, worker, *_ = build_operations(tmp_path, create_project=False)

    result = operations.verify_assignment()

    assert result.success is False
    assert result.error_code == "PROJECT_NOT_FOUND"
    assert not Path(worker.run_dir).exists()


def test_verify_resources_succeeds_when_pid_absent_port_free_and_tunnel_available(tmp_path: Path) -> None:
    operations, worker, _, observer, _, _, tunnel, *_ = build_operations(tmp_path)

    result = operations.verify_resources()

    assert result.success is True
    assert ("port", (worker.health_port, None)) in observer.calls
    assert tunnel.calls == [("available", worker.worker_id)]
    assert not Path(worker.run_dir).exists()


def test_verify_resources_port_collision_fails_closed(tmp_path: Path) -> None:
    operations, _, _, observer, *_ = build_operations(tmp_path)
    observer.port_states = [PortBindingState.COLLISION]

    result = operations.verify_resources()

    assert result.success is False
    assert result.error_code == "PORT_IN_USE"


def test_verify_resources_stale_pid_requires_recovery(tmp_path: Path) -> None:
    operations, _, _, observer, *_ = build_operations(tmp_path)
    observer.metadata = PidMetadataObservation(PidMetadataStatus.VALID, 4321)
    observer.process = ProcessObservation(True, 4321, False, None, None)

    result = operations.verify_resources()

    assert result.success is False
    assert result.error_code == "STALE_PID_METADATA"
    assert result.recovery_required is True


def test_render_then_start_uses_materialized_exact_owned_spec(tmp_path: Path) -> None:
    operations, worker, _, _, controller, tokens, *_ = build_operations(tmp_path)

    rendered = operations.render_profile()
    started = operations.start_owned_process()

    assert rendered.success is True
    assert started.state is OwnedProcessMutationState.STARTED
    assert tokens.calls == 1
    assert len(controller.starts) == 1
    spec = controller.starts[0]
    assert spec.expected_profile_marker == str(Path(worker.run_dir).resolve() / "runtime-profile.yaml")
    assert spec.environment_overrides == (("SERENA_HOME", str(Path(worker.serena_home).resolve())),)


def test_start_without_materialize_requires_recovery(tmp_path: Path) -> None:
    operations, *_ = build_operations(tmp_path)

    result = operations.start_owned_process()

    assert result.state is OwnedProcessMutationState.RECOVERY_REQUIRED
    assert result.reason_code == "RUNTIME_NOT_MATERIALIZED"


def test_targeted_stop_after_restart_reconstructs_spec_without_token_resolution(tmp_path: Path) -> None:
    operations, worker, _, _, controller, tokens, *_ = build_operations(tmp_path)

    result = operations.targeted_stop()

    assert result.state is OwnedProcessMutationState.STOPPED
    assert tokens.calls == 0
    assert len(controller.stops) == 1
    spec = controller.stops[0]
    assert spec.expected_profile_marker == str(Path(worker.run_dir).resolve() / "runtime-profile.yaml")


def test_wait_ready_requires_owned_process_owned_port_and_http_ready(tmp_path: Path) -> None:
    operations, worker, _, observer, *_ = build_operations(tmp_path)
    Path(worker.run_dir).mkdir(parents=True, exist_ok=True)
    (Path(worker.run_dir) / "runtime.pid").write_text("4321", encoding="utf-8")
    observer.metadata = PidMetadataObservation(PidMetadataStatus.VALID, 4321)
    observer.port_states = [PortBindingState.OWNED]
    observer.health_states = [HealthProbeObservation(HealthProbeState.READY, 200, None)]

    result = operations.wait_ready()

    assert result.success is True


def test_wait_ready_timeout_requires_recovery(tmp_path: Path) -> None:
    clock_values = iter([0.0, 0.0, 3.0, 3.0])
    operations, worker, _, observer, *_ = build_operations(
        tmp_path,
        clock=lambda: next(clock_values),
    )
    Path(worker.run_dir).mkdir(parents=True, exist_ok=True)
    (Path(worker.run_dir) / "runtime.pid").write_text("4321", encoding="utf-8")
    observer.metadata = PidMetadataObservation(PidMetadataStatus.VALID, 4321)
    observer.port_states = [PortBindingState.OWNED]
    observer.health_states = [
        HealthProbeObservation(HealthProbeState.NOT_READY, None, "not-ready")
    ]

    result = operations.wait_ready()

    assert result.success is False
    assert result.error_code == "STARTUP_TIMEOUT"
    assert result.recovery_required is True


def test_wait_exit_requires_absent_pid_and_free_port(tmp_path: Path) -> None:
    operations, _, _, observer, *_ = build_operations(tmp_path)
    observer.metadata = PidMetadataObservation(PidMetadataStatus.ABSENT, None)
    observer.port_states = [PortBindingState.FREE]

    result = operations.wait_exit()

    assert result.success is True


def test_verify_released_includes_tunnel_release_check(tmp_path: Path) -> None:
    operations, _, _, observer, _, _, tunnel, *_ = build_operations(tmp_path)
    observer.metadata = PidMetadataObservation(PidMetadataStatus.ABSENT, None)
    observer.port_states = [PortBindingState.FREE]
    tunnel.result = SerenaOperationResult(
        success=False,
        error_code="TUNNEL_STILL_OWNED",
        recovery_required=True,
    )

    result = operations.verify_released()

    assert result == tunnel.result


def test_injected_boundaries_are_delegated_explicitly(tmp_path: Path) -> None:
    operations, _, binding, _, _, _, _, preflight, identity, assignment, evidence = build_operations(tmp_path)
    assert operations.render_profile().success is True

    assert operations.preflight().success is True
    assert operations.verify_project_identity().success is True
    assert operations.clear_assignment().success is True
    assert operations.emit_evidence().success is True

    assert preflight.calls and preflight.calls[0][0] == "preflight"
    assert identity.calls == [("identity", binding.project_id)]
    assert assignment.calls == [("clear", "a-worker-test", binding.project_id)]
    assert evidence.calls == [("emit", "a-worker-test", binding.project_id)]


def test_token_provider_exception_is_redacted(tmp_path: Path) -> None:
    operations, _, _, _, _, tokens, *_ = build_operations(tmp_path)
    tokens.raise_error = True

    result = operations.render_profile()

    assert result.success is False
    assert result.error_code == "PROFILE_TOKEN_RESOLUTION_FAILED"
    assert "secret tunnel token" not in repr(result)
