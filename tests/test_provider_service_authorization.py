from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from a_conductor.provider_service_authorization import (
    ProviderServiceAuthorizationRecord,
    ServiceAuthorizationState,
    ServiceIntegrationMode,
    evaluate_provider_service_authorization,
)

NOW = datetime(2026, 9, 3, 4, 0, tzinfo=timezone.utc)
TERMS = "aipass-terms@2026-08-19"
EVIDENCE = "a" * 64


def _record(**overrides):
    data = {
        "provider_id": "aipass",
        "state": ServiceAuthorizationState.AUTHORIZED,
        "integration_mode": ServiceIntegrationMode.LIVE,
        "terms_identity": TERMS,
        "evidence_sha256": EVIDENCE,
        "observed_at": NOW - timedelta(hours=1),
        "recheck_after": NOW + timedelta(days=1),
        "configuration_generation": 7,
    }
    data.update(overrides)
    return ProviderServiceAuthorizationRecord(**data)


def _evaluate(record, *, mode=ServiceIntegrationMode.LIVE, provider_id="aipass",
              terms=TERMS, generation=7, now=NOW):
    return evaluate_provider_service_authorization(
        record,
        provider_id=provider_id,
        requested_mode=mode,
        terms_identity=terms,
        expected_configuration_generation=generation,
        now=now,
    )


def test_fake_mode_needs_no_service_authorization():
    decision = _evaluate(None, mode=ServiceIntegrationMode.FAKE)
    assert decision.allowed is True
    assert decision.reason_code == "SERVICE_AUTHORIZATION_NOT_REQUIRED_FAKE"
    assert decision.state is None


@pytest.mark.parametrize("mode", [ServiceIntegrationMode.READ_ONLY, ServiceIntegrationMode.LIVE])
def test_external_modes_without_record_fail_closed(mode):
    decision = _evaluate(None, mode=mode)
    assert decision.allowed is False
    assert decision.reason_code == "SERVICE_AUTHORIZATION_REQUIRED"


@pytest.mark.parametrize(
    ("state", "reason"),
    [
        (ServiceAuthorizationState.UNKNOWN, "SERVICE_AUTHORIZATION_UNKNOWN"),
        (ServiceAuthorizationState.BLOCKED_EXTERNAL, "SERVICE_AUTHORIZATION_BLOCKED_EXTERNAL"),
    ],
)
def test_unknown_and_blocked_states_fail_closed(state, reason):
    decision = _evaluate(_record(state=state, evidence_sha256=None))
    assert decision.allowed is False
    assert decision.reason_code == reason


def test_provider_identity_mismatch_fails_closed():
    decision = _evaluate(_record(), provider_id="other")
    assert not decision.allowed
    assert decision.reason_code == "SERVICE_AUTHORIZATION_PROVIDER_MISMATCH"


def test_authorization_is_bound_to_exact_integration_mode():
    decision = _evaluate(_record(), mode=ServiceIntegrationMode.READ_ONLY)
    assert not decision.allowed
    assert decision.reason_code == "SERVICE_AUTHORIZATION_MODE_MISMATCH"


def test_terms_identity_change_invalidates_authorization():
    decision = _evaluate(_record(), terms="aipass.go.th/term-and-cond-th@future")
    assert not decision.allowed
    assert decision.reason_code == "SERVICE_AUTHORIZATION_TERMS_STALE"


def test_configuration_generation_drift_invalidates_authorization():
    decision = _evaluate(_record(), generation=8)
    assert not decision.allowed
    assert decision.reason_code == "SERVICE_AUTHORIZATION_GENERATION_STALE"


def test_expired_recheck_window_invalidates_authorization():
    decision = _evaluate(_record(), now=NOW + timedelta(days=2))
    assert not decision.allowed
    assert decision.reason_code == "SERVICE_AUTHORIZATION_EVIDENCE_STALE"


