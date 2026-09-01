from __future__ import annotations

from dataclasses import fields, replace
from datetime import datetime, timedelta, timezone

import pytest

from a_conductor.provider_config_store import ProviderConfigurationSnapshot
from a_conductor.provider_configuration import (
    EgressBoundary,
    HarnessStrategy,
    ProtocolFamily,
    ProviderConfiguration,
    ProviderEndpointConfig,
    ProviderHealth,
    ProviderModelConfiguration,
    ProviderObservation,
    ProviderTrustClass,
    QuotaSnapshot,
)
from a_conductor.provider_operator_view import (
    build_provider_operator_row,
    build_provider_operator_rows,
)

NOW = datetime(2026, 9, 1, 9, 30, tzinfo=timezone.utc)


def _profile(*, provider_id: str = "provider-glm-shared", display_name: str = "GLM Shared", enabled: bool = True) -> ProviderConfiguration:
    return ProviderConfiguration(
        provider_id=provider_id,
        display_name=display_name,
        provider_type="cloud-proxy",
        protocol_family=ProtocolFamily.OPENAI_COMPATIBLE,
        endpoint_ref=f"provider-config:{provider_id}/base-url",
        credential_ref=f"secret-ref:provider/{provider_id}/main",
        trust_class=ProviderTrustClass.TRUSTED_THIRD_PARTY,
        egress_boundary=EgressBoundary.EXTERNAL_THIRD_PARTY,
        harness_strategies=(HarnessStrategy.CLAUDE_CODE_CLI,),
        max_concurrency=2,
        models=(
            ProviderModelConfiguration(
                model_id="glm-5.3",
                display_name="GLM 5.3",
                actor_capabilities=(),
                supported_effort_levels=("MAX", "DEFAULT"),
                context_window_tokens=200_000,
            ),
        ),
        enabled=enabled,
    )


def _snapshot(
    *,
    profile: ProviderConfiguration | None = None,
    generation: int | None = 7,
    observation_generation: int | None = 7,
    health: ProviderHealth = ProviderHealth.AVAILABLE,
    observed_at: datetime = NOW - timedelta(seconds=30),
    include_endpoint: bool = True,
    include_observation: bool = True,
) -> ProviderConfigurationSnapshot:
    configured = profile or _profile()
    endpoint = (
        ProviderEndpointConfig(configured.endpoint_ref, "https://provider.example/v1")
        if include_endpoint
        else None
    )
    quota = QuotaSnapshot(
        window_type="5h",
        limit=100,
        used=20,
        remaining=80,
        reset_in_seconds=3_600,
        unit="requests",
    )
    observation = (
        ProviderObservation(
            provider_id=configured.provider_id,
            health=health,
            observed_at=observed_at,
            provenance="probe:test-provider-operator-view",
            latency_ms=25,
            quota=quota,
            configuration_generation=observation_generation,
        )
        if include_observation
        else None
    )
    return ProviderConfigurationSnapshot(
        profile=configured,
        endpoint=endpoint,
        generation=generation,
        observation=observation,
    )


def test_ready_row_is_truthful_and_secret_free() -> None:
    snapshot = _snapshot()
    row = build_provider_operator_row(snapshot, now=NOW)

    assert row.configured is True
    assert row.runtime_ready is True
    assert row.readiness_reason == "READY"
    assert row.task_authorization == "NOT_EVALUATED"
    assert row.configuration_generation == 7
    assert row.health is ProviderHealth.AVAILABLE
    assert row.observation_age_seconds == 30
    assert row.provenance == "probe:test-provider-operator-view"
    assert row.quota is snapshot.observation.quota
    assert row.models == snapshot.profile.models

    names = {field.name for field in fields(row)}
    assert {"credential_ref", "endpoint", "base_url", "profile"}.isdisjoint(names)
    assert "secret-ref:" not in repr(row)
    assert "https://provider.example" not in repr(row)


def test_configured_does_not_imply_ready_when_observation_is_missing() -> None:
    row = build_provider_operator_row(_snapshot(include_observation=False), now=NOW)
    assert row.configured is True
    assert row.runtime_ready is False
    assert row.readiness_reason == "PROVIDER_OBSERVATION_MISSING"


