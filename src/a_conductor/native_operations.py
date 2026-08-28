"""Allowlisted native operation registry and durable-job backend adapter.

This module maps opaque operation IDs to fixed native adapter methods. It has
no generic argv/shell/executable surface, persistence, scheduler, model router,
or Git/filesystem mutation implementation.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping, Protocol, Sequence

from .domain import RecoveryClassification
from .job_execution import JobBackendResult, JobExecutionContext
from .native_execution import NativeCommandResult


_OPERATION_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_MAX_TIMEOUT_SECONDS = 3600


class NativeOperationError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class NativeOperationKind(str, Enum):
    GIT_STATUS = "GIT_STATUS"
    GIT_WORKING_DIFF = "GIT_WORKING_DIFF"
    GIT_CACHED_DIFF = "GIT_CACHED_DIFF"
    PYTEST = "PYTEST"
    COMPILEALL = "COMPILEALL"


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


def _require_operation_ref(value: str) -> str:
    _require_text(value, "operation_ref")
    if _OPERATION_REF_RE.fullmatch(value) is None:
        raise ValueError("operation_ref must be an opaque identifier")
    return value


def _require_timeout(value: int) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
        or value > _MAX_TIMEOUT_SECONDS
    ):
        raise ValueError("timeout_seconds must be between 1 and 3600")
    return value


def _normalize_paths(values: Sequence[str | Path]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError("paths must be a sequence")
    rendered: list[str] = []
    for value in values:
        if not isinstance(value, (str, Path)):
            raise ValueError("path must be text or Path")
        text = str(value)
        if not text.strip() or "\x00" in text:
            raise ValueError("path must not be blank")
        candidate = Path(text)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("operation paths must be relative and confined")
        normalized = candidate.as_posix()
        if normalized in {"", "."}:
            raise ValueError("operation path must not be project root")
        rendered.append(normalized)
    return tuple(rendered)


@dataclass(frozen=True, slots=True)
class NativeOperationDefinition:
    operation_ref: str
    kind: NativeOperationKind
    paths: tuple[str, ...] = ()
    timeout_seconds: int = 30

    def __post_init__(self) -> None:
        _require_operation_ref(self.operation_ref)
        if not isinstance(self.kind, NativeOperationKind):
            raise ValueError("kind must be a NativeOperationKind")
        normalized = _normalize_paths(self.paths)
        object.__setattr__(self, "paths", normalized)
        _require_timeout(self.timeout_seconds)
        if self.kind is NativeOperationKind.GIT_STATUS and normalized:
            raise ValueError("GIT_STATUS does not accept paths")
        if self.kind in {NativeOperationKind.PYTEST, NativeOperationKind.COMPILEALL} and not normalized:
            raise ValueError("verification operation requires explicit paths")


class NativeOperationRegistry:
    def __init__(self, definitions: Sequence[NativeOperationDefinition] = ()) -> None:
        if isinstance(definitions, (str, bytes)):
            raise ValueError("definitions must be a sequence")
        by_ref: dict[str, NativeOperationDefinition] = {}
        for definition in definitions:
            if not isinstance(definition, NativeOperationDefinition):
                raise ValueError("definition must be a NativeOperationDefinition")
            if definition.operation_ref in by_ref:
                raise NativeOperationError("OPERATION_REF_DUPLICATE")
            by_ref[definition.operation_ref] = definition
        self._definitions = by_ref

    def resolve(self, operation_ref: str) -> NativeOperationDefinition:
        _require_operation_ref(operation_ref)
        definition = self._definitions.get(operation_ref)
        if definition is None:
            raise NativeOperationError("OPERATION_NOT_REGISTERED")
        return definition

    def list_refs(self) -> tuple[str, ...]:
        return tuple(sorted(self._definitions))


class NativeGitOperations(Protocol):
    def status_short(self, *, timeout_seconds: int = 10) -> NativeCommandResult: ...

    def working_diff(
        self,
        paths: Sequence[str | Path] = (),
        *,
        timeout_seconds: int = 15,
    ) -> NativeCommandResult: ...

    def cached_diff(
        self,
        paths: Sequence[str | Path] = (),
        *,
        timeout_seconds: int = 15,
    ) -> NativeCommandResult: ...


class NativeVerificationOperations(Protocol):
    def pytest(
        self,
        paths: Sequence[str | Path] = ("tests",),
        *,
        timeout_seconds: int = 120,
    ) -> NativeCommandResult: ...

    def compileall(
        self,
        paths: Sequence[str | Path] = ("src",),
        *,
        timeout_seconds: int = 120,
    ) -> NativeCommandResult: ...


@dataclass(frozen=True, slots=True)
class WorkerNativeAdapters:
    git: NativeGitOperations
    verification: NativeVerificationOperations


class WorkerNativeAdapterResolver(Protocol):
    def resolve(self, worker_id: str) -> WorkerNativeAdapters: ...


class StaticWorkerNativeAdapterResolver:
    def __init__(self, adapters: Mapping[str, WorkerNativeAdapters]) -> None:
        if not isinstance(adapters, Mapping):
            raise ValueError("adapters must be a mapping")
        copied: dict[str, WorkerNativeAdapters] = {}
        for worker_id, value in adapters.items():
            _require_text(worker_id, "worker_id")
            if not isinstance(value, WorkerNativeAdapters):
                raise ValueError("adapter mapping values must be WorkerNativeAdapters")
            copied[worker_id] = value
        self._adapters = copied

    def resolve(self, worker_id: str) -> WorkerNativeAdapters:
        _require_text(worker_id, "worker_id")
        adapters = self._adapters.get(worker_id)
        if adapters is None:
            raise NativeOperationError("WORKER_NATIVE_ADAPTERS_NOT_REGISTERED")
        return adapters


def _evidence_ref(
    definition: NativeOperationDefinition,
    result: NativeCommandResult,
) -> str:
    payload = {
        "operation_ref": definition.operation_ref,
        "kind": definition.kind.value,
        "executable_name": Path(result.executable).name,
        "argument_count": result.argument_count,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "stdout_sha256": result.stdout_sha256,
        "stderr_sha256": result.stderr_sha256,
        "stdout_truncated": result.stdout_truncated,
        "stderr_truncated": result.stderr_truncated,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return f"native-evidence:{definition.kind.value.lower()}:{digest}"


def _failure_classification(kind: NativeOperationKind) -> RecoveryClassification:
    if kind in {
        NativeOperationKind.GIT_STATUS,
        NativeOperationKind.GIT_WORKING_DIFF,
        NativeOperationKind.GIT_CACHED_DIFF,
    }:
        return RecoveryClassification.NO_MUTATION
    return RecoveryClassification.UNKNOWN


class AllowlistedNativeJobBackend:
    def __init__(
        self,
        *,
        registry: NativeOperationRegistry,
        resolver: WorkerNativeAdapterResolver,
    ) -> None:
        self._registry = registry
        self._resolver = resolver

    @staticmethod
    def _execute_definition(
        definition: NativeOperationDefinition,
        adapters: WorkerNativeAdapters,
    ) -> NativeCommandResult:
        if definition.kind is NativeOperationKind.GIT_STATUS:
            result = adapters.git.status_short(
                timeout_seconds=definition.timeout_seconds
            )
        elif definition.kind is NativeOperationKind.GIT_WORKING_DIFF:
            result = adapters.git.working_diff(
                definition.paths,
                timeout_seconds=definition.timeout_seconds,
            )
        elif definition.kind is NativeOperationKind.GIT_CACHED_DIFF:
            result = adapters.git.cached_diff(
                definition.paths,
                timeout_seconds=definition.timeout_seconds,
            )
        elif definition.kind is NativeOperationKind.PYTEST:
            result = adapters.verification.pytest(
                definition.paths,
                timeout_seconds=definition.timeout_seconds,
            )
        elif definition.kind is NativeOperationKind.COMPILEALL:
            result = adapters.verification.compileall(
                definition.paths,
                timeout_seconds=definition.timeout_seconds,
            )
        else:  # pragma: no cover - enum exhaustiveness guard
            raise NativeOperationError("OPERATION_KIND_UNSUPPORTED")
        if not isinstance(result, NativeCommandResult):
            raise NativeOperationError("NATIVE_RESULT_INVALID")
        return result

    def execute(
        self, operation_ref: str, context: JobExecutionContext
    ) -> JobBackendResult:
        if not isinstance(context, JobExecutionContext):
            raise ValueError("context must be a JobExecutionContext")
        definition = self._registry.resolve(operation_ref)
        adapters = self._resolver.resolve(context.worker_id)
        result = self._execute_definition(definition, adapters)
        evidence_ref = _evidence_ref(definition, result)
        success = not result.timed_out and result.exit_code == 0
        if success:
            return JobBackendResult(success=True, evidence_ref=evidence_ref)
        return JobBackendResult(
            success=False,
            evidence_ref=evidence_ref,
            recovery_classification=_failure_classification(definition.kind),
        )
