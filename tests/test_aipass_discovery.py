from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from a_conductor.aipass_discovery import (
    AiPassDiscoveredModel,
    AiPassDiscoverySnapshot,
    AiPassDiscoveryState,
    build_aipass_discovery,
)


NOW = datetime(2026, 9, 3, 8, 0, tzinfo=timezone.utc)


def _models(*items: dict) -> dict:
    return {"object": "list", "data": list(items)}


def _model(
    model_id: str = "gemini-3.1-flash-lite",
    *,
    name: str = "Gemini Flash Lite",
    free_credit: bool | None = True,
    kind: str | None = "chat",
) -> dict:
    item = {"id": model_id, "name": name, "is_default": False}
    if free_credit is not None:
        item["free_credit"] = free_credit
    if kind is not None:
        item["kind"] = kind
    return item


def _quota() -> dict:
    return {
        "limit": 10000,
        "used": 167,
        "available": 9833,
        "periodEndsAt": "2026-09-30T17:00:00Z",
        "video": {"limit": 10, "used": 2, "remaining": 8, "period": "month"},
        "fetchedAt": int(NOW.timestamp() * 1000),
    }


def _build(models: object = None, quota: object = None, **kwargs):
    observed_at = kwargs.pop("observed_at", NOW)
    if quota is None:
        quota = _quota()
        quota["fetchedAt"] = int(observed_at.timestamp() * 1000)
    return build_aipass_discovery(
        models_payload=_models(_model()) if models is None else models,
        quota_payload=quota,
        observed_at=observed_at,
        now=kwargs.pop("now", NOW),
        configuration_generation=kwargs.pop("configuration_generation", 7),
        stale_after_seconds=kwargs.pop("stale_after_seconds", 60),
        **kwargs,
    )


def test_valid_discovery_is_canonical_generation_bound_and_quota_reuses_existing_type() -> None:
    payload = _models(
        _model("z-model", name="Z", free_credit=False),
        _model("a-model", name="A", free_credit=True),
    )
    result = _build(models=payload)
    assert result.state is AiPassDiscoveryState.OK
    assert [item.model_id for item in result.models] == ["a-model", "z-model"]
    assert result.configuration_generation == 7
    assert result.shared_quota.window_type == "aipass_shared_credits"
    assert result.shared_quota.remaining == 9833
    assert result.video_quota.window_type == "aipass_video"
    assert result.video_quota.remaining == 8


def test_missing_free_credit_stays_unknown_and_unknown_optional_fields_do_not_gain_authority() -> None:
    model = _model(free_credit=None)
    model.update({"description": "safe public description", "options": {"future": True}, "ready": True})
    result = _build(models=_models(model), quota={})
    assert result.state is AiPassDiscoveryState.OK
    assert result.models[0].free_credit is None
    assert result.shared_quota is None
    encoded = result.to_dict()
    assert "ready" not in encoded["models"][0]
    assert "options" not in encoded["models"][0]


def test_empty_model_inventory_is_explicit_not_provider_ready_truth() -> None:
    result = _build(models=_models(), quota={})
    assert result.state is AiPassDiscoveryState.EMPTY
    assert result.models == ()
    assert result.shared_quota is None


def test_no_fake_payloads_is_unavailable_without_network_fallback() -> None:
    result = build_aipass_discovery(
        models_payload=None,
        quota_payload=None,
        observed_at=NOW,
        now=NOW,
        configuration_generation=3,
    )
    assert result.state is AiPassDiscoveryState.UNAVAILABLE
    assert result.models == ()
    assert result.reason_code == "DISCOVERY_UNAVAILABLE"


def test_stale_snapshot_preserves_observed_facts_but_state_is_stale() -> None:
    result = _build(observed_at=NOW - timedelta(seconds=61), now=NOW, stale_after_seconds=60)
    assert result.state is AiPassDiscoveryState.STALE
    assert result.models
    assert result.shared_quota is not None
    assert result.reason_code == "DISCOVERY_STALE"


