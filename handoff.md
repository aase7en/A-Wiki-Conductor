# HANDOFF — A-Conductor

Last updated: 2026-08-21 (session 3 end)

## Current objective

One-app orchestration delivered end-to-end. Awaiting user trial feedback and next milestone pick.

## Status

`COMPLETE` for the authorized scope (one program to see/control all Serena tunnel instances, autostart, UI config fallback per user requirement).

## Baseline

- branch `main` at merge `a91a2a3` (PR #11); PRs #9-#11 CI-green
- full suite 780 passed, 2 skipped (display-dependent); real-app check passed (INSTANCES panel populated with live states, exit 0)

## What the next agent must know

- WO-P1-050 closed with evidence; design alternatives recorded in `docs/superpowers/specs/2026-08-21-one-app-orchestration-design.md` (MCP gateway deferred — future ADR).
- Instance lifecycle stays inside the validated scripts; the orchestrator only launches them detached and polls health (`local_instances.py`).
- `AConductorDesktopApp.start_background_operations()` must be called by real entrypoints (construction-time hooks caused a Tcl cross-thread teardown crash — see WO-P1-050 checkpoint).
- Real instances on this machine: Serena-Conductor (18011, STOPPED), Serena-Phase6 (18012, STOPPED), Serena-Wastewater (18013, READY/live).

## Safety state

- No real instance was started/stopped by automated work tonight (real checks were read-only: discovery + health GET).
- Wastewater instance remains live (user-created tunnel; watchdog available, not running unless the user starts it).

## Next safe action

Read CURRENT-WORK.md "Next safe action"; open a new work order + reuse gate before implementation.
