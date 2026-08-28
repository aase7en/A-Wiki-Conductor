"""Durable-job backend wrapper for the accepted Claude Code harness.

This module owns no lifecycle, scheduler, process runner, retry loop, or
persistence. It maps one opaque operation to the AHA-3 adapter and returns a
bounded JobBackendResult to the existing durable execution coordinator.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Callable, Mapping, Protocol, Sequence

from .claude_code_harness import (
    ClaudeCodeHarnessAdapter,
    ClaudeCodeHarnessError,
    ClaudeCodeHarnessResult,
    HarnessExecutionStatus,
    HarnessDispatch,
    TaskPacketFile,
)
from .domain import RecoveryClassification
from .job_execution import JobBackendResult, JobExecutionContext
from .provider_configuration import (
    ProviderConfiguration,
    ProviderEndpointConfig,
    ProviderHealth,
    ProviderObservation,
)

_OPERATION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


def _text(value: str, field: str, *, max_length: int = 1024) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or "\x00" in value
        or len(value) > max_length
    ):
        raise ValueError(f"{field} is invalid")
    return value.strip()


@dataclass(frozen=True, slots=True)
class ClaudeCodeProviderState:
    profile: ProviderConfiguration
    endpoint: ProviderEndpointConfig
    observation: ProviderObservation | None

    def __post_init__(self) -> None:
        if not isinstance(self.profile, ProviderConfiguration):
            raise ValueError("profile must be a ProviderConfiguration")
        if not isinstance(self.endpoint, ProviderEndpointConfig):
            raise ValueError("endpoint must be a ProviderEndpointConfig")
        if self.observation is not None and not isinstance(
            self.observation, ProviderObservation
        ):
            raise ValueError("observation must be a ProviderObservation or None")
        if self.endpoint.endpoint_ref != self.profile.endpoint_ref:
            raise ValueError("provider endpoint does not match profile")


class ClaudeCodeProviderResolver(Protocol):
    def resolve(self, provider_id: str) -> ClaudeCodeProviderState | None: ...


class StaticClaudeCodeProviderResolver:
    def __init__(self, states: Mapping[str, ClaudeCodeProviderState]) -> None:
        if not isinstance(states, Mapping):
            raise ValueError("states must be a mapping")
        copied: dict[str, ClaudeCodeProviderState] = {}
        for provider_id, state in states.items():
            provider_id = _text(provider_id, "provider_id", max_length=128)
            if not isinstance(state, ClaudeCodeProviderState):
                raise ValueError("state must be a ClaudeCodeProviderState")
            if state.profile.provider_id != provider_id:
                raise ValueError("provider state id mismatch")
            copied[provider_id] = state
        self._states = copied

    def resolve(self, provider_id: str) -> ClaudeCodeProviderState | None:
        return self._states.get(_text(provider_id, "provider_id", max_length=128))


@dataclass(frozen=True, slots=True)
class ClaudeCodeOperationDefinition:
    operation_ref: str
    dispatch: HarnessDispatch
    packet: TaskPacketFile
    worker_id: str


    def __post_init__(self) -> None:
        if not isinstance(self.operation_ref, str) or _OPERATION_RE.fullmatch(
            self.operation_ref
        ) is None:
            raise ValueError("operation_ref is invalid")
        if not isinstance(self.dispatch, HarnessDispatch):
            raise ValueError("dispatch must be a HarnessDispatch")
        if not isinstance(self.packet, TaskPacketFile):
            raise ValueError("packet must be a TaskPacketFile")
        _text(self.worker_id, "worker_id", max_length=128)


def _result_digest(
    definition: ClaudeCodeOperationDefinition,
    context: JobExecutionContext,
    result: ClaudeCodeHarnessResult | None,
    code: str,
) -> str:
    payload = None if result is None else result.payload
    payload_bytes = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    digest_payload = {
        "operation_ref": definition.operation_ref,
        "job_id": context.job_id,
        "work_order_ref": context.work_order_ref,
        "project_id": context.project_id,
        "worker_id": context.worker_id,
        "attempt_no": context.attempt_no,
        "provider_id": definition.dispatch.provider_id,
        "model_id": definition.dispatch.model_id,
        "task_packet_sha256": definition.packet.sha256.casefold(),
        "code": code,
        "status": None if result is None else result.status.value,
        "exit_code": None if result is None else result.exit_code,
        "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
        "stderr_sha256": hashlib.sha256(
            ("" if result is None else result.stderr).encode("utf-8")
        ).hexdigest(),
    }
    raw = json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode()
    return f"claude-harness-evidence:{hashlib.sha256(raw).hexdigest()}"


def _provider_error_code(state: ClaudeCodeProviderState) -> str:
    observation = state.observation
    if observation is None:
        return "PROVIDER_UNAVAILABLE"
    return {
        ProviderHealth.AUTH_FAILED: "AUTH_FAILED",
        ProviderHealth.RATE_LIMITED: "RATE_LIMITED",
        ProviderHealth.QUOTA_EXHAUSTED: "QUOTA_EXHAUSTED",
        ProviderHealth.UNAVAILABLE: "PROVIDER_UNAVAILABLE",
        ProviderHealth.DEGRADED: "PROVIDER_UNAVAILABLE",
        ProviderHealth.UNKNOWN: "PROVIDER_UNAVAILABLE",
    }.get(observation.health, "PROVIDER_UNAVAILABLE")


def _failure(
    definition: ClaudeCodeOperationDefinition,
    context: JobExecutionContext,
    code: str,
    *,
    classification: RecoveryClassification,
    result: ClaudeCodeHarnessResult | None = None,
) -> JobBackendResult:
    return JobBackendResult(
        success=False,
        evidence_ref=_result_digest(definition, context, result, code),
        recovery_classification=classification,
        error_code=code,
    )


class ClaudeCodeJobBackend:
    def __init__(
        self,
        *,
        operations: Sequence[ClaudeCodeOperationDefinition],
        adapter: ClaudeCodeHarnessAdapter,
        provider_resolver: ClaudeCodeProviderResolver,
        clock: Callable[[], object],
    ) -> None:
        if isinstance(operations, (str, bytes)):
            raise ValueError("operations must be a sequence")
        by_ref: dict[str, ClaudeCodeOperationDefinition] = {}
        for definition in operations:
            if not isinstance(definition, ClaudeCodeOperationDefinition):
                raise ValueError("operation must be a ClaudeCodeOperationDefinition")
            if definition.operation_ref in by_ref:
                raise ValueError("operation_ref must be unique")
            by_ref[definition.operation_ref] = definition
        if not callable(getattr(adapter, "execute", None)):
            raise ValueError("adapter must provide execute")
        if not callable(getattr(provider_resolver, "resolve", None)):
            raise ValueError("provider_resolver must provide resolve")
        if not callable(clock):
            raise ValueError("clock must be callable")
        self._operations = by_ref
        self._adapter = adapter
        self._provider_resolver = provider_resolver
        self._clock = clock

    @staticmethod
    def _validate_identity(
        definition: ClaudeCodeOperationDefinition,
        context: JobExecutionContext,
    ) -> None:
        dispatch = definition.dispatch
        if (
            context.job_id != dispatch.execution_id
            or context.work_order_ref != dispatch.task_contract_ref
            or context.project_id != dispatch.project_id
            or context.worker_id != definition.worker_id
        ):
            raise ValueError("CLAUDE_JOB_IDENTITY_MISMATCH")

    def execute(
        self,
        operation_ref: str,
        context: JobExecutionContext,
    ) -> JobBackendResult:
        if not isinstance(context, JobExecutionContext):
            raise ValueError("context must be a JobExecutionContext")
        definition = self._operations.get(operation_ref)
        if definition is None:
            raise ValueError("CLAUDE_OPERATION_NOT_REGISTERED")
        self._validate_identity(definition, context)

        state = self._provider_resolver.resolve(definition.dispatch.provider_id)
        if state is None:
            return _failure(
                definition,
                context,
                "PROVIDER_UNAVAILABLE",
                classification=RecoveryClassification.NO_MUTATION,
            )

        try:
            result = self._adapter.execute(
                definition.dispatch,
                state.profile,
                state.endpoint,
                state.observation,
                definition.packet,
                now=self._clock(),
            )
        except ClaudeCodeHarnessError as exc:
            code = (
                _provider_error_code(state)
                if exc.code == "PROVIDER_NOT_READY"
                else "POLICY_DENIED"
                if exc.code in {
                    "HARNESS_MUTATION_NOT_READY",
                    "HARNESS_STRATEGY_UNSUPPORTED",
                    "HARNESS_NOT_CONFIGURED",
                    "PROVIDER_ID_MISMATCH",
                    "ENDPOINT_REF_MISMATCH",
                    "MODEL_NOT_CONFIGURED",
                    "EFFORT_NOT_SUPPORTED",
                }
                else "HARNESS_FAILED"
            )
            return _failure(
                definition,
                context,
                code,
                classification=RecoveryClassification.NO_MUTATION,
            )

        if result.status is HarnessExecutionStatus.SUCCESS:
            return JobBackendResult(
                success=True,
                evidence_ref=_result_digest(definition, context, result, "SUCCESS"),
            )
        if result.status is HarnessExecutionStatus.TIMEOUT:
            return _failure(
                definition,
                context,
                "EXECUTION_STATE_UNKNOWN",
                classification=RecoveryClassification.UNKNOWN,
                result=result,
            )
        if result.status in {
            HarnessExecutionStatus.FAILED,
            HarnessExecutionStatus.OUTPUT_LIMIT,
            HarnessExecutionStatus.OUTPUT_INVALID,
        }:
            return _failure(
                definition,
                context,
                "HARNESS_FAILED",
                classification=RecoveryClassification.NO_MUTATION,
                result=result,
            )
        return _failure(
            definition,
            context,
            "HARNESS_FAILED",
            classification=RecoveryClassification.UNKNOWN,
            result=result,
        )
