"""WO-P1-246 — durable author-attempt provenance seam (design §3.5/§3.6/§3.3a).

This module is the single home for:

- the proof-carrying ``AuthorProvenanceBinding`` value type (no public
  construction path — only the classification factory over durable evidence
  can produce it);
- the opaque author attempt-id mint used by ``SupervisedRunCoordinator`` in
  its ``SAFE_TO_LAUNCH`` branch (format ``author-attempt-v1:<uuid4 hex>``);
- the classification entry invoked only by the trusted ZCode assembly seam
  (generation 0 for verified original packets; the ``zra2-repair-`` family
  enters the repair-proof path and NEVER silently downgrades to generation
  0 — it fails closed because the durable Phase-D rejected-review lineage
  predecessor does not exist at this base);
- the generation-1 lineage reconstruction home (§3.3a), structurally blocked
  until that predecessor exists under its own scope;
- the exact-record ``ResultIdentity`` composition seam (§3.5), which never
  looks up provenance by fingerprint and never mints anything.

It adds no store, scheduler, query authority, retry engine, review
lifecycle, provider authority, or completion state machine.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from .execution_record import DurableExecutionRecord
from .zero_relay import ResultIdentity


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_AUTHOR_ATTEMPT_RE = re.compile(r"^author-attempt-v1:[0-9a-f]{32}$")
_REASON_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_MAX_TEXT = 1024
REPAIR_FAMILY_PREFIX = "zra2-repair-"
_REPAIR_V1_GRAMMAR_RE = re.compile(r"^zra2-repair-v1:[0-9a-f]{64}$")


class AuthorProvenanceError(RuntimeError):
    """Stable code-only provenance failure; never echoes input text."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _identity_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise AuthorProvenanceError("PROVENANCE_INPUT_INVALID")
    if len(value) > _MAX_TEXT:
        raise AuthorProvenanceError("PROVENANCE_INPUT_INVALID")
    if "\x00" in value or "\r" in value or "\n" in value:
        raise AuthorProvenanceError("PROVENANCE_INPUT_INVALID")
    return value


def _sha256_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise AuthorProvenanceError("PROVENANCE_INPUT_INVALID")
    return value


class _ConstructionTicket:
    """Module-private construction authority for ``AuthorProvenanceBinding``."""


_CONSTRUCTION_TICKET = _ConstructionTicket()


