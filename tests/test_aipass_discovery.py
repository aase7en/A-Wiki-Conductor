from __future__ import annotations

from datetime import datetime, timedelta, timezone

from a_conductor.aipass_discovery import (
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
    return build_aipass_discovery(
        models_payload=_models(_model()) if models is None else models,
        quota_payload=_quota() if quota is None else quota,
        observed_at=kwargs.pop("observed_at", NOW),
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
