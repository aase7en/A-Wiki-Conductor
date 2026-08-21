# HANDOFF — A-Conductor

Last updated: 2026-08-21 (session 6, WO-P1-055 verified)

## Current objective

Phase 1 Second Brain + usability/onboarding polish is delivered. WO-P1-055 UI status/error polish is verified. Next work should enter Phase 2 through a fresh reuse-gated work order.

## Status

`COMPLETE` for WO-P1-055. Phase 2 backlog remains `NOT_STARTED`.

## Current repository state

- Project: `A-Wiki-Conductor`
- Worktree: `A:\GitHub\A-Wiki-Conductor`
- Branch during WO-P1-055: `chunk/p1-055-alive-status-themed-errors`
- Baseline HEAD before WO-P1-055 edits: `2a24c5b5e59c2453add53ad2e957c3616e1327c6`
- Pending WO-P1-055 files at handoff: `src/a_conductor/desktop_ui.py`, `tests/test_desktop_ui.py`, `docs/work-orders/WO-P1-055-alive-status-themed-errors.md`, `CURRENT-WORK.md`, `handoff.md`

## Completed

- WO-P1-052 Second Brain Phase 1 shipped.
- WO-P1-053 usability overhaul shipped.
- WO-P1-054 onboarding/Tunnel ID/AI connection guide shipped.
- WO-P1-055 completed: slow ONLINE pulse + themed Thai teaching error popup; cleanup of duplicate error logging, hard-coded pulse color, obsolete `messagebox` import, and stray debug marker.

## Evidence

- WO-P1-055 `git diff --check`: clean.
- Desktop UI targeted suite: **38 passed**.
- First full suite: 809 passed / 1 timing failure in `test_timeout_leaves_durable_running_execution_then_retry_attaches`; isolated rerun passed.
- Verification full suite: **810 passed**.
- 29 statically emitted `_handle_error("CODE")` values have explanation coverage.

## Known environment issue

Sunday-Conducter inherited stale PyInstaller `TCL_LIBRARY` and `TK_LIBRARY` values pointing to an expired `%LOCALAPPDATA%\Temp\_MEI...` directory. This made Tk tests skip and the default pytest temp cleanup had previously hit `WinError 5` on `pytest-current`.

Safe verification workaround used only for test commands:

- Python 3.13 at `C:\Users\aase7\AppData\Local\Programs\Python\Python313\python.exe`
- command-scoped `TCL_LIBRARY=...\Python313\tcl\tcl8.6`
- command-scoped `TK_LIBRARY=...\Python313\tcl\tk8.6`
- custom `--basetemp=%LOCALAPPDATA%\A-Conductor\...`

No machine-wide environment, live connector, worker, or tunnel configuration was changed.

## Do Not Do

- Do not treat the inherited `_MEI...` Tcl/Tk paths as valid persistent runtime configuration.
- Do not modify Serena core merely to expose Phase 2 UI behavior.
- Do not duplicate A-Wiki coordination/memory primitives; apply the reuse-before-build contract first.
- Do not redesign unrelated orchestration while implementing a bounded Phase 2 item.

## TODO

- Phase 2 reuse/backlog triage — `NOT_STARTED`
- MCP gateway enforcement — `NOT_STARTED`
- CONNECTORS rebind UI — `NOT_STARTED`
- onboarding warning when expected memory is absent — `NOT_STARTED`
- activation-prompt helper — `NOT_STARTED`
- rebuild/reinstall installed A-Conductor executable after the desired feature checkpoint — `NOT_STARTED`

## Next safe action

Read the Phase 2 section of `PROJECT-PLAN.md` plus `docs/contracts/a-wiki-a-conductor-integration.md`; classify the four backlog candidates as REUSE / WRAP / EXTEND / REPLACE / NEW, then open one bounded work order for the smallest deterministic item.
