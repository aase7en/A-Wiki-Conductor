"""DEX-2c/DEX-2dA authority-gated admission issuer (WO-P1-625 / WO-P1-627).

Typed, idempotent admission decisions over the accepted DEX-2b identity
foundation. This module creates NO new claim authority: callers present the
authoritative claim view; the issuer only validates freshness and binding
consistency and records the decision — including DENIALS, which are frozen
exactly like admissions (a denied identity can never be re-decided, even if
the claim view later looks valid). Decisions bind the full binding digest;
a replay presenting a mutated binding under the same identity is a typed
conflict.

Durability (DEX-2dA, WO-P1-627): an issuer constructed with a journal
(``AdmissionIssuer(journal=DurableAdmissionJournal(store))``) persists every
decision — acceptances AND denials — through the existing durable execution
store, and a restarted issuer replays the frozen decision with exactly the
in-process semantics. The default journal-less issuer keeps the historical
in-memory behavior for deterministic contract tests; production composition
is journal-backed. Journal failures propagate fail-closed: an unreadable or
conflicting journal never becomes a fresh admission.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

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
    """Frozen admission decision for exactly one attempt identity."""

    execution_id: str
    attempt_id: str
    binding_digest: str
    claim_ref: str
    claim_generation: int
    admitted: bool
    code: str | None = None
    detail: str | None = None

    def __post_init__(self) -> None:
        for field in ("execution_id", "attempt_id", "binding_digest", "claim_ref"):
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
        if self.code is not None and (not isinstance(self.code, str) or not self.code.strip()):
            raise ValueError("code must be a non-empty string or None")
        if self.detail is not None and not isinstance(self.detail, str):
            raise ValueError("detail must be a string or None")


class AdmissionJournal(Protocol):
    """Durable decision-journal port (DEX-2dA). Implementations must be
    idempotent for identical rows and fail closed on unreadable/conflicting
    state — they never invent or flip decisions."""

    def load(self, execution_id: str, attempt_id: str) -> "AdmissionRecord | None": ...

    def record(self, record: "AdmissionRecord") -> None: ...


class DurableAdmissionJournal:
    """Journal adapter over the existing SQLiteExecutionStore (DEX-2dA).

    No new store: rows live in the store's ``admission_decisions`` table.
    Corrupt rows surface as typed store errors; conflicting re-records are
    typed conflicts. ``AdmissionRecord`` <-> row mapping lives here so the
    store stays policy-free.
    """

    def __init__(self, store) -> None:  # store: SQLiteExecutionStore (avoid import cycle)
        from .execution_store import SQLiteExecutionStore  # noqa: F401 - runtime type check

        if not isinstance(store, SQLiteExecutionStore):
            raise ValueError("store must be a SQLiteExecutionStore")
        self._store = store

    def load(self, execution_id: str, attempt_id: str) -> AdmissionRecord | None:
        row = self._store.load_admission_decision(execution_id, attempt_id)
        if row is None:
            return None
        return AdmissionRecord(
            execution_id=row.execution_id,
            attempt_id=row.attempt_id,
            binding_digest=row.binding_digest,
            claim_ref=row.claim_ref,
            claim_generation=row.claim_generation,
            admitted=row.admitted,
            code=row.code,
            detail=row.detail,
        )

    def record(self, record: AdmissionRecord) -> None:
        from .execution_store import AdmissionDecisionRow

        self._store.record_admission_decision(
            AdmissionDecisionRow(
                execution_id=record.execution_id,
                attempt_id=record.attempt_id,
                binding_digest=record.binding_digest,
                claim_ref=record.claim_ref,
                claim_generation=record.claim_generation,
                admitted=record.admitted,
                code=record.code,
                detail=record.detail,
            )
        )


class AdmissionIssuer:
    """Idempotent admission decisions keyed by (execution_id, attempt_id).

    The FIRST call for an identity decides permanently — admission or
    denial — and every later call for that identity returns or re-raises
    the SAME outcome. A replay whose binding digest or claim reference
    differs from the recorded decision is a typed identity conflict, never
    a re-decision. The issuer never generates attempt identities.

    With a journal, "permanently" spans process restarts: the decision is
    checked memory -> journal -> fresh-decide, and every fresh decision is
    journaled before being cached/returned.
    """

    def __init__(self, journal: AdmissionJournal | None = None) -> None:
        self._records: dict[tuple[str, str], AdmissionRecord] = {}
        self._journal = journal

    def decide(
        self,
        *,
        binding: DexBindingIdentity,
        claim_view: ClaimView,
    ) -> AdmissionRecord:
        """Decide (or replay) one admission. Denied decisions raise
        AdmissionDenied on every call, including replays."""
        if not isinstance(binding, DexBindingIdentity):
            raise ValueError("binding must be a DexBindingIdentity")
        if not isinstance(claim_view, ClaimView):
            raise ValueError("claim_view must be a ClaimView")

        digest = binding_digest(binding)
        key = (binding.execution_id, binding.attempt_id)
        existing = self._records.get(key)
        if existing is None and self._journal is not None:
            # Fail-closed durable replay: an unreadable journal propagates
            # (never becomes a fresh decision); a journaled decision is
            # cached and replayed with the in-process semantics.
            existing = self._journal.load(*key)
            if existing is not None:
                self._records[key] = existing
        if existing is not None:
            # Replay: the identity is already decided. The presented
            # binding/claim must match the frozen decision exactly.
            if existing.binding_digest != digest or existing.claim_ref != binding.claim_ref:
                raise AdmissionDenied(
                    DENIED_IDENTITY_MISMATCH,
                    "admission replay binding does not match the frozen decision",
                )
            if existing.claim_generation != claim_view.claim_generation:
                raise AdmissionDenied(
                    DENIED_IDENTITY_MISMATCH,
                    "admission replay claim generation differs from the frozen decision",
                )
            if not existing.admitted:
                raise AdmissionDenied(
                    existing.code or DENIED_IDENTITY_MISMATCH,
                    existing.detail or "identity was previously denied",
                )
            return existing

        record = self._decide_fresh(binding=binding, claim_view=claim_view, digest=digest)
        if self._journal is not None:
            # Journaled BEFORE being cached/returned: a crash between
            # journal-write and return still leaves the decision durable.
            # A journal conflict (concurrent deciding process with a
            # different outcome) propagates typed — fail closed.
            self._journal.record(record)
        self._records[key] = record
        if not record.admitted:
            raise AdmissionDenied(record.code or DENIED_IDENTITY_MISMATCH, record.detail or "")
        return record

    def lookup(self, execution_id: str, attempt_id: str) -> AdmissionRecord | None:
        return self._records.get((execution_id, attempt_id))

    def _decide_fresh(
        self,
        *,
        binding: DexBindingIdentity,
        claim_view: ClaimView,
        digest: str,
    ) -> AdmissionRecord:
        if not claim_view.live:
            return self._denial(
                binding, claim_view, digest, DENIED_NOT_LIVE, f"claim {claim_view.claim_ref} is not live"
            )
        if claim_view.claim_ref != binding.claim_ref:
            return self._denial(
                binding,
                claim_view,
                digest,
                DENIED_IDENTITY_MISMATCH,
                "claim view does not match the binding claim_ref",
            )
        if claim_view.claim_generation != binding.claim_generation:
            return self._denial(
                binding,
                claim_view,
                digest,
                DENIED_STALE_CLAIM,
                f"binding generation {binding.claim_generation} != live generation {claim_view.claim_generation}",
            )
        return AdmissionRecord(
            execution_id=binding.execution_id,
            attempt_id=binding.attempt_id,
            binding_digest=digest,
            claim_ref=binding.claim_ref,
            claim_generation=claim_view.claim_generation,
            admitted=True,
        )

    @staticmethod
    def _denial(
        binding: DexBindingIdentity,
        claim_view: ClaimView,
        digest: str,
        code: str,
        detail: str,
    ) -> AdmissionRecord:
        return AdmissionRecord(
            execution_id=binding.execution_id,
            attempt_id=binding.attempt_id,
            binding_digest=digest,
            claim_ref=binding.claim_ref,
            claim_generation=claim_view.claim_generation,
            admitted=False,
            code=code,
            detail=detail,
        )
