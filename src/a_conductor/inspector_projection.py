"""Pure, secret-free inspector presentation contract for WO-P1-739.

No I/O dependencies or runtime authority. AVAILABLE is a skill-only static
availability label, not InspectorState.READY or evidence of runtime liveness.
Inputs are injected frozen rows; this module never discovers or probes sources.
Integer last_verified values must be within -2**53 .. 2**53, inclusive,
the inspector's finite JavaScript-safe interchange range (bool is not an int).
"""

from __future__ import annotations

import re
import unicodedata
from collections import deque
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from enum import Enum
from typing import Sequence


class InspectorState(str, Enum):
    READY = "READY"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"
    DISCONNECTED = "DISCONNECTED"
    DEGRADED = "DEGRADED"


class ToolPhase(str, Enum):
    REGISTERED = "REGISTERED"
    STARTED = "STARTED"
    CONNECTED = "CONNECTED"
    INJECTED = "INJECTED"
    UNKNOWN = "UNKNOWN"


class InspectorProjectionError(RuntimeError):
    """Invalid untrusted projection input; never carries raw input text."""

    code = "INSPECTOR_PROJECTION_INVALID_INPUT"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class ToolInspectorRow:
    name: str
    device: str
    category: str
    source: str
    phase: ToolPhase | str
    state: InspectorState | str
    registration_evidence: str
    last_verified: str | int | None
    last_error: str
    next_safe_action: str
    provenance: str


@dataclass(frozen=True, slots=True)
class HookInspectorRow:
    name: str
    hook_class: str
    authority_source: str
    enabled: bool
    fail_mode: str
    state: InspectorState | str
    last_event: str
    last_error: str
    provenance: str


@dataclass(frozen=True, slots=True)
class SkillInspectorRow:
    name: str
    state: InspectorState | str
    registry_source: str
    routing_hint: str
    harness: str
    deprecated: bool
    duplicate: bool
    provenance: str


_SECRET = re.compile(
    r"sk-[A-Za-z0-9_-]{8,}|gh[pousr]_[A-Za-z0-9_]{8,}|"
    r"github_pat_[A-Za-z0-9_]+|xox[baprs]-[A-Za-z0-9-]+|AKIA[A-Z0-9]{12,}|"
    r"\bauthorization\s*:|\bBearer\s+\S+|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"[a-z][a-z0-9+.-]*://[^\s/?#@]+@[^\s/?#]+|"
    r"(?:api[_ -]?key|access[_ -]?key|token|credential|password|secret|cookie)"
    r"\s*[\"']?\s*[:=]\s*\S+|tunnel_[0-9a-f]{32}|"
    r"https?://[^\s]+/(?:share|s)/[^\s]+|"
    r"[^\s:=]*[^\x00-\x7f][^\s:=]*\s*[:=]\s*\S+",
    re.IGNORECASE,
)

# NFKD does not fold cross-script lookalikes. Fold marker confusables as well;
# remaining non-ASCII assignment labels are conservatively treated as secrets.
_MARKER_CONFUSABLES = str.maketrans({
    "\u0430": "a", "\u0432": "b", "\u0441": "c", "\u0501": "d",
    "\u0435": "e", "\u04bb": "h", "\u0456": "i", "\u0458": "j",
    "\u043a": "k", "\u04cf": "l", "\u043c": "m", "\u043d": "h",
    "\u043e": "o", "\u0440": "p", "\u051b": "q", "\u0455": "s",
    "\u0442": "t", "\u0443": "y", "\u0445": "x", "\u051d": "w",
    "\u03b1": "a", "\u03b5": "e", "\u03b9": "i", "\u03ba": "k",
    "\u03bf": "o", "\u03c1": "p", "\u03c4": "t", "\u03c5": "u",
})


def _text(value: object, *, required: bool = False) -> str:
    if type(value) is not str or (required and not value.strip()):
        raise InspectorProjectionError()
    normalized = "".join(char for char in unicodedata.normalize("NFKD", value).casefold()
                         if not unicodedata.combining(char)).translate(_MARKER_CONFUSABLES)
    if _SECRET.search(value) or _SECRET.search(normalized):
        return "[REDACTED]"
    if any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise InspectorProjectionError()
    return value[:200]


def _enum(value: object, allowed: tuple[str, ...]) -> str:
    if isinstance(value, (InspectorState, ToolPhase)):
        value = value.value
    return value if type(value) is str and value in allowed else "UNKNOWN"


def _row_view(row: object, row_type: type) -> dict:
    if type(row) is not row_type:
        raise InspectorProjectionError()
    result = {}
    for field in fields(row_type):
        value = getattr(row, field.name)
        if field.name == "state":
            allowed = tuple(state.value for state in InspectorState)
            if row_type is SkillInspectorRow:
                allowed += ("AVAILABLE",)
            result[field.name] = _enum(value, allowed)
        elif field.name == "phase":
            result[field.name] = _enum(value, tuple(phase.value for phase in ToolPhase))
        elif field.name == "hook_class":
            result[field.name] = _enum(value, ("OBSERVE", "ADVISORY", "GUARD", "COMMAND"))
        elif field.name == "fail_mode":
            result[field.name] = _enum(value, ("FAIL_CLOSED", "FAIL_OPEN", "UNKNOWN"))
        elif field.name in {"enabled", "deprecated", "duplicate"}:
            if type(value) is not bool:
                raise InspectorProjectionError()
            result[field.name] = value
        elif field.name == "last_verified":
            if value is None or type(value) is int:
                if type(value) is int and not -(1 << 53) <= value <= (1 << 53):
                    raise InspectorProjectionError()
                result[field.name] = value
            else:
                result[field.name] = _text(value)
        else:
            result[field.name] = _text(value, required=field.name == "name")
    return result


def build_inspector_views(
    *,
    tools: Sequence[ToolInspectorRow],
    hooks: Sequence[HookInspectorRow],
    skills: Sequence[SkillInspectorRow],
    now: datetime | None = None,
) -> dict:
    """Project validated rows; retain the newest 128 per input-order section."""
    try:
        current = datetime.now(timezone.utc) if now is None else now
        if not isinstance(current, datetime) or current.tzinfo is None or current.utcoffset() is None:
            raise InspectorProjectionError()
        summary = {"generated_at": current.astimezone(timezone.utc).isoformat()}
        result = {"summary": summary}
        for section, inputs, row_type in (
            ("tools", tools, ToolInspectorRow),
            ("hooks", hooks, HookInspectorRow),
            ("skills", skills, SkillInspectorRow),
        ):
            retained: deque = deque(maxlen=128)
            total = 0
            for row in inputs:
                retained.append(_row_view(row, row_type))
                total += 1
            counts: dict[str, int] = {}
            for row in retained:
                counts[row["state"]] = counts.get(row["state"], 0) + 1
            result[section] = list(retained)
            summary[section] = {
                "counts": counts, "truncated": total > 128,
                "dropped": max(0, total - 128),
            }
        return result
    except Exception:
        raise InspectorProjectionError() from None
