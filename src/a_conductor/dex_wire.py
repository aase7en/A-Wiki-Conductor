"""DEX-2c end-to-end admission → dispatch → collect → receipt wiring (WO-P1-612).

Orchestrates the ACCEPTED foundations over an injectable transport port:

    admit (dex_admission) → execution-record precondition → receipt-
    idempotency check → ONE dispatch → collect → strict
    decode_collected_evidence (+generation agreement) → idempotent receipt
    (SQLiteExecutionStore).

Fail-closed posture: admission denial happens BEFORE any dispatch; each
identity is serialized by a per-identity lock held from the fence check
through receipt persistence, so concurrent run_attempt calls cannot
double-dispatch (the loser observes the receipt, or the ambiguity fence);
an ambiguous/throwing dispatch FENCES the identity permanently (typed
AMBIGUOUS, never a silent retry); a collect failure, evidence rejection,
or receipt-persistence failure AFTER a dispatched attempt also fences the
identity (re-dispatch would duplicate substrate effects — reconciliation
is an explicit typed state); receipt-state
lookups never fail open; a receipt-store conflict on ANY immutable field
propagates typed instead of masking as duplicate success.

Honest limitations — DEFERRED to successor slice DEX-2d (WO-612 §Limitations):
  1. Durable admission journal (decisions/fences are in-process only).
  2. Cross-restart at-most-once dispatch fence (crash between dispatch
     and receipt relies on substrate scope-conflict truth + manual
     reconciliation; this wire adds no durable fence).
  3. Contract §6 same-execution retry model (new attempts require new
     execution identities in this slice).
  4. Contract §2 simultaneous-dispatch fencing beyond one process.
  5. Contract §5 TERMINAL_UNHARVESTED blocking on admission.

No new authority is created here: admission validity comes from
AdmissionIssuer + the caller-owned ClaimView; transport is a caller
port; receipts are stamped only through the accepted durable store.
"""
from __future__ import annotations

