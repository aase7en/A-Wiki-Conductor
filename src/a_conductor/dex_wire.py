"""DEX-2c end-to-end admission → dispatch → collect → receipt wiring (WO-P1-612).

Orchestrates the ACCEPTED foundations over an injectable transport port:

    admit (dex_admission) → execution-record precondition → receipt-
    idempotency check → ONE dispatch → collect → strict
    decode_collected_evidence (+generation agreement) → idempotent receipt
    (SQLiteExecutionStore).

Fail-closed posture: admission denial happens BEFORE any dispatch; an
ambiguous or throwing dispatch FENCES the identity (later calls return
AMBIGUOUS without re-dispatch — reconciliation is an explicit typed
state, never a silent retry); receipt-state lookups never fail open; a
receipt-store conflict propagates typed instead of masking as duplicate
success.

Honest limitations (successor slice DEX-2d, per WO-612): the dispatch
fence and admission decisions are in-process; a crash between dispatch
and receipt leaves reconciliation to the durable store + substrate truth
(there is NO cross-restart at-most-once fence in this slice — the
substrate scope-conflict behavior narrows but does not eliminate double
dispatch; a durable dispatch journal requires its own authority decision).
No new authority is created here: admission validity comes from
AdmissionIssuer + the caller-owned ClaimView; transport is a caller
port; receipts are stamped only through the accepted durable store.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .dex_admission import AdmissionDenied, AdmissionIssuer, ClaimView
from .dex_evidence import DexEvidenceError, decode_collected_evidence
from .dex_identity import DexBindingIdentity
from .execution_record import ReceiptDisposition, new_execution_receipt
from .execution_store import ExecutionStoreError, SQLiteExecutionStore

WIRE_ADMISSION_DENIED = "WIRE_ADMISSION_DENIED"
WIRE_LAUNCH_AMBIGUOUS = "WIRE_LAUNCH_AMBIGUOUS"
WIRE_COLLECT_UNAVAILABLE = "WIRE_COLLECT_UNAVAILABLE"
WIRE_EVIDENCE_REJECTED = "WIRE_EVIDENCE_REJECTED"
WIRE_EXECUTION_RECORD_MISSING = "WIRE_EXECUTION_RECORD_MISSING"
WIRE_STATE_UNAVAILABLE = "WIRE_STATE_UNAVAILABLE"
WIRE_RECEIPT_CONFLICT = "WIRE_RECEIPT_CONFLICT"
WIRE_GENERATION_MISMATCH = "WIRE_GENERATION_MISMATCH"


class WireError(RuntimeError):
    """Typed fail-closed wire outcome. `code` is one of WIRE_* codes."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


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
    """One orchestrator instance over one store. Per-identity state:

    - decided-admitted + receipt stored  -> DUPLICATE_ALREADY_COMPLETED
    - dispatch returned/raised ambiguous -> AMBIGUOUS forever (fence)
    - dispatch in flight for the identity -> AMBIGUOUS (concurrency fence)
    """

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
        self._fenced: set[tuple[str, str]] = set()
        self._inflight: set[tuple[str, str]] = set()

    def run_attempt(
        self,
        *,
        binding: DexBindingIdentity,
        claim_view: ClaimView,
    ) -> WireOutcome:
        identity = (binding.execution_id, binding.attempt_id)

        # 1. Admission (fail-closed BEFORE any dispatch). A frozen denial
        # re-raises here on every call; the identity can never flip.
        try:
            admission = self._issuer.decide(binding=binding, claim_view=claim_view)
        except AdmissionDenied as denial:
            return self._denied(binding, denial)

        # 2. Ambiguity fence: an identity whose dispatch was ambiguous (or
        # is in flight right now) NEVER dispatches again from this wire.
        if identity in self._fenced or identity in self._inflight:
            return self._ambiguous(binding, "identity is fenced as ambiguous pending reconciliation")

        # 3. Durable precondition: receipt persistence requires an existing
        # execution record. Fail closed BEFORE dispatch when absent —
        # otherwise the attempt would dispatch and then lose its receipt.
        try:
            self._store.list_events(binding.execution_id)
        except ExecutionStoreError as err:
            if "EXECUTION_NOT_FOUND" in str(err) or "not found" in str(err).lower():
                raise WireError(
                    WIRE_EXECUTION_RECORD_MISSING,
                    f"execution record missing for {binding.execution_id}; create it via the authority path first",
                ) from err
            raise WireError(WIRE_STATE_UNAVAILABLE, f"execution state unreadable: {err}") from err
        except Exception as err:  # noqa: BLE001 - typed containment, never fail-open
            raise WireError(WIRE_STATE_UNAVAILABLE, f"execution state unreadable: {err}") from err

        # 4. Durable duplicate check (fail-closed: state errors raise, they
        # never masquerade as "no receipt yet").
        existing = self._find_receipt(binding)
        if existing is not None:
            return WireOutcome(
                execution_id=binding.execution_id,
                attempt_id=binding.attempt_id,
                receipt_id=existing,
                status="DUPLICATE_ALREADY_COMPLETED",
                detail="receipt already recorded for this identity",
            )

        # 5. ONE dispatch, fenced against exceptions and malformed status.
        self._inflight.add(identity)
        try:
            try:
                dispatch_result = self._transport.dispatch(binding)
            except Exception as err:  # noqa: BLE001 - typed containment
                self._fenced.add(identity)
                return self._ambiguous(binding, f"dispatch threw: {err}")
            status = dispatch_result.get("status") if isinstance(dispatch_result, dict) else None
            if status != "DISPATCHED":
                self._fenced.add(identity)
                return self._ambiguous(binding, f"dispatch status was not DISPATCHED: {status!r}")
        finally:
            self._inflight.discard(identity)

        # 6. Collect raw evidence bytes from the substrate.
        try:
            raw = self._transport.collect(binding.execution_id, binding.attempt_id)
        except Exception as err:  # noqa: BLE001 - typed containment
            raise WireError(WIRE_COLLECT_UNAVAILABLE, f"collect failed: {err}") from err

        # 7. Strict decode against the binding's expected identities, plus
        # generation agreement with the frozen admission decision.
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
        if evidence.claim_generation != admission.claim_generation:
            return WireOutcome(
                execution_id=binding.execution_id,
                attempt_id=binding.attempt_id,
                receipt_id=None,
                status="EVIDENCE_REJECTED",
                detail=(
                    f"{WIRE_GENERATION_MISMATCH}: evidence generation {evidence.claim_generation} "
                    f"!= admitted generation {admission.claim_generation}"
                ),
            )

        # 8. Idempotent durable receipt. Drift is surfaced through the
        # QUARANTINED disposition — never silently ACCEPTED.
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
        except ExecutionStoreError as err:
            replay = self._find_receipt_for_identity(
                binding.execution_id,
                binding.attempt_id,
                receipt.result_digest,
                receipt.binding_digest,
            )
            if replay is not None:
                return WireOutcome(
                    execution_id=binding.execution_id,
                    attempt_id=binding.attempt_id,
                    receipt_id=replay,
                    status="DUPLICATE_ALREADY_COMPLETED",
                    detail=f"receipt raced an identical stored receipt: {err}",
                )
            # A DIFFERENT immutable receipt exists for this identity, or the
            # store is genuinely broken — both propagate typed, never
            # masked as duplicate success.
            raise WireError(WIRE_RECEIPT_CONFLICT, f"receipt store rejected the receipt: {err}") from err
        return WireOutcome(
            execution_id=stored.execution_id,
            attempt_id=stored.attempt_id,
            receipt_id=stored.receipt_id,
            status="COMPLETED",
            detail="receipt recorded",
        )

    def _denied(self, binding: DexBindingIdentity, denial: AdmissionDenied) -> WireOutcome:
        return WireOutcome(
            execution_id=binding.execution_id,
            attempt_id=binding.attempt_id,
            receipt_id=None,
            status="DENIED",
            detail=f"{denial.code}: {denial.detail}",
        )

    def _ambiguous(self, binding: DexBindingIdentity, detail: str) -> WireOutcome:
        return WireOutcome(
            execution_id=binding.execution_id,
            attempt_id=binding.attempt_id,
            receipt_id=None,
            status="AMBIGUOUS",
            detail=f"{WIRE_LAUNCH_AMBIGUOUS}: {detail} (no auto-retry; explicit reconciliation required)",
        )

    def _find_receipt(self, binding: DexBindingIdentity) -> str | None:
        """Durable duplicate signal: any RECEIPT_RECORDED event on the
        execution means an attempt already completed. Conservative by
        design (multi-attempt sequencing is the caller's authority — new
        attempts require new execution identities in this slice; the
        contract's same-execution retry model is deferred to DEX-2d).
        Store errors propagate typed — never fail open."""
        events = self._store.list_events(binding.execution_id)
        for event in events or ():
            if str(getattr(event.event_type, "value", event.event_type)) == "RECEIPT_RECORDED":
                evidence_ref = getattr(event, "evidence_ref", None)
                if isinstance(evidence_ref, str) and evidence_ref:
                    return evidence_ref
        return None

    def _find_receipt_for_identity(
        self,
        execution_id: str,
        attempt_id: str,
        result_digest: str,
        binding_digest_value: str,
    ) -> str | None:
        """Compute the deterministic receipt id for OUR identity tuple and
        confirm it actually exists — only an exact-tuple match counts as a
        raced duplicate; anything else is a conflict."""
        from .execution_record import compute_receipt_id

        receipt_id = compute_receipt_id(
            execution_id=execution_id,
            attempt_id=attempt_id,
            result_digest=result_digest,
            binding_digest=binding_digest_value,
        )
        try:
            stored = self._store.get_receipt(receipt_id)
        except Exception:  # noqa: BLE001 - unreadable => not provably identical
            return None
        if (
            stored.execution_id == execution_id
            and stored.attempt_id == attempt_id
            and stored.result_digest == result_digest
            and stored.binding_digest == binding_digest_value
        ):
            return stored.receipt_id
        return None