@dataclass(frozen=True, slots=True, init=False)
class AuthorProvenanceBinding:
    """Proof-carrying author provenance produced ONLY by classification.

    Carries deliberately NO attempt id: the attempt id is minted by the
    coordinator after ``SAFE_TO_LAUNCH``. Generation-1 bindings additionally
    carry the re-derived lineage proof; generation 0 carries ``None``
    lineage fields.
    """

    author_generation: int
    task_contract_ref: str
    task_packet_sha256: str
    rejected_execution_id: str | None
    rejected_task_sha256: str | None
    rejected_result_sha256: str | None
    review_reason_id: str | None
    repair_packet_sha256: str | None

    def __init__(
        self,
        _ticket: object = None,
        /,
        *,
        author_generation: int,
        task_contract_ref: str,
        task_packet_sha256: str,
        rejected_execution_id: str | None = None,
        rejected_task_sha256: str | None = None,
        rejected_result_sha256: str | None = None,
        review_reason_id: str | None = None,
        repair_packet_sha256: str | None = None,
    ) -> None:
        if _ticket is not _CONSTRUCTION_TICKET:
            raise AuthorProvenanceError(
                "AUTHOR_PROVENANCE_BINDING_CONSTRUCTION_FORBIDDEN"
            )
        if (
            isinstance(author_generation, bool)
            or not isinstance(author_generation, int)
            or author_generation not in (0, 1)
        ):
            raise AuthorProvenanceError("PROVENANCE_GENERATION_INVALID")
        contract = _identity_text(task_contract_ref, "task_contract_ref")
        packet_sha = _sha256_text(task_packet_sha256, "task_packet_sha256")
        set_fields = {
            name: value
            for name, value in (
                ("rejected_execution_id", rejected_execution_id),
                ("rejected_task_sha256", rejected_task_sha256),
                ("rejected_result_sha256", rejected_result_sha256),
                ("review_reason_id", review_reason_id),
                ("repair_packet_sha256", repair_packet_sha256),
            )
            if value is not None
        }
        if author_generation == 0 and set_fields:
            raise AuthorProvenanceError("PROVENANCE_LINEAGE_FORBIDDEN_FOR_GEN0")
        if author_generation == 1 and len(set_fields) != 5:
            raise AuthorProvenanceError("PROVENANCE_LINEAGE_INCOMPLETE")
        object.__setattr__(self, "author_generation", author_generation)
        object.__setattr__(self, "task_contract_ref", contract)
        object.__setattr__(self, "task_packet_sha256", packet_sha)
        if author_generation == 1:
            _identity_text(rejected_execution_id, "rejected_execution_id")
            _sha256_text(rejected_task_sha256, "rejected_task_sha256")
            _sha256_text(rejected_result_sha256, "rejected_result_sha256")
            if not isinstance(
                review_reason_id, str
            ) or not _REASON_ID_RE.fullmatch(review_reason_id):
                raise AuthorProvenanceError("PROVENANCE_INPUT_INVALID")
            _sha256_text(repair_packet_sha256, "repair_packet_sha256")
        object.__setattr__(self, "rejected_execution_id", rejected_execution_id)
        object.__setattr__(self, "rejected_task_sha256", rejected_task_sha256)
        object.__setattr__(self, "rejected_result_sha256", rejected_result_sha256)
        object.__setattr__(self, "review_reason_id", review_reason_id)
        object.__setattr__(self, "repair_packet_sha256", repair_packet_sha256)


def mint_author_attempt_id() -> str:
    """Mint one opaque author attempt id (``author-attempt-v1:<uuid4 hex>``).

    No caller may provide or override the token; it is minted only by the
    coordinator's ``SAFE_TO_LAUNCH`` new-record branch.
    """
    return f"author-attempt-v1:{uuid.uuid4().hex}"


def is_valid_author_attempt_id(value: object) -> bool:
    """Exact minted-token grammar check (opaque; format is load-bearing)."""
    return isinstance(value, str) and bool(_AUTHOR_ATTEMPT_RE.fullmatch(value))


def is_repair_family_contract_ref(task_contract_ref: str) -> bool:
    """Broad reserved-family detection: ANY ref beginning ``zra2-repair-``
    enters the repair-proof path (never a silent generation-0 downgrade)."""
    return isinstance(task_contract_ref, str) and task_contract_ref.startswith(
        REPAIR_FAMILY_PREFIX
    )


def bind_original_author_provenance(
    *,
    task_contract_ref: str,
    task_packet_sha256: str,
) -> AuthorProvenanceBinding:
    """Factory for a generation-0 binding over the VERIFIED original packet.

    Re-runs the §3.3 verification available at this seam: the exact verified
    packet digest and the fact that the contract does NOT claim the reserved
    repair family (a prefix grammar match alone classifies nothing).
    """
    contract = _identity_text(task_contract_ref, "task_contract_ref")
    packet_sha = _sha256_text(task_packet_sha256, "task_packet_sha256")
    if is_repair_family_contract_ref(contract):
        raise AuthorProvenanceError("REPAIR_CONTRACT_UNSUPPORTED")
    return AuthorProvenanceBinding(
        _CONSTRUCTION_TICKET,
        author_generation=0,
        task_contract_ref=contract,
        task_packet_sha256=packet_sha,
    )


