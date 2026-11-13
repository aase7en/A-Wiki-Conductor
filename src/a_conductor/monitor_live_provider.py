"""WO-P1-750: bounded live monitor view producer for the web read port.

Pure synchronous composition over the WO-P1-739 collectors and the
WO-P1-596 monitor projection: no network, no subprocess, no threads, no
scheduling. The factory itself performs no I/O at all; every collection
happens inside the returned zero-arg closure, which the web feed invokes
exactly once per poller tick (one shared producer — never in the HTTP
request path). Section row data is re-projected through the existing
redaction/bounds seam, so secrets entering via collector rows are
redacted end-to-end.

Env knobs follow the agent_change_packets / awiki_environment_resolver
precedent (injectable mapping, default os.environ):
- ``A_CONDUCTOR_AWIKI_ROOT``: skills registry root override; UNSET keeps
  the collector default verbatim (Windows behavior unchanged).
- ``A_CONDUCTOR_MONITOR_PROJECTION``: value ``off`` (case/space
  tolerant) is the kill-switch; the producer then returns the exact
  pre-change placeholder, restoring the rollback default.

The closure also carries ``initial_child`` — the child a consumer should
serve before any collection completed (the kill-switch placeholder when
off, a typed ``MONITOR_NOT_COLLECTED`` marker when live). Result modes
are distinct: ``off`` (kill-switch placeholder), ``live`` (sanitized
views), ``error`` (typed failure naming the failing section, without raw
exception text or paths).
"""
from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .inspector_sources import (
    collect_local_hook_rows,
    collect_local_skill_rows,
    collect_local_tool_rows,
)
from .monitor_projection import build_monitor_views
from .inspector_projection import (
    HookInspectorRow, SkillInspectorRow, ToolInspectorRow,
)

__all__ = [
    "MONITOR_NOT_COLLECTED", "MONITOR_PLACEHOLDER", "build_live_monitor_provider",
]

MONITOR_PLACEHOLDER: dict = {
    "error": "MONITOR_PROJECTION_UNAVAILABLE",
    "gate": "OPTIONAL_READ_PORT_UNAVAILABLE",
}
MONITOR_NOT_COLLECTED: dict = {
    "error": "MONITOR_NOT_COLLECTED",
    "gate": "OPTIONAL_READ_PORT_UNAVAILABLE",
}
MONITOR_LIVE_PROJECTION_FAILED = "MONITOR_LIVE_PROJECTION_FAILED"
_INSPECTOR_ROWS_LIMIT = 128
_ROW_TYPES = {"tools": ToolInspectorRow, "hooks": HookInspectorRow,
              "skills": SkillInspectorRow}


def _error_child(gate: str) -> dict:
    return {"error": MONITOR_LIVE_PROJECTION_FAILED, "gate": gate}


def _section_summary(rows: list) -> dict:
    counts: dict[str, int] = {}
    for row in rows:
        key = getattr(row, "state", "UNKNOWN")
        if isinstance(key, str):
            counts[key] = counts.get(key, 0) + 1
    dropped = max(0, len(rows) - _INSPECTOR_ROWS_LIMIT)
    return {"counts": counts, "truncated": dropped > 0, "dropped": dropped}


def build_live_monitor_provider(
    env=None,
    *,
    repo_root=None,
    tool_collector: Callable[..., tuple] = collect_local_tool_rows,
    hook_collector: Callable[..., tuple] = collect_local_hook_rows,
    skill_collector: Callable[..., tuple] = collect_local_skill_rows,
):
    """Return a zero-arg producer closure; no I/O happens until it is called."""
    mapping = os.environ if env is None else env
    projection_value = mapping.get("A_CONDUCTOR_MONITOR_PROJECTION")
    off = (isinstance(projection_value, str)
           and projection_value.strip().casefold() == "off")
    awiki_root = mapping.get("A_CONDUCTOR_AWIKI_ROOT")
    if not isinstance(awiki_root, str) or not awiki_root.strip():
        awiki_root = None  # UNSET keeps the collector default verbatim
    # hook contracts are repo-relative; default to this checkout's root
    hook_root = Path(__file__).resolve().parents[2] if repo_root is None else Path(repo_root)

    def provider() -> dict:
        if off:
            return {"mode": "off", "monitor": dict(MONITOR_PLACEHOLDER)}
        try:
            tool_rows, _ = tool_collector()
        except Exception:
            return {"mode": "error", "monitor": _error_child("TOOLS")}
        try:
            hook_rows, _ = hook_collector(hook_root)
        except Exception:
            return {"mode": "error", "monitor": _error_child("HOOKS")}
        try:
            skill_rows, _ = (skill_collector(awiki_root=awiki_root)
                             if awiki_root is not None else skill_collector())
        except Exception:
            return {"mode": "error", "monitor": _error_child("SKILLS")}
        collected = {"tools": list(tool_rows), "hooks": list(hook_rows),
                     "skills": list(skill_rows)}
        summary = {"generated_at": datetime.now(timezone.utc).isoformat()}
        inputs = {}
        for section, rows in collected.items():
            summary[section] = _section_summary(rows)
            # Dataclass rows are flattened for the projection seam; anything
            # else passes through untouched so the projection's own typed
            # DEGRADED fallback owns validation.
            inputs[section] = [
                asdict(row) if type(row) is _ROW_TYPES[section] else row
                for row in rows[-_INSPECTOR_ROWS_LIMIT:]
            ]
        try:
            views = build_monitor_views(
                bus_health={"degraded": True, "counters": {},
                            "conditions": ["MONITOR_BUS_ABSENT"]},
                timeline_records=(), stm_states=(), correlation=None,
                inspector={"summary": summary, **inputs},
            )
        except Exception:
            return {"mode": "error", "monitor": _error_child("PROJECTION")}
        return {"mode": "live", "monitor": views}

    provider.initial_child = dict(MONITOR_PLACEHOLDER if off else MONITOR_NOT_COLLECTED)
    return provider
