"""WO-P1-752 — pure route/usage telemetry baseline projection tests.

The projection composes per-attempt evidence from injected inputs only. It
owns no clock, network, or store; absent evidence stays typed-unavailable and
is never fabricated into zero.
"""

from __future__ import annotations

import pytest

from a_conductor.provider_fallback_policy import (
    REASON_ELIGIBLE_NOT_SELECTED,
    REASON_QUOTA_EXHAUSTED,
    REASON_SELECTED,
    CandidateEvaluation,
    ProviderFallbackSelectionResult,
    SelectionOutcome,
    SelectionStage,
)
from a_conductor.semantic_admission import (
    SemanticAdmissionTelemetry,
    SemanticDecisionFamily,
    SemanticDecisionMode,
    SemanticDecisionReason,
    SemanticDisposition,
    SemanticFallbackReason,
)
from a_conductor.route_telemetry_projection import (
    COST_REASON_CURRENCY_ABSENT,
    COST_REASON_PRICING_ABSENT,
    COST_REASON_USAGE_ABSENT,
    COST_STATE_KNOWN,
    COST_STATE_UNKNOWN,
    EVIDENCE_STATE_AVAILABLE,
    EVIDENCE_STATE_UNAVAILABLE,
    LATENCY_CLOCK_MONOTONIC,
    RECEIPT_STATUS_ACCEPTED,
    RECEIPT_STATUS_QUARANTINED,
    SELECTION_ABSENT_REASON,
    TELEMETRY_ABSENT_REASON,
    TOKEN_USAGE_ABSENT_REASON,
    USAGE_STATE_MEASURED,
    WALL_STAMP_CLOCK,
    RouteAttemptInput,
    RouteUnitPricing,
    project_route_telemetry,
)


def make_semantic(**overrides) -> SemanticAdmissionTelemetry:
    data = dict(
        family=SemanticDecisionFamily.TASK_CLASSIFICATION,
        mode=SemanticDecisionMode.OFF,
        disposition=SemanticDisposition.BYPASS,
        decision_reason=SemanticDecisionReason.MODE_OFF,
        fallback_reason=SemanticFallbackReason.MODE_OFF,
        input_usage=None,
        output_usage=None,
        latency_ms=None,
    )
    data.update(overrides)
    return SemanticAdmissionTelemetry(**data)


def make_evaluation(
    provider_id="provider-a",
    model_id="model-a",
    stage=SelectionStage.AUTHORIZED,
    eligible=True,
    reason_code=REASON_ELIGIBLE_NOT_SELECTED,
    generation=7,
) -> CandidateEvaluation:
    return CandidateEvaluation(
        provider_id=provider_id,
        model_id=model_id,
        expected_configuration_generation=generation,
        stage=stage,
        eligible=eligible,
        reason_code=reason_code,
    )


def make_selection(
    *evaluations,
    outcome=SelectionOutcome.SELECTED,
    provider_id="provider-a",
    model_id="model-a",
    reason_code=REASON_SELECTED,
    generation=7,
) -> ProviderFallbackSelectionResult:
    selected = outcome is SelectionOutcome.SELECTED
    return ProviderFallbackSelectionResult(
        outcome=outcome,
        provider_id=provider_id if selected else None,
        model_id=model_id if selected else None,
        expected_configuration_generation=generation if selected else None,
        requested_effort="DEFAULT",
        reason_code=reason_code if selected else outcome.value,
        evaluations=tuple(evaluations),
    )


def test_wo752_duplicate_identity_dedup_with_duplicate_of_pointer() -> None:
    evidence = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                receipt_status=RECEIPT_STATUS_QUARANTINED,
            ),
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                receipt_status=RECEIPT_STATUS_ACCEPTED,
            ),
        )
    )
    assert evidence.attempts[0].duplicate_of is None
    assert evidence.attempts[1].duplicate_of == 0
    assert evidence.attempted_attempt_count == 1
    assert evidence.duplicate_row_count == 1
    # the retried row's ACCEPTED receipt is honored once, never double-counted
    assert evidence.accepted_attempt_count == 1
    assert evidence.attempts[0].accepted is False
    assert evidence.attempts[1].accepted is True


def test_wo752_fallback_retry_chain_attempted_vs_accepted() -> None:
    evidence = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                receipt_status=RECEIPT_STATUS_QUARANTINED,
                semantic=make_semantic(
                    disposition=SemanticDisposition.ESCALATE,
                    decision_reason=SemanticDecisionReason.PROVIDER_ERROR,
                    fallback_reason=SemanticFallbackReason.PROVIDER_RATE_LIMIT,
                ),
            ),
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-2",
                receipt_status=RECEIPT_STATUS_ACCEPTED,
                semantic=make_semantic(),
            ),
        )
    )
    assert evidence.attempted_attempt_count == 2
    assert evidence.accepted_attempt_count == 1
    assert evidence.duplicate_row_count == 0
    assert evidence.attempts[0].fallback_reason == "PROVIDER_RATE_LIMIT"
    assert evidence.attempts[0].disposition == "ESCALATE"
    assert evidence.attempts[0].accepted is False
    assert evidence.attempts[1].accepted is True


