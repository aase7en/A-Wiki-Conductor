# WO-P1-050: One-App Instance Orchestration

Status: in_progress
Lane/files: `src/a_conductor/local_instances.py`, `src/a_conductor/serena_config_store.py`, `src/a_conductor/desktop_control.py`, `src/a_conductor/desktop_ui.py`, `src/a_conductor/__init__.py`, `tests/test_local_instances.py`, `tests/test_desktop_ui.py`, `docs/superpowers/specs/2026-08-21-one-app-orchestration-design.md`, `docs/work-orders/WO-P1-050-one-app-orchestration.md`, `PROJECT-PLAN.md`, `CURRENT-WORK.md`, `handoff.md`
Branch: chunk/p1-050-one-app-orchestration-docs (PR series)
Model tier: high

## Goal

Open one program and work: the Control Center auto-discovers validated Serena tunnel instances, shows health, starts/stops them through their validated scripts, and auto-starts flagged instances on launch — removing the "open each cmd one by one" workflow (user requirement 2026-08-21).

## Reuse classification

`WRAP`: validated instance scripts own all credential/preflight/PID logic; the app only discovers, probes health (`LoopbackReadyzHttpProbe`), invokes scripts hidden, and parses results. The MCP-gateway alternative is explicitly deferred to a future ADR (design doc records trade-offs).

## Acceptance

- Discovery finds instances under the configured root by parsing `instance.ps1` (name/project/health address); no mutation.
- Health states READY/STOPPED/UNKNOWN via injectable probe.
- Start/stop return structured outcomes (`RUNNING`, `ALREADY_RUNNING`, `PORT_IN_USE`, `FAILED:<code>` + output tail); scripts run hidden, no shell, bounded timeout; orchestrator never kills processes.
- Autostart flags persist per instance and drive launch-time start (background executor).
- UI INSTANCES panel: list + states + Start/Stop/Start-All/Rescan + Auto checkboxes; CLI-minimal style.
- Full suite + CI green per PR; real-machine check is read-only (discovery + health only).

## Micro-steps

- [x] 050-A design doc (alternatives + trade-offs) + this work order
- [x] 050-B RED core service tests (discovery/probe/orchestrator)
- [x] 050-C implement `local_instances.py`
- [x] 050-D persistence + facade + UI panel + tests
- [ ] 050-E regression + close/push

## Forbidden

- No MCP gateway implementation; no edits to validated instance scripts; no real instance start/stop in automated tests; no broad process kills.

## Checkpoint log

- [2026-08-21] Opened; design doc records why the multiplexer gateway is deferred (user fallback clause sanctions the UI-orchestration path).
- [2026-08-21] 050-B/C complete: 12/12 tests green (RED first). Bugfix loop (2 rounds): fake probes now mimic real observation contract (`.state`/`.error_code` — STOPPED is only inferable from TRANSPORT_ERROR), and `clock_fn` injection replaced real `time.monotonic` so poll loops are deterministic (test time 61.75s → 0.39s). Start = detached launch + health poll (script owns lifecycle; orchestrator never waits on the blocking Start script and never kills). Real-machine read-only check: discovery found Serena-Conductor/Phase6/Wastewater with correct ports/projects; health = Wastewater READY (live), others STOPPED. Full suite 777 passed, 1 skipped.
- [2026-08-21] 050-D complete: `instance_flags` store table + facade (`instances`/`instance_states`/`instance_action`/autostart flags) + INSTANCES UI panel (states with semantic colors, Start/Stop/Start-All/Toggle-Auto/Rescan, palette entry). **Debug loop (root-caused via bisection)**: construction-time instance hooks made `run_smoke` (real service) submit real discovery/probe work to a pool thread and schedule timer callbacks on a root destroyed milliseconds later → `Tcl_AsyncDelete ... wrong thread` crash at pytest teardown. Fix: hooks moved to explicit `start_background_operations()` called only by the real entrypoint before mainloop; instance buttons start disabled. 24/24 UI tests + full suite 780 passed, 2 skipped (display-dependent), smoke OK.
