from __future__ import annotations

import pytest

from src.a_conductor.semantic_admission import (
    FamilyAdmission,
    SemanticAdmissionError,
    SemanticAdmissionPolicy,
    SemanticFallbackReason,
    SemanticProductionAdmission,
)
from src.a_conductor.typesafe_semantic_provider import (
    TypeSafeHTTPResponse,
    TypeSafeSemanticDecisionProvider,
)
from src.a_conductor.semantic_decision import (
    SemanticDecisionFamily,
    SemanticDecisionMode,
    SemanticDecisionRequest,
    SemanticDisposition,
    SemanticEvidence,
    SemanticEvidenceErrorKind,
    SemanticPrimitive,
    SemanticProviderError,
    SemanticRiskLevel,
)


class CountingProvider:
    def __init__(self, evidence: SemanticEvidence) -> None:
        self.evidence = evidence
        self.calls = 0
        self.requests: list[SemanticDecisionRequest] = []

    def evaluate(self, request: SemanticDecisionRequest) -> SemanticEvidence:
        self.calls += 1
        self.requests.append(request)
        return self.evidence


def choice_request(family=SemanticDecisionFamily.TASK_CLASSIFICATION):
    return SemanticDecisionRequest(
        request_id="req-1",
        family=family,
        primitive=SemanticPrimitive.CHOICE,
        state={"summary": "synthetic public documentation task"},
        risk=SemanticRiskLevel.LOW,
        options=("bugfix", "feature", "docs", "review"),
    )


def noul_request(family=SemanticDecisionFamily.EVIDENCE_RELEVANCE):
    return SemanticDecisionRequest(
        request_id="req-2",
        family=family,
        primitive=SemanticPrimitive.NOUL,
        state={"summary": "synthetic public evidence"},
        risk=SemanticRiskLevel.LOW,
        decision_threshold=0.5,
    )


def choice_evidence(confidence=0.95):
    return SemanticEvidence(
        provider="typesafe",
        model="jev-1.13.0",
        primitive=SemanticPrimitive.CHOICE,
        answer="docs",
        confidence=confidence,
        probabilities={"bugfix": 0.0, "feature": 0.0, "docs": confidence, "review": 1.0 - confidence},
        input_usage=10,
        output_usage=2,
        latency_ms=12.0,
    )


def noul_evidence(answer=0.95):
    return SemanticEvidence(
        provider="typesafe",
        model="jev-1.13.0",
        primitive=SemanticPrimitive.NOUL,
        answer=answer,
        input_usage=8,
        output_usage=1,
        latency_ms=9.0,
    )


def error_evidence(kind):
    return SemanticEvidence(
        provider="typesafe",
        model="jev-1.13.0",
        primitive=SemanticPrimitive.CHOICE,
        error=SemanticProviderError(kind=kind, detail="bounded failure"),
    )


def admitted_choice(mode=SemanticDecisionMode.ADVISORY):
    return SemanticAdmissionPolicy(
        {
            SemanticDecisionFamily.TASK_CLASSIFICATION: FamilyAdmission(
                mode=mode,
                heldout_candidate=True,
                evidence_ref="JEV4:heldout-v1:task",
                min_confidence=0.9,
            )
        }
    )


def test_off_is_safe_default_and_never_calls_provider():
    provider = CountingProvider(choice_evidence())
    result = SemanticProductionAdmission(provider).evaluate(choice_request())
    assert provider.calls == 0
    assert result.decision.mode is SemanticDecisionMode.OFF
    assert result.decision.disposition is SemanticDisposition.BYPASS
    assert result.telemetry.fallback_reason is SemanticFallbackReason.MODE_OFF
    assert result.telemetry.authoritative_for_action is False


def test_missing_family_is_off_even_when_another_family_is_admitted():
    provider = CountingProvider(choice_evidence())
    result = SemanticProductionAdmission(provider, admitted_choice()).evaluate(
        choice_request(SemanticDecisionFamily.SKILL_SUGGESTION)
    )
    assert provider.calls == 0
    assert result.decision.disposition is SemanticDisposition.BYPASS


def test_advisory_injects_heldout_threshold_and_can_advise():
    provider = CountingProvider(choice_evidence(0.95))
    result = SemanticProductionAdmission(provider, admitted_choice()).evaluate(
        choice_request()
    )
    assert provider.calls == 1
    assert provider.requests[0].min_confidence == pytest.approx(0.9)
    assert result.decision.disposition is SemanticDisposition.ADVISE
    assert result.telemetry.evidence_ref == "JEV4:heldout-v1:task"
    assert result.telemetry.confidence == pytest.approx(0.95)
    assert not hasattr(result.telemetry, "state")


def test_shadow_observes_but_never_advises():
    provider = CountingProvider(choice_evidence())
    result = SemanticProductionAdmission(
        provider, admitted_choice(SemanticDecisionMode.SHADOW)
    ).evaluate(choice_request())
    assert provider.calls == 1
    assert result.decision.disposition is SemanticDisposition.OBSERVE


