"""Truthful read-only provider projection for the AHA-7 operator UI.

This module is presentation-only. It does not read SQLite, resolve credentials,
probe providers, evaluate task policy, route work, reserve capacity, or launch a
harness. Runtime readiness reuses the accepted provider readiness authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from .provider_config_store import ProviderConfigurationSnapshot
from .provider_configuration import (
    EgressBoundary,
    HarnessStrategy,
    ProviderHealth,
    ProviderModelConfiguration,
    ProviderTrustClass,
    QuotaSnapshot,
    is_provider_ready,
)


@dataclass(frozen=True, slots=True)
class ProviderOperatorRow:
    provider_id: str
    display_name: str
    provider_type: str
    enabled: bool
    configured: bool
    runtime_ready: bool
    readiness_reason: str
    task_authorization: str
    models: tuple[ProviderModelConfiguration, ...]
    harness_strategies: tuple[HarnessStrategy, ...]
    trust_class: ProviderTrustClass
    egress_boundary: EgressBoundary
    max_concurrency: int
    configuration_generation: int | None
    health: ProviderHealth | None
    observed_at: datetime | None
    observation_age_seconds: float | None
    provenance: str | None
    latency_ms: int | None
    quota: QuotaSnapshot | None


def _utc_now(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("now must be an aware datetime")
    return value.astimezone(timezone.utc)


def _validate_max_age(max_age_seconds: int) -> int:
    if isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, int) or max_age_seconds < 0:
        raise ValueError("max_age_seconds must be a non-negative integer")
    return max_age_seconds


def _readiness_reason(
    snapshot: ProviderConfigurationSnapshot,
    *,
    now: datetime,
    max_age_seconds: int,
) -> tuple[bool, bool, str, float | None]:
    profile = snapshot.profile
    endpoint = snapshot.endpoint
    observation = snapshot.observation
    generation = snapshot.generation

    endpoint_valid = endpoint is not None and endpoint.endpoint_ref == profile.endpoint_ref
    configured = endpoint_valid and generation is not None

    age = None
    if observation is not None:
        age = (now - observation.observed_at).total_seconds()

    if endpoint is None:
        return configured, False, "PROVIDER_ENDPOINT_MISSING", age
    if endpoint.endpoint_ref != profile.endpoint_ref:
        return configured, False, "PROVIDER_ENDPOINT_REF_MISMATCH", age
    if generation is None:
        return configured, False, "PROVIDER_GENERATION_UNKNOWN", age
    if not profile.enabled:
        return configured, False, "PROVIDER_DISABLED", age
    if observation is None:
        return configured, False, "PROVIDER_OBSERVATION_MISSING", age
    if observation.provider_id != profile.provider_id:
        return configured, False, "PROVIDER_OBSERVATION_ID_MISMATCH", age
    if observation.configuration_generation is None:
        return configured, False, "PROVIDER_OBSERVATION_GENERATION_UNKNOWN", age
    if observation.configuration_generation != generation:
        return configured, False, "PROVIDER_OBSERVATION_GENERATION_STALE", age
    if age is None or age < 0:
        return configured, False, "PROVIDER_OBSERVATION_TIME_INVALID", age
    if age > max_age_seconds:
        return configured, False, "PROVIDER_OBSERVATION_STALE", age
    if observation.health is not ProviderHealth.AVAILABLE:
        return configured, False, observation.health.value, age

    ready = is_provider_ready(
        profile,
        observation,
        now=now,
        max_age_seconds=max_age_seconds,
        expected_generation=generation,
    )
    return configured, ready, "READY" if ready else "PROVIDER_NOT_READY", age


def build_provider_operator_row(
    snapshot: ProviderConfigurationSnapshot,
    *,
    now: datetime,
    max_age_seconds: int = 300,
) -> ProviderOperatorRow:
    if not isinstance(snapshot, ProviderConfigurationSnapshot):
        raise ValueError("snapshot must be ProviderConfigurationSnapshot")
    current = _utc_now(now)
    freshness = _validate_max_age(max_age_seconds)
    configured, runtime_ready, reason, age = _readiness_reason(
        snapshot,
        now=current,
        max_age_seconds=freshness,
    )
    observation = snapshot.observation
    profile = snapshot.profile
    return ProviderOperatorRow(
        provider_id=profile.provider_id,
        display_name=profile.display_name,
        provider_type=profile.provider_type,
        enabled=profile.enabled,
        configured=configured,
        runtime_ready=runtime_ready,
        readiness_reason=reason,
        task_authorization="NOT_EVALUATED",
        models=profile.models,
        harness_strategies=profile.harness_strategies,
        trust_class=profile.trust_class,
        egress_boundary=profile.egress_boundary,
        max_concurrency=profile.max_concurrency,
        configuration_generation=snapshot.generation,
        health=None if observation is None else observation.health,
        observed_at=None if observation is None else observation.observed_at,
        observation_age_seconds=age,
        provenance=None if observation is None else observation.provenance,
        latency_ms=None if observation is None else observation.latency_ms,
        quota=None if observation is None else observation.quota,
    )


def build_provider_operator_rows(
    snapshots: Iterable[ProviderConfigurationSnapshot],
    *,
    now: datetime,
    max_age_seconds: int = 300,
) -> tuple[ProviderOperatorRow, ...]:
    rows = tuple(
        build_provider_operator_row(
            snapshot,
            now=now,
            max_age_seconds=max_age_seconds,
        )
        for snapshot in snapshots
    )
    return tuple(sorted(rows, key=lambda row: (row.display_name.casefold(), row.provider_id.casefold())))
