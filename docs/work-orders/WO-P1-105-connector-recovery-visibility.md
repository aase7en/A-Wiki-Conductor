# WO-P1-105 — Connector recovery operator visibility

Date: 2026-08-28
Owner: GPT-5.6 Sol integrator
Status: ACTIVE — CR-4 TDD
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-connector-recovery-ui`
Branch: `fix/wo-p1-105-connector-recovery-visibility`
Base: `origin/main@8dddb6ffe9dbbc561a9d3b4fb11501cf0fb3f33c`
Parent: WO-P1-096 CR-4; CR-2 accepted via PR #125

## Reuse classification

**EXTEND + WRAP** existing `ConnectorRecoveryRecord`, `DesktopControlService`, 15s connector refresh, MONITOR panel, and ACTIVITY / LOG. No new timer, monitor, store, scheduler, lifecycle, or recovery state machine.

## Operator contract

`CONNECTION` remains live `/readyz` transport health per `DESIGN.md`. Recovery state is a separate MONITOR diagnostic: `READY / RECOVERING / DEGRADED / STOPPED`, restart/failure counts, last-exit reason/time, and next retry. Missing recovery evidence renders `-`; never infer.

A successful automatic recovery emits `AUTO-RECOVER` once when durable `restart_count` advances. Explicit Stop must never produce an unexpected-exit event.
## Allowed mutable scope

- `src/a_conductor/desktop_control.py`
- `src/a_conductor/desktop_ui.py`
- focused connector/UI recovery tests
- this work order
- `DEFECT_LESSONS.md` only after verified prevention evidence

Forbidden: WO-P1-102/PR #131 files and SSoT hotspots; installer/PR #132; North Star; live connector mutation; tunnel-client binary; A-Wiki.

## Acceptance

1. MONITOR shows recovery state separately from CONNECTION health.
2. Restart/failure counts, last exit reason/time, next retry are factual from durable record; missing data is `-`.
3. Successful recovery produces one `AUTO-RECOVER` activity entry per restart-count increment, not every 15s refresh.
4. Explicit Stop produces no false AUTO-RECOVER/unexpected-exit diagnostic.
5. Recovery-store read failure degrades to unavailable diagnostics without breaking connector refresh/monitor.
6. Existing monitor remains async/single-flight and no periodic subprocess/MCP/timer is added.
7. Focused GUI/service tests, broader connector/monitor/UI regressions, compileall/diff/secret gates and exact-head 3-OS CI pass.
