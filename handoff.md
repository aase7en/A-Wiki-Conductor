# HANDOFF — A-Conductor

Last updated: 2026-08-21 (autonomous night session 2 end)

## Current objective

Per-worker Serena configuration surface delivered end-to-end; resilient supervised path now a tested one-parameter enable; all clearable leftovers cleared. Awaiting user milestone decisions.

## Status

`COMPLETE` for the authorized night scope (update plan + clear leftovers + chunked PRs + self review/debug loop until product usable).

## Baseline

- branch `main` at merge `617fac5` (PR #7), all PRs #4-#7 CI-green before merge
- final regression on main: 764 passed, 2 skipped (display-dependent), 0 failed; smoke OK
- product runnable: `python -m pip install -e .` → `a-conductor`; Config dialog on worker rows

## What the next agent must know

- WO-P1-048/049 closed with evidence; PRs #4-#7 are the record.
- Config values persist via `SQLiteSerenaConfigStore.serena_worker_settings`; materialization into a live worker's `SERENA_HOME` on start is the identified next chunk (`apply_worker_serena_settings` exists and is tested — wiring into the start flow is not built yet).
- `DurableJobControlService.open(supervised=True)` enables durable/dedup/bounded execution; default remains plain (decision recorded in WO-P1-049).
- User-gated items: Worker-3 tunnel creation (OpenAI Platform web UI, like the prepared wastewater instance) and flipping the supervised default.
- Known flake: one real-process owned_process test can exceed its 5s deadline under heavy load; passes in isolation/rerun.

## Safety state

- No real Serena/tunnel/PID mutation tonight; test targets were short-lived real Python children in temp dirs.
- Infrastructure from 2026-08-21: wastewater instance prepared (`C:\AI\serena-instances\wastewater`, port 18013, watchdog + desktop shortcut) awaiting user tunnel creation + configure + start.

## Next safe action

Read CURRENT-WORK.md "Next safe action", confirm the milestone with the user, open a new work order + reuse gate before implementation.
