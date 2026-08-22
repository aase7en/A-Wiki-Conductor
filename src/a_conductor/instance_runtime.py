"""Runtime cleanup helpers for connector instances (best-effort, Windows-scoped)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _ps_quote(value: str) -> str:
    """Escape a value for a PowerShell single-quoted string."""
    return value.replace("'", "''")


def reap_instance_wrappers(instance_root: Path | str) -> list[int]:
    """Kill stale detached cmd/powershell wrappers whose command line points
    into the given instance folder (path-boundary match: the needle must be
    followed by a path separator, so sibling folders sharing a prefix are
    never matched). No-op outside Windows. Returns the PIDs it terminated."""
    if sys.platform != "win32":
        return []
    needle = str(Path(instance_root))
    if not needle.strip():
        return []
    quoted = _ps_quote(needle)
    script = (
        "Get-CimInstance Win32_Process -Filter \"Name='powershell.exe' or Name='cmd.exe'\" | "
        "Where-Object { $_.CommandLine -like ('*' + '" + quoted + "' + '\\*') } | "
        "ForEach-Object { $_.ProcessId }"
    )
    try:
        out = subprocess.run(
            [
                "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-Command", script,
            ],
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout
    except Exception:
        return []
    pids: list[int] = []
    for line in out.splitlines():
        line = line.strip()
        if not line.isdigit():
            continue
        pid = int(line)
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"], capture_output=True
        )
        if result.returncode == 0:
            pids.append(pid)
    return pids
