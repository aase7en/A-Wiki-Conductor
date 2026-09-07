"""WO-P1-158 — real OS child-process observation for exact identity.

One primitive, ``observe_child_process(pid)``, returns the SAME fact shape the
recovery consumer accepts (``{'pid','created_epoch_ms','executable',
'parent_pid'}``) but from the REAL operating system:

- Windows: kernel32 via ctypes (OpenProcess + GetProcessTimes +
  QueryFullProcessImageNameW + toolhelp32 snapshot for the actual parent PID).
- Linux: ``/proc/<pid>/stat`` (ppid + starttime) and ``/proc/<pid>/exe``.
- macOS/other POSIX: ``ps -p <pid> -o ppid= -o lstart= -o comm=``.

Fail-closed: any observation failure returns ``None`` — a child whose exact
identity cannot be observed is NEVER given a fabricated/wall-clock identity.
No process is created, killed, or modified here: read-only observation only.
"""

from __future__ import annotations

import os
import re


def observe_child_process(pid: int) -> dict | None:
    """Observe one live process or return None (gone / unobservable)."""
    if isinstance(pid, bool) or not isinstance(pid, int) or pid < 1:
        return None
    if os.name == "nt":
        return _observe_windows(pid)
    if os.path.exists("/proc"):
        return _observe_procfs(pid)
    return _observe_ps(pid)


# ---------------- Windows (kernel32 via ctypes) ----------------

def _observe_windows(pid: int) -> dict | None:
    import ctypes
    import ctypes.wintypes as wt

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        # creation time (FILETIME, 100ns since 1601-01-01 UTC)
        creation = wt.FILETIME()
        exit_time = wt.FILETIME()
        kernel_time = wt.FILETIME()
        user_time = wt.FILETIME()
        if not kernel32.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel_time),
            ctypes.byref(user_time),
        ):
            return None
        filetime = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
        epoch_ms = (filetime - 116444736000000000) // 10000
        if epoch_ms <= 0:
            return None

        # actual executable image path
        size = wt.DWORD(1024)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return None
        executable = buffer.value

        parent_pid = _windows_parent_pid(kernel32, pid)
        if parent_pid is None:
            return None
        return {
            "pid": pid,
            "created_epoch_ms": int(epoch_ms),
            "executable": executable,
            "parent_pid": int(parent_pid),
        }
    finally:
        kernel32.CloseHandle(handle)


def _windows_parent_pid(kernel32, pid: int) -> int | None:
    """Actual parent PID from the OS process table (toolhelp32 snapshot)."""
    import ctypes
    import ctypes.wintypes as wt

    TH32CS_SNAPPROCESS = 0x2

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wt.DWORD),
            ("cntUsage", wt.DWORD),
            ("th32ProcessID", wt.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wt.DWORD),
            ("cntThreads", wt.DWORD),
            ("th32ParentProcessID", wt.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wt.DWORD),
            ("szExeFile", wt.WCHAR * 260),
        ]

    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot in (0, -1):  # INVALID_HANDLE_VALUE is -1 as a handle
        return None
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            return None
        while True:
            if entry.th32ProcessID == pid:
                return int(entry.th32ParentProcessID)
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                return None
    finally:
        kernel32.CloseHandle(snapshot)


# ---------------- Linux (/proc) ----------------

def _observe_procfs(pid: int) -> dict | None:
    import datetime

    stat_path = f"/proc/{pid}/stat"
    try:
        raw = open(stat_path, encoding="utf-8").read()
    except OSError:
        return None
    # fields after the (comm) block: state(3) ppid(4) ... starttime(22)
    close = raw.rfind(")")
    if close < 0:
        return None
    fields = raw[close + 1:].split()
    try:
        ppid = int(fields[1])
        starttime_ticks = int(fields[19])
    except (IndexError, ValueError):
        return None
    try:
        with open("/proc/stat", encoding="utf-8") as f:
            btime_line = next(l for l in f if l.startswith("btime"))
        boot_epoch = int(btime_line.split()[1])
        clock_ticks = os.sysconf("SC_CLK_TCK")
    except (OSError, StopIteration, ValueError):
        return None
    hz = clock_ticks if clock_ticks and clock_ticks > 0 else 100
    epoch_ms = (boot_epoch + starttime_ticks // hz) * 1000
    try:
        executable = os.readlink(f"/proc/{pid}/exe")
    except OSError:
        try:
            executable = open(f"/proc/{pid}/comm", encoding="utf-8").read().strip()
        except OSError:
            return None
    return {
        "pid": pid,
        "created_epoch_ms": int(epoch_ms),
        "executable": executable,
        "parent_pid": int(ppid),
    }


# ---------------- macOS / other POSIX (ps) ----------------

_PS_LSTART_RE = re.compile(
    r"([A-Za-z]{3})\s+(\d{1,2})\s+(\d{2}:\d{2}:\d{2})\s+(\d{4})"
)
_MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def _observe_ps(pid: int) -> dict | None:
    import datetime
    import subprocess

    try:
        completed = subprocess.run(
            ["ps", "-p", str(pid), "-o", "ppid=", "-o", "lstart=", "-o", "comm="],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    parts = completed.stdout.strip().split(None, 1)
    if len(parts) != 2:
        return None
    try:
        ppid = int(parts[0])
    except ValueError:
        return None
    match = _PS_LSTART_RE.search(parts[1])
    if match is None:
        return None
    month, day, clock, year = match.groups()
    try:
        hour, minute, second = (int(x) for x in clock.split(":"))
        created = datetime.datetime(
            int(year), _MONTHS[month], int(day), hour, minute, second,
            tzinfo=datetime.timezone.utc,
        )
    except (KeyError, ValueError):
        return None
    executable = parts[1][match.end():].strip()
    if not executable:
        return None
    return {
        "pid": pid,
        "created_epoch_ms": int(created.timestamp() * 1000),
        "executable": executable,
        "parent_pid": ppid,
    }
