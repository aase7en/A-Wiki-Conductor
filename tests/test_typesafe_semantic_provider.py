from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from a_conductor.semantic_decision import (
    SemanticDecisionFamily,
    SemanticDecisionMode,
    SemanticDecisionProvider,
    SemanticDecisionReason,
    SemanticDecisionRequest,
    SemanticDisposition,
    SemanticEvidence,
    SemanticEvidenceErrorKind,
    SemanticPrimitive,
    SemanticRiskLevel,
    evaluate_semantic_decision,
)
from a_conductor.typesafe_semantic_provider import (
    PINNED_TYPESAFE_MODEL,
    TYPESAFE_MAX_REQUEST_BYTES,
    TYPESAFE_MAX_RESPONSE_BYTES,
    TYPESAFE_PROVIDER_NAME,
    TYPESAFE_SYSTEMONE_URL,
    TypeSafeAdapterError,
    TypeSafeHTTPResponse,
    TypeSafeSemanticDecisionProvider,
    classify_transport_exception,
    http_error_kind,
)

SECRET = "apikey_typesafe_test_0123456789abcdef"
API_KEY_REFERENCE = "secret-ref:awiki-env/TYPESAFE_API_KEY"


class FakeResolver:
    def __init__(self, values=None, error=None):
        self.values = dict(values or {})
        self.error = error
        self.calls: list[str] = []

    def resolve(self, reference: str) -> str:
        self.calls.append(reference)
        if self.error is not None:
            raise self.error
        if reference not in self.values:
            raise RuntimeError(f"unresolved reference {reference!r}")
        return self.values[reference]


class FakeTransport:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls: list = []

    def post(self, request):
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        assert self.response is not None, "no scripted transport response"
        return self.response


def make_resolver() -> FakeResolver:
    return FakeResolver({API_KEY_REFERENCE: SECRET})


def make_provider(transport, resolver=None, **overrides) -> TypeSafeSemanticDecisionProvider:
    return TypeSafeSemanticDecisionProvider(
        transport=transport,
        secret_resolver=resolver if resolver is not None else make_resolver(),
        **overrides,
    )


def make_choice_request(**overrides) -> SemanticDecisionRequest:
    defaults: dict = {
        "request_id": "req-choice-001",
        "family": SemanticDecisionFamily.TASK_CLASSIFICATION,
        "primitive": SemanticPrimitive.CHOICE,
        "state": {"summary": "Focused tests fail with a missing module import."},
        "risk": SemanticRiskLevel.MEDIUM,
        "options": ("bugfix", "feature", "docs", "review"),
        "min_confidence": 0.8,
    }
    defaults.update(overrides)
    return SemanticDecisionRequest(**defaults)


def make_score_request(**overrides) -> SemanticDecisionRequest:
    defaults: dict = {
        "request_id": "req-score-001",
        "family": SemanticDecisionFamily.EVIDENCE_RELEVANCE,
        "primitive": SemanticPrimitive.SCORE,
        "state": {"finding": "Cache is cleared before the read completes."},
        "risk": SemanticRiskLevel.LOW,
        "score_levels": 4,
        "min_confidence": 0.8,
    }
    defaults.update(overrides)
    return SemanticDecisionRequest(**defaults)


def make_noul_request(**overrides) -> SemanticDecisionRequest:
    defaults: dict = {
        "request_id": "req-noul-001",
        "family": SemanticDecisionFamily.EVIDENCE_RELEVANCE,
        "primitive": SemanticPrimitive.NOUL,
        "state": {
            "claim": "The focused test passed on the candidate SHA.",
            "evidence": "pytest reported 18 passed on that exact candidate SHA.",
        },
        "risk": SemanticRiskLevel.MEDIUM,
        "decision_threshold": 0.5,
        "review_band": (0.3, 0.7),
    }
    defaults.update(overrides)
    return SemanticDecisionRequest(**defaults)


def choice_answer(**overrides) -> dict:
    answer = {
        "type": "choice",
        "choice": "bugfix",
        "confidence": 0.91,
        "probabilities": {
            "bugfix": 0.91,
            "feature": 0.03,
            "docs": 0.03,
            "review": 0.03,
        },
    }
    answer.update(overrides)
    return answer


def score_answer(**overrides) -> dict:
    answer = {
        "type": "score",
        "score": 2,
        "legend": {"0": "none", "1": "minor", "2": "major", "3": "critical"},
        "confidence": 0.85,
        "probabilities": {"0": 0.05, "1": 0.05, "2": 0.80, "3": 0.10},
    }
    answer.update(overrides)
    return answer


def noul_answer(**overrides) -> dict:
    answer = {"type": "noul", "noul": 0.87}
    answer.update(overrides)
    return answer