def test_choice_below_heldout_threshold_falls_back():
    provider = CountingProvider(choice_evidence(0.89))
    result = SemanticProductionAdmission(provider, admitted_choice()).evaluate(
        choice_request()
    )
    assert result.decision.disposition is SemanticDisposition.ESCALATE
    assert result.telemetry.fallback_reason is SemanticFallbackReason.POLICY_ESCALATION


def test_noul_review_band_is_bound_from_heldout_evidence():
    policy = SemanticAdmissionPolicy(
        {
            SemanticDecisionFamily.EVIDENCE_RELEVANCE: FamilyAdmission(
                mode=SemanticDecisionMode.ADVISORY,
                heldout_candidate=True,
                evidence_ref="JEV4:heldout-v1:evidence",
                review_band=(0.1, 0.9),
            )
        }
    )
    provider = CountingProvider(noul_evidence(0.95))
    result = SemanticProductionAdmission(provider, policy).evaluate(noul_request())
    assert provider.requests[0].review_band == pytest.approx((0.1, 0.9))
    assert provider.requests[0].decision_threshold == pytest.approx(0.5)
    assert result.decision.disposition is SemanticDisposition.ADVISE


@pytest.mark.parametrize(
    ("kind", "reason"),
    [
        (SemanticEvidenceErrorKind.AUTH, SemanticFallbackReason.PROVIDER_AUTH),
        (SemanticEvidenceErrorKind.RATE_LIMIT, SemanticFallbackReason.PROVIDER_RATE_LIMIT),
        (SemanticEvidenceErrorKind.OVERLOAD, SemanticFallbackReason.PROVIDER_OVERLOAD),
        (SemanticEvidenceErrorKind.SCHEMA, SemanticFallbackReason.PROVIDER_SCHEMA),
        (SemanticEvidenceErrorKind.TIMEOUT, SemanticFallbackReason.AMBIGUOUS_TRANSPORT),
        (SemanticEvidenceErrorKind.TRANSPORT, SemanticFallbackReason.AMBIGUOUS_TRANSPORT),
        (SemanticEvidenceErrorKind.UNKNOWN, SemanticFallbackReason.PROVIDER_UNKNOWN),
    ],
)
def test_fault_matrix_fails_closed_without_retry(kind, reason):
    provider = CountingProvider(error_evidence(kind))
    result = SemanticProductionAdmission(provider, admitted_choice()).evaluate(
        choice_request()
    )
    assert provider.calls == 1
    assert result.decision.disposition is SemanticDisposition.ESCALATE
    assert result.telemetry.fallback_reason is reason
    assert result.telemetry.authoritative_for_action is False


def test_rollback_off_stops_calls_without_task_state_migration():
    provider = CountingProvider(choice_evidence())
    router = SemanticProductionAdmission(provider, admitted_choice())
    first = router.evaluate(choice_request())
    assert first.decision.disposition is SemanticDisposition.ADVISE
    router.rollback_off()
    second = router.evaluate(choice_request())
    assert provider.calls == 1
    assert second.decision.disposition is SemanticDisposition.BYPASS
    assert router.policy.families == {}


def test_frontier_only_family_cannot_be_enabled():
    with pytest.raises(SemanticAdmissionError, match="frontier-only"):
        SemanticAdmissionPolicy(
            {
                SemanticDecisionFamily.REVIEW_SEVERITY: FamilyAdmission(
                    mode=SemanticDecisionMode.ADVISORY,
                    heldout_candidate=True,
                    evidence_ref="not-admissible",
                    min_confidence=0.9,
                )
            }
        )


def test_off_admission_rejects_evidence_reference_before_telemetry():
    with pytest.raises(SemanticAdmissionError, match="OFF admission"):
        FamilyAdmission(
            mode=SemanticDecisionMode.OFF,
            evidence_ref="PRIVATE secret note",
        )


def test_enabled_admission_requires_heldout_evidence_reference():
    with pytest.raises(SemanticAdmissionError, match="held-out"):
        FamilyAdmission(
            mode=SemanticDecisionMode.ADVISORY,
            heldout_candidate=True,
            min_confidence=0.9,
        )


def test_enabled_admission_requires_candidate_verdict():
    with pytest.raises(SemanticAdmissionError, match="CANDIDATE"):
        FamilyAdmission(
            mode=SemanticDecisionMode.ADVISORY,
            evidence_ref="JEV4:heldout-v1:task",
            min_confidence=0.9,
        )


def test_noul_without_review_band_fails_before_provider_call():
    policy = SemanticAdmissionPolicy(
        {
            SemanticDecisionFamily.EVIDENCE_RELEVANCE: FamilyAdmission(
                mode=SemanticDecisionMode.ADVISORY,
                heldout_candidate=True,
                evidence_ref="JEV4:bad-policy",
                min_confidence=0.9,
            )
        }
    )
    provider = CountingProvider(noul_evidence())
    with pytest.raises(SemanticAdmissionError, match="NOUL admission"):
        SemanticProductionAdmission(provider, policy).evaluate(noul_request())
    assert provider.calls == 0


