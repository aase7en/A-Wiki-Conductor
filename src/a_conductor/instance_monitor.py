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


def tail_lines(path: Path | None, count: int = 12, max_bytes: int = 65536) -> list[str]:
    """Tail the last lines without loading the whole file into memory."""
    if path is None or not path.is_file():
        return []
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > max_bytes:
                handle.seek(size - max_bytes)
                handle.readline()  # drop the partial first line
            chunk = handle.read(max_bytes)
    except OSError:
        return []
    return chunk.decode("utf-8", errors="replace").splitlines()[-count:]


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
    """Working-set size in MB. Native Windows API via ctypes — NEVER spawns
    a process (no powershell, no cmd). See DEFECT_LESSONS.md #1."""
    if pid is None or pid <= 0:
        return None
    if sys.platform == "win32":
        if runner is not None:
            # Test mode: use the injected runner
            code, out, _err = runner(["fake"])
            if code == 0 and out.strip().isdigit():
                return round(int(out.strip()) / (1024 * 1024), 1)
            return None
        # Production: native Windows API (zero process spawn)
        try:
            import ctypes
            import ctypes.wintypes

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", ctypes.wintypes.DWORD),
                    ("PageFaultCount", ctypes.wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            handle = ctypes.windll.kernel32.OpenProcess(
                0x0400 | 0x0010,  # PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
                False, pid,
            )
            if handle:
                try:
                    if ctypes.windll.psapi.GetProcessMemoryInfo(
                        handle, ctypes.byref(counters), counters.cb
                    ):
                        return round(counters.WorkingSetSize / (1024 * 1024), 1)
                finally:
                    ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            pass
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
    """Build the monitor report for an instance.

    GUARANTEE: NEVER spawns any process (no cmd.exe, no powershell.exe).
    All data gathered via file reads and native Windows API (ctypes).
    See DEFECT_LESSONS.md #1.
    """
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
