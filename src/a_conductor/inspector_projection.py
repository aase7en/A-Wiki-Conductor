"""WO-P1-739: pure offline read-only inspector projection (no I/O, no clock).

Projects caller-injected EVIDENCE into a sanitized, read-only inspector
view. Evidence arrives as DATA through three injected ports (plain mappings
or dataclass instances); this module performs no live reads, no collection,
no network, and imports nothing outside the standard library.

Ports (fixture-ownable)
-----------------------
registry snapshot port: ``{"present": bool, "missing": bool, "items": [...]}``
  item: ``{"item_id": str, "kind": "hook"|"tool", "route": str?, "source":
  str?, "revision": str?, "observed_at": iso8601?}`` — registration/routing
  facts only. An explicit ``missing`` truthy flag (or ``present is False``)
  declares the registry authority absent.

hook evidence port: ``{"items": [...], "bus": {...}?}``
  item: ``{"item_id": str, "classification": "hard"|"soft"?, "available":
  bool?, "observed_at": iso8601?, "source": str?, "revision": str?,
  "observation_id": str?}``. ``classification`` is validated against the
  A-Wiki hard/soft vocabulary (anything else is typed-rejected) and then
  surfaced verbatim within it — it is never remapped to OBSERVE/GUARD.
  ``bus``: ``{"backpressure": bool, "conditions": [str]?, "observed_at"?,
  "source"?}`` — bus-LEVEL evidence only.

tool evidence port: ``{"items": [...]}``
  item: ``{"item_id": str, "device_connection": str?, "available": bool?,
  "observed_at": iso8601?, "source": str?, "revision": str?,
  "observation_id": str?}``. ``device_connection == "disconnected"`` is
  explicit disconnection evidence.

Input contract (fail-closed caps)
---------------------------------
Each port's ``items`` list is capped at ``MAX_ITEMS_PER_PORT`` (256)
records. Callers MUST bound their own input: a port handing more than the
cap is a typed ``InspectorProjectionError``
(``INSPECTOR_PROJECTION_INPUT_OVERSIZED_*``) — records are never silently
truncated, because dropping the head could silently discard conflicting
evidence (e.g. one unavailable record behind 256 identical available ones).

Identity normalization (source / revision, registration + evidence)
--------------------------------------------------------------------
Identity fields are type-validated, whitespace-STRIPPED, and compared as
COMPLETE values (never truncated) for correlation, registration-conflict
comparison, and dedup signatures. A value that is blank after strip
(e.g. ``" "``) counts as absent: a registration whose source or revision is
blank fails the READY provenance gate (``provenance-missing``). ``MAX_VALUE``
(128) truncation applies only to emitted display strings, after all
comparisons.

Truth rules (WO-P1-739 §2)
--------------------------
- Registration/routing facts stay separate from health; facts never imply
  state.
- Per-item health is NEVER inferred from bus-level signals. Bus backpressure
  marks only the BUS view DEGRADED; individual hooks are unaffected by it.
- Bus freshness is evaluated BEFORE backpressure: bus evidence older than
  ``max_age_seconds`` is STALE regardless of any backpressure flag.
- Missing, stale, or disconnected evidence NEVER implies healthy.

Five-state contract (the ONLY places each state is emitted)
----------------------------------------------------------
Per-item state precedence (first match wins; every non-final outcome keeps
a machine reason):

1. duplicate/conflicting evidence records for one item+source
   (e.g. one startup reported twice with different observation ids)
   -> UNKNOWN ``duplicate-startup`` / ``conflicting-evidence``; no record is
   arbitrarily picked. The dedup/conflict signature covers EVERY identity
   and report fact — source, revision, observation id, availability,
   device connection, classification, observed time — so records agreeing
   except for the revision are CONFLICTING evidence, never deduplicated
   (order-independent; differing revision = conflicting evidence -> UNKNOWN
   ``conflicting-evidence``). Records whose ``classification`` values
   disagree -> UNKNOWN ``conflicting-classification`` with the
   ``classification`` fact suppressed (never picked from the first record).
2. registry declared missing -> UNKNOWN ``missing-registry``.
3. item absent from the (present) registry -> UNKNOWN
   ``absent-registration``; evidence alone never yields READY.
4. explicit ``device_connection == "disconnected"`` -> DISCONNECTED
   ``disconnected-device``; ``available`` cannot override this.
5. no evidence record at all -> UNKNOWN ``no-evidence`` (registration
   provenance is still emitted: source + observed-at of the registration).
6. evidence ``observed_at`` in the future of ``now`` (negative age) ->
   UNKNOWN ``freshness-invalid`` (an observation from the future is never
   treated as fresh). Unparseable or absent ``observed_at`` -> UNKNOWN
   ``freshness-unobserved`` (freshness is never guessed). Evidence older
   than ``max_age_seconds`` -> STALE ``stale-evidence``.
7. ``available is True`` may yield READY ``ready-evidence`` ONLY when ALL
   of the following hold (else UNKNOWN + the named reason, availability
   stays ``asserted`` because the record asserts it):
   - registration record carries a non-empty source identity AND a pinned
     revision (non-blank after whitespace strip) -> else ``provenance-missing``;
   - registration observation is parseable and within ``max_age_seconds``
     (not future-dated) -> else ``registration-stale``;
   - the evidence record's source identity AND revision both match the
     registration record's COMPLETE (pre-truncation), whitespace-stripped
     identity values exactly (explicit correlation, not item_id-only
     joining; ``MAX_VALUE`` truncation is display-only and applied after
     comparison) -> else ``evidence-uncorrelated``;
   - the evidence record's port domain matches the registration kind
     (hook evidence justifies hook items only, tool evidence tool items) ->
     else ``domain-mismatch``.
   ``available is False`` -> UNKNOWN ``availability-false``. Assertion
   absent -> UNKNOWN ``availability-not-asserted``.

Hook domain: states 1-7 apply; ``classification`` is carried verbatim in
facts regardless of state (suppressed on classification conflict). Tool
domain: states 1-7 apply with ``device_connection`` evidence. Registry-only
items (no evidence): UNKNOWN ``no-evidence`` only. Bus domain: a bus
mapping whose observation time is absent or unparseable has no provable
freshness, so its view is UNKNOWN ``bus-freshness-unobserved`` regardless
of any backpressure flag. Otherwise the view is STALE iff bus evidence is
older than ``max_age_seconds`` (``bus-evidence-stale``) or future-dated
(``bus-freshness-invalid``) — checked BEFORE backpressure; then DEGRADED
iff ``backpressure`` evidence is True (``bus-backpressure``); otherwise
UNKNOWN (``no-bus-evidence`` / ``bus-no-backpressure``). The bus
view is never READY or DISCONNECTED, and bus state never leaks into items.

Output safety (WO-P1-739 §3)
----------------------------
- Emitted shape is a strict allowlist: ``InspectorView`` /
  ``InspectorItem`` / ``InspectorBusView`` fields and the facts keys
  ``{"kind", "route", "classification"}``. Unrecognized input fields are
  dropped, never passed through.
- Redaction strategy (fail-closed, applied to every emitted free-text
  string — item ids, facts, reasons, source metadata, observation times,
  bus conditions):
  (a) field-name heuristic: field names containing key/token/secret/
      password/credential (case-insensitive) redact the WHOLE value;
  (b) embedded-credential segment scrubber: in ANY value string, segments
      ``<name>=`` where the name contains key/token/secret/password/
      credential (e.g. ``password=abcd1234``, ``label?token=abc123``) and
      ``Bearer <run>`` have the credential run replaced with ``[REDACTED]``
      (the surrounding label text survives). Detection is fail-closed for
      confusables: a COPY of the value is NFKC-normalized and confusable-
      folded (Cyrillic/Greek homoglyphs, e.g. ``tоken=`` with Cyrillic ``о``
      or ``Bеarer`` with Cyrillic ``е``; NFKC folds fullwidth forms like
      ``＝``) before marker detection. When a segment fires ONLY on the
      folded copy, the WHOLE original value is redacted — confusable text
      is never surgically edited or passed through verbatim;
  (c) high-entropy token-shaped runs (>= 24 chars mixing >= 3 character
      classes) redact the WHOLE value;
  (d) a caller-supplied ``secret_predicate`` COMPOSES with the default
      strategy (default OR custom): a firing custom predicate redacts the
      whole value, and the default strategy still applies to values the
      custom predicate passes.
- Constant-safe fields (documented exceptions, NOT routed through the
  redactor): ``domain`` is always the validated vocabulary value
  ``hook``/``tool``, and ``availability`` is always one of
  ``asserted``/``not-asserted``/``unavailable``/``absent``. Every other
  emitted string passes through the strategy above.
- Determinism: ``now`` is injected (no clock read); identical inputs yield
  an identical view, and inputs are never mutated.

Malformed structure (non-mapping ports, missing ``item_id``, non-bool
``available``, non-str ``observed_at``, non hard/soft ``classification``,
oversized port item lists, unknown ``kind``, bad ``now`` /
``max_age_seconds``) is typed-rejected via ``InspectorProjectionError`` —
never fabricated into a view.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

__all__ = [
    "InspectorProjectionError",
    "InspectorItem",
    "InspectorBusView",
    "InspectorView",
    "build_inspector_view",
    "default_secret_predicate",
]

DEFAULT_MAX_AGE_SECONDS = 900
MAX_ITEMS_PER_PORT = 256
MAX_BUS_CONDITIONS = 16
MAX_ITEM_ID = 64
MAX_VALUE = 128
REDACTED = "[REDACTED]"

READY = "READY"
UNKNOWN = "UNKNOWN"
STALE = "STALE"
DISCONNECTED = "DISCONNECTED"
DEGRADED = "DEGRADED"

_FACT_KEYS = ("kind", "route", "classification")
_AVAILABILITY_ASSERTED = "asserted"
_AVAILABILITY_NOT_ASSERTED = "not-asserted"
_AVAILABILITY_UNAVAILABLE = "unavailable"
_AVAILABILITY_ABSENT = "absent"

_SECRET_FIELD_MARKERS = ("key", "token", "secret", "password", "credential")
_TOKEN_RUN_MIN = 24
_CREDENTIAL_SEGMENT_RE = re.compile(
    r"(?i)(?P<prefix>(?:api[_-]?|access[_-]?|auth[_-]?|client[_-]?|private[_-]?)?"
    r"(?:key|token|secret|password|passwd|pwd|credential)[a-z0-9_\-]*\s*=\s*)"
    r"(?P<run>[^\s&]+)"
)
_BEARER_SEGMENT_RE = re.compile(r"(?i)(?P<prefix>\bbearer\s+)(?P<run>[^\s]+)")

# Fail-closed confusable folding for marker DETECTION (G2): NFKC already
# folds compatibility forms (fullwidth ``＝`` -> ``=``); the table folds
# cross-script homoglyphs that the ASCII markers would otherwise miss.
# Detection runs on a folded COPY of the value; the ORIGINAL is never
# surgically edited when only the folded copy matches — it is redacted
# wholesale instead, because confusable offsets cannot be mapped back
# to the original reliably.
_CONFUSABLE_FOLDS = {
    # Cyrillic homoglyphs of the Latin letters used in the markers
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y",
    "к": "k", "м": "m", "н": "h", "т": "t", "в": "b", "і": "i", "ѕ": "s",
    "һ": "h", "А": "a", "Е": "e", "О": "o", "Р": "p", "С": "c", "Х": "x",
    "У": "y", "К": "k", "М": "m", "Н": "h", "Т": "t", "В": "b", "І": "i",
    # Greek homoglyphs
    "α": "a", "ε": "e", "ο": "o", "ρ": "p", "σ": "c", "ς": "c", "τ": "t",
    "κ": "k", "Α": "a", "Ε": "e", "Ο": "o", "Ρ": "p", "Σ": "c", "Τ": "t",
    "Κ": "k",
}
_CONFUSABLE_FOLD_TABLE = str.maketrans(_CONFUSABLE_FOLDS)


def _detection_copy(value: str) -> str:
    """NFKC + confusable-folded COPY of ``value`` for marker detection only."""
    normalized = unicodedata.normalize("NFKC", value)
    return normalized.translate(_CONFUSABLE_FOLD_TABLE)


class InspectorProjectionError(ValueError):
    """Typed rejection of malformed projection input; never fabricated views."""


def _field_name_is_secret_shaped(field_name: str) -> bool:
    # H3: the heuristic folds the field NAME through the same NFKC +
    # confusable-fold infrastructure used for values, so a confusable marker
    # name (``tоken`` with Cyrillic о, fullwidth ``Ｓecret``) is detected too.
    lowered = _detection_copy(field_name).lower()
    return any(marker in lowered for marker in _SECRET_FIELD_MARKERS)


def _has_high_entropy_run(value: str) -> bool:
    run: list[str] = []
    for char in value:
        if char.isalnum() or char in "_-+=":
            run.append(char)
            continue
        if _run_is_secret(run):
            return True
        run = []
    return _run_is_secret(run)


def _run_is_secret(run: list[str]) -> bool:
    if len(run) < _TOKEN_RUN_MIN:
        return False
    classes = 0
    if any(c.isdigit() for c in run):
        classes += 1
    if any(c.islower() for c in run):
        classes += 1
    if any(c.isupper() for c in run):
        classes += 1
    if any(not c.isalnum() for c in run):
        classes += 1
    return classes >= 3


def _has_credential_segment(value: str) -> bool:
    return bool(
        _CREDENTIAL_SEGMENT_RE.search(value) or _BEARER_SEGMENT_RE.search(value)
    )


def _scrub_credential_segments(value: str) -> str:
    value = _CREDENTIAL_SEGMENT_RE.sub(lambda m: m.group("prefix") + REDACTED, value)
    return _BEARER_SEGMENT_RE.sub(lambda m: m.group("prefix") + REDACTED, value)


def _segment_match_count(value: str) -> int:
    """Number of fired credential segments on one detection copy."""
    return len(_CREDENTIAL_SEGMENT_RE.findall(value)) + len(
        _BEARER_SEGMENT_RE.findall(value)
    )


def _compose_segment_redaction(value: str) -> str:
    """H1: scan BOTH detection copies before any return and COMPOSE them.

    The ASCII original and the NFKC + confusable-folded detection copy are
    both scanned. Pure-ASCII-fired segments are surgically scrubbed. A
    segment that fires ONLY on the folded copy cannot be mapped back to
    original offsets, so its presence (folded count != ASCII count, since
    every ASCII-fired segment's image always fires on the folded copy)
    redacts the WHOLE original value — confusable text is never surgically
    edited or passed through verbatim. Neither scan may early-return before
    the other completes.
    """
    ascii_segments = _segment_match_count(value)
    folded_segments = _segment_match_count(_detection_copy(value))
    if folded_segments and folded_segments != ascii_segments:
        return REDACTED
    return _scrub_credential_segments(value)


def default_secret_predicate(field_name: str, value: str) -> bool:
    """Default redaction detection surface (composed into the strategy).

    True when the field name is secret-shaped (key/token/secret/password/
    credential substrings, case-insensitive), the value carries an embedded
    credential segment (``key=``/``token=``/``secret=``/``password=``/
    ``Bearer <run>`` in any value string), the value carries such a segment
    ONLY after NFKC + confusable folding (fail-closed: Cyrillic/Greek/full-
    width lookalikes of the marker keywords, e.g. ``tоken=`` with Cyrillic
    ``о``, are treated as credentials), or the value contains a high-entropy
    token-shaped run (>= 24 chars mixing >= 3 character classes). Timestamps,
    routes and dotted identities do not match.
    """
    if _field_name_is_secret_shaped(field_name):
        return True
    if _has_credential_segment(value):
        return True
    if _has_credential_segment(_detection_copy(value)):
        return True
    return _has_high_entropy_run(value)


@dataclass(frozen=True)
class InspectorItem:
    """Allowlisted per-item projection (facts, provenance, explicit state)."""

    item_id: str
    domain: str
    state: str
    reason: str
    facts: dict[str, str]
    source: str | None
    observed_at: str | None
    availability: str


@dataclass(frozen=True)
class InspectorBusView:
    """Bus-LEVEL view only; never a per-hook health source."""

    state: str
    reason: str
    degraded: bool
    conditions: tuple[str, ...]
    observed_at: str | None
    source: str | None


@dataclass(frozen=True)
class InspectorView:
    """Allowlisted inspector projection output."""

    items: tuple[InspectorItem, ...]
    hook_bus: InspectorBusView
    registry_missing: bool


def _as_port(obj: object, what: str) -> dict[str, Any]:
    if isinstance(obj, Mapping):
        return dict(obj)
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    raise InspectorProjectionError(f"INSPECTOR_PROJECTION_INVALID_{what}")


def _bounded_items(value: object, what: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise InspectorProjectionError(f"INSPECTOR_PROJECTION_INVALID_{what}")
    # Documented input cap (see module docstring): exceeding it is a typed
    # error, never a silent last-N truncation — truncation could silently
    # discard conflicting evidence records.
    if len(value) > MAX_ITEMS_PER_PORT:
        raise InspectorProjectionError(
            f"INSPECTOR_PROJECTION_INPUT_OVERSIZED_{what}"
        )
    records = []
    for record in value:
        if isinstance(record, Mapping):
            records.append(dict(record))
        elif is_dataclass(record) and not isinstance(record, type):
            records.append(asdict(record))
        else:
            raise InspectorProjectionError(f"INSPECTOR_PROJECTION_INVALID_{what}")
    return records


def _str_field(record: Mapping[str, Any], key: str, limit: int) -> str | None:
    value = record.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise InspectorProjectionError("INSPECTOR_PROJECTION_INVALID_INPUT")
    return value[:limit]


def _identity(record: Mapping[str, Any], key: str) -> str | None:
    """Normalized COMPLETE identity field (G3/G4): type-validated, stripped,
    never truncated. Correlation and dedup compare these exact stripped
    values; ``MAX_VALUE`` truncation applies only to emitted display strings.
    A field that is blank after strip compares as empty and therefore fails
    the non-blank provenance gate."""
    value = record.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise InspectorProjectionError("INSPECTOR_PROJECTION_INVALID_INPUT")
    return value.strip()


def _bool_field(record: Mapping[str, Any], key: str) -> bool | None:
    value = record.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise InspectorProjectionError("INSPECTOR_PROJECTION_INVALID_INPUT")
    return value


def _parse_iso(value: str) -> datetime | None:
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _registrations(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = _bounded_items(snapshot.get("items"), "REGISTRY_ITEMS")
    registrations: dict[str, dict[str, Any]] = {}
    for record in items:
        item_id = _str_field(record, "item_id", MAX_ITEM_ID)
        if not item_id:
            raise InspectorProjectionError("INSPECTOR_PROJECTION_INVALID_INPUT")
        kind = record.get("kind")
        if kind not in ("hook", "tool"):
            raise InspectorProjectionError("INSPECTOR_PROJECTION_INVALID_INPUT")
        registration = {
            "kind": kind,
            "route": _str_field(record, "route", MAX_VALUE),
            # display copies: stripped complete identity, truncated AFTER
            # normalization and only for emission (G3)
            "source": None,
            "revision": None,
            "observed_at": _str_field(record, "observed_at", MAX_VALUE),
            # complete stripped identity values used for correlation and
            # registration-conflict comparison (G3/G4)
            "full_source": _identity(record, "source"),
            "full_revision": _identity(record, "revision"),
        }
        registration["source"] = (
            registration["full_source"][:MAX_VALUE]
            if registration["full_source"] is not None else None
        )
        registration["revision"] = (
            registration["full_revision"][:MAX_VALUE]
            if registration["full_revision"] is not None else None
        )
        existing = registrations.get(item_id)
        if existing is not None and existing != registration:
            # Conflicting registrations: fail closed, never pick one.
            raise InspectorProjectionError("INSPECTOR_PROJECTION_REGISTRATION_CONFLICT")
        registrations[item_id] = registration
    return registrations


def _groups(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        item_id = _str_field(record, "item_id", MAX_ITEM_ID)
        if not item_id:
            raise InspectorProjectionError("INSPECTOR_PROJECTION_INVALID_INPUT")
        # Known-field type validation happens before any state is derived:
        # non-bool availability, non-str observation metadata, or a
        # classification outside the A-Wiki hard/soft vocabulary is malformed
        # input, never a silently-tolerated value.
        _bool_field(record, "available")
        _str_field(record, "observed_at", MAX_VALUE)
        _str_field(record, "observation_id", MAX_VALUE)
        _str_field(record, "device_connection", MAX_VALUE)
        _str_field(record, "source", MAX_VALUE)
        _str_field(record, "revision", MAX_VALUE)
        classification = record.get("classification")
        if classification is not None:
            if not isinstance(classification, str) or classification not in ("hard", "soft"):
                raise InspectorProjectionError("INSPECTOR_PROJECTION_INVALID_INPUT")
        # G4: identity fields are normalized to their exact stripped values
        # on the internal copy so dedup signatures, correlation comparison,
        # and emission all use the same consistent basis.
        for identity_key in ("source", "revision"):
            normalized = _identity(record, identity_key)
            if normalized is not None:
                record[identity_key] = normalized
        groups.setdefault(item_id, []).append(record)
    return groups


def _dedupe_or_conflict(records: list[dict[str, Any]]) -> str | None:
    """Return a duplicate/conflict reason, or None when one record survives."""
    if len(records) <= 1:
        return None
    # G1: the signature must cover every identity/report fact including the
    # revision (and source); two records that agree except for the revision
    # are CONFLICTING evidence, never deduplicated — otherwise the surviving
    # record would depend on input order.
    signatures = {
        (
            record.get("source"),
            record.get("revision"),
            record.get("observation_id"),
            # H2: the signature uses the SAME normalized availability token
            # that _availability_of emits, so an absent 'available' key and
            # an explicit 'available=None' collapse to one canonical token —
            # surviving-record choice (and emitted availability) is
            # order-independent.
            _availability_of(record),
            record.get("device_connection"),
            record.get("classification"),
            record.get("observed_at"),
        )
        for record in records
    }
    if len(signatures) == 1:
        return None  # identical report repeated; deterministic dedupe
    sources = {record.get("source") for record in records}
    observation_ids = {record.get("observation_id") for record in records}
    if len(sources) == 1 and len(observation_ids) > 1:
        return "duplicate-startup"
    return "conflicting-evidence"


def _availability_of(record: Mapping[str, Any]) -> str:
    # H2: an explicit 'available=None' and an absent 'available' key map to
    # ONE canonical unasserted token, used identically for dedup signatures,
    # availability derivation, and emitted output (order-independence).
    if record.get("available") is None:
        return _AVAILABILITY_NOT_ASSERTED
    if record["available"]:
        return _AVAILABILITY_ASSERTED
    return _AVAILABILITY_UNAVAILABLE


def _ready_gate_failure(
    record: Mapping[str, Any],
    registration: Mapping[str, Any],
    evidence_domain: str,
    *,
    now: datetime,
    max_age_seconds: int,
) -> str | None:
    """Explicit-correlation gates on the READY grant (see module docstring)."""
    # G3: correlation compares COMPLETE (pre-truncation) identity values;
    # the truncated display copies are never used for matching.
    reg_source = registration["full_source"]
    reg_revision = registration["full_revision"]
    if not reg_source or not reg_revision:  # blank-after-strip fails too (G4)
        return "provenance-missing"
    reg_observed = registration["observed_at"]
    reg_parsed = _parse_iso(reg_observed) if reg_observed else None
    if reg_parsed is None:
        return "registration-stale"
    reg_age = (now - reg_parsed).total_seconds()
    if reg_age < 0 or reg_age > max_age_seconds:
        return "registration-stale"
    rec_source = record.get("source")
    rec_revision = record.get("revision")
    if not rec_source or not rec_revision:
        return "evidence-uncorrelated"
    if rec_source != reg_source or rec_revision != reg_revision:
        return "evidence-uncorrelated"
    if evidence_domain != registration["kind"]:
        return "domain-mismatch"
    return None


def _project_item(
    *,
    item_id: str,
    domain: str,
    evidence_domain: str,
    records: list[dict[str, Any]],
    registration: dict[str, Any] | None,
    registry_missing: bool,
    now: datetime,
    max_age_seconds: int,
    redact: Callable[[str, str], str],
) -> InspectorItem:
    # Classification agreement is evaluated across ALL records before any
    # side is picked: disagreeing classifications suppress the fact entirely.
    classification_values = {record.get("classification") for record in records}
    classification_conflict = len(classification_values) > 1
    classification_value = None
    if records and not classification_conflict:
        classification_value = records[0].get("classification")

    facts: dict[str, str] = {}
    if registration is not None:
        facts["kind"] = registration["kind"]
        if registration["route"] is not None:
            facts["route"] = registration["route"]
    if classification_value is not None:  # A-Wiki hard/soft label, verbatim
        facts["classification"] = classification_value
    facts = {key: redact(key, value) for key, value in facts.items() if key in _FACT_KEYS}

    def fail(state: str, reason: str, availability: str, *, source: str | None = None,
             observed_at: str | None = None) -> InspectorItem:
        return InspectorItem(
            item_id=redact("item_id", item_id),
            domain=domain,  # constant-safe: validated hook/tool vocabulary
            state=redact("state", state),
            reason=redact("reason", reason),
            facts=facts,
            source=redact("source", source) if source is not None else None,
            observed_at=redact("observed_at", observed_at) if observed_at is not None else None,
            availability=availability,  # constant-safe: documented vocabulary
        )

    if classification_conflict:
        return fail(UNKNOWN, "conflicting-classification", _AVAILABILITY_NOT_ASSERTED)
    conflict = _dedupe_or_conflict(records)
    if conflict is not None:
        return fail(UNKNOWN, conflict, _AVAILABILITY_NOT_ASSERTED)
    if registry_missing:
        return fail(UNKNOWN, "missing-registry", _availability_of(records[0]) if records else _AVAILABILITY_ABSENT)
    if registration is None:
        return fail(UNKNOWN, "absent-registration",
                    _availability_of(records[0]) if records else _AVAILABILITY_ABSENT)

    connection = records[0].get("device_connection") if records else None
    if connection is not None:
        if not isinstance(connection, str):
            raise InspectorProjectionError("INSPECTOR_PROJECTION_INVALID_INPUT")
        if connection.strip().lower() == "disconnected":
            return fail(DISCONNECTED, "disconnected-device", _AVAILABILITY_UNAVAILABLE)

    if not records:
        return fail(UNKNOWN, "no-evidence", _AVAILABILITY_ABSENT,
                    source=registration["source"], observed_at=registration["observed_at"])

    record = records[0]
    observed_at = record.get("observed_at")
    parsed = _parse_iso(observed_at) if observed_at else None
    if parsed is None:
        return fail(UNKNOWN, "freshness-unobserved", _availability_of(record),
                    source=record.get("source"), observed_at=observed_at)
    age = (now - parsed).total_seconds()
    if age < 0:
        return fail(UNKNOWN, "freshness-invalid", _availability_of(record),
                    source=record.get("source"), observed_at=observed_at)
    if age > max_age_seconds:
        return fail(STALE, "stale-evidence", _availability_of(record),
                    source=record.get("source"), observed_at=observed_at)
    available = record.get("available")
    if available is True:
        gate = _ready_gate_failure(record, registration, evidence_domain,
                                   now=now, max_age_seconds=max_age_seconds)
        if gate is not None:
            return fail(UNKNOWN, gate, _AVAILABILITY_ASSERTED,
                        source=record.get("source"), observed_at=observed_at)
        return fail(READY, "ready-evidence", _AVAILABILITY_ASSERTED,
                    source=record.get("source"), observed_at=observed_at)
    if available is False:
        return fail(UNKNOWN, "availability-false", _AVAILABILITY_UNAVAILABLE,
                    source=record.get("source"), observed_at=observed_at)
    return fail(UNKNOWN, "availability-not-asserted", _AVAILABILITY_NOT_ASSERTED,
                source=record.get("source"), observed_at=observed_at)


def _project_bus(
    bus: object,
    *,
    now: datetime,
    max_age_seconds: int,
    redact: Callable[[str, str], str],
) -> InspectorBusView:
    if bus is None:
        return InspectorBusView(
            state=redact("state", UNKNOWN),
            reason=redact("reason", "no-bus-evidence"),
            degraded=False,
            conditions=(),
            observed_at=None,
            source=None,
        )
    if not isinstance(bus, Mapping):
        raise InspectorProjectionError("INSPECTOR_PROJECTION_INVALID_INPUT")
    raw_conditions = bus.get("conditions")
    conditions: list[str] = []
    if raw_conditions is not None:
        if not isinstance(raw_conditions, (list, tuple)):
            raise InspectorProjectionError("INSPECTOR_PROJECTION_INVALID_INPUT")
        for condition in raw_conditions[:MAX_BUS_CONDITIONS]:
            if not isinstance(condition, str):
                raise InspectorProjectionError("INSPECTOR_PROJECTION_INVALID_INPUT")
            conditions.append(redact("conditions", condition[:MAX_VALUE]))
    observed_at = _str_field(bus, "observed_at", MAX_VALUE)
    source = _str_field(bus, "source", MAX_VALUE)
    backpressure = bus.get("backpressure")
    if backpressure is not None and not isinstance(backpressure, bool):
        raise InspectorProjectionError("INSPECTOR_PROJECTION_INVALID_INPUT")

    def emit(state: str, reason: str, *, degraded: bool) -> InspectorBusView:
        return InspectorBusView(
            state=redact("state", state),
            reason=redact("reason", reason),
            degraded=degraded,
            conditions=tuple(conditions),
            observed_at=redact("observed_at", observed_at) if observed_at else None,
            source=redact("source", source) if source else None,
        )

    # Bus freshness is evaluated BEFORE backpressure: a stale or
    # future-dated bus observation is STALE regardless of the flag, and a
    # bus mapping whose observation time is absent or unparseable has no
    # provable freshness — asserting its backpressure as current would be
    # unfounded (G5), so the view is UNKNOWN regardless of the flag.
    parsed = _parse_iso(observed_at) if observed_at else None
    if parsed is None:
        return emit(UNKNOWN, "bus-freshness-unobserved", degraded=False)
    age = (now - parsed).total_seconds()
    if age > max_age_seconds:
        return emit(STALE, "bus-evidence-stale", degraded=False)
    if age < 0:
        return emit(STALE, "bus-freshness-invalid", degraded=False)
    if backpressure is True:
        # Bus-LEVEL degraded only; never projected onto individual hooks.
        return emit(DEGRADED, "bus-backpressure", degraded=True)
    return emit(
        UNKNOWN,
        "bus-no-backpressure" if bus else "no-bus-evidence",
        degraded=False,
    )


def build_inspector_view(
    registry_snapshot: object,
    hook_evidence: object,
    tool_evidence: object,
    *,
    now: str,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    secret_predicate: Callable[[str, str], bool] | None = None,
) -> InspectorView:
    """Build one deterministic, sanitized, read-only inspector view.

    ``now`` is a caller-injected ISO-8601 instant (no clock is read here);
    ``max_age_seconds`` is the explicit freshness rule; ``secret_predicate``
    is an EXTRA detection layer COMPOSED with ``default_secret_predicate``
    (default OR custom — passing a custom predicate never disables the
    default strategy; a firing custom predicate redacts the whole value).
    """
    if not isinstance(now, str):
        raise InspectorProjectionError("INSPECTOR_PROJECTION_INVALID_NOW")
    now_dt = _parse_iso(now)
    if now_dt is None:
        raise InspectorProjectionError("INSPECTOR_PROJECTION_INVALID_NOW")
    if not isinstance(max_age_seconds, int) or isinstance(max_age_seconds, bool) \
            or max_age_seconds <= 0:
        raise InspectorProjectionError("INSPECTOR_PROJECTION_INVALID_MAX_AGE")
    if secret_predicate is not None and not callable(secret_predicate):
        raise InspectorProjectionError("INSPECTOR_PROJECTION_INVALID_REDACTOR")

    def redact(field_name: str, value: str) -> str:
        # (d) custom predicate composes: firing custom redacts the whole value.
        if secret_predicate is not None and secret_predicate(field_name, value):
            return REDACTED
        # (a) secret-named fields and (c) high-entropy token runs: whole value.
        if _field_name_is_secret_shaped(field_name) or _has_high_entropy_run(value):
            return REDACTED
        # (b) embedded credential segments: BOTH scans run before any return
        # (H1) — the ASCII copy (safe surgery) and the folded detection copy
        # (fail-closed whole-value) are composed via _compose_segment_redaction.
        return _compose_segment_redaction(value)

    registry = _as_port(registry_snapshot, "REGISTRY")
    hooks = _as_port(hook_evidence, "HOOKS")
    tools = _as_port(tool_evidence, "TOOLS")

    registry_missing = bool(registry.get("missing")) or registry.get("present") is False
    registrations = _registrations(registry)
    hook_groups = _groups(_bounded_items(hooks.get("items"), "HOOK_ITEMS"))
    tool_groups = _groups(_bounded_items(tools.get("items"), "TOOL_ITEMS"))

    items: list[InspectorItem] = []
    evidence_ids = set(hook_groups) | set(tool_groups)
    for item_id, registration in registrations.items():
        if item_id in evidence_ids:
            continue
        items.append(_project_item(
            item_id=item_id,
            domain=registration["kind"],
            evidence_domain=registration["kind"],
            records=[],
            registration=registration,
            registry_missing=registry_missing,
            now=now_dt,
            max_age_seconds=max_age_seconds,
            redact=redact,
        ))
    for item_id, records in hook_groups.items():
        registration = registrations.get(item_id)
        domain = registration["kind"] if registration is not None else "hook"
        items.append(_project_item(
            item_id=item_id,
            domain=domain,
            evidence_domain="hook",
            records=records,
            registration=registration,
            registry_missing=registry_missing,
            now=now_dt,
            max_age_seconds=max_age_seconds,
            redact=redact,
        ))
    for item_id, records in tool_groups.items():
        registration = registrations.get(item_id)
        domain = registration["kind"] if registration is not None else "tool"
        items.append(_project_item(
            item_id=item_id,
            domain=domain,
            evidence_domain="tool",
            records=records,
            registration=registration,
            registry_missing=registry_missing,
            now=now_dt,
            max_age_seconds=max_age_seconds,
            redact=redact,
        ))

    bus = hooks.get("bus")
    return InspectorView(
        items=tuple(items),
        hook_bus=_project_bus(bus, now=now_dt, max_age_seconds=max_age_seconds, redact=redact),
        registry_missing=registry_missing,
    )
