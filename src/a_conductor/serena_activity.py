"""Read-only observation of Serena's current active project from runtime logs.

This is telemetry only: it never invokes Serena/MCP tools and never mutates connector state.
Serena runtime stderr files may retain legacy instance names after a connector is renamed,
so the observer selects the newest ``*-runtime.stderr.log``. It scans backwards in
bounded chunks and stops as soon as the newest real Serena activation record is present.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re


_DEFAULT_MAX_BYTES = 2 * 1024 * 1024
_READ_CHUNK_BYTES = 64 * 1024
_ACTIVATION_RE = re.compile(
    r"^(?:DEBUG|INFO|WARNING|ERROR)\s+"
    r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+)\s+"
    r"\[[^]\r\n]+\]\s+serena\.agent:_activate_project:\d+\s+-\s+"
    r"Activating (?P<name>.+?) at (?P<path>.+?)\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class SerenaActivityObservation:
    """Latest project-activation observation for one live Serena instance."""

    active_project_name: str | None = None
    active_project_path: str | None = None
    switched_at: datetime | None = None


def _activation_suffix(path: Path, *, max_bytes: int) -> str:
    """Return a bounded suffix containing the newest real activation record.

    The file is read from the end in small chunks. As soon as the accumulated suffix
    contains a Serena ``_activate_project`` record we stop, because earlier bytes
    cannot contain a newer activation. ``max_bytes`` remains a hard I/O ceiling.
    """

    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    try:
        size = path.stat().st_size
    except OSError:
        return ""
    if size <= 0:
        return ""

    limit = min(size, max_bytes)
    payload = b""
    offset = size
    read_total = 0
    try:
        with path.open("rb") as handle:
            while read_total < limit:
                read_size = min(_READ_CHUNK_BYTES, limit - read_total)
                offset -= read_size
                handle.seek(offset)
                payload = handle.read(read_size) + payload
                read_total += read_size
                text = payload.decode("utf-8", errors="replace")
                if _ACTIVATION_RE.search(text):
                    return text
    except OSError:
        return ""
    return payload.decode("utf-8", errors="replace")


def _runtime_stderr_log(instance_root: Path | str) -> Path | None:
    """Return the newest runtime stderr log, including legacy instance names."""

    log_dir = Path(instance_root) / "logs"
    try:
        candidates = [
            path for path in log_dir.glob("*-runtime.stderr.log") if path.is_file()
        ]
    except OSError:
        return None
    if not candidates:
        return None

    def modified_ns(path: Path) -> int:
        try:
            return path.stat().st_mtime_ns
        except OSError:
            return -1

    return max(candidates, key=modified_ns)


def observe_serena_activity(
    instance_root: Path | str,
    *,
    max_bytes: int = _DEFAULT_MAX_BYTES,
) -> SerenaActivityObservation:
    """Return the latest observed active project for a connector.

    Missing/unreadable logs are normal and return an empty observation. Runtime I/O is
    bounded and accepts only Serena's own ``serena.agent:_activate_project`` logger
    signature, so quoted tool/test output cannot masquerade as live project state.
    """

    log_path = _runtime_stderr_log(instance_root)
    if log_path is None:
        return SerenaActivityObservation()
    text = _activation_suffix(log_path, max_bytes=max_bytes)
    latest = None
    for match in _ACTIVATION_RE.finditer(text):
        latest = match
    if latest is None:
        return SerenaActivityObservation()
    try:
        switched_at = datetime.strptime(
            latest.group("timestamp"), "%Y-%m-%d %H:%M:%S,%f"
        )
    except ValueError:
        return SerenaActivityObservation()
    return SerenaActivityObservation(
        active_project_name=latest.group("name").strip() or None,
        active_project_path=latest.group("path").strip() or None,
        switched_at=switched_at,
    )
