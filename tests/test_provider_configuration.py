from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from a_conductor.provider_configuration import (
    ActorCapabilityEvidence,
    EgressBoundary,
    HarnessStrategy,
    ProviderConfiguration,
    ProviderEndpointConfig,
    ProviderHealth,
    ProviderModelConfiguration,
    ProviderProbeResult,
    ProviderProbeState,
    ProviderTrustClass,
    ProtocolFamily,
    QuotaSnapshot,
    is_provider_ready,
    observe_provider,
)


NOW = datetime(2026, 8, 28, 1, 0, tzinfo=timezone.utc)

def make_profile(*, enabled: bool = True) -> ProviderConfiguration:
    return ProviderConfiguration(
        provider_id="provider-glm-shared",
        display_name="GLM Shared Provider",
        provider_type="cloud-proxy",
        protocol_family=ProtocolFamily.ANTHROPIC_MESSAGES,
        endpoint_ref="provider-config:glm-shared/base-url",
        credential_ref="secret-ref:provider/glm-shared/main",
        trust_class=ProviderTrustClass.TRUSTED_THIRD_PARTY,
        egress_boundary=EgressBoundary.EXTERNAL_THIRD_PARTY,
        harness_strategies=(HarnessStrategy.CLAUDE_CODE_CLI,),
        max_concurrency=1,
        models=(
            ProviderModelConfiguration(
                model_id="glm-5.3",
                display_name="GLM-5.3",
                actor_capabilities=(
                    ActorCapabilityEvidence(
                        capability="documentation",
                        evidence_level="DECLARED",
                        source="operator-config",
                    ),
                ),
                supported_effort_levels=("HIGH", "MAX"),
            ),
        ),
        enabled=enabled,
    )


def test_provider_configuration_is_non_secret_and_schema_aligned() -> None:
    profile = make_profile()
    assert profile.credential_ref.startswith("secret-ref:")
    names = set(profile.__dataclass_fields__)
    assert not names.intersection(
        {"api_key", "token", "password", "secret_value", "authorization_header"}
    )
    with pytest.raises(ValueError, match="credential_ref"):
        ProviderConfiguration(**{**profile.as_dict(), "credential_ref": "raw-token-value"})


def test_endpoint_accepts_https_and_loopback_http_only() -> None:
    https = ProviderEndpointConfig(
        endpoint_ref="provider-config:cloud/base-url",
        base_url="https://api.example.test/v1",
    )
    local = ProviderEndpointConfig(
        endpoint_ref="provider-config:local/base-url",
        base_url="http://127.0.0.1:3456",
    )
    assert https.base_url.startswith("https://")
    assert local.base_url.startswith("http://127.0.0.1")
    with pytest.raises(ValueError, match="HTTPS"):
        ProviderEndpointConfig(
            endpoint_ref="provider-config:bad/base-url",
            base_url="http://api.example.test/v1",
        )


def test_endpoint_rejects_secret_smuggling_components() -> None:
    bad_urls = (
        "https://user:pass@example.test/v1",
        "https://example.test/v1?token=abc",
        "https://example.test/v1#secret",
    )
    for index, url in enumerate(bad_urls):
        with pytest.raises(ValueError, match="base_url"):
            ProviderEndpointConfig(
                endpoint_ref=f"provider-config:bad-{index}/base-url",
                base_url=url,
            )


class FakeProbe:
    def __init__(self, result: ProviderProbeResult) -> None:
        self.result = result
        self.calls = []

    def probe(self, profile, endpoint):
        self.calls.append((profile.provider_id, endpoint.endpoint_ref))
        return self.result


def test_fake_probe_normalizes_available_quota_observation() -> None:
    profile = make_profile()
    endpoint = ProviderEndpointConfig(
        endpoint_ref=profile.endpoint_ref,
        base_url="https://api.example.test/v1",
    )
    probe = FakeProbe(
        ProviderProbeResult(
            state=ProviderProbeState.OK,
            latency_ms=120,
            quota=QuotaSnapshot(
                window_type="ROLLING_5H",
                limit=100,
                used=25,
                remaining=75,
                reset_at=NOW + timedelta(hours=4),
                reset_in_seconds=14400,
                unit="requests",
            ),
        )
    )
    observation = observe_provider(
        profile,
        endpoint,
        probe,
        observed_at=NOW,
        provenance="fake-probe:test",
    )
    assert observation.health is ProviderHealth.AVAILABLE
    assert observation.quota is not None and observation.quota.remaining == 75
    assert probe.calls == [(profile.provider_id, endpoint.endpoint_ref)]
    assert is_provider_ready(profile, observation, now=NOW)


def test_quota_zero_and_auth_failures_are_typed() -> None:
    profile = make_profile()
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test")
    exhausted = observe_provider(
        profile,
        endpoint,
        FakeProbe(
            ProviderProbeResult(
                state=ProviderProbeState.OK,
                quota=QuotaSnapshot(window_type="daily", remaining=0),
            )
        ),
        observed_at=NOW,
        provenance="fake:test",
    )
    assert exhausted.health is ProviderHealth.QUOTA_EXHAUSTED
    auth_failed = observe_provider(
        profile,
        endpoint,
        FakeProbe(ProviderProbeResult(state=ProviderProbeState.AUTH_FAILED)),
        observed_at=NOW,
        provenance="fake:test",
    )
    assert auth_failed.health is ProviderHealth.AUTH_FAILED
    assert not is_provider_ready(profile, auth_failed, now=NOW)


def test_stale_missing_or_disabled_provider_is_never_ready() -> None:
    profile = make_profile()
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test")
    observation = observe_provider(
        profile,
        endpoint,
        FakeProbe(ProviderProbeResult(state=ProviderProbeState.OK)),
        observed_at=NOW,
        provenance="fake:test",
    )
    assert not is_provider_ready(
        profile,
        observation,
        now=NOW + timedelta(seconds=301),
        max_age_seconds=300,
    )
    assert not is_provider_ready(profile, None, now=NOW)
    assert not is_provider_ready(make_profile(enabled=False), observation, now=NOW)


@pytest.mark.parametrize(
    ("state", "expected_health"),
    (
        (ProviderProbeState.DEGRADED, ProviderHealth.DEGRADED),
        (ProviderProbeState.UNAVAILABLE, ProviderHealth.UNAVAILABLE),
        (ProviderProbeState.RATE_LIMITED, ProviderHealth.RATE_LIMITED),
        (ProviderProbeState.QUOTA_EXHAUSTED, ProviderHealth.QUOTA_EXHAUSTED),
    ),
)
def test_fake_probe_normalizes_non_ready_states(state, expected_health) -> None:
    profile = make_profile()
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test")
    observation = observe_provider(
        profile,
        endpoint,
        FakeProbe(ProviderProbeResult(state=state)),
        observed_at=NOW,
        provenance="fake:test",
    )
    assert observation.health is expected_health
    assert not is_provider_ready(profile, observation, now=NOW)


def test_provider_readiness_has_no_authorization_field_or_side_effect() -> None:
    profile = make_profile()
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test")
    observation = observe_provider(
        profile,
        endpoint,
        FakeProbe(ProviderProbeResult(state=ProviderProbeState.OK)),
        observed_at=NOW,
        provenance="fake:test",
    )
    assert is_provider_ready(profile, observation, now=NOW)
    assert "authorized" not in profile.__dataclass_fields__
    assert "authorization" not in profile.__dataclass_fields__
    assert "authorized" not in observation.__dataclass_fields__
    assert "authorization" not in observation.__dataclass_fields__
