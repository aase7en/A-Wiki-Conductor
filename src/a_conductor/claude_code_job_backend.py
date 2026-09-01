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
    is_provider_ready,
)
from .provider_execution_authority import ProviderExecutionRequirement
from .provider_policy import (
    ProviderPolicyTaskSecurity,
    evaluate_provider_policy,
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
    configuration_generation: int | None = None

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
        if self.configuration_generation is not None:
            if (
                isinstance(self.configuration_generation, bool)
                or not isinstance(self.configuration_generation, int)
                or self.configuration_generation < 1
            ):
                raise ValueError("configuration_generation must be positive or None")


class ClaudeCodeProviderResolver(Protocol):
    def resolve(self, provider_id: str) -> ClaudeCodeProviderState | None: ...


class ClaudeCodeHarnessAdapterFactory(Protocol):
    def build(
        self,
        definition: "ClaudeCodeOperationDefinition",
        context: JobExecutionContext,
        state: ClaudeCodeProviderState,
    ) -> ClaudeCodeHarnessAdapter: ...


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
    provider_security: ProviderPolicyTaskSecurity | None = None
    expected_configuration_generation: int | None = None
    require_quota: bool = False
    provider_requirement: ProviderExecutionRequirement | None = None


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
        authority = (self.provider_security, self.expected_configuration_generation)
        if any(item is not None for item in authority):
            if not all(item is not None for item in authority):
                raise ValueError("provider execution authority must be complete")
            if not isinstance(self.provider_security, ProviderPolicyTaskSecurity):
                raise ValueError("provider_security must be ProviderPolicyTaskSecurity")
            generation = self.expected_configuration_generation
            if (
                isinstance(generation, bool)
                or not isinstance(generation, int)
                or generation < 1
            ):
                raise ValueError("expected_configuration_generation must be positive")
        if not isinstance(self.require_quota, bool):
            raise ValueError("require_quota must be bool")
        if self.provider_requirement is not None:
            requirement = self.provider_requirement
            if not isinstance(requirement, ProviderExecutionRequirement):
                raise ValueError("provider_requirement must be ProviderExecutionRequirement")
            if requirement.provider_id != self.dispatch.provider_id:
                raise ValueError("provider requirement identity mismatch")
            if requirement.task_contract_ref != self.dispatch.task_contract_ref:
                raise ValueError("provider requirement contract mismatch")
            if requirement.operation_ref != self.operation_ref:
                raise ValueError("provider requirement operation mismatch")
            if requirement.provider_security != self.provider_security:
                raise ValueError("provider requirement security mismatch")
            if requirement.expected_configuration_generation != self.expected_configuration_generation:
                raise ValueError("provider requirement generation mismatch")


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


_PROVIDER_AUTHORITY_ERROR_CODES = frozenset({
    "PROVIDER_AUTHORITY_REQUIRED",
    "PROVIDER_AUTHORITY_CHECK_FAILED",
    "PROVIDER_AUTHORITY_DENIED",
    "PROVIDER_CONFIGURATION_STALE",
    "PROVIDER_CONFIGURATION_DRIFT",
    "PROVIDER_CONFIGURATION_UNAVAILABLE",
    "PROVIDER_NOT_READY",
    "PROVIDER_QUOTA_UNKNOWN",
    "PROVIDER_QUOTA_EXHAUSTED",
    "PROVIDER_ENDPOINT_REF_MISMATCH",
    "PROVIDER_TRUST_UNKNOWN",
    "PROVIDER_EGRESS_UNKNOWN",
    "PROVIDER_TRUST_EGRESS_MISMATCH",
    "PROVIDER_EGRESS_ENDPOINT_MISMATCH",
    "TASK_NETWORK_POLICY_UNRESOLVED",
    "TASK_NETWORK_DENIED",
    "SECRET_TASK_EXTERNAL_DENIED",
    "SENSITIVE_THIRD_PARTY_EXTERNAL_DENIED",
    "SENSITIVE_FIRST_PARTY_ALLOWLIST_REQUIRED",
    "INTERNAL_THIRD_PARTY_ALLOWLIST_REQUIRED",
    "ENDPOINT_NOT_ALLOWLISTED",
    "AUTH_FAILED",
    "RATE_LIMITED",
    "QUOTA_EXHAUSTED",
    "PROVIDER_UNAVAILABLE",
})


def provider_execution_authority_reason(
    definition: ClaudeCodeOperationDefinition,
    state: ClaudeCodeProviderState,
    *,
    now: object,
) -> str | None:
    requirement = definition.provider_requirement
    security = definition.provider_security
    expected_generation = definition.expected_configuration_generation
    if requirement is not None:
        security = requirement.provider_security
        expected_generation = requirement.expected_configuration_generation
    if security is None and expected_generation is None:
        return None
    if security is None or expected_generation is None:
        return "PROVIDER_AUTHORITY_REQUIRED"
    if state.configuration_generation != expected_generation:
        return "PROVIDER_CONFIGURATION_STALE"
    policy = evaluate_provider_policy(state.profile, state.endpoint, security)
    if not policy.allowed:
        return policy.reason_code
    if not is_provider_ready(
        state.profile,
        state.observation,
        now=now,
        expected_generation=expected_generation,
    ):
        return _provider_error_code(state)
    if definition.require_quota:
        quota = None if state.observation is None else state.observation.quota
        if quota is None or any(
            item is None
            for item in (
                quota.limit, quota.used, quota.remaining,
                quota.reset_at, quota.reset_in_seconds,
            )
        ):
            return "PROVIDER_QUOTA_UNKNOWN"
        if quota.remaining is not None and quota.remaining <= 0:
            return "PROVIDER_QUOTA_EXHAUSTED"
    return None


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
        provider_resolver: ClaudeCodeProviderResolver,
        clock: Callable[[], object],
        adapter: ClaudeCodeHarnessAdapter | None = None,
        adapter_factory: ClaudeCodeHarnessAdapterFactory | None = None,
        require_provider_authority: bool = False,
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
        has_adapter = callable(getattr(adapter, "execute", None))
        has_factory = callable(getattr(adapter_factory, "build", None))
        if has_adapter == has_factory:
            raise ValueError("exactly one of adapter or adapter_factory is required")
        if not callable(getattr(provider_resolver, "resolve", None)):
            raise ValueError("provider_resolver must provide resolve")
        if not callable(clock):
            raise ValueError("clock must be callable")
        if not isinstance(require_provider_authority, bool):
            raise ValueError("require_provider_authority must be bool")
        self._operations = by_ref
        self._adapter = adapter
        self._adapter_factory = adapter_factory
        self._provider_resolver = provider_resolver
        self._clock = clock
        self._require_provider_authority = require_provider_authority

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
        if self._require_provider_authority and definition.provider_requirement is None:
            return _failure(
                definition,
                context,
                "PROVIDER_AUTHORITY_REQUIRED",
                classification=RecoveryClassification.NO_MUTATION,
            )

        state = self._provider_resolver.resolve(definition.dispatch.provider_id)
        if state is None:
            return _failure(
                definition,
                context,
                "PROVIDER_UNAVAILABLE",
                classification=RecoveryClassification.NO_MUTATION,
            )
        authority_reason = provider_execution_authority_reason(
            definition, state, now=self._clock()
        )
        if authority_reason is not None:
            return _failure(
                definition,
                context,
                authority_reason,
                classification=RecoveryClassification.NO_MUTATION,
            )

        try:
            adapter = self._adapter
            if adapter is None:
                assert self._adapter_factory is not None
                adapter = self._adapter_factory.build(definition, context, state)
            if not callable(getattr(adapter, "execute", None)):
                raise ClaudeCodeHarnessError("HARNESS_ADAPTER_INVALID")
            result = adapter.execute(
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
                    "HARNESS_BRANCH_REQUIRED",
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
            code = (
                result.error_code
                if result.error_code in _PROVIDER_AUTHORITY_ERROR_CODES
                else "HARNESS_FAILED"
            )
            return _failure(
                definition,
                context,
                code,
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
