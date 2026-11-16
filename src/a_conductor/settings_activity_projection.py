"""WO-P1-767 / SFU26 card 05: safe logs + effective settings read models.

Pure, deny-by-default read-model projection over injected records for eleven
operator surfaces. The module performs no I/O, reads no wall clock (``now``
is injectable on the facade), imports no ambient-system, network, storage,
or provider machinery beyond the pure ``ProviderOperatorRow`` type, and
never fabricates values.

Per-surface law (ALLOW = metadata only; DENY = value-bearing, never read
into the projection; unknown injected fields never project):

- ``providers``: reuse ``ProviderOperatorRow`` by import (embedded by
  reference, never redefined) plus protocol_family, schema_version,
  endpoint_ref, admission metadata (admission_id, status, acquired_at,
  expires_at, released_at, reconciled_at, configuration_generation) and the
  derived ``credential_configured`` boolean. DENY endpoint base URLs and
  credential refs; the credential ref is read solely to derive the boolean.
- ``hook_activity``: allowlist-filtered HookBus envelopes (event metadata,
  correlation, evidence digests/refs, markers, adapter contract metadata,
  guard scope metadata). DENY summary/justification free text, repo /
  worktree / branch / authority_repo / execution_repo, and guard.policy_ref
  (never read at all).
- ``control_activity``: the five payload-free ControlEvent fields.
- ``execution_activity``: execution event metadata; ``evidence_ref`` is
  DENY/opaque-only (never read).
- ``mutation_audit``: actor id (worker or connector), action, at.
- ``worker_brain``: brain settings metadata; ``brain_folder_count`` and
  ``brain_entry_count`` replace the folder/entry path entries; ``project_path``
  and entry values are DENY; ``settings_version`` is typed ``NOT_CARRIED``
  because the source carries no version (drift typing: generation fields are
  carried where the source has them, never fabricated where it does not).
- ``worker_runtime``: runtime config scalars plus derived
  ``tunnel_binding_configured``; instance roots, homes, dirs, hosts, refs
  and credential refs are DENY (the tunnel ref is read solely for the
  derived boolean).
- ``project_bindings``: identity metadata; ``worktree_path`` DENY.
- ``local_references``: opaque reference_id + ``reference_count`` /
  ``root_count`` counts that replace file paths and allowed roots (DENY).
- ``registry``: display/identity metadata; ``root_path`` and ``worktree_key``
  DENY.
- ``network_policy``: policy metadata plus ``network_allowlist_count`` which
  replaces the individual host entries (DENY); ``reason_code`` is a closed
  module vocabulary.

Safety mechanics (fleet_projection laws applied verbatim): every attribute
read on injected records is wrapped — a raising property becomes a typed
per-record rejection, never an exception escape; malformed records become
typed rejections carrying a code only (no diagnostic value echo) while valid
neighbors survive; identifier handles and all safe text fields obey the
fleet path-shape law plus the web_api deny-prefix/``_REF``/``_CODE`` shapes
(reimplemented locally because ``web_api`` drags in pydantic and transport
machinery; ``tests/test_settings_activity_projection.py`` imports both and
asserts decision equality, pinning parity); emitted text is always the
probed plain-str view returned by the validator — never ``str()`` on the
original duck value — and emitted ints are plain ``int`` coercions, so
two-faced str/int subclasses cannot launder attacker text into safe fields
or record reprs; hostile iterables that fail mid-iteration degrade their
group with a typed reason instead of escaping; emitted frames are bounded
at 256 rows per group with drop accounting; every emitted dataclass is
frozen with slots and carries a pinned ``non_authoritative`` flag: this
projection is display/read context, never mutation, claim, or completion
authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from datetime import datetime
from typing import Sequence

from .provider_operator_view import ProviderOperatorRow

__all__ = [
    "SettingsActivityView",
    "SettingsAdmissionRecord",
    "SettingsControlActivityRecord",
    "SettingsExecutionActivityRecord",
    "SettingsHookActivityRecord",
    "SettingsHookAdapter",
    "SettingsHookGuard",
    "SettingsLocalReferenceRecord",
    "SettingsMutationAuditRecord",
    "SettingsNetworkPolicyRecord",
    "SettingsProjectionError",
    "SettingsProjectBindingRecord",
    "SettingsProviderRecord",
    "SettingsRecordRejection",
    "SettingsRegistryRecord",
    "SettingsSurfaceGroup",
    "SettingsWorkerBrainRecord",
    "SettingsWorkerRuntimeRecord",
    "project_settings_activity_view",
]

_FRAME_ROW_LIMIT = 256
_REJECTION_LIMIT = 256
_TEXT_LIMIT = 256
_REF_LIMIT = 128
_STAMP_LIMIT = 40
_DIGEST_LIMIT = 128
_TUPLE_LIMIT = 16
_TOOL_TUPLE_LIMIT = 64

# Validator parity pins: identical shapes to a_conductor.web_api (WO law:
# same regex semantics, locally defined because web_api is import-heavy;
# parity asserted decision-by-decision in the tests).
_CODE_RE = re.compile(r"[A-Z][A-Z0-9_:\-]{0,127}\Z")
_REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:#\-]{0,127}\Z")
_DENY_PREFIXES = ("sk-", "bearer", "token", "password", "secret")
_DRIVE = re.compile(r"^[A-Za-z]:")
_SHA = re.compile(r"[0-9a-f]{40}")
_DIGEST = re.compile(r"[0-9a-f]{8,128}\Z")

_NOT_CARRIED = "NOT_CARRIED"
_NETWORK_REASON_CODES = frozenset(
    {
        "POLICY_ALLOWLISTED",
        "POLICY_INHERIT",
        "POLICY_DENIED",
        "SECRET_ACCESS_DENIED",
        "NOT_EVALUATED",
        "UNAVAILABLE",
    }
)

_MISSING = object()
_PLAIN_TYPES = (
    type(None),
    str,
    bytes,
    bool,
    int,
    float,
    complex,
    tuple,
    list,
    dict,
    set,
    frozenset,
)


class SettingsProjectionError(ValueError):
    """Typed caller-contract violation; never a fabricated view."""


@dataclass(frozen=True, slots=True)
class SettingsRecordRejection:
    surface: str = ""
    code: str = ""
    field: str | None = None
    source_index: int = 0
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class SettingsSurfaceGroup:
    kind: str = ""
    state: str = "OK"
    reason: str | None = None
    records: tuple = ()
    rejections: tuple[SettingsRecordRejection, ...] = ()
    dropped_count: int = 0
    truncated: bool = False
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class SettingsAdmissionRecord:
    admission_id: str = ""
    status: str | None = None
    acquired_at: str | None = None
    expires_at: str | None = None
    released_at: str | None = None
    reconciled_at: str | None = None
    configuration_generation: int | None = None
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class SettingsProviderRecord:
    row: ProviderOperatorRow = dc_field(default_factory=ProviderOperatorRow)
    protocol_family: str | None = None
    schema_version: str | None = None
    endpoint_ref: str | None = None
    admission: SettingsAdmissionRecord | None = None
    credential_configured: bool = False
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class SettingsHookAdapter:
    adapter_id: str = ""
    adapter_version: str | None = None
    contract_version: str | None = None
    redaction_policy: str | None = None
    supports_sequence: bool = False
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class SettingsHookGuard:
    failure_policy: str | None = None
    security_scope: str | None = None
    authority_scope: str | None = None
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class SettingsHookActivityRecord:
    event_id: str = ""
    event_type: str | None = None
    hook_class: str | None = None
    phase: str | None = None
    domain: str | None = None
    action: str | None = None
    occurred_at: str | None = None
    source: str | None = None
    source_version: str | None = None
    device_id: str | None = None
    host_os: str | None = None
    privacy_class: str | None = None
    lane_id: str | None = None
    task_id: str | None = None
    work_order: str | None = None
    task_topology: str | None = None
    head_sha: str | None = None
    claim_ref: str | None = None
    execution_id: str | None = None
    harness_id: str | None = None
    model_id: str | None = None
    effort: str | None = None
    state: str | None = None
    duration_ms: int | None = None
    blocker_code: str | None = None
    sequence: int | None = None
    dedupe_key: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    evidence_refs: tuple[str, ...] = ()
    evidence_digest: str | None = None
    command_digest: str | None = None
    command_ref: str | None = None
    markers: tuple[str, ...] = ()
    adapter: SettingsHookAdapter | None = None
    guard: SettingsHookGuard | None = None
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class SettingsControlActivityRecord:
    event_id: str = ""
    event_type: str | None = None
    worker_id: str | None = None
    project_id: str | None = None
    recorded_at: str | None = None
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class SettingsExecutionActivityRecord:
    event_id: str = ""
    execution_id: str = ""
    sequence_no: int = 0
    event_type: str | None = None
    transport_state: str | None = None
    execution_state: str | None = None
    pid: int | None = None
    exit_code: int | None = None
    started_at: str | None = None
    finished_at: str | None = None
    recorded_at: str | None = None
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class SettingsMutationAuditRecord:
    actor_id: str = ""
    actor_kind: str = "worker"
    action: str | None = None
    at: str | None = None
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class SettingsWorkerBrainRecord:
    worker_id: str = ""
    language_backend: str | None = None
    tool_timeout: int | None = None
    excluded_tools: tuple[str, ...] = ()
    included_optional_tools: tuple[str, ...] = ()
    fixed_tools: tuple[str, ...] = ()
    base_modes: tuple[str, ...] = ()
    enabled_languages: tuple[str, ...] = ()
    brain_folder_count: int = 0
    brain_entry_count: int = 0
    settings_version: str = _NOT_CARRIED
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class SettingsWorkerRuntimeRecord:
    worker_id: str = ""
    runtime_id: str = ""
    health_port: int | None = None
    startup_timeout_seconds: int | None = None
    stop_timeout_seconds: int | None = None
    tunnel_binding_configured: bool = False
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class SettingsProjectBindingRecord:
    project_id: str = ""
    identity_policy: str | None = None
    expected_branch: str | None = None
    expected_head: str | None = None
    mutation_allowed: bool = False
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class SettingsLocalReferenceRecord:
    reference_id: str = ""
    reference_count: int = 0
    root_count: int = 0
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class SettingsRegistryRecord:
    project_id: str = ""
    display_name: str | None = None
    worker_id: str | None = None
    worker_display_name: str | None = None
    runtime_id: str | None = None
    state: str | None = None
    assignment_id: str | None = None
    mutation_allowed: bool = False
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class SettingsNetworkPolicyRecord:
    privacy_class: str | None = None
    network_policy: str | None = None
    secret_access: bool = False
    network_allowlist_count: int = 0
    reason_code: str | None = None
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class SettingsActivityView:
    providers: SettingsSurfaceGroup = dc_field(default_factory=SettingsSurfaceGroup)
    hook_activity: SettingsSurfaceGroup = dc_field(default_factory=SettingsSurfaceGroup)
    control_activity: SettingsSurfaceGroup = dc_field(
        default_factory=SettingsSurfaceGroup
    )
    execution_activity: SettingsSurfaceGroup = dc_field(
        default_factory=SettingsSurfaceGroup
    )
    mutation_audit: SettingsSurfaceGroup = dc_field(
        default_factory=SettingsSurfaceGroup
    )
    worker_brain: SettingsSurfaceGroup = dc_field(default_factory=SettingsSurfaceGroup)
    worker_runtime: SettingsSurfaceGroup = dc_field(
        default_factory=SettingsSurfaceGroup
    )
    project_bindings: SettingsSurfaceGroup = dc_field(
        default_factory=SettingsSurfaceGroup
    )
    local_references: SettingsSurfaceGroup = dc_field(
        default_factory=SettingsSurfaceGroup
    )
    registry: SettingsSurfaceGroup = dc_field(default_factory=SettingsSurfaceGroup)
    network_policy: SettingsSurfaceGroup = dc_field(
        default_factory=SettingsSurfaceGroup
    )
    non_authoritative: bool = dc_field(init=False, default=True)


# ---------------------------------------------------------------------------
# Wrapped access + text laws
# ---------------------------------------------------------------------------


def _read(record: object, name: str) -> tuple[str, object]:
    """Wrapped duck access returning ("ok"|"missing"|"unreadable", value)."""
    try:
        value = getattr(record, name, _MISSING)
    except Exception:
        return "unreadable", None
    if value is _MISSING:
        return "missing", None
    return "ok", value


def _probed_str(value: str) -> str | None:
    """Safe plain-str view of a text value; None for a lying str subclass."""
    if type(value) is str:
        return value
    try:
        probe = "".join(list(value))
    except Exception:
        return None
    try:
        if len(probe) != len(value):
            return None
    except Exception:
        return None
    return probe


def _deny_prefixed(value: str) -> bool:
    """web_api ``_text`` deny-prefix law: secret-shaped leading vocabulary."""
    return value.lower().startswith(_DENY_PREFIXES)


def _path_shaped(value: str) -> bool:
    """Fleet path-shape law: paths never project through safe text fields."""
    if "\\" in value or value.startswith("/") or value.startswith("~"):
        return True
    if _DRIVE.match(value):
        return True
    return ".." in value.split("/")


def _url_shaped(value: str) -> bool:
    return "://" in value


def _checked_ref(value: object) -> tuple[str | None, str | None]:
    """Typed ``(rejection_code, validated_emission_text)`` for identifier/refs.

    The returned text is the probed plain-str view that was validated —
    emission sites must emit exactly that text and never ``str(value)`` on
    the original duck value: a two-faced str subclass can carry an
    attacker-controlled ``__str__`` that differs from its iteration view.
    Decision-equal to ``web_api._text`` on the parity corpus (charset,
    length and deny-prefix law) and additionally enforces the fleet
    path-shape law so a path never projects through a safe field.
    """
    if not isinstance(value, str):
        return "IDENTIFIER_INVALID", None
    probed = _probed_str(value)
    if probed is None:
        return "IDENTIFIER_INVALID", None
    value = probed
    if any(ord(char) < 32 for char in value):
        return "IDENTIFIER_INVALID", None
    if value == "" or value.strip() == "":
        return "IDENTIFIER_BLANK", None
    if value != value.strip():
        return "IDENTIFIER_INVALID", None
    if _deny_prefixed(value):
        return "SAFE_FIELD_SECRET_SHAPED", None
    if _url_shaped(value):
        return "SAFE_FIELD_URL_SHAPED", None
    if _path_shaped(value):
        return "SAFE_FIELD_PATH_SHAPED", None
    if len(value) > _REF_LIMIT:
        return "IDENTIFIER_TOO_LONG", None
    if _REF_RE.fullmatch(value) is None:
        return "IDENTIFIER_INVALID", None
    return None, probed


def _check_ref(value: object) -> str | None:
    """Typed rejection code for a non-conforming identifier/ref, else None."""
    return _checked_ref(value)[0]


def _checked_text(value: object) -> tuple[str | None, str | None]:
    """Typed ``(rejection_code, validated_emission_text)`` for free text.

    The emitted text is the probed plain-str view, never ``str()`` on the
    original duck value (two-faced str subclass containment).
    """
    if not isinstance(value, str):
        return "FIELD_TYPE_INVALID", None
    probed = _probed_str(value)
    if probed is None:
        return "FIELD_TYPE_INVALID", None
    value = probed
    if any(ord(char) < 32 for char in value):
        return "FIELD_TYPE_INVALID", None
    if value != value.strip():
        return "FIELD_TYPE_INVALID", None
    if _deny_prefixed(value):
        return "SAFE_FIELD_SECRET_SHAPED", None
    if _url_shaped(value):
        return "SAFE_FIELD_URL_SHAPED", None
    if _path_shaped(value):
        return "SAFE_FIELD_PATH_SHAPED", None
    if len(value) > _TEXT_LIMIT:
        return "FIELD_TOO_LONG", None
    return None, probed


def _check_text(value: object) -> str | None:
    """Safe free-text law for display/code-ish fields (no charset pin)."""
    return _checked_text(value)[0]


def _checked_digest(value: object) -> tuple[str | None, str | None]:
    """Typed ``(rejection_code, validated_emission_text)`` for digests."""
    if not isinstance(value, str):
        return "FIELD_TYPE_INVALID", None
    probed = _probed_str(value)
    if probed is None:
        return "FIELD_TYPE_INVALID", None
    if any(ord(char) < 32 for char in probed):
        return "FIELD_TYPE_INVALID", None
    if _DIGEST.fullmatch(probed) is None:
        return "DIGEST_INVALID", None
    return None, probed


def _check_digest(value: object) -> str | None:
    return _checked_digest(value)[0]


def _checked_sha(value: object) -> tuple[str | None, str | None]:
    """Typed ``(rejection_code, validated_emission_text)`` for head SHAs."""
    if not isinstance(value, str):
        return "HEAD_SHA_INVALID", None
    probed = _probed_str(value)
    if probed is None or _SHA.fullmatch(probed) is None:
        return "HEAD_SHA_INVALID", None
    return None, probed


def _check_sha(value: object) -> str | None:
    return _checked_sha(value)[0]


def _check_int(value: object) -> str | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return "FIELD_TYPE_INVALID"
    return None


def _coerce_int(value: object) -> int | None:
    """Plain-int emission view; None when not a plain coercible int.

    A hostile int subclass can carry an attacker-controlled ``__repr__``;
    emission stores plain ``int`` values only so record reprs cannot
    launder attacker text.
    """
    if type(value) is int:
        return value
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    try:
        return int(value)
    except Exception:
        return None


def _check_bool(value: object) -> str | None:
    if not isinstance(value, bool):
        return "FIELD_TYPE_INVALID"
    return None


def _tz_aware(value: datetime) -> bool:
    try:
        return value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None
    except Exception:
        return False


def _check_stamp(value: object) -> tuple[str | None, str | None]:
    """Returns (emitted_text, rejection_code). None emission = absent."""
    if value is None:
        return None, None
    if isinstance(value, datetime):
        if not _tz_aware(value):
            return None, "TIMESTAMP_NAIVE"
        try:
            return value.isoformat(), None
        except Exception:
            return None, "TIMESTAMP_INVALID"
    if not isinstance(value, str):
        return None, "TIMESTAMP_INVALID"
    probed = _probed_str(value)
    if probed is None or len(probed) > _STAMP_LIMIT:
        return None, "TIMESTAMP_INVALID"
    try:
        parsed = datetime.fromisoformat(probed.replace("Z", "+00:00"))
    except ValueError:
        return None, "TIMESTAMP_INVALID"
    if not _tz_aware(parsed):
        return None, "TIMESTAMP_NAIVE"
    return probed, None


def _enum_text(value: object) -> object:
    """Enum-like -> str text; a raising or non-str ``value`` is returned
    unchanged so the text law rejects it fail-closed."""
    if isinstance(value, str):
        return value
    try:
        text = value.value  # type: ignore[union-attr]
    except Exception:
        return value
    return text if isinstance(text, str) else value


def _scope_count(value: object) -> tuple[str | None, int]:
    """Count entries without ever reading their raw values."""
    if isinstance(value, (str, bytes, dict, set, frozenset)):
        return "COUNT_SEQUENCE_INVALID", 0
    try:
        return None, len(value)  # type: ignore[arg-type]
    except Exception:
        return "COUNT_SEQUENCE_INVALID", 0


def _tuple_text_field(
    value: object, limit: int
) -> tuple[str | None, tuple[str, ...] | None]:
    """Validate a bounded tuple of safe text entries; None tuple on error."""
    if isinstance(value, (str, bytes, dict, set, frozenset)) or value is None:
        if value is None:
            return None, ()
        return "FIELD_TYPE_INVALID", None
    try:
        entries = tuple(value)
    except Exception:
        return "FIELD_TYPE_INVALID", None
    if len(entries) > limit:
        return "TUPLE_TOO_LONG", None
    emitted: list[str] = []
    for entry in entries:
        code, entry_text = _checked_ref(entry)
        if code is None:
            emitted.append(entry_text)
            continue
        code_text, entry_text = _checked_text(entry)
        if code_text is not None:
            return code_text, None
        emitted.append(entry_text)
    return None, tuple(emitted)


def _rejection(
    surface: str, code: str, field_name: str | None, source_index: int
) -> SettingsRecordRejection:
    return SettingsRecordRejection(
        surface=surface,
        code=code,
        field=field_name,
        source_index=source_index,
    )


def _unreadable(surface: str, source_index: int) -> SettingsRecordRejection:
    return _rejection(surface, "RECORD_ATTRIBUTE_UNREADABLE", None, source_index)


def _reject_plain(record: object) -> bool:
    return record is None or isinstance(record, _PLAIN_TYPES)


def _text_fields(
    record: object,
    surface: str,
    source_index: int,
    required: tuple[str, ...],
    optional: tuple[str, ...],
    optional_free: tuple[str, ...] = (),
) -> tuple[SettingsRecordRejection | None, dict[str, str | None]]:
    """Read + validate required/optional ``_REF``-class fields and optional
    free-text fields.

    Required fields: missing -> RECORD_FIELD_MISSING; invalid -> its code.
    Optional fields: missing or explicit None -> None (absence is never
    fabricated); blank -> None; invalid -> typed rejection.
    """
    values: dict[str, str | None] = {}
    for name in required:
        status, value = _read(record, name)
        if status == "unreadable":
            return _unreadable(surface, source_index), values
        if status == "missing":
            return (
                _rejection(surface, "RECORD_FIELD_MISSING", name, source_index),
                values,
            )
        code, emitted = _checked_ref(value)
        if code == "IDENTIFIER_BLANK":
            code = "FIELD_TYPE_INVALID"
        if code:
            return _rejection(surface, code, name, source_index), values
        values[name] = emitted
    for name in optional:
        status, value = _read(record, name)
        if status == "unreadable":
            return _unreadable(surface, source_index), values
        if status == "missing" or value is None:
            values[name] = None
            continue
        code, emitted = _checked_ref(value)
        if code:
            return _rejection(surface, code, name, source_index), values
        values[name] = emitted
    for name in optional_free:
        status, value = _read(record, name)
        if status == "unreadable":
            return _unreadable(surface, source_index), values
        if status == "missing" or value is None:
            values[name] = None
            continue
        text = _enum_text(value)
        code, emitted = _checked_text(text)
        if code:
            return _rejection(surface, code, name, source_index), values
        values[name] = None if emitted == "" else emitted
    return None, values


def _optional_int_fields(
    record: object,
    surface: str,
    source_index: int,
    names: tuple[str, ...],
) -> tuple[SettingsRecordRejection | None, dict[str, int | None]]:
    values: dict[str, int | None] = {}
    for name in names:
        status, value = _read(record, name)
        if status == "unreadable":
            return _unreadable(surface, source_index), values
        if status == "missing" or value is None:
            values[name] = None
            continue
        coerced = _coerce_int(value)
        if coerced is None:
            return _rejection(surface, "FIELD_TYPE_INVALID", name, source_index), values
        values[name] = coerced
    return None, values


def _stamp_fields(
    record: object,
    surface: str,
    source_index: int,
    names: tuple[str, ...],
) -> tuple[SettingsRecordRejection | None, dict[str, str | None]]:
    values: dict[str, str | None] = {}
    for name in names:
        status, value = _read(record, name)
        if status == "unreadable":
            return _unreadable(surface, source_index), values
        if status == "missing":
            values[name] = None
            continue
        emitted, code = _check_stamp(value)
        if code:
            return _rejection(surface, code, name, source_index), values
        values[name] = emitted
    return None, values


def _derived_flag(
    record: object, name: str
) -> tuple[str, bool]:
    """Read a DENY ref solely to derive its configured boolean.

    Returns ("unreadable", False) on a raising read; ("ok", flag) otherwise.
    Missing -> False (nothing configured), blank -> False, present -> True.
    The raw value itself never projects.
    """
    status, value = _read(record, name)
    if status == "unreadable":
        return "unreadable", False
    if status == "missing" or value is None:
        return "ok", False
    if isinstance(value, str):
        probed = _probed_str(value)
        if probed is None:
            return "ok", False
        return "ok", probed.strip() != ""
    return "ok", True


# ---------------------------------------------------------------------------
# Per-surface validators
# ---------------------------------------------------------------------------


def _validate_provider(
    record: object, source_index: int
) -> SettingsProviderRecord | SettingsRecordRejection:
    """Validate one injected provider record into its display record.

    Trust boundary (F4 note): the embedded ``ProviderOperatorRow``
    (including its ``display_name``, provider_type and models metadata) is
    reused by import and trusted by contract as validated at the
    ``provider_operator_view`` boundary; this module re-validates only the
    injected metadata extras (protocol_family, schema_version, endpoint_ref,
    admission, and the credential_ref-derived boolean).
    """
    surface = "providers"
    if _reject_plain(record):
        return _rejection(surface, "RECORD_TYPE_UNSUPPORTED", None, source_index)
    row_status, row = _read(record, "row")
    if row_status == "unreadable":
        return _unreadable(surface, source_index)
    if row_status == "missing" or not isinstance(row, ProviderOperatorRow):
        return _rejection(surface, "RECORD_TYPE_UNSUPPORTED", "row", source_index)
    extras: dict[str, str | None] = {}
    for name in ("protocol_family", "schema_version"):
        status, value = _read(record, name)
        if status == "unreadable":
            return _unreadable(surface, source_index)
        if status == "missing" or value is None:
            extras[name] = None
            continue
        text = _enum_text(value)
        code, emitted = _checked_text(text)
        if code:
            return _rejection(surface, code, name, source_index)
        extras[name] = None if emitted == "" else emitted
    status, endpoint_value = _read(record, "endpoint_ref")
    if status == "unreadable":
        return _unreadable(surface, source_index)
    if status == "ok" and endpoint_value is not None:
        code, emitted = _checked_ref(endpoint_value)
        if code:
            return _rejection(surface, code, "endpoint_ref", source_index)
        extras["endpoint_ref"] = emitted
    else:
        extras["endpoint_ref"] = None
    admission_status, admission_value = _read(record, "admission")
    if admission_status == "unreadable":
        return _unreadable(surface, source_index)
    admission: SettingsAdmissionRecord | None = None
    if admission_status == "ok" and admission_value is not None:
        if _reject_plain(admission_value):
            return _rejection(
                surface, "RECORD_TYPE_UNSUPPORTED", "admission", source_index
            )
        outcome, admission = _build_admission(
            admission_value, surface, source_index
        )
        if outcome is not None:
            return outcome
    cred_status, credential_configured = _derived_flag(record, "credential_ref")
    if cred_status == "unreadable":
        return _unreadable(surface, source_index)
    return SettingsProviderRecord(
        row=row,
        protocol_family=extras["protocol_family"],
        schema_version=extras["schema_version"],
        endpoint_ref=extras["endpoint_ref"],
        admission=admission,
        credential_configured=credential_configured,
    )


def _build_admission(
    admission: object, surface: str, source_index: int
) -> tuple[SettingsRecordRejection | None, SettingsAdmissionRecord | None]:
    id_status, admission_id = _read(admission, "admission_id")
    if id_status == "unreadable":
        return _unreadable(surface, source_index), None
    if id_status == "missing":
        return (
            _rejection(surface, "RECORD_FIELD_MISSING", "admission_id", source_index),
            None,
        )
    code, admission_text = _checked_ref(admission_id)
    if code:
        return _rejection(surface, code, "admission_id", source_index), None
    status_outcome, status_values = _text_fields(
        admission,
        surface,
        source_index,
        required=(),
        optional=("status",),
    )
    if status_outcome is not None:
        return status_outcome, None
    stamps_outcome, stamps = _stamp_fields(
        admission,
        surface,
        source_index,
        names=("acquired_at", "expires_at", "released_at", "reconciled_at"),
    )
    if stamps_outcome is not None:
        return stamps_outcome, None
    gen_status, generation = _read(admission, "configuration_generation")
    if gen_status == "unreadable":
        return _unreadable(surface, source_index), None
    generation_value: int | None = None
    if gen_status == "ok" and generation is not None:
        generation_value = _coerce_int(generation)
        if generation_value is None:
            return (
                _rejection(
                    surface, "GENERATION_INVALID", "configuration_generation",
                    source_index,
                ),
                None,
            )
    return None, SettingsAdmissionRecord(
        admission_id=admission_text or "",
        status=status_values["status"],
        acquired_at=stamps["acquired_at"],
        expires_at=stamps["expires_at"],
        released_at=stamps["released_at"],
        reconciled_at=stamps["reconciled_at"],
        configuration_generation=generation_value,
    )


_HOOK_REQUIRED = ("event_id", "event_type")
_HOOK_REFS = (
    "action",
    "source",
    "source_version",
    "device_id",
    "lane_id",
    "task_id",
    "work_order",
    "claim_ref",
    "execution_id",
    "harness_id",
    "model_id",
    "dedupe_key",
    "correlation_id",
    "causation_id",
    "command_ref",
)
_HOOK_TEXT = (
    "hook_class",
    "phase",
    "domain",
    "host_os",
    "privacy_class",
    "task_topology",
    "effort",
    "state",
    "blocker_code",
)
_HOOK_INTS = ("duration_ms", "sequence")


def _build_adapter(
    adapter: object, surface: str, source_index: int
) -> tuple[SettingsRecordRejection | None, SettingsHookAdapter | None]:
    outcome, values = _text_fields(
        adapter,
        surface,
        source_index,
        required=("adapter_id",),
        optional=("adapter_version",),
        optional_free=("contract_version", "redaction_policy"),
    )
    if outcome is not None:
        return outcome, None
    seq_status, supports_sequence = _read(adapter, "supports_sequence")
    if seq_status == "unreadable":
        return _unreadable(surface, source_index), None
    if seq_status == "missing":
        supports_sequence = False
    code = _check_bool(supports_sequence)
    if code:
        return _rejection(surface, code, "supports_sequence", source_index), None
    return None, SettingsHookAdapter(
        adapter_id=values["adapter_id"] or "",
        adapter_version=values["adapter_version"],
        contract_version=values["contract_version"],
        redaction_policy=values["redaction_policy"],
        supports_sequence=bool(supports_sequence),
    )


def _build_guard(
    guard: object, surface: str, source_index: int
) -> tuple[SettingsRecordRejection | None, SettingsHookGuard | None]:
    outcome, values = _text_fields(
        guard,
        surface,
        source_index,
        required=(),
        optional=(),
        optional_free=("failure_policy", "security_scope", "authority_scope"),
    )
    if outcome is not None:
        return outcome, None
    return None, SettingsHookGuard(
        failure_policy=values["failure_policy"],
        security_scope=values["security_scope"],
        authority_scope=values["authority_scope"],
    )


def _validate_hook(
    record: object, source_index: int
) -> SettingsHookActivityRecord | SettingsRecordRejection:
    surface = "hook_activity"
    if _reject_plain(record):
        return _rejection(surface, "RECORD_TYPE_UNSUPPORTED", None, source_index)
    outcome, values = _text_fields(
        record, surface, source_index, _HOOK_REQUIRED, _HOOK_REFS, _HOOK_TEXT
    )
    if outcome is not None:
        return outcome
    ints_outcome, ints = _optional_int_fields(record, surface, source_index, _HOOK_INTS)
    if ints_outcome is not None:
        return ints_outcome
    stamps_outcome, stamps = _stamp_fields(
        record, surface, source_index, names=("occurred_at",)
    )
    if stamps_outcome is not None:
        return stamps_outcome
    head_status, head = _read(record, "head_sha")
    if head_status == "unreadable":
        return _unreadable(surface, source_index)
    head_value: str | None = None
    if head_status == "ok" and head is not None:
        code, emitted = _checked_sha(head)
        if code:
            return _rejection(surface, code, "head_sha", source_index)
        head_value = emitted
    digest_outcome, digests = _digest_fields(
        record, surface, source_index, names=("evidence_digest", "command_digest")
    )
    if digest_outcome is not None:
        return digest_outcome
    refs_outcome, evidence_refs = _tuple_text_field_wrapped(
        _read_or_none(record, "evidence_refs"), surface, source_index,
        "evidence_refs", _TUPLE_LIMIT,
    )
    if refs_outcome is not None:
        return refs_outcome
    markers_outcome, markers = _tuple_text_field_wrapped(
        _read_or_none(record, "markers"), surface, source_index,
        "markers", _TUPLE_LIMIT,
    )
    if markers_outcome is not None:
        return markers_outcome
    adapter: SettingsHookAdapter | None = None
    adapter_status, adapter_value = _read(record, "adapter")
    if adapter_status == "unreadable":
        return _unreadable(surface, source_index)
    if adapter_status == "ok" and adapter_value is not None:
        if _reject_plain(adapter_value):
            return _rejection(
                surface, "RECORD_TYPE_UNSUPPORTED", "adapter", source_index
            )
        adapter_outcome, adapter = _build_adapter(
            adapter_value, surface, source_index
        )
        if adapter_outcome is not None:
            return adapter_outcome
    guard: SettingsHookGuard | None = None
    guard_status, guard_value = _read(record, "guard")
    if guard_status == "unreadable":
        return _unreadable(surface, source_index)
    if guard_status == "ok" and guard_value is not None:
        if _reject_plain(guard_value):
            return _rejection(surface, "RECORD_TYPE_UNSUPPORTED", "guard", source_index)
        guard_outcome, guard = _build_guard(guard_value, surface, source_index)
        if guard_outcome is not None:
            return guard_outcome
    return SettingsHookActivityRecord(
        event_id=values["event_id"] or "",
        event_type=values["event_type"],
        hook_class=values["hook_class"],
        phase=values["phase"],
        domain=values["domain"],
        action=values["action"],
        occurred_at=stamps["occurred_at"],
        source=values["source"],
        source_version=values["source_version"],
        device_id=values["device_id"],
        host_os=values["host_os"],
        privacy_class=values["privacy_class"],
        lane_id=values["lane_id"],
        task_id=values["task_id"],
        work_order=values["work_order"],
        task_topology=values["task_topology"],
        head_sha=head_value,
        claim_ref=values["claim_ref"],
        execution_id=values["execution_id"],
        harness_id=values["harness_id"],
        model_id=values["model_id"],
        effort=values["effort"],
        state=values["state"],
        duration_ms=ints["duration_ms"],
        blocker_code=values["blocker_code"],
        sequence=ints["sequence"],
        dedupe_key=values["dedupe_key"],
        correlation_id=values["correlation_id"],
        causation_id=values["causation_id"],
        evidence_refs=evidence_refs or (),
        evidence_digest=digests["evidence_digest"],
        command_digest=digests["command_digest"],
        command_ref=values["command_ref"],
        markers=markers or (),
        adapter=adapter,
        guard=guard,
    )


def _read_or_none(record: object, name: str) -> object:
    status, value = _read(record, name)
    if status != "ok":
        return () if status == "missing" else _UNREADABLE
    return value


_UNREADABLE = object()


def _tuple_text_field_wrapped(
    value: object, surface: str, source_index: int, field_name: str, limit: int
) -> tuple[SettingsRecordRejection | None, tuple[str, ...] | None]:
    if value is _UNREADABLE:
        return _unreadable(surface, source_index), None
    outcome, emitted = _tuple_text_field(value, limit)
    if outcome is not None:
        return _rejection(surface, outcome, field_name, source_index), None
    return None, emitted or ()


def _digest_fields(
    record: object,
    surface: str,
    source_index: int,
    names: tuple[str, ...],
) -> tuple[SettingsRecordRejection | None, dict[str, str | None]]:
    values: dict[str, str | None] = {}
    for name in names:
        status, value = _read(record, name)
        if status == "unreadable":
            return _unreadable(surface, source_index), values
        if status == "missing" or value is None:
            values[name] = None
            continue
        code, emitted = _checked_digest(value)
        if code:
            return _rejection(surface, code, name, source_index), values
        values[name] = emitted
    return None, values


def _validate_control(
    record: object, source_index: int
) -> SettingsControlActivityRecord | SettingsRecordRejection:
    surface = "control_activity"
    if _reject_plain(record):
        return _rejection(surface, "RECORD_TYPE_UNSUPPORTED", None, source_index)
    outcome, values = _text_fields(
        record,
        surface,
        source_index,
        required=("event_id", "event_type", "worker_id", "project_id"),
        optional=(),
    )
    if outcome is not None:
        return outcome
    stamps_outcome, stamps = _stamp_fields(
        record, surface, source_index, names=("recorded_at",)
    )
    if stamps_outcome is not None:
        return stamps_outcome
    return SettingsControlActivityRecord(
        event_id=values["event_id"] or "",
        event_type=values["event_type"],
        worker_id=values["worker_id"],
        project_id=values["project_id"],
        recorded_at=stamps["recorded_at"],
    )


def _validate_execution(
    record: object, source_index: int
) -> SettingsExecutionActivityRecord | SettingsRecordRejection:
    surface = "execution_activity"
    if _reject_plain(record):
        return _rejection(surface, "RECORD_TYPE_UNSUPPORTED", None, source_index)
    seq_status, sequence_no = _read(record, "sequence_no")
    if seq_status == "unreadable":
        return _unreadable(surface, source_index)
    if seq_status == "missing":
        return (
            _rejection(surface, "RECORD_FIELD_MISSING", "sequence_no", source_index),
            None,
        )[0]
    sequence_value = _coerce_int(sequence_no)
    if sequence_value is None:
        return _rejection(surface, "FIELD_TYPE_INVALID", "sequence_no", source_index)
    outcome, values = _text_fields(
        record,
        surface,
        source_index,
        required=("event_id", "execution_id", "event_type"),
        optional=(),
        optional_free=("transport_state", "execution_state"),
    )
    if outcome is not None:
        return outcome
    ints_outcome, ints = _optional_int_fields(
        record, surface, source_index, names=("pid", "exit_code")
    )
    if ints_outcome is not None:
        return ints_outcome
    stamps_outcome, stamps = _stamp_fields(
        record,
        surface,
        source_index,
        names=("started_at", "finished_at", "recorded_at"),
    )
    if stamps_outcome is not None:
        return stamps_outcome
    return SettingsExecutionActivityRecord(
        event_id=values["event_id"] or "",
        execution_id=values["execution_id"] or "",
        sequence_no=sequence_value,
        event_type=values["event_type"],
        transport_state=values["transport_state"],
        execution_state=values["execution_state"],
        pid=ints["pid"],
        exit_code=ints["exit_code"],
        started_at=stamps["started_at"],
        finished_at=stamps["finished_at"],
        recorded_at=stamps["recorded_at"],
    )


def _validate_mutation(
    record: object, source_index: int
) -> SettingsMutationAuditRecord | SettingsRecordRejection:
    surface = "mutation_audit"
    if _reject_plain(record):
        return _rejection(surface, "RECORD_TYPE_UNSUPPORTED", None, source_index)
    worker_status, worker_id = _read(record, "worker_id")
    if worker_status == "unreadable":
        return _unreadable(surface, source_index)
    connector_status, connector_id = _read(record, "connector_id")
    if connector_status == "unreadable":
        return _unreadable(surface, source_index)
    actor_kind = "worker"
    actor_value: object = None
    if worker_status == "ok" and worker_id is not None:
        actor_value = worker_id
    elif connector_status == "ok" and connector_id is not None:
        actor_kind = "connector"
        actor_value = connector_id
    else:
        return (
            _rejection(
                surface, "RECORD_FIELD_MISSING", "worker_id", source_index
            ),
            None,
        )[0]
    code, actor_text = _checked_ref(actor_value)
    if code:
        return _rejection(surface, code, "actor_id", source_index)
    outcome, values = _text_fields(
        record, surface, source_index, required=("action",), optional=()
    )
    if outcome is not None:
        return outcome
    stamps_outcome, stamps = _stamp_fields(record, surface, source_index, names=("at",))
    if stamps_outcome is not None:
        return stamps_outcome
    return SettingsMutationAuditRecord(
        actor_id=actor_text or "",
        actor_kind=actor_kind,
        action=values["action"],
        at=stamps["at"],
    )


_TOOL_TUPLES = (
    "excluded_tools",
    "included_optional_tools",
    "fixed_tools",
    "base_modes",
    "enabled_languages",
)


def _validate_brain(
    record: object, source_index: int
) -> SettingsWorkerBrainRecord | SettingsRecordRejection:
    surface = "worker_brain"
    if _reject_plain(record):
        return _rejection(surface, "RECORD_TYPE_UNSUPPORTED", None, source_index)
    outcome, values = _text_fields(
        record, surface, source_index, required=("worker_id",), optional=()
    )
    if outcome is not None:
        return outcome
    language_status, language_backend = _read(record, "language_backend")
    if language_status == "unreadable":
        return _unreadable(surface, source_index)
    language_value: str | None = None
    if language_status == "ok" and language_backend is not None:
        text = _enum_text(language_backend)
        code, emitted = _checked_text(text)
        if code:
            return _rejection(surface, code, "language_backend", source_index)
        language_value = None if emitted == "" else emitted
    timeout_outcome, timeouts = _optional_int_fields(
        record, surface, source_index, names=("tool_timeout",)
    )
    if timeout_outcome is not None:
        return timeout_outcome
    tool_values: dict[str, tuple[str, ...]] = {}
    for name in _TOOL_TUPLES:
        outcome2, emitted = _tuple_text_field_wrapped(
            _read_or_none(record, name), surface, source_index, name,
            _TOOL_TUPLE_LIMIT,
        )
        if outcome2 is not None:
            return outcome2
        tool_values[name] = emitted or ()
    counts: dict[str, int] = {}
    for name in ("brain_folders", "brain_entry_files"):
        status, value = _read(record, name)
        if status == "unreadable":
            return _unreadable(surface, source_index)
        if status == "missing":
            counts[name] = 0
            continue
        code, count = _scope_count(value)
        if code:
            return _rejection(surface, code, name, source_index)
        counts[name] = count
    return SettingsWorkerBrainRecord(
        worker_id=values["worker_id"] or "",
        language_backend=language_value,
        tool_timeout=timeouts["tool_timeout"],
        excluded_tools=tool_values["excluded_tools"],
        included_optional_tools=tool_values["included_optional_tools"],
        fixed_tools=tool_values["fixed_tools"],
        base_modes=tool_values["base_modes"],
        enabled_languages=tool_values["enabled_languages"],
        brain_folder_count=counts["brain_folders"],
        brain_entry_count=counts["brain_entry_files"],
        settings_version=_NOT_CARRIED,
    )


def _validate_runtime(
    record: object, source_index: int
) -> SettingsWorkerRuntimeRecord | SettingsRecordRejection:
    surface = "worker_runtime"
    if _reject_plain(record):
        return _rejection(surface, "RECORD_TYPE_UNSUPPORTED", None, source_index)
    outcome, values = _text_fields(
        record, surface, source_index, required=("worker_id", "runtime_id"), optional=()
    )
    if outcome is not None:
        return outcome
    port_status, health_port = _read(record, "health_port")
    if port_status == "unreadable":
        return _unreadable(surface, source_index)
    port_value: int | None = None
    if port_status == "ok" and health_port is not None:
        port_value = _coerce_int(health_port)
        if port_value is None or not 1 <= port_value <= 65535:
            return _rejection(surface, "FIELD_TYPE_INVALID", "health_port", source_index)
    timeouts_outcome, timeouts = _optional_int_fields(
        record,
        surface,
        source_index,
        names=("startup_timeout_seconds", "stop_timeout_seconds"),
    )
    if timeouts_outcome is not None:
        return timeouts_outcome
    tunnel_status, tunnel_binding_configured = _derived_flag(
        record, "tunnel_binding_ref"
    )
    if tunnel_status == "unreadable":
        return _unreadable(surface, source_index)
    return SettingsWorkerRuntimeRecord(
        worker_id=values["worker_id"] or "",
        runtime_id=values["runtime_id"] or "",
        health_port=port_value,
        startup_timeout_seconds=timeouts["startup_timeout_seconds"],
        stop_timeout_seconds=timeouts["stop_timeout_seconds"],
        tunnel_binding_configured=tunnel_binding_configured,
    )


def _validate_binding(
    record: object, source_index: int
) -> SettingsProjectBindingRecord | SettingsRecordRejection:
    surface = "project_bindings"
    if _reject_plain(record):
        return _rejection(surface, "RECORD_TYPE_UNSUPPORTED", None, source_index)
    outcome, values = _text_fields(
        record,
        surface,
        source_index,
        required=("project_id",),
        optional=(),
        optional_free=("identity_policy", "expected_branch"),
    )
    if outcome is not None:
        return outcome
    head_status, expected_head = _read(record, "expected_head")
    if head_status == "unreadable":
        return _unreadable(surface, source_index)
    head_value: str | None = None
    if head_status == "ok" and expected_head is not None:
        code, emitted = _checked_sha(expected_head)
        if code:
            return _rejection(surface, code, "expected_head", source_index)
        head_value = emitted
    mutation_status, mutation_allowed = _read(record, "mutation_allowed")
    if mutation_status == "unreadable":
        return _unreadable(surface, source_index)
    if mutation_status == "missing":
        mutation_allowed = False
    code = _check_bool(mutation_allowed)
    if code:
        return _rejection(surface, code, "mutation_allowed", source_index)
    return SettingsProjectBindingRecord(
        project_id=values["project_id"] or "",
        identity_policy=values["identity_policy"],
        expected_branch=values["expected_branch"],
        expected_head=head_value,
        mutation_allowed=bool(mutation_allowed),
    )


def _validate_reference_group(
    record: object, source_index: int
) -> SettingsLocalReferenceRecord | SettingsRecordRejection:
    surface = "local_references"
    if _reject_plain(record):
        return _rejection(surface, "RECORD_TYPE_UNSUPPORTED", None, source_index)
    id_status, reference_id = _read(record, "reference_id")
    if id_status == "unreadable":
        return _unreadable(surface, source_index)
    if id_status == "missing":
        return (
            _rejection(surface, "RECORD_FIELD_MISSING", "reference_id", source_index),
            None,
        )[0]
    code, reference_text = _checked_ref(reference_id)
    if code:
        return _rejection(surface, code, "reference_id", source_index)
    counts: dict[str, int] = {}
    for name in ("paths", "roots"):
        status, value = _read(record, name)
        if status == "unreadable":
            return _unreadable(surface, source_index)
        if status == "missing":
            counts[name] = 0
            continue
        code, count = _scope_count(value)
        if code:
            return _rejection(surface, code, name, source_index)
        counts[name] = count
    return SettingsLocalReferenceRecord(
        reference_id=reference_text or "",
        reference_count=counts["paths"],
        root_count=counts["roots"],
    )


def _validate_registry(
    record: object, source_index: int
) -> SettingsRegistryRecord | SettingsRecordRejection:
    surface = "registry"
    if _reject_plain(record):
        return _rejection(surface, "RECORD_TYPE_UNSUPPORTED", None, source_index)
    outcome, values = _text_fields(
        record,
        surface,
        source_index,
        required=("project_id", "assignment_id"),
        optional=("worker_id", "runtime_id"),
        optional_free=("display_name", "worker_display_name", "state"),
    )
    if outcome is not None:
        return outcome
    mutation_status, mutation_allowed = _read(record, "mutation_allowed")
    if mutation_status == "unreadable":
        return _unreadable(surface, source_index)
    if mutation_status == "missing":
        mutation_allowed = False
    code = _check_bool(mutation_allowed)
    if code:
        return _rejection(surface, code, "mutation_allowed", source_index)
    return SettingsRegistryRecord(
        project_id=values["project_id"] or "",
        display_name=values["display_name"],
        worker_id=values["worker_id"],
        worker_display_name=values["worker_display_name"],
        runtime_id=values["runtime_id"],
        state=values["state"],
        assignment_id=values["assignment_id"] or "",
        mutation_allowed=bool(mutation_allowed),
    )


def _validate_network(
    record: object, source_index: int
) -> SettingsNetworkPolicyRecord | SettingsRecordRejection:
    surface = "network_policy"
    if _reject_plain(record):
        return _rejection(surface, "RECORD_TYPE_UNSUPPORTED", None, source_index)
    outcome, values = _text_fields(
        record,
        surface,
        source_index,
        required=(),
        optional=(),
        optional_free=("privacy_class", "network_policy"),
    )
    if outcome is not None:
        return outcome
    secret_status, secret_access = _read(record, "secret_access")
    if secret_status == "unreadable":
        return _unreadable(surface, source_index)
    if secret_status == "missing":
        secret_access = False
    code = _check_bool(secret_access)
    if code:
        return _rejection(surface, code, "secret_access", source_index)
    allow_status, allowlist = _read(record, "network_allowlist")
    if allow_status == "unreadable":
        return _unreadable(surface, source_index)
    allow_count = 0
    if allow_status == "ok" and allowlist is not None:
        code, count = _scope_count(allowlist)
        if code:
            return _rejection(surface, code, "network_allowlist", source_index)
        allow_count = count
    reason_status, reason_code = _read(record, "reason_code")
    if reason_status == "unreadable":
        return _unreadable(surface, source_index)
    reason_value: str | None = None
    if reason_status == "ok" and reason_code is not None:
        text = _enum_text(reason_code)
        probed = _probed_str(text) if isinstance(text, str) else None
        if probed is None or probed not in _NETWORK_REASON_CODES:
            return _rejection(surface, "REASON_CODE_INVALID", "reason_code", source_index)
        reason_value = probed
    return SettingsNetworkPolicyRecord(
        privacy_class=values["privacy_class"],
        network_policy=values["network_policy"],
        secret_access=bool(secret_access),
        network_allowlist_count=allow_count,
        reason_code=reason_value,
    )


# ---------------------------------------------------------------------------
# Frame assembly
# ---------------------------------------------------------------------------


def _degraded_group(kind: str) -> SettingsSurfaceGroup:
    return SettingsSurfaceGroup(
        kind=kind,
        state="DEGRADED",
        reason="SURFACE_INPUT_INVALID",
        records=(),
        rejections=(),
        dropped_count=0,
        truncated=False,
    )


def _project_surface(kind: str, inputs: object, validate) -> SettingsSurfaceGroup:
    if not isinstance(inputs, (list, tuple)):
        return _degraded_group(kind)
    records: list = []
    rejections: list[SettingsRecordRejection] = []
    try:
        for index, record in enumerate(inputs):
            outcome = validate(record, index)
            if isinstance(outcome, SettingsRecordRejection):
                rejections.append(outcome)
            else:
                records.append(outcome)
    except Exception:
        # F2 containment: a hostile list/tuple subclass may raise from
        # ``__iter__`` mid-iteration. Already-validated records/rejections
        # are trivially safe to keep; the group degrades with a typed
        # reason instead of letting the raw exception escape.
        return SettingsSurfaceGroup(
            kind=kind,
            state="DEGRADED",
            reason="SURFACE_INPUT_INVALID",
            records=tuple(records[:_FRAME_ROW_LIMIT]),
            rejections=tuple(rejections[:_REJECTION_LIMIT]),
            dropped_count=0,
            truncated=False,
        )
    truncated = len(records) > _FRAME_ROW_LIMIT or len(rejections) > _REJECTION_LIMIT
    dropped_count = max(0, len(records) - _FRAME_ROW_LIMIT) + max(
        0, len(rejections) - _REJECTION_LIMIT
    )
    reason = "FRAME_ROW_LIMIT_EXCEEDED" if truncated else None
    return SettingsSurfaceGroup(
        kind=kind,
        state="OK",
        reason=reason,
        records=tuple(records[:_FRAME_ROW_LIMIT]),
        rejections=tuple(rejections[:_REJECTION_LIMIT]),
        dropped_count=dropped_count,
        truncated=truncated,
    )


def _validate_now(now: object) -> datetime | None:
    if now is None:
        return None
    if not isinstance(now, datetime) or not _tz_aware(now):
        raise SettingsProjectionError("SETTINGS_NOW_MUST_BE_TZ_AWARE")
    return now


def project_settings_activity_view(
    *,
    providers: object = (),
    hook_records: object = (),
    control_events: object = (),
    execution_events: object = (),
    mutation_audits: object = (),
    worker_brain_settings: object = (),
    worker_runtime_configs: object = (),
    project_bindings: object = (),
    local_reference_groups: object = (),
    registry_entries: object = (),
    network_policies: object = (),
    now: object = None,
) -> SettingsActivityView:
    """Compose the eleven safe-logs / effective-settings surface groups.

    Injected records are untrusted data: every attribute read is wrapped,
    DENY-bearing attributes are never read, malformed records become typed
    per-record rejections whose neighbors survive, and the result is a pure
    value carrying no mutation, claim, or completion authority. ``now`` is
    injectable (wall clock is never read); it must be a timezone-aware
    :class:`datetime` when provided, otherwise ``SettingsProjectionError``.
    """
    _validate_now(now)
    return SettingsActivityView(
        providers=_project_surface(
            "providers", providers, _validate_provider
        ),
        hook_activity=_project_surface(
            "hook_activity", hook_records, _validate_hook
        ),
        control_activity=_project_surface(
            "control_activity", control_events, _validate_control
        ),
        execution_activity=_project_surface(
            "execution_activity", execution_events, _validate_execution
        ),
        mutation_audit=_project_surface(
            "mutation_audit", mutation_audits, _validate_mutation
        ),
        worker_brain=_project_surface(
            "worker_brain", worker_brain_settings, _validate_brain
        ),
        worker_runtime=_project_surface(
            "worker_runtime", worker_runtime_configs, _validate_runtime
        ),
        project_bindings=_project_surface(
            "project_bindings", project_bindings, _validate_binding
        ),
        local_references=_project_surface(
            "local_references", local_reference_groups, _validate_reference_group
        ),
        registry=_project_surface("registry", registry_entries, _validate_registry),
        network_policy=_project_surface(
            "network_policy", network_policies, _validate_network
        ),
    )
