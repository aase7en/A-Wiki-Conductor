"""Fleet/work identity read DTO — pure projection (WO-P1-763, SFU26 card 03).

Composes typed per-source-class record groups from injected records:

- A-Wiki claim bindings (safe handles only; raw worktree/scope values never
  project — scope is a count; expiry is typed ``EXPIRY_UNKNOWN`` because the
  upstream binding carries no timestamps);
- cockpit lease observations, passed through by reference
  (``CockpitLeaseObservation`` is imported, never redefined);
- app-session worker/connector records (label ``app-session``; worker state
  typed ``UNKNOWN``, connector state as recorded; never fleet-ready);
- local instances (name, tunnel pairing aid, health; machine paths excluded;
  age typed ``NOT_CARRIED``);
- remote devices: absent from this topology — one constant typed record.

Cross-source identity joins are provable-only (same branch + head across a
claim and a lease); divergences become typed ``IDENTITY_CONFLICT`` records
that name the divergent fields and are never merged. Duplicate ids dedup
first-wins per class with ``duplicate_count``. Malformed injected records
become per-record typed rejections with a code only (no diagnostic value
echo); valid neighbors survive. Every attribute read on injected records is
wrapped: a raising property becomes a typed rejection, never an exception
escape. Identifier handles (claim/task/lease/worker/session and instance
ids) are opaque handles held to the same path-shape law as other safe text
fields: a path-shaped id is rejected, never projected. Emitted frames are
bounded at 256 rows per group.

The module performs no I/O, reads no wall clock (``now`` is injectable), and
imports no ambient-system, network, storage, or provider machinery. All emitted
dataclasses are frozen with slots and carry a pinned ``non_authoritative``
flag set at class definition time: this projection is display/read context,
never mutation or claim authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from dataclasses import replace as _dc_replace
from datetime import datetime

from .cockpit_projection import CockpitLeaseObservation

__all__ = [
    "FleetAppSessionRecord",
    "FleetClaimRecord",
    "FleetIdentityConflict",
    "FleetIdentityLink",
    "FleetIdentitySummary",
    "FleetLeaseRecord",
    "FleetLocalInstanceRecord",
    "FleetRecordGroup",
    "FleetRecordRejection",
    "FleetRemoteDeviceRecord",
    "FleetView",
    "project_fleet_view",
]

_FRAME_ROW_LIMIT = 256
_SHA = re.compile(r"[0-9a-f]{40}")
_DRIVE = re.compile(r"^[A-Za-z]:")

_LEASE_HEALTH_STATES = frozenset({"ACTIVE", "STALE", "EXPIRY_UNKNOWN", "QUARANTINED"})
_LOCAL_HEALTH_STATES = frozenset({"READY", "STOPPED", "UNKNOWN"})
_SESSION_STATES = frozenset({"STOPPED", "UNKNOWN"})
_SESSION_ID_ATTRS = ("id", "session_id", "worker_id", "connector_id")
_SESSION_LABEL_ATTRS = ("display_name", "label", "name")

_CLAIM_PROVENANCE = "AWIKI_CLAIM_BINDING"
_LEASE_GROUP_PROVENANCE = "COCKPIT_LEASE_OBSERVATION"
_SESSION_GROUP_PROVENANCE = "APP_SESSION_RECORD"
_INSTANCE_GROUP_PROVENANCE = "LOCAL_INSTANCE_RECORD"
_REMOTE_GROUP_PROVENANCE = "AWC_TOPOLOGY_CONSTANT"
_REMOTE_UNAVAILABLE_REASON = "REMOTE_DEVICE_OBSERVATION_UNAVAILABLE"
_CLAIM_EXPIRY = "EXPIRY_UNKNOWN"
_INSTANCE_STALENESS = "NOT_CARRIED"

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


@dataclass(frozen=True, slots=True)
class FleetClaimRecord:
    claim_id: str = ""
    task_id: str = ""
    agent: str = ""
    generation: int = 0
    branch: str = ""
    head_sha: str = ""
    repository: str = ""
    scope_count: int = 0
    expiry: str = _CLAIM_EXPIRY
    provenance: str = _CLAIM_PROVENANCE
    duplicate_count: int = 0
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class FleetLeaseRecord:
    available: bool = False
    provenance: str | None = None
    reason: str | None = None
    observation: CockpitLeaseObservation | None = None
    duplicate_count: int = 0
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class FleetAppSessionRecord:
    kind: str = "worker"
    session_id: str = ""
    label: str = ""
    created_at: str | None = None
    scope: str = "app-session"
    state: str = "UNKNOWN"
    age_seconds: float | None = None
    staleness: str | None = None
    duplicate_count: int = 0
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class FleetLocalInstanceRecord:
    name: str = ""
    tunnel_configured: bool = False
    tunnel_suffix: str = ""
    health: str = "UNKNOWN"
    staleness: str = _INSTANCE_STALENESS
    duplicate_count: int = 0
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class FleetRemoteDeviceRecord:
    state: str = "UNKNOWN"
    reason: str = _REMOTE_UNAVAILABLE_REASON
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class FleetRecordRejection:
    source_class: str = ""
    code: str = ""
    field: str | None = None
    source_index: int = 0
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class FleetIdentityLink:
    claim_id: str = ""
    lease_id: str = ""
    branch: str = ""
    head_sha: str = ""
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class FleetIdentityConflict:
    code: str = "IDENTITY_CONFLICT"
    divergent_fields: tuple[str, ...] = ()
    claim_ids: tuple[str, ...] = ()
    lease_ids: tuple[str, ...] = ()
    task_id: str | None = None
    branch: str | None = None
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class FleetIdentitySummary:
    links: tuple[FleetIdentityLink, ...] = ()
    conflicts: tuple[FleetIdentityConflict, ...] = ()
    links_truncated: bool = False
    conflicts_truncated: bool = False
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class FleetRecordGroup:
    kind: str = ""
    available: bool = True
    provenance: str | None = None
    reason: str | None = None
    records: tuple = ()
    rejections: tuple[FleetRecordRejection, ...] = ()
    duplicate_count: int = 0
    truncated: bool = False
    non_authoritative: bool = dc_field(init=False, default=True)


@dataclass(frozen=True, slots=True)
class FleetView:
    claims: FleetRecordGroup = dc_field(default_factory=FleetRecordGroup)
    leases: FleetRecordGroup = dc_field(default_factory=FleetRecordGroup)
    worker_sessions: FleetRecordGroup = dc_field(default_factory=FleetRecordGroup)
    connector_sessions: FleetRecordGroup = dc_field(default_factory=FleetRecordGroup)
    local_instances: FleetRecordGroup = dc_field(default_factory=FleetRecordGroup)
    remote_devices: FleetRecordGroup = dc_field(default_factory=FleetRecordGroup)
    identity: FleetIdentitySummary = dc_field(default_factory=FleetIdentitySummary)
    non_authoritative: bool = dc_field(init=False, default=True)


def _read(record: object, name: str) -> tuple[str, object]:
    """Wrapped duck access returning ("ok"|"missing"|"unreadable", value)."""
    try:
        value = getattr(record, name, _MISSING)
    except Exception:
        return "unreadable", None
    if value is _MISSING:
        return "missing", None
    return "ok", value


def _first_attr(
    record: object, names: tuple[str, ...]
) -> tuple[str, str | None, object]:
    for name in names:
        status, value = _read(record, name)
        if status == "unreadable":
            return "unreadable", name, None
        if status == "ok":
            return "ok", name, value
    return "missing", None, None


def _reject_plain(record: object) -> bool:
    return record is None or isinstance(record, _PLAIN_TYPES)


def _path_shaped(value: str) -> bool:
    if "\\" in value or value.startswith("/") or value.startswith("~"):
        return True
    if _DRIVE.match(value):
        return True
    return ".." in value.split("/")


def _probed_str(value: str) -> str | None:
    """Safe plain-str view of a text value; None for a lying str subclass.

    A plain ``str`` is returned as-is. A ``str`` subclass is probed through
    its derived views first (iteration and length are wrapped), so a
    two-faced subclass raising from ``__iter__``/``__len__`` — or one whose
    length disagrees with its iteration — yields None for typed rejection
    instead of escaping as a raw exception.
    """
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


def _check_text(value: object) -> str | None:
    """Typed rejection code for a non-conforming text field, else None.

    Text checks are narrowed against str subclasses: a subclass whose
    ``__iter__``/``__len__`` raise is a typed rejection, never an escape.
    """
    if not isinstance(value, str):
        return "IDENTIFIER_INVALID"
    value = _probed_str(value)
    if value is None:
        return "IDENTIFIER_INVALID"
    if any(ord(char) < 32 for char in value):
        return "IDENTIFIER_INVALID"
    if len(value) > 256:
        return "IDENTIFIER_TOO_LONG"
    if value.strip() == "":
        return "IDENTIFIER_BLANK"
    if value != value.strip():
        return "IDENTIFIER_INVALID"
    if _path_shaped(value):
        return "SAFE_FIELD_PATH_SHAPED"
    return None


def _tz_aware(value: datetime) -> bool:
    """Timezone awareness with liar-tzinfo containment (raise -> naive)."""
    try:
        return value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None
    except Exception:
        return False


def _parse_stamp(value: object) -> tuple[str, datetime | None]:
    """Returns ("ok", dt) | ("naive", None) | ("invalid", None)."""
    if isinstance(value, datetime):
        if not _tz_aware(value):
            return "naive", None
        return "ok", value
    if not isinstance(value, str):
        return "invalid", None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return "invalid", None
    if not _tz_aware(parsed):
        return "naive", None
    return "ok", parsed


def _scope_count(value: object) -> tuple[str | None, int]:
    """Count scope entries without ever reading their raw values."""
    if isinstance(value, (str, bytes, dict, set, frozenset)):
        return "SCOPE_SEQUENCE_INVALID", 0
    try:
        return None, len(value)  # type: ignore[arg-type]
    except Exception:
        return "SCOPE_SEQUENCE_INVALID", 0


def _rejection(
    source_class: str, code: str, field_name: str | None, source_index: int
) -> FleetRecordRejection:
    return FleetRecordRejection(
        source_class=source_class,
        code=code,
        field=field_name,
        source_index=source_index,
    )


def _unreadable(
    source_class: str, source_index: int
) -> FleetRecordRejection:
    return _rejection(
        source_class, "RECORD_ATTRIBUTE_UNREADABLE", None, source_index
    )


def _enum_text(value: object) -> object:
    """Enum-like -> str text; a raising or non-str ``value`` returns the
    object unchanged so health classification rejects it fail-closed."""
    if isinstance(value, str):
        return value
    try:
        text = value.value  # type: ignore[union-attr]
    except Exception:
        return value
    return text if isinstance(text, str) else value


def _validate_claim(
    binding: object, source_class: str, source_index: int
) -> FleetClaimRecord | FleetRecordRejection:
    texts = {}
    for name in ("claim_id", "task_id", "agent", "repository", "branch"):
        status, value = _read(binding, name)
        if status == "unreadable":
            return _unreadable(source_class, source_index)
        texts[name] = value
    head_status, head = _read(binding, "head_sha")
    if head_status == "unreadable":
        return _unreadable(source_class, source_index)
    generation_status, generation = _read(binding, "generation")
    if generation_status == "unreadable":
        return _unreadable(source_class, source_index)
    scope_status, scope = _read(binding, "scope")
    if scope_status == "unreadable":
        return _unreadable(source_class, source_index)
    if head_status == "missing":
        return _rejection(
            source_class, "RECORD_FIELD_MISSING", "head_sha", source_index
        )
    if generation_status == "missing":
        return _rejection(
            source_class, "RECORD_FIELD_MISSING", "generation", source_index
        )
    if scope_status == "missing":
        return _rejection(source_class, "RECORD_FIELD_MISSING", "scope", source_index)
    for name in ("claim_id", "task_id", "agent", "repository", "branch"):
        status, value = _read(binding, name)
        if status == "missing":
            return _rejection(source_class, "RECORD_FIELD_MISSING", name, source_index)
    for name in ("claim_id", "task_id", "agent", "repository", "branch"):
        code = _check_text(texts[name])
        if code:
            return _rejection(source_class, code, name, source_index)
    if not isinstance(head, str) or not _SHA.fullmatch(head):
        return _rejection(source_class, "HEAD_SHA_INVALID", "head_sha", source_index)
    if not isinstance(generation, int) or isinstance(generation, bool) or generation < 0:
        return _rejection(
            source_class, "GENERATION_INVALID", "generation", source_index
        )
    scope_code, scope_count = _scope_count(scope)
    if scope_code:
        return _rejection(source_class, scope_code, "scope", source_index)
    return FleetClaimRecord(
        claim_id=str(texts["claim_id"]),
        task_id=str(texts["task_id"]),
        agent=str(texts["agent"]),
        generation=generation,
        branch=str(texts["branch"]),
        head_sha=str(head),
        repository=str(texts["repository"]),
        scope_count=scope_count,
    )


def _lease_id_of(lease: FleetLeaseRecord) -> str:
    observation = lease.observation
    if observation is None:
        return ""
    status, value = _read(observation, "lease_id")
    if status == "ok" and isinstance(value, str):
        return value
    return ""


def _validate_lease(
    observation: object, source_class: str, source_index: int
) -> FleetLeaseRecord | FleetRecordRejection:
    if _reject_plain(observation):
        return _rejection(source_class, "RECORD_TYPE_UNSUPPORTED", None, source_index)
    values: dict[str, object] = {}
    for name in (
        "available",
        "provenance",
        "reason",
        "lease_id",
        "worker_id",
        "branch",
        "expected_head",
        "health",
    ):
        status, value = _read(observation, name)
        if status == "unreadable":
            return _unreadable(source_class, source_index)
        if status == "missing":
            value = False if name == "available" else None
        values[name] = value
    available = values["available"]
    if not isinstance(available, bool):
        return _rejection(
            source_class, "RECORD_TYPE_UNSUPPORTED", "available", source_index
        )
    if available:
        for name in ("lease_id", "worker_id"):
            code = _check_text(values[name])
            if code:
                return _rejection(source_class, code, name, source_index)
        if _blank_text(values["provenance"]):
            return _rejection(
                source_class, "LEASE_PROVENANCE_REQUIRED", "provenance", source_index
            )
    branch = values["branch"]
    if branch is not None:
        code = _check_text(branch)
        if code:
            return _rejection(source_class, code, "branch", source_index)
    head = values["expected_head"]
    if head is not None and (not isinstance(head, str) or not _SHA.fullmatch(head)):
        return _rejection(
            source_class, "HEAD_SHA_INVALID", "expected_head", source_index
        )
    health = values["health"]
    if health is not None:
        health_text = _enum_text(health)
        if not isinstance(health_text, str) or health_text not in _LEASE_HEALTH_STATES:
            return _rejection(
                source_class, "LEASE_HEALTH_INVALID", "health", source_index
            )
    return FleetLeaseRecord(
        available=available,
        provenance=(
            str(values["provenance"]) if isinstance(values["provenance"], str) else None
        ),
        reason=(str(values["reason"]) if isinstance(values["reason"], str) else None),
        observation=observation,  # type: ignore[arg-type]
    )


def _blank_text(value: object) -> bool:
    return not isinstance(value, str) or value.strip() == ""


def _validate_session(
    record: object,
    kind: str,
    source_class: str,
    source_index: int,
    now: datetime | None,
) -> FleetAppSessionRecord | FleetRecordRejection:
    if _reject_plain(record):
        return _rejection(source_class, "RECORD_TYPE_UNSUPPORTED", None, source_index)
    id_status, id_name, session_id = _first_attr(record, _SESSION_ID_ATTRS)
    if id_status == "unreadable":
        return _unreadable(source_class, source_index)
    if id_status == "missing":
        return _rejection(
            source_class, "RECORD_FIELD_MISSING", _SESSION_ID_ATTRS[0], source_index
        )
    code = _check_text(session_id)
    if code:
        return _rejection(source_class, code, id_name, source_index)
    label_status, label_name, label = _first_attr(record, _SESSION_LABEL_ATTRS)
    if label_status == "unreadable":
        return _unreadable(source_class, source_index)
    if label_status == "missing":
        return _rejection(
            source_class, "RECORD_FIELD_MISSING", _SESSION_LABEL_ATTRS[0], source_index
        )
    label_code = _check_text(label)
    if label_code:
        return _rejection(source_class, label_code, label_name, source_index)
    created_status, created_value = _read(record, "created_at")
    if created_status == "unreadable":
        return _unreadable(source_class, source_index)
    if created_status == "missing":
        return _rejection(
            source_class, "RECORD_FIELD_MISSING", "created_at", source_index
        )
    stamp_status, parsed = _parse_stamp(created_value)
    if stamp_status == "naive":
        return _rejection(source_class, "TIMESTAMP_NAIVE", "created_at", source_index)
    if stamp_status == "invalid":
        return _rejection(
            source_class, "TIMESTAMP_INVALID", "created_at", source_index
        )
    state = "UNKNOWN"
    if kind == "connector":
        state_status, state_value = _read(record, "state")
        if state_status == "unreadable":
            return _unreadable(source_class, source_index)
        if state_status == "ok":
            if isinstance(state_value, str) and state_value in _SESSION_STATES:
                state = state_value
            else:
                return _rejection(
                    source_class, "SESSION_STATE_INVALID", "state", source_index
                )
    # Two-faced stamp containment: a flip-flop tzinfo can pass the awareness
    # probe and then raise at the second read inside isoformat() (or at the
    # third read inside the ``now - parsed`` subtraction). Both are wrapped;
    # a raising stamp is a typed rejection, never an exception escape.
    try:
        created_at = (
            str(created_value)
            if isinstance(created_value, str)
            else parsed.isoformat()
        )
    except Exception:
        return _rejection(
            source_class, "TIMESTAMP_INVALID", "created_at", source_index
        )
    age_seconds: float | None = None
    staleness: str | None = None
    if now is not None:
        try:
            age_seconds = (now - parsed).total_seconds()
        except Exception:
            return _rejection(
                source_class, "TIMESTAMP_INVALID", "created_at", source_index
            )
        staleness = "UNKNOWN" if age_seconds < 0 else "AVAILABLE"
    return FleetAppSessionRecord(
        kind=kind,
        session_id=str(session_id),
        label=str(label),
        created_at=created_at,
        scope="app-session",
        state=state,
        age_seconds=age_seconds,
        staleness=staleness,
    )


def _validate_instance(
    record: object, source_class: str, source_index: int
) -> FleetLocalInstanceRecord | FleetRecordRejection:
    if _reject_plain(record):
        return _rejection(source_class, "RECORD_TYPE_UNSUPPORTED", None, source_index)
    name_status, name = _read(record, "name")
    if name_status == "unreadable":
        return _unreadable(source_class, source_index)
    if name_status == "missing":
        return _rejection(source_class, "RECORD_FIELD_MISSING", "name", source_index)
    code = _check_text(name)
    if code:
        return _rejection(source_class, code, "name", source_index)
    tunnel_status, tunnel_configured = _read(record, "tunnel_configured")
    if tunnel_status == "unreadable":
        return _unreadable(source_class, source_index)
    if tunnel_status == "missing":
        tunnel_configured = False
    if not isinstance(tunnel_configured, bool):
        return _rejection(
            source_class, "TUNNEL_CONFIG_INVALID", "tunnel_configured", source_index
        )
    suffix_status, tunnel_suffix = _read(record, "tunnel_suffix")
    if suffix_status == "unreadable":
        return _unreadable(source_class, source_index)
    if suffix_status == "missing":
        tunnel_suffix = ""
    if not isinstance(tunnel_suffix, str):
        return _rejection(
            source_class, "TUNNEL_SUFFIX_INVALID", "tunnel_suffix", source_index
        )
    tunnel_suffix = _probed_str(tunnel_suffix)
    if tunnel_suffix is None or len(tunnel_suffix) > 4:
        return _rejection(
            source_class, "TUNNEL_SUFFIX_INVALID", "tunnel_suffix", source_index
        )
    health_status, health = _read(record, "health")
    if health_status == "unreadable":
        return _unreadable(source_class, source_index)
    if health_status == "missing" or health is None:
        health_text = "UNKNOWN"
    else:
        health_text = _enum_text(health)
        if not isinstance(health_text, str) or health_text not in _LOCAL_HEALTH_STATES:
            return _rejection(
                source_class, "LOCAL_HEALTH_INVALID", "health", source_index
            )
    return FleetLocalInstanceRecord(
        name=str(name),
        tunnel_configured=tunnel_configured,
        tunnel_suffix=str(tunnel_suffix),
        health=str(health_text),
        staleness=_INSTANCE_STALENESS,
    )


def _dedup_and_cap(records: list, key_of, cap: int) -> tuple[tuple, int, bool]:
    survivors: list = []
    seen: dict[object, int] = {}
    duplicate_count = 0
    for record in records:
        key = key_of(record)
        if key in seen:
            duplicate_count += 1
            index = seen[key]
            survivor = survivors[index]
            survivors[index] = _dc_replace(
                survivor, duplicate_count=survivor.duplicate_count + 1
            )
            continue
        seen[key] = len(survivors)
        survivors.append(record)
    truncated = len(survivors) > cap
    return tuple(survivors[:cap]), duplicate_count, truncated


def _project_class(
    source_class: str,
    inputs: object,
    validate,
    key_of,
    provenance: str | None,
) -> FleetRecordGroup:
    if not isinstance(inputs, (list, tuple)):
        return FleetRecordGroup(
            kind=source_class,
            available=False,
            provenance=provenance,
            reason="RECORD_FRAME_INPUT_INVALID",
            records=(),
            rejections=(),
            duplicate_count=0,
            truncated=False,
        )
    records: list = []
    rejections: list[FleetRecordRejection] = []
    for index, record in enumerate(inputs):
        outcome = validate(record, source_class, index)
        if isinstance(outcome, FleetRecordRejection):
            rejections.append(outcome)
        else:
            records.append(outcome)
    deduped, duplicate_count, records_truncated = _dedup_and_cap(
        records, key_of, _FRAME_ROW_LIMIT
    )
    truncated = records_truncated or len(rejections) > _FRAME_ROW_LIMIT
    reason = "FRAME_ROW_LIMIT_EXCEEDED" if truncated else None
    return FleetRecordGroup(
        kind=source_class,
        available=True,
        provenance=provenance,
        reason=reason,
        records=deduped,
        rejections=tuple(rejections[:_FRAME_ROW_LIMIT]),
        duplicate_count=duplicate_count,
        truncated=truncated,
    )


def _join_and_reconcile(
    claims: tuple, leases: tuple
) -> FleetIdentitySummary:
    links: list[FleetIdentityLink] = []
    head_conflicts: list[FleetIdentityConflict] = []
    for claim in claims:
        for lease in leases:
            observation = lease.observation
            if observation is None:
                continue
            branch_status, lease_branch = _read(observation, "branch")
            head_status, lease_head = _read(observation, "expected_head")
            if branch_status != "ok" or head_status != "ok":
                continue
            if not isinstance(lease_branch, str) or not isinstance(lease_head, str):
                continue
            if lease_branch == claim.branch and lease_head == claim.head_sha:
                if len(links) < _FRAME_ROW_LIMIT:
                    links.append(
                        FleetIdentityLink(
                            claim_id=claim.claim_id,
                            lease_id=_lease_id_of(lease),
                            branch=claim.branch,
                            head_sha=claim.head_sha,
                        )
                    )
            elif lease_branch == claim.branch:
                if len(head_conflicts) < _FRAME_ROW_LIMIT:
                    head_conflicts.append(
                        FleetIdentityConflict(
                            divergent_fields=("head_sha",),
                            claim_ids=(claim.claim_id,),
                            lease_ids=(_lease_id_of(lease),),
                            branch=claim.branch,
                        )
                    )
    task_conflicts: list[FleetIdentityConflict] = []
    by_task: dict[str, list] = {}
    for claim in claims:
        by_task.setdefault(claim.task_id, []).append(claim)
    for task_id, group in by_task.items():
        distinct = list(dict.fromkeys(claim.claim_id for claim in group))
        if len(distinct) > 1 and len(task_conflicts) < _FRAME_ROW_LIMIT:
            task_conflicts.append(
                FleetIdentityConflict(
                    divergent_fields=("claim_id",),
                    claim_ids=tuple(distinct),
                    task_id=task_id,
                )
            )
    links_truncated = len(links) > _FRAME_ROW_LIMIT
    conflicts = head_conflicts + task_conflicts
    conflicts_truncated = len(conflicts) > _FRAME_ROW_LIMIT
    return FleetIdentitySummary(
        links=tuple(links[:_FRAME_ROW_LIMIT]),
        conflicts=tuple(conflicts[:_FRAME_ROW_LIMIT]),
        links_truncated=links_truncated,
        conflicts_truncated=conflicts_truncated,
    )


def project_fleet_view(
    *,
    claim_bindings=(),
    lease_observations=(),
    worker_sessions=(),
    connector_sessions=(),
    local_instances=(),
    now=None,
) -> FleetView:
    """Compose the fleet/work identity read DTO from injected records.

    ``now`` must be a timezone-aware :class:`datetime` when provided; a naive
    value is a caller-contract violation and raises ``ValueError``. Injected
    records are untrusted data: every attribute read is wrapped, every
    malformed record becomes a typed per-record rejection whose neighbors
    survive, and the result is a pure value carrying no mutation, claim, or
    completion authority.
    """
    if now is not None and (not isinstance(now, datetime) or not _tz_aware(now)):
        raise ValueError("FLEET_NOW_MUST_BE_TZ_AWARE")
    claims = _project_class(
        "claims",
        claim_bindings,
        _validate_claim,
        lambda record: record.claim_id,
        _CLAIM_PROVENANCE,
    )
    leases = _project_class(
        "leases",
        lease_observations,
        _validate_lease,
        lambda record: _lease_id_of(record),
        _LEASE_GROUP_PROVENANCE,
    )
    worker_group = _project_class(
        "worker_sessions",
        worker_sessions,
        lambda record, source_class, index: _validate_session(
            record, "worker", source_class, index, now
        ),
        lambda record: record.session_id,
        _SESSION_GROUP_PROVENANCE,
    )
    connector_group = _project_class(
        "connector_sessions",
        connector_sessions,
        lambda record, source_class, index: _validate_session(
            record, "connector", source_class, index, now
        ),
        lambda record: record.session_id,
        _SESSION_GROUP_PROVENANCE,
    )
    instance_group = _project_class(
        "local_instances",
        local_instances,
        _validate_instance,
        lambda record: record.name,
        _INSTANCE_GROUP_PROVENANCE,
    )
    remote_group = FleetRecordGroup(
        kind="remote_devices",
        available=False,
        provenance=_REMOTE_GROUP_PROVENANCE,
        reason=_REMOTE_UNAVAILABLE_REASON,
        records=(FleetRemoteDeviceRecord(),),
        rejections=(),
        duplicate_count=0,
        truncated=False,
    )
    identity = _join_and_reconcile(claims.records, leases.records)
    return FleetView(
        claims=claims,
        leases=leases,
        worker_sessions=worker_group,
        connector_sessions=connector_group,
        local_instances=instance_group,
        remote_devices=remote_group,
        identity=identity,
    )
