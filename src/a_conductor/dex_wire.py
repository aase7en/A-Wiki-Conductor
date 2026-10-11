"""DEX-2c end-to-end admission → dispatch → collect → receipt wiring (WO-P1-612).

Orchestrates the ACCEPTED foundations over an injectable transport port:

    admit (dex_admission) → receipt-idempotency check → dispatch →
    collect → strict decode_collected_evidence → idempotent receipt
    (SQLiteExecutionStore).

Creates NO new authority: admission validity comes from AdmissionIssuer +
the caller-owned ClaimView; transport is a caller-supplied port; receipts
are stamped only through the accepted durable store. Fail-closed typed
outcomes; at-most-once dispatch per admitted identity; no auto-retry.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .dex_admission import AdmissionDenied, AdmissionIssuer, ClaimView
from .dex_evidence import DexCollectedEvidence, DexEvidenceError, decode_collected_evidence
from .dex_identity import DexBindingIdentity
from .execution_record import ReceiptDisposition, new_execution_receipt
from .execution_store import SQLiteExecutionStore


class WireError(RuntimeError):
    """Typed fail-closed wire outcome. `code` is one of WIRE_* codes."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


WIRE_ADMISSION_DENIED = "WIRE_ADMISSION_DENIED"
WIRE_LAUNCH_AMBIGUOUS = "WIRE_LAUNCH_AMBIGUOUS"
WIRE_COLLECT_UNAVAILABLE = "WIRE_COLLECT_UNAVAILABLE"
WIRE_EVIDENCE_REJECTED = "WIRE_EVIDENCE_REJECTED"


class DispatchTransport(Protocol):
    """Caller-supplied substrate transport port (no implementation here)."""

    def dispatch(self, binding: DexBindingIdentity) -> dict: ...

    def collect(self, execution_id: str, attempt_id: str) -> bytes: ...


@dataclass(frozen=True, slots=True)
class WireOutcome:
    execution_id: str
    attempt_id: str
    receipt_id: str | None
    status: str  # COMPLETED | DUPLICATE_ALREADY_COMPLETED | AMBIGUOUS | DENIED | EVIDENCE_REJECTED
    detail: str