class StaticResolver:
    def resolve(self, reference: str) -> str:
        return "synthetic-test-secret"


class FaultTransport:
    def __init__(self, *, status=200, body="{}", error=None):
        self.status = status
        self.body = body
        self.error = error
        self.calls = 0

    def post(self, request):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return TypeSafeHTTPResponse(
            status_code=self.status,
            body=self.body,
            elapsed_ms=5.0,
        )


def integrated_router(transport):
    provider = TypeSafeSemanticDecisionProvider(
        transport=transport,
        secret_resolver=StaticResolver(),
    )
    return SemanticProductionAdmission(provider, admitted_choice())


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (401, SemanticFallbackReason.PROVIDER_AUTH),
        (403, SemanticFallbackReason.PROVIDER_AUTH),
        (429, SemanticFallbackReason.PROVIDER_RATE_LIMIT),
        (529, SemanticFallbackReason.PROVIDER_OVERLOAD),
        (500, SemanticFallbackReason.AMBIGUOUS_TRANSPORT),
        (503, SemanticFallbackReason.AMBIGUOUS_TRANSPORT),
    ],
)
def test_typesafe_http_fault_e2e_falls_back_once(status, reason):
    transport = FaultTransport(status=status)
    result = integrated_router(transport).evaluate(choice_request())
    assert transport.calls == 1
    assert result.decision.disposition is SemanticDisposition.ESCALATE
    assert result.telemetry.fallback_reason is reason


def test_typesafe_timeout_e2e_is_ambiguous_and_not_replayed():
    transport = FaultTransport(error=TimeoutError("bounded timeout"))
    result = integrated_router(transport).evaluate(choice_request())
    assert transport.calls == 1
    assert result.telemetry.fallback_reason is SemanticFallbackReason.AMBIGUOUS_TRANSPORT


def test_typesafe_malformed_response_e2e_falls_back_once():
    transport = FaultTransport(status=200, body="not-json")
    result = integrated_router(transport).evaluate(choice_request())
    assert transport.calls == 1
    assert result.decision.disposition is SemanticDisposition.ESCALATE
    assert result.telemetry.fallback_reason is SemanticFallbackReason.PROVIDER_SCHEMA


def test_rate_limit_opens_family_circuit_until_explicit_reset():
    transport = FaultTransport(status=429)
    router = integrated_router(transport)
    first = router.evaluate(choice_request())
    second = router.evaluate(choice_request())
    assert first.telemetry.fallback_reason is SemanticFallbackReason.PROVIDER_RATE_LIMIT
    assert second.telemetry.fallback_reason is SemanticFallbackReason.PROVIDER_RATE_LIMIT
    assert transport.calls == 1
    router.reset_provider_fault(SemanticDecisionFamily.TASK_CLASSIFICATION)
    router.evaluate(choice_request())
    assert transport.calls == 2


def test_telemetry_drops_unsafe_provider_identity():
    evidence = SemanticEvidence(
        provider="unsafe identity with spaces",
        model="jev-1.13.0",
        primitive=SemanticPrimitive.CHOICE,
        answer="docs",
        confidence=0.95,
        probabilities={"bugfix": 0.0, "feature": 0.0, "docs": 0.95, "review": 0.05},
    )
    result = SemanticProductionAdmission(
        CountingProvider(evidence), admitted_choice()
    ).evaluate(choice_request())
    assert result.telemetry.provider is None
    assert result.telemetry.model == "jev-1.13.0"


def test_evidence_reference_must_be_safe_for_telemetry():
    with pytest.raises(SemanticAdmissionError, match="bounded safe"):
        FamilyAdmission(
            mode=SemanticDecisionMode.ADVISORY,
            heldout_candidate=True,
            evidence_ref="private note with spaces",
            min_confidence=0.9,
        )


class RaisingProvider:
    def __init__(self, exc):
        self.exc = exc
        self.calls = 0

    def evaluate(self, request):
        self.calls += 1
        raise self.exc


def test_provider_exception_fails_closed_without_escape_or_retry():
    provider = RaisingProvider(RuntimeError("provider bug with private detail"))
    result = SemanticProductionAdmission(provider, admitted_choice()).evaluate(choice_request())
    assert provider.calls == 1
    assert result.decision.disposition is SemanticDisposition.ESCALATE
    assert result.telemetry.fallback_reason is SemanticFallbackReason.PROVIDER_UNKNOWN
    assert result.telemetry.provider is None


def test_raw_timeout_exception_opens_ambiguous_transport_circuit():
    provider = RaisingProvider(TimeoutError("after-send outcome unknown"))
    router = SemanticProductionAdmission(provider, admitted_choice())
    first = router.evaluate(choice_request())
    second = router.evaluate(choice_request())
    assert first.telemetry.fallback_reason is SemanticFallbackReason.AMBIGUOUS_TRANSPORT
    assert second.telemetry.fallback_reason is SemanticFallbackReason.AMBIGUOUS_TRANSPORT
    assert provider.calls == 1
