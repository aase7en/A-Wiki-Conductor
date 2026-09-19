"""Pure projection of one authoritative ControlEvent into a Hook Contract v1 OBSERVE envelope."""

from __future__ import annotations

import re
from dataclasses import dataclass, fields
from datetime import datetime
from typing import NoReturn, Sequence

from .control_events import ControlEvent

__all__ = [
    "ControlHookContext",
    "ControlHookNormalizationError",
    "normalize_control_event",
]

HOOK_SCHEMA_VERSION = "1.0.0"

_EVENT_INVALID = "CONTROL_HOOK_EVENT_INVALID"
_CONTEXT_INVALID = "CONTROL_HOOK_CONTEXT_INVALID"
_EVENT_ID_MALFORMED = "CONTROL_HOOK_EVENT_ID_MALFORMED"
_EVENT_TYPE_UNSUPPORTED = "CONTROL_HOOK_EVENT_TYPE_UNSUPPORTED"
_CONTEXT_REQUIRED = "CONTROL_HOOK_CONTEXT_REQUIRED"
_OCCURRED_AT_INVALID = "CONTROL_HOOK_OCCURRED_AT_INVALID"
_SOURCE_VERSION_INVALID = "CONTROL_HOOK_SOURCE_VERSION_INVALID"
_DEVICE_ID_INVALID = "CONTROL_HOOK_DEVICE_ID_INVALID"
_HOST_OS_INVALID = "CONTROL_HOOK_HOST_OS_INVALID"
_CONTEXT_FIELD_INVALID = "CONTROL_HOOK_CONTEXT_FIELD_INVALID"

_SOURCE_EVENT_ID = re.compile(r"event-[0-9a-f]{32}")
_OCCURRED_AT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,9})?Z")
_SOURCE_VERSION = re.compile(r"\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?")
_DEVICE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_LANE_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}")
_HOOK_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_HOOK_PATH_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}")
_HEAD_SHA = re.compile(r"[0-9a-f]{7,64}")
_CAUSATION_ID = re.compile(r"hk-[0-9a-f]{32}")
_EFFORT = re.compile(r"[a-z0-9][a-z0-9._-]{0,31}")
_STATE = re.compile(r"[A-Z][A-Z0-9_]{1,31}")
_BLOCKER_CODE = re.compile(r"[A-Z][A-Z0-9_]{1,63}")
_EVIDENCE_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
_EVIDENCE_DIGEST = re.compile(r"[0-9a-f]{16,128}")
_BRANCH = re.compile(r"\S{1,256}")

_HOST_OS_VALUES = frozenset({"windows", "macos", "linux"})
_TASK_TOPOLOGY_VALUES = frozenset(
    {"CONTROL_PLANE_ONLY", "EXECUTION_SUBSTRATE_ONLY", "CROSS_REPO", "UNBOUND"}
)

_EVENT_TYPE_MAP = {
    "START": ("control.start.after", "start"),
    "STOP": ("control.stop.after", "stop"),
    "RESTART": ("control.restart.after", "restart"),
    "RELEASE": ("control.release.after", "release"),
}

_PATTERN_FIELDS = {
    "lane_id": _LANE_REF,
    "task_id": _LANE_REF,
    "work_order": _LANE_REF,
    "claim_ref": _HOOK_PATH_REF,
    "execution_id": _HOOK_PATH_REF,
    "harness_id": _HOOK_PATH_REF,
    "model_id": _HOOK_PATH_REF,
    "correlation_id": _HOOK_REF,
    "causation_id": _CAUSATION_ID,
    "head_sha": _HEAD_SHA,
    "effort": _EFFORT,
    "state": _STATE,
    "blocker_code": _BLOCKER_CODE,
    "evidence_digest": _EVIDENCE_DIGEST,
}

_MAX_FREE_TEXT = 256
_MAX_SUMMARY = 512
_MAX_EVIDENCE_REFS = 16
_MAX_SOURCE_VERSION = 64

_REQUIRED_CONTEXT_FIELDS = frozenset(
    {"occurred_at", "source_version", "device_id", "host_os"}
)

_SECRET_MARKERS = (
    "sk-FAKE0000000000000000000000000000000000",
    "ghp_FAKE0000000000000000000000000000000",
    "xoxb-FAKE-000000000000000000000000",
    "AKIAFAKE0000000000",
    "FAKESESSIONCOOKIE=0000000000000000",
    "-----BEGIN FAKE PRIVATE KEY-----",
    "https://chat.example/FAKE/share/0000",
    "Bearer FAKE000000000000000000000000000",
)


class ControlHookNormalizationError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class ControlHookContext:
    occurred_at: str
    source_version: str
    device_id: str
    host_os: str
    lane_id: str | None = None
    task_id: str | None = None
    work_order: str | None = None
    task_topology: str | None = None
    authority_repo: str | None = None
    execution_repo: str | None = None
    repo: str | None = None
    worktree: str | None = None
    branch: str | None = None
    head_sha: str | None = None
    claim_ref: str | None = None
    execution_id: str | None = None
    harness_id: str | None = None
    model_id: str | None = None
    effort: str | None = None
    state: str | None = None
    blocker_code: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    evidence_refs: Sequence[str] | None = None
    evidence_digest: str | None = None
    summary: str | None = None


def _fail(code: str) -> NoReturn:
    raise ControlHookNormalizationError(code)


