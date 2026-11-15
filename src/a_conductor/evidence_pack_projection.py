"""Evidence packing projection (WO-P1-759, SFU26 card 07).

Pure, deterministic packer of injected retrieval evidence into a bounded,
self-digested ``EvidencePack``. Canonical retrieval results arrive as
injected data (snapshot-or-loader per the card-08/09 pattern); this module
performs NO retrieval I/O, no clock/network/store access, and never imports
a provider/semantic/typesafe module. Budgets are char/item/byte ONLY — this
module does not measure tokens and never fabricates a remaining-context
percentage (context_rollover_guard prohibition).

Documented design decisions:

- **Span**: ``EvidenceSpan(start, end)`` — byte offsets into the referenced
  artifact, ``end`` exclusive, invariant ``0 <= start <= end``. Spans are
  typed locally (no shared span type exists in AWC); inputs may supply an
  ``EvidenceSpan``, a 2-tuple, or a ``{"start", "end"}`` dict.
- **Budgets**: char/item/byte only, injectable ``EvidenceBudget`` with
  documented defaults ``DEFAULT_EVIDENCE_BUDGET`` (chars 32768, items 16 —
  mirroring orchestration ``EVIDENCE_REF_LIMIT``, bytes 16384 — mirroring
  orchestration ``SIZE_LIMIT``). Accounting is a pre-encode walk over the
  ACTUAL UTF-8 bytes/characters of each item's content; the declared
  ``size_bytes`` is carried provenance (validated, never used for budget
  math). No token counting of any kind.
- **No partial clipping**: the mandatory subset alone over any cap
  abstains ``PACK_MANDATORY_BUDGET_EXCEEDED`` (mandatory evidence is never
  clipped); optional overflow items are dropped WHOLE with monitor-style
  dropped accounting and the invariant ``truncated == (dropped > 0)``.
- **Dedup**: identity is ``(ref, sha256, span)``; first occurrence wins,
  later occurrences are counted in ``duplicate_count`` and never
  double-packed.
- **Same-ref conflicts**: items sharing ``ref`` but differing in ``sha256``
  and/or ``span`` are BOTH retained (the pack is non-authoritative inert
  data; silent evidence loss is worse than over-retention) with typed
  ``EvidenceConflictNote`` entries (``SHA256_MISMATCH`` /
  ``SPAN_MISMATCH``). Conflicts never block packing.
- **Malformed items**: present-but-invalid values are typed-rejected per
  item with field-specific codes (bad hex, oversize/non-printable ref,
  negative/non-int size, inverted/negative span, non-string content).
  Malformed OPTIONAL items are rejected and packing proceeds; malformed
  MANDATORY items abstain ``PACK_MANDATORY_ITEM_MALFORMED`` (never
  silently dropped). An invalid ``mandatory`` flag is handled
  conservatively as mandatory-severity (abstain). Missing/unreadable
  required fields (including raising attribute access) become
  ``EVIDENCE_ITEM_UNREADABLE`` — distinct from present-but-invalid values.
- **Staleness**: carried as injected input evidence, never computed. A
  missing/invalid ``source_revision`` degrades staleness to ``UNKNOWN``
  (a staleness claim without revision evidence is not carried); an
  invalid staleness word degrades to ``UNKNOWN``.
- **Content**: inert data. It round-trips byte-exactly, is never parsed,
  interpreted, or promoted into any other field — prompt-injection-looking
  text remains opaque content text and nothing else.
- **Digest recipe** (dex pattern): ``EvidencePack.digest`` is
  ``sha256`` over canonical JSON (``sort_keys=True``,
  ``separators=(",",":")``, ``ensure_ascii=True``) of the pack body MINUS
  the digest field. ``EvidencePack.fingerprint`` is the sha256 input
  fingerprint over the canonical JSON of the normalized per-input records
  (including rejected/duplicate statuses), so any input field change
  changes it. ``EvidencePackOutcome.fingerprint`` carries those same
  normalized records readable (empty tuple when the input could not be
  normalized at all, e.g. loader failure).
- **Injection**: ``items`` accepts an item sequence, a snapshot object
  with an ``items`` sequence attribute, or a zero-argument loader callable
  returning either. Loader failures, garbage returns, unusable containers
  and ANY duck-typed attribute-access failure degrade to typed outcomes —
  never an exception escape (card-08/09 P2 lesson). ``budget`` must be an
  ``EvidenceBudget``; anything else degrades ``BUDGET_INVALID``.
- ``now`` is accepted for call-site seam parity with sibling projections;
  it is unused in v1 because staleness here is carried input evidence,
  never derived from time.
- ``non_authoritative`` is pinned ``True`` with ``init=False`` on both the
  pack and the outcome; frozen ``slots`` dataclasses throughout; imports
  limited to stdlib ``dataclasses``/``hashlib``/``json``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json

DISPOSITION_PACKED = "PACKED"
DISPOSITION_ABSTAIN = "ABSTAIN"
DISPOSITION_DEGRADED = "DEGRADED"

ABSTAIN_MANDATORY_BUDGET_EXCEEDED = "PACK_MANDATORY_BUDGET_EXCEEDED"
ABSTAIN_MANDATORY_ITEM_MALFORMED = "PACK_MANDATORY_ITEM_MALFORMED"
DEGRADED_SNAPSHOT_UNAVAILABLE = "EVIDENCE_SNAPSHOT_UNAVAILABLE"
DEGRADED_BUDGET_INVALID = "BUDGET_INVALID"

EVIDENCE_REF_INVALID = "EVIDENCE_REF_INVALID"
EVIDENCE_SHA256_INVALID = "EVIDENCE_SHA256_INVALID"
EVIDENCE_SIZE_INVALID = "EVIDENCE_SIZE_INVALID"
EVIDENCE_SPAN_INVALID = "EVIDENCE_SPAN_INVALID"
EVIDENCE_CONTENT_INVALID = "EVIDENCE_CONTENT_INVALID"
EVIDENCE_ITEM_UNREADABLE = "EVIDENCE_ITEM_UNREADABLE"
EVIDENCE_MANDATORY_FLAG_INVALID = "EVIDENCE_MANDATORY_FLAG_INVALID"

CONFLICT_SHA256_MISMATCH = "SHA256_MISMATCH"
CONFLICT_SPAN_MISMATCH = "SPAN_MISMATCH"

STALENESS_AVAILABLE = "AVAILABLE"
STALENESS_STALE = "STALE"
STALENESS_UNKNOWN = "UNKNOWN"

_SCHEMA = "evidence.pack.v1"
_REF_LIMIT = 256
_HEX_DIGITS = frozenset("0123456789abcdef")
_STALENESS_VOCABULARY = frozenset((STALENESS_AVAILABLE, STALENESS_STALE, STALENESS_UNKNOWN))
_REQUIRED_FIELDS = ("ref", "sha256", "size_bytes", "span", "content", "mandatory")


@dataclass(frozen=True, slots=True)
class EvidenceSpan:
    """Byte-offset span into the referenced artifact; ``end`` exclusive."""

    start: int
    end: int


@dataclass(frozen=True, slots=True)
class EvidenceBudget:
    """Char/item/byte caps. Token counting is out of scope by contract."""

    max_chars: int
    max_items: int
    max_bytes: int


DEFAULT_EVIDENCE_BUDGET = EvidenceBudget(max_chars=32768, max_items=16, max_bytes=16384)


@dataclass(frozen=True, slots=True)
class PackedEvidenceItem:
    """One packed evidence item; provenance preserved, content inert."""

    ref: str
    sha256: str
    size_bytes: int
    span: EvidenceSpan
    content: str
    mandatory: bool
    source_revision: str | None
    staleness: str


@dataclass(frozen=True, slots=True)
class RejectedEvidenceItem:
    """One typed per-item rejection (index into the resolved input order)."""

    index: int
    reason_code: str


@dataclass(frozen=True, slots=True)
class EvidenceConflictNote:
    """Typed same-ref identity conflict; both sides retained (retain rule)."""

    ref: str
    conflict_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidencePack:
    """Frozen non-authoritative pack; digest is over the body minus digest."""

    schema: str
    fingerprint: str
    digest: str
    items: tuple[PackedEvidenceItem, ...]
    dropped_optional_count: int
    truncated: bool
    duplicate_count: int
    conflicts: tuple[EvidenceConflictNote, ...]
    non_authoritative: bool = field(default=True, init=False)


@dataclass(frozen=True, slots=True)
class EvidencePackOutcome:
    """Typed outcome: packed, abstain, or degraded — never an exception."""

    disposition: str
    reason_code: str
    pack: EvidencePack | None
    rejected: tuple[RejectedEvidenceItem, ...]
    exceeded_caps: tuple[str, ...]
    fingerprint: tuple[dict, ...]
    non_authoritative: bool = field(default=True, init=False)


class _Missing:
    __slots__ = ()

    def __repr__(self) -> str:
        return "<missing>"


_MISSING = _Missing()


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("utf-8")


def _digest_hex(value: dict) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _field(item: object, name: str) -> object:
    """Duck-typed read; every failure mode becomes the _MISSING sentinel."""
    try:
        if type(item) is dict:
            return item.get(name, _MISSING)
        return getattr(item, name, _MISSING)
    except Exception:
        return _MISSING


def _is_int(value: object) -> bool:
    return type(value) is int  # bool is intentionally not an int here


def _valid_ref(value: object) -> bool:
    return (type(value) is str and 1 <= len(value) <= _REF_LIMIT
            and all(33 <= ord(char) <= 126 for char in value))


def _valid_sha256(value: object) -> bool:
    return (type(value) is str and len(value) == 64
            and all(char in _HEX_DIGITS for char in value))


def _normalize_span(value: object) -> EvidenceSpan | None:
    start: object = _MISSING
    end: object = _MISSING
    if type(value) is EvidenceSpan:
        start, end = value.start, value.end
    elif type(value) is tuple and len(value) == 2:
        start, end = value
    elif type(value) is dict:
        start = value.get("start", _MISSING)
        end = value.get("end", _MISSING)
    if not _is_int(start) or not _is_int(end):
        return None
    if start < 0 or end < start:
        return None
    return EvidenceSpan(start, end)


def _resolve_items(items: object) -> tuple | None:
    """Snapshot-or-loader resolution; any failure degrades to None."""
    try:
        candidate = items() if callable(items) else items
    except Exception:
        return None
    if type(candidate) in (tuple, list):
        return tuple(candidate)
    try:
        nested = getattr(candidate, "items", None)
    except Exception:
        return None
    if type(nested) in (tuple, list):
        return tuple(nested)
    return None


def _valid_budget(budget: EvidenceBudget) -> bool:
    return (_is_int(budget.max_chars) and _is_int(budget.max_items)
            and _is_int(budget.max_bytes)
            and budget.max_chars >= 0 and budget.max_items >= 0
            and budget.max_bytes >= 0)


def _fingerprint_value(value: object) -> str:
    """Bounded deterministic repr for non-normalizable input values."""
    if value is _MISSING:
        return "<missing>"
    try:
        return repr(value)[:200]
    except Exception:
        return "<unrepr>"


def _normalize_item(raw: object) -> tuple[str, str, PackedEvidenceItem | None, bool]:
    """Validate one duck-typed input item.

    Returns ``(status, code, packed_item, mandatory_severity)`` where status
    is ``"accepted"`` or ``"rejected"``. Never raises.
    """
    try:
        for name in _REQUIRED_FIELDS:
            if _field(raw, name) is _MISSING:
                return "rejected", EVIDENCE_ITEM_UNREADABLE, None, False
        mandatory = _field(raw, "mandatory")
        if type(mandatory) is not bool:
            return "rejected", EVIDENCE_MANDATORY_FLAG_INVALID, None, True
        ref = _field(raw, "ref")
        if not _valid_ref(ref):
            return "rejected", EVIDENCE_REF_INVALID, None, mandatory
        sha = _field(raw, "sha256")
        if not _valid_sha256(sha):
            return "rejected", EVIDENCE_SHA256_INVALID, None, mandatory
        size = _field(raw, "size_bytes")
        if not _is_int(size) or size < 0:
            return "rejected", EVIDENCE_SIZE_INVALID, None, mandatory
        span = _normalize_span(_field(raw, "span"))
        if span is None:
            return "rejected", EVIDENCE_SPAN_INVALID, None, mandatory
        content = _field(raw, "content")
        if type(content) is not str:
            return "rejected", EVIDENCE_CONTENT_INVALID, None, mandatory
        revision = _field(raw, "source_revision")
        if type(revision) is not str or not revision:
            revision = None
        staleness = _field(raw, "staleness")
        if type(staleness) is not str or staleness not in _STALENESS_VOCABULARY:
            staleness = STALENESS_UNKNOWN
        if revision is None:
            staleness = STALENESS_UNKNOWN
        return "accepted", "", PackedEvidenceItem(
            ref=ref, sha256=sha, size_bytes=size, span=span, content=content,
            mandatory=mandatory, source_revision=revision, staleness=staleness,
        ), False
    except Exception:
        return "rejected", EVIDENCE_ITEM_UNREADABLE, None, False


def _accepted_record(item: PackedEvidenceItem) -> dict:
    return {
        "status": "accepted",
        "ref": item.ref,
        "sha256": item.sha256,
        "size_bytes": item.size_bytes,
        "span": {"start": item.span.start, "end": item.span.end},
        "content": item.content,
        "mandatory": item.mandatory,
        "source_revision": item.source_revision,
        "staleness": item.staleness,
    }


def _rejected_record(raw: object, code: str, index: int) -> dict:
    record: dict = {"status": "rejected", "index": index, "code": code}
    for name in _REQUIRED_FIELDS + ("source_revision", "staleness"):
        record[name] = _fingerprint_value(_field(raw, name))
    return record


def _packed_value(item: PackedEvidenceItem) -> dict:
    return {
        "ref": item.ref,
        "sha256": item.sha256,
        "size_bytes": item.size_bytes,
        "span": {"start": item.span.start, "end": item.span.end},
        "content": item.content,
        "mandatory": item.mandatory,
        "source_revision": item.source_revision,
        "staleness": item.staleness,
    }


def _identity(item: PackedEvidenceItem) -> tuple[str, str, tuple[int, int]]:
    return (item.ref, item.sha256, (item.span.start, item.span.end))


def _conflict_notes(candidates: list[PackedEvidenceItem]) -> list[EvidenceConflictNote]:
    by_ref: dict[str, list[PackedEvidenceItem]] = {}
    for item in candidates:
        by_ref.setdefault(item.ref, []).append(item)
    notes: list[EvidenceConflictNote] = []
    for ref in sorted(by_ref):
        group = by_ref[ref]
        if len(group) < 2:
            continue
        codes: list[str] = []
        if len({item.sha256 for item in group}) > 1:
            codes.append(CONFLICT_SHA256_MISMATCH)
        if len({_identity(item)[2] for item in group}) > 1:
            codes.append(CONFLICT_SPAN_MISMATCH)
        if codes:
            notes.append(EvidenceConflictNote(ref=ref, conflict_codes=tuple(codes)))
    return notes


def project_evidence_pack(
    items: object,
    *,
    budget: object = None,
    now: object = None,
) -> EvidencePackOutcome:
    """Pack injected evidence items into a bounded self-digested pack.

    ``items`` is an item sequence, a snapshot object exposing an ``items``
    sequence, or a zero-argument loader callable returning either. Loader
    and attribute failures degrade to typed outcomes. ``budget`` defaults
    to ``DEFAULT_EVIDENCE_BUDGET``; ``now`` is accepted for seam parity and
    intentionally unused (staleness is carried input evidence).
    """
    resolved = _resolve_items(items)
    if resolved is None:
        return EvidencePackOutcome(
            disposition=DISPOSITION_DEGRADED,
            reason_code=DEGRADED_SNAPSHOT_UNAVAILABLE,
            pack=None, rejected=(), exceeded_caps=(), fingerprint=(),
        )
    selected = budget if budget is not None else DEFAULT_EVIDENCE_BUDGET
    if type(selected) is not EvidenceBudget or not _valid_budget(selected):
        return EvidencePackOutcome(
            disposition=DISPOSITION_DEGRADED,
            reason_code=DEGRADED_BUDGET_INVALID,
            pack=None, rejected=(), exceeded_caps=(), fingerprint=(),
        )

    records: list[dict] = []
    accepted: list[PackedEvidenceItem] = []
    rejected: list[RejectedEvidenceItem] = []
    mandatory_block = False
    for index, raw in enumerate(resolved):
        status, code, packed, severity = _normalize_item(raw)
        if status == "accepted":
            records.append(_accepted_record(packed))
            accepted.append(packed)
        else:
            records.append(_rejected_record(raw, code, index))
            rejected.append(RejectedEvidenceItem(index=index, reason_code=code))
            if severity:
                mandatory_block = True
    if mandatory_block:
        return EvidencePackOutcome(
            disposition=DISPOSITION_ABSTAIN,
            reason_code=ABSTAIN_MANDATORY_ITEM_MALFORMED,
            pack=None, rejected=tuple(rejected), exceeded_caps=(),
            fingerprint=tuple(records),
        )

    accepted_positions = [position for position, record in enumerate(records)
                          if record["status"] == "accepted"]
    seen: set[tuple[str, str, tuple[int, int]]] = set()
    candidates: list[PackedEvidenceItem] = []
    duplicate_count = 0
    for position, item in zip(accepted_positions, accepted):
        identity = _identity(item)
        if identity in seen:
            duplicate_count += 1
            records[position]["status"] = "duplicate"
            continue
        seen.add(identity)
        candidates.append(item)

    fingerprint_records = tuple(records)
    fingerprint = _digest_hex({"items": fingerprint_records})

    mandatory_items = [item for item in candidates if item.mandatory]
    used_chars = sum(len(item.content) for item in mandatory_items)
    used_bytes = sum(len(item.content.encode("utf-8")) for item in mandatory_items)
    exceeded: list[str] = []
    if used_chars > selected.max_chars:
        exceeded.append("chars")
    if len(mandatory_items) > selected.max_items:
        exceeded.append("items")
    if used_bytes > selected.max_bytes:
        exceeded.append("bytes")
    if exceeded:
        return EvidencePackOutcome(
            disposition=DISPOSITION_ABSTAIN,
            reason_code=ABSTAIN_MANDATORY_BUDGET_EXCEEDED,
            pack=None, rejected=tuple(rejected),
            exceeded_caps=tuple(sorted(exceeded)),
            fingerprint=fingerprint_records,
        )

    packed_items: list[PackedEvidenceItem] = []
    dropped_optional_count = 0
    for item in candidates:
        item_chars = len(item.content)
        item_bytes = len(item.content.encode("utf-8"))
        if not item.mandatory and (
            len(packed_items) + 1 > selected.max_items
            or used_chars + item_chars > selected.max_chars
            or used_bytes + item_bytes > selected.max_bytes
        ):
            dropped_optional_count += 1
            continue
        packed_items.append(item)
        used_chars += item_chars
        used_bytes += item_bytes
    truncated = dropped_optional_count > 0

    conflicts = _conflict_notes(candidates)
    body = {
        "schema": _SCHEMA,
        "items": [_packed_value(item) for item in packed_items],
        "dropped_optional_count": dropped_optional_count,
        "truncated": truncated,
        "duplicate_count": duplicate_count,
        "conflicts": [{"ref": note.ref, "codes": list(note.conflict_codes)}
                      for note in conflicts],
    }
    pack = EvidencePack(
        schema=_SCHEMA,
        fingerprint=fingerprint,
        digest=_digest_hex(body),
        items=tuple(packed_items),
        dropped_optional_count=dropped_optional_count,
        truncated=truncated,
        duplicate_count=duplicate_count,
        conflicts=tuple(conflicts),
    )
    return EvidencePackOutcome(
        disposition=DISPOSITION_PACKED,
        reason_code="",
        pack=pack,
        rejected=tuple(rejected),
        exceeded_caps=(),
        fingerprint=fingerprint_records,
    )
