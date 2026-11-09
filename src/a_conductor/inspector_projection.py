"""Pure, secret-free inspector presentation contract for WO-P1-739.

No I/O dependencies or runtime authority. AVAILABLE is a skill-only static
availability label, not InspectorState.READY or evidence of runtime liveness.
Build behavior is intentionally unimplemented for the RED checkpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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


def build_inspector_views(
    *,
    tools: Sequence[ToolInspectorRow],
    hooks: Sequence[HookInspectorRow],
    skills: Sequence[SkillInspectorRow],
    now: datetime | None = None,
) -> dict:
    """Project validated rows; retain the newest 128 per input-order section."""
    raise NotImplementedError("INSPECTOR_SLICE_1_RED")
