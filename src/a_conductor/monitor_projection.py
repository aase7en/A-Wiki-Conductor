"""WO-P1-596: pure read-only monitor view projection (no transport, no I/O).

Derives sanitized, bounded view models from caller-supplied read results
(HookBus health/records, HookStm reads, optional correlation data). Truthful
by construction: STALE stays STALE with its rebuild semantics, UNKNOWN stays
UNKNOWN, absent correlation is an explicit UNKNOWN marker — never fabricated
health. Only whitelisted public fields cross this seam (correlation entries
carry an explicit field allowlist); private-shaped keys are omitted. Bounds
are applied before materialization and malformed input is typed-rejected.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Mapping, Sequence

__all__ = ["MonitorProjectionError", "build_monitor_views"]

_TIMELINE_LIMIT = 64
_STM_LIMIT = 64
_CORRELATION_ENTRY_LIMIT = 16
_NOTE_LIMIT = 256
_KEY_LIMIT = 64
_TIMELINE_FIELDS = ("event_id", "event_type", "hook_class", "occurred_at", "note")
# MSP-3 public correlation vocabulary; anything else (secret-shaped or raw
# private payload keys) is omitted, never passed through.
_CORRELATION_FIELDS = (
    "origin_surface", "chat_session_ref", "claim_ref", "lane_ref",
    "task_id", "work_order", "run_id", "execution_id", "command_id",
    "correlation_id", "state",
)
_STM_STATES = ("FRESH", "STALE", "UNKNOWN")


class MonitorProjectionError(ValueError):
    """Typed rejection of malformed projection input; never fabricated views."""


def _plain_str(value: object, limit: int) -> str:
    if not isinstance(value, str):
        raise MonitorProjectionError("MONITOR_PROJECTION_INVALID_INPUT")
    return value[:limit]


def _health_view(bus_health: object) -> dict[str, Any]:
    if not isinstance(bus_health, Mapping):
        raise MonitorProjectionError("MONITOR_PROJECTION_INVALID_INPUT")
    degraded = bus_health.get("degraded")
    counters = bus_health.get("counters")
    conditions = bus_health.get("conditions")
    if not isinstance(degraded, bool) or not isinstance(counters, Mapping):
        raise MonitorProjectionError("MONITOR_PROJECTION_INVALID_INPUT")
    bounded_counters: dict[str, int] = {}
    for index, (key, value) in enumerate(counters.items()):
        if index >= 32:
            break  # bound iteration before materialization
        if not isinstance(key, str) or not isinstance(value, int):
            raise MonitorProjectionError("MONITOR_PROJECTION_INVALID_INPUT")
        bounded_counters[key[:_KEY_LIMIT]] = value
    bounded_conditions: list[str] = []
    if conditions is None:
        pass
    elif isinstance(conditions, (list, tuple)):
        for index, condition in enumerate(conditions):
            if index >= 16:
                break
            bounded_conditions.append(_plain_str(condition, 128))
    else:
        raise MonitorProjectionError("MONITOR_PROJECTION_INVALID_INPUT")
    return {
        "degraded": degraded,
        "counters": bounded_counters,
        "conditions": bounded_conditions,
    }


def _timeline_view(records: object) -> list[dict[str, Any]]:
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        raise MonitorProjectionError("MONITOR_PROJECTION_INVALID_INPUT")
    view: list[dict[str, Any]] = []
    # Slice the tail before iterating; no whole-collection copy.
    for item in records[-_TIMELINE_LIMIT:]:
        if isinstance(item, tuple) and len(item) == 2:
            envelope, markers = item
        else:
            envelope, markers = item, ()
        if not isinstance(envelope, Mapping) or not isinstance(markers, (tuple, list)):
            raise MonitorProjectionError("MONITOR_PROJECTION_INVALID_INPUT")
        entry: dict[str, Any] = {}
        for field in _TIMELINE_FIELDS:
            if field in envelope:
                entry[field] = _plain_str(envelope[field], _NOTE_LIMIT)
        view.append(entry)
    return view


def _stm_view(states: object) -> list[dict[str, Any]]:
    if not isinstance(states, Sequence) or isinstance(states, (str, bytes)):
        raise MonitorProjectionError("MONITOR_PROJECTION_INVALID_INPUT")
    view = []
    for state in states[-_STM_LIMIT:]:
        if not isinstance(state, Mapping):
            raise MonitorProjectionError("MONITOR_PROJECTION_INVALID_INPUT")
        # Strict, fail-closed: never fabricate rebuild/count values for a
        # state whose recovery semantics depend on them (Sol round-1 P2).
        partition = state.get("partition")
        stm_state = state.get("state")
        rebuild_required = state.get("rebuild_required")
        record_count = state.get("record_count")
        if (
            not isinstance(partition, str) or not 1 <= len(partition) <= 128
            or stm_state not in _STM_STATES
            or type(rebuild_required) is not bool
            or type(record_count) is not int or record_count < 0
        ):
            raise MonitorProjectionError("MONITOR_PROJECTION_INVALID_INPUT")
        view.append({
            "partition": partition,
            "state": stm_state,
            "rebuild_required": rebuild_required,
            "record_count": record_count,
        })
    return view


def _correlation_view(correlation: object) -> dict[str, Any]:
    if correlation is None:
        # Absent evidence is explicit UNKNOWN — never fabricated lanes/runs.
        return {"state": "UNKNOWN"}
    if not isinstance(correlation, Mapping):
        raise MonitorProjectionError("MONITOR_PROJECTION_INVALID_INPUT")
    state = correlation.get("state", "UNKNOWN")
    if not isinstance(state, str):
        raise MonitorProjectionError("MONITOR_PROJECTION_INVALID_INPUT")
    entries = correlation.get("entries")
    if entries is None:
        entries = ()
    elif not isinstance(entries, (list, tuple)):
        raise MonitorProjectionError("MONITOR_PROJECTION_INVALID_INPUT")
    view_entries = []
    for index, entry in enumerate(entries):
        if index >= _CORRELATION_ENTRY_LIMIT:
            break  # bound iteration before materialization
        if not isinstance(entry, Mapping):
            raise MonitorProjectionError("MONITOR_PROJECTION_INVALID_INPUT")
        projected: dict[str, str] = {}
        for key, value in entry.items():
            # Explicit allowlist: private-shaped keys are silently omitted;
            # malformed keys/values are typed-rejected (Sol round-1 P1/P2).
            if key not in _CORRELATION_FIELDS:
                continue
            projected[key] = _plain_str(value, _NOTE_LIMIT)
        view_entries.append(projected)
    return {"state": state[:32], "entries": view_entries}


def build_monitor_views(
    *,
    bus_health: object,
    timeline_records: object,
    stm_states: object,
    correlation: object,
) -> dict[str, Any]:
    """Build one sanitized snapshot view from injected read results."""
    return {
        "health": _health_view(bus_health),
        "timeline": _timeline_view(timeline_records),
        "stm": _stm_view(stm_states),
        "correlation": _correlation_view(correlation),
    }


def bounded_stream_queue(limit: int) -> deque:
    """Bounded drop-oldest queue used by the monitor stream."""
    return deque(maxlen=max(1, min(limit, 256)))
