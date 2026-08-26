"""Read-only observation of Serena's current active project from runtime logs.

This is telemetry only: it never invokes Serena/MCP tools and never mutates connector state.
The tunnel runtime redirects Serena stderr to ``logs/conductor-runtime.stderr.log``.
Serena emits an ``Activating <name> at <path>`` record whenever ``activate_project``
changes the server-wide active project. We tail a bounded suffix and surface the
latest such observation for the desktop live view.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re


_DEFAULT_MAX_BYTES = 256 * 1024
_ACTIVATION_RE = re.compile(
    r"^(?:DEBUG|INFO|WARNING|ERROR)\s+"
    r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+)"
    r".*? - Activating (?P<name>.+?) at (?P<path>.+?)\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class SerenaActivityObservation:
    """Latest project-activation observation for one live Serena instance."""

    active_project_name: str | None = None
    active_project_path: str | None = None
    switched_at: datetime | None = None


def _tail_text(path: Path, *, max_bytes: int) -> str:
    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            start = max(0, size - max_bytes)
            handle.seek(start)
            payload = handle.read(max_bytes)
    except OSError:
        return ""
    if start:
        newline = payload.find(b"\n")
        if newline >= 0:
            payload = payload[newline + 1 :]
    return payload.decode("utf-8", errors="replace")


def observe_serena_activity(
    instance_root: Path | str,
    *,
    max_bytes: int = _DEFAULT_MAX_BYTES,
) -> SerenaActivityObservation:
    """Return the latest observed active project for a connector.

    Missing/unreadable logs are normal (for example a never-started connector)
    and return an empty observation. Only a bounded log tail is read.
    """

    log_path = Path(instance_root) / "logs" / "conductor-runtime.stderr.log"
    text = _tail_text(log_path, max_bytes=max_bytes)
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
