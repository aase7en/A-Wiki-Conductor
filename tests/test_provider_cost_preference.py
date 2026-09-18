from __future__ import annotations

from datetime import datetime, timezone

import pytest

from a_conductor.provider_configuration import (
    ModelCostClass,
    ProviderModelConfiguration,
    QuotaSnapshot,
)
from a_conductor.provider_cost_preference import (
    LOW_QUOTA_REMAINING_RATIO,
    PreferenceEligibility,
    ProviderPreferenceCandidate,
    ProviderPreferenceReason,
    QuotaPreferenceTier,
    derive_quota_tier,
    rank_provider_candidates,
)


NOW = datetime(2026, 9, 19, 2, 0, tzinfo=timezone.utc)


def quota(
    *,
    limit: int | float | None = 100,
    used: int | float | None = 20,
    remaining: int | float | None = 80,
    reset_at: datetime | None = NOW,
    reset_in_seconds: int | None = 3600,
    window_type: str = "5h",
) -> QuotaSnapshot:
    return QuotaSnapshot(
        window_type=window_type,
        limit=limit,
        used=used,
        remaining=remaining,
        reset_at=reset_at,
        reset_in_seconds=reset_in_seconds,
        unit="tokens",
    )


def candidate(
    provider_id: str,
    *,
    model_id: str | None = None,
    cost: ModelCostClass | str = ModelCostClass.STANDARD,
    efforts: tuple[str, ...] = ("LOW", "HIGH", "MAX"),
    quota_snapshot: QuotaSnapshot | None = None,
) -> ProviderPreferenceCandidate:
    return ProviderPreferenceCandidate(
        provider_id=provider_id,
        model=ProviderModelConfiguration(
            model_id=model_id or f"{provider_id}-model",
            display_name=model_id or f"{provider_id} model",
            cost_class=cost,
            supported_effort_levels=efforts,
        ),
        quota=quota_snapshot,
    )


@pytest.mark.parametrize(
    ("snapshot", "expected"),
    [
        (None, QuotaPreferenceTier.UNKNOWN),
        (quota(limit=None), QuotaPreferenceTier.UNKNOWN),
        (quota(used=None), QuotaPreferenceTier.UNKNOWN),
        (quota(remaining=None), QuotaPreferenceTier.UNKNOWN),
        (quota(reset_at=None), QuotaPreferenceTier.UNKNOWN),
        (quota(reset_in_seconds=None), QuotaPreferenceTier.UNKNOWN),
        (quota(window_type="daily"), QuotaPreferenceTier.UNKNOWN),
        (quota(limit=float("nan")), QuotaPreferenceTier.UNKNOWN),
        (quota(limit=float("inf")), QuotaPreferenceTier.UNKNOWN),
        (quota(limit=100, used=101, remaining=0), QuotaPreferenceTier.UNKNOWN),
        (quota(limit=100, used=10, remaining=80), QuotaPreferenceTier.UNKNOWN),
        (quota(limit=100, used=100, remaining=0), QuotaPreferenceTier.EXHAUSTED),
        (quota(limit=100, used=80, remaining=20), QuotaPreferenceTier.LOW),
        (quota(limit=100, used=79, remaining=21), QuotaPreferenceTier.AVAILABLE),
        (quota(window_type="ROLLING_5H"), QuotaPreferenceTier.AVAILABLE),
    ],
)
def test_quota_tier_is_conservative_and_deterministic(
    snapshot: QuotaSnapshot | None,
    expected: QuotaPreferenceTier,
) -> None:
    assert derive_quota_tier(snapshot) is expected
    assert derive_quota_tier(snapshot) is expected


def test_low_quota_threshold_is_explicit_and_stable() -> None:
    assert LOW_QUOTA_REMAINING_RATIO == 0.20


def test_bool_quota_evidence_is_unknown_not_available() -> None:
    snapshot = quota()
    object.__setattr__(snapshot, "remaining", True)
    assert derive_quota_tier(snapshot) is QuotaPreferenceTier.UNKNOWN


def test_unknown_cost_is_never_treated_as_free() -> None:
    free = candidate("provider-free", cost=ModelCostClass.FREE, quota_snapshot=quota())
    unknown = candidate("provider-unknown", cost=ModelCostClass.UNKNOWN, quota_snapshot=quota())
    ranked = rank_provider_candidates((unknown, free))
    assert [item.candidate.provider_id for item in ranked] == [
        "provider-free",
        "provider-unknown",
    ]
    assert ProviderPreferenceReason.COST_UNKNOWN in ranked[1].reasons


def test_unknown_quota_is_never_treated_as_available() -> None:
    known = candidate("provider-known", quota_snapshot=quota())
    unknown = candidate("provider-unknown", quota_snapshot=None)
    ranked = rank_provider_candidates((unknown, known))
    assert ranked[0].candidate.provider_id == "provider-known"
    assert ranked[0].quota_tier is QuotaPreferenceTier.AVAILABLE
    assert ranked[1].quota_tier is QuotaPreferenceTier.UNKNOWN


