# WO-P1-099 — Connector bounded auto-recovery core

Date: 2026-08-28
Owner: GPT-5.6 Sol integrator
Status: REVIEW_READY — CORE LOCAL GREEN / PR PENDING
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-connector-recovery`
Branch: `fix/wo-p1-099-connector-auto-recovery`
Base: `origin/main@ceee9bb7aa361aef6d0ecfc210c25b564578d552`; reconciled `origin/main@dec80993f7c567e370d09288386ebb87e7f3f4e9`
Parent: `WO-P1-096` CR-2 / CR-4

## Goal

Implement the durable, deterministic connector recovery core required by CR-2 without adding a second lifecycle/store/scheduler. Unexpected STOPPED autostart connectors recover with bounded backoff; explicit Stop remains suppressed; repeated failure becomes DEGRADED.

## Reuse gate

Classification: **EXTEND + WRAP**.
Reuse `SQLiteSerenaConfigStore`, `LocalInstanceOrchestrator.start/stop`, connector `/readyz` observations, and the existing low-frequency single-flight connector refresh. No new process monitor, subprocess timer, job store, or worker model.
## Allowed scope

- new `src/a_conductor/connector_recovery.py`
- new `tests/test_connector_recovery.py`
- `src/a_conductor/serena_config_store.py` + focused tests for durable recovery state
- `src/a_conductor/desktop_control.py` + focused tests for explicit intent/recovery seams
- this work order

Forbidden: PR #124 AHA files/SSoT, PR #108 installer, North Star, live connector fleet, tunnel-client binary, A-Wiki, UI mutation until CR-2 core is accepted.

## Acceptance

1. READY -> no recovery launch.
2. UNKNOWN -> fail closed; no recovery launch.
3. unexpected STOPPED + autostart + unsuppressed -> RECOVERING and one due restart attempt.
4. explicit Stop suppresses recovery before stop execution; manual Start clears suppression and failure budget.
5. failures use bounded backoff; 3 failures inside 5 minutes -> DEGRADED and no restart storm.
6. successful recovery -> READY and durable restart count.
7. recovery state survives store reopen and contains no tunnel/secret values.
8. deleting/clearing instance flags clears recovery state.
9. deterministic fake tests only; no live process/network mutation.
10. existing config/control/local-instance suites remain green.


## Core implementation checkpoint — 2026-08-28

Implemented CR-2 core without UI mutation:
- durable `ConnectorRecoveryRecord` in existing `SQLiteSerenaConfigStore`;
- pure `ConnectorRecoveryCoordinator` over injected clock/autostart/start seam;
- explicit Stop suppression is persisted before stop execution;
- manual Start clears suppression/failure budget before launch;
- unexpected STOPPED autostart connector uses bounded backoff; third failure within 5 minutes becomes `DEGRADED`;
- READY resets transient failure state; UNKNOWN never launches;
- successful recovery increments durable restart count;
- clearing instance flags also removes recovery state.

Deterministic evidence:
- RED: recovery module missing; then core **8 passed**;
- RED: store API missing; then config/recovery **16 passed**;
- RED: DesktopControl integration **4 failed**; then **4 passed**;
- focused CR-2/config/control/local-instance regression: **80 passed**;
- `python -m compileall -q src/a_conductor`: PASS;
- `git diff --check`: PASS.

Next: scope/secret audit -> commit/push Draft PR -> exact remote diff -> 3-OS CI. CR-4 UI/operator state remains a separate follow-up after CR-2 core acceptance.

## Production wiring + idempotence repair ? 2026-08-28

Independent review findings `5051679381` / `5051827379` were reproduced on current-main integration: the recovery core had no production caller. `instance_states_cancellable()` only probed health, so the existing 15-second single-flight refresh could observe STOPPED forever without invoking recovery.

RED production-path evidence:
- STOPPED + autostart via `instance_states_cancellable()` did not call the existing orchestrator start seam;
- cancellation after a health probe still returned the row instead of aborting before recovery.

Repair stays inside the existing monitor/lifecycle architecture:
- `instance_states_cancellable()` now reconciles recovery after each health probe; no second timer/monitor was added;
- app cancellation is checked before probe, after probe, inside recovery, and propagated to `LocalInstanceOrchestrator.start(cancel_check=...)`; `START_CANCELLED` does not consume failure budget;
- successful bounded recovery maps that refresh result to READY because the existing orchestrator returns RUNNING only after its readiness probe passes;
- READY/UNKNOWN observations never launch recovery.

Deep-bug review also found that enabling the 15-second caller would otherwise rewrite durable SQLite state on every unchanged READY/explicit-STOPPED observation and continually move `last_exit_at`. Repeated stable observations are now idempotent; unchanged READY/STOPPED records are returned without a write and an existing exit timestamp is preserved.

Verification on the reconciled branch: focused recovery/control `19 passed`; broader config/control/local-instance/monitor `58 passed`; compileall PASS; `git diff --check` PASS. Next: exact scope/secret audit -> commit/push -> fresh 3-OS CI -> final remote diff/review -> merge. CR-4 operator visibility remains a separate follow-up after CR-2 acceptance.

## Explicit-Stop metadata repair - 2026-08-28

Final staff review reproduced a semantic defect before merge: an explicit Stop was correctly persisted as `recovery_suppressed=True`, but the next STOPPED health observation rewrote `last_exit_reason` to `UNEXPECTED_STOPPED` and invented a new `last_exit_at`. That would make CR-4 operator diagnostics falsely report a user-requested stop as an incident.

Repair separates explicit suppression from non-autostart stop classification. A suppressed stable STOPPED observation now returns the existing durable record without a write or exit-metadata mutation; non-autostart unexpected stops retain their prior classification behavior.

Evidence: RED single regression `1 failed`; after repair single `1 passed`, focused recovery/control `19 passed`, broader recovery/config/control/local-instance/monitor `77 passed`; compileall, diff-check, and bounded secret scan PASS.