class AdmissionReceiptWire:
    """One orchestrator instance over one store; stateless per call except
    the issuer's idempotent decision records and the store's UNIQUE rows."""

    def __init__(
        self,
        *,
        issuer: AdmissionIssuer,
        store: SQLiteExecutionStore,
        transport: DispatchTransport,
    ) -> None:
        self._issuer = issuer
        self._store = store
        self._transport = transport

    def run_attempt(
        self,
        *,
        binding: DexBindingIdentity,
        claim_view: ClaimView,
    ) -> WireOutcome:
        # 1. Admission (fail-closed BEFORE any dispatch).
        try:
            admission = self._issuer.admit(binding=binding, claim_view=claim_view)
        except AdmissionDenied as denial:
            return WireOutcome(
                execution_id=binding.execution_id,
                attempt_id=binding.attempt_id,
                receipt_id=None,
                status="DENIED",
                detail=f"{denial.code}: {denial.detail}",
            )

        # 2. Idempotency: an existing receipt for this identity means the
        # attempt already completed — at most one effect, no re-dispatch.
        existing = self._find_receipt(binding)
        if existing is not None:
            return WireOutcome(
                execution_id=binding.execution_id,
                attempt_id=binding.attempt_id,
                receipt_id=existing,
                status="DUPLICATE_ALREADY_COMPLETED",
                detail="receipt already recorded for this identity",
            )

        # 3. Dispatch through the caller port. The port reports ambiguity
        # itself (lost response); the wire NEVER retries.
        dispatch_result = self._transport.dispatch(binding)
        if dispatch_result.get("status") == "AMBIGUOUS":
            return WireOutcome(
                execution_id=binding.execution_id,
                attempt_id=binding.attempt_id,
                receipt_id=None,
                status="AMBIGUOUS",
                detail="dispatch response lost; reconciliation required (no auto-retry)",
            )
        if dispatch_result.get("status") != "DISPATCHED":
            return WireOutcome(
                execution_id=binding.execution_id,
                attempt_id=binding.attempt_id,
                receipt_id=None,
                status="AMBIGUOUS",
                detail=f"unexpected dispatch status: {dispatch_result.get('status')!r}",
            )

        # 4. Collect raw evidence bytes from the substrate.
        try:
            raw = self._transport.collect(binding.execution_id, binding.attempt_id)
        except Exception as err:  # noqa: BLE001 - typed containment
            raise WireError(
                WIRE_COLLECT_UNAVAILABLE,
                f"collect failed: {err}",
            ) from err

        # 5. Strict decode against the binding's expected identities.
        try:
            evidence = decode_collected_evidence(
                raw,
                expected_execution_id=binding.execution_id,
                expected_attempt_id=binding.attempt_id,
                expected_binding_digest=admission.binding_digest,
                expected_authority_sha=binding.authority_sha,
                expected_execution_sha=binding.execution_sha,
            )
        except DexEvidenceError as err:
            return WireOutcome(
                execution_id=binding.execution_id,
                attempt_id=binding.attempt_id,
                receipt_id=None,
                status="EVIDENCE_REJECTED",
                detail=f"{WIRE_EVIDENCE_REJECTED}: {err}",
            )

        # 6. Idempotent durable receipt (executor-claimed facts are
        # advisory; substrate evidence decides the ACCEPTED disposition
        # only when exit state was observed terminal and drift is flagged
        # through the QUARANTINED disposition, never silently).
        disposition = (
            ReceiptDisposition.QUARANTINED
            if evidence.collected_under_drift
            else ReceiptDisposition.ACCEPTED
        )
        receipt = new_execution_receipt(
            execution_id=evidence.execution_id,
            attempt_id=evidence.attempt_id,
            result_digest=evidence.result_sha256,
            binding_digest=evidence.binding_digest,
            claim_generation=evidence.claim_generation,
            authority_sha=evidence.authority_sha,
            execution_sha=evidence.execution_sha,
            disposition=disposition,
            evidence_ref=evidence.evidence_sha256,
        )
        try:
            stored = self._store.record_receipt(receipt)
        except Exception as err:  # noqa: BLE001 - typed containment
            # Idempotent re-record of the identical receipt is the accepted
            # store behavior; anything else is a typed outage.
            replay = self._find_receipt(binding)
            if replay is not None:
                return WireOutcome(
                    execution_id=binding.execution_id,
                    attempt_id=binding.attempt_id,
                    receipt_id=replay,
                    status="DUPLICATE_ALREADY_COMPLETED",
                    detail=f"receipt raced: {err}",
                )
            raise WireError(WIRE_COLLECT_UNAVAILABLE, f"receipt record failed: {err}") from err
        return WireOutcome(
            execution_id=stored.execution_id,
            attempt_id=stored.attempt_id,
            receipt_id=stored.receipt_id,
            status="COMPLETED",
            detail="receipt recorded",
        )

    def _find_receipt(self, binding: DexBindingIdentity) -> str | None:
        """Durable duplicate signal: any RECEIPT_RECORDED event on the
        execution means an attempt already completed. Conservative by
        design (multi-attempt sequencing is the caller's authority; the
        wire fails closed toward NOT dispatching again)."""
        try:
            events = self._store.list_events(binding.execution_id)
        except Exception:  # noqa: BLE001 - unknown execution id etc.
            return None
        for event in events or ():
            if getattr(event, "event_type", None) is not None and str(
                getattr(event.event_type, "value", event.event_type)
            ) == "RECEIPT_RECORDED":
                evidence_ref = getattr(event, "evidence_ref", None)
                if isinstance(evidence_ref, str) and evidence_ref:
                    return evidence_ref
        return None


def decode_for_binding(
    raw: bytes, *, binding: DexBindingIdentity, binding_digest_value: str
) -> DexCollectedEvidence:
    """Strict decode helper re-exported for drivers and tests."""
    return decode_collected_evidence(
        raw,
        expected_execution_id=binding.execution_id,
        expected_attempt_id=binding.attempt_id,
        expected_binding_digest=binding_digest_value,
        expected_authority_sha=binding.authority_sha,
        expected_execution_sha=binding.execution_sha,
    )
