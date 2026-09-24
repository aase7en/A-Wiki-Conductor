"""Production admission boundary for provider-neutral semantic decisions.

JEV/provider output remains evidence only.  This module owns no task, claim,
WIP, mutation, review, merge, completion, release, or acceptance authority.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from .semantic_decision import (
    FRONTIER_ONLY_FAMILIES,
    SemanticDecision,
    SemanticDecisionContractError,
    SemanticDecisionFamily,
    SemanticDecisionMode,
    SemanticDecisionProvider,
    SemanticDecisionReason,
    SemanticDecisionRequest,
    SemanticDisposition,
    SemanticEvidenceErrorKind,
    SemanticPrimitive,
    evaluate_semantic_decision,
)


class SemanticAdmissionError(ValueError):
    """Raised when production admission policy is internally inconsistent."""


class SemanticFallbackReason(str, Enum):
    MODE_OFF = "MODE_OFF"
    FAMILY_NOT_ADMITTED = "FAMILY_NOT_ADMITTED"
    PROVIDER_AUTH = "PROVIDER_AUTH"
    PROVIDER_RATE_LIMIT = "PROVIDER_RATE_LIMIT"
    PROVIDER_OVERLOAD = "PROVIDER_OVERLOAD"
    PROVIDER_SCHEMA = "PROVIDER_SCHEMA"
    AMBIGUOUS_TRANSPORT = "AMBIGUOUS_TRANSPORT"
    PROVIDER_UNKNOWN = "PROVIDER_UNKNOWN"
    POLICY_ESCALATION = "POLICY_ESCALATION"


@dataclass(frozen=True)
class FamilyAdmission:
    """One family-specific, evidence-bound production admission."""

    mode: SemanticDecisionMode = SemanticDecisionMode.OFF
    evidence_ref: str = ""
    min_confidence: float | None = None
    review_band: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        mode = SemanticDecisionMode(self.mode)
        object.__setattr__(self, "mode", mode)
        if mode is SemanticDecisionMode.OFF:
            if self.min_confidence is not None or self.review_band is not None:
                raise SemanticAdmissionError("OFF admission must not carry thresholds")
            return
        if not isinstance(self.evidence_ref, str) or not self.evidence_ref.strip():
            raise SemanticAdmissionError("enabled admission requires held-out evidence_ref")
        if self.min_confidence is not None:
            value = float(self.min_confidence)
            if not 0.0 <= value <= 1.0:
                raise SemanticAdmissionError("min_confidence must be in [0, 1]")
            object.__setattr__(self, "min_confidence", value)
        if self.review_band is not None:
            if len(self.review_band) != 2:
                raise SemanticAdmissionError("review_band must contain two values")
            lower, upper = map(float, self.review_band)
            if not 0.0 <= lower <= upper <= 1.0:
                raise SemanticAdmissionError("review_band must be ordered in [0, 1]")
            object.__setattr__(self, "review_band", (lower, upper))


@dataclass(frozen=True)
class SemanticAdmissionPolicy:
    """Immutable per-family admission map. Missing families are OFF."""

    families: Mapping[SemanticDecisionFamily, FamilyAdmission]
    kill_switch_off: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.families, Mapping):
            raise SemanticAdmissionError("families must be a mapping")
        normalized: dict[SemanticDecisionFamily, FamilyAdmission] = {}
        for raw_family, admission in self.families.items():
            family = SemanticDecisionFamily(raw_family)
            if not isinstance(admission, FamilyAdmission):
                raise SemanticAdmissionError("family admission must use FamilyAdmission")
            if family in FRONTIER_ONLY_FAMILIES and admission.mode is not SemanticDecisionMode.OFF:
                raise SemanticAdmissionError("frontier-only family cannot be production-admitted")
            normalized[family] = admission
        object.__setattr__(self, "families", MappingProxyType(normalized))

    def admission_for(self, family: SemanticDecisionFamily) -> FamilyAdmission:
        if self.kill_switch_off:
            return FamilyAdmission()
        return self.families.get(SemanticDecisionFamily(family), FamilyAdmission())

    @classmethod
    def off(cls) -> "SemanticAdmissionPolicy":
        return cls({})


@dataclass(frozen=True)
class SemanticAdmissionTelemetry:
    """Privacy-safe normalized receipt; raw request/provider payload is excluded."""

    family: SemanticDecisionFamily
    mode: SemanticDecisionMode
    disposition: SemanticDisposition
    decision_reason: SemanticDecisionReason
    fallback_reason: SemanticFallbackReason | None
    provider: str | None = None
    model: str | None = None
    confidence: float | None = None
    latency_ms: float | None = None
    input_usage: int | None = None
    output_usage: int | None = None
    evidence_ref: str | None = None
    authoritative_for_action: bool = False

    def __post_init__(self) -> None:
        if self.authoritative_for_action:
            raise SemanticAdmissionError("semantic telemetry can never be authoritative")


@dataclass(frozen=True)
class SemanticAdmissionResult:
    decision: SemanticDecision
    telemetry: SemanticAdmissionTelemetry


class SemanticProductionAdmission:
    """Single-call fail-closed semantic production boundary.

    There is deliberately no retry loop.  TIMEOUT and TRANSPORT are treated as
    ambiguous outcomes and fall back immediately; callers may not infer that a
    provider did or did not receive the request.
    """

    def __init__(
        self,
        provider: SemanticDecisionProvider,
        policy: SemanticAdmissionPolicy | None = None,
    ) -> None:
        if not isinstance(policy, (SemanticAdmissionPolicy, type(None))):
            raise SemanticAdmissionError("policy must be SemanticAdmissionPolicy")
        self._provider = provider
        self._policy = policy or SemanticAdmissionPolicy.off()

    @property
    def policy(self) -> SemanticAdmissionPolicy:
        return self._policy

    def rollback_off(self) -> None:
        """Kill switch: local admission only; no task/claim state is migrated."""
        self._policy = SemanticAdmissionPolicy.off()

    @staticmethod
    def _request_with_admission(
        request: SemanticDecisionRequest, admission: FamilyAdmission
    ) -> SemanticDecisionRequest:
        if request.primitive is SemanticPrimitive.NOUL:
            if admission.review_band is None:
                raise SemanticAdmissionError("NOUL admission requires review_band")
            return replace(
                request,
                min_confidence=None,
                decision_threshold=0.5,
                review_band=admission.review_band,
            )
        if admission.min_confidence is None:
            raise SemanticAdmissionError("non-NOUL admission requires min_confidence")
        return replace(request, min_confidence=admission.min_confidence)

    @staticmethod
    def _fallback_reason(decision: SemanticDecision) -> SemanticFallbackReason | None:
        evidence = decision.evidence
        if evidence is not None and evidence.error is not None:
            kind = evidence.error.kind
            if kind is SemanticEvidenceErrorKind.AUTH:
                return SemanticFallbackReason.PROVIDER_AUTH
            if kind is SemanticEvidenceErrorKind.RATE_LIMIT:
                return SemanticFallbackReason.PROVIDER_RATE_LIMIT
            if kind is SemanticEvidenceErrorKind.OVERLOAD:
                return SemanticFallbackReason.PROVIDER_OVERLOAD
            if kind is SemanticEvidenceErrorKind.SCHEMA:
                return SemanticFallbackReason.PROVIDER_SCHEMA
            if kind in {SemanticEvidenceErrorKind.TIMEOUT, SemanticEvidenceErrorKind.TRANSPORT}:
                return SemanticFallbackReason.AMBIGUOUS_TRANSPORT
            return SemanticFallbackReason.PROVIDER_UNKNOWN
        if decision.disposition is SemanticDisposition.ESCALATE:
            return SemanticFallbackReason.POLICY_ESCALATION
        return None

    @staticmethod
    def _telemetry(
        decision: SemanticDecision,
        admission: FamilyAdmission,
        fallback_reason: SemanticFallbackReason | None,
    ) -> SemanticAdmissionTelemetry:
        evidence = decision.evidence
        return SemanticAdmissionTelemetry(
            family=decision.family,
            mode=decision.mode,
            disposition=decision.disposition,
            decision_reason=decision.reason,
            fallback_reason=fallback_reason,
            provider=None if evidence is None else evidence.provider,
            model=None if evidence is None else evidence.model,
            confidence=None if evidence is None else evidence.confidence,
            latency_ms=None if evidence is None else evidence.latency_ms,
            input_usage=None if evidence is None else evidence.input_usage,
            output_usage=None if evidence is None else evidence.output_usage,
            evidence_ref=admission.evidence_ref or None,
            authoritative_for_action=False,
        )

    def evaluate(self, request: SemanticDecisionRequest) -> SemanticAdmissionResult:
        if not isinstance(request, SemanticDecisionRequest):
            raise SemanticDecisionContractError("request must be a SemanticDecisionRequest")
        admission = self._policy.admission_for(request.family)
        if admission.mode is SemanticDecisionMode.OFF:
            # OFF must not call the provider.  Use a harmless local evidence value
            # only to satisfy the pure evaluator signature; OFF never observes it.
            decision = SemanticDecision(
                request_id=request.request_id,
                family=request.family,
                primitive=request.primitive,
                mode=SemanticDecisionMode.OFF,
                risk=request.risk,
                disposition=SemanticDisposition.BYPASS,
                reason=SemanticDecisionReason.MODE_OFF,
                evidence=None,
            )
            telemetry = self._telemetry(
                decision, admission, SemanticFallbackReason.MODE_OFF
            )
            return SemanticAdmissionResult(decision, telemetry)

        admitted_request = self._request_with_admission(request, admission)
        evidence = self._provider.evaluate(admitted_request)
        decision = evaluate_semantic_decision(
            admitted_request, evidence, admission.mode
        )
        fallback = self._fallback_reason(decision)
        return SemanticAdmissionResult(
            decision,
            self._telemetry(decision, admission, fallback),
        )
