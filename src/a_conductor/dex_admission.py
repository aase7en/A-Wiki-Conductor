"""DEX-2c authority-gated admission issuer (WO-P1-612 / #526 / #495).

Typed, durable, idempotent admission decisions over the accepted DEX-2b
identity foundation. This module creates NO new claim authority: callers
present the authoritative claim view; the issuer only validates freshness
and binding consistency and records the decision. Fail-closed everywhere.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .dex_identity import DexBindingIdentity, binding_digest


class AdmissionDenied(RuntimeError):
    """Typed fail-closed denial. `code` is one of ADMISSION_* codes."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


DENIED_STALE_CLAIM = "ADMISSION_CLAIM_GENERATION_STALE"
DENIED_IDENTITY_MISMATCH = "ADMISSION_IDENTITY_MISMATCH"
DENIED_NOT_LIVE = "ADMISSION_CLAIM_NOT_LIVE"


@dataclass(frozen=True, slots=True)
class ClaimView:
    """Authoritative claim state supplied by the existing claim authority.

    The admission issuer never derives or owns this view; it fails closed
    when the view is absent or inconsistent with the requested binding.
    """

    claim_ref: str
    claim_generation: int
    live: bool

    def __post_init__(self) -> None:
        if not isinstance(self.claim_ref, str) or not self.claim_ref.strip():
            raise ValueError("claim_ref must be a non-empty string")
        if (
            not isinstance(self.claim_generation, int)
            or isinstance(self.claim_generation, bool)
            or self.claim_generation < 0
        ):
            raise ValueError("claim_generation must be a non-negative int")
        if not isinstance(self.live, bool):
            raise ValueError("live must be a bool")


@dataclass(frozen=True, slots=True)
class AdmissionRecord:
    """Durable admission decision for exactly one attempt."""

    execution_id: str
    attempt_id: str
    binding_digest: str
    claim_generation: int
    admitted: bool

    def __post_init__(self) -> None:
        for field in ("execution_id", "attempt_id", "binding_digest"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string")
        if (
            not isinstance(self.claim_generation, int)
            or isinstance(self.claim_generation, bool)
            or self.claim_generation < 0
        ):
            raise ValueError("claim_generation must be a non-negative int")
        if not isinstance(self.admitted, bool):
            raise ValueError("admitted must be a bool")


class AdmissionIssuer:
    """Idempotent admission decisions keyed by (execution_id, attempt_id).

    Repeated admission of the SAME identity returns the ORIGINAL decision
    (at most one live attempt per identity). A second, different attempt of
    the same execution requires a new attempt_id from the caller — the
    issuer never generates attempt identities.
    """

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], AdmissionRecord] = {}

    def admit(
        self,
        *,
        binding: DexBindingIdentity,
        claim_view: ClaimView,
        expected_claim_generation: Optional[int] = None,
    ) -> AdmissionRecord:
        if not isinstance(binding, DexBindingIdentity):
            raise ValueError("binding must be a DexBindingIdentity")
        if not isinstance(claim_view, ClaimView):
            raise ValueError("claim_view must be a ClaimView")

        key = (binding.execution_id, binding.attempt_id)
        existing = self._records.get(key)
        if existing is not None:
            # Idempotent replay: return the original decision unchanged.
            # A replay whose claim view no longer matches the recorded
            # generation is an identity inconsistency, not a re-decision.
            if existing.claim_generation != claim_view.claim_generation:
                raise AdmissionDenied(
                    DENIED_IDENTITY_MISMATCH,
                    "admission replay claim generation differs from the recorded decision",
                )
            return existing

        if not claim_view.live:
            raise AdmissionDenied(
                DENIED_NOT_LIVE,
                f"claim {claim_view.claim_ref} is not live",
            )
        if claim_view.claim_ref != binding.claim_ref:
            raise AdmissionDenied(
                DENIED_IDENTITY_MISMATCH,
                "claim view does not match the binding claim_ref",
            )
        if claim_view.claim_generation != binding.claim_generation:
            raise AdmissionDenied(
                DENIED_STALE_CLAIM,
                f"binding generation {binding.claim_generation} != live generation {claim_view.claim_generation}",
            )
        if (
            expected_claim_generation is not None
            and claim_view.claim_generation != expected_claim_generation
        ):
            raise AdmissionDenied(
                DENIED_STALE_CLAIM,
                "claim generation does not match the caller-required generation",
            )

        record = AdmissionRecord(
            execution_id=binding.execution_id,
            attempt_id=binding.attempt_id,
            binding_digest=binding_digest(binding),
            claim_generation=claim_view.claim_generation,
            admitted=True,
        )
        self._records[key] = record
        return record
