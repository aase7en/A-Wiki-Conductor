# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current objective

Continue Phase 1 from a clean owned-process safety boundary into Serena-specific runtime profile/lifecycle composition without touching active workers.

## Current task

No active work order. `WO-P1-016 — Windows Owned-Process Controller` is completed and awaiting the close commit.

## Completed

- Contracts/local Git/runtime safety/read-only layers complete.
- Registry + SQLite persistence complete.
- Lifecycle planner/executor/journal/recovery stack complete.
- Stage A self-owned dummy runtime integration complete.
- Production Windows exact-owned process controller complete.
- P1-016 targeted tests: 16 passed.
- Full suite: 250 passed.
- Broad-kill/static safety review passed.
- Atomic preservation run proved active Conductor PID 25396 unchanged across the P1-016 integration run.

## Current repository state

- branch: `main`
- HEAD before P1-016 close commit: `b0f8762`
- no Git remote
- exact per-command safe-directory override required; global Git config unchanged.

## GitHub state

The user explicitly requested `@GitHub`. Connector calls were attempted but the platform returned `FORBIDDEN: This conversation is restricted to developer MCPs`. Local `git remote -v` is empty. No GitHub write/push was attempted.

## DECISION_REQUIRED

`DR-C1-001`: GitHub publication destination/visibility unresolved; private-first remains recommended.

`DR-P1-002`: first live Serena/tunnel lifecycle integration must use a dedicated isolated worker and must not target the active Sunday-Conducter or Phase6 worker.

## Do not do

- No broad process termination or `shell=True`.
- No active Conductor/Phase6 process targeting.
- No blind stale-PID cleanup.
- No reuse of a health port/profile already owned by another worker.
- No mutation of `serena-test`; use it read-only for identity checks only.
- No Git remote/push until publication decision is resolved.

## Next safe action

1. Commit the P1-016 close checkpoint.
2. Open/claim `WO-P1-017` for Serena runtime profile rendering + lifecycle backend composition.
3. Start with pure/fake/dummy tests; preserve `DR-P1-002` until a dedicated A-Worker 3 Stage B preflight is complete.

## Resume instructions

Read `AGENTS.md` -> `PROJECT-PLAN.md` -> `COLLAB.md` -> `CURRENT-WORK.md` -> this file -> active WO. Verify Git HEAD/status before mutation.
