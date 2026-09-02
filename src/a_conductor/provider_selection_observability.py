"""Pure one-provider selection/fallback observability projection (WO128 T1).

This module is presentation-only evidence shaping. It performs no store or
filesystem access, launches nothing, resolves no credentials, and recomputes
no policy, readiness, routing, or ranking. Absent selection authority is
always ``UNKNOWN`` and absent fallback authority is always ``NOT_EVALUATED``;
those are constants, not derivations. Admission evidence describes capacity
grants and their persisted lifecycle only — it is never a router decision
and never an execution-outcome claim, including when an ACTIVE grant is
observed past expiry (that is reconcile evidence with unknown outcome).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .provider_config_store import ProviderAdmissionRecord

SELECTION_REASON_UNKNOWN = "UNKNOWN"
FALLBACK_REASON_NOT_EVALUATED = "NOT_EVALUATED"

GENERATION_MATCHES_CURRENT = "MATCHES_CURRENT"
GENERATION_STALE_VS_CURRENT = "STALE_VS_CURRENT"
GENERATION_UNKNOWN = "UNKNOWN"

EXPIRY_NOT_EXPIRED = "NOT_EXPIRED"
EXPIRY_PAST_EXPIRY_RECONCILE_REQUIRED = "PAST_EXPIRY_RECONCILE_REQUIRED"
EXPIRY_TERMINAL = "TERMINAL"
EXPIRY_NOT_EVALUATED = "EXPIRY_NOT_EVALUATED"

_ADMISSION_STATUSES = frozenset({"ACTIVE", "RELEASED", "EXPIRED"})
_MAX_GENERATION = (1 << 63) - 1


def _require_identity(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("provider_id must not be blank")
    return value


def _require_generation(value: int | None) -> int | None:
    if value is None:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= _MAX_GENERATION
    ):
        raise ValueError(
            "current_configuration_generation must be a bounded positive integer or None"
        )
    return value


def _require_now(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("now must be an aware datetime or None")
    return value.astimezone(timezone.utc)


def _generation_relation(
    admission_generation: int | None, current_generation: int | None
) -> str:
    if admission_generation is None or current_generation is None:
        return GENERATION_UNKNOWN
    if admission_generation == current_generation:
        return GENERATION_MATCHES_CURRENT
    return GENERATION_STALE_VS_CURRENT


def _expiry_observation(record: ProviderAdmissionRecord, now: datetime | None) -> str:
    if record.status == "RELEASED":
        return EXPIRY_TERMINAL
    if record.status == "EXPIRED":
        return EXPIRY_PAST_EXPIRY_RECONCILE_REQUIRED
    # remaining persisted status is ACTIVE by validation
    if now is None:
        return EXPIRY_NOT_EVALUATED
    if record.expires_at <= now:
        return EXPIRY_PAST_EXPIRY_RECONCILE_REQUIRED
    return EXPIRY_NOT_EXPIRED


@dataclass(frozen=True, slots=True)
class AdmissionEvidence:
    """One persisted admission grant projected as operator evidence."""

    admission_id: str
    provider_id: str
    execution_id: str
    batch_id: str
    status: str
    acquired_at: datetime
    expires_at: datetime
    released_at: datetime | None
    reconciled_at: datetime | None
    configuration_generation: int | None
    generation_relation: str
    expiry_observation: str


@dataclass(frozen=True, slots=True)
class ProviderSelectionEvidence:
    """One provider's selection/fallback evidence without invented authority."""

    provider_id: str
    selection_reason: str
    fallback_reason: str
    current_configuration_generation: int | None
    admissions: tuple[AdmissionEvidence, ...]


def project_provider_selection_evidence(
    *,
    provider_id: str,
    current_configuration_generation: int | None,
    admissions: tuple[ProviderAdmissionRecord, ...],
    now: datetime | None = None,
) -> ProviderSelectionEvidence:
    """Project one provider's persisted evidence without inventing authority.

    Accepts exactly one provider so cross-provider ranking or fallback
    inference is structurally absent. Every record must already be decoded
    (store-typed) and must belong to this provider; near-miss identifiers are
    kept verbatim and never joined or correlated. Ordering is deterministic
    newest-first regardless of input order.
    """
    resolved_provider = _require_identity(provider_id)
    resolved_generation = _require_generation(current_configuration_generation)
    resolved_now = _require_now(now)
    if not isinstance(admissions, tuple):
        raise ValueError("admissions must be a tuple of ProviderAdmissionRecord")
    records: list[ProviderAdmissionRecord] = []
    for record in admissions:
        if not isinstance(record, ProviderAdmissionRecord):
            raise ValueError("admissions must contain ProviderAdmissionRecord values")
        if record.provider_id != resolved_provider:
            raise ValueError("admission provider identity mismatch")
        if record.status not in _ADMISSION_STATUSES:
            raise ValueError("admission status is outside the persisted vocabulary")
        records.append(record)
    ordered = sorted(
        records,
        key=lambda item: (item.acquired_at, item.admission_id),
        reverse=True,
    )
    evidence = tuple(
        AdmissionEvidence(
            admission_id=record.admission_id,
            provider_id=record.provider_id,
            execution_id=record.execution_id,
            batch_id=record.batch_id,
            status=record.status,
            acquired_at=record.acquired_at,
            expires_at=record.expires_at,
            released_at=record.released_at,
            reconciled_at=record.reconciled_at,
            configuration_generation=record.configuration_generation,
            generation_relation=_generation_relation(
                record.configuration_generation, resolved_generation
            ),
            expiry_observation=_expiry_observation(record, resolved_now),
        )
        for record in ordered
    )
    return ProviderSelectionEvidence(
        provider_id=resolved_provider,
        selection_reason=SELECTION_REASON_UNKNOWN,
        fallback_reason=FALLBACK_REASON_NOT_EVALUATED,
        current_configuration_generation=resolved_generation,
        admissions=evidence,
    )