@pytest.mark.parametrize(
    ("snapshot", "reason"),
    [
        (_snapshot(include_endpoint=False), "PROVIDER_ENDPOINT_MISSING"),
        (_snapshot(generation=None), "PROVIDER_GENERATION_UNKNOWN"),
        (_snapshot(observation_generation=None), "PROVIDER_OBSERVATION_GENERATION_UNKNOWN"),
        (_snapshot(observation_generation=6), "PROVIDER_OBSERVATION_GENERATION_STALE"),
        (_snapshot(observed_at=NOW - timedelta(seconds=301)), "PROVIDER_OBSERVATION_STALE"),
        (_snapshot(observed_at=NOW + timedelta(seconds=1)), "PROVIDER_OBSERVATION_TIME_INVALID"),
        (_snapshot(profile=_profile(enabled=False)), "PROVIDER_DISABLED"),
    ],
)
def test_incomplete_or_stale_state_never_claims_ready(snapshot: ProviderConfigurationSnapshot, reason: str) -> None:
    row = build_provider_operator_row(snapshot, now=NOW)
    assert row.runtime_ready is False
    assert row.readiness_reason == reason


@pytest.mark.parametrize(
    "health",
    [
        ProviderHealth.UNKNOWN,
        ProviderHealth.DEGRADED,
        ProviderHealth.UNAVAILABLE,
        ProviderHealth.AUTH_FAILED,
        ProviderHealth.RATE_LIMITED,
        ProviderHealth.QUOTA_EXHAUSTED,
    ],
)
def test_non_available_health_is_displayed_without_becoming_ready(health: ProviderHealth) -> None:
    row = build_provider_operator_row(_snapshot(health=health), now=NOW)
    assert row.runtime_ready is False
    assert row.health is health
    assert row.readiness_reason == health.value


def test_endpoint_reference_mismatch_is_not_configured() -> None:
    snapshot = _snapshot()
    wrong = replace(
        snapshot,
        endpoint=ProviderEndpointConfig("provider-config:other/base-url", "https://provider.example/v1"),
    )
    row = build_provider_operator_row(wrong, now=NOW)
    assert row.configured is False
    assert row.runtime_ready is False
    assert row.readiness_reason == "PROVIDER_ENDPOINT_REF_MISMATCH"


def test_rows_are_sorted_deterministically_without_input_order_authority() -> None:
    alpha = _snapshot(profile=_profile(provider_id="provider-alpha", display_name="alpha"))
    zulu = _snapshot(profile=_profile(provider_id="provider-zulu", display_name="Zulu"))
    rows = build_provider_operator_rows((zulu, alpha), now=NOW)
    assert [row.provider_id for row in rows] == ["provider-alpha", "provider-zulu"]


def test_runtime_ready_never_claims_task_authorization() -> None:
    profile = replace(
        _profile(),
        trust_class=ProviderTrustClass.UNKNOWN,
        egress_boundary=EgressBoundary.UNKNOWN,
    )
    row = build_provider_operator_row(_snapshot(profile=profile), now=NOW)
    assert row.runtime_ready is True
    assert row.task_authorization == "NOT_EVALUATED"
    assert row.trust_class is ProviderTrustClass.UNKNOWN
    assert row.egress_boundary is EgressBoundary.UNKNOWN


def test_naive_clock_fails_closed() -> None:
    with pytest.raises(ValueError, match="aware datetime"):
        build_provider_operator_row(_snapshot(), now=datetime(2026, 9, 1, 9, 30))


@pytest.mark.parametrize("bad", [-1, True])
def test_invalid_freshness_window_fails_closed(bad) -> None:
    with pytest.raises(ValueError, match="max_age_seconds"):
        build_provider_operator_row(_snapshot(), now=NOW, max_age_seconds=bad)

@pytest.mark.parametrize("generation", [0, -1, True, 1 << 63])
def test_invalid_snapshot_generation_is_not_configured(generation) -> None:
    row = build_provider_operator_row(
        _snapshot(generation=generation, observation_generation=7),
        now=NOW,
    )

    assert row.configured is False
    assert row.runtime_ready is False
    assert row.readiness_reason == "PROVIDER_GENERATION_INVALID"
