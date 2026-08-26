"""Project folder size display — pure filesystem walk, no subprocess.

WO-P1-070: shows total disk usage of the selected project folder.
The exact size remains the authoritative data display. A bounded log-magnitude
particle helper feeds the optional SYSTEM OVERVIEW visual cue without extra I/O.
"""

from __future__ import annotations

import math
import os
import re
from pathlib import Path
from typing import Callable


def folder_size_bytes(
    path: Path | str,
    *,
    cancel_check: Callable[[], bool] | None = None,
) -> int | None:
    """Total size in bytes of all files under ``path`` (recursive walk).

    Never spawns a process. Returns 0 for missing/unreadable paths and ``None``
    when cooperative cancellation is requested.
    """
    if cancel_check is not None and cancel_check():
        return None
    root = Path(path)
    if not root.is_dir():
        return 0
    total = 0
    try:
        for dirpath, _dirnames, filenames in os.walk(root):
            if cancel_check is not None and cancel_check():
                return None
            for filename in filenames:
                if cancel_check is not None and cancel_check():
                    return None
                try:
                    total += os.path.getsize(os.path.join(dirpath, filename))
                except (OSError, ValueError):
                    continue
    except OSError:
        return 0
    return total


def format_size(num_bytes: int) -> str:
    """Human-readable size: B, KB, MB, GB, TB (1 decimal place)."""
    if num_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


_SIZE_RE = re.compile(r"^\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>B|KB|MB|GB|TB)\s*$", re.I)
_SIZE_UNITS = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
_DISK_PARTICLE_COUNT = 24

def disk_particle_levels(display_value: str, *, count: int = _DISK_PARTICLE_COUNT) -> tuple[float, ...]:
    """Map formatted size to a bounded visual-only logarithmic gradient."""
    if count < 1:
        raise ValueError("count must be positive")
    match = _SIZE_RE.match(str(display_value))
    if match is None:
        return (0.0,) * count
    num_bytes = float(match.group("value")) * _SIZE_UNITS[match.group("unit").upper()]
    if num_bytes <= 0:
        return (0.0,) * count
    magnitude = max(0.0, min(4.0, math.log(num_bytes, 1024.0)))
    lit = max(1, min(count, int(round((magnitude / 4.0) * count))))
    return tuple((i + 1) / lit for i in range(lit)) + (0.0,) * (count - lit)


def project_disk_display(
    path: Path | str | None,
    *,
    cancel_check: Callable[[], bool] | None = None,
) -> str | None:
    """Formatted size string, ``—`` when unavailable, or ``None`` if cancelled."""
    if not path:
        return "—"
    size = folder_size_bytes(path, cancel_check=cancel_check)
    if size is None:
        return None
    return format_size(size)