def test_wo752_absent_usage_pricing_currency_is_unknown_never_zero() -> None:
    # no semantic telemetry at all
    bare = project_route_telemetry(
        attempts=(RouteAttemptInput(execution_id="exec-1", attempt_id="att-1"),)
    ).attempts[0]
    assert bare.cost.state == COST_STATE_UNKNOWN
    assert bare.cost.reason == COST_REASON_USAGE_ABSENT
    assert bare.cost.amount is None
    assert bare.cost.input_usage is None
    assert bare.cost.output_usage is None
    assert 0 not in (bare.cost.input_usage, bare.cost.output_usage)

    # usage measured, pricing absent
    usage_only = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                semantic=make_semantic(input_usage=10, output_usage=4),
            ),
        )
    ).attempts[0]
    assert usage_only.cost.state == COST_STATE_UNKNOWN
    assert usage_only.cost.reason == COST_REASON_PRICING_ABSENT

    # usage + pricing, currency absent
    no_currency = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                semantic=make_semantic(input_usage=10, output_usage=4),
                pricing=RouteUnitPricing(
                    input_cost_per_thousand_tokens=0.5,
                    output_cost_per_thousand_tokens=1.5,
                ),
            ),
        )
    ).attempts[0]
    assert no_currency.cost.state == COST_STATE_UNKNOWN
    assert no_currency.cost.reason == COST_REASON_CURRENCY_ABSENT

    # everything present -> KNOWN, never silently zero
    known = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                semantic=make_semantic(input_usage=10, output_usage=4),
                pricing=RouteUnitPricing(
                    input_cost_per_thousand_tokens=0.5,
                    output_cost_per_thousand_tokens=1.5,
                ),
                currency="USD",
            ),
        )
    ).attempts[0]
    assert known.cost.state == COST_STATE_KNOWN
    assert known.cost.reason == "COST_KNOWN"
    assert known.cost.amount == pytest.approx(10 / 1000 * 0.5 + 4 / 1000 * 1.5)
    assert known.cost.currency == "USD"
    assert known.cost.to_dict()["state"] == "KNOWN"


def test_wo752_wall_vs_monotonic_labeled_distinctly() -> None:
    evidence = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                semantic=make_semantic(latency_ms=12.0, input_usage=3, output_usage=1),
                started_at_wall="2026-11-13T10:00:00Z",
                finished_at_wall="2026-11-13T10:00:05Z",
            ),
            RouteAttemptInput(execution_id="exec-1", attempt_id="att-2"),
        )
    )
    first = evidence.attempts[0]
    assert first.latency_ms == pytest.approx(12.0)
    assert first.latency_clock == "MONOTONIC"
    assert first.started_at_wall == "2026-11-13T10:00:00Z"
    assert first.finished_at_wall == "2026-11-13T10:00:05Z"
    assert first.wall_stamp_clock == WALL_STAMP_CLOCK == "WALL"

    second = evidence.attempts[1]
    assert second.latency_ms is None
    assert second.latency_clock == "UNAVAILABLE"
    assert second.started_at_wall is None
    assert second.finished_at_wall is None
    assert second.wall_stamp_clock == "UNAVAILABLE"
    assert first.latency_clock != first.wall_stamp_clock


def test_wo752_telemetry_absent_degrades_only_its_fields() -> None:
    evidence = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                selection=make_selection(make_evaluation()),
                receipt_status=RECEIPT_STATUS_ACCEPTED,
            ),
        )
    )
    row = evidence.attempts[0]
    assert row.telemetry_state == EVIDENCE_STATE_UNAVAILABLE
    assert row.telemetry_unavailable_reason == TELEMETRY_ABSENT_REASON
    assert row.usage_state == EVIDENCE_STATE_UNAVAILABLE
    assert row.usage_unavailable_reason == TELEMETRY_ABSENT_REASON
    assert row.latency_clock == "UNAVAILABLE"
    # everything else still projects; the object is still returned
    assert row.selection.state == EVIDENCE_STATE_AVAILABLE
    assert row.selection.reason_code == REASON_SELECTED
    assert row.receipt_state == EVIDENCE_STATE_AVAILABLE
    assert row.accepted is True
    assert row.cost.state == COST_STATE_UNKNOWN
    assert row.cost.reason == COST_REASON_USAGE_ABSENT


def test_wo752_semantic_present_but_usage_absent_is_typed_unavailable() -> None:
    row = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                semantic=make_semantic(),
            ),
        )
    ).attempts[0]
    assert row.telemetry_state == EVIDENCE_STATE_AVAILABLE
    assert row.telemetry_unavailable_reason is None
    assert row.usage_state == EVIDENCE_STATE_UNAVAILABLE
    assert row.usage_unavailable_reason == TOKEN_USAGE_ABSENT_REASON
    assert row.input_usage is None
    assert row.output_usage is None


