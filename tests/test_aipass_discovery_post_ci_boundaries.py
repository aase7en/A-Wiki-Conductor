from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from a_conductor.aipass_discovery import AiPassDiscoveryState, build_aipass_discovery


NOW = datetime(2026, 9, 3, 8, 0, tzinfo=timezone.utc)


def _models(model_id: str = "safe-model", *, name: str = "Safe Model") -> dict:
    return {"object": "list", "data": [{"id": model_id, "name": name, "is_default": False}]}


def _build(*, model_id: str = "safe-model", name: str = "Safe Model", **kwargs):
    return build_aipass_discovery(
        models_payload=_models(model_id, name=name),
        quota_payload=kwargs.pop("quota_payload", {}),
        observed_at=kwargs.pop("observed_at", NOW),
        now=kwargs.pop("now", NOW),
        configuration_generation=kwargs.pop("configuration_generation", 1),
        stale_after_seconds=kwargs.pop("stale_after_seconds", 60),
        **kwargs,
    )


@pytest.mark.parametrize(
    "unsafe_name",
    (
        'xpassword="abcdef0123456789abcdef"',
        "xpassword='abcdef0123456789abcdef'",
        'xsession_id: "abcdef0123456789abcdef"',
        "xsession_id: 'abcdef0123456789abcdef'",
        'fooAuthorization: "abcdef0123456789abcdef"',
        '{"password":"abcdef0123456789abcdef"}',
        "{'auth':'abcdef0123456789abcdef'}",
        '{"password":"p@ss!"}',
        "xauth='short!'",
    ),
)
def test_quoted_or_object_shaped_generic_credentials_fall_back(unsafe_name: str) -> None:
    result = _build(name=unsafe_name)
    assert result.state is AiPassDiscoveryState.OK
    assert result.models[0].name == "safe-model"
    assert unsafe_name not in str(result.to_dict())


def test_configuration_generation_matches_canonical_bounded_domain() -> None:
    maximum = (1 << 63) - 1
    accepted = _build(configuration_generation=maximum)
    assert accepted.state is AiPassDiscoveryState.OK
    assert accepted.configuration_generation == maximum

    for invalid in ((1 << 63), 10**100):
        rejected = _build(configuration_generation=invalid)
        assert rejected.state is AiPassDiscoveryState.MALFORMED
        assert rejected.reason_code == "DISCOVERY_CONTEXT_INVALID"
        assert rejected.configuration_generation is None


@pytest.mark.parametrize(
    "unsafe_name",
    (
        "backend 8.8.8.8",
        "node 2001:db8::1",
        "node fe80::1",
        "node ::1",
        "server example.com",
        "endpoint api.example.com",
    ),
)
def test_embedded_public_endpoint_tokens_fall_back(unsafe_name: str) -> None:
    result = _build(name=unsafe_name)
    assert result.state is AiPassDiscoveryState.OK
    assert result.models[0].name == "safe-model"
    assert unsafe_name not in str(result.to_dict())


def test_embedded_endpoint_guard_preserves_semantic_and_version_text() -> None:
    for safe_name in (
        "IPv4 Research",
        "IPv6 Research",
        "Domain Research",
        "API Example Model",
        "Localhost Model",
        "Version 1.2.3",
        "model-1.2.3.4",
    ):
        result = _build(name=safe_name)
        assert result.state is AiPassDiscoveryState.OK
        assert result.models[0].name == safe_name


@pytest.mark.parametrize("unsafe_id", ("8.8.8.8", "localhost", "api.example.com"))
def test_endpoint_shaped_model_ids_fail_closed(unsafe_id: str) -> None:
    result = _build(model_id=unsafe_id, name="safe")
    assert result.state is AiPassDiscoveryState.MALFORMED
    assert result.reason_code == "MODEL_PAYLOAD_MALFORMED"
    assert unsafe_id not in str(result.to_dict())


def test_model_id_endpoint_guard_preserves_real_dotted_model_ids() -> None:
    for safe_id in (
        "gemini-3.1-flash-lite",
        "gpt-4.1",
        "FLUX.2-pro",
        "provider@model-v1",
    ):
        result = _build(model_id=safe_id, name=safe_id)
        assert result.state is AiPassDiscoveryState.OK
        assert result.models[0].model_id == safe_id


def test_huge_integer_stale_budget_is_accepted_without_float_overflow() -> None:
    result = _build(stale_after_seconds=10**400)
    assert result.state is AiPassDiscoveryState.OK
    assert result.reason_code == "DISCOVERY_OK"


def test_extreme_aware_datetime_utc_normalization_returns_typed_malformed() -> None:
    extreme = datetime(1, 1, 1, 0, 0, tzinfo=timezone(timedelta(hours=14)))
    result = _build(observed_at=extreme, now=NOW)
    assert result.state is AiPassDiscoveryState.MALFORMED
    assert result.reason_code == "DISCOVERY_CONTEXT_INVALID"


def test_extreme_quota_reset_time_returns_typed_malformed() -> None:
    quota = {
        "limit": 10,
        "used": 1,
        "available": 9,
        "fetchedAt": int(NOW.timestamp() * 1000),
        "periodEndsAt": "0001-01-01T00:00:00+14:00",
    }
    result = _build(quota_payload=quota)
    assert result.state is AiPassDiscoveryState.MALFORMED
    assert result.reason_code == "QUOTA_PAYLOAD_MALFORMED"
