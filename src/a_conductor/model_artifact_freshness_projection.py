"""Pure read-only freshness projection over A-Wiki model-intel artifacts.

WO-P1-757 (SFU26 card 09). This module is a presentation-only projection over
an injectable artifact snapshot/loader (card-08 duck-typed pattern). It reads
no files, opens no sockets, runs no subprocesses, and has no write path: it
structurally cannot refresh, purchase, activate, pin, or configure anything.
Runtime decisions stay with their existing authorities; every report is
pinned ``non_authoritative=True``.

Artifact set and decision-input map (verified inputs, discovery 2026-11-15):

- ``model_scout_current`` — scout JSON; source of policy TIER1/TIER2 PRIMARY
  plus RACE override recommendations (``generated_at`` offset-ISO,
  ``volatile``/``offline`` flags, ``recommendations`` may be empty — typed,
  never fabricated).
- ``model_roster`` — flat ``KEY="VALUE"`` conf with a ``Generated:`` header;
  source of policy tier slots/fallbacks/TIER3/RACE base/pinned.
- ``model_router_policy`` — composed policy conf (naive-local
  ``MODEL_ROUTER_POLICY_GENERATED_AT``, ``MODEL_SCOUT_GENERATED_AT`` echo,
  ``MODEL_IDS_ARE_SEEDS``).
- ``model_catalog`` — model_match tier/price matrix JSON (may be near-empty:
  ``model_count: 0`` stays a valid AVAILABLE record).
- ``model_capability_cache`` — capability scores by family JSON
  (``as_of``, ``confidence``).

Artifact paths are machine-local and intentionally never enter this module:
the projection is keyed by artifact key only, so no raw path can be echoed
into any output field.

Staleness vocabulary follows the inspector chain precedent
(``AVAILABLE``/``STALE``/``UNKNOWN``; future-dated mtime → ``UNKNOWN``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from json import loads as _json_loads

SCOUT_KEY = "model_scout_current"
ROSTER_KEY = "model_roster"
POLICY_KEY = "model_router_policy"
CATALOG_KEY = "model_catalog"
CAPABILITY_KEY = "model_capability_cache"

ARTIFACT_KEYS: tuple[str, ...] = (
    SCOUT_KEY,
    ROSTER_KEY,
    POLICY_KEY,
    CATALOG_KEY,
    CAPABILITY_KEY,
)

#: Documented per-artifact default ``max_age_seconds`` thresholds, chosen from
#: each artifact's regeneration cadence (injectable per call via
#: ``max_age_seconds``): the scout regenerates on the shortest cycle (6h),
#: roster and composed policy on a daily cycle (24h), the tier/price catalog
#: weekly (7d), and capability scores drift the slowest (30d).
DEFAULT_MAX_AGE_SECONDS_BY_ARTIFACT: dict[str, int] = {
    SCOUT_KEY: 21_600,
    ROSTER_KEY: 86_400,
    POLICY_KEY: 86_400,
    CATALOG_KEY: 604_800,
    CAPABILITY_KEY: 2_592_000,
}

_DECISION_INPUT_ROLES: dict[str, str] = {
    SCOUT_KEY: "POLICY_TIER_PRIMARY_AND_RACE_OVERRIDE_SOURCE",
    ROSTER_KEY: "POLICY_TIER_SLOTS_FALLBACKS_TIER3_AND_RACE_BASE_SOURCE",
    POLICY_KEY: "COMPOSED_ROUTER_POLICY_SOURCE",
    CATALOG_KEY: "MODEL_MATCH_TIER_PRICE_MATRIX_SOURCE",
    CAPABILITY_KEY: "CAPABILITY_SCORES_BY_FAMILY_SOURCE",
}

_READ_AVAILABLE = "AVAILABLE"
_READ_ABSENT = "ABSENT"
_READ_UNPARSEABLE = "UNPARSEABLE"
_READ_UNREADABLE = "UNREADABLE"

_REASON_OK = "OK"
_REASON_ABSENT = "ARTIFACT_ABSENT"
_REASON_JSON_INVALID = "EMBEDDED_JSON_INVALID"
_REASON_JSON_SHAPE = "EMBEDDED_JSON_SHAPE_INVALID"
_REASON_CONF_INVALID = "EMBEDDED_CONF_INVALID"
_REASON_MATERIAL_MALFORMED = "ARTIFACT_MATERIAL_MALFORMED"

_STALENESS_AVAILABLE = "AVAILABLE"
_STALENESS_STALE = "STALE"
_STALENESS_UNKNOWN = "UNKNOWN"

_PARSE_OFFSET = "PARSED_OFFSET"
_PARSE_NAIVE_LOCAL = "PARSED_NAIVE_LOCAL"
_PARSE_UNPARSEABLE = "UNPARSEABLE"

_NOTE_DRIFT = "ROSTER_NEWER_THAN_POLICY"
_NOTE_ECHO_MISMATCH = "SCOUT_ECHO_MISMATCH"
_NOTE_SEEDS_ACTIVE = "SEEDS_ACTIVE"

_SEVERITY_DRIFT = "DRIFT"
_SEVERITY_MISMATCH = "MISMATCH"
_SEVERITY_WARNING = "WARNING"

_BASIS_OFFSET_INSTANT = "OFFSET_INSTANT"
_BASIS_NAIVE_LOCAL_WALL = "NAIVE_LOCAL_WALL"

_DEGRADED_LOADER = "LOADER_FAILURE"
_DEGRADED_SHAPE = "SNAPSHOT_SHAPE_INVALID"


@dataclass(frozen=True, slots=True)
class ModelArtifactEmbeddedFlags:
    """Typed embedded artifact flags; ``None`` means not stated by the artifact."""

    volatile: bool | None = None
    offline: bool | None = None
    confidence: str | None = None
    model_count: int | None = None
    model_ids_are_seeds: bool | None = None


@dataclass(frozen=True, slots=True)
class ModelArtifactRecord:
    """Per-artifact freshness record for one decision-input artifact.

    ``read_state`` is one of ``AVAILABLE``/``ABSENT``/``UNPARSEABLE``/
    ``UNREADABLE`` with a fixed ``read_reason`` code. ``mtime_staleness`` is
    the mtime-based label (``AVAILABLE``/``STALE``/``UNKNOWN``; a future mtime
    is ``UNKNOWN``). ``generated_at_raw`` preserves the embedded timestamp
    byte-for-byte; ``generated_at_parse_state`` labels how it parsed
    (``PARSED_OFFSET``/``PARSED_NAIVE_LOCAL``/``UNPARSEABLE``); naive-local
    values are never converted to UTC. No field carries a raw path.
    """

    artifact_key: str
    decision_input_role: str
    read_state: str
    read_reason: str
    mtime_staleness: str
    file_age_seconds: float | None
    generated_at_raw: str | None
    generated_at_parse_state: str | None
    embedded_flags: ModelArtifactEmbeddedFlags
    recommendations_empty: bool | None
    content_fingerprint: str | None
    size_bytes: int | None


@dataclass(frozen=True, slots=True)
class ModelFreshnessNote:
    """Typed cross-artifact observation.

    Compared raw values are shown only when both sides parsed; mixed
    tz-kind pairs are never ordered, so no note is emitted for them.
    """

    note_kind: str
    severity: str
    left_label: str
    left_raw: str | None
    right_label: str | None
    right_raw: str | None
    comparison_basis: str | None


@dataclass(frozen=True, slots=True)
class ModelIntelFreshnessReport:
    """Non-authoritative freshness report over the model-intel artifact set."""

    artifacts: tuple[ModelArtifactRecord, ...]
    observations: tuple[ModelFreshnessNote, ...]
    degraded: bool = False
    degraded_reason: str | None = None
    non_authoritative: bool = field(default=True, init=False)


def _utc_now(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("now must be an aware datetime")
    return value.astimezone(timezone.utc)


def _validated_threshold(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError("max_age_seconds must be a non-negative number")
    return float(value)


def _resolve_thresholds(max_age_seconds: object) -> dict[str, float]:
    defaults = {key: float(value) for key, value in DEFAULT_MAX_AGE_SECONDS_BY_ARTIFACT.items()}
    if max_age_seconds is None:
        return defaults
    if isinstance(max_age_seconds, Mapping):
        for key in max_age_seconds:
            if key not in defaults:
                raise ValueError(f"max_age_seconds: unknown artifact key {key!r}")
        for key, value in max_age_seconds.items():
            defaults[key] = _validated_threshold(value)
        return defaults
    single = _validated_threshold(max_age_seconds)
    return {key: single for key in defaults}


def _mtime_value(value: object) -> float | None | str:
    """Return a usable mtime epoch, ``None`` (unstated) or ``"MALFORMED"``."""

    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "MALFORMED"
    return float(value)


def _raw_bytes(value: object) -> bytes | None | str:
    """Return raw content bytes, ``None`` (absent) or ``"MALFORMED"``."""

    if value is None:
        return None
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return "MALFORMED"


def _decode_text(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace")


def _parse_embedded_timestamp(raw: str | None) -> tuple[datetime | None, str | None]:
    if raw is None:
        return None, None
    try:
        parsed = datetime.fromisoformat(raw.strip())
    except ValueError:
        return None, _PARSE_UNPARSEABLE
    if parsed.tzinfo is not None and parsed.utcoffset() is not None:
        return parsed, _PARSE_OFFSET
    return parsed, _PARSE_NAIVE_LOCAL


def _parse_conf(text: str) -> tuple[str | None, dict[str, str]]:
    header: str | None = None
    pairs: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if header is None and stripped.startswith("Generated:"):
            header = stripped.partition(":")[2].strip()
            continue
        if "=" in stripped:
            key, _, value = stripped.partition("=")
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            if key:
                pairs[key] = value
    if header is None and not pairs:
        raise ValueError(_REASON_CONF_INVALID)
    return header, pairs


def _parse_json(text: str) -> dict:
    try:
        data = _json_loads(text)
    except ValueError:
        raise ValueError(_REASON_JSON_INVALID) from None
    if not isinstance(data, dict):
        raise ValueError(_REASON_JSON_SHAPE)
    return data


def _optional_flag(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _entries_from(container: object) -> dict[str, object] | None:
    if isinstance(container, Mapping):
        return {key: value for key, value in container.items() if isinstance(key, str)}
    if isinstance(container, (str, bytes)):
        return None
    try:
        iterator = iter(container)
    except TypeError:
        return None
    entries: dict[str, object] = {}
    for entry in iterator:
        if isinstance(entry, Mapping):
            key = entry.get("artifact_key")
        else:
            key = getattr(entry, "artifact_key", None)
        if not isinstance(key, str):
            return None
        entries[key] = entry
    return entries


def _resolve_artifact_entries(snapshot: object) -> dict[str, object] | None:
    source = snapshot
    if callable(source):
        source = source()
    if isinstance(source, (str, bytes)):
        return None
    if isinstance(source, Mapping):
        inner = source.get("artifacts") if "artifacts" in source else None
        if inner is not None:
            return _entries_from(inner)
        return _entries_from(source)
    attribute = getattr(source, "artifacts", None)
    if attribute is not None and not callable(attribute):
        return _entries_from(attribute)
    return _entries_from(source)


def _material_fields(entry: object) -> tuple[bytes | None | str, float | None | str]:
    if isinstance(entry, Mapping):
        raw = entry.get("raw")
        mtime = entry.get("mtime_epoch_seconds")
    else:
        raw = getattr(entry, "raw", None)
        mtime = getattr(entry, "mtime_epoch_seconds", None)
    return _raw_bytes(raw), _mtime_value(mtime)


def _staleness(mtime: float | None, threshold: float, now_epoch: float) -> tuple[str, float | None]:
    if mtime is None:
        return _STALENESS_UNKNOWN, None
    age = now_epoch - mtime
    if age < 0:
        return _STALENESS_UNKNOWN, age
    if age > threshold:
        return _STALENESS_STALE, age
    return _STALENESS_AVAILABLE, age


def _json_flags(data: dict, key: str) -> tuple[str | None, ModelArtifactEmbeddedFlags, bool | None]:
    generated_at_raw = _optional_str(data.get("generated_at"))
    if key == SCOUT_KEY:
        flags = ModelArtifactEmbeddedFlags(
            volatile=_optional_flag(data.get("volatile")),
            offline=_optional_flag(data.get("offline")),
        )
        recommendations = data.get("recommendations")
        empty = None
        if isinstance(recommendations, dict):
            empty = len(recommendations) == 0
        return generated_at_raw, flags, empty
    if key == CATALOG_KEY:
        return None, ModelArtifactEmbeddedFlags(model_count=_optional_int(data.get("model_count"))), None
    if key == CAPABILITY_KEY:
        as_of = _optional_str(data.get("as_of"))
        flags = ModelArtifactEmbeddedFlags(confidence=_optional_str(data.get("confidence")))
        return as_of, flags, None
    return None, ModelArtifactEmbeddedFlags(), None


def _conf_flags(key: str, pairs: dict[str, str], header: str | None) -> tuple[str | None, ModelArtifactEmbeddedFlags, bool | None, str | None]:
    if key == ROSTER_KEY:
        return header, ModelArtifactEmbeddedFlags(), None, None
    if key == POLICY_KEY:
        seeds_raw = pairs.get("MODEL_IDS_ARE_SEEDS")
        if seeds_raw == "1":
            seeds: bool | None = True
        elif seeds_raw == "0":
            seeds = False
        else:
            seeds = None
        echo = pairs.get("MODEL_SCOUT_GENERATED_AT")
        return (
            pairs.get("MODEL_ROUTER_POLICY_GENERATED_AT"),
            ModelArtifactEmbeddedFlags(model_ids_are_seeds=seeds),
            None,
            echo,
        )
    return None, ModelArtifactEmbeddedFlags(), None, None


def _timestamp_fields(raw: str | None) -> tuple[str | None, str | None]:
    _, state = _parse_embedded_timestamp(raw)
    return raw, state


def _comparable_pair(
    left: tuple[datetime | None, str | None],
    right: tuple[datetime | None, str | None],
) -> tuple[datetime, datetime, str] | None:
    left_value, left_state = left
    right_value, right_state = right
    if left_value is None or right_value is None:
        return None
    if left_state == _PARSE_OFFSET and right_state == _PARSE_OFFSET:
        return (
            left_value.astimezone(timezone.utc),
            right_value.astimezone(timezone.utc),
            _BASIS_OFFSET_INSTANT,
        )
    if left_state == _PARSE_NAIVE_LOCAL and right_state == _PARSE_NAIVE_LOCAL:
        return left_value, right_value, _BASIS_NAIVE_LOCAL_WALL
    return None


def _build_record(
    key: str,
    entry: object | None,
    *,
    thresholds: dict[str, float],
    now_epoch: float,
) -> tuple[ModelArtifactRecord, str | None, tuple[datetime | None, str | None], str | None]:
    if entry is None:
        return (
            ModelArtifactRecord(
                artifact_key=key,
                decision_input_role=_DECISION_INPUT_ROLES[key],
                read_state=_READ_ABSENT,
                read_reason=_REASON_ABSENT,
                mtime_staleness=_STALENESS_UNKNOWN,
                file_age_seconds=None,
                generated_at_raw=None,
                generated_at_parse_state=None,
                embedded_flags=ModelArtifactEmbeddedFlags(),
                recommendations_empty=None,
                content_fingerprint=None,
                size_bytes=None,
            ),
            None,
            (None, None),
            None,
        )

    raw, mtime = _material_fields(entry)
    if raw is None:
        return (
            ModelArtifactRecord(
                artifact_key=key,
                decision_input_role=_DECISION_INPUT_ROLES[key],
                read_state=_READ_ABSENT,
                read_reason=_REASON_ABSENT,
                mtime_staleness=_STALENESS_UNKNOWN,
                file_age_seconds=None,
                generated_at_raw=None,
                generated_at_parse_state=None,
                embedded_flags=ModelArtifactEmbeddedFlags(),
                recommendations_empty=None,
                content_fingerprint=None,
                size_bytes=None,
            ),
            None,
            (None, None),
            None,
        )
    if isinstance(raw, str):  # "MALFORMED" sentinel
        return (
            ModelArtifactRecord(
                artifact_key=key,
                decision_input_role=_DECISION_INPUT_ROLES[key],
                read_state=_READ_UNREADABLE,
                read_reason=_REASON_MATERIAL_MALFORMED,
                mtime_staleness=_STALENESS_UNKNOWN,
                file_age_seconds=None,
                generated_at_raw=None,
                generated_at_parse_state=None,
                embedded_flags=ModelArtifactEmbeddedFlags(),
                recommendations_empty=None,
                content_fingerprint=None,
                size_bytes=None,
            ),
            None,
            (None, None),
            None,
        )
    if isinstance(mtime, str):  # "MALFORMED" sentinel
        return (
            ModelArtifactRecord(
                artifact_key=key,
                decision_input_role=_DECISION_INPUT_ROLES[key],
                read_state=_READ_UNREADABLE,
                read_reason=_REASON_MATERIAL_MALFORMED,
                mtime_staleness=_STALENESS_UNKNOWN,
                file_age_seconds=None,
                generated_at_raw=None,
                generated_at_parse_state=None,
                embedded_flags=ModelArtifactEmbeddedFlags(),
                recommendations_empty=None,
                content_fingerprint=None,
                size_bytes=None,
            ),
            None,
            (None, None),
            None,
        )

    fingerprint = sha256(raw).hexdigest()
    size = len(raw)
    staleness, age = _staleness(mtime, thresholds[key], now_epoch)

    try:
        if key in (SCOUT_KEY, CATALOG_KEY, CAPABILITY_KEY):
            data = _parse_json(_decode_text(raw))
            generated_at_raw, flags, recommendations_empty = _json_flags(data, key)
            echo = None
        else:
            header, pairs = _parse_conf(_decode_text(raw))
            generated_at_raw, flags, recommendations_empty, echo = _conf_flags(key, pairs, header)
    except ValueError as reason:
        return (
            ModelArtifactRecord(
                artifact_key=key,
                decision_input_role=_DECISION_INPUT_ROLES[key],
                read_state=_READ_UNPARSEABLE,
                read_reason=str(reason),
                mtime_staleness=staleness,
                file_age_seconds=age,
                generated_at_raw=None,
                generated_at_parse_state=None,
                embedded_flags=ModelArtifactEmbeddedFlags(),
                recommendations_empty=None,
                content_fingerprint=fingerprint,
                size_bytes=size,
            ),
            None,
            (None, None),
            None,
        )

    generated_at_raw, parse_state = _timestamp_fields(generated_at_raw)
    record = ModelArtifactRecord(
        artifact_key=key,
        decision_input_role=_DECISION_INPUT_ROLES[key],
        read_state=_READ_AVAILABLE,
        read_reason=_REASON_OK,
        mtime_staleness=staleness,
        file_age_seconds=age,
        generated_at_raw=generated_at_raw,
        generated_at_parse_state=parse_state,
        embedded_flags=flags,
        recommendations_empty=recommendations_empty,
        content_fingerprint=fingerprint,
        size_bytes=size,
    )
    return record, echo, (None, None) if generated_at_raw is None else _parse_embedded_timestamp(generated_at_raw), echo


def _degraded_report(reason: str) -> ModelIntelFreshnessReport:
    return ModelIntelFreshnessReport(
        artifacts=(),
        observations=(),
        degraded=True,
        degraded_reason=reason,
    )


def project_model_artifact_freshness(
    snapshot: object,
    *,
    now: datetime | None = None,
    max_age_seconds: float | int | Mapping[str, float | int] | None = None,
) -> ModelIntelFreshnessReport:
    """Project a pure, non-authoritative freshness report.

    ``snapshot`` is an injectable artifact material source: a mapping of
    artifact key → material, an object exposing an ``artifacts`` mapping, an
    iterable of entries carrying ``artifact_key``, or a zero-argument loader
    callable returning any of those (card-08 duck-typed pattern). Each
    material carries ``raw`` (``str``/``bytes``/``None``) and an optional
    ``mtime_epoch_seconds``; extra attributes (including any local path) are
    ignored and never echoed. A loader that raises yields a typed degraded
    report, never an exception.

    ``now`` must be an aware ``datetime``; ``max_age_seconds`` may be a single
    non-negative number applied to every artifact or a per-artifact mapping
    over :data:`DEFAULT_MAX_AGE_SECONDS_BY_ARTIFACT` keys.
    """

    current = _utc_now(now)
    thresholds = _resolve_thresholds(max_age_seconds)
    now_epoch = current.timestamp()

    try:
        entries = _resolve_artifact_entries(snapshot)
    except Exception:
        return _degraded_report(_DEGRADED_LOADER)
    if entries is None:
        return _degraded_report(_DEGRADED_SHAPE)

    parsed: dict[str, tuple[datetime | None, str | None]] = {}
    echo_raw: dict[str, str | None] = {}
    records: list[ModelArtifactRecord] = []
    for key in ARTIFACT_KEYS:
        record, echo, parsed_pair, _ = _build_record(
            key,
            entries.get(key),
            thresholds=thresholds,
            now_epoch=now_epoch,
        )
        records.append(record)
        parsed[key] = parsed_pair
        echo_raw[key] = echo

    roster_value, roster_state = parsed[ROSTER_KEY]
    policy_value, policy_state = parsed[POLICY_KEY]
    scout_value, scout_state = parsed[SCOUT_KEY]

    observations: list[ModelFreshnessNote] = []

    drift_pair = _comparable_pair((roster_value, roster_state), (policy_value, policy_state))
    if drift_pair is not None and drift_pair[0] > drift_pair[1]:
        observations.append(
            ModelFreshnessNote(
                note_kind=_NOTE_DRIFT,
                severity=_SEVERITY_DRIFT,
                left_label=ROSTER_KEY,
                left_raw=_raw_generated_at(records, ROSTER_KEY),
                right_label=POLICY_KEY,
                right_raw=_raw_generated_at(records, POLICY_KEY),
                comparison_basis=drift_pair[2],
            )
        )

    echo_pair = _comparable_pair(
        _parse_embedded_timestamp(echo_raw[POLICY_KEY]),
        (scout_value, scout_state),
    )
    if echo_pair is not None and echo_pair[0] != echo_pair[1]:
        observations.append(
            ModelFreshnessNote(
                note_kind=_NOTE_ECHO_MISMATCH,
                severity=_SEVERITY_MISMATCH,
                left_label=f"{POLICY_KEY}.MODEL_SCOUT_GENERATED_AT",
                left_raw=echo_raw[POLICY_KEY],
                right_label=f"{SCOUT_KEY}.generated_at",
                right_raw=_raw_generated_at(records, SCOUT_KEY),
                comparison_basis=echo_pair[2],
            )
        )

    seeds_flag = next(
        (record.embedded_flags.model_ids_are_seeds for record in records if record.artifact_key == POLICY_KEY),
        None,
    )
    if seeds_flag is True:
        observations.append(
            ModelFreshnessNote(
                note_kind=_NOTE_SEEDS_ACTIVE,
                severity=_SEVERITY_WARNING,
                left_label=f"{POLICY_KEY}.MODEL_IDS_ARE_SEEDS",
                left_raw="1",
                right_label=None,
                right_raw=None,
                comparison_basis=None,
            )
        )

    return ModelIntelFreshnessReport(
        artifacts=tuple(records),
        observations=tuple(observations),
    )


def _raw_generated_at(records: list[ModelArtifactRecord], key: str) -> str | None:
    for record in records:
        if record.artifact_key == key:
            return record.generated_at_raw
    return None
