"""Read-only Serena memory-presence inspection (WO-P1-057).

Pure filesystem checks against the selected project's `.serena/memories/`.
Never writes, never mutates the target project, never starts the engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class MemoryPresenceState(str, Enum):
    NO_PROJECT = "NO_PROJECT"
    NO_MEMORIES = "NO_MEMORIES"
    EMPTY = "EMPTY"
    MAINTENANCE_ONLY = "MAINTENANCE_ONLY"
    HAS_MEMORIES = "HAS_MEMORIES"


@dataclass(frozen=True, slots=True)
class MemoryPresence:
    state: MemoryPresenceState
    total_files: int
    maintenance_only: bool


def inspect_memory_presence(project_root: Path | str) -> MemoryPresence:
    root = Path(project_root).expanduser().resolve(strict=False)
    if not root.is_dir():
        return MemoryPresence(MemoryPresenceState.NO_PROJECT, 0, False)
    memories_dir = root / ".serena" / "memories"
    if not memories_dir.is_dir():
        return MemoryPresence(MemoryPresenceState.NO_MEMORIES, 0, False)
    try:
        files = [item for item in sorted(memories_dir.iterdir()) if item.is_file()]
    except OSError:
        return MemoryPresence(MemoryPresenceState.EMPTY, 0, False)
    if not files:
        return MemoryPresence(MemoryPresenceState.EMPTY, 0, False)
    names = [item.name.lower() for item in files]
    maintenance_only = names == ["memory_maintenance.md"] or (
        len(names) == 1 and names[0].startswith("memory_maintenance")
    )
    state = (
        MemoryPresenceState.MAINTENANCE_ONLY
        if maintenance_only
        else MemoryPresenceState.HAS_MEMORIES
    )
    return MemoryPresence(state, len(files), maintenance_only)