def test_exhausted_is_never_preferred_over_available() -> None:
    exhausted = candidate(
        "provider-a",
        cost=ModelCostClass.FREE,
        quota_snapshot=quota(used=100, remaining=0),
    )
    available = candidate(
        "provider-z",
        cost=ModelCostClass.PREMIUM,
        quota_snapshot=quota(),
    )
    ranked = rank_provider_candidates((exhausted, available))
    assert ranked[0].candidate.provider_id == "provider-z"
    assert ranked[0].quota_tier is QuotaPreferenceTier.AVAILABLE


def test_lower_declared_cost_breaks_otherwise_comparable_tie() -> None:
    premium = candidate(
        "provider-a",
        cost=ModelCostClass.PREMIUM,
        quota_snapshot=quota(),
    )
    low = candidate(
        "provider-z",
        cost=ModelCostClass.LOW_COST,
        quota_snapshot=quota(),
    )
    ranked = rank_provider_candidates((premium, low))
    assert ranked[0].candidate.provider_id == "provider-z"
    assert ranked[0].cost_class is ModelCostClass.LOW_COST


def test_explicit_unsupported_effort_is_preference_ineligible() -> None:
    unsupported = candidate(
        "provider-free",
        cost=ModelCostClass.FREE,
        efforts=("LOW",),
        quota_snapshot=quota(),
    )
    supported = candidate(
        "provider-premium",
        cost=ModelCostClass.PREMIUM,
        efforts=("HIGH",),
        quota_snapshot=quota(),
    )
    ranked = rank_provider_candidates(
        (unsupported, supported),
        requested_effort="HIGH",
    )
    assert ranked[0].candidate.provider_id == "provider-premium"
    assert ranked[0].eligibility is PreferenceEligibility.ELIGIBLE
    assert ranked[1].eligibility is PreferenceEligibility.EFFORT_UNSUPPORTED
    assert ProviderPreferenceReason.EFFORT_UNSUPPORTED in ranked[1].reasons


def test_empty_effort_declaration_does_not_prove_explicit_support() -> None:
    item = candidate(
        "provider-empty",
        efforts=(),
        quota_snapshot=quota(),
    )
    ranked = rank_provider_candidates((item,), requested_effort="MAX")
    assert ranked[0].eligibility is PreferenceEligibility.EFFORT_UNSUPPORTED


def test_default_effort_does_not_require_nondefault_capability() -> None:
    item = candidate(
        "provider-empty",
        efforts=(),
        quota_snapshot=quota(),
    )
    ranked = rank_provider_candidates((item,), requested_effort="DEFAULT")
    assert ranked[0].eligibility is PreferenceEligibility.ELIGIBLE
    assert ProviderPreferenceReason.EFFORT_DEFAULT in ranked[0].reasons


def test_invalid_requested_effort_fails_closed() -> None:
    with pytest.raises(ValueError, match="requested_effort"):
        rank_provider_candidates(
            (candidate("provider-a", quota_snapshot=quota()),),
            requested_effort="ULTRA",
        )


def test_ranking_is_stable_and_identity_only_breaks_semantic_ties() -> None:
    a2 = candidate(
        "provider-a",
        model_id="model-2",
        quota_snapshot=quota(),
    )
    a1 = candidate(
        "provider-a",
        model_id="model-1",
        quota_snapshot=quota(),
    )
    z = candidate(
        "provider-z",
        model_id="model-0",
        quota_snapshot=quota(),
    )
    first = rank_provider_candidates((z, a2, a1))
    second = rank_provider_candidates((a1, z, a2))
    expected = [
        ("provider-a", "model-1"),
        ("provider-a", "model-2"),
        ("provider-z", "model-0"),
    ]
    assert [
        (item.candidate.provider_id, item.candidate.model.model_id)
        for item in first
    ] == expected
    assert [
        (item.candidate.provider_id, item.candidate.model.model_id)
        for item in second
    ] == expected


def test_ranking_is_pure_and_does_not_mutate_candidate_evidence() -> None:
    original = (
        candidate(
            "provider-a",
            cost=ModelCostClass.LOW_COST,
            quota_snapshot=quota(),
        ),
        candidate(
            "provider-b",
            cost=ModelCostClass.STANDARD,
            quota_snapshot=None,
        ),
    )
    snapshot = repr(original)
    ranked = rank_provider_candidates(original, requested_effort="HIGH")
    assert repr(original) == snapshot
    assert tuple(item.candidate for item in ranked) != ()
    assert original[0].model.cost_class is ModelCostClass.LOW_COST
    assert original[0].quota is not None
