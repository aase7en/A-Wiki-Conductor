"""Pure, secret-free inspector presentation contract for WO-P1-739.

No I/O dependencies or runtime authority. AVAILABLE is a skill-only static
availability label, not InspectorState.READY or evidence of runtime liveness.
Inputs are injected frozen rows; this module never discovers or probes sources.
Integer last_verified values must be within -2**53 .. 2**53, inclusive,
the inspector's finite JavaScript-safe interchange range (bool is not an int).
Raw free-text fields longer than 4096 characters are invalid, checked before
stripping, normalization, or secret scanning. Accepted text is scanned before
the 200-character display truncation using linear token analysis, never regex.
"""

from __future__ import annotations

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


_RAW_FIELD_LIMIT = 4096
_SECRET_MARKERS = (
    "authorization", "token", "secret", "password", "apikey", "accesskey",
    "credential", "cookie", "bearer",
)
_LABEL_PUNCTUATION = str.maketrans("", "", "_-\"'")
_TOKEN_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789_"
_PREFIX_RULES = (
    ("sk-", 8, _TOKEN_ALPHABET + "-"),
    *((prefix, 8, _TOKEN_ALPHABET) for prefix in ("ghp_", "gho_", "ghu_", "ghs_", "ghr_")),
    ("github_pat_", 1, _TOKEN_ALPHABET),
    *((prefix, 1, _TOKEN_ALPHABET.replace("_", "-"))
      for prefix in ("xoxb-", "xoxa-", "xoxp-", "xoxr-", "xoxs-")),
    ("akia", 12, _TOKEN_ALPHABET.replace("_", "")),
    ("tunnel_", 32, "0123456789abcdef"),
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


def _secret_tokens(tokens: list[str]) -> bool:
    """Fixed work per character: disjoint splits and constant-size checks."""
    previous_label = ""
    private_header = private_word = False
    for index, token in enumerate(tokens):
        if token.startswith("authorization:") or (token == "bearer" and index + 1 < len(tokens)):
            return True
        scheme_end = token.find("://")
        if scheme_end >= 0:
            authority_start = scheme_end + 3
            authority_end = token.find("/", authority_start)
            if authority_end < 0:
                authority_end = len(token)
            if token.find("@", authority_start, authority_end) >= 0:
                return True
        if token.startswith(("http://", "https://")):
            if token.partition("/share/")[2] or token.partition("/s/")[2]:
                return True
        if "-----begin" in token:
            private_header, private_word = True, False
        elif private_header and token == "private":
            private_word = True
        elif private_word and token.startswith("key-----"):
            return True
        for prefix, minimum, alphabet in _PREFIX_RULES:
            # Searches advance monotonically; inspect only a fixed <=32-char
            # window, even when credential content contains another prefix.
            start = token.find(prefix)
            while start >= 0:
                payload_start = start + len(prefix)
                if len(token) - payload_start >= minimum and all(
                    char in alphabet for char in token[payload_start:payload_start + minimum]
                ):
                    return True
                start = token.find(prefix, start + 1)
        parts = token.replace(":", "=").split("=")
        first = parts[0].translate(_LABEL_PUNCTUATION)
        if not first:
            first = previous_label
        elif previous_label in ("api", "access") and first == "key":
            first = previous_label + first
        for part_index, part in enumerate(parts[:-1]):
            label = first if part_index == 0 else part.translate(_LABEL_PUNCTUATION)
            if label.endswith(_SECRET_MARKERS) or any(ord(char) > 127 for char in label):
                return True
        previous_label = (first if len(parts) == 1 else
                          parts[-1].translate(_LABEL_PUNCTUATION))[-32:]
    return False


def _text(value: object, *, required: bool = False) -> str:
    if type(value) is not str or len(value) > _RAW_FIELD_LIMIT:
        raise InspectorProjectionError()
    if required and not value.strip():
        raise InspectorProjectionError()
    normalized = "".join(char for char in unicodedata.normalize("NFKD", value).casefold()
                         if not unicodedata.combining(char)).translate(_MARKER_CONFUSABLES)
    if _secret_tokens(normalized.split()):
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
