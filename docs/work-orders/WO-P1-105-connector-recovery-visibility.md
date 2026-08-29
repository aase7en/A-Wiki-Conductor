# WO-P1-105 — Connector recovery operator visibility

Date: 2026-08-28
Owner: GPT-5.6 Sol integrator
Status: COMPLETE / MERGED
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

## TDD implementation checkpoint — 2026-08-29

Implemented CR-4 without a second monitor/timer/store/lifecycle:
- `DesktopControlService.connector_recovery_record()` exposes fail-safe durable diagnostics;
- successful automatic recovery is detected only when durable `restart_count` advances;
- events use a bounded in-memory queue (`maxlen=64`) and drain exactly once;
- explicit Stop remains suppressed and never emits `AUTO-RECOVER`;
- MONITOR keeps `CONNECTION` separate and renders recovery state/counts/last exit/next retry;
- existing 15s connector refresh drains `AUTO-RECOVER <slot> READY restart=<n>` events.

Deterministic evidence:
- baseline before mutation: 77 passed, 1 local Tk-environment skip;
- RED new visibility suite: 6 failed on the six missing seams;
- GREEN visibility suite: 6 passed;
- focused recovery/control/store/monitor: 52 passed, 1 local Tk-environment skip;
- desktop UI integration: 49 passed;
- broader lifecycle/recovery/instance integration: 90 passed;
- `python -m compileall -q src`: PASS;
- `git diff --check`: PASS;
- bounded secret scan: 0 hits;
- diff audit: no added timer, subprocess, Popen, Thread, or Timer path.

Next: final intended-file/secret audit -> commit/push -> exact remote diff -> 3-OS CI -> post-CI re-audit -> merge -> reconcile WO-P1-096 release gate.

## Staff-review correction — 2026-08-29

Remote diff review found a replay edge: the UI diagnostic helper intentionally returns `None` on a transient store-read failure. Reusing that fail-closed value as the event baseline could compare an existing restart count against zero and emit an old `AUTO-RECOVER` event.

Correction removes diagnostic reads from event detection. A recovery event is queued only when the current observed transport health is `STOPPED` and the recovery coordinator returns durable state `READY`; in the accepted coordinator this result occurs only after a successful RUNNING/ALREADY_RUNNING recovery path increments `restart_count`.

Evidence:
- RED replay regression: 1 failed with an old `restart_count=7` event replay;
- GREEN visibility suite: 7 passed;
- focused recovery/control/monitor: 29 passed;
- desktop UI: 48 passed, 1 local Tk-installation skip;
- broader lifecycle/recovery/instance: 91 passed;
- compileall + diff-check: PASS.

## Repo-health reconciliation - 2026-08-29

- Historical execution text above is preserved as evidence; the stale status is superseded by accepted GitHub state.
- PR #133 merged into main as `599e0dcd68173aca857a14d77b5628cd2333e673`.
