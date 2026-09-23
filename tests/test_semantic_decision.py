from __future__ import annotations

import dataclasses
import math
import types
from pathlib import Path

import pytest

from a_conductor.semantic_decision import (
    DEFAULT_SEMANTIC_RISK_POLICY,
    FRONTIER_ONLY_FAMILIES,
    JEV_ELIGIBLE_FAMILIES,
    FakeSemanticDecisionProvider,
    SemanticDecision,
    SemanticDecisionContractError,
    SemanticDecisionFamily,
    SemanticDecisionMode,
    SemanticDecisionProvider,
    SemanticDecisionReason,
    SemanticDisposition,
    SemanticEvidence,
    SemanticEvidenceErrorKind,
    SemanticPrimitive,
    SemanticProviderError,
    SemanticRiskLevel,
    SemanticRiskPolicy,
    SemanticDecisionRequest,
    evaluate_semantic_decision,
)


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "src" / "a_conductor" / "semantic_decision.py"
)


def make_request(**overrides) -> SemanticDecisionRequest:
    defaults: dict = {
        "request_id": "req-001",
        "family": SemanticDecisionFamily.TASK_CLASSIFICATION,
        "primitive": SemanticPrimitive.CHOICE,
        "state": {"summary": "Focused tests fail with a missing module import."},
        "risk": SemanticRiskLevel.MEDIUM,
        "options": ("bugfix", "feature", "docs", "review"),
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


def make_evidence(**overrides) -> SemanticEvidence:
    defaults: dict = {
        "provider": "typesafe",
        "model": "jev-1.13.0",
        "primitive": SemanticPrimitive.CHOICE,
        "answer": "bugfix",
        "confidence": 0.91,
        "probabilities": {
            "bugfix": 0.92,
            "feature": 0.03,
            "docs": 0.02,
            "review": 0.03,
        },
        "input_usage": 392,
        "output_usage": 40,
        "latency_ms": 120.0,
    }
    defaults.update(overrides)
    return SemanticEvidence(**defaults)


def make_noul_evidence(**overrides) -> SemanticEvidence:
    defaults: dict = {
        "provider": "typesafe",
        "model": "jev-1.13.0",
        "primitive": SemanticPrimitive.NOUL,
        "answer": 0.94,
        "input_usage": 300,
        "output_usage": 18,
        "latency_ms": 90.0,
    }
    defaults.update(overrides)
    return SemanticEvidence(**defaults)


# ---------------------------------------------------------------------------
# Vocabulary and eligibility
# ---------------------------------------------------------------------------


def test_family_and_primitive_vocabulary_is_exact() -> None:
    assert {family.value for family in SemanticDecisionFamily} == {
        "task_classification",
        "skill_suggestion",
        "failure_classification",
        "evidence_relevance",
        "escalation_decision",
        "review_severity",
    }
    assert {primitive.value for primitive in SemanticPrimitive} == {
        "choice",
        "score",
        "noul",
    }
    assert {mode.value for mode in SemanticDecisionMode} == {
        "OFF",
        "SHADOW",
        "ADVISORY",
    }
    assert {disposition.value for disposition in SemanticDisposition} == {
        "BYPASS",
        "OBSERVE",
        "ADVISE",
        "ESCALATE",
    }
    assert {risk.value for risk in SemanticRiskLevel} == {"low", "medium", "high"}


def test_only_benchmark_proven_families_are_jev_eligible() -> None:
    assert JEV_ELIGIBLE_FAMILIES == frozenset(
        {
            SemanticDecisionFamily.TASK_CLASSIFICATION,
            SemanticDecisionFamily.SKILL_SUGGESTION,
            SemanticDecisionFamily.FAILURE_CLASSIFICATION,
            SemanticDecisionFamily.EVIDENCE_RELEVANCE,
            SemanticDecisionFamily.ESCALATION_DECISION,
        }
    )
    assert FRONTIER_ONLY_FAMILIES == frozenset({SemanticDecisionFamily.REVIEW_SEVERITY})
    assert JEV_ELIGIBLE_FAMILIES | FRONTIER_ONLY_FAMILIES == frozenset(
        SemanticDecisionFamily
    )
    assert not JEV_ELIGIBLE_FAMILIES & FRONTIER_ONLY_FAMILIES


# ---------------------------------------------------------------------------
# Request contract
# ---------------------------------------------------------------------------


def test_request_is_immutable_with_frozen_state() -> None:
    request = make_request(state={"outer": {"inner": [1, 2]}})

    with pytest.raises(dataclasses.FrozenInstanceError):
        request.request_id = "other"  # type: ignore[misc]

    assert isinstance(request.state, types.MappingProxyType)
    with pytest.raises(TypeError):
        request.state["outer"] = 1  # type: ignore[index]
    assert isinstance(request.state["outer"], types.MappingProxyType)
    assert request.state["outer"]["inner"] == (1, 2)


def test_request_coerces_enum_values_and_normalizes_review_band() -> None:
    request = SemanticDecisionRequest(
        request_id="req-coerce",
        family="evidence_relevance",
        primitive="noul",
        state={"claim": "c"},
        risk="medium",
        review_band=[0.3, 0.7],
    )

    assert request.family is SemanticDecisionFamily.EVIDENCE_RELEVANCE
    assert request.primitive is SemanticPrimitive.NOUL
    assert request.risk is SemanticRiskLevel.MEDIUM
    assert request.review_band == (0.3, 0.7)
    assert isinstance(request.review_band, tuple)


@pytest.mark.parametrize(
    "overrides",
    [
        {"request_id": ""},
        {"request_id": "x" * 129},
        {"request_id": "bad\nid"},
        {"family": "vibes_classification"},
        {"primitive": "vibe"},
        {"risk": "extreme"},
    ],
)
def test_request_rejects_malformed_identity_fields(overrides: dict) -> None:
    with pytest.raises(SemanticDecisionContractError):
        make_request(**overrides)


@pytest.mark.parametrize(
    "state",
    [
        {f"key{index}": "value" for index in range(33)},
        {"deep": {"a": {"b": {"c": {"d": {"e": 1}}}}}},
        {"text": "x" * 4097},
        {"blob": b"bytes"},
        {"secret": "sk-" + ("a" * 20)},
        {"leak": "api_key =" + ("a" * 16)},
        {"nan": float("nan")},
        {1: "non-string-key"},
        {"ctrl": "bad\x00value"},
    ],
)
def test_request_rejects_unsanitized_or_unbounded_state(state: dict) -> None:
    with pytest.raises(SemanticDecisionContractError):
        make_request(state=state)


@pytest.mark.parametrize(
    "overrides",
    [
        {"options": ("bugfix",)},
        {"options": ("bugfix", "bugfix")},
        {"options": ("bugfix", "")},
        {"options": ("bugfix", "x" * 129)},
        {"score_levels": 4},
        {"review_band": (0.3, 0.7)},
        {"decision_threshold": 0.5},
    ],
)
def test_choice_request_metadata_is_explicit(overrides: dict) -> None:
    with pytest.raises(SemanticDecisionContractError):
        make_request(**overrides)


def test_score_request_requires_levels_and_rejects_cross_metadata() -> None:
    valid = make_request(
        primitive=SemanticPrimitive.SCORE,
        options=(),
        score_levels=4,
        min_confidence=None,
    )
    assert valid.score_levels == 4

    for overrides in (
        {"score_levels": 1},
        {"score_levels": 11},
        {"score_levels": True},
        {"score_levels": None},
        {"options": ("a", "b")},
        {"review_band": (0.3, 0.7)},
        {"decision_threshold": 0.5},
    ):
        kwargs = {
            "primitive": SemanticPrimitive.SCORE,
            "options": (),
            "min_confidence": None,
        }
        kwargs.update(overrides)
        with pytest.raises(SemanticDecisionContractError):
            make_request(**kwargs)


def test_noul_request_rejects_confidence_semantics_and_bad_bands() -> None:
    with pytest.raises(SemanticDecisionContractError):
        make_noul_request(min_confidence=0.8)
    with pytest.raises(SemanticDecisionContractError):
        make_noul_request(options=("a", "b"))
    with pytest.raises(SemanticDecisionContractError):
        make_noul_request(score_levels=4)
    with pytest.raises(SemanticDecisionContractError):
        make_noul_request(decision_threshold=1.5)
    with pytest.raises(SemanticDecisionContractError):
        make_noul_request(review_band=(0.7, 0.3))
    with pytest.raises(SemanticDecisionContractError):
        make_noul_request(review_band=(0.3,))


def test_min_confidence_must_be_a_probability_when_present() -> None:
    with pytest.raises(SemanticDecisionContractError):
        make_request(min_confidence=1.2)
    with pytest.raises(SemanticDecisionContractError):
        make_request(min_confidence=float("nan"))


# ---------------------------------------------------------------------------
# Evidence envelope
# ---------------------------------------------------------------------------


def test_evidence_is_structurally_never_authoritative() -> None:
    evidence = make_evidence()
    assert evidence.authoritative_for_action is False

    with pytest.raises(SemanticDecisionContractError):
        make_evidence(authoritative_for_action=True)


def test_evidence_probabilities_are_read_only() -> None:
    evidence = make_evidence()
    assert isinstance(evidence.probabilities, types.MappingProxyType)
    with pytest.raises(TypeError):
        evidence.probabilities["extra"] = 1.0  # type: ignore[index]


@pytest.mark.parametrize(
    "overrides",
    [
        {"provider": ""},
        {"model": ""},
        {"provider": "p" * 129},
        {"primitive": "vibe"},
        {"latency_ms": -1.0},
        {"latency_ms": float("nan")},
        {"latency_ms": float("inf")},
        {"input_usage": -1},
        {"output_usage": -2},
        {"input_usage": True},
        {"output_usage": 1.5},
        {"error": "SCHEMA"},
    ],
)
def test_evidence_rejects_malformed_envelope_fields(overrides: dict) -> None:
    with pytest.raises(SemanticDecisionContractError):
        make_evidence(**overrides)


def test_provider_error_detail_is_bounded_non_empty_text() -> None:
    assert SemanticProviderError(
        kind=SemanticEvidenceErrorKind.TIMEOUT, detail="upstream timeout"
    ).kind is SemanticEvidenceErrorKind.TIMEOUT

    with pytest.raises(SemanticDecisionContractError):
        SemanticProviderError(
            kind=SemanticEvidenceErrorKind.TIMEOUT, detail=""
        )
    with pytest.raises(SemanticDecisionContractError):
        SemanticProviderError(
            kind=SemanticEvidenceErrorKind.TIMEOUT, detail="x" * 513
        )


# ---------------------------------------------------------------------------
# Fake provider and protocol
# ---------------------------------------------------------------------------


def test_fake_provider_satisfies_protocol_and_is_deterministic() -> None:
    scripted = make_evidence()
    provider = FakeSemanticDecisionProvider(scripted={"req-001": scripted})

    assert isinstance(provider, SemanticDecisionProvider)

    first = provider.evaluate(make_request())
    second = provider.evaluate(make_request())
    assert first == scripted
    assert first == second


def test_fake_provider_returns_typed_error_for_missing_scripted_id() -> None:
    provider = FakeSemanticDecisionProvider(scripted={})
    evidence = provider.evaluate(make_request(request_id="req-missing"))

    assert evidence.error is not None
    assert evidence.error.kind is SemanticEvidenceErrorKind.SCHEMA
    assert "req-missing" in evidence.error.detail


# ---------------------------------------------------------------------------
# Mode and disposition policy
# ---------------------------------------------------------------------------


def test_off_mode_bypasses_even_with_error_evidence() -> None:
    decision = evaluate_semantic_decision(
        make_request(),
        make_evidence(
            error=SemanticProviderError(
                kind=SemanticEvidenceErrorKind.TRANSPORT, detail="broken pipe"
            )
        ),
        SemanticDecisionMode.OFF,
    )

    assert decision.disposition is SemanticDisposition.BYPASS
    assert decision.reason is SemanticDecisionReason.MODE_OFF


def test_shadow_mode_observes_valid_evidence_and_never_advises() -> None:
    for decision in (
        evaluate_semantic_decision(
            make_request(), make_evidence(), SemanticDecisionMode.SHADOW
        ),
        evaluate_semantic_decision(
            make_noul_request(),
            make_noul_evidence(),
            SemanticDecisionMode.SHADOW,
        ),
        evaluate_semantic_decision(
            make_request(
                family=SemanticDecisionFamily.REVIEW_SEVERITY,
            ),
            make_evidence(),
            SemanticDecisionMode.SHADOW,
        ),
        evaluate_semantic_decision(
            make_request(), make_evidence(confidence=0.1), SemanticDecisionMode.SHADOW
        ),
    ):
        assert decision.disposition is SemanticDisposition.OBSERVE
        assert decision.reason is SemanticDecisionReason.SHADOW_OBSERVE


def test_shadow_mode_escalates_provider_errors() -> None:
    decision = evaluate_semantic_decision(
        make_request(),
        make_evidence(
            error=SemanticProviderError(
                kind=SemanticEvidenceErrorKind.RATE_LIMIT, detail="http 429"
            )
        ),
        SemanticDecisionMode.SHADOW,
    )

    assert decision.disposition is SemanticDisposition.ESCALATE
    assert decision.reason is SemanticDecisionReason.PROVIDER_ERROR


def test_advisory_mode_advises_when_all_gates_pass() -> None:
    decision = evaluate_semantic_decision(
        make_request(), make_evidence(), SemanticDecisionMode.ADVISORY
    )

    assert decision.disposition is SemanticDisposition.ADVISE
    assert decision.reason is SemanticDecisionReason.ADVISORY_GATES_SATISFIED
    assert decision.evidence is not None
    assert decision.evidence.answer == "bugfix"
    assert decision.evidence.authoritative_for_action is False


@pytest.mark.parametrize(
    ("evidence", "reason"),
    [
        (
            make_evidence(primitive=SemanticPrimitive.SCORE, answer=2.0),
            SemanticDecisionReason.EVIDENCE_PRIMITIVE_MISMATCH,
        ),
        (
            make_evidence(answer="not-an-option"),
            SemanticDecisionReason.EVIDENCE_ANSWER_INVALID,
        ),
        (
            make_evidence(answer=42),
            SemanticDecisionReason.EVIDENCE_ANSWER_INVALID,
        ),
        (
            make_evidence(confidence=None),
            SemanticDecisionReason.EVIDENCE_CONFIDENCE_MISSING,
        ),
        (
            make_evidence(confidence=float("nan")),
            SemanticDecisionReason.EVIDENCE_CONFIDENCE_INVALID,
        ),
        (
            make_evidence(confidence=1.4),
            SemanticDecisionReason.EVIDENCE_CONFIDENCE_INVALID,
        ),
        (
            make_evidence(probabilities=None),
            SemanticDecisionReason.EVIDENCE_PROBABILITIES_INVALID,
        ),
        (
            make_evidence(
                probabilities={"bugfix": 0.5, "feature": 0.4, "docs": 0.0, "review": 0.0}
            ),
            SemanticDecisionReason.EVIDENCE_PROBABILITIES_INVALID,
        ),
        (
            make_evidence(
                probabilities={"bugfix": 0.9, "other": 0.1}
            ),
            SemanticDecisionReason.EVIDENCE_PROBABILITIES_INVALID,
        ),
        (
            make_evidence(
                probabilities={"bugfix": 1.5, "feature": -0.5, "docs": 0.0, "review": 0.0}
            ),
            SemanticDecisionReason.EVIDENCE_PROBABILITIES_INVALID,
        ),
    ],
)
def test_invalid_evidence_escalates_in_shadow_and_advisory(
    evidence: SemanticEvidence, reason: SemanticDecisionReason
) -> None:
    for mode in (SemanticDecisionMode.SHADOW, SemanticDecisionMode.ADVISORY):
        decision = evaluate_semantic_decision(make_request(), evidence, mode)
        assert decision.disposition is SemanticDisposition.ESCALATE
        assert decision.reason is reason


def test_score_missing_probabilities_escalates() -> None:
    request = make_request(
        primitive=SemanticPrimitive.SCORE, options=(), score_levels=4, min_confidence=None
    )
    evidence = make_evidence(
        primitive=SemanticPrimitive.SCORE,
        answer=2.0,
        confidence=0.9,
        probabilities=None,
    )
    for mode in (SemanticDecisionMode.SHADOW, SemanticDecisionMode.ADVISORY):
        decision = evaluate_semantic_decision(request, evidence, mode)
        assert decision.disposition is SemanticDisposition.ESCALATE
        assert decision.reason is SemanticDecisionReason.EVIDENCE_PROBABILITIES_INVALID


def test_out_of_range_and_nonfinite_answers_escalate() -> None:
    request = make_request(
        primitive=SemanticPrimitive.SCORE, options=(), score_levels=4, min_confidence=None
    )
    score_evidence = make_evidence(
        primitive=SemanticPrimitive.SCORE, answer=3.5, confidence=0.9,
        probabilities={"0": 0.05, "1": 0.05, "2": 0.1, "3": 0.8},
    )
    decision = evaluate_semantic_decision(request, score_evidence, SemanticDecisionMode.ADVISORY)
    assert decision.disposition is SemanticDisposition.ESCALATE
    assert decision.reason is SemanticDecisionReason.EVIDENCE_ANSWER_INVALID

    noul_evidence = make_noul_evidence(answer=1.7)
    decision = evaluate_semantic_decision(
        make_noul_request(), noul_evidence, SemanticDecisionMode.ADVISORY
    )
    assert decision.disposition is SemanticDisposition.ESCALATE
    assert decision.reason is SemanticDecisionReason.EVIDENCE_ANSWER_INVALID

    nonfinite = make_noul_evidence(answer=float("nan"))
    decision = evaluate_semantic_decision(
        make_noul_request(), nonfinite, SemanticDecisionMode.ADVISORY
    )
    assert decision.disposition is SemanticDisposition.ESCALATE
    assert decision.reason is SemanticDecisionReason.EVIDENCE_ANSWER_INVALID


def test_noul_evidence_must_not_invent_confidence_or_probabilities() -> None:
    with_confidence = make_noul_evidence(confidence=0.9)
    decision = evaluate_semantic_decision(
        make_noul_request(), with_confidence, SemanticDecisionMode.ADVISORY
    )
    assert decision.disposition is SemanticDisposition.ESCALATE
    assert decision.reason is SemanticDecisionReason.EVIDENCE_NOUL_FORBIDDEN_FIELD

    with_probabilities = make_noul_evidence(
        probabilities={"true": 0.9, "false": 0.1}
    )
    decision = evaluate_semantic_decision(
        make_noul_request(), with_probabilities, SemanticDecisionMode.ADVISORY
    )
    assert decision.disposition is SemanticDisposition.ESCALATE
    assert decision.reason is SemanticDecisionReason.EVIDENCE_NOUL_FORBIDDEN_FIELD


def test_advisory_escalates_frontier_only_family() -> None:
    decision = evaluate_semantic_decision(
        make_request(family=SemanticDecisionFamily.REVIEW_SEVERITY),
        make_evidence(),
        SemanticDecisionMode.ADVISORY,
    )

    assert decision.disposition is SemanticDisposition.ESCALATE
    assert decision.reason is SemanticDecisionReason.FAMILY_FRONTIER_ONLY


def test_advisory_escalates_below_min_confidence() -> None:
    decision = evaluate_semantic_decision(
        make_request(min_confidence=0.95),
        make_evidence(confidence=0.91),
        SemanticDecisionMode.ADVISORY,
    )

    assert decision.disposition is SemanticDisposition.ESCALATE
    assert decision.reason is SemanticDecisionReason.CONFIDENCE_BELOW_THRESHOLD


def test_advisory_noul_review_band_escalates_uncertain_answers() -> None:
    inside_band = make_noul_evidence(answer=0.55)
    decision = evaluate_semantic_decision(
        make_noul_request(), inside_band, SemanticDecisionMode.ADVISORY
    )
    assert decision.disposition is SemanticDisposition.ESCALATE
    assert decision.reason is SemanticDecisionReason.REVIEW_BAND_UNCERTAIN

    above_band = make_noul_evidence(answer=0.94)
    decision = evaluate_semantic_decision(
        make_noul_request(), above_band, SemanticDecisionMode.ADVISORY
    )
    assert decision.disposition is SemanticDisposition.ADVISE


def test_default_risk_policy_escalates_high_risk_and_permits_medium() -> None:
    assert DEFAULT_SEMANTIC_RISK_POLICY.max_advise_risk is SemanticRiskLevel.MEDIUM

    high = evaluate_semantic_decision(
        make_request(risk=SemanticRiskLevel.HIGH),
        make_evidence(),
        SemanticDecisionMode.ADVISORY,
    )
    assert high.disposition is SemanticDisposition.ESCALATE
    assert high.reason is SemanticDecisionReason.RISK_ESCALATION_REQUIRED

    medium = evaluate_semantic_decision(
        make_request(risk=SemanticRiskLevel.MEDIUM),
        make_evidence(),
        SemanticDecisionMode.ADVISORY,
    )
    assert medium.disposition is SemanticDisposition.ADVISE


def test_risk_policy_is_explicit_and_can_be_widened() -> None:
    permissive = SemanticRiskPolicy(max_advise_risk=SemanticRiskLevel.HIGH)
    decision = evaluate_semantic_decision(
        make_request(risk=SemanticRiskLevel.HIGH),
        make_evidence(),
        SemanticDecisionMode.ADVISORY,
        risk_policy=permissive,
    )
    assert decision.disposition is SemanticDisposition.ADVISE

    strict = SemanticRiskPolicy(max_advise_risk=SemanticRiskLevel.LOW)
    decision = evaluate_semantic_decision(
        make_request(risk=SemanticRiskLevel.MEDIUM),
        make_evidence(),
        SemanticDecisionMode.ADVISORY,
        risk_policy=strict,
    )
    assert decision.disposition is SemanticDisposition.ESCALATE
    assert decision.reason is SemanticDecisionReason.RISK_ESCALATION_REQUIRED

    with pytest.raises(SemanticDecisionContractError):
        SemanticRiskPolicy(max_advise_risk="extreme")


# ---------------------------------------------------------------------------
# Authority and purity invariants
# ---------------------------------------------------------------------------


def test_decision_output_grants_no_authority() -> None:
    decision = evaluate_semantic_decision(
        make_request(), make_evidence(), SemanticDecisionMode.ADVISORY
    )

    assert {field.name for field in dataclasses.fields(decision)} == {
        "request_id",
        "family",
        "primitive",
        "mode",
        "risk",
        "disposition",
        "reason",
        "evidence",
    }
    assert not any(
        token in reason.value
        for reason in SemanticDecisionReason
        for token in ("GRANT", "AUTHORIZE", "AUTHORISED", "AUTHORIZED", "ACCEPT")
    )
    if decision.evidence is not None:
        assert decision.evidence.authoritative_for_action is False


def test_evaluation_is_deterministic_and_pure() -> None:
    request = make_request()
    evidence = make_evidence()

    first = evaluate_semantic_decision(request, evidence, SemanticDecisionMode.ADVISORY)
    second = evaluate_semantic_decision(request, evidence, SemanticDecisionMode.ADVISORY)

    assert first == second
    assert request == make_request()
    assert evidence == make_evidence()
    assert evidence.probabilities is not None
    assert evidence.probabilities == {
        "bugfix": 0.92,
        "feature": 0.03,
        "docs": 0.02,
        "review": 0.03,
    }
    assert math.isclose(sum(evidence.probabilities.values()), 1.0, abs_tol=1e-6)


def test_decision_echoes_request_identity() -> None:
    decision = evaluate_semantic_decision(
        make_noul_request(),
        make_noul_evidence(),
        SemanticDecisionMode.SHADOW,
    )

    assert decision.request_id == "req-noul-001"
    assert decision.family is SemanticDecisionFamily.EVIDENCE_RELEVANCE
    assert decision.primitive is SemanticPrimitive.NOUL
    assert decision.mode is SemanticDecisionMode.SHADOW
    assert decision.risk is SemanticRiskLevel.MEDIUM


def test_score_evidence_advises_when_rubric_gates_pass() -> None:
    request = make_request(
        request_id="req-score-001",
        family=SemanticDecisionFamily.FAILURE_CLASSIFICATION,
        primitive=SemanticPrimitive.SCORE,
        options=(),
        score_levels=4,
        min_confidence=0.8,
        risk=SemanticRiskLevel.LOW,
    )
    evidence = make_evidence(
        primitive=SemanticPrimitive.SCORE,
        answer=2.0,
        confidence=0.88,
        probabilities={"0": 0.01, "1": 0.05, "2": 0.9, "3": 0.04},
    )

    decision = evaluate_semantic_decision(request, evidence, SemanticDecisionMode.ADVISORY)
    assert decision.disposition is SemanticDisposition.ADVISE


# ---------------------------------------------------------------------------
# Module hygiene
# ---------------------------------------------------------------------------


def test_module_has_no_io_network_environment_or_secret_surface() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    forbidden = [
        "import os",
        "import sys",
        "import subprocess",
        "import socket",
        "import urllib",
        "import requests",
        "import httpx",
        "import pathlib",
        "import json",
        "import secrets",
        "import tempfile",
        "import shutil",
        "os.environ",
        "getenv(",
        "open(",
        "__import__",
    ]

    for token in forbidden:
        assert token not in source, token