def test_unsupported_model_envelope_is_typed_without_raw_payload_echo() -> None:
    result = _build(models={"object": "future-list", "data": []}, quota={})
    assert result.state is AiPassDiscoveryState.UNSUPPORTED
    assert result.reason_code == "MODEL_PAYLOAD_UNSUPPORTED"
    assert "future-list" not in str(result.to_dict())


def test_malformed_duplicate_or_unsafe_models_fail_closed_as_typed_state() -> None:
    cases = (
        {"object": "list", "data": "not-a-list"},
        _models(_model("same"), _model("same")),
        _models(_model("https://bad.example/model")),
        _models({"id": "model-a", "name": "A", "free_credit": "yes"}),
    )
    for models in cases:
        result = _build(models=models, quota={})
        assert result.state is AiPassDiscoveryState.MALFORMED
        assert result.reason_code == "MODEL_PAYLOAD_MALFORMED"
        assert result.models == ()


def test_quota_contradiction_negative_and_nonfinite_fail_closed_without_partial_truth() -> None:
    cases = (
        {"limit": 100, "used": 70, "available": 40},
        {"limit": 100, "used": -1, "available": 101},
        {"limit": float("nan"), "used": 0, "available": 0},
        {"limit": 100, "used": 10, "available": 90, "video": {"limit": 10, "used": 9, "remaining": 9}},
    )
    for quota in cases:
        result = _build(quota=quota)
        assert result.state is AiPassDiscoveryState.MALFORMED
        assert result.reason_code == "QUOTA_PAYLOAD_MALFORMED"
        assert result.models == ()
        assert result.shared_quota is None


@pytest.mark.parametrize(
    ("limit", "used", "remaining"),
    (
        (10**12, 10**12 - 500, 0),
        (10**15, 10**15 - 100_000, 0),
        ((1 << 53) - 1, (1 << 53) - 1 - 1_000_000, 0),
    ),
)
def test_large_quota_contradictions_do_not_gain_relative_tolerance(
    limit: int, used: int, remaining: int,
) -> None:
    result = _build(
        quota={
            "limit": limit,
            "used": used,
            "available": remaining,
            "fetchedAt": int(NOW.timestamp() * 1000),
        }
    )
    assert result.state is AiPassDiscoveryState.MALFORMED
    assert result.reason_code == "QUOTA_PAYLOAD_MALFORMED"
    assert result.shared_quota is None


def test_generation_and_time_contract_fail_closed_before_projection() -> None:
    for generation in (0, -1, True):
        result = _build(configuration_generation=generation)
        assert result.state is AiPassDiscoveryState.MALFORMED
        assert result.reason_code == "DISCOVERY_CONTEXT_INVALID"
    result = _build(observed_at=NOW + timedelta(seconds=1), now=NOW)
    assert result.state is AiPassDiscoveryState.MALFORMED
    assert result.reason_code == "DISCOVERY_CONTEXT_INVALID"


def test_cached_quota_age_participates_in_snapshot_staleness() -> None:
    quota = _quota()
    quota["fetchedAt"] = int((NOW - timedelta(seconds=61)).timestamp() * 1000)
    result = _build(quota=quota, observed_at=NOW, now=NOW, stale_after_seconds=60)
    assert result.state is AiPassDiscoveryState.STALE
    assert result.reason_code == "DISCOVERY_STALE"
    assert result.shared_quota is not None
    assert result.quota_fetched_at == NOW - timedelta(seconds=61)


def test_future_or_unbounded_quota_fetched_at_fails_closed() -> None:
    future = _quota()
    future["fetchedAt"] = int((NOW + timedelta(seconds=1)).timestamp() * 1000)
    missing = _quota()
    missing.pop("fetchedAt")
    for quota in (future, missing):
        result = _build(quota=quota)
        assert result.state is AiPassDiscoveryState.MALFORMED
        assert result.reason_code == "QUOTA_PAYLOAD_MALFORMED"
        assert result.shared_quota is None


