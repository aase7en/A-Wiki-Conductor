"""Resilient wiring between native operation adapters and the AC-RES supervisor.

Implements the ``NativeCommandRunner`` protocol so native git/verification
commands execute through the supervised execution service (durable execution
record, duplicate-execution protection, bounded collect) instead of a bare
subprocess call. Transport-loss recovery, retry, and failover decisions stay
outside this module.

The run lifecycle itself (fingerprint, dedup guard, record creation, launch,
poll/timeout, collect/version CAS, artifact mapping) lives in the shared
``SupervisedRunCoordinator`` so future supervised backends reuse one authority.
This module is the spec/scope-validating adapter for native commands.
"""

from __future__ import annotations

import time
from pathlib import Path, PureWindowsPath
from typing import Callable, Sequence

from .execution_deduplication import compute_execution_fingerprint
from .native_execution import (
    NativeCommandResult,
    NativeCommandSpec,
    NativeExecutionError,
    NativeExecutionScope,
)
from .supervised_run_coordinator import (
    SupervisedLauncher,
    SupervisedExecutionFingerprintStore,
    SupervisedRunCoordinator,
    SupervisedRunIdentity,
)


class SupervisedCommandRunner:
    """Run authorized native commands under durable supervised execution."""

    def __init__(
        self,
        *,
        scope: NativeExecutionScope,
        execution_store: SupervisedExecutionFingerprintStore,
        supervised: SupervisedLauncher,
        job_id: str,
        work_order_ref: str,
        project_id: str,
        worker_id: str,
        backend_id: str,
        branch: str,
        head_before: str,
        runtime_profile_ref: str,
        poll_interval_seconds: float = 0.05,
        sleep_fn: Callable[[float], None] = time.sleep,
        clock_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(scope, NativeExecutionScope):
            raise ValueError("scope must be a NativeExecutionScope")
        self._scope = scope
        repo_root = Path(scope.root).expanduser().resolve(strict=False)
        # Kept as an attribute so existing behavior probes (tests) observing
        # the runner's resolved repo root keep working against the adapter.
        self._repo_root = repo_root
        self._coordinator = SupervisedRunCoordinator(
            execution_store=execution_store,
            supervised=supervised,
            identity=SupervisedRunIdentity(
                job_id=job_id,
                work_order_ref=work_order_ref,
                project_id=project_id,
                worker_id=worker_id,
                backend_id=backend_id,
                branch=branch,
                head_before=head_before,
                runtime_profile_ref=runtime_profile_ref,
                repo_root=str(repo_root),
            ),
            poll_interval_seconds=poll_interval_seconds,
            sleep_fn=sleep_fn,
            clock_fn=clock_fn,
            max_output_bytes=scope.max_output_bytes,
        )

    def _validated_argv(self, spec: NativeCommandSpec) -> tuple[str, ...]:
        if isinstance(spec.argv, (str, bytes)) or not isinstance(spec.argv, Sequence):
            raise NativeExecutionError("ARGV_INVALID")
        argv = tuple(spec.argv)
        if not argv:
            raise NativeExecutionError("ARGV_INVALID")
        for argument in argv:
            if not isinstance(argument, str) or not argument or "\x00" in argument:
                raise NativeExecutionError("ARGV_INVALID")
        if not isinstance(spec.mutation_intent, bool):
            raise NativeExecutionError("MUTATION_INTENT_INVALID")
        if spec.mutation_intent and not self._scope.mutation_allowed:
            raise NativeExecutionError("MUTATION_FORBIDDEN")
        executable = PureWindowsPath(argv[0]).name
        allowed = {PureWindowsPath(value).name.casefold() for value in self._scope.allowed_executables}
        if executable.casefold() not in allowed:
            raise NativeExecutionError("EXECUTABLE_NOT_ALLOWED")
        timeout = spec.timeout_seconds
        if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout < 1:
            raise NativeExecutionError("TIMEOUT_INVALID")
        if timeout > self._scope.max_timeout_seconds:
            raise NativeExecutionError("TIMEOUT_INVALID")
        return argv

    def _validated_environment_overrides(
        self, spec: NativeCommandSpec
    ) -> tuple[tuple[str, str], ...]:
        overrides = spec.environment_overrides
        if not isinstance(overrides, tuple):
            raise NativeExecutionError("ENV_OVERRIDE_INVALID")
        allowed = {key.casefold() for key in self._scope.allowed_environment_overrides}
        seen: set[str] = set()
        normalized: list[tuple[str, str]] = []
        for item in overrides:
            if not isinstance(item, tuple) or len(item) != 2:
                raise NativeExecutionError("ENV_OVERRIDE_INVALID")
            key, value = item
            if (
                not isinstance(key, str)
                or not key.strip()
                or "=" in key
                or "\x00" in key
                or not isinstance(value, str)
                or not value
                or "\x00" in value
            ):
                raise NativeExecutionError("ENV_OVERRIDE_INVALID")
            folded = key.casefold()
            if folded not in allowed:
                raise NativeExecutionError("ENV_OVERRIDE_NOT_ALLOWED")
            if folded in seen:
                raise NativeExecutionError("ENV_OVERRIDE_INVALID")
            seen.add(folded)
            normalized.append((key, value))
        return tuple(normalized)

    def _poll_until_resolved(self, execution_id: str, *, timeout_seconds: int):
        # Behavior-preserving delegation for existing lifecycle probes.
        return self._coordinator._poll_until_resolved(
            execution_id, timeout_seconds=timeout_seconds
        )

    def fingerprint_for(self, spec: NativeCommandSpec) -> str:
        return self._coordinator.fingerprint_for_argv(self._validated_argv(spec))

    def run(self, spec: NativeCommandSpec) -> NativeCommandResult:
        if not isinstance(spec, NativeCommandSpec):
            raise NativeExecutionError("SPEC_INVALID")
        argv = self._validated_argv(spec)
        environment_overrides = self._validated_environment_overrides(spec)
        cwd = self._scope.resolve_relative(spec.cwd, must_exist=True)
        if cwd != Path(self._coordinator.identity.repo_root):
            raise NativeExecutionError("CWD_UNSUPPORTED")

        return self._coordinator.run(
            argv,
            environment_overrides=environment_overrides,
            timeout_seconds=spec.timeout_seconds,
        )


def build_supervised_native_adapter_resolver(
    *,
    service: object,
    database_path: "Path | str",
    python_executable: str = __import__("sys").executable,
    git_executable: str = "git",
    poll_interval_seconds: float = 0.05,
):
    """Assemble a ControlCenter resolver whose native commands run supervised.

    Enabling point for the resilient path: pass the returned resolver (or set
    ``supervised=True`` on ``DurableJobControlService.open``) to route git and
    verification commands through durable execution records, duplicate
    protection, and bounded collection. The default assembly remains the plain
    subprocess runner until per-job fingerprint identity plumbing lands; the
    static identity below keeps dedup correct per (repo, argv) which is the
    operation-level duplicate dimension.
    """
    import sys

    from .execution_store import SQLiteExecutionStore
    from .native_operation_assembly import ControlCenterNativeAdapterResolver
    from .owned_process import WindowsOwnedProcessController
    from .supervised_execution import SupervisedExecutionService
    from .windows_io import LoopbackReadyzHttpProbe, StrictPowerShellInspectionRunner
    from .windows_observer import WindowsRuntimeObserver

    store = SQLiteExecutionStore(database_path)
    observer = WindowsRuntimeObserver(
        runner=StrictPowerShellInspectionRunner(),
        http_probe=LoopbackReadyzHttpProbe(),
    )
    controller = WindowsOwnedProcessController(observer=observer)
    python_name = PureWindowsPath(python_executable).name
    git_name = PureWindowsPath(git_executable).name
    supervised_service = SupervisedExecutionService(
        store=store,
        controller=controller,
        observer=observer,
        allowed_target_executables=(python_name, git_name),
        python_executable=python_executable,
    )

    def runner_factory(scope: NativeExecutionScope) -> SupervisedCommandRunner:
        return SupervisedCommandRunner(
            scope=scope,
            execution_store=store,
            supervised=supervised_service,
            job_id="job:native-supervised",
            work_order_ref="docs/contracts/resilient-execution-supervisor.md",
            project_id="project:native",
            worker_id="worker:native-supervised",
            backend_id="supervised-native",
            branch="unknown",
            head_before="unknown",
            runtime_profile_ref="runtime:supervised-native",
            poll_interval_seconds=poll_interval_seconds,
        )

    return ControlCenterNativeAdapterResolver(
        service=service,
        git_executable=git_executable,
        python_executable=python_executable,
        runner_factory=runner_factory,
    )
