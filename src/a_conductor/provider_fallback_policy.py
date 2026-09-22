"""BWA-1B1 deterministic pre-attempt provider selection policy (WO-P1-458).

This module owns exactly one pure decision: given an explicitly authorized,
explicitly ordered candidate set supplied by the caller, select at most one
provider/model before any admission or launch attempt, and hand identity plus
typed evidence to the existing execution authority.

It reuses existing authority vocabulary instead of inventing a router:

- ``evaluate_provider_policy`` for task trust/egress authorization;
- ``evaluate_provider_service_authorization`` for SERVICE_AUTHORIZED;
- ``is_provider_ready`` for freshness/generation readiness evidence;
- ``derive_quota_tier`` (WO252) for conservative quota tiers;
- WO128 observability truth: absent evidence is never fabricated into
  history, and this policy never claims ADMITTED.

Boundaries:

- the caller supplies the explicit ordered candidate set; it is never
  auto-widened, re-ranked, or remembered across calls;
- stages distinguish NOT_CAPABLE / CAPABLE / READY / AUTHORIZED / ADMITTED,
  and ADMITTED exists in the vocabulary only — this policy never emits it;
- quota EXHAUSTED or UNKNOWN is ineligible; UNKNOWN is never promoted
  optimistically;
- the cost ceiling / paid-substitution policy is enforced from explicit pure
  inputs only;
- selection is deterministic: the first eligible candidate in explicit order
  wins;
- no I/O, store, network, subprocess, credential resolution, launch, retry,
  or lifecycle mutation happens here, and there is no re-selection after
  launch;
- Issue #340 remains owner of global provider routing; Issue #215 NEXT_READY
  and WO433 runtime-activation authority are unchanged.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum

from .provider_configuration import (
    EFFORT_LEVELS,
    ModelCostClass,
    ProviderConfiguration,
    ProviderEndpointConfig,
    ProviderModelConfiguration,
    ProviderObservation,
    QuotaSnapshot,
    is_provider_ready,
)
from .provider_cost_preference import (
    QuotaPreferenceTier,
    derive_quota_tier,
)
from .provider_policy import (
    ProviderPolicyTaskSecurity,
    evaluate_provider_policy,
)
from .provider_service_authorization import (
    ProviderServiceAuthorizationRecord,
    ServiceIntegrationMode,
    evaluate_provider_service_authorization,
)

_MAX_GENERATION = (1 << 63) - 1
_MAX_AGE_DEFAULT = 300
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")

REASON_SELECTED = "SELECTED_FIRST_ELIGIBLE_IN_EXPLICIT_ORDER"
REASON_ELIGIBLE_NOT_SELECTED = "ELIGIBLE_NOT_FIRST_IN_EXPLICIT_ORDER"
REASON_MODEL_NOT_IN_PROVIDER_CONFIGURATION = "MODEL_NOT_IN_PROVIDER_CONFIGURATION"
REASON_MODEL_CONFIGURATION_MISMATCH = "MODEL_CONFIGURATION_MISMATCH"
REASON_EFFORT_UNSUPPORTED = "EFFORT_UNSUPPORTED"
REASON_PROVIDER_DISABLED = "PROVIDER_DISABLED"
REASON_READINESS_EVIDENCE_MISSING = "READINESS_EVIDENCE_MISSING"
REASON_READINESS_GENERATION_MISSING = "READINESS_GENERATION_MISSING"
REASON_READINESS_GENERATION_STALE = "READINESS_GENERATION_STALE"
REASON_READINESS_OBSERVATION_STALE = "READINESS_OBSERVATION_STALE"
REASON_QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
REASON_QUOTA_UNKNOWN = "QUOTA_UNKNOWN"
REASON_COST_CLASS_UNKNOWN = "COST_CLASS_UNKNOWN"
REASON_PAID_SUBSTITUTION_NOT_AUTHORIZED = "PAID_SUBSTITUTION_NOT_AUTHORIZED"
REASON_COST_CEILING_EXCEEDED = "COST_CEILING_EXCEEDED"

_COST_CLASS_RANK = {
    ModelCostClass.FREE: 0,
    ModelCostClass.LOW_COST: 1,
    ModelCostClass.STANDARD: 2,
    ModelCostClass.PREMIUM: 3,
}


class SelectionStage(str, Enum):
    """Stage vocabulary distinguishing capability/readiness/authorization.

    ``ADMITTED`` is part of the shared vocabulary for consumers of this
    policy, but this module never emits it: admission belongs to the existing
    execution authority seams.
    """

    NOT_CAPABLE = "NOT_CAPABLE"
    CAPABLE = "CAPABLE"
    READY = "READY"
    AUTHORIZED = "AUTHORIZED"
    ADMITTED = "ADMITTED"


class SelectionOutcome(str, Enum):
    SELECTED = "SELECTED"
    NO_CANDIDATE_EMPTY_SET = "NO_CANDIDATE_EMPTY_SET"
    NO_CANDIDATE_ALL_INELIGIBLE = "NO_CANDIDATE_ALL_INELIGIBLE"


def _text(value: object, field: str, *, max_length: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    cleaned = value.strip()
    if not cleaned or len(cleaned) > max_length or _CONTROL_RE.search(cleaned):
        raise ValueError(f"{field} is invalid")
    return cleaned


def _generation(value: object) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= _MAX_GENERATION
    ):
        raise ValueError("expected_configuration_generation must be positive")
    return value


def _aware_utc(value: object, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{field} must be timezone-aware")
    offset = value.utcoffset()
    if offset is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class ProviderSelectionCostPolicy:
    """Explicit pure cost/paid-substitution policy.

    ``allow_paid_substitution`` gates any non-FREE, non-UNKNOWN cost class;
    ``max_cost_class`` is a hard ceiling; UNKNOWN cost fails closed unless
    explicitly allowed and is never treated as FREE.
    """

    allow_paid_substitution: bool = False
    max_cost_class: ModelCostClass = ModelCostClass.PREMIUM
    allow_unknown_cost_class: bool = False

    def __post_init__(self) -> None:
        for name in ("allow_paid_substitution", "allow_unknown_cost_class"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be bool")
        ceiling = self.max_cost_class
        if not isinstance(ceiling, ModelCostClass):
            try:
                ceiling = ModelCostClass(ceiling)
            except (TypeError, ValueError) as exc:
                raise ValueError("max_cost_class is invalid") from exc
        if ceiling is ModelCostClass.UNKNOWN:
            raise ValueError("max_cost_class must not be UNKNOWN")
        object.__setattr__(self, "max_cost_class", ceiling)


@dataclass(frozen=True, slots=True)
class ServiceAuthorizationContext:
    """Explicit service-authorization request context for one selection."""

    service_identity: str
    terms_identity: str
    requested_mode: ServiceIntegrationMode

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "service_identity",
            _text(self.service_identity, "service_identity", max_length=48),
        )
        object.__setattr__(
            self,
            "terms_identity",
            _text(self.terms_identity, "terms_identity", max_length=64),
        )
        if not isinstance(self.requested_mode, ServiceIntegrationMode):
            raise ValueError("requested_mode must be ServiceIntegrationMode")


@dataclass(frozen=True, slots=True)
class ProviderFallbackCandidate:
    """One explicitly supplied pre-attempt candidate with its own evidence.

    Absent evidence (``observation``, ``service_authorization``, ``quota`` of
    ``None``) is typed missing evidence, not authorization: the selection
    fails closed with a typed reason instead of raising or guessing.
    """

    provider_id: str
    model: ProviderModelConfiguration
    profile: ProviderConfiguration
    endpoint: ProviderEndpointConfig | None
    observation: ProviderObservation | None
    expected_configuration_generation: int
    service_authorization: ProviderServiceAuthorizationRecord | None = None
    quota: QuotaSnapshot | None = None

    def __post_init__(self) -> None:
        provider_id = _text(self.provider_id, "provider_id", max_length=128)
        if not isinstance(self.model, ProviderModelConfiguration):
            raise ValueError("model must be ProviderModelConfiguration")
        if not isinstance(self.profile, ProviderConfiguration):
            raise ValueError("profile must be ProviderConfiguration")
        if self.profile.provider_id != provider_id:
            raise ValueError("profile provider identity mismatch")
        if self.endpoint is not None and not isinstance(
            self.endpoint, ProviderEndpointConfig
        ):
            raise ValueError("endpoint must be ProviderEndpointConfig or None")
        if self.observation is not None:
            if not isinstance(self.observation, ProviderObservation):
                raise ValueError("observation must be ProviderObservation or None")
            if self.observation.provider_id != provider_id:
                raise ValueError("observation provider identity mismatch")
        generation = _generation(self.expected_configuration_generation)
        if self.service_authorization is not None:
            record = self.service_authorization
            if not isinstance(record, ProviderServiceAuthorizationRecord):
                raise ValueError(
                    "service_authorization must be "
                    "ProviderServiceAuthorizationRecord or None"
                )
            if record.provider_id != provider_id:
                raise ValueError("service authorization provider identity mismatch")
        if self.quota is not None and not isinstance(self.quota, QuotaSnapshot):
            raise ValueError("quota must be QuotaSnapshot or None")
        object.__setattr__(self, "provider_id", provider_id)
        object.__setattr__(self, "expected_configuration_generation", generation)


@dataclass(frozen=True, slots=True)
class CandidateEvaluation:
    """Typed per-candidate stage/reason evidence; never ADMITTED here."""

    provider_id: str
    model_id: str
    expected_configuration_generation: int
    stage: SelectionStage
    eligible: bool
    reason_code: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "provider_id", _text(self.provider_id, "provider_id", max_length=128)
        )
        object.__setattr__(
            self, "model_id", _text(self.model_id, "model_id", max_length=128)
        )
        object.__setattr__(
            self,
            "expected_configuration_generation",
            _generation(self.expected_configuration_generation),
        )
        if not isinstance(self.stage, SelectionStage):
            raise ValueError("stage must be SelectionStage")
        if not isinstance(self.eligible, bool):
            raise ValueError("eligible must be bool")
        object.__setattr__(
            self, "reason_code", _text(self.reason_code, "reason_code", max_length=256)
        )


@dataclass(frozen=True, slots=True)
class ProviderFallbackSelectionResult:
    """Deterministic pre-attempt selection result.

    ``provider_id``/``model_id``/``expected_configuration_generation`` are
    populated only when one candidate was selected; otherwise a typed
    ``NO_CANDIDATE_*`` outcome carries the refusal. ``to_json`` is canonical
    and byte-stable for equal inputs.
    """

    outcome: SelectionOutcome
    provider_id: str | None
    model_id: str | None
    expected_configuration_generation: int | None
    requested_effort: str
    reason_code: str
    evaluations: tuple[CandidateEvaluation, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, SelectionOutcome):
            raise ValueError("outcome must be SelectionOutcome")
        for name in ("provider_id", "model_id"):
            if getattr(self, name) is not None:
                object.__setattr__(
                    self, name, _text(getattr(self, name), name, max_length=128)
                )
        if self.expected_configuration_generation is not None:
            object.__setattr__(
                self,
                "expected_configuration_generation",
                _generation(self.expected_configuration_generation),
            )
        if not isinstance(self.requested_effort, str) or (
            self.requested_effort not in EFFORT_LEVELS
        ):
            raise ValueError("requested_effort is invalid")
        object.__setattr__(
            self, "reason_code", _text(self.reason_code, "reason_code", max_length=256)
        )
        if not isinstance(self.evaluations, tuple):
            raise ValueError("evaluations must be a tuple of CandidateEvaluation")
        for evaluation in self.evaluations:
            if not isinstance(evaluation, CandidateEvaluation):
                raise ValueError("evaluations must contain CandidateEvaluation")

    def to_dict(self) -> dict[str, object]:
        return {
            "evaluations": [
                {
                    "eligible": evaluation.eligible,
                    "expected_configuration_generation": (
                        evaluation.expected_configuration_generation
                    ),
                    "model_id": evaluation.model_id,
                    "provider_id": evaluation.provider_id,
                    "reason_code": evaluation.reason_code,
                    "stage": evaluation.stage.value,
                }
                for evaluation in self.evaluations
            ],
            "expected_configuration_generation": self.expected_configuration_generation,
            "model_id": self.model_id,
            "outcome": self.outcome.value,
            "provider_id": self.provider_id,
            "reason_code": self.reason_code,
            "requested_effort": self.requested_effort,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )

    @property
    def result_sha256(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()


def _evaluate_candidate(
    candidate: ProviderFallbackCandidate,
    *,
    task_security: ProviderPolicyTaskSecurity,
    requested_effort: str,
    cost_policy: ProviderSelectionCostPolicy,
    service: ServiceAuthorizationContext,
    now: datetime,
    max_observation_age_seconds: int,
) -> CandidateEvaluation:
    def evaluation(
        stage: SelectionStage, eligible: bool, reason_code: str
    ) -> CandidateEvaluation:
        return CandidateEvaluation(
            provider_id=candidate.provider_id,
            model_id=candidate.model.model_id,
            expected_configuration_generation=candidate.expected_configuration_generation,
            stage=stage,
            eligible=eligible,
            reason_code=reason_code,
        )

    # CAPABLE: the claimed model must be the provider's canonical model and
    # must support the requested effort.
    profile_model = next(
        (
            entry
            for entry in candidate.profile.models
            if entry.model_id == candidate.model.model_id
        ),
        None,
    )
    if profile_model is None:
        return evaluation(
            SelectionStage.NOT_CAPABLE,
            False,
            REASON_MODEL_NOT_IN_PROVIDER_CONFIGURATION,
        )
    if profile_model != candidate.model:
        return evaluation(
            SelectionStage.NOT_CAPABLE, False, REASON_MODEL_CONFIGURATION_MISMATCH
        )
    if (
        requested_effort != "DEFAULT"
        and requested_effort not in profile_model.supported_effort_levels
    ):
        return evaluation(
            SelectionStage.NOT_CAPABLE, False, REASON_EFFORT_UNSUPPORTED
        )

    # READY: fresh readiness evidence bound to the expected generation.
    if not candidate.profile.enabled:
        return evaluation(SelectionStage.CAPABLE, False, REASON_PROVIDER_DISABLED)
    observation = candidate.observation
    if observation is None:
        return evaluation(
            SelectionStage.CAPABLE, False, REASON_READINESS_EVIDENCE_MISSING
        )
    if observation.configuration_generation is None:
        return evaluation(
            SelectionStage.CAPABLE, False, REASON_READINESS_GENERATION_MISSING
        )
    if observation.configuration_generation != candidate.expected_configuration_generation:
        return evaluation(
            SelectionStage.CAPABLE, False, REASON_READINESS_GENERATION_STALE
        )
    if not is_provider_ready(
        candidate.profile,
        observation,
        now=now,
        max_age_seconds=max_observation_age_seconds,
        expected_generation=candidate.expected_configuration_generation,
    ):
        return evaluation(
            SelectionStage.CAPABLE, False, REASON_READINESS_OBSERVATION_STALE
        )

    # AUTHORIZED: task trust/egress policy, then service authorization.
    policy_decision = evaluate_provider_policy(
        candidate.profile, candidate.endpoint, task_security
    )
    if not policy_decision.allowed:
        return evaluation(
            SelectionStage.READY,
            False,
            f"PROVIDER_POLICY_DENIED:{policy_decision.reason_code}",
        )
    service_decision = evaluate_provider_service_authorization(
        candidate.service_authorization,
        provider_id=candidate.provider_id,
        service_identity=service.service_identity,
        requested_mode=service.requested_mode,
        terms_identity=service.terms_identity,
        expected_configuration_generation=candidate.expected_configuration_generation,
        now=now,
    )
    if not service_decision.allowed:
        return evaluation(
            SelectionStage.READY,
            False,
            f"SERVICE_AUTHORIZATION_DENIED:{service_decision.reason_code}",
        )

    # Quota eligibility: EXHAUSTED is ineligible and UNKNOWN is never
    # promoted optimistically.
    quota_tier = derive_quota_tier(candidate.quota)
    if quota_tier is QuotaPreferenceTier.EXHAUSTED:
        return evaluation(SelectionStage.AUTHORIZED, False, REASON_QUOTA_EXHAUSTED)
    if quota_tier is QuotaPreferenceTier.UNKNOWN:
        return evaluation(SelectionStage.AUTHORIZED, False, REASON_QUOTA_UNKNOWN)

    # Cost eligibility from explicit pure inputs only.
    cost_class = candidate.model.cost_class
    if cost_class is ModelCostClass.UNKNOWN and not cost_policy.allow_unknown_cost_class:
        return evaluation(
            SelectionStage.AUTHORIZED, False, REASON_COST_CLASS_UNKNOWN
        )
    if (
        cost_class is not ModelCostClass.UNKNOWN
        and cost_class is not ModelCostClass.FREE
        and not cost_policy.allow_paid_substitution
    ):
        return evaluation(
            SelectionStage.AUTHORIZED,
            False,
            REASON_PAID_SUBSTITUTION_NOT_AUTHORIZED,
        )
    if (
        cost_class is not ModelCostClass.UNKNOWN
        and _COST_CLASS_RANK[cost_class] > _COST_CLASS_RANK[cost_policy.max_cost_class]
    ):
        return evaluation(
            SelectionStage.AUTHORIZED, False, REASON_COST_CEILING_EXCEEDED
        )

    return evaluation(
        SelectionStage.AUTHORIZED, True, REASON_ELIGIBLE_NOT_SELECTED
    )


def select_pre_attempt_provider(
    candidates: tuple[ProviderFallbackCandidate, ...],
    *,
    task_security: ProviderPolicyTaskSecurity,
    requested_effort: str,
    cost_policy: ProviderSelectionCostPolicy,
    service: ServiceAuthorizationContext,
    now: datetime,
    max_observation_age_seconds: int = _MAX_AGE_DEFAULT,
) -> ProviderFallbackSelectionResult:
    """Select at most one candidate from the explicit ordered set.

    Deterministic and pure: same inputs produce an equal, byte-stable result.
    The first fully eligible candidate in the caller's explicit order wins;
    nothing outside the supplied set is ever considered, no state is retained
    across calls, and this function never admits, launches, retries, or
    resolves secrets.
    """

    if not isinstance(task_security, ProviderPolicyTaskSecurity):
        raise ValueError("task_security must be ProviderPolicyTaskSecurity")
    if not isinstance(requested_effort, str) or requested_effort not in EFFORT_LEVELS:
        raise ValueError("requested_effort is invalid")
    if not isinstance(cost_policy, ProviderSelectionCostPolicy):
        raise ValueError("cost_policy must be ProviderSelectionCostPolicy")
    if not isinstance(service, ServiceAuthorizationContext):
        raise ValueError("service must be ServiceAuthorizationContext")
    resolved_now = _aware_utc(now, "now")
    if (
        isinstance(max_observation_age_seconds, bool)
        or not isinstance(max_observation_age_seconds, int)
        or max_observation_age_seconds < 0
    ):
        raise ValueError("max_observation_age_seconds must be a non-negative int")
    if isinstance(candidates, (str, bytes)) or not isinstance(candidates, (tuple, list)):
        raise ValueError("candidates must be a tuple of ProviderFallbackCandidate")
    resolved_candidates = tuple(candidates)
    for item in resolved_candidates:
        if not isinstance(item, ProviderFallbackCandidate):
            raise ValueError("candidates must contain ProviderFallbackCandidate")

    evaluations = tuple(
        _evaluate_candidate(
            candidate,
            task_security=task_security,
            requested_effort=requested_effort,
            cost_policy=cost_policy,
            service=service,
            now=resolved_now,
            max_observation_age_seconds=max_observation_age_seconds,
        )
        for candidate in resolved_candidates
    )

    if not evaluations:
        return ProviderFallbackSelectionResult(
            outcome=SelectionOutcome.NO_CANDIDATE_EMPTY_SET,
            provider_id=None,
            model_id=None,
            expected_configuration_generation=None,
            requested_effort=requested_effort,
            reason_code=SelectionOutcome.NO_CANDIDATE_EMPTY_SET.value,
            evaluations=evaluations,
        )

    selected_index = next(
        (index for index, item in enumerate(evaluations) if item.eligible), None
    )
    if selected_index is None:
        return ProviderFallbackSelectionResult(
            outcome=SelectionOutcome.NO_CANDIDATE_ALL_INELIGIBLE,
            provider_id=None,
            model_id=None,
            expected_configuration_generation=None,
            requested_effort=requested_effort,
            reason_code=SelectionOutcome.NO_CANDIDATE_ALL_INELIGIBLE.value,
            evaluations=evaluations,
        )

    selected = evaluations[selected_index]
    evaluations = tuple(
        replace(item, reason_code=REASON_SELECTED) if index == selected_index else item
        for index, item in enumerate(evaluations)
    )
    return ProviderFallbackSelectionResult(
        outcome=SelectionOutcome.SELECTED,
        provider_id=selected.provider_id,
        model_id=selected.model_id,
        expected_configuration_generation=selected.expected_configuration_generation,
        requested_effort=requested_effort,
        reason_code=REASON_SELECTED,
        evaluations=evaluations,
    )
