"""WO-P1-502 JEV-2A provider-neutral semantic decision core.

This module owns exactly one pure decision family: normalizing a semantic
request/evidence pair and mapping it onto bounded advisory dispositions
(``BYPASS`` / ``OBSERVE`` / ``ADVISE`` / ``ESCALATE``) under the JEV
modes ``OFF`` / ``SHADOW`` / ``ADVISORY``.

It reuses the JEV-1 benchmark vocabulary instead of inventing a second
policy system:

- decision families, question primitives (``choice`` / ``score`` / ``noul``),
  risk levels, confidence/probability and review-band semantics mirror
  ``scripts/jev_shadow_benchmark.py`` and ``scripts/jev_typesafe_contract.py``;
- only the five benchmark-proven families are Jev-eligible;
  ``review_severity`` stays frontier-only;
- malformed, non-finite, out-of-range, mismatched or provider-error evidence
  always escalates; it is never silently repaired;
- SHADOW observes valid evidence and never advises;
- ADVISORY advises only when the family is eligible, the evidence is valid,
  confidence/threshold requirements are satisfied and the explicit risk
  policy permits advising at the request's risk level.

Boundaries:

- deterministic and I/O-free: no filesystem, network, environment, secret,
  process, or clock access happens here;
- no TypeSafe/Jev transport, no provider registry, scheduler, task database
  or claim state (JEV-1 scripts and existing authority seams own those);
- no A-FastTask/A-Faster routing mutation;
- no output grants claim, mutation, review, merge, completion or SSoT
  authority: evidence is structurally ``authoritative_for_action=False``
  and the disposition vocabulary cannot express authority;
- ``FakeSemanticDecisionProvider`` exists for tests only; production
  providers implement ``SemanticDecisionProvider`` elsewhere under their
  own gates.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable

_STATE_MAX_KEYS = 32
_STATE_MAX_DEPTH = 4
_STATE_MAX_ITEMS = 256
_STATE_MAX_STRING = 4096
_STATE_MAX_KEY = 64
_TEXT_MAX = 128
_DETAIL_MAX = 512
_OPTION_MAX = 255
_PROBABILITY_SUM_TOLERANCE = 1e-6

_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_SECRET_PATTERNS = (
    re.compile(r"apikey_[A-Za-z0-9]{16,}", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]{16,}", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]{16,}", re.IGNORECASE),
    re.compile(
        r"(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|secret)"
        r"\s*[:=]\s*[A-Za-z0-9+/=_-]{12,}",
        re.IGNORECASE,
    ),
)


class SemanticDecisionContractError(ValueError):
    """Raised when a request or evidence envelope violates the module contract."""


class SemanticDecisionFamily(str, Enum):
    TASK_CLASSIFICATION = "task_classification"
    SKILL_SUGGESTION = "skill_suggestion"
    FAILURE_CLASSIFICATION = "failure_classification"
    EVIDENCE_RELEVANCE = "evidence_relevance"
    ESCALATION_DECISION = "escalation_decision"
    REVIEW_SEVERITY = "review_severity"


class SemanticPrimitive(str, Enum):
    CHOICE = "choice"
    SCORE = "score"
    NOUL = "noul"


class SemanticDecisionMode(str, Enum):
    OFF = "OFF"
    SHADOW = "SHADOW"
    ADVISORY = "ADVISORY"


class SemanticDisposition(str, Enum):
    BYPASS = "BYPASS"
    OBSERVE = "OBSERVE"
    ADVISE = "ADVISE"
    ESCALATE = "ESCALATE"


class SemanticRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SemanticEvidenceErrorKind(str, Enum):
    TRANSPORT = "TRANSPORT"
    TIMEOUT = "TIMEOUT"
    RATE_LIMIT = "RATE_LIMIT"
    OVERLOAD = "OVERLOAD"
    AUTH = "AUTH"
    SCHEMA = "SCHEMA"
    RETRY_EXHAUSTED = "RETRY_EXHAUSTED"
    UNKNOWN = "UNKNOWN"


class SemanticDecisionReason(str, Enum):
    MODE_OFF = "MODE_OFF"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    EVIDENCE_MALFORMED = "EVIDENCE_MALFORMED"
    EVIDENCE_MEASUREMENT_INVALID = "EVIDENCE_MEASUREMENT_INVALID"
    EVIDENCE_PRIMITIVE_MISMATCH = "EVIDENCE_PRIMITIVE_MISMATCH"
    EVIDENCE_ANSWER_INVALID = "EVIDENCE_ANSWER_INVALID"
    EVIDENCE_CONFIDENCE_MISSING = "EVIDENCE_CONFIDENCE_MISSING"
    EVIDENCE_CONFIDENCE_INVALID = "EVIDENCE_CONFIDENCE_INVALID"
    EVIDENCE_PROBABILITIES_INVALID = "EVIDENCE_PROBABILITIES_INVALID"
    EVIDENCE_NOUL_FORBIDDEN_FIELD = "EVIDENCE_NOUL_FORBIDDEN_FIELD"
    SHADOW_OBSERVE = "SHADOW_OBSERVE"
    FAMILY_FRONTIER_ONLY = "FAMILY_FRONTIER_ONLY"
    CONFIDENCE_BELOW_THRESHOLD = "CONFIDENCE_BELOW_THRESHOLD"
    REVIEW_BAND_UNCERTAIN = "REVIEW_BAND_UNCERTAIN"
    RISK_ESCALATION_REQUIRED = "RISK_ESCALATION_REQUIRED"
    ADVISORY_GATES_SATISFIED = "ADVISORY_GATES_SATISFIED"


JEV_ELIGIBLE_FAMILIES = frozenset(
    {
        SemanticDecisionFamily.TASK_CLASSIFICATION,
        SemanticDecisionFamily.SKILL_SUGGESTION,
        SemanticDecisionFamily.FAILURE_CLASSIFICATION,
        SemanticDecisionFamily.EVIDENCE_RELEVANCE,
        SemanticDecisionFamily.ESCALATION_DECISION,
    }
)
FRONTIER_ONLY_FAMILIES = frozenset({SemanticDecisionFamily.REVIEW_SEVERITY})

_RISK_RANK = {
    SemanticRiskLevel.LOW: 0,
    SemanticRiskLevel.MEDIUM: 1,
    SemanticRiskLevel.HIGH: 2,
}


def _text(value: object, field: str, *, max_length: int = _TEXT_MAX) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SemanticDecisionContractError(f"{field} must be a non-empty string")
    if len(value) > max_length:
        raise SemanticDecisionContractError(
            f"{field} must be at most {max_length} characters"
        )
    if _CONTROL_RE.search(value):
        raise SemanticDecisionContractError(f"{field} must not contain control characters")
    return value


def _coerce_enum(value: object, enum_cls: type, field: str):
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except ValueError:
        allowed = sorted(member.value for member in enum_cls)
        raise SemanticDecisionContractError(
            f"{field} must be one of {allowed}"
        ) from None


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SemanticDecisionContractError(f"{field} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise SemanticDecisionContractError(f"{field} must be a finite number")
    return number


def _optional_probability(value: object, field: str) -> float | None:
    if value is None:
        return None
    number = _finite_number(value, field)
    if not 0.0 <= number <= 1.0:
        raise SemanticDecisionContractError(f"{field} must be between 0 and 1")
    return number


def _has_secret_shape(value: str) -> bool:
    return any(pattern.search(value) for pattern in _SECRET_PATTERNS)


def _freeze_state_value(value: object, field: str, depth: int, budget: list[int]) -> Any:
    if budget[0] <= 0:
        raise SemanticDecisionContractError(
            f"{field} exceeds the bounded state item budget"
        )
    if isinstance(value, str):
        if len(value) > _STATE_MAX_STRING:
            raise SemanticDecisionContractError(
                f"{field} strings must be at most {_STATE_MAX_STRING} characters"
            )
        if _CONTROL_RE.search(value):
            raise SemanticDecisionContractError(
                f"{field} must not contain control characters"
            )
        if _has_secret_shape(value):
            raise SemanticDecisionContractError(
                f"{field} contains a secret-shaped value"
            )
        budget[0] -= 1
        return value
    if isinstance(value, bool) or value is None:
        budget[0] -= 1
        return value
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            raise SemanticDecisionContractError(f"{field} must contain finite numbers")
        budget[0] -= 1
        return value
    if isinstance(value, Mapping):
        if depth >= _STATE_MAX_DEPTH:
            raise SemanticDecisionContractError(
                f"{field} exceeds the bounded state depth"
            )
        return _freeze_state_mapping(value, field, depth + 1, budget)
    if isinstance(value, (list, tuple)):
        if depth >= _STATE_MAX_DEPTH:
            raise SemanticDecisionContractError(
                f"{field} exceeds the bounded state depth"
            )
        frozen = tuple(
            _freeze_state_value(item, f"{field}[{index}]", depth + 1, budget)
            for index, item in enumerate(value)
        )
        return frozen
    raise SemanticDecisionContractError(
        f"{field} must contain only text, numbers, booleans, null, arrays or objects"
    )


def _freeze_state_mapping(
    mapping: Mapping[object, object], field: str, depth: int, budget: list[int]
) -> Mapping[str, Any]:
    if len(mapping) > _STATE_MAX_KEYS:
        raise SemanticDecisionContractError(
            f"{field} must contain at most {_STATE_MAX_KEYS} keys"
        )
    frozen: dict[str, Any] = {}
    for key, value in mapping.items():
        if not isinstance(key, str) or not key:
            raise SemanticDecisionContractError(f"{field} keys must be non-empty text")
        if len(key) > _STATE_MAX_KEY:
            raise SemanticDecisionContractError(
                f"{field} keys must be at most {_STATE_MAX_KEY} characters"
            )
        if _CONTROL_RE.search(key) or _has_secret_shape(key):
            raise SemanticDecisionContractError(f"{field} keys must be sanitized text")
        frozen[key] = _freeze_state_value(value, f"{field}[{key!r}]", depth, budget)
    return MappingProxyType(frozen)


@dataclass(frozen=True)
class SemanticProviderError:
    """Typed provider error carried inside a semantic evidence envelope."""

    kind: SemanticEvidenceErrorKind
    detail: str

    def __post_init__(self) -> None:
        kind = _coerce_enum(self.kind, SemanticEvidenceErrorKind, "error.kind")
        object.__setattr__(self, "kind", kind)
        detail = _text(self.detail, "error.detail", max_length=_DETAIL_MAX)
        object.__setattr__(self, "detail", detail)


@dataclass(frozen=True)
class SemanticRiskPolicy:
    """Explicit advisory risk ceiling; risk above it escalates to the integrator.

    The default ceiling is MEDIUM: high-risk decisions return to the existing
    authority (frontier/human) even when every evidence gate passes, matching
    the shadow-first posture of the JEV roadmap. The ceiling is an explicit
    input so a future admitted policy can widen it on evidence, never by
    default.
    """

    max_advise_risk: SemanticRiskLevel = SemanticRiskLevel.MEDIUM

    def __post_init__(self) -> None:
        risk = _coerce_enum(self.max_advise_risk, SemanticRiskLevel, "risk_policy.max_advise_risk")
        object.__setattr__(self, "max_advise_risk", risk)

    def permits_advise(self, risk: SemanticRiskLevel) -> bool:
        return _RISK_RANK[risk] <= _RISK_RANK[self.max_advise_risk]


DEFAULT_SEMANTIC_RISK_POLICY = SemanticRiskPolicy()


@dataclass(frozen=True)
class SemanticDecisionRequest:
    """Immutable normalized semantic decision request.

    ``state`` must be sanitized bounded JSON-shaped data; it is validated and
    frozen read-only here so no later mutation can change what a provider or
    the policy observed.
    """

    request_id: str
    family: SemanticDecisionFamily
    primitive: SemanticPrimitive
    state: Mapping[str, Any]
    risk: SemanticRiskLevel
    options: tuple[str, ...] = ()
    score_levels: int | None = None
    min_confidence: float | None = None
    decision_threshold: float | None = None
    review_band: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        request_id = _text(self.request_id, "request_id")
        object.__setattr__(self, "request_id", request_id)
        family = _coerce_enum(self.family, SemanticDecisionFamily, "family")
        object.__setattr__(self, "family", family)
        primitive = _coerce_enum(self.primitive, SemanticPrimitive, "primitive")
        object.__setattr__(self, "primitive", primitive)
        risk = _coerce_enum(self.risk, SemanticRiskLevel, "risk")
        object.__setattr__(self, "risk", risk)

        if not isinstance(self.state, Mapping):
            raise SemanticDecisionContractError("state must be an object")
        frozen_state = _freeze_state_mapping(
            self.state, "state", depth=1, budget=[_STATE_MAX_ITEMS]
        )
        object.__setattr__(self, "state", frozen_state)

        options = self._normalize_options()
        object.__setattr__(self, "options", options)
        self._validate_metadata()

    def _normalize_options(self) -> tuple[str, ...]:
        raw = self.options
        if isinstance(raw, str) or not isinstance(raw, (list, tuple)):
            if raw == () or raw is None:
                return ()
            raise SemanticDecisionContractError(
                "options must be a sequence of strings"
            )
        options = tuple(
            _text(item, "options", max_length=_TEXT_MAX) for item in raw
        )
        if len(set(options)) != len(options):
            raise SemanticDecisionContractError("options must be unique")
        return options

    def _validate_metadata(self) -> None:
        primitive = self.primitive

        if primitive is SemanticPrimitive.CHOICE:
            if not 2 <= len(self.options) <= _OPTION_MAX:
                raise SemanticDecisionContractError(
                    "choice options must contain between 2 and "
                    f"{_OPTION_MAX} declared options"
                )
        else:
            if self.options:
                raise SemanticDecisionContractError(
                    f"{primitive.value} requests must not declare options"
                )

        if primitive is SemanticPrimitive.SCORE:
            levels = self.score_levels
            if (
                isinstance(levels, bool)
                or not isinstance(levels, int)
                or not 2 <= levels <= 10
            ):
                raise SemanticDecisionContractError(
                    "score_levels must be an integer from 2 to 10"
                )
        elif self.score_levels is not None:
            raise SemanticDecisionContractError(
                f"{primitive.value} requests must not declare score_levels"
            )

        _optional_probability(self.min_confidence, "min_confidence")
        if primitive is SemanticPrimitive.NOUL and self.min_confidence is not None:
            raise SemanticDecisionContractError(
                "noul requests must not carry confidence semantics"
            )

        if primitive is SemanticPrimitive.NOUL:
            _optional_probability(self.decision_threshold, "decision_threshold")
        elif self.decision_threshold is not None:
            raise SemanticDecisionContractError(
                f"{primitive.value} requests must not declare decision_threshold"
            )

        if self.review_band is not None:
            if isinstance(self.review_band, str) or not isinstance(
                self.review_band, (list, tuple)
            ):
                raise SemanticDecisionContractError(
                    "review_band must be a [lower, upper] pair"
                )
            if len(self.review_band) != 2:
                raise SemanticDecisionContractError(
                    "review_band must be a [lower, upper] pair"
                )
            lower = _optional_probability(self.review_band[0], "review_band[0]")
            upper = _optional_probability(self.review_band[1], "review_band[1]")
            assert lower is not None and upper is not None
            if lower > upper:
                raise SemanticDecisionContractError(
                    "review_band lower must be <= upper"
                )
            object.__setattr__(self, "review_band", (lower, upper))
            if primitive is not SemanticPrimitive.NOUL:
                raise SemanticDecisionContractError(
                    f"{primitive.value} requests must not declare review_band"
                )


@dataclass(frozen=True)
class SemanticEvidence:
    """Immutable normalized provider-neutral semantic evidence envelope.

    ``authoritative_for_action`` is structurally False: constructing an
    envelope with any other value fails closed, so no provider output can
    claim action authority through this type.
    """

    provider: str
    model: str
    primitive: SemanticPrimitive
    answer: Any = None
    confidence: float | None = None
    probabilities: Mapping[str, float] | None = None
    input_usage: int = 0
    output_usage: int = 0
    latency_ms: float = 0.0
    error: SemanticProviderError | None = None
    authoritative_for_action: bool = False

    def __post_init__(self) -> None:
        if self.authoritative_for_action is not False:
            raise SemanticDecisionContractError(
                "semantic evidence is never authoritative_for_action"
            )
        _text(self.provider, "provider")
        _text(self.model, "model")
        primitive = _coerce_enum(self.primitive, SemanticPrimitive, "evidence.primitive")
        object.__setattr__(self, "primitive", primitive)

        for field in ("input_usage", "output_usage"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise SemanticDecisionContractError(
                    f"{field} must be a non-negative integer"
                )

        latency = self.latency_ms
        if isinstance(latency, bool) or not isinstance(latency, (int, float)):
            raise SemanticDecisionContractError(
                "latency_ms must be a non-negative finite number"
            )
        latency = float(latency)
        if not math.isfinite(latency) or latency < 0.0:
            raise SemanticDecisionContractError(
                "latency_ms must be a non-negative finite number"
            )
        object.__setattr__(self, "latency_ms", latency)

        if self.error is not None and not isinstance(self.error, SemanticProviderError):
            raise SemanticDecisionContractError(
                "error must be a SemanticProviderError"
            )

        probabilities = self.probabilities
        if probabilities is not None:
            if not isinstance(probabilities, Mapping):
                raise SemanticDecisionContractError(
                    "probabilities must be an object"
                )
            object.__setattr__(
                self, "probabilities", MappingProxyType(dict(probabilities))
            )


@dataclass(frozen=True)
class SemanticDecision:
    """Advisory disposition for one request/evidence pair under one mode.

    This type carries no authority field: a disposition is advisory
    observability, never claim, mutation, review, merge, completion or SSoT
    authority.
    """

    request_id: str
    family: SemanticDecisionFamily
    primitive: SemanticPrimitive
    mode: SemanticDecisionMode
    risk: SemanticRiskLevel
    disposition: SemanticDisposition
    reason: SemanticDecisionReason
    evidence: SemanticEvidence | None


@runtime_checkable
class SemanticDecisionProvider(Protocol):
    """Provider-neutral semantic decision transport seam.

    Implementations perform I/O and own their own failure handling; they must
    return a normalized :class:`SemanticEvidence` envelope and never raise
    provider-specific exceptions across this boundary.
    """

    def evaluate(self, request: SemanticDecisionRequest) -> SemanticEvidence:
        ...


class FakeSemanticDecisionProvider:
    """Deterministic scripted provider for tests only.

    Returns the scripted evidence for a known ``request_id``; every unknown
    request receives a deterministic typed SCHEMA error envelope so the
    fail-closed escalation path can be exercised without any I/O.
    """

    def __init__(
        self,
        scripted: Mapping[str, SemanticEvidence],
        default: SemanticEvidence | None = None,
    ) -> None:
        self._scripted = dict(scripted)
        self._default = default

    def evaluate(self, request: SemanticDecisionRequest) -> SemanticEvidence:
        evidence = self._scripted.get(request.request_id)
        if evidence is not None:
            return evidence
        if self._default is not None:
            return self._default
        return SemanticEvidence(
            provider="fake-semantic",
            model="fake-deterministic",
            primitive=request.primitive,
            answer=None,
            error=SemanticProviderError(
                kind=SemanticEvidenceErrorKind.SCHEMA,
                detail=f"no scripted evidence for request {request.request_id!r}",
            ),
        )


def _validate_probabilities(
    probabilities: Mapping[str, float] | None,
    *,
    expected_keys: tuple[str, ...],
) -> bool:
    if probabilities is None:
        return True
    if set(probabilities) != set(expected_keys):
        return False
    total = 0.0
    for key in expected_keys:
        value = probabilities[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        number = float(value)
        if not math.isfinite(number) or not 0.0 <= number <= 1.0:
            return False
        total += number
    return math.isclose(total, 1.0, abs_tol=_PROBABILITY_SUM_TOLERANCE)


def _validate_confidence(evidence: SemanticEvidence) -> SemanticDecisionReason | None:
    if evidence.confidence is None:
        return SemanticDecisionReason.EVIDENCE_CONFIDENCE_MISSING
    confidence = evidence.confidence
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return SemanticDecisionReason.EVIDENCE_CONFIDENCE_INVALID
    number = float(confidence)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        return SemanticDecisionReason.EVIDENCE_CONFIDENCE_INVALID
    return None


def _as_finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def _structural_evidence_reason(
    request: SemanticDecisionRequest, evidence: SemanticEvidence
) -> SemanticDecisionReason | None:
    """Return the structural (mode-independent) invalidity reason, if any."""

    if evidence.primitive is not request.primitive:
        return SemanticDecisionReason.EVIDENCE_PRIMITIVE_MISMATCH

    if request.primitive is SemanticPrimitive.CHOICE:
        if not isinstance(evidence.answer, str) or evidence.answer not in request.options:
            return SemanticDecisionReason.EVIDENCE_ANSWER_INVALID
        reason = _validate_confidence(evidence)
        if reason is not None:
            return reason
        if not _validate_probabilities(evidence.probabilities, expected_keys=request.options):
            return SemanticDecisionReason.EVIDENCE_PROBABILITIES_INVALID
        return None

    if request.primitive is SemanticPrimitive.SCORE:
        answer = _as_finite_number(evidence.answer)
        levels = request.score_levels
        assert levels is not None
        if answer is None or not 0.0 <= answer <= float(levels - 1):
            return SemanticDecisionReason.EVIDENCE_ANSWER_INVALID
        reason = _validate_confidence(evidence)
        if reason is not None:
            return reason
        keys = tuple(str(index) for index in range(levels))
        if not _validate_probabilities(evidence.probabilities, expected_keys=keys):
            return SemanticDecisionReason.EVIDENCE_PROBABILITIES_INVALID
        return None

    answer = _as_finite_number(evidence.answer)
    if answer is None or not 0.0 <= answer <= 1.0:
        return SemanticDecisionReason.EVIDENCE_ANSWER_INVALID
    if evidence.confidence is not None or evidence.probabilities is not None:
        return SemanticDecisionReason.EVIDENCE_NOUL_FORBIDDEN_FIELD
    return None


def evaluate_semantic_decision(
    request: SemanticDecisionRequest,
    evidence: SemanticEvidence,
    mode: SemanticDecisionMode,
    risk_policy: SemanticRiskPolicy = DEFAULT_SEMANTIC_RISK_POLICY,
) -> SemanticDecision:
    """Map one request/evidence pair onto a bounded advisory disposition.

    Deterministic, pure, and fail-closed: any evidence defect escalates in
    every non-OFF mode, and OFF bypasses without observing evidence at all.
    """

    if not isinstance(request, SemanticDecisionRequest):
        raise SemanticDecisionContractError(
            "request must be a SemanticDecisionRequest"
        )
    mode = _coerce_enum(mode, SemanticDecisionMode, "mode")
    if not isinstance(risk_policy, SemanticRiskPolicy):
        raise SemanticDecisionContractError(
            "risk_policy must be a SemanticRiskPolicy"
        )

    def decision(
        disposition: SemanticDisposition,
        reason: SemanticDecisionReason,
        carried_evidence: SemanticEvidence | None,
    ) -> SemanticDecision:
        return SemanticDecision(
            request_id=request.request_id,
            family=request.family,
            primitive=request.primitive,
            mode=mode,
            risk=request.risk,
            disposition=disposition,
            reason=reason,
            evidence=carried_evidence,
        )

    if mode is SemanticDecisionMode.OFF:
        return decision(
            SemanticDisposition.BYPASS,
            SemanticDecisionReason.MODE_OFF,
            evidence if isinstance(evidence, SemanticEvidence) else None,
        )

    if not isinstance(evidence, SemanticEvidence):
        return decision(
            SemanticDisposition.ESCALATE,
            SemanticDecisionReason.EVIDENCE_MALFORMED,
            None,
        )

    if evidence.error is not None:
        return decision(
            SemanticDisposition.ESCALATE,
            SemanticDecisionReason.PROVIDER_ERROR,
            evidence,
        )

    latency = _as_finite_number(evidence.latency_ms)
    if latency is None or latency < 0.0:
        return decision(
            SemanticDisposition.ESCALATE,
            SemanticDecisionReason.EVIDENCE_MEASUREMENT_INVALID,
            evidence,
        )
    for usage_field in (evidence.input_usage, evidence.output_usage):
        if isinstance(usage_field, bool) or not isinstance(usage_field, int) or usage_field < 0:
            return decision(
                SemanticDisposition.ESCALATE,
                SemanticDecisionReason.EVIDENCE_MEASUREMENT_INVALID,
                evidence,
            )

    structural_reason = _structural_evidence_reason(request, evidence)
    if structural_reason is not None:
        return decision(SemanticDisposition.ESCALATE, structural_reason, evidence)

    if mode is SemanticDecisionMode.SHADOW:
        return decision(
            SemanticDisposition.OBSERVE,
            SemanticDecisionReason.SHADOW_OBSERVE,
            evidence,
        )

    if request.family in FRONTIER_ONLY_FAMILIES:
        return decision(
            SemanticDisposition.ESCALATE,
            SemanticDecisionReason.FAMILY_FRONTIER_ONLY,
            evidence,
        )

    if request.primitive is SemanticPrimitive.NOUL:
        if request.review_band is not None:
            lower, upper = request.review_band
            answer = _as_finite_number(evidence.answer)
            assert answer is not None
            if lower <= answer <= upper:
                return decision(
                    SemanticDisposition.ESCALATE,
                    SemanticDecisionReason.REVIEW_BAND_UNCERTAIN,
                    evidence,
                )
    else:
        min_confidence = request.min_confidence
        confidence = evidence.confidence
        assert confidence is not None
        if min_confidence is not None and float(confidence) < float(min_confidence):
            return decision(
                SemanticDisposition.ESCALATE,
                SemanticDecisionReason.CONFIDENCE_BELOW_THRESHOLD,
                evidence,
            )

    if not risk_policy.permits_advise(request.risk):
        return decision(
            SemanticDisposition.ESCALATE,
            SemanticDecisionReason.RISK_ESCALATION_REQUIRED,
            evidence,
        )

    return decision(
        SemanticDisposition.ADVISE,
        SemanticDecisionReason.ADVISORY_GATES_SATISFIED,
        evidence,
    )
