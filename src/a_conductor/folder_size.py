"""Project folder size display — pure filesystem walk, no subprocess.

WO-P1-070: shows total disk usage of the selected project folder.
Data-only display; the visual gradient/particle rendering is GPT design
lane. This module feeds the SYSTEM OVERVIEW "PROJECT DISK" metric.
"""

from __future__ import annotations

import os
from pathlib import Path


def folder_size_bytes(path: Path | str) -> int:
    """Total size in bytes of all files under ``path`` (recursive walk).

    Never spawns a process. Returns 0 for missing/unreadable paths.
    """
    root = Path(path)
    if not root.is_dir():
        return 0
    total = 0
    try:
        for dirpath, _dirnames, filenames in os.walk(root):
            for filename in filenames:
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


def project_disk_display(path: Path | str | None) -> str:
    """Formatted size string for UI display, or '—' when unavailable."""
    if not path:
        return "—"
    return format_size(folder_size_bytes(path))
