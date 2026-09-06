"""WO-P1-158 — production recovery consumer for child.identity.json.

Pure restart-reconciliation under the EXISTING recovery authority: reads the
durable identity document, re-observes the actual running child through an
injected observer (same primitives the supervisor uses), and classifies:

- exact match (PID + creation time + executable + parent) ⇒ ATTACH
- PID alive but any identity fact mismatched (incl. PID reuse) ⇒ RECOVERY_REQUIRED
- PID gone / malformed document / unreadable ⇒ RECOVERY_REQUIRED (no attach)

Evidence-truth contract: ``target_argv_sha256`` in the durable document is
LAUNCH evidence — written by the helper from the exact allowlisted argv at
spawn time — and is NOT re-observed live, because the OS observer can only
independently corroborate PID, creation time, executable, and parent across
the supported platforms. Live restart identity authority therefore uses
ONLY those observable facts; persisted-but-not-reobserved evidence is never
described or tested as live-verified. No kill authority, no replay
authority, no polling thread, no new store: the document is evidence for
reconciliation only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from .zcode_supervised_helper import (
    ZCodeChildIdentity,
    parse_child_identity_document,
)


class ZCodeChildRecoveryKind(str, Enum):
    ATTACH = "ATTACH"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


@dataclass(frozen=True, slots=True)
class ZCodeChildRecoveryDecision:
    kind: ZCodeChildRecoveryKind
    execution_id: str | None = None
    child_pid: int | None = None
    reason_code: str | None = None

    @property
    def attach(self) -> bool:
        return self.kind is ZCodeChildRecoveryKind.ATTACH


from typing import Protocol


class ZCodeChildProcessObserver(Protocol):
    """Exact child re-observation (same primitive shape the supervisor uses)."""

    def observe_child(self, pid: int) -> dict | None:
        """Return {'pid','created_epoch_ms','executable','parent_pid'} for a
        LIVE child or None when the PID is gone."""


def reconcile_zcode_child(
    identity_document: object,
    *,
    observer: ZCodeChildProcessObserver,
) -> ZCodeChildRecoveryDecision:
    """Reconcile one durable identity document against live process truth.

    Compares ONLY the facts the OS observer can independently corroborate
    (PID, creation time, executable, parent). The persisted argv digest is
    launch evidence and is intentionally not part of the live check."""
    try:
        identity = parse_child_identity_document(identity_document)
    except (ValueError, TypeError) as exc:
        return ZCodeChildRecoveryDecision(
            ZCodeChildRecoveryKind.RECOVERY_REQUIRED, reason_code=f"IDENTITY_MALFORMED:{exc}"
        )
    live = observer.observe_child(identity.child_pid)
    if live is None:
        return ZCodeChildRecoveryDecision(
            ZCodeChildRecoveryKind.RECOVERY_REQUIRED,
            execution_id=identity.execution_id,
            child_pid=identity.child_pid,
            reason_code="CHILD_PID_GONE",
        )
    # PID reuse: same pid, different creation time => NOT the original child
    if int(live.get("created_epoch_ms", 0)) != identity.child_created_epoch_ms:
        return ZCodeChildRecoveryDecision(
            ZCodeChildRecoveryKind.RECOVERY_REQUIRED,
            execution_id=identity.execution_id,
            child_pid=identity.child_pid,
            reason_code="CHILD_PID_REUSED",
        )
    live_exe = str(live.get("executable", ""))
    if live_exe.casefold() != identity.executable.casefold():
        return ZCodeChildRecoveryDecision(
            ZCodeChildRecoveryKind.RECOVERY_REQUIRED,
            execution_id=identity.execution_id,
            child_pid=identity.child_pid,
            reason_code="CHILD_EXECUTABLE_MISMATCH",
        )
    if int(live.get("parent_pid", 0)) != identity.parent_pid:
        return ZCodeChildRecoveryDecision(
            ZCodeChildRecoveryKind.RECOVERY_REQUIRED,
            execution_id=identity.execution_id,
            child_pid=identity.child_pid,
            reason_code="CHILD_PARENT_MISMATCH",
        )
    return ZCodeChildRecoveryDecision(
        ZCodeChildRecoveryKind.ATTACH,
        execution_id=identity.execution_id,
        child_pid=identity.child_pid,
    )


def read_child_identity_from_run_dir(run_dir: Path) -> object:
    """Read + JSON-parse child.identity.json from a run dir (evidence only)."""
    import json

    path = Path(run_dir) / "child.identity.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"__unreadable__": str(type(exc).__name__)}