def payload(answer: dict, *, model: str = PINNED_TYPESAFE_MODEL) -> dict:
    return {
        "model": model,
        "answers": {"decision": answer},
        "usage": {"input_tokens": 392, "output_tokens": 40},
    }


def respond(
    answer: dict | None = None,
    *,
    body: str | None = None,
    status: int = 200,
    elapsed: float = 120.0,
    model: str = PINNED_TYPESAFE_MODEL,
) -> TypeSafeHTTPResponse:
    if body is None:
        body = json.dumps(payload(answer, model=model))
    return TypeSafeHTTPResponse(status_code=status, body=body, elapsed_ms=elapsed)


def ok_choice_response() -> TypeSafeHTTPResponse:
    return respond(choice_answer())


# ---------------------------------------------------------------------------
# Construction and pinned contract
# ---------------------------------------------------------------------------


def test_satisfies_semantic_decision_provider_protocol() -> None:
    provider = make_provider(FakeTransport(ok_choice_response()))
    assert isinstance(provider, SemanticDecisionProvider)


def test_constructor_rejects_alias_model() -> None:
    with pytest.raises(TypeSafeAdapterError):
        make_provider(FakeTransport(), model="jev-latest")


def test_constructor_rejects_unversioned_model() -> None:
    with pytest.raises(TypeSafeAdapterError):
        make_provider(FakeTransport(), model="jev-1")


def test_constructor_accepts_explicit_versioned_model() -> None:
    provider = make_provider(FakeTransport(), model="jev-1.12.0")
    evidence = provider.evaluate(make_choice_request())
    assert evidence.model == "jev-1.12.0"


def test_constructor_rejects_raw_secret_reference() -> None:
    with pytest.raises(TypeSafeAdapterError):
        make_provider(FakeTransport(), api_key_reference=SECRET)


def test_constructor_rejects_invalid_timeout() -> None:
    for timeout in (0.5, 121.0, float("inf"), float("nan"), -1.0):
        with pytest.raises(TypeSafeAdapterError):
            make_provider(FakeTransport(), timeout_seconds=timeout)


def test_credential_not_resolved_at_construction() -> None:
    resolver = make_resolver()
    make_provider(FakeTransport(), resolver=resolver)
    assert resolver.calls == []


# ---------------------------------------------------------------------------
# Request normalization
# ---------------------------------------------------------------------------


def test_choice_request_body_is_explicit() -> None:
    transport = FakeTransport(ok_choice_response())
    make_provider(transport).evaluate(make_choice_request())
    assert len(transport.calls) == 1
    wire = transport.calls[0]
    assert wire.url == TYPESAFE_SYSTEMONE_URL
    body = json.loads(wire.body)
    assert body["model"] == PINNED_TYPESAFE_MODEL
    assert body["state"] == {"summary": "Focused tests fail with a missing module import."}
    question = body["questions"]["decision"]
    assert question["type"] == "choice"
    assert isinstance(question["instructions"], str) and question["instructions"]
    assert question["criteria"] == {
        "bugfix": None,
        "feature": None,
        "docs": None,
        "review": None,
    }


def test_score_request_carries_level_criteria() -> None:
    transport = FakeTransport(respond(score_answer()))
    make_provider(transport).evaluate(make_score_request())
    question = json.loads(transport.calls[0].body)["questions"]["decision"]
    assert question["type"] == "score"
    assert question["criteria"] == ["level 0", "level 1", "level 2", "level 3"]


def test_noul_request_omits_criteria() -> None:
    transport = FakeTransport(respond(noul_answer()))
    make_provider(transport).evaluate(make_noul_request())
    question = json.loads(transport.calls[0].body)["questions"]["decision"]
    assert question["type"] == "noul"
    assert "criteria" not in question


def test_request_headers_carry_bearer_and_content_type() -> None:
    transport = FakeTransport(ok_choice_response())
    make_provider(transport).evaluate(make_choice_request())
    headers = transport.calls[0].headers
    assert headers["Authorization"] == f"Bearer {SECRET}"
    assert headers["Content-Type"] == "application/json"
    assert set(headers) == {"Authorization", "Content-Type", "Accept"}


def test_request_timeout_is_forwarded() -> None:
    transport = FakeTransport(ok_choice_response())
    make_provider(transport).evaluate(make_choice_request())
    assert transport.calls[0].timeout_seconds == 10.0
    transport2 = FakeTransport(ok_choice_response())
    make_provider(transport2, timeout_seconds=5.0).evaluate(make_choice_request())
    assert transport2.calls[0].timeout_seconds == 5.0


def test_request_body_is_deterministic() -> None:
    transport = FakeTransport(ok_choice_response())
    provider = make_provider(transport)
    provider.evaluate(make_choice_request())
    provider.evaluate(make_choice_request())
    assert transport.calls[0].body == transport.calls[1].body


