"""Pure route/usage telemetry baseline projection (WO-P1-752, SFU26 card 06).

This module composes per-attempt route telemetry from injected inputs only.
It performs no clock read, no network access, no store I/O, launches nothing,
resolves no credentials, and recomputes no policy. Every input is optional in
shape: missing selection evidence, missing semantic telemetry rows, missing
receipt rows, and missing usage/pricing/currency degrade to per-field typed
unavailable values and are never fabricated into zero.

Cost semantics are typed: absent pricing, currency, or token usage yields
``cost.state == UNKNOWN`` with an explicit reason code — cost is never
``0``/``None``-as-zero. Latency measured from the monotonic clock is labeled
``MONOTONIC``; durable wall-clock stamps are passed through verbatim in
``*_wall`` fields labeled ``WALL``. Attempt identity is the durable
``(execution_id, attempt_id)`` pair: duplicate/fallback/retry rows carrying
the same identity keep their evidence but are deduplicated in accounting via
an explicit ``duplicate_of`` pointer to the first row with that identity, so
attempted-vs-accepted counts never double-count.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

COST_STATE_KNOWN = "KNOWN"
COST_STATE_UNKNOWN = "UNKNOWN"
COST_REASON_KNOWN = "COST_KNOWN"
COST_REASON_USAGE_ABSENT = "USAGE_ABSENT"
COST_REASON_PRICING_ABSENT = "PRICING_ABSENT"
COST_REASON_CURRENCY_ABSENT = "CURRENCY_ABSENT"

EVIDENCE_STATE_AVAILABLE = "AVAILABLE"
EVIDENCE_STATE_UNAVAILABLE = "UNAVAILABLE"
USAGE_STATE_MEASURED = "MEASURED"

SELECTION_ABSENT_REASON = "SELECTION_RESULT_ABSENT"
TELEMETRY_ABSENT_REASON = "SEMANTIC_TELEMETRY_ABSENT"
RECEIPT_ABSENT_REASON = "RECEIPT_ROW_ABSENT"
TOKEN_USAGE_ABSENT_REASON = "TOKEN_USAGE_ABSENT"

LATENCY_CLOCK_MONOTONIC = "MONOTONIC"
LATENCY_CLOCK_UNAVAILABLE = "UNAVAILABLE"
WALL_STAMP_CLOCK = "WALL"
WALL_STAMP_UNAVAILABLE = "UNAVAILABLE"

RECEIPT_STATUS_ACCEPTED = "ACCEPTED"
RECEIPT_STATUS_QUARANTINED = "QUARANTINED"
_RECEIPT_STATUSES = frozenset({RECEIPT_STATUS_ACCEPTED, RECEIPT_STATUS_QUARANTINED})

_MAX_IDENTITY_LENGTH = 128


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-blank text")
    return value


def _require_optional_text(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_text(value, field_name)


def _require_optional_usage(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer token count or None")
    return value


def _require_optional_latency(value: Any, field_name: str) -> float | None:
    if value is None:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"{field_name} must be a finite number or None")
    return float(value)


@dataclass(frozen=True, slots=True)
class RouteUnitPricing:
    """Explicit injected unit pricing; unit is currency per 1000 tokens."""

    input_cost_per_thousand_tokens: float
    output_cost_per_thousand_tokens: float

    def __post_init__(self) -> None:
        for name in (
            "input_cost_per_thousand_tokens",
            "output_cost_per_thousand_tokens",
        ):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or value < 0
            ):
                raise ValueError(f"{name} must be a finite non-negative number")


@dataclass(frozen=True, slots=True)
class RouteTelemetryCost:
    """Typed cost evidence; absent inputs stay UNKNOWN with a reason code."""

    state: str
    reason: str
    amount: float | None = None
    currency: str | None = None
    input_usage: int | None = None
    output_usage: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "reason": self.reason,
            "amount": self.amount,
            "currency": self.currency,
        }


@dataclass(frozen=True, slots=True)
class RouteCandidateReason:
    """One shortlist candidate row with its verbatim reason code."""

    provider_id: str
    model_id: str
    stage: str
    eligible: bool
    reason_code: str
    expected_configuration_generation: int


@dataclass(frozen=True, slots=True)
class RouteSelectionSummary:
    """Selection evidence for one attempt; absent input is typed unavailable."""

    state: str
    unavailable_reason: str | None
    outcome: str | None
    reason_code: str | None
    selected_provider_id: str | None
    selected_model_id: str | None
    expected_configuration_generation: int | None
    shortlist: tuple[RouteCandidateReason, ...]


@dataclass(frozen=True, slots=True)
class RouteAttemptInput:
    """Injected per-attempt composition input (caller-owned rows only).

    ``selection`` must be selection-result-shaped (outcome, reason_code,
    provider_id, model_id, expected_configuration_generation, evaluations of
    provider/model/stage/eligible/reason_code/generation rows);
    ``semantic`` must be telemetry-shaped (input_usage/output_usage/latency_ms
    numeric-or-None, fallback_reason/disposition string-or-None, optional
    execution_id/attempt_id/request_id correlation). Wall stamps are opaque
    durable TEXT passed through verbatim; ``receipt_status`` uses the durable
    ACCEPTED/QUARANTINED vocabulary.
    """

    execution_id: str
    attempt_id: str
    request_id: str | None = None
    selection: Any = None
    semantic: Any = None
    started_at_wall: str | None = None
    finished_at_wall: str | None = None
    receipt_status: str | None = None
    pricing: RouteUnitPricing | None = None
    currency: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.execution_id, "execution_id")
        _require_text(self.attempt_id, "attempt_id")
        _require_optional_text(self.request_id, "request_id")
        _require_optional_text(self.started_at_wall, "started_at_wall")
        _require_optional_text(self.finished_at_wall, "finished_at_wall")
        _require_optional_text(self.currency, "currency")
        if self.pricing is not None and not isinstance(self.pricing, RouteUnitPricing):
            raise ValueError("pricing must be RouteUnitPricing or None")
        if self.receipt_status is not None:
            status = _enum_value(self.receipt_status)
            if status not in _RECEIPT_STATUSES:
                raise ValueError("receipt_status must be ACCEPTED or QUARANTINED")
        if self.selection is not None:
            _validate_selection_shape(self.selection)
        if self.semantic is not None:
            _validate_semantic_shape(self.semantic)


def _shape_attr(obj: Any, name: str) -> Any:
    if not hasattr(obj, name):
        raise ValueError(f"selection must expose {name}")
    return getattr(obj, name)


def _validate_selection_shape(selection: Any) -> None:
    _shape_attr(selection, "outcome")
    _shape_attr(selection, "reason_code")
    _shape_attr(selection, "provider_id")
    _shape_attr(selection, "model_id")
    _shape_attr(selection, "expected_configuration_generation")
    evaluations = _shape_attr(selection, "evaluations")
    if isinstance(evaluations, (str, bytes)) or not isinstance(
        evaluations, (tuple, list)
    ):
        raise ValueError("selection evaluations must be a tuple or list")
    for evaluation in evaluations:
        _shape_attr(evaluation, "provider_id")
        _shape_attr(evaluation, "model_id")
        _shape_attr(evaluation, "stage")
        eligible = _shape_attr(evaluation, "eligible")
        if not isinstance(eligible, bool):
            raise ValueError("selection evaluation eligible must be bool")
        _shape_attr(evaluation, "reason_code")
        _shape_attr(evaluation, "expected_configuration_generation")


def _validate_semantic_shape(semantic: Any) -> None:
    for name in ("input_usage", "output_usage"):
        value = _shape_attr(semantic, name)
        _require_optional_usage(value, name)
    _require_optional_latency(_shape_attr(semantic, "latency_ms"), "latency_ms")
    for name in ("fallback_reason", "disposition"):
        value = getattr(semantic, name, None)
        if value is not None and not isinstance(value, str):
            raise ValueError(f"semantic telemetry {name} must be text or None")


@dataclass(frozen=True, slots=True)
class RouteAttemptTelemetry:
    """Composed evidence for one attempt; every missing input stays typed."""

    execution_id: str
    attempt_id: str
    request_id: str | None
    selection: RouteSelectionSummary
    telemetry_state: str
    telemetry_unavailable_reason: str | None
    input_usage: int | None
    output_usage: int | None
    usage_state: str
    usage_unavailable_reason: str | None
    latency_ms: float | None
    latency_clock: str
    started_at_wall: str | None
    finished_at_wall: str | None
    wall_stamp_clock: str
    fallback_reason: str | None
    disposition: str | None
    receipt_state: str
    receipt_unavailable_reason: str | None
    receipt_status: str | None
    accepted: bool
    duplicate_of: int | None
    cost: RouteTelemetryCost


@dataclass(frozen=True, slots=True)
class RouteTelemetryEvidence:
    """Frozen baseline evidence set with attempted-vs-accepted accounting.

    ``attempted_attempt_count`` counts distinct (execution_id, attempt_id)
    identities; ``accepted_attempt_count`` counts identities with an ACCEPTED
    receipt; duplicate rows with a repeated identity are never double-counted
    and carry an explicit ``duplicate_of`` pointer instead.
    """

    attempts: tuple[RouteAttemptTelemetry, ...]
    attempted_attempt_count: int
    accepted_attempt_count: int
    duplicate_row_count: int


def _project_selection_summary(row: RouteAttemptInput) -> RouteSelectionSummary:
    if row.selection is None:
        return RouteSelectionSummary(
            state=EVIDENCE_STATE_UNAVAILABLE,
            unavailable_reason=SELECTION_ABSENT_REASON,
            outcome=None,
            reason_code=None,
            selected_provider_id=None,
            selected_model_id=None,
            expected_configuration_generation=None,
            shortlist=(),
        )
    selection = row.selection
    shortlist = tuple(
        RouteCandidateReason(
            provider_id=evaluation.provider_id,
            model_id=evaluation.model_id,
            stage=_enum_value(evaluation.stage),
            eligible=evaluation.eligible,
            reason_code=evaluation.reason_code,
            expected_configuration_generation=(
                evaluation.expected_configuration_generation
            ),
        )
        for evaluation in selection.evaluations
    )
    return RouteSelectionSummary(
        state=EVIDENCE_STATE_AVAILABLE,
        unavailable_reason=None,
        outcome=_enum_value(selection.outcome),
        reason_code=selection.reason_code,
        selected_provider_id=selection.provider_id,
        selected_model_id=selection.model_id,
        expected_configuration_generation=selection.expected_configuration_generation,
        shortlist=shortlist,
    )


def _project_cost(
    input_usage: int | None,
    output_usage: int | None,
    pricing: RouteUnitPricing | None,
    currency: str | None,
) -> RouteTelemetryCost:
    if input_usage is None or output_usage is None:
        return RouteTelemetryCost(
            state=COST_STATE_UNKNOWN,
            reason=COST_REASON_USAGE_ABSENT,
            input_usage=input_usage,
            output_usage=output_usage,
        )
    if pricing is None:
        return RouteTelemetryCost(
            state=COST_STATE_UNKNOWN,
            reason=COST_REASON_PRICING_ABSENT,
            input_usage=input_usage,
            output_usage=output_usage,
        )
    if currency is None:
        return RouteTelemetryCost(
            state=COST_STATE_UNKNOWN,
            reason=COST_REASON_CURRENCY_ABSENT,
            input_usage=input_usage,
            output_usage=output_usage,
        )
    amount = (
        input_usage / 1000 * pricing.input_cost_per_thousand_tokens
        + output_usage / 1000 * pricing.output_cost_per_thousand_tokens
    )
    return RouteTelemetryCost(
        state=COST_STATE_KNOWN,
        reason=COST_REASON_KNOWN,
        amount=amount,
        currency=currency,
        input_usage=input_usage,
        output_usage=output_usage,
    )


def _project_attempt(row: RouteAttemptInput, duplicate_of: int | None) -> RouteAttemptTelemetry:
    semantic = row.semantic
    if semantic is None:
        telemetry_state = EVIDENCE_STATE_UNAVAILABLE
        telemetry_unavailable_reason = TELEMETRY_ABSENT_REASON
        input_usage = None
        output_usage = None
        usage_state = EVIDENCE_STATE_UNAVAILABLE
        usage_unavailable_reason = TELEMETRY_ABSENT_REASON
        latency_ms = None
        latency_clock = LATENCY_CLOCK_UNAVAILABLE
        fallback_reason = None
        disposition = None
    else:
        telemetry_state = EVIDENCE_STATE_AVAILABLE
        telemetry_unavailable_reason = None
        input_usage = _require_optional_usage(
            semantic.input_usage, "semantic input_usage"
        )
        output_usage = _require_optional_usage(
            semantic.output_usage, "semantic output_usage"
        )
        if input_usage is None and output_usage is None:
            usage_state = EVIDENCE_STATE_UNAVAILABLE
            usage_unavailable_reason = TOKEN_USAGE_ABSENT_REASON
        else:
            usage_state = USAGE_STATE_MEASURED
            usage_unavailable_reason = None
        latency_ms = _require_optional_latency(semantic.latency_ms, "semantic latency_ms")
        latency_clock = (
            LATENCY_CLOCK_MONOTONIC if latency_ms is not None else LATENCY_CLOCK_UNAVAILABLE
        )
        fallback_reason = getattr(semantic, "fallback_reason", None)
        fallback_reason = None if fallback_reason is None else str(_enum_value(fallback_reason))
        disposition = getattr(semantic, "disposition", None)
        disposition = None if disposition is None else str(_enum_value(disposition))
        for name in ("execution_id", "attempt_id", "request_id"):
            sem_value = getattr(semantic, name, None)
            if sem_value is not None and str(sem_value) != getattr(row, name):
                raise ValueError(
                    f"semantic telemetry correlation identity mismatch: {name}"
                )

    if row.receipt_status is None:
        receipt_state = EVIDENCE_STATE_UNAVAILABLE
        receipt_unavailable_reason = RECEIPT_ABSENT_REASON
        receipt_status = None
        accepted = False
    else:
        receipt_state = EVIDENCE_STATE_AVAILABLE
        receipt_unavailable_reason = None
        receipt_status = str(_enum_value(row.receipt_status))
        accepted = receipt_status == RECEIPT_STATUS_ACCEPTED

    if row.started_at_wall is None and row.finished_at_wall is None:
        wall_stamp_clock = WALL_STAMP_UNAVAILABLE
    else:
        wall_stamp_clock = WALL_STAMP_CLOCK

    cost = _project_cost(input_usage, output_usage, row.pricing, row.currency)
    return RouteAttemptTelemetry(
        execution_id=row.execution_id,
        attempt_id=row.attempt_id,
        request_id=row.request_id,
        selection=_project_selection_summary(row),
        telemetry_state=telemetry_state,
        telemetry_unavailable_reason=telemetry_unavailable_reason,
        input_usage=input_usage,
        output_usage=output_usage,
        usage_state=usage_state,
        usage_unavailable_reason=usage_unavailable_reason,
        latency_ms=latency_ms,
        latency_clock=latency_clock,
        started_at_wall=row.started_at_wall,
        finished_at_wall=row.finished_at_wall,
        wall_stamp_clock=wall_stamp_clock,
        fallback_reason=fallback_reason,
        disposition=disposition,
        receipt_state=receipt_state,
        receipt_unavailable_reason=receipt_unavailable_reason,
        receipt_status=receipt_status,
        accepted=accepted,
        duplicate_of=duplicate_of,
        cost=cost,
    )


def project_route_telemetry(
    *, attempts: tuple[RouteAttemptInput, ...]
) -> RouteTelemetryEvidence:
    """Compose per-attempt route telemetry from injected inputs only.

    Deterministic and pure: same inputs produce an equal result. Rows are
    kept verbatim; accounting counts distinct attempt identities once, and
    rows repeating an identity point at the first row with that identity via
    ``duplicate_of``. An empty input set still returns a valid evidence
    object with zero counts.
    """
    if attempts is None:
        raise ValueError("attempts must be a tuple of RouteAttemptInput")
    if isinstance(attempts, (str, bytes)) or not isinstance(attempts, (tuple, list)):
        raise ValueError("attempts must be a tuple of RouteAttemptInput")
    rows = list(attempts)
    for row in rows:
        if not isinstance(row, RouteAttemptInput):
            raise ValueError("attempts must contain RouteAttemptInput values")

    projected: list[RouteAttemptTelemetry] = []
    identity_to_index: dict[tuple[str, str], int] = {}
    accepted_identities: set[tuple[str, str]] = set()
    duplicate_row_count = 0
    for row in rows:
        identity = (row.execution_id, row.attempt_id)
        if identity in identity_to_index:
            duplicate_of = identity_to_index[identity]
            duplicate_row_count += 1
        else:
            duplicate_of = None
            identity_to_index[identity] = len(projected)
        projected.append(_project_attempt(row, duplicate_of))
        if row.receipt_status is not None:
            status = str(_enum_value(row.receipt_status))
            if status == RECEIPT_STATUS_ACCEPTED:
                accepted_identities.add(identity)

    return RouteTelemetryEvidence(
        attempts=tuple(projected),
        attempted_attempt_count=len(identity_to_index),
        accepted_attempt_count=len(accepted_identities),
        duplicate_row_count=duplicate_row_count,
    )
