"""Concrete pre-bound Serena lifecycle operations.

This module composes already-bounded collaborators. It does not construct shell
commands, resolve secret stores itself, mutate Git, or write lifecycle journals.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Mapping, Protocol

from .owned_process import (
    OwnedProcessMutationResult,
    OwnedProcessMutationState,
    WindowsOwnedProcessController,
)
from .runtime_safety import (
    PortBindingState,
    ProcessOwnership,
    classify_process_ownership,
)
from .serena_lifecycle_backend import SerenaOperationResult
from .serena_materializer import (
    SerenaMaterializationError,
    SerenaMaterializedRuntime,
    SerenaRuntimeMaterializer,
)
from .serena_runtime import SerenaProjectBinding, SerenaWorkerConfig
from .windows_observer import HealthProbeState, PidMetadataStatus, WindowsRuntimeObserver


class SerenaTokenProvider(Protocol):
    def resolve(
        self,
        worker: SerenaWorkerConfig,
        binding: SerenaProjectBinding,
    ) -> Mapping[str, str]: ...


class SerenaTunnelGuard(Protocol):
    def verify_available(self, worker: SerenaWorkerConfig) -> SerenaOperationResult: ...

    def verify_released(self, worker: SerenaWorkerConfig) -> SerenaOperationResult: ...


class SerenaPreflightService(Protocol):
    def run(self, materialized: SerenaMaterializedRuntime) -> SerenaOperationResult: ...


class SerenaProjectIdentityService(Protocol):
    def verify(self, binding: SerenaProjectBinding) -> SerenaOperationResult: ...


class SerenaAssignmentService(Protocol):
    def clear(self, worker_id: str, project_id: str) -> SerenaOperationResult: ...


class SerenaEvidenceService(Protocol):
    def emit(self, worker_id: str, project_id: str) -> SerenaOperationResult: ...


class SerenaProcessController(Protocol):
    def start(self, spec) -> OwnedProcessMutationResult: ...

    def stop(self, spec) -> OwnedProcessMutationResult: ...


class BoundSerenaLifecycleOperations:
    """Lifecycle operations bound to exactly one worker/project assignment."""

    def __init__(
        self,
        *,
        worker: SerenaWorkerConfig,
        binding: SerenaProjectBinding,
        observer: WindowsRuntimeObserver,
        materializer: SerenaRuntimeMaterializer,
        process_controller: SerenaProcessController,
        token_provider: SerenaTokenProvider,
        tunnel_guard: SerenaTunnelGuard,
        preflight_service: SerenaPreflightService,
        project_identity_service: SerenaProjectIdentityService,
        assignment_service: SerenaAssignmentService,
        evidence_service: SerenaEvidenceService,
        monotonic: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._worker = worker
        self._binding = binding
        self._observer = observer
        self._materializer = materializer
        self._process_controller = process_controller
        self._token_provider = token_provider
        self._tunnel_guard = tunnel_guard
        self._preflight_service = preflight_service
        self._project_identity_service = project_identity_service
        self._assignment_service = assignment_service
        self._evidence_service = evidence_service
        self._monotonic = monotonic or time.monotonic
        self._sleeper = sleeper or time.sleep
        self._materialized: SerenaMaterializedRuntime | None = None

    def _describe_existing(self) -> SerenaMaterializedRuntime:
        return self._materializer.describe_existing(self._worker)

    def verify_assignment(self) -> SerenaOperationResult:
        try:
            worktree = Path(self._binding.worktree_path).expanduser().resolve(strict=False)
            exists = worktree.is_dir()
        except OSError:
            exists = False
        if not exists:
            return SerenaOperationResult(success=False, error_code="PROJECT_NOT_FOUND")
        return SerenaOperationResult(success=True)

    def _process_ownership(self, materialized: SerenaMaterializedRuntime):
        metadata = self._observer.read_pid_metadata(materialized.process_spec.pid_path)
        if metadata.status is PidMetadataStatus.ABSENT:
            return metadata, ProcessOwnership.ABSENT
        if metadata.status is PidMetadataStatus.INVALID:
            return metadata, ProcessOwnership.MISMATCH
        if metadata.status is PidMetadataStatus.UNKNOWN:
            return metadata, ProcessOwnership.UNKNOWN
        assert metadata.pid is not None
        observation = self._observer.observe_process(
            pid=metadata.pid,
            expected_executable_name=materialized.process_spec.expected_executable_name,
            expected_profile_marker=materialized.process_spec.expected_profile_marker,
        )
        return metadata, classify_process_ownership(observation)

    def verify_resources(self) -> SerenaOperationResult:
        try:
            materialized = self._describe_existing()
        except SerenaMaterializationError as exc:
            return SerenaOperationResult(
                success=False,
                error_code=exc.code,
                recovery_required=True,
            )

        serena_config = materialized.serena_home / "serena_config.yml"
        if not serena_config.is_file():
            return SerenaOperationResult(
                success=False,
                error_code="SERENA_CONFIG_NOT_FOUND",
            )

        metadata, ownership = self._process_ownership(materialized)
        if metadata.status is PidMetadataStatus.INVALID:
            return SerenaOperationResult(
                success=False,
                error_code="PID_METADATA_INVALID",
                recovery_required=True,
            )
        if metadata.status is PidMetadataStatus.UNKNOWN:
            return SerenaOperationResult(
                success=False,
                error_code="PID_METADATA_UNKNOWN",
                recovery_required=True,
            )
        if ownership is ProcessOwnership.STALE:
            return SerenaOperationResult(
                success=False,
                error_code="STALE_PID_METADATA",
                recovery_required=True,
            )
        if ownership is ProcessOwnership.MISMATCH:
            return SerenaOperationResult(success=False, error_code="PID_MISMATCH")
        if ownership is ProcessOwnership.UNKNOWN:
            return SerenaOperationResult(
                success=False,
                error_code="PROCESS_OWNERSHIP_UNKNOWN",
                recovery_required=True,
            )
        if ownership is ProcessOwnership.OWNED:
            return SerenaOperationResult(
                success=False,
                error_code="PROCESS_ALREADY_PRESENT",
                recovery_required=True,
            )

        port = self._observer.observe_port_binding(
            port=self._worker.health_port,
            expected_pid=None,
        )
        if port is PortBindingState.COLLISION:
            return SerenaOperationResult(success=False, error_code="PORT_IN_USE")
        if port is PortBindingState.UNKNOWN:
            return SerenaOperationResult(
                success=False,
                error_code="PORT_STATE_UNKNOWN",
                recovery_required=True,
            )
        if port is PortBindingState.OWNED:
            return SerenaOperationResult(
                success=False,
                error_code="PORT_STILL_OWNED",
                recovery_required=True,
            )
        return self._tunnel_guard.verify_available(self._worker)

    def render_profile(self) -> SerenaOperationResult:
        try:
            token_values = self._token_provider.resolve(self._worker, self._binding)
        except Exception:
            return SerenaOperationResult(
                success=False,
                error_code="PROFILE_TOKEN_RESOLUTION_FAILED",
            )
        try:
            self._materialized = self._materializer.materialize(
                self._worker,
                self._binding,
                token_values,
            )
        except SerenaMaterializationError as exc:
            return SerenaOperationResult(
                success=False,
                error_code=exc.code,
                recovery_required=(exc.code == "PROFILE_WRITE_FAILED"),
            )
        return SerenaOperationResult(success=True)

    def preflight(self) -> SerenaOperationResult:
        if self._materialized is None:
            return SerenaOperationResult(
                success=False,
                error_code="RUNTIME_NOT_MATERIALIZED",
                recovery_required=True,
            )
        return self._preflight_service.run(self._materialized)

    def start_owned_process(self) -> OwnedProcessMutationResult:
        if self._materialized is None:
            return OwnedProcessMutationResult(
                OwnedProcessMutationState.RECOVERY_REQUIRED,
                "RUNTIME_NOT_MATERIALIZED",
            )
        return self._process_controller.start(self._materialized.process_spec)

    def wait_ready(self) -> SerenaOperationResult:
        try:
            materialized = self._materialized or self._describe_existing()
        except SerenaMaterializationError as exc:
            return SerenaOperationResult(
                success=False,
                error_code=exc.code,
                recovery_required=True,
            )
        spec = materialized.process_spec
        deadline = self._monotonic() + self._worker.startup_timeout_seconds
        while self._monotonic() < deadline:
            metadata = self._observer.read_pid_metadata(spec.pid_path)
            if metadata.status is not PidMetadataStatus.VALID or metadata.pid is None:
                return SerenaOperationResult(
                    success=False,
                    error_code="PID_METADATA_NOT_READY",
                    recovery_required=True,
                )
            observation = self._observer.observe_process(
                pid=metadata.pid,
                expected_executable_name=spec.expected_executable_name,
                expected_profile_marker=spec.expected_profile_marker,
            )
            ownership = classify_process_ownership(observation)
            if ownership is ProcessOwnership.STALE:
                return SerenaOperationResult(
                    success=False,
                    error_code="PROCESS_EXITED_DURING_START",
                    recovery_required=True,
                )
            if ownership is ProcessOwnership.MISMATCH:
                return SerenaOperationResult(success=False, error_code="PID_MISMATCH")
            if ownership is ProcessOwnership.UNKNOWN:
                return SerenaOperationResult(
                    success=False,
                    error_code="PROCESS_OWNERSHIP_UNKNOWN",
                    recovery_required=True,
                )
            port = self._observer.observe_port_binding(
                port=self._worker.health_port,
                expected_pid=metadata.pid,
            )
            if port is PortBindingState.COLLISION:
                return SerenaOperationResult(success=False, error_code="PORT_IN_USE")
            if port is PortBindingState.OWNED:
                health = self._observer.probe_ready(
                    health_host=self._worker.health_host,
                    health_port=self._worker.health_port,
                    timeout_seconds=1,
                )
                if health.state is HealthProbeState.READY:
                    return SerenaOperationResult(success=True)
            self._sleeper(0.05)
        return SerenaOperationResult(
            success=False,
            error_code="STARTUP_TIMEOUT",
            recovery_required=True,
        )

    def verify_project_identity(self) -> SerenaOperationResult:
        return self._project_identity_service.verify(self._binding)

    def targeted_stop(self) -> OwnedProcessMutationResult:
        try:
            materialized = self._materialized or self._describe_existing()
        except SerenaMaterializationError as exc:
            return OwnedProcessMutationResult(
                OwnedProcessMutationState.RECOVERY_REQUIRED,
                exc.code,
            )
        return self._process_controller.stop(materialized.process_spec)

    def wait_exit(self) -> SerenaOperationResult:
        try:
            materialized = self._materialized or self._describe_existing()
        except SerenaMaterializationError as exc:
            return SerenaOperationResult(
                success=False,
                error_code=exc.code,
                recovery_required=True,
            )
        metadata = self._observer.read_pid_metadata(materialized.process_spec.pid_path)
        if metadata.status is not PidMetadataStatus.ABSENT:
            return SerenaOperationResult(
                success=False,
                error_code="PROCESS_EXIT_UNCONFIRMED",
                recovery_required=True,
            )
        port = self._observer.observe_port_binding(
            port=self._worker.health_port,
            expected_pid=None,
        )
        if port is PortBindingState.FREE:
            return SerenaOperationResult(success=True)
        if port is PortBindingState.UNKNOWN:
            return SerenaOperationResult(
                success=False,
                error_code="PORT_STATE_UNKNOWN",
                recovery_required=True,
            )
        return SerenaOperationResult(
            success=False,
            error_code="PORT_STILL_OWNED",
            recovery_required=True,
        )

    def verify_released(self) -> SerenaOperationResult:
        local = self.wait_exit()
        if not local.success:
            return local
        return self._tunnel_guard.verify_released(self._worker)

    def clear_assignment(self) -> SerenaOperationResult:
        return self._assignment_service.clear(
            self._worker.worker_id,
            self._binding.project_id,
        )

    def emit_evidence(self) -> SerenaOperationResult:
        return self._evidence_service.emit(
            self._worker.worker_id,
            self._binding.project_id,
        )
