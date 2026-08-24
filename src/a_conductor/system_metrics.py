"""Lightweight real system metrics for the desktop command-center overview.

The sampler intentionally avoids periodic shell/process execution. Windows uses
native kernel APIs via ``ctypes``; Linux uses ``/proc`` files. Unsupported
platform metrics degrade to ``None`` so the UI can render an honest em dash.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os
from pathlib import Path
import sys
import time
from typing import Callable

_GIB = 1024**3

CpuTimesReader = Callable[[], tuple[int, int] | None]
MemoryReader = Callable[[], tuple[int, int] | None]
Clock = Callable[[], float]


@dataclass(frozen=True, slots=True)
class SystemMetrics:
    cpu_percent: float | None
    memory_used_bytes: int | None
    memory_total_bytes: int | None
    uptime_seconds: float


def format_percent(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{max(0.0, min(100.0, value)):.0f}%"


def format_memory(used_bytes: int | float | None, total_bytes: int | float | None) -> str:
    if used_bytes is None or total_bytes is None or total_bytes <= 0:
        return "—"
    return f"{float(used_bytes) / _GIB:.1f} / {float(total_bytes) / _GIB:.1f} GB"


def format_uptime(seconds: float) -> str:
    total = max(0, int(seconds))
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days:
        return f"{days}d {hours:02d}h {minutes:02d}m"
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _filetime_to_int(value: wintypes.FILETIME) -> int:
    return (int(value.dwHighDateTime) << 32) | int(value.dwLowDateTime)


def _windows_cpu_times() -> tuple[int, int] | None:
    if os.name != "nt":
        return None
    try:
        kernel32 = ctypes.windll.kernel32
        idle = wintypes.FILETIME()
        kernel = wintypes.FILETIME()
        user = wintypes.FILETIME()
        ok = kernel32.GetSystemTimes(
            ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
        )
        if not ok:
            return None
        idle_ticks = _filetime_to_int(idle)
        total_ticks = _filetime_to_int(kernel) + _filetime_to_int(user)
        return idle_ticks, total_ticks
    except Exception:
        return None


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def _windows_memory() -> tuple[int, int] | None:
    if os.name != "nt":
        return None
    try:
        status = _MemoryStatusEx()
        status.dwLength = ctypes.sizeof(_MemoryStatusEx)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None
        total = int(status.ullTotalPhys)
        available = int(status.ullAvailPhys)
        if total <= 0:
            return None
        used = max(0, min(total, total - available))
        return used, total
    except Exception:
        return None


def _linux_cpu_times() -> tuple[int, int] | None:
    if not sys.platform.startswith("linux"):
        return None
    try:
        first = Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0].split()
        if not first or first[0] != "cpu":
            return None
        values = [int(item) for item in first[1:]]
        if len(values) < 4:
            return None
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        # guest and guest_nice (fields 9-10) are already included in user and
        # nice by the Linux kernel, so including them would double-count time.
        total = sum(values[:8])
        return idle, total
    except (OSError, ValueError, IndexError):
        return None


def _linux_memory() -> tuple[int, int] | None:
    if not sys.platform.startswith("linux"):
        return None
    try:
        values: dict[str, int] = {}
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, _, raw = line.partition(":")
            if key not in {"MemTotal", "MemAvailable"}:
                continue
            amount = raw.strip().split()[0]
            values[key] = int(amount) * 1024
        total = values.get("MemTotal")
        available = values.get("MemAvailable")
        if not total or available is None:
            return None
        used = max(0, min(total, total - available))
        return used, total
    except (OSError, ValueError, IndexError):
        return None


def _default_cpu_times() -> tuple[int, int] | None:
    if os.name == "nt":
        return _windows_cpu_times()
    if sys.platform.startswith("linux"):
        return _linux_cpu_times()
    return None


def _default_memory() -> tuple[int, int] | None:
    if os.name == "nt":
        return _windows_memory()
    if sys.platform.startswith("linux"):
        return _linux_memory()
    return None


class SystemMetricsSampler:
    """Stateful low-cost sampler; CPU utilisation is derived from counter deltas."""

    def __init__(
        self,
        *,
        clock: Clock = time.monotonic,
        cpu_times_reader: CpuTimesReader | None = None,
        memory_reader: MemoryReader | None = None,
    ) -> None:
        self._clock = clock
        self._cpu_times_reader = cpu_times_reader or _default_cpu_times
        self._memory_reader = memory_reader or _default_memory
        self._started_at = float(clock())
        self._previous_cpu_times = self._safe_cpu_times()

    def _safe_cpu_times(self) -> tuple[int, int] | None:
        try:
            return self._cpu_times_reader()
        except Exception:
            return None

    def _safe_memory(self) -> tuple[int, int] | None:
        try:
            return self._memory_reader()
        except Exception:
            return None

    def sample(self) -> SystemMetrics:
        cpu_percent: float | None = None
        current_cpu = self._safe_cpu_times()
        previous_cpu = self._previous_cpu_times
        self._previous_cpu_times = current_cpu
        if previous_cpu is not None and current_cpu is not None:
            idle_delta = current_cpu[0] - previous_cpu[0]
            total_delta = current_cpu[1] - previous_cpu[1]
            if total_delta > 0:
                busy = total_delta - max(0, idle_delta)
                cpu_percent = max(0.0, min(100.0, busy / total_delta * 100.0))

        memory = self._safe_memory()
        used: int | None = None
        total: int | None = None
        if memory is not None:
            used, total = memory

        return SystemMetrics(
            cpu_percent=cpu_percent,
            memory_used_bytes=used,
            memory_total_bytes=total,
            uptime_seconds=max(0.0, float(self._clock()) - self._started_at),
        )
