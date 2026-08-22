"""Per-instance runtime monitoring (PID, memory, log tail, errors)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable

_ERROR_MARKERS = ("ERROR", "FAILED", "FAIL:", "CRITICAL")
_PID_FILE = Path("run") / "tunnel-client.pid"


def read_pid(instance_root: Path | str) -> int | None:
    path = Path(instance_root) / _PID_FILE
    try:
        text = path.read_text(encoding="utf-8").strip()
        return int(text) if text.isdigit() else None
    except (OSError, ValueError):
        return None


def latest_log_path(instance_root: Path | str) -> Path | None:
    logs = Path(instance_root) / "logs"
    if not logs.is_dir():
        return None
    candidates = sorted(logs.glob("*.log"))
    return candidates[-1] if candidates else None


def tail_lines(path: Path | None, count: int = 12) -> list[str]:
    if path is None or not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return lines[-count:]


def scan_errors(lines: list[str]) -> list[str]:
    flagged: list[str] = []
    for line in lines:
        upper = line.upper()
        if any(marker in upper for marker in _ERROR_MARKERS):
            flagged.append(line.strip())
    return flagged


def process_memory_mb(
    pid: int, *, runner: Callable[[list[str]], tuple[int, str, str]] | None = None
) -> float | None:
    """Working-set size in MB (PowerShell on Windows, /proc on Linux)."""
    if pid is None or pid <= 0:
        return None
    if sys.platform == "win32":
        def default_runner(argv: list[str]) -> tuple[int, str, str]:
            done = subprocess.run(argv, capture_output=True, text=True, timeout=10)
            return done.returncode, done.stdout, done.stderr

        active = runner or default_runner
        code, out, _err = active(
            [
                "powershell.exe", "-NoProfile", "-Command",
                f"(Get-Process -Id {pid}).WorkingSet64",
            ]
        )
        if code == 0 and out.strip().isdigit():
            return round(int(out.strip()) / (1024 * 1024), 1)
        return None
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                kb = int(line.split()[1])
                return round(kb / 1024, 1)
    except (OSError, ValueError, IndexError):
        pass
    return None


def monitor_report(instance_root: Path | str, *, state: str) -> dict:
    root = Path(instance_root)
    log = latest_log_path(root)
    tail = tail_lines(log)
    pid = read_pid(root)
    return {
        "state": state,
        "pid": pid,
        "memory_mb": process_memory_mb(pid) if pid else None,
        "log_file": str(log) if log else None,
        "tail": tail,
        "errors": scan_errors(tail),
    }