def test_untrusted_display_metadata_cannot_serialize_secret_or_endpoint_shapes() -> None:
    unsafe_names = (
        "Authorization: Bearer TOPSECRET",
        "https://bridge.example.invalid/private",
        r"C:\\Users\\name\\secret.txt",
    )
    for name in unsafe_names:
        model = _model("model-a", name=name)
        model["description"] = "Cookie=session-secret"
        result = _build(models=_models(model), quota={})
        assert result.state is AiPassDiscoveryState.OK
        assert result.models[0].name == "model-a"
        encoded = str(result.to_dict())
        assert "TOPSECRET" not in encoded
        assert "bridge.example.invalid" not in encoded
        assert "session-secret" not in encoded


def test_extreme_quota_number_fails_typed_without_exception_escape() -> None:
    huge = 10**400
    quota = {
        "limit": huge,
        "used": 0,
        "available": huge,
        "fetchedAt": int(NOW.timestamp() * 1000),
    }
    result = _build(quota=quota)
    assert result.state is AiPassDiscoveryState.MALFORMED
    assert result.reason_code == "QUOTA_PAYLOAD_MALFORMED"


@pytest.mark.parametrize(
    "unsafe_model_id",
    (
        "".join(("gh", "p_FAKE")),
        "".join(("sk", "-ant-FAKE")),
    ),
)
def test_credential_shaped_model_id_fails_closed_without_serialization(unsafe_model_id: str) -> None:
    now = NOW
    result = build_aipass_discovery(
        models_payload={"object": "list", "data": [{"id": unsafe_model_id, "name": "safe"}]},
        quota_payload=None,
        observed_at=now,
        now=now,
        configuration_generation=1,
    )
    assert result.state is AiPassDiscoveryState.MALFORMED
    assert result.reason_code == "MODEL_PAYLOAD_MALFORMED"
    assert result.models == ()
    assert unsafe_model_id not in str(result.to_dict())


@pytest.mark.parametrize(
    "unsafe_name",
    (
        "".join(("gh", "p_FAKE")),
        "".join(("Bearer ", "A" * 24)),
    ),
)
def test_credential_shaped_display_name_falls_back_without_serialization(unsafe_name: str) -> None:
    now = NOW
    result = build_aipass_discovery(
        models_payload={"object": "list", "data": [{"id": "safe-model", "name": unsafe_name}]},
        quota_payload=None,
        observed_at=now,
        now=now,
        configuration_generation=1,
    )
    assert result.state is AiPassDiscoveryState.OK
    assert result.models[0].name == "safe-model"
    assert unsafe_name not in str(result.to_dict())


def test_semantic_bearer_display_name_is_not_mistaken_for_a_credential() -> None:
    result = build_aipass_discovery(
        models_payload={"object": "list", "data": [{"id": "safe-model", "name": "Bearer Capacity"}]},
        quota_payload=None,
        observed_at=NOW,
        now=NOW,
        configuration_generation=1,
    )
    assert result.state is AiPassDiscoveryState.OK
    assert result.models[0].name == "Bearer Capacity"


def test_generic_sk_secret_shaped_model_id_fails_closed_without_overrejecting_semantic_ids() -> None:
    now = NOW
    unsafe = "sk-proj-" + "A" * 24
    bad = build_aipass_discovery(
        models_payload={"object": "list", "data": [{"id": unsafe, "name": "safe"}]},
        quota_payload=None,
        observed_at=now, now=now, configuration_generation=1,
    )
    assert bad.state is AiPassDiscoveryState.MALFORMED
    assert unsafe not in str(bad.to_dict())

    for safe_id in ("sketch-model", "sk-model-small"):
        good = build_aipass_discovery(
            models_payload={"object": "list", "data": [{"id": safe_id, "name": safe_id}]},
            quota_payload=None,
            observed_at=now, now=now, configuration_generation=1,
        )
        assert good.state is AiPassDiscoveryState.OK
        assert good.models[0].model_id == safe_id


