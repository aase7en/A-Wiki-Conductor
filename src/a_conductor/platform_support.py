"""OS-aware defaults and process flags (cross-platform plan P1).

Windows keeps its validated behavior; macOS/Linux get home-relative roots
and POSIX process semantics. The env override wins on every platform.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ENV_INSTANCES_ROOT = "A_CONDUCTOR_INSTANCES_ROOT"


def is_windows() -> bool:
    return sys.platform == "win32"


def default_instances_root() -> Path:
    override = os.environ.get(ENV_INSTANCES_ROOT, "").strip()
    if override:
        return Path(override).expanduser()
    if is_windows():
        return Path("C:/AI/serena-instances")
    return Path.home() / "AI" / "serena-instances"


def process_creation_flags() -> int:
    """Flags for spawning owned processes without console windows.

    Windows: CREATE_NO_WINDOW. POSIX: 0 — console semantics don't exist;
    use start_new_session in Popen for process-group control instead.
    """
    if is_windows():
        return getattr(__import__("subprocess"), "CREATE_NO_WINDOW", 0)
    return 0
