"""Assemble fresh worker-native read/verification adapters from Control Center state.

This module performs no worker lifecycle, project assignment, process, tunnel,
Git mutation, scheduler, routing, or model action. Each resolve reads a fresh
Control Center snapshot and constructs a new confined NativeExecutionScope.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Protocol

from .control_center import ControlCenterSnapshot
from .native_adapters import NativeCommandRunner, NativeGitReadAdapter, NativeVerificationAdapter
from .native_execution import NativeExecutionError, NativeExecutionScope
from .native_operations import (
    NativeGitOperations,
    NativeOperationError,
    NativeVerificationOperations,
    WorkerNativeAdapters,
)


class ControlCenterSnapshotProvider(Protocol):
    def snapshot(self) -> ControlCenterSnapshot: ...


GitAdapterFactory = Callable[[NativeExecutionScope], NativeGitOperations]
VerificationAdapterFactory = Callable[
    [NativeExecutionScope], NativeVerificationOperations
]
RunnerFactory = Callable[[NativeExecutionScope], NativeCommandRunner]


def _require_executable(value: str, code: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise NativeOperationError(code)
    return value.strip()


class ControlCenterNativeAdapterResolver:
    def __init__(
        self,
        *,
        service: ControlCenterSnapshotProvider,
        git_executable: str = "git",
        python_executable: str = sys.executable,
        max_timeout_seconds: int = 300,
        max_output_bytes: int = 1_048_576,
        max_file_bytes: int = 1_048_576,
        git_adapter_factory: GitAdapterFactory | None = None,
        verification_adapter_factory: VerificationAdapterFactory | None = None,
        runner_factory: RunnerFactory | None = None,
    ) -> None:
        self._service = service
        self._git_executable = _require_executable(
            git_executable, "GIT_EXECUTABLE_INVALID"
        )
        self._python_executable = _require_executable(
            python_executable, "PYTHON_EXECUTABLE_INVALID"
        )
        self._max_timeout_seconds = max_timeout_seconds
        self._max_output_bytes = max_output_bytes
        self._max_file_bytes = max_file_bytes
        self._git_factory = git_adapter_factory or self._build_git_adapter
        self._verification_factory = (
            verification_adapter_factory or self._build_verification_adapter
        )
        self._runner_factory = runner_factory

    def _build_git_adapter(
        self, scope: NativeExecutionScope
    ) -> NativeGitReadAdapter:
        return NativeGitReadAdapter(
            scope,
            runner=self._runner_factory(scope) if self._runner_factory else None,
            git_executable=self._git_executable,
        )

    def _build_verification_adapter(
        self, scope: NativeExecutionScope
    ) -> NativeVerificationAdapter:
        return NativeVerificationAdapter(
            scope,
            runner=self._runner_factory(scope) if self._runner_factory else None,
            python_executable=self._python_executable,
        )

    def _scope_for_worker(self, worker_id: str) -> NativeExecutionScope:
        if not isinstance(worker_id, str) or not worker_id.strip():
            raise ValueError("worker_id must not be blank")
        snapshot = self._service.snapshot()
        row = next(
            (candidate for candidate in snapshot.workers if candidate.worker_id == worker_id),
            None,
        )
        if row is None:
            raise NativeOperationError("WORKER_NOT_FOUND")
        if (
            row.assignment_id is None
            or row.project_id is None
            or row.project_root_path is None
        ):
            raise NativeOperationError("WORKER_ASSIGNMENT_MISSING")
        if not isinstance(row.mutation_allowed, bool):
            raise NativeOperationError("MUTATION_AUTHORITY_MISSING")

        allowed_executables = (
            Path(self._git_executable).name,
            Path(self._python_executable).name,
        )
        try:
            return NativeExecutionScope(
                root=row.project_root_path,
                mutation_allowed=row.mutation_allowed,
                allowed_executables=allowed_executables,
                allowed_environment_overrides=(),
                max_timeout_seconds=self._max_timeout_seconds,
                max_output_bytes=self._max_output_bytes,
                max_file_bytes=self._max_file_bytes,
            )
        except NativeExecutionError as exc:
            raise NativeOperationError(exc.code) from exc

    def resolve(self, worker_id: str) -> WorkerNativeAdapters:
        scope = self._scope_for_worker(worker_id)
        return WorkerNativeAdapters(
            git=self._git_factory(scope),
            verification=self._verification_factory(scope),
        )