@pytest.mark.parametrize(
    "unsafe_value",
    (
        "github_pat_" + "A" * 32,
        "sk_live_" + "A" * 24,
        "sk_test_" + "A" * 24,
        "rk_live_" + "A" * 24,
        "rk_test_" + "A" * 24,
        "glpat-" + "A" * 24,
        "npm_" + "A" * 32,
        "pypi-" + "A" * 32,
        "ASIA" + "A" * 16,
    ),
)
def test_additional_high_confidence_credential_shapes_fail_closed(unsafe_value: str) -> None:
    result = build_aipass_discovery(
        models_payload={"object": "list", "data": [{"id": unsafe_value, "name": "safe"}]},
        quota_payload=None,
        observed_at=NOW,
        now=NOW,
        configuration_generation=1,
    )
    assert result.state is AiPassDiscoveryState.MALFORMED
    assert result.models == ()
    assert unsafe_value not in str(result.to_dict())


@pytest.mark.parametrize(
    "unsafe_value",
    (
        "github_pat_" + "B" * 32,
        "sk_live_" + "B" * 24,
        "sk_test_" + "B" * 24,
        "rk_live_" + "B" * 24,
        "rk_test_" + "B" * 24,
        "glpat-" + "B" * 24,
        "npm_" + "B" * 32,
        "pypi-" + "B" * 32,
        "ASIA" + "B" * 16,
    ),
)
def test_additional_high_confidence_credential_display_names_fall_back(unsafe_value: str) -> None:
    result = build_aipass_discovery(
        models_payload={"object": "list", "data": [{"id": "safe-model", "name": unsafe_value}]},
        quota_payload=None,
        observed_at=NOW,
        now=NOW,
        configuration_generation=1,
    )
    assert result.state is AiPassDiscoveryState.OK
    assert result.models[0].name == "safe-model"
    assert unsafe_value not in str(result.to_dict())


def test_additional_credential_shape_guards_preserve_semantic_near_neighbors() -> None:
    safe_values = (
        "github_pat_model",
        "sk_live_model",
        "rk_live_model",
        "glpat-model",
        "npm_model",
        "pypi-model",
        "asia-model",
    )
    for safe_value in safe_values:
        result = build_aipass_discovery(
            models_payload={"object": "list", "data": [{"id": safe_value, "name": safe_value}]},
            quota_payload=None,
            observed_at=NOW,
            now=NOW,
            configuration_generation=1,
        )
        assert result.state is AiPassDiscoveryState.OK
        assert result.models[0].model_id == safe_value
        assert result.models[0].name == safe_value


@pytest.mark.parametrize(
    "unsafe_name",
    (
        " /home/alice/.ssh/id_ed25519",
        "Model cache /home/alice/.ssh/id_ed25519",
        r" C:\Users\alice\secret.txt",
        r"Model cache C:\Users\alice\secret.txt",
        r" \\server\share\secret.txt",
        r"Model cache \\server\share\secret.txt",
        "endpoint /v1/models",
    ),
)
def test_embedded_private_path_display_names_fall_back(unsafe_name: str) -> None:
    result = build_aipass_discovery(
        models_payload={"object": "list", "data": [{"id": "safe-model", "name": unsafe_name}]},
        quota_payload=None,
        observed_at=NOW,
        now=NOW,
        configuration_generation=1,
    )
    assert result.state is AiPassDiscoveryState.OK
    assert result.models[0].name == "safe-model"
    assert unsafe_name != result.models[0].name


def test_private_path_guard_preserves_semantic_slash_text() -> None:
    for safe_name in ("Vision / Chat", "Home / Research", "C drive model", "Path-aware model"):
        result = build_aipass_discovery(
            models_payload={"object": "list", "data": [{"id": "safe-model", "name": safe_name}]},
            quota_payload=None,
            observed_at=NOW,
            now=NOW,
            configuration_generation=1,
        )
        assert result.state is AiPassDiscoveryState.OK
        assert result.models[0].name == safe_name