def test_authorized_current_exact_record_allows_service_mode():
    decision = _evaluate(_record())
    assert decision.allowed is True
    assert decision.reason_code == "SERVICE_AUTHORIZATION_ALLOWED"
    assert decision.state is ServiceAuthorizationState.AUTHORIZED


def test_authorized_record_requires_evidence_digest():
    with pytest.raises(ValueError, match="evidence_sha256"):
        _record(evidence_sha256=None)


@pytest.mark.parametrize("digest", ["", "abc", "g" * 64, "a" * 63, "a" * 65])
def test_evidence_digest_is_strict_sha256(digest):
    with pytest.raises(ValueError, match="evidence_sha256"):
        _record(evidence_sha256=digest)


def test_timestamps_must_be_timezone_aware_and_ordered():
    with pytest.raises(ValueError, match="timezone-aware"):
        _record(observed_at=NOW.replace(tzinfo=None))
    with pytest.raises(ValueError, match="recheck_after"):
        _record(recheck_after=NOW - timedelta(hours=2))


@pytest.mark.parametrize("generation", [0, -1, True, None])
def test_configuration_generation_must_be_positive_integer(generation):
    with pytest.raises(ValueError, match="configuration_generation"):
        _record(configuration_generation=generation)


@pytest.mark.parametrize("field", ["provider_id", "terms_identity"])
def test_identity_text_must_be_bounded_nonblank_without_controls(field):
    with pytest.raises(ValueError):
        _record(**{field: " "})
    with pytest.raises(ValueError):
        _record(**{field: "bad\nvalue"})


def test_non_authorized_record_may_have_no_evidence_digest():
    blocked = _record(
        state=ServiceAuthorizationState.BLOCKED_EXTERNAL,
        evidence_sha256=None,
    )
    assert blocked.evidence_sha256 is None


def test_source_license_fact_cannot_authorize_service_access():
    # License evidence is intentionally absent from the service-auth contract.
    # A MIT source license must not become an input that flips this decision.
    decision = _evaluate(
        _record(state=ServiceAuthorizationState.BLOCKED_EXTERNAL, evidence_sha256=None)
    )
    assert not decision.allowed
    assert decision.reason_code == "SERVICE_AUTHORIZATION_BLOCKED_EXTERNAL"


@pytest.mark.parametrize(
    "terms_identity",
    [
        "https://aipass.go.th/terms?token=SECRET",
        "https://aipass.go.th/terms#credential",
        "Authorization: Bearer SECRET",
        "aipass terms @ 2026-08-19",
        "https://aipass.go.th/terms/TOKENSECRET",
        "Authorization:BearerSECRET",
        "secret-ref:awiki-env/API_TOKEN",
        "aipass/terms@2026-08-19",
    ],
)
def test_terms_identity_rejects_secret_bearing_or_url_query_shapes(terms_identity):
    with pytest.raises(ValueError, match="terms_identity"):
        _record(terms_identity=terms_identity)


def test_safe_serialization_contains_only_non_secret_contract_fields():
    record = _record()
    payload = record.to_dict()
    text = repr(record) + repr(payload)
    assert payload["evidence_sha256"] == EVIDENCE
    for forbidden in ("cookie", "token", "authorization_header", "credential", "api_key"):
        assert forbidden not in text.casefold()


def test_evaluator_rejects_malformed_call_inputs():
    with pytest.raises(ValueError):
        evaluate_provider_service_authorization(
            None,
            provider_id="",
            requested_mode=ServiceIntegrationMode.FAKE,
            terms_identity=TERMS,
            expected_configuration_generation=7,
            now=NOW,
        )
    with pytest.raises(ValueError):
        _evaluate(None, generation=0, mode=ServiceIntegrationMode.FAKE)
    with pytest.raises(ValueError, match="timezone-aware"):
        _evaluate(None, now=NOW.replace(tzinfo=None), mode=ServiceIntegrationMode.FAKE)
