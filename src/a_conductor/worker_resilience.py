"""Worker recovery policy boundary (WO-P1-156) — production-wired policy only.

The ONE durable recovery authority is the existing production path:
``DesktopControlService.instance_states_cancellable`` →
``instance_health_state`` (real /readyz HTTP probe) →
``reconcile_instance_recovery`` → ``ConnectorRecoveryCoordinator`` →
``SQLiteSerenaConfigStore.instance_recovery`` → ``LocalInstanceOrchestrator``.
This module deliberately owns no store, classification table, circuit,
budget, dedupe registry or process control; earlier policy shapes without a
production consumer were deleted rather than kept as dead code.

EXTERNAL_CONTROL_SURFACE contract: remote plugin/session conditions
(HTTP 429, HTTP 404, stale remote session) are NOT observable by the local
recovery path — its only signal is the instance /readyz HTTP probe. They
are excluded from the local production-recovery claim: no local process may
be restarted, suppressed or marked degraded solely because of such a
condition observed on a remote surface.

Transient recovery holds (ownership/task/quarantine) are fail-closed gates
that defer — never persist — recovery intent: while a hold is active the
production path performs zero automatic recovery and must not invoke
``ConnectorRecoveryCoordinator.suppress`` (that is durable manual-stop
intent). When the hold clears, the same real failure is recovered through
the normal authority path with no manual start required.
"""

from __future__ import annotations

_HOLD_FLAGS = ("ownership_unsafe", "task_state_unknown", "quarantined")


def recovery_hold_active(
    *,
    ownership_unsafe: bool = False,
    task_state_unknown: bool = False,
    quarantined: bool = False,
) -> bool:
    """True while any transient recovery-hold cause exists.

    A hold is evaluated fresh on every production refresh; it is never
    persisted and never converts into manual-stop suppression.
    """
    for name in _HOLD_FLAGS:
        if not isinstance(getattr_value := locals()[name], bool):
            raise ValueError(f"{name} must be bool")
        if getattr_value:
            return True
    return False