@pytest.mark.parametrize(
    "unsafe_name",
    (
        "Basic dXNlcjpwYXNzd29yZA==",
        "-----BEGIN PRIVATE KEY-----",
        "password=SuperSecretValue123",
        "client_secret=SuperSecretValue123",
        "client-secret: SuperSecretValue123",
        "session=abcdef0123456789abcdef",
        "session_id=abcdef0123456789abcdef",
        "token=abcdef0123456789abcdef",
        "secret=abcdef0123456789abcdef",
        "private_key=abcdef0123456789abcdef",
        "passphrase=abcdef0123456789abcdef",
        "credential=abcdef0123456789abcdef",
        "auth=abcdef0123456789abcdef",
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDemo",
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDemoKeyMaterial",
    ),
)
def test_opaque_credential_material_display_names_fall_back(unsafe_name: str) -> None:
    result = build_aipass_discovery(
        models_payload={"object": "list", "data": [{"id": "safe-model", "name": unsafe_name}]},
        quota_payload=None,
        observed_at=NOW,
        now=NOW,
        configuration_generation=1,
    )
    assert result.state is AiPassDiscoveryState.OK
    assert result.models[0].name == "safe-model"
    assert unsafe_name not in str(result.to_dict())


def test_opaque_credential_guards_preserve_semantic_text() -> None:
    safe_names = (
        "Basic Research",
        "Password Manager",
        "Client Secret Rotation",
        "Session Analysis",
        "Token Budget",
        "Private Key Concepts",
        "SSH Research",
        "Credential Policy",
        "Auth Model",
    )
    for safe_name in safe_names:
        result = build_aipass_discovery(
            models_payload={"object": "list", "data": [{"id": "safe-model", "name": safe_name}]},
            quota_payload=None,
            observed_at=NOW,
            now=NOW,
            configuration_generation=1,
        )
        assert result.state is AiPassDiscoveryState.OK
        assert result.models[0].name == safe_name


@pytest.mark.parametrize(
    "unsafe_name",
    (
        "OPENAI_API_KEY=abcdef0123456789",
        "AWS_SECRET_ACCESS_KEY=abcdef0123456789",
        "AWS_ACCESS_KEY_ID=AKIAEXAMPLE12345678",
        "AWS_SESSION_TOKEN=abcdef0123456789",
        "AZURE_CLIENT_SECRET=abcdef0123456789",
        "GITHUB_TOKEN=abcdef0123456789",
    ),
)
def test_prefixed_environment_credential_assignments_fall_back(unsafe_name: str) -> None:
    result = build_aipass_discovery(
        models_payload={"object": "list", "data": [{"id": "safe-model", "name": unsafe_name}]},
        quota_payload=None,
        observed_at=NOW,
        now=NOW,
        configuration_generation=1,
    )
    assert result.state is AiPassDiscoveryState.OK
    assert result.models[0].name == "safe-model"
    assert unsafe_name not in str(result.to_dict())


@pytest.mark.parametrize(
    "unsafe_name",
    (
        "localhost:8080",
        "127.0.0.1:8080",
        "api.example.com:443",
        "api.example.com/v1",
        "10.0.0.1",
    ),
)
def test_raw_endpoint_shaped_display_names_fall_back(unsafe_name: str) -> None:
    result = build_aipass_discovery(
        models_payload={"object": "list", "data": [{"id": "safe-model", "name": unsafe_name}]},
        quota_payload=None,
        observed_at=NOW,
        now=NOW,
        configuration_generation=1,
    )
    assert result.state is AiPassDiscoveryState.OK
    assert result.models[0].name == "safe-model"
    assert unsafe_name not in str(result.to_dict())


def test_endpoint_guard_preserves_semantic_network_text() -> None:
    for safe_name in ("Localhost Model", "IPv4 Research", "API Example Model", "Domain Research"):
        result = build_aipass_discovery(
            models_payload={"object": "list", "data": [{"id": "safe-model", "name": safe_name}]},
            quota_payload=None,
            observed_at=NOW, now=NOW, configuration_generation=1,
        )
        assert result.state is AiPassDiscoveryState.OK
        assert result.models[0].name == safe_name


