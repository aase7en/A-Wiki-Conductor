# A-Conductor — Current Work

Last updated: 2026-08-21 (session 3)

## Current phase

**One-app orchestration delivered: open `a-conductor`, see and control every Serena tunnel instance.**

## Session 3 summary (GLM 5.3/ZCode under user authorization)

PRs #9-#11 (WO-P1-050), CI-green before every merge:

- **PR #9** (`docs`): design doc with alternatives — MCP multiplexer gateway explicitly deferred (needs protocol proxy subsystem; risks second orchestration universe; Serena already supports multi-project activation); script-wrapping orchestration chosen per the user's fallback clause.
- **PR #10**: `local_instances.py` — zero-config discovery (parses validated `instance.ps1`), health via existing readyz probe, orchestrator that starts instances detached+polls and stops via the validated scripts (never kills, never waits on the blocking start script).
- **PR #11**: `instance_flags` autostart persistence + facade + **INSTANCES panel** in the app (READY/STOPPED/UNKNOWN semantic colors, Start/Stop/Start-All/Toggle-Auto/Rescan, palette entry); autostart honored at real app launch via `start_background_operations()`.

## Evidence

- Full suite 780 passed, 2 skipped (display-dependent), 0 failed; smoke OK.
- Real-machine read-only: discovery found all 3 real instances; health states correct (Wastewater READY live).
- **Real-app check**: actual application launched (withdrawn root, real DB/service) — INSTANCES panel auto-populated with correct live states; exit 0.
- Debug loops this session (root-caused): fake-probe observation contract; clock injection for poll loops; `Tcl_AsyncDelete wrong thread` teardown crash (bisected to construction-time hooks + smoke's real service → moved to explicit `start_background_operations()`).

## User-facing workflow now

Open `a-conductor` → see Projects/Workers + INSTANCES with health → select instance → Start/Stop; flag Auto for launch-time autostart; Config dialog per worker; Start All for one-click bring-up. No more opening each `Start-*.cmd` by hand.

## DECISION_REQUIRED / future

- MCP gateway (one server, any provider's plugin, dynamic project routing) — deferred with rationale in `docs/superpowers/specs/2026-08-21-one-app-orchestration-design.md`; needs its own ADR + A-Wiki gate.
- Changing an instance's bound project from the UI (instance project pinning currently comes from the validated `instance.ps1`).
- Flipping `supervised=True` default (static identity noted in WO-P1-049).

## Next safe action

User tries the real app (`a-conductor`) and reports friction; natural next chunks: materialize `WorkerSerenaSettings` into SERENA_HOME on start, or instance-project rebinding UI. Open a new work order first.
