# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current objective

Add safe Runtime Setup to the lifecycle-capable desktop shell, then close the local Phase 1 MVP around the external Worker 3 transport gate.

## Current task

`WO-P1-030 — Runtime Setup Service + Desktop Dialog`

Status: `IN_PROGRESS`

## Completed

- Local process-manager/runtime safety stack complete.
- Control Center service + desktop shell complete.
- Durable Serena config + lifecycle coordinator/assembly complete.
- Desktop Start/Stop/Restart wired through background lifecycle facade.
- Stage B external transport provisioning remains `DR-P1-003 / BLOCKED_EXTERNAL`.
- A-Wiki ↔ A-Conductor responsibility/integration contract established in `docs/contracts/a-wiki-a-conductor-integration.md`; A-Conductor remains a separate sibling repo.
- A-Wiki companion registration/master-work-order payload is prepared in `docs/contracts/a-wiki-companion-registration-payload.md` but is not yet applied to A-Wiki.

## Repository state

- branch: `main`
- no Git remote

## Next safe action

Resume P1-030 from the existing uncommitted implementation exactly as-is. Inspect the actual runtime/UI/test files first because prior patches were partially applied; fix the known Serena-config atomic-copy portability issue and desktop background-executor/setup-dialog wiring, then run targeted tests with a unique basetemp before the full suite. Do not apply the A-Wiki registration payload from this pinned Conductor project; use an authorized A-Wiki execution surface later.

## Resume instructions

Read `AGENTS.md` -> `PROJECT-PLAN.md` -> `COLLAB.md` -> `CURRENT-WORK.md` -> this file -> active WO; verify HEAD/status before mutation.
