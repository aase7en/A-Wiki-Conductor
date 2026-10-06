"""WO-P1-596: pure read-only monitor view projection (no transport, no I/O).

Derives sanitized, bounded view models from caller-supplied read results
(HookBus health/records, HookStm reads, optional correlation data). Truthful
by construction: STALE stays STALE, UNKNOWN stays UNKNOWN, absent correlation
is an explicit UNKNOWN marker — never fabricated health. No secrets, raw
prompts, or private payloads cross this seam; only whitelisted bounded fields.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Mapping, Sequence

__all__ = ["MonitorProjectionError", "build_monitor_views"]

_TIMELINE_LIMIT = 64
_NOTE_LIMIT = 256
_TIMELINE_FIELDS = ("event_id", "event_type", "hook_class", "occurred_at", "note")


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
    bounded_counters = {
        _plain_str(key, 64): value
        for key, value in list(counters.items())[:32]
        if isinstance(value, int)
    }
    bounded_conditions = [
        _plain_str(condition, 128)
        for condition in (conditions if isinstance(conditions, (list, tuple)) else [])[:16]
    ]
    return {
        "degraded": degraded,
        "counters": bounded_counters,
        "conditions": bounded_conditions,
    }


def _timeline_view(records: object) -> list[dict[str, Any]]:
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        raise MonitorProjectionError("MONITOR_PROJECTION_INVALID_INPUT")
    view: list[dict[str, Any]] = []
    for item in list(records)[-_TIMELINE_LIMIT:]:
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
    for state in list(states)[:64]:
        if not isinstance(state, Mapping):
            raise MonitorProjectionError("MONITOR_PROJECTION_INVALID_INPUT")
        view.append({
            "partition": _plain_str(state.get("partition", ""), 128),
            "state": _plain_str(state.get("state", "UNKNOWN"), 32),
            "rebuild_required": bool(state.get("rebuild_required", False)),
            "record_count": state.get("record_count", 0)
            if isinstance(state.get("record_count", 0), int) else 0,
        })
    return view


def _correlation_view(correlation: object) -> dict[str, Any]:
    if correlation is None:
        # Absent evidence is explicit UNKNOWN — never fabricated lanes/runs.
        return {"state": "UNKNOWN"}
    if not isinstance(correlation, Mapping):
        raise MonitorProjectionError("MONITOR_PROJECTION_INVALID_INPUT")
    return {
        "state": _plain_str(correlation.get("state", "UNKNOWN"), 32),
        "entries": [
            {key: _plain_str(value, _NOTE_LIMIT) for key, value in
             list(entry.items())[:8]}
            for entry in (correlation.get("entries") or [])[:16]
            if isinstance(entry, Mapping)
        ],
    }


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