def test_wo752_zero_usage_stays_distinguishable_from_absent() -> None:
    zero = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                semantic=make_semantic(input_usage=0, output_usage=0),
                pricing=RouteUnitPricing(
                    input_cost_per_thousand_tokens=0.5,
                    output_cost_per_thousand_tokens=1.5,
                ),
                currency="USD",
            ),
        )
    ).attempts[0]
    assert zero.usage_state == USAGE_STATE_MEASURED
    assert zero.usage_unavailable_reason is None
    assert zero.input_usage == 0
    assert zero.output_usage == 0
    assert zero.cost.state == COST_STATE_KNOWN
    assert zero.cost.amount == pytest.approx(0.0)


def test_wo752_correlation_conflict_fails_closed() -> None:
    with pytest.raises(ValueError, match="correlation identity mismatch"):
        project_route_telemetry(
            attempts=(
                RouteAttemptInput(
                    execution_id="exec-1",
                    attempt_id="att-1",
                    semantic=make_semantic(
                        execution_id="exec-9",
                        attempt_id="att-1",
                    ),
                ),
            )
        )
    with pytest.raises(ValueError, match="correlation identity mismatch"):
        project_route_telemetry(
            attempts=(
                RouteAttemptInput(
                    execution_id="exec-1",
                    attempt_id="att-1",
                    request_id="req-1",
                    semantic=make_semantic(request_id="req-2"),
                ),
            )
        )


def test_wo752_matching_correlation_passes_through() -> None:
    row = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                request_id="req-1",
                semantic=make_semantic(
                    execution_id="exec-1",
                    attempt_id="att-1",
                    request_id="req-1",
                ),
            ),
        )
    ).attempts[0]
    assert (row.execution_id, row.attempt_id, row.request_id) == (
        "exec-1",
        "att-1",
        "req-1",
    )


def test_wo752_selection_summary_reason_and_shortlist() -> None:
    selection = make_selection(
        make_evaluation(reason_code=REASON_SELECTED),
        make_evaluation(
            provider_id="provider-b",
            model_id="model-b",
            eligible=False,
            reason_code=REASON_QUOTA_EXHAUSTED,
        ),
    )
    row = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                selection=selection,
            ),
        )
    ).attempts[0]
    assert row.selection.state == EVIDENCE_STATE_AVAILABLE
    assert row.selection.unavailable_reason is None
    assert row.selection.outcome == "SELECTED"
    assert row.selection.reason_code == REASON_SELECTED
    assert row.selection.selected_provider_id == "provider-a"
    assert row.selection.selected_model_id == "model-a"
    assert row.selection.expected_configuration_generation == 7
    assert len(row.selection.shortlist) == 2
    assert row.selection.shortlist[0].provider_id == "provider-a"
    assert row.selection.shortlist[0].stage == "AUTHORIZED"
    assert row.selection.shortlist[0].eligible is True
    assert row.selection.shortlist[1].reason_code == REASON_QUOTA_EXHAUSTED


def test_wo752_selection_absent_is_typed_unavailable() -> None:
    row = project_route_telemetry(
        attempts=(RouteAttemptInput(execution_id="exec-1", attempt_id="att-1"),)
    ).attempts[0]
    assert row.selection.state == EVIDENCE_STATE_UNAVAILABLE
    assert row.selection.unavailable_reason == SELECTION_ABSENT_REASON
    assert row.selection.reason_code is None
    assert row.selection.shortlist == ()
    assert row.selection.selected_provider_id is None


def test_wo752_empty_attempts_returns_object_with_zero_counts() -> None:
    evidence = project_route_telemetry(attempts=())
    assert evidence.attempts == ()
    assert evidence.attempted_attempt_count == 0
    assert evidence.accepted_attempt_count == 0
    assert evidence.duplicate_row_count == 0


def test_wo752_invalid_inputs_fail_closed() -> None:
    with pytest.raises(ValueError):
        RouteAttemptInput(execution_id="  ", attempt_id="att-1")
    with pytest.raises(ValueError):
        RouteAttemptInput(execution_id="exec-1", attempt_id="")
    with pytest.raises(ValueError):
        RouteAttemptInput(execution_id="exec-1", attempt_id="att-1", receipt_status="RUNNING")
    with pytest.raises(ValueError):
        RouteAttemptInput(execution_id="exec-1", attempt_id="att-1", currency="  ")
    with pytest.raises(ValueError):
        RouteAttemptInput(
            execution_id="exec-1",
            attempt_id="att-1",
            pricing=RouteUnitPricing(
                input_cost_per_thousand_tokens=-1.0,
                output_cost_per_thousand_tokens=1.5,
            ),
        )
    with pytest.raises(ValueError):
        RouteAttemptInput(
            execution_id="exec-1",
            attempt_id="att-1",
            selection=("not-a-selection",),
        )
    with pytest.raises(ValueError):
        RouteAttemptInput(
            execution_id="exec-1",
            attempt_id="att-1",
            semantic=("not-a-telemetry",),
        )
    with pytest.raises(ValueError):
        project_route_telemetry(attempts=("not-a-row",))
    with pytest.raises(ValueError):
        project_route_telemetry(attempts=None)
