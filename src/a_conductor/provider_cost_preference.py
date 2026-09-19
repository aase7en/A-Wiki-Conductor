"""Pure provider cost/quota preference evidence for WO-P1-252.

This module ranks already-supplied provider/model evidence only. It performs no
provider calls, credential access, admission, launch, failover, scheduler, lease,
job, task, or claim mutation. Ranking is advisory and never execution authority.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .provider_configuration import (
    EFFORT_LEVELS,
    ModelCostClass,
    ProviderModelConfiguration,
    QuotaSnapshot,
)


LOW_QUOTA_REMAINING_RATIO = 0.20


class QuotaPreferenceTier(str, Enum):
    AVAILABLE = "AVAILABLE"
    LOW = "LOW"
    EXHAUSTED = "EXHAUSTED"
    UNKNOWN = "UNKNOWN"


class PreferenceEligibility(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    EFFORT_UNSUPPORTED = "EFFORT_UNSUPPORTED"


class ProviderPreferenceReason(str, Enum):
    EFFORT_DEFAULT = "EFFORT_DEFAULT"
    EFFORT_SUPPORTED = "EFFORT_SUPPORTED"
    EFFORT_UNSUPPORTED = "EFFORT_UNSUPPORTED"
    QUOTA_AVAILABLE = "QUOTA_AVAILABLE"
    QUOTA_LOW = "QUOTA_LOW"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    QUOTA_UNKNOWN = "QUOTA_UNKNOWN"
    COST_DECLARED = "COST_DECLARED"
    COST_UNKNOWN = "COST_UNKNOWN"


@dataclass(frozen=True, slots=True)
class ProviderPreferenceCandidate:
    provider_id: str
    model: ProviderModelConfiguration
    quota: QuotaSnapshot | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.provider_id, str)
            or not self.provider_id.strip()
            or len(self.provider_id) > 128
        ):
            raise ValueError("provider_id is invalid")
        if not isinstance(self.model, ProviderModelConfiguration):
            raise ValueError("model must be ProviderModelConfiguration")
        if self.quota is not None and not isinstance(self.quota, QuotaSnapshot):
            raise ValueError("quota must be QuotaSnapshot or None")


@dataclass(frozen=True, slots=True)
class ProviderPreferenceResult:
    candidate: ProviderPreferenceCandidate
    requested_effort: str
    eligibility: PreferenceEligibility
    quota_tier: QuotaPreferenceTier
    cost_class: ModelCostClass
    reasons: tuple[ProviderPreferenceReason, ...]


def _finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0:
        return None
    return numeric


def _is_five_hour_window(window_type: str) -> bool:
    normalized = window_type.strip().casefold()
    return normalized in {"5h", "rolling_5h"}


def derive_quota_tier(snapshot: QuotaSnapshot | None) -> QuotaPreferenceTier:
    """Derive a conservative preference tier from a complete five-hour tuple.

    UNKNOWN is returned for missing, partial, non-finite, contradictory, or
    non-five-hour evidence. This function never promotes ambiguous evidence to
    execution authority.
    """

    if snapshot is None or not isinstance(snapshot, QuotaSnapshot):
        return QuotaPreferenceTier.UNKNOWN
    if not _is_five_hour_window(snapshot.window_type):
        return QuotaPreferenceTier.UNKNOWN

    if (
        snapshot.limit is None
        or snapshot.used is None
        or snapshot.remaining is None
        or snapshot.reset_at is None
        or snapshot.reset_in_seconds is None
    ):
        return QuotaPreferenceTier.UNKNOWN

    limit = _finite_number(snapshot.limit)
    used = _finite_number(snapshot.used)
    remaining = _finite_number(snapshot.remaining)
    if limit is None or used is None or remaining is None:
        return QuotaPreferenceTier.UNKNOWN
    if limit == 0:
        return (
            QuotaPreferenceTier.EXHAUSTED
            if used == 0 and remaining == 0
            else QuotaPreferenceTier.UNKNOWN
        )
    if used > limit or remaining > limit:
        return QuotaPreferenceTier.UNKNOWN
    if not math.isclose(
        used + remaining,
        limit,
        rel_tol=1e-6,
        abs_tol=1e-9,
    ):
        return QuotaPreferenceTier.UNKNOWN

    if not isinstance(snapshot.reset_at, datetime):
        return QuotaPreferenceTier.UNKNOWN
    if snapshot.reset_at.tzinfo is None or snapshot.reset_at.utcoffset() is None:
        return QuotaPreferenceTier.UNKNOWN
    if (
        isinstance(snapshot.reset_in_seconds, bool)
        or not isinstance(snapshot.reset_in_seconds, int)
        or snapshot.reset_in_seconds < 0
    ):
        return QuotaPreferenceTier.UNKNOWN

    if remaining <= 0:
        return QuotaPreferenceTier.EXHAUSTED
    if remaining / limit <= LOW_QUOTA_REMAINING_RATIO:
        return QuotaPreferenceTier.LOW
    return QuotaPreferenceTier.AVAILABLE


def _effort_eligibility(
    model: ProviderModelConfiguration,
    requested_effort: str,
) -> PreferenceEligibility:
    if requested_effort == "DEFAULT":
        return PreferenceEligibility.ELIGIBLE
    if requested_effort in model.supported_effort_levels:
        return PreferenceEligibility.ELIGIBLE
    return PreferenceEligibility.EFFORT_UNSUPPORTED


def _reasons(
    *,
    eligibility: PreferenceEligibility,
    quota_tier: QuotaPreferenceTier,
    cost_class: ModelCostClass,
    requested_effort: str,
) -> tuple[ProviderPreferenceReason, ...]:
    reasons: list[ProviderPreferenceReason] = []
    if eligibility is PreferenceEligibility.EFFORT_UNSUPPORTED:
        reasons.append(ProviderPreferenceReason.EFFORT_UNSUPPORTED)
    elif requested_effort == "DEFAULT":
        reasons.append(ProviderPreferenceReason.EFFORT_DEFAULT)
    else:
        reasons.append(ProviderPreferenceReason.EFFORT_SUPPORTED)

    reasons.append(
        {
            QuotaPreferenceTier.AVAILABLE: ProviderPreferenceReason.QUOTA_AVAILABLE,
            QuotaPreferenceTier.LOW: ProviderPreferenceReason.QUOTA_LOW,
            QuotaPreferenceTier.EXHAUSTED: ProviderPreferenceReason.QUOTA_EXHAUSTED,
            QuotaPreferenceTier.UNKNOWN: ProviderPreferenceReason.QUOTA_UNKNOWN,
        }[quota_tier]
    )
    reasons.append(
        ProviderPreferenceReason.COST_UNKNOWN
        if cost_class is ModelCostClass.UNKNOWN
        else ProviderPreferenceReason.COST_DECLARED
    )
    return tuple(reasons)


_ELIGIBILITY_RANK = {
    PreferenceEligibility.ELIGIBLE: 0,
    PreferenceEligibility.EFFORT_UNSUPPORTED: 1,
}
_QUOTA_RANK = {
    QuotaPreferenceTier.AVAILABLE: 0,
    QuotaPreferenceTier.LOW: 1,
    QuotaPreferenceTier.UNKNOWN: 2,
    QuotaPreferenceTier.EXHAUSTED: 3,
}
_COST_RANK = {
    ModelCostClass.FREE: 0,
    ModelCostClass.LOW_COST: 1,
    ModelCostClass.STANDARD: 2,
    ModelCostClass.PREMIUM: 3,
    ModelCostClass.UNKNOWN: 4,
}


def rank_provider_candidates(
    candidates: tuple[ProviderPreferenceCandidate, ...],
    *,
    requested_effort: str = "DEFAULT",
) -> tuple[ProviderPreferenceResult, ...]:
    """Return deterministic advisory preference ordering.

    The function is pure. It never authorizes, launches, retries, reserves,
    releases, or mutates a provider. Hard execution gates remain external.
    """

    if requested_effort not in EFFORT_LEVELS:
        raise ValueError("requested_effort is invalid")
    if not isinstance(candidates, tuple):
        candidates = tuple(candidates)

    results: list[ProviderPreferenceResult] = []
    for candidate in candidates:
        if not isinstance(candidate, ProviderPreferenceCandidate):
            raise ValueError("candidates must contain ProviderPreferenceCandidate")
        eligibility = _effort_eligibility(candidate.model, requested_effort)
        quota_tier = derive_quota_tier(candidate.quota)
        cost_class = candidate.model.cost_class
        results.append(
            ProviderPreferenceResult(
                candidate=candidate,
                requested_effort=requested_effort,
                eligibility=eligibility,
                quota_tier=quota_tier,
                cost_class=cost_class,
                reasons=_reasons(
                    eligibility=eligibility,
                    quota_tier=quota_tier,
                    cost_class=cost_class,
                    requested_effort=requested_effort,
                ),
            )
        )

    return tuple(
        sorted(
            results,
            key=lambda result: (
                _ELIGIBILITY_RANK[result.eligibility],
                _QUOTA_RANK[result.quota_tier],
                _COST_RANK[result.cost_class],
                result.candidate.provider_id,
                result.candidate.model.model_id,
            ),
        )
    )