def _has_control_characters(value: str) -> bool:
    return any(ord(character) < 0x20 or ord(character) == 0x7F for character in value)


def _reject_secret_markers(envelope: dict[str, object]) -> None:
    values: list[object] = list(envelope.values())
    while values:
        value = values.pop()
        if isinstance(value, str):
            if any(marker in value for marker in _SECRET_MARKERS):
                _fail(_CONTEXT_FIELD_INVALID)
        elif isinstance(value, (list, tuple)):
            values.extend(value)


def _required_text(
    value: object, pattern: re.Pattern[str], code: str
) -> str:
    if value is None:
        _fail(_CONTEXT_REQUIRED)
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        _fail(code)
    return value


def _required_enum(
    value: object, allowed: frozenset[str], code: str
) -> str:
    if value is None:
        _fail(_CONTEXT_REQUIRED)
    if not isinstance(value, str) or value not in allowed:
        _fail(code)
    return value


def _required_occurred_at(value: object) -> str:
    text = _required_text(value, _OCCURRED_AT, _OCCURRED_AT_INVALID)
    try:
        datetime(int(text[0:4]), int(text[5:7]), int(text[8:10]))
    except ValueError:
        _fail(_OCCURRED_AT_INVALID)
    if int(text[11:13]) > 23 or int(text[14:16]) > 59 or int(text[17:19]) > 60:
        _fail(_OCCURRED_AT_INVALID)
    return text


def _required_source_version(value: object) -> str:
    if value is None:
        _fail(_CONTEXT_REQUIRED)
    if (
        not isinstance(value, str)
        or len(value) > _MAX_SOURCE_VERSION
        or _SOURCE_VERSION.fullmatch(value) is None
    ):
        _fail(_SOURCE_VERSION_INVALID)
    return value


def _optional_text(value: object) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= _MAX_FREE_TEXT
        or _has_control_characters(value)
    ):
        _fail(_CONTEXT_FIELD_INVALID)
    return value


def _optional_evidence_refs(value: object) -> list[str]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        _fail(_CONTEXT_FIELD_INVALID)
    refs = list(value)
    if len(refs) > _MAX_EVIDENCE_REFS or len(set(refs)) != len(refs):
        _fail(_CONTEXT_FIELD_INVALID)
    for ref in refs:
        if (
            not isinstance(ref, str)
            or _EVIDENCE_REF.fullmatch(ref) is None
            or _has_control_characters(ref)
        ):
            _fail(_CONTEXT_FIELD_INVALID)
    return refs


def _optional_summary(value: object) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= _MAX_SUMMARY
        or _has_control_characters(value)
    ):
        _fail(_CONTEXT_FIELD_INVALID)
    return value


def _validated_optional(name: str, value: object) -> object:
    pattern = _PATTERN_FIELDS.get(name)
    if pattern is not None:
        if not isinstance(value, str) or pattern.fullmatch(value) is None:
            _fail(_CONTEXT_FIELD_INVALID)
        return value
    if name == "task_topology":
        if not isinstance(value, str) or value not in _TASK_TOPOLOGY_VALUES:
            _fail(_CONTEXT_FIELD_INVALID)
        return value
    if name == "branch":
        if (
            not isinstance(value, str)
            or _BRANCH.fullmatch(value) is None
            or _has_control_characters(value)
        ):
            _fail(_CONTEXT_FIELD_INVALID)
        return value
    if name == "evidence_refs":
        return _optional_evidence_refs(value)
    if name == "summary":
        return _optional_summary(value)
    return _optional_text(value)


def normalize_control_event(
    event: ControlEvent, context: ControlHookContext
) -> dict[str, object]:
    if not isinstance(event, ControlEvent):
        _fail(_EVENT_INVALID)
    if not isinstance(context, ControlHookContext):
        _fail(_CONTEXT_INVALID)
    source_event_id = event.event_id
    if (
        not isinstance(source_event_id, str)
        or _SOURCE_EVENT_ID.fullmatch(source_event_id) is None
    ):
        _fail(_EVENT_ID_MALFORMED)
    if not isinstance(event.event_type, str):
        _fail(_EVENT_TYPE_UNSUPPORTED)
    mapping = _EVENT_TYPE_MAP.get(event.event_type)
    if mapping is None:
        _fail(_EVENT_TYPE_UNSUPPORTED)
    hook_event_type, action = mapping
    occurred_at = _required_occurred_at(context.occurred_at)
    source_version = _required_source_version(context.source_version)
    device_id = _required_text(context.device_id, _DEVICE_ID, _DEVICE_ID_INVALID)
    host_os = _required_enum(context.host_os, _HOST_OS_VALUES, _HOST_OS_INVALID)
    envelope: dict[str, object] = {
        "schema_version": HOOK_SCHEMA_VERSION,
        "event_id": f"hk-{source_event_id[len('event-') :]}",
        "event_type": hook_event_type,
        "hook_class": "OBSERVE",
        "phase": "after",
        "domain": "control",
        "action": action,
        "occurred_at": occurred_at,
        "source": "a-conductor",
        "source_version": source_version,
        "device_id": device_id,
        "host_os": host_os,
        "privacy_class": "INTERNAL",
    }
    for field in fields(context):
        if field.name in _REQUIRED_CONTEXT_FIELDS:
            continue
        value = getattr(context, field.name)
        if value is None:
            continue
        envelope[field.name] = _validated_optional(field.name, value)
    _reject_secret_markers(envelope)
    return envelope