def test_nested_state_serializes_to_plain_json() -> None:
    transport = FakeTransport(ok_choice_response())
    request = make_choice_request(
        state={"items": ["a", "b"], "nested": {"depth": 2, "flag": True}}
    )
    make_provider(transport).evaluate(request)
    state = json.loads(transport.calls[0].body)["state"]
    assert state == {"items": ["a", "b"], "nested": {"depth": 2, "flag": True}}


def render(value):
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: render(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, Mapping) or isinstance(value, dict):
        return {key: render(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [render(item) for item in value]
    return value


def test_oversized_request_fails_closed_without_transport() -> None:
    transport = FakeTransport(ok_choice_response())
    oversized = {"bucket": ["x" * 4000 for _ in range(66)]}
    assert len(json.dumps(oversized).encode("utf-8")) > TYPESAFE_MAX_REQUEST_BYTES
    request = make_choice_request(state=oversized)
    evidence = make_provider(transport).evaluate(request)
    assert evidence.error is not None
    assert evidence.error.kind is SemanticEvidenceErrorKind.SCHEMA
    assert transport.calls == []


# ---------------------------------------------------------------------------
# Credential boundary
# ---------------------------------------------------------------------------


def test_credential_resolved_once_per_call() -> None:
    resolver = make_resolver()
    transport = FakeTransport(ok_choice_response())
    provider = make_provider(transport, resolver=resolver)
    provider.evaluate(make_choice_request())
    provider.evaluate(make_choice_request())
    assert resolver.calls == [API_KEY_REFERENCE, API_KEY_REFERENCE]


def test_missing_credential_returns_auth_error_without_transport() -> None:
    resolver = FakeResolver(error=RuntimeError("secret source unavailable"))
    transport = FakeTransport(ok_choice_response())
    evidence = make_provider(transport, resolver=resolver).evaluate(make_choice_request())
    assert evidence.error is not None
    assert evidence.error.kind is SemanticEvidenceErrorKind.AUTH
    assert transport.calls == []


def test_empty_credential_returns_auth_error() -> None:
    resolver = FakeResolver({API_KEY_REFERENCE: "   "})
    evidence = make_provider(
        FakeTransport(ok_choice_response()), resolver=resolver
    ).evaluate(make_choice_request())
    assert evidence.error is not None
    assert evidence.error.kind is SemanticEvidenceErrorKind.AUTH


def test_control_character_credential_returns_auth_error() -> None:
    for bad in ("bad\nkey", "bad\r\nkey", "bad\x00key"):
        resolver = FakeResolver({API_KEY_REFERENCE: bad})
        evidence = make_provider(
            FakeTransport(ok_choice_response()), resolver=resolver
        ).evaluate(make_choice_request())
        assert evidence.error is not None
        assert evidence.error.kind is SemanticEvidenceErrorKind.AUTH


def test_secret_never_appears_in_evidence_or_errors() -> None:
    success = make_provider(FakeTransport(ok_choice_response())).evaluate(
        make_choice_request()
    )
    for rendered in (repr(success), str(success), json.dumps(render(success))):
        assert SECRET not in rendered

    leaking = FakeResolver(error=RuntimeError(f"resolver failed near {SECRET}"))
    failure = make_provider(
        FakeTransport(ok_choice_response()), resolver=leaking
    ).evaluate(make_choice_request())
    for rendered in (repr(failure), str(failure), json.dumps(render(failure))):
        assert SECRET not in rendered
    assert failure.error is not None
    assert failure.error.kind is SemanticEvidenceErrorKind.AUTH


def test_real_awiki_resolver_drives_adapter() -> None:
    from a_conductor.awiki_environment_resolver import (
        AWikiEnvironmentReferenceResolver,
        AWikiEnvironmentResolutionError,
    )

    class InMemorySecretSource:
        def __init__(self, values):
            self._values = dict(values)

        def resolve_key(self, key: str) -> str:
            if key not in self._values:
                raise AWikiEnvironmentResolutionError("SECRET_REFERENCE_NOT_FOUND")
            return self._values[key]

    class NullEndpointReader:
        def get_endpoint(self, endpoint_ref):
            return None

    resolver = AWikiEnvironmentReferenceResolver(
        endpoint_reader=NullEndpointReader(),
        secret_source=InMemorySecretSource({"TYPESAFE_API_KEY": SECRET}),
    )
    transport = FakeTransport(ok_choice_response())
    evidence = make_provider(transport, resolver=resolver).evaluate(make_choice_request())
    assert evidence.error is None
    assert transport.calls[0].headers["Authorization"] == f"Bearer {SECRET}"

    empty = AWikiEnvironmentReferenceResolver(
        endpoint_reader=NullEndpointReader(),
        secret_source=InMemorySecretSource({}),
    )
    failure = make_provider(
        FakeTransport(ok_choice_response()), resolver=empty
    ).evaluate(make_choice_request())
    assert failure.error is not None
    assert failure.error.kind is SemanticEvidenceErrorKind.AUTH


# ---------------------------------------------------------------------------
# Transport and HTTP failure mapping
# ---------------------------------------------------------------------------


def test_timeout_maps_to_timeout_error() -> None:
    transport = FakeTransport(error=TimeoutError("read timed out"))
    evidence = make_provider(transport).evaluate(make_choice_request())
    assert evidence.error is not None
    assert evidence.error.kind is SemanticEvidenceErrorKind.TIMEOUT


def test_urlerror_wrapping_timeout_maps_to_timeout() -> None:
    from urllib.error import URLError

    transport = FakeTransport(error=URLError(TimeoutError("handshake timed out")))
    evidence = make_provider(transport).evaluate(make_choice_request())
    assert evidence.error is not None
    assert evidence.error.kind is SemanticEvidenceErrorKind.TIMEOUT


def test_connection_error_maps_to_transport_error() -> None:
    transport = FakeTransport(error=ConnectionError("connection reset"))
    evidence = make_provider(transport).evaluate(make_choice_request())
    assert evidence.error is not None
    assert evidence.error.kind is SemanticEvidenceErrorKind.TRANSPORT


def test_oserror_maps_to_transport_error() -> None:
    transport = FakeTransport(error=OSError("network unreachable"))
    evidence = make_provider(transport).evaluate(make_choice_request())
    assert evidence.error is not None
    assert evidence.error.kind is SemanticEvidenceErrorKind.TRANSPORT


def test_unexpected_exception_maps_to_unknown_error() -> None:
    transport = FakeTransport(error=ValueError("garbage"))
    evidence = make_provider(transport).evaluate(make_choice_request())
    assert evidence.error is not None
    assert evidence.error.kind is SemanticEvidenceErrorKind.UNKNOWN


def test_classify_transport_exception_table() -> None:
    from urllib.error import URLError

    assert classify_transport_exception(TimeoutError()) is (
        SemanticEvidenceErrorKind.TIMEOUT
    )
    assert classify_transport_exception(URLError(TimeoutError())) is (
        SemanticEvidenceErrorKind.TIMEOUT
    )
    assert classify_transport_exception(URLError(OSError())) is (
        SemanticEvidenceErrorKind.TRANSPORT
    )
    assert classify_transport_exception(ConnectionError()) is (
        SemanticEvidenceErrorKind.TRANSPORT
    )
    assert classify_transport_exception(RuntimeError()) is (
        SemanticEvidenceErrorKind.UNKNOWN
    )


@pytest.mark.parametrize(
    "status,kind",
    [
        (401, SemanticEvidenceErrorKind.AUTH),
        (403, SemanticEvidenceErrorKind.AUTH),
        (429, SemanticEvidenceErrorKind.RATE_LIMIT),
        (422, SemanticEvidenceErrorKind.SCHEMA),
        (529, SemanticEvidenceErrorKind.OVERLOAD),
        (500, SemanticEvidenceErrorKind.OVERLOAD),
        (503, SemanticEvidenceErrorKind.OVERLOAD),
        (418, SemanticEvidenceErrorKind.UNKNOWN),
        (302, SemanticEvidenceErrorKind.UNKNOWN),
    ],
)
def test_http_error_status_maps_to_typed_evidence(status, kind) -> None:
    transport = FakeTransport(
        TypeSafeHTTPResponse(
            status_code=status, body='{"unexpected": "sensitive body text"}', elapsed_ms=15.0
        )
    )
    evidence = make_provider(transport).evaluate(make_choice_request())
    assert evidence.error is not None
    assert evidence.error.kind is kind
    assert "sensitive body text" not in evidence.error.detail
    assert str(status) in evidence.error.detail
    assert evidence.latency_ms == 15.0


def test_http_error_kind_pure_function() -> None:
    assert http_error_kind(200) is None
    assert http_error_kind(401) is SemanticEvidenceErrorKind.AUTH
    assert http_error_kind(429) is SemanticEvidenceErrorKind.RATE_LIMIT
    assert http_error_kind(529) is SemanticEvidenceErrorKind.OVERLOAD
    assert http_error_kind(422) is SemanticEvidenceErrorKind.SCHEMA
    assert http_error_kind(502) is SemanticEvidenceErrorKind.OVERLOAD
    assert http_error_kind(451) is SemanticEvidenceErrorKind.UNKNOWN


def test_non_raising_adapter_returns_error_on_garbage_request() -> None:
    evidence = make_provider(FakeTransport(ok_choice_response())).evaluate(object())
    assert isinstance(evidence, SemanticEvidence)
    assert evidence.error is not None
    assert evidence.error.kind is SemanticEvidenceErrorKind.SCHEMA


# ---------------------------------------------------------------------------
# Response shape failures (status 200, malformed body)
# ---------------------------------------------------------------------------


def error_kind_for(body: str, request=None) -> SemanticEvidenceErrorKind:
    transport = FakeTransport(
        TypeSafeHTTPResponse(status_code=200, body=body, elapsed_ms=50.0)
    )
    evidence = make_provider(transport).evaluate(
        request if request is not None else make_choice_request()
    )
    assert evidence.error is not None
    return evidence.error.kind


def test_malformed_json_returns_schema_error() -> None:
    assert error_kind_for("not-json{") is SemanticEvidenceErrorKind.SCHEMA


def test_non_object_payload_returns_schema_error() -> None:
    assert error_kind_for("[1, 2, 3]") is SemanticEvidenceErrorKind.SCHEMA


def test_unknown_top_level_field_rejected() -> None:
    raw = payload(choice_answer())
    raw["extra"] = 1
    assert error_kind_for(json.dumps(raw)) is SemanticEvidenceErrorKind.SCHEMA


def test_missing_top_level_field_rejected() -> None:
    raw = payload(choice_answer())
    del raw["usage"]
    assert error_kind_for(json.dumps(raw)) is SemanticEvidenceErrorKind.SCHEMA


def test_model_mismatch_returns_schema_error() -> None:
    assert error_kind_for(
        json.dumps(payload(choice_answer(), model="jev-1.12.0"))
    ) is SemanticEvidenceErrorKind.SCHEMA
    assert error_kind_for(
        json.dumps(payload(choice_answer(), model="jev-latest"))
    ) is SemanticEvidenceErrorKind.SCHEMA


def test_usage_missing_field_rejected() -> None:
    raw = payload(choice_answer())
    del raw["usage"]["output_tokens"]
    assert error_kind_for(json.dumps(raw)) is SemanticEvidenceErrorKind.SCHEMA


def test_usage_extra_field_rejected() -> None:
    raw = payload(choice_answer())
    raw["usage"]["cost_usd"] = 0.01
    assert error_kind_for(json.dumps(raw)) is SemanticEvidenceErrorKind.SCHEMA


def test_usage_negative_rejected() -> None:
    raw = payload(choice_answer())
    raw["usage"]["input_tokens"] = -1
    assert error_kind_for(json.dumps(raw)) is SemanticEvidenceErrorKind.SCHEMA


def test_usage_bool_rejected() -> None:
    raw = payload(choice_answer())
    raw["usage"]["input_tokens"] = True
    assert error_kind_for(json.dumps(raw)) is SemanticEvidenceErrorKind.SCHEMA


def test_answers_missing_question_id_rejected() -> None:
    raw = payload(choice_answer())
    raw["answers"] = {}
    assert error_kind_for(json.dumps(raw)) is SemanticEvidenceErrorKind.SCHEMA


def test_answers_extra_question_id_rejected() -> None:
    raw = payload(choice_answer())
    raw["answers"]["other"] = noul_answer()
    assert error_kind_for(json.dumps(raw)) is SemanticEvidenceErrorKind.SCHEMA


def test_answer_not_object_rejected() -> None:
    raw = payload(choice_answer())
    raw["answers"]["decision"] = "bugfix"
    assert error_kind_for(json.dumps(raw)) is SemanticEvidenceErrorKind.SCHEMA


def test_answer_type_mismatch_rejected() -> None:
    assert error_kind_for(json.dumps(payload(score_answer()))) is (
        SemanticEvidenceErrorKind.SCHEMA
    )


# ---------------------------------------------------------------------------
# Choice answer validation
# ---------------------------------------------------------------------------


def test_choice_missing_probabilities_rejected() -> None:
    answer = choice_answer()
    del answer["probabilities"]
    assert error_kind_for(json.dumps(payload(answer))) is SemanticEvidenceErrorKind.SCHEMA


def test_choice_probability_key_mismatch_rejected() -> None:
    answer = choice_answer(
        probabilities={"bugfix": 1.0, "feature": 0.0, "docs": 0.0, "refactor": 0.0}
    )
    assert error_kind_for(json.dumps(payload(answer))) is SemanticEvidenceErrorKind.SCHEMA


def test_choice_probabilities_do_not_sum_to_one_rejected() -> None:
    answer = choice_answer(
        probabilities={"bugfix": 0.80, "feature": 0.03, "docs": 0.03, "review": 0.03}
    )
    assert error_kind_for(json.dumps(payload(answer))) is SemanticEvidenceErrorKind.SCHEMA


def test_choice_probability_out_of_range_rejected() -> None:
    answer = choice_answer(
        probabilities={"bugfix": 1.50, "feature": -0.30, "docs": -0.10, "review": -0.10}
    )
    assert error_kind_for(json.dumps(payload(answer))) is SemanticEvidenceErrorKind.SCHEMA


def test_choice_probability_non_finite_rejected() -> None:
    body = (
        '{"model": "jev-1.13.0", "answers": {"decision": {"type": "choice", '
        '"choice": "bugfix", "confidence": 0.9, "probabilities": {"bugfix": NaN, '
        '"feature": 0.03, "docs": 0.03, "review": 0.03}}}, '
        '"usage": {"input_tokens": 10, "output_tokens": 2}}'
    )
    assert error_kind_for(body) is SemanticEvidenceErrorKind.SCHEMA


def test_choice_missing_confidence_rejected() -> None:
    answer = choice_answer()
    del answer["confidence"]
    assert error_kind_for(json.dumps(payload(answer))) is SemanticEvidenceErrorKind.SCHEMA


def test_choice_confidence_out_of_range_rejected() -> None:
    assert error_kind_for(
        json.dumps(payload(choice_answer(confidence=1.5)))
    ) is SemanticEvidenceErrorKind.SCHEMA


def test_choice_confidence_non_finite_rejected() -> None:
    body = (
        '{"model": "jev-1.13.0", "answers": {"decision": {"type": "choice", '
        '"choice": "bugfix", "confidence": Infinity, "probabilities": {"bugfix": 0.91, '
        '"feature": 0.03, "docs": 0.03, "review": 0.03}}}, '
        '"usage": {"input_tokens": 10, "output_tokens": 2}}'
    )
    assert error_kind_for(body) is SemanticEvidenceErrorKind.SCHEMA


def test_choice_extra_answer_field_rejected() -> None:
    answer = choice_answer()
    answer["legend"] = {"bugfix": "x"}
    assert error_kind_for(json.dumps(payload(answer))) is SemanticEvidenceErrorKind.SCHEMA


def test_choice_answer_outside_options_passes_through_for_core_escalation() -> None:
    transport = FakeTransport(respond(choice_answer(choice="mystery")))
    evidence = make_provider(transport).evaluate(make_choice_request())
    assert evidence.error is None
    assert evidence.answer == "mystery"
    decision = evaluate_semantic_decision(
        make_choice_request(), evidence, SemanticDecisionMode.ADVISORY
    )
    assert decision.disposition is SemanticDisposition.ESCALATE
    assert decision.reason is SemanticDecisionReason.EVIDENCE_ANSWER_INVALID


# ---------------------------------------------------------------------------
# Score answer validation
# ---------------------------------------------------------------------------


def test_score_missing_legend_rejected() -> None:
    answer = score_answer()
    del answer["legend"]
    assert error_kind_for(
        json.dumps(payload(answer)), request=make_score_request()
    ) is SemanticEvidenceErrorKind.SCHEMA


def test_score_legend_key_mismatch_rejected() -> None:
    answer = score_answer(legend={"0": "none", "1": "minor", "2": "major"})
    assert error_kind_for(
        json.dumps(payload(answer)), request=make_score_request()
    ) is SemanticEvidenceErrorKind.SCHEMA


def test_score_legend_non_string_value_rejected() -> None:
    answer = score_answer(legend={"0": "none", "1": "minor", "2": 2, "3": "critical"})
    assert error_kind_for(
        json.dumps(payload(answer)), request=make_score_request()
    ) is SemanticEvidenceErrorKind.SCHEMA


def test_score_missing_confidence_rejected() -> None:
    answer = score_answer()
    del answer["confidence"]
    assert error_kind_for(
        json.dumps(payload(answer)), request=make_score_request()
    ) is SemanticEvidenceErrorKind.SCHEMA


def test_score_probability_key_mismatch_rejected() -> None:
    answer = score_answer(probabilities={"0": 0.25, "1": 0.25, "2": 0.25, "3": 0.25, "4": 0.0})
    assert error_kind_for(
        json.dumps(payload(answer)), request=make_score_request()
    ) is SemanticEvidenceErrorKind.SCHEMA


def test_score_answer_out_of_range_passes_through_for_core_escalation() -> None:
    transport = FakeTransport(respond(score_answer(score=9)))
    evidence = make_provider(transport).evaluate(make_score_request())
    assert evidence.error is None
    decision = evaluate_semantic_decision(
        make_score_request(), evidence, SemanticDecisionMode.SHADOW
    )
    assert decision.disposition is SemanticDisposition.ESCALATE
    assert decision.reason is SemanticDecisionReason.EVIDENCE_ANSWER_INVALID


# ---------------------------------------------------------------------------
# Noul answer validation
# ---------------------------------------------------------------------------


def test_noul_extra_confidence_rejected() -> None:
    answer = noul_answer(confidence=0.9)
    assert error_kind_for(
        json.dumps(payload(answer)), request=make_noul_request()
    ) is SemanticEvidenceErrorKind.SCHEMA


def test_noul_extra_probabilities_rejected() -> None:
    answer = noul_answer(probabilities={"true": 0.9, "false": 0.1})
    assert error_kind_for(
        json.dumps(payload(answer)), request=make_noul_request()
    ) is SemanticEvidenceErrorKind.SCHEMA


def test_noul_answer_out_of_range_passes_through_for_core_escalation() -> None:
    transport = FakeTransport(respond(noul_answer(noul=1.5)))
    evidence = make_provider(transport).evaluate(make_noul_request())
    assert evidence.error is None
    decision = evaluate_semantic_decision(
        make_noul_request(), evidence, SemanticDecisionMode.SHADOW
    )
    assert decision.disposition is SemanticDisposition.ESCALATE
    assert decision.reason is SemanticDecisionReason.EVIDENCE_ANSWER_INVALID


# ---------------------------------------------------------------------------
# Measurement and size bounds
# ---------------------------------------------------------------------------


def test_negative_elapsed_returns_schema_error() -> None:
    transport = FakeTransport(
        TypeSafeHTTPResponse(status_code=200, body=json.dumps(payload(choice_answer())), elapsed_ms=-1.0)
    )
    evidence = make_provider(transport).evaluate(make_choice_request())
    assert evidence.error is not None
    assert evidence.error.kind is SemanticEvidenceErrorKind.SCHEMA
    assert evidence.latency_ms == 0.0


def test_non_finite_elapsed_returns_schema_error() -> None:
    transport = FakeTransport(
        TypeSafeHTTPResponse(
            status_code=200, body=json.dumps(payload(choice_answer())), elapsed_ms=float("nan")
        )
    )
    evidence = make_provider(transport).evaluate(make_choice_request())
    assert evidence.error is not None
    assert evidence.error.kind is SemanticEvidenceErrorKind.SCHEMA


def test_oversized_response_body_rejected() -> None:
    transport = FakeTransport(
        TypeSafeHTTPResponse(
            status_code=200, body="x" * (TYPESAFE_MAX_RESPONSE_BYTES + 1), elapsed_ms=10.0
        )
    )
    evidence = make_provider(transport).evaluate(make_choice_request())
    assert evidence.error is not None
    assert evidence.error.kind is SemanticEvidenceErrorKind.SCHEMA


# ---------------------------------------------------------------------------
# Success normalization
# ---------------------------------------------------------------------------


def test_choice_success_evidence_is_fully_normalized() -> None:
    transport = FakeTransport(ok_choice_response())
    evidence = make_provider(transport).evaluate(make_choice_request())
    assert evidence.error is None
    assert evidence.provider == TYPESAFE_PROVIDER_NAME
    assert evidence.model == PINNED_TYPESAFE_MODEL
    assert evidence.primitive is SemanticPrimitive.CHOICE
    assert evidence.answer == "bugfix"
    assert evidence.confidence == pytest.approx(0.91)
    assert dict(evidence.probabilities) == {
        "bugfix": pytest.approx(0.91),
        "feature": pytest.approx(0.03),
        "docs": pytest.approx(0.03),
        "review": pytest.approx(0.03),
    }
    assert evidence.input_usage == 392
    assert evidence.output_usage == 40
    assert evidence.latency_ms == 120.0


def test_score_success_evidence_is_fully_normalized() -> None:
    transport = FakeTransport(respond(score_answer()))
    evidence = make_provider(transport).evaluate(make_score_request())
    assert evidence.error is None
    assert evidence.primitive is SemanticPrimitive.SCORE
    assert evidence.answer == 2
    assert evidence.confidence == pytest.approx(0.85)
    assert set(evidence.probabilities) == {"0", "1", "2", "3"}


def test_noul_success_evidence_is_fully_normalized() -> None:
    transport = FakeTransport(respond(noul_answer()))
    evidence = make_provider(transport).evaluate(make_noul_request())
    assert evidence.error is None
    assert evidence.primitive is SemanticPrimitive.NOUL
    assert evidence.answer == pytest.approx(0.87)
    assert evidence.confidence is None
    assert evidence.probabilities is None


# ---------------------------------------------------------------------------
# Transport call discipline (no blind retry/replay)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "transport",
    [
        FakeTransport(ok_choice_response()),
        FakeTransport(error=TimeoutError("timed out")),
        FakeTransport(respond(choice_answer(), status=401, body="{}")),
        FakeTransport(TypeSafeHTTPResponse(status_code=200, body="not-json{", elapsed_ms=5.0)),
    ],
)
def test_transport_called_exactly_once_per_evaluate(transport) -> None:
    provider = make_provider(transport)
    provider.evaluate(make_choice_request())
    assert len(transport.calls) == 1


def test_no_internal_replay_after_ambiguous_outcome() -> None:
    transport = FakeTransport(error=TimeoutError("timed out"))
    provider = make_provider(transport)
    first = provider.evaluate(make_choice_request())
    second = provider.evaluate(make_choice_request())
    assert first.error.kind is SemanticEvidenceErrorKind.TIMEOUT
    assert second.error.kind is SemanticEvidenceErrorKind.TIMEOUT
    assert len(transport.calls) == 2


# ---------------------------------------------------------------------------
# Authority boundaries
# ---------------------------------------------------------------------------


def test_evidence_is_never_authoritative() -> None:
    cases = [
        FakeTransport(ok_choice_response()),
        FakeTransport(error=TimeoutError()),
        FakeTransport(error=ConnectionError()),
        FakeTransport(respond(choice_answer(), status=401, body="{}")),
        FakeTransport(respond(choice_answer(), status=429, body="{}")),
        FakeTransport(respond(choice_answer(), status=529, body="{}")),
        FakeTransport(TypeSafeHTTPResponse(status_code=200, body="{}", elapsed_ms=1.0)),
    ]
    for transport in cases:
        evidence = make_provider(transport).evaluate(make_choice_request())
        assert evidence.authoritative_for_action is False


def test_evidence_type_rejects_authority_claim() -> None:
    with pytest.raises(ValueError):
        SemanticEvidence(
            provider=TYPESAFE_PROVIDER_NAME,
            model=PINNED_TYPESAFE_MODEL,
            primitive=SemanticPrimitive.CHOICE,
            authoritative_for_action=True,
        )


# ---------------------------------------------------------------------------
# Upstream integration through the accepted #502 core
# ---------------------------------------------------------------------------


def test_off_shadow_advisory_modes_consume_adapter_evidence() -> None:
    valid = make_provider(FakeTransport(ok_choice_response())).evaluate(
        make_choice_request()
    )
    decision = evaluate_semantic_decision(
        make_choice_request(), valid, SemanticDecisionMode.OFF
    )
    assert decision.disposition is SemanticDisposition.BYPASS
    assert decision.reason is SemanticDecisionReason.MODE_OFF

    decision = evaluate_semantic_decision(
        make_choice_request(), valid, SemanticDecisionMode.SHADOW
    )
    assert decision.disposition is SemanticDisposition.OBSERVE
    assert decision.reason is SemanticDecisionReason.SHADOW_OBSERVE

    decision = evaluate_semantic_decision(
        make_choice_request(), valid, SemanticDecisionMode.ADVISORY
    )
    assert decision.disposition is SemanticDisposition.ADVISE
    assert decision.reason is SemanticDecisionReason.ADVISORY_GATES_SATISFIED


@pytest.mark.parametrize(
    "transport,kind",
    [
        (FakeTransport(error=TimeoutError()), SemanticEvidenceErrorKind.TIMEOUT),
        (FakeTransport(respond(choice_answer(), status=401, body="{}")), SemanticEvidenceErrorKind.AUTH),
        (FakeTransport(respond(choice_answer(), status=429, body="{}")), SemanticEvidenceErrorKind.RATE_LIMIT),
        (FakeTransport(respond(choice_answer(), status=529, body="{}")), SemanticEvidenceErrorKind.OVERLOAD),
        (FakeTransport(error=ConnectionError()), SemanticEvidenceErrorKind.TRANSPORT),
        (FakeTransport(TypeSafeHTTPResponse(status_code=200, body="not-json{", elapsed_ms=1.0)), SemanticEvidenceErrorKind.SCHEMA),
    ],
)
def test_typed_errors_deterministically_escalate_upstream(transport, kind) -> None:
    evidence = make_provider(transport).evaluate(make_choice_request())
    assert evidence.error is not None
    assert evidence.error.kind is kind
    for mode in (SemanticDecisionMode.SHADOW, SemanticDecisionMode.ADVISORY):
        decision = evaluate_semantic_decision(make_choice_request(), evidence, mode)
        assert decision.disposition is SemanticDisposition.ESCALATE
        assert decision.reason is SemanticDecisionReason.PROVIDER_ERROR


def test_module_has_no_default_network_transport_wiring() -> None:
    source = Path(__file__).resolve().parents[1].joinpath(
        "src", "a_conductor", "typesafe_semantic_provider.py"
    ).read_text(encoding="utf-8")
    assert "UrllibTypeSafeTransport" in source
    assert "requests" not in source.replace("urllib.request", "")
