"""Provider-neutral configuration and observed readiness for AHA-2.

This module contains no network client, credential resolver, scheduler, or
execution authority. Probes are injected; configuration never implies READY.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from ipaddress import ip_address
from typing import Mapping, Protocol
from urllib.parse import urlsplit


_PROVIDER_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
_CREDENTIAL_REF_RE = re.compile(r"^secret-ref:[A-Za-z0-9][A-Za-z0-9._:/-]{2,255}$")
_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{2,511}$")

_RUNTIME_BINDING_REF_RE = re.compile(r"^[a-z0-9][a-z0-9._:/-]{1,127}$")
_SCHEMA_VERSIONS = frozenset({"1.0.0", "1.1.0"})


@dataclass(frozen=True, slots=True)
class HarnessRuntimeBinding:
    """Typed per-model runtime binding for schema-1.1.0 provider profiles.

    Refs are opaque stable identifiers resolved against accepted provider /
    endpoint authority at the launch seam; display names are never matched.
    """

    harness_strategy: HarnessStrategy
    runtime_provider_ref: str
    runtime_model_ref: str

    def __post_init__(self) -> None:
        strategy = self.harness_strategy
        if not isinstance(strategy, HarnessStrategy):
            try:
                strategy = HarnessStrategy(strategy)
            except (TypeError, ValueError) as exc:
                raise ValueError("harness_strategy is invalid") from exc
        object.__setattr__(self, "harness_strategy", strategy)
        for name in ("runtime_provider_ref", "runtime_model_ref"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _RUNTIME_BINDING_REF_RE.fullmatch(value):
                raise ValueError(f"{name} is invalid")
            object.__setattr__(self, name, value)

    def as_dict(self) -> dict[str, str]:
        return {
            "harness_strategy": self.harness_strategy.value,
            "runtime_provider_ref": self.runtime_provider_ref,
            "runtime_model_ref": self.runtime_model_ref,
        }

    @classmethod
    def from_dict(cls, data: object) -> "HarnessRuntimeBinding":
        if not isinstance(data, Mapping):
            raise ValueError("runtime binding is invalid")
        allowed = {"harness_strategy", "runtime_provider_ref", "runtime_model_ref"}
        keys = set(data.keys())
        if keys != allowed:
            raise ValueError("runtime binding is invalid")
        return cls(
            harness_strategy=data["harness_strategy"],
            runtime_provider_ref=data["runtime_provider_ref"],
            runtime_model_ref=data["runtime_model_ref"],
        )


def _sanitized_selection_bytes(
    *,
    runtime_binding: HarnessRuntimeBinding,
    runtime_base_url: str,
    runtime_source_enabled: bool | None,
) -> bytes:
    """Canonical non-secret selection bytes for the selection digest.

    Only approved public fields participate; secrets, prompts, config reprs
    and raw config objects are excluded by construction."""
    parts = (
        runtime_binding.harness_strategy.value,
        runtime_binding.runtime_provider_ref,
        runtime_binding.runtime_model_ref,
        runtime_base_url.strip(),
        "" if runtime_source_enabled is None else ("enabled" if runtime_source_enabled else "disabled"),
    )
    return "".join(parts).encode("utf-8")


def runtime_selection_sha256(
    *,
    runtime_binding: HarnessRuntimeBinding,
    runtime_base_url: str,
    runtime_source_enabled: bool | None = None,
) -> str:
    """Sanitized runtime-selection digest (never contains secret values)."""
    import hashlib

    return hashlib.sha256(
        _sanitized_selection_bytes(
            runtime_binding=runtime_binding,
            runtime_base_url=runtime_base_url,
            runtime_source_enabled=runtime_source_enabled,
        )
    ).hexdigest()
_EVIDENCE_LEVELS = frozenset({"DECLARED", "OBSERVED", "VERIFIED", "UNKNOWN"})
_EFFORT_LEVELS = frozenset({"LOW", "HIGH", "MAX", "DEFAULT"})


def _require_text(value: str, field_name: str, *, max_length: int | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if max_length is not None and len(value) > max_length:
        raise ValueError(f"{field_name} is too long")
    return value


def _coerce_enum(value, enum_type, field_name: str):
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} is invalid") from exc


def _coerce_datetime(value: datetime | str, field_name: str) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an aware datetime") from exc
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be an aware datetime")
    return value.astimezone(timezone.utc)


def _datetime_text(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _coerce_datetime(value, "datetime").isoformat().replace("+00:00", "Z")


def _nonnegative_number(value, field_name: str):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{field_name} must be non-negative or None")
    return value


class ProtocolFamily(str, Enum):
    ANTHROPIC_MESSAGES = "ANTHROPIC_MESSAGES"
    OPENAI_COMPATIBLE = "OPENAI_COMPATIBLE"
    LOCAL = "LOCAL"
    CUSTOM = "CUSTOM"


class ProviderTrustClass(str, Enum):
    FIRST_PARTY = "FIRST_PARTY"
    TRUSTED_THIRD_PARTY = "TRUSTED_THIRD_PARTY"
    LOCAL = "LOCAL"
    UNKNOWN = "UNKNOWN"


class EgressBoundary(str, Enum):
    EXTERNAL_THIRD_PARTY = "EXTERNAL_THIRD_PARTY"
    EXTERNAL_FIRST_PARTY = "EXTERNAL_FIRST_PARTY"
    LOCAL_MACHINE = "LOCAL_MACHINE"
    NO_EGRESS = "NO_EGRESS"
    UNKNOWN = "UNKNOWN"


class HarnessStrategy(str, Enum):
    CLAUDE_CODE_CLI = "CLAUDE_CODE_CLI"
    DIRECT_API = "DIRECT_API"
    LOCAL_CLI = "LOCAL_CLI"
    ZCODE_APP_SERVER = "ZCODE_APP_SERVER"


class ProviderHealth(str, Enum):
    UNKNOWN = "UNKNOWN"
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    AUTH_FAILED = "AUTH_FAILED"
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"


class ProviderProbeState(str, Enum):
    OK = "OK"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    AUTH_FAILED = "AUTH_FAILED"
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"


@dataclass(frozen=True, slots=True)
class ActorCapabilityEvidence:
    capability: str
    evidence_level: str
    source: str

    def __post_init__(self) -> None:
        _require_text(self.capability, "capability", max_length=128)
        _require_text(self.source, "source", max_length=256)
        if self.evidence_level not in _EVIDENCE_LEVELS:
            raise ValueError("evidence_level is invalid")

    def as_dict(self) -> dict[str, str]:
        return {
            "capability": self.capability,
            "evidence_level": self.evidence_level,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class ProviderModelConfiguration:
    model_id: str
    display_name: str
    actor_capabilities: tuple[ActorCapabilityEvidence, ...] = ()
    supported_effort_levels: tuple[str, ...] = ()
    context_window_tokens: int | None = None
    runtime_binding: "HarnessRuntimeBinding | None" = None

    def __post_init__(self) -> None:
        _require_text(self.model_id, "model_id", max_length=128)
        _require_text(self.display_name, "display_name", max_length=128)
        capabilities = tuple(
            item
            if isinstance(item, ActorCapabilityEvidence)
            else ActorCapabilityEvidence(**item)
            for item in self.actor_capabilities
        )
        efforts = tuple(self.supported_effort_levels)
        if any(level not in _EFFORT_LEVELS for level in efforts):
            raise ValueError("supported_effort_levels contains an invalid value")
        if len(set(efforts)) != len(efforts):
            raise ValueError("supported_effort_levels must be unique")
        if self.context_window_tokens is not None:
            if isinstance(self.context_window_tokens, bool) or self.context_window_tokens < 1:
                raise ValueError("context_window_tokens must be positive or None")
        binding = self.runtime_binding
        if binding is not None and not isinstance(binding, HarnessRuntimeBinding):
            binding = HarnessRuntimeBinding.from_dict(binding)
        object.__setattr__(self, "runtime_binding", binding)
        object.__setattr__(self, "actor_capabilities", capabilities)
        object.__setattr__(self, "supported_effort_levels", efforts)

    def as_dict(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "display_name": self.display_name,
            "actor_capabilities": [item.as_dict() for item in self.actor_capabilities],
            "supported_effort_levels": list(self.supported_effort_levels),
            "context_window_tokens": self.context_window_tokens,
            "runtime_binding": None if self.runtime_binding is None else self.runtime_binding.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class ProviderConfiguration:
    provider_id: str
    display_name: str
    provider_type: str
    protocol_family: ProtocolFamily
    endpoint_ref: str
    credential_ref: str
    trust_class: ProviderTrustClass
    egress_boundary: EgressBoundary
    harness_strategies: tuple[HarnessStrategy, ...]
    max_concurrency: int
    models: tuple[ProviderModelConfiguration, ...]
    enabled: bool
    schema_version: str = "1.0.0"

    def __post_init__(self) -> None:
        if not _PROVIDER_ID_RE.fullmatch(self.provider_id):
            raise ValueError("provider_id is invalid")
        _require_text(self.display_name, "display_name", max_length=128)
        _require_text(self.provider_type, "provider_type", max_length=64)
        if not _REFERENCE_RE.fullmatch(self.endpoint_ref):
            raise ValueError("endpoint_ref is invalid")
        if not _CREDENTIAL_REF_RE.fullmatch(self.credential_ref):
            raise ValueError("credential_ref is invalid")
        protocol = _coerce_enum(self.protocol_family, ProtocolFamily, "protocol_family")
        trust = _coerce_enum(self.trust_class, ProviderTrustClass, "trust_class")
        egress = _coerce_enum(self.egress_boundary, EgressBoundary, "egress_boundary")
        harnesses = tuple(
            _coerce_enum(item, HarnessStrategy, "harness_strategies")
            for item in self.harness_strategies
        )
        if not harnesses or len(set(harnesses)) != len(harnesses):
            raise ValueError("harness_strategies must be non-empty and unique")
        models = tuple(
            item if isinstance(item, ProviderModelConfiguration) else ProviderModelConfiguration(**item)
            for item in self.models
        )
        if not models:
            raise ValueError("models must not be empty")
        if isinstance(self.max_concurrency, bool) or not 1 <= self.max_concurrency <= 64:
            raise ValueError("max_concurrency must be between 1 and 64")
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be boolean")
        if self.schema_version not in _SCHEMA_VERSIONS:
            raise ValueError("schema_version is unsupported")
        if self.schema_version == "1.0.0" and any(
            model.runtime_binding is not None for model in models
        ):
            raise ValueError("runtime bindings require schema_version 1.1.0")
        object.__setattr__(self, "protocol_family", protocol)
        object.__setattr__(self, "trust_class", trust)
        object.__setattr__(self, "egress_boundary", egress)
        object.__setattr__(self, "harness_strategies", harnesses)
        object.__setattr__(self, "models", models)

    def as_dict(self) -> dict[str, object]:
        return {
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "provider_type": self.provider_type,
            "protocol_family": self.protocol_family.value,
            "endpoint_ref": self.endpoint_ref,
            "credential_ref": self.credential_ref,
            "trust_class": self.trust_class.value,
            "egress_boundary": self.egress_boundary.value,
            "harness_strategies": [item.value for item in self.harness_strategies],
            "max_concurrency": self.max_concurrency,
            "models": [item.as_dict() for item in self.models],
            "enabled": self.enabled,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class ProviderEndpointConfig:
    endpoint_ref: str
    base_url: str

    def __post_init__(self) -> None:
        if not _REFERENCE_RE.fullmatch(self.endpoint_ref):
            raise ValueError("endpoint_ref is invalid")
        _require_text(self.base_url, "base_url", max_length=2048)
        if any(char.isspace() for char in self.base_url):
            raise ValueError("base_url is invalid")
        try:
            parsed = urlsplit(self.base_url)
            _ = parsed.port
        except ValueError as exc:
            raise ValueError("base_url is invalid") from exc
        if parsed.scheme.lower() not in {"http", "https"} or parsed.hostname is None:
            raise ValueError("base_url is invalid")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("base_url is invalid")
        if parsed.query or parsed.fragment:
            raise ValueError("base_url is invalid")
        if parsed.scheme.lower() == "http" and not _is_loopback_host(parsed.hostname):
            raise ValueError("external provider endpoints require HTTPS")


def _is_loopback_host(hostname: str) -> bool:
    if hostname.casefold() == "localhost":
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False


@dataclass(frozen=True, slots=True)
class QuotaSnapshot:
    window_type: str
    limit: int | float | None = None
    used: int | float | None = None
    remaining: int | float | None = None
    reset_at: datetime | str | None = None
    reset_in_seconds: int | None = None
    unit: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.window_type, "window_type", max_length=64)
        for field_name in ("limit", "used", "remaining"):
            object.__setattr__(self, field_name, _nonnegative_number(getattr(self, field_name), field_name))
        if self.reset_at is not None:
            object.__setattr__(self, "reset_at", _coerce_datetime(self.reset_at, "reset_at"))
        if self.reset_in_seconds is not None:
            if isinstance(self.reset_in_seconds, bool) or self.reset_in_seconds < 0:
                raise ValueError("reset_in_seconds must be non-negative or None")
        if self.unit is not None:
            _require_text(self.unit, "unit", max_length=32)

    def as_dict(self) -> dict[str, object]:
        return {
            "window_type": self.window_type,
            "limit": self.limit,
            "used": self.used,
            "remaining": self.remaining,
            "reset_at": _datetime_text(self.reset_at),
            "reset_in_seconds": self.reset_in_seconds,
            "unit": self.unit,
        }


@dataclass(frozen=True, slots=True)
class ProviderObservation:
    provider_id: str
    health: ProviderHealth
    observed_at: datetime | str
    provenance: str
    latency_ms: int | None = None
    quota: QuotaSnapshot | None = None
    schema_version: str = "1.0.0"
    configuration_generation: int | None = None

    def __post_init__(self) -> None:
        if not _PROVIDER_ID_RE.fullmatch(self.provider_id):
            raise ValueError("provider_id is invalid")
        health = _coerce_enum(self.health, ProviderHealth, "health")
        observed = _coerce_datetime(self.observed_at, "observed_at")
        _require_text(self.provenance, "provenance", max_length=512)
        if self.latency_ms is not None:
            if isinstance(self.latency_ms, bool) or self.latency_ms < 0:
                raise ValueError("latency_ms must be non-negative or None")
        quota = self.quota
        if quota is not None and not isinstance(quota, QuotaSnapshot):
            quota = QuotaSnapshot(**quota)
        if self.schema_version != "1.0.0":
            raise ValueError("schema_version is unsupported")
        if self.configuration_generation is not None:
            if (
                isinstance(self.configuration_generation, bool)
                or not isinstance(self.configuration_generation, int)
                or self.configuration_generation < 1
            ):
                raise ValueError("configuration_generation must be positive or None")
        object.__setattr__(self, "health", health)
        object.__setattr__(self, "observed_at", observed)
        object.__setattr__(self, "quota", quota)
    def as_dict(self) -> dict[str, object]:
        return {
            "provider_id": self.provider_id,
            "health": self.health.value,
            "observed_at": _datetime_text(self.observed_at),
            "provenance": self.provenance,
            "latency_ms": self.latency_ms,
            "quota": self.quota.as_dict() if self.quota is not None else None,
            "schema_version": self.schema_version,
            "configuration_generation": self.configuration_generation,
        }


@dataclass(frozen=True, slots=True)
class ProviderProbeResult:
    state: ProviderProbeState
    latency_ms: int | None = None
    quota: QuotaSnapshot | None = None

    def __post_init__(self) -> None:
        state = _coerce_enum(self.state, ProviderProbeState, "state")
        if self.latency_ms is not None:
            if isinstance(self.latency_ms, bool) or self.latency_ms < 0:
                raise ValueError("latency_ms must be non-negative or None")
        quota = self.quota
        if quota is not None and not isinstance(quota, QuotaSnapshot):
            quota = QuotaSnapshot(**quota)
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "quota", quota)


class ProviderProbe(Protocol):
    def probe(
        self,
        profile: ProviderConfiguration,
        endpoint: ProviderEndpointConfig,
    ) -> ProviderProbeResult: ...


_PROBE_HEALTH = {
    ProviderProbeState.OK: ProviderHealth.AVAILABLE,
    ProviderProbeState.DEGRADED: ProviderHealth.DEGRADED,
    ProviderProbeState.UNAVAILABLE: ProviderHealth.UNAVAILABLE,
    ProviderProbeState.AUTH_FAILED: ProviderHealth.AUTH_FAILED,
    ProviderProbeState.RATE_LIMITED: ProviderHealth.RATE_LIMITED,
    ProviderProbeState.QUOTA_EXHAUSTED: ProviderHealth.QUOTA_EXHAUSTED,
}


def observe_provider(
    profile: ProviderConfiguration,
    endpoint: ProviderEndpointConfig,
    probe: ProviderProbe,
    *,
    observed_at: datetime | str,
    provenance: str,
) -> ProviderObservation:
    if endpoint.endpoint_ref != profile.endpoint_ref:
        raise ValueError("endpoint_ref does not match provider configuration")
    observed = _coerce_datetime(observed_at, "observed_at")
    _require_text(provenance, "provenance", max_length=512)
    result = probe.probe(profile, endpoint)
    if not isinstance(result, ProviderProbeResult):
        raise ValueError("probe must return ProviderProbeResult")
    health = _PROBE_HEALTH[result.state]
    if (
        result.quota is not None
        and result.quota.remaining is not None
        and result.quota.remaining <= 0
    ):
        health = ProviderHealth.QUOTA_EXHAUSTED
    return ProviderObservation(
        provider_id=profile.provider_id,
        health=health,
        observed_at=observed,
        provenance=provenance,
        latency_ms=result.latency_ms,
        quota=result.quota,
    )


def is_provider_ready(
    profile: ProviderConfiguration,
    observation: ProviderObservation | None,
    *,
    now: datetime | str,
    max_age_seconds: int = 300,
    expected_generation: int | None = None,
) -> bool:
    if isinstance(max_age_seconds, bool) or max_age_seconds < 0:
        raise ValueError("max_age_seconds must be non-negative")
    if not profile.enabled or observation is None:
        return False
    if observation.provider_id != profile.provider_id:
        return False
    if observation.health is not ProviderHealth.AVAILABLE:
        return False
    if expected_generation is not None:
        if (
            observation.configuration_generation is None
            or observation.configuration_generation != expected_generation
        ):
            return False
    current = _coerce_datetime(now, "now")
    age = (current - observation.observed_at).total_seconds()
    return 0 <= age <= max_age_seconds
