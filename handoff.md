# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current objective

Compose Serena-specific lifecycle steps onto the already-built planner/executor/checkpoint and exact-owned process safety boundaries without introducing direct live Serena/tunnel mutation yet.

## Current task

`WO-P1-017 — Serena Lifecycle Backend Composition`

Status: `IN_PROGRESS`

## Completed

- Contracts/local Git/runtime safety/read-only layers complete.
- Registry + SQLite persistence complete.
- Lifecycle planner/executor/journal/recovery stack complete.
- Stage A dummy runtime integration complete.
- Exact-owned Windows process controller complete; commit `8c4cb8c`.
- Full suite at previous checkpoint: 250 passed.

## Current repository state

- branch: `main`
- HEAD before P1-017 coordination commit: `8c4cb8c`
- no Git remote
- exact safe-directory override remains required; global Git config unchanged.

## GitHub state

User requested `@GitHub`; connector access was attempted but platform returned `FORBIDDEN: This conversation is restricted to developer MCPs`. No GitHub mutation was performed.

## DECISION_REQUIRED

`DR-C1-001`: GitHub publication destination/visibility unresolved.

`DR-P1-002`: first live Serena/tunnel lifecycle integration must use a dedicated isolated worker, never Sunday-Conducter or Phase6.

## Do not do

- No direct live Serena/tunnel/A-Worker 3 mutation in WO-P1-017.
- No broad process termination or `shell=True`.
- No secret resolution/logging in the composition backend.
- No direct journal persistence from the backend.

## Next safe action

Claim/commit P1-017 coordination state, write failing backend mapping tests, then implement only the injected collaborator composition layer.

## Resume instructions

Read `AGENTS.md` -> `PROJECT-PLAN.md` -> `COLLAB.md` -> `CURRENT-WORK.md` -> this file -> active WO. Verify Git HEAD/status before mutation.