def derive_generation1_repair_binding(
    *,
    rejected_execution_id: str,
) -> AuthorProvenanceBinding:
    """§3.3a lineage reconstruction home — BLOCKED at this base.

    The complete durable predecessor (a rejected-review linkage persisted by
    the accepted review lifecycle and re-readable through existing
    store/artifact APIs) does not exist in the current source. Every call
    fails closed BEFORE launch; no caller fact is ever accepted as lineage
    authority. When the predecessor exists under its own scope this seam
    must re-read the rejected execution via ``ExecutionStore.get()``,
    re-read and re-hash every referenced persisted artifact, re-resolve the
    exact reviewer execution only from durable accepted review linkage, and
    require exact equality with the packet being launched.
    """
    _identity_text(rejected_execution_id, "rejected_execution_id")
    raise AuthorProvenanceError("REPAIR_LINEAGE_UNAVAILABLE")


def classify_author_provenance(
    *,
    task_contract_ref: str,
    packet_sha256: str,
) -> AuthorProvenanceBinding:
    """Single classification entry for the trusted ZCode assembly seam.

    - generation 0: verified original author packet (non-repair-family);
    - any ``zra2-repair-`` family contract: grammar gate, then the §3.3a
      repair-proof path, which is structurally unavailable at this base —
      ``REPAIR_LINEAGE_UNAVAILABLE`` / ``REPAIR_CONTRACT_UNSUPPORTED`` fail
      closed; NEVER a silent downgrade to generation 0.

    Caller integers, prefixes, hashes, verdicts, findings, or prebuilt
    repair requests are never authority.
    """
    contract = _identity_text(task_contract_ref, "task_contract_ref")
    packet_sha = _sha256_text(packet_sha256, "packet_sha256")
    if is_repair_family_contract_ref(contract):
        if not _REPAIR_V1_GRAMMAR_RE.fullmatch(contract):
            raise AuthorProvenanceError("REPAIR_CONTRACT_UNSUPPORTED")
        # exact v1 grammar: only the recomputed durable lineage of §3.3a
        # (derive_generation1_repair_binding) can authorize generation 1 —
        # structurally unavailable at this base, fail closed before launch
        raise AuthorProvenanceError("REPAIR_LINEAGE_UNAVAILABLE")
    return bind_original_author_provenance(
        task_contract_ref=contract,
        task_packet_sha256=packet_sha,
    )


def compose_result_identity(
    *,
    record: DurableExecutionRecord,
    task_contract_ref: str,
    task_sha256: str,
    result_ref: str,
    result_sha256: str,
) -> ResultIdentity:
    """Exact-record composition (§3.5): identity, not acceptance.

    Requires present valid author provenance on the exact record,
    cross-binds the supplied task contract ref to ``record.work_order_ref``
    and the supplied result ref to ``record.result_ref``, consumes
    already-computed exact SHA-256 values, and returns the downstream
    ``ResultIdentity``. Never looks up provenance by fingerprint; never
    mints anything. Legacy/foreign/unprovenanced rows fail with the stable
    typed ``AUTHOR_PROVENANCE_UNKNOWN``; binding mismatches fail with the
    distinct typed identity-mismatch error.
    """
    if not isinstance(record, DurableExecutionRecord):
        raise AuthorProvenanceError("AUTHOR_PROVENANCE_UNKNOWN")
    if (
        record.author_attempt_id is None
        or record.author_generation is None
        or not is_valid_author_attempt_id(record.author_attempt_id)
    ):
        raise AuthorProvenanceError("AUTHOR_PROVENANCE_UNKNOWN")
    contract = _identity_text(task_contract_ref, "task_contract_ref")
    result = _identity_text(result_ref, "result_ref")
    if contract != record.work_order_ref or result != record.result_ref:
        raise AuthorProvenanceError("AUTHOR_PROVENANCE_IDENTITY_MISMATCH")
    try:
        return ResultIdentity(
            task_contract_ref=contract,
            task_sha256=task_sha256,
            result_ref=result,
            result_sha256=result_sha256,
            attempt_id=record.author_attempt_id,
            generation=record.author_generation,
            author_execution_id=record.execution_id,
        )
    except (TypeError, ValueError) as exc:
        raise AuthorProvenanceError("PROVENANCE_INPUT_INVALID") from exc
