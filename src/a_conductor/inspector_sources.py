"""Read-only local inspector collectors for WO-P1-739.

Guarantee for GREEN: never write files, spawn processes, load credentials,
or grant runtime authority. Only discovery and bounded health reads are allowed.
Each collector returns (rows, degraded_notes), with code-only degradation.
Omitted probe uses the existing health check; explicit None is discovery-only.
The RED checkpoint intentionally performs no discovery, probing, or file reads.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

from .inspector_projection import (
    HookInspectorRow,
    SkillInspectorRow,
    ToolInspectorRow,
)


def collect_local_tool_rows(
    instances_root: Path | str | None = None,
    *,
    probe: Callable[[object], object] | None | object = ...,
) -> tuple[tuple[ToolInspectorRow, ...], tuple[str, ...]]:
    """Reuse instance discovery and health; None disables all health probes."""
    raise NotImplementedError("INSPECTOR_SLICE_1_RED")


def collect_local_hook_rows(
    repo_root: Path | str,
) -> tuple[tuple[HookInspectorRow, ...], tuple[str, ...]]:
    """Read static contracts, never infer runtime hook liveness from presence."""
    raise NotImplementedError("INSPECTOR_SLICE_1_RED")


def collect_local_skill_rows(
    awiki_root: Path | str = Path(r"A:\GitHub\A-Wiki"),
    *,
    max_age_seconds: int = 7 * 24 * 60 * 60,
    now: datetime | None = None,
) -> tuple[tuple[SkillInspectorRow, ...], tuple[str, ...]]:
    """Read schema-v3 skills-registry.json; freshness uses file mtime, not JSON."""
    raise NotImplementedError("INSPECTOR_SLICE_1_RED")