@pytest.mark.parametrize(
    "unsafe_name",
    (
        "8.8.8.8",
        "api.example.com",
        "example.com",
        "::1",
        "2001:db8::1",
    ),
)
def test_standalone_raw_endpoint_values_fall_back(unsafe_name: str) -> None:
    result = build_aipass_discovery(
        models_payload={"object": "list", "data": [{"id": "safe-model", "name": unsafe_name}]},
        quota_payload=None,
        observed_at=NOW, now=NOW, configuration_generation=1,
    )
    assert result.state is AiPassDiscoveryState.OK
    assert result.models[0].name == "safe-model"
    assert unsafe_name not in str(result.to_dict())


def test_standalone_endpoint_guard_preserves_semantic_text() -> None:
    for safe_name in ("Domain Research", "IPv4 Research", "IPv6 Research", "API Example Model"):
        result = build_aipass_discovery(
            models_payload={"object": "list", "data": [{"id": "safe-model", "name": safe_name}]},
            quota_payload=None,
            observed_at=NOW, now=NOW, configuration_generation=1,
        )
        assert result.state is AiPassDiscoveryState.OK
        assert result.models[0].name == safe_name


def test_discovery_model_direct_constructor_fails_closed() -> None:
    with pytest.raises(ValueError, match="factory"):
        AiPassDiscoveredModel("safe-model", "Safe Model", None, "chat", False)


def test_discovery_snapshot_direct_constructor_fails_closed() -> None:
    safe_model = _build(quota={}).models[0]
    with pytest.raises(ValueError, match="factory"):
        AiPassDiscoverySnapshot(
            AiPassDiscoveryState.OK,
            "DISCOVERY_OK",
            (safe_model,),
            configuration_generation=7,
            observed_at=NOW,
        )


@pytest.mark.parametrize(
    "unsafe_value",
    (
        "a" + "ghp_" + "A" * 36,
        "x" + "sk-ant-" + "A" * 24,
        "x" + "AKIA" + "B" * 16,
        "x" + "npm_" + "B" * 32,
        "1" + "eyJhbGciOiJIUzI1NiI",
    ),
)
def test_glued_credential_shapes_fail_closed(unsafe_value: str) -> None:
    result = _build(models=_models(_model(unsafe_value, name="safe")), quota={})
    assert result.state is AiPassDiscoveryState.MALFORMED
    assert unsafe_value not in str(result.to_dict())


@pytest.mark.parametrize(
    "unsafe_name",
    (
        "a" + "ghp_" + "A" * 36,
        "x" + "sk-ant-" + "A" * 24,
        "x" + "AKIA" + "B" * 16,
        "x" + "npm_" + "B" * 32,
    ),
)
def test_glued_credential_display_names_fall_back(unsafe_name: str) -> None:
    result = _build(models=_models(_model("safe-model", name=unsafe_name)), quota={})
    assert result.state is AiPassDiscoveryState.OK
    assert result.models[0].name == "safe-model"
    assert unsafe_name not in str(result.to_dict())


@pytest.mark.parametrize(
    "unsafe_name",
    (
        "cache/home/alice/.ssh/id_ed25519",
        "endpoint/v1/models",
        r"cacheC:\Users\alice\secret.txt",
        r"cache\\server\share\secret.txt",
    ),
)
def test_glued_private_path_display_names_fall_back(unsafe_name: str) -> None:
    result = _build(models=_models(_model("safe-model", name=unsafe_name)), quota={})
    assert result.state is AiPassDiscoveryState.OK
    assert result.models[0].name == "safe-model"
    assert unsafe_name not in str(result.to_dict())


def test_glued_guards_preserve_semantic_near_neighbors() -> None:
    for safe_value in ("highp_model", "Rakia1", "sketch-model", "cache-aware-model"):
        result = _build(models=_models(_model(safe_value, name=safe_value)), quota={})
        assert result.state is AiPassDiscoveryState.OK
        assert result.models[0].model_id == safe_value
        assert result.models[0].name == safe_value