import threading
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
    """One orchestrator instance over one store.

    Per-identity serialization: a per-identity lock is taken BEFORE the
    fence check and held through receipt persistence, so two concurrent
    run_attempt calls for the same identity cannot both dispatch — the
    second observes the receipt (DUPLICATE) or the ambiguity fence.
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
        self._locks_guard = threading.Lock()
        self._locks: dict[tuple[str, str], threading.Lock] = {}

    def _identity_lock(self, identity: tuple[str, str]) -> threading.Lock:
        with self._locks_guard:
            lock = self._locks.get(identity)
            if lock is None:
                lock = threading.Lock()
                self._locks[identity] = lock
            return lock

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

        # 2. Serialize the identity from fence-check through receipt.
        with self._identity_lock(identity):
            return self._attempt_locked(binding, admission, identity)

    def _attempt_locked(
        self,
        binding: DexBindingIdentity,
        admission,
        identity: tuple[str, str],
    ) -> WireOutcome:
        # 3. Ambiguity fence: an identity whose dispatch was ambiguous can
        # NEVER dispatch again from this wire.
        if identity in self._fenced:
            return self._ambiguous(binding, "identity is fenced as ambiguous pending reconciliation")

        # 4. Durable precondition: receipt persistence requires an existing
        # execution record. Fail closed BEFORE dispatch when absent.
        self._probe_execution_record(binding)

        # 5. Durable duplicate check (typed containment — never fail open).
        existing = self._find_receipt_contained(binding)
        if existing is not None:
            return WireOutcome(
                execution_id=binding.execution_id,
                attempt_id=binding.attempt_id,
                receipt_id=existing,
                status="DUPLICATE_ALREADY_COMPLETED",
                detail="receipt already recorded for this identity",
            )

        # 6. ONE dispatch; exceptions and non-DISPATCHED statuses both
        # permanently fence the identity (typed AMBIGUOUS, no retry).
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
        except WireError:
            raise
        except Exception as err:  # noqa: BLE001 - belt/braces containment
            self._fenced.add(identity)
            return self._ambiguous(binding, f"dispatch failed unexpectedly: {err}")

        # 7. Collect. A failure AFTER a dispatched attempt fences the
        # identity too: re-dispatching would duplicate substrate effects.
        try:
            raw = self._transport.collect(binding.execution_id, binding.attempt_id)
        except Exception as err:  # noqa: BLE001 - typed containment
            self._fenced.add(identity)
            raise WireError(
                WIRE_COLLECT_UNAVAILABLE,
                f"collect failed after dispatch; identity fenced pending reconciliation: {err}",
            ) from err

        # 8. Strict decode + generation agreement with the frozen decision.
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
            # Evidence about a dispatched attempt failed ingest: fence so a
            # re-run cannot dispatch again and produce another effect.
            self._fenced.add(identity)
            return WireOutcome(
                execution_id=binding.execution_id,
                attempt_id=binding.attempt_id,
                receipt_id=None,
                status="EVIDENCE_REJECTED",
                detail=f"{WIRE_EVIDENCE_REJECTED}: {err} (identity fenced)",
            )
        if evidence.claim_generation != admission.claim_generation:
            self._fenced.add(identity)
            return WireOutcome(
                execution_id=binding.execution_id,
                attempt_id=binding.attempt_id,
                receipt_id=None,
                status="EVIDENCE_REJECTED",
                detail=(
                    f"{WIRE_GENERATION_MISMATCH}: evidence generation {evidence.claim_generation} "
                    f"!= admitted generation {admission.claim_generation} (identity fenced)"
                ),
            )

        # 9. Idempotent durable receipt. Drift is surfaced through the
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
            replay = self._find_identical_receipt(receipt)
            if replay is not None:
                return WireOutcome(
                    execution_id=binding.execution_id,
                    attempt_id=binding.attempt_id,
                    receipt_id=replay,
                    status="DUPLICATE_ALREADY_COMPLETED",
                    detail=f"receipt raced an identical stored receipt: {err}",
                )
            # A DIFFERENT immutable receipt exists for this identity, or the
            # store is genuinely broken. The substrate effect ALREADY
            # happened, so fence before propagating typed — a re-run must
            # never dispatch again, and never mask this as duplicate success.
            self._fenced.add(identity)
            raise WireError(
                WIRE_RECEIPT_CONFLICT,
                f"receipt store rejected the receipt; identity fenced pending reconciliation: {err}",
            ) from err
        except Exception as err:  # noqa: BLE001 - typed containment
            # Same reasoning: the effect happened, only the durable record
            # failed — fence so no re-run can duplicate it.
            self._fenced.add(identity)
            raise WireError(
                WIRE_STATE_UNAVAILABLE,
                f"receipt persistence failed; identity fenced pending reconciliation: {err}",
            ) from err
        return WireOutcome(
            execution_id=stored.execution_id,
            attempt_id=stored.attempt_id,
            receipt_id=stored.receipt_id,
            status="COMPLETED",
            detail="receipt recorded",
        )

    def _probe_execution_record(self, binding: DexBindingIdentity) -> None:
        try:
            self._store.list_events(binding.execution_id)
        except ExecutionStoreError as err:
            if "EXECUTION_NOT_FOUND" in str(err):
                raise WireError(
                    WIRE_EXECUTION_RECORD_MISSING,
                    f"execution record missing for {binding.execution_id}; create it via the authority path first",
                ) from err
            raise WireError(WIRE_STATE_UNAVAILABLE, f"execution state unreadable: {err}") from err
        except Exception as err:  # noqa: BLE001 - typed containment
            raise WireError(WIRE_STATE_UNAVAILABLE, f"execution state unreadable: {err}") from err

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

    def _find_receipt_contained(self, binding: DexBindingIdentity) -> str | None:
        """Durable duplicate signal (contract §5 ingest idempotency): any
        RECEIPT_RECORDED event on the execution means an attempt already
        completed. Conservative by design (multi-attempt sequencing is the
        caller's authority — new attempts require new execution identities
        in this slice; the contract's same-execution retry model is
        deferred to DEX-2d). Store errors propagate typed — never fail
        open."""
        try:
            events = self._store.list_events(binding.execution_id)
        except ExecutionStoreError as err:
            raise WireError(WIRE_STATE_UNAVAILABLE, f"receipt state unreadable: {err}") from err
        except Exception as err:  # noqa: BLE001 - typed containment
            raise WireError(WIRE_STATE_UNAVAILABLE, f"receipt state unreadable: {err}") from err
        for event in events or ():
            if str(getattr(event.event_type, "value", event.event_type)) == "RECEIPT_RECORDED":
                evidence_ref = getattr(event, "evidence_ref", None)
                if isinstance(evidence_ref, str) and evidence_ref:
                    return evidence_ref
        return None

    def _find_identical_receipt(self, receipt) -> str | None:
        """A raced duplicate requires agreement on EVERY immutable field
        the store enforces (identity tuple AND claim_generation, SHA set,
        disposition, evidence_ref) — anything less is a conflict."""
        from .execution_record import compute_receipt_id

        receipt_id = compute_receipt_id(
            execution_id=receipt.execution_id,
            attempt_id=receipt.attempt_id,
            result_digest=receipt.result_digest,
            binding_digest=receipt.binding_digest,
        )
        try:
            stored = self._store.get_receipt(receipt_id)
        except Exception:  # noqa: BLE001 - unreadable => not provably identical
            return None
        if (
            stored.execution_id == receipt.execution_id
            and stored.attempt_id == receipt.attempt_id
            and stored.result_digest == receipt.result_digest
            and stored.binding_digest == receipt.binding_digest
            and stored.claim_generation == receipt.claim_generation
            and stored.authority_sha == receipt.authority_sha
            and stored.execution_sha == receipt.execution_sha
            and stored.disposition == receipt.disposition
            and stored.evidence_ref == receipt.evidence_ref
        ):
            return stored.receipt_id
        return None
