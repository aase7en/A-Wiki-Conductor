# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current objective

Persist the reusable Project/A-Worker registry with local SQLite so Control Center assignments survive restart, while keeping the later task broker out of scope.

## Current task

`WO-P1-009 — SQLite Registry Persistence`

Status: `IN_PROGRESS`

## Completed

- C1 contracts/schemas complete.
- Local Git safety baseline complete.
- Typed core domain complete, commit `dbf5b34`.
- Serena runtime-manager contract complete, commit `2b2ecbd`.
- Pure runtime safety classifiers complete, commit `676a881`.
- Reusable Serena worker profile/project binding complete, commit `4e36681`.
- Read-only Windows observer complete, commit `af1979e`.
- Normalized worker status evaluator complete, commit `26ea225`.
- Strict concrete read-only Windows I/O complete, commit `e0682cc`.
- Reusable in-memory worker/project registry complete; full suite `150 passed`, commit `61db9af`.
- WO-P1-009 opened/claimed.

## Current repository state

- branch: `main`
- HEAD before WO-P1-009 coordination commit: `61db9af`
- no Git remote
- exact per-command safe-directory override required; global Git config unchanged.

## Environment note

Use ignored local pytest basetemp: ensure `runtime/` exists, then `python -m pytest tests -q --basetemp=runtime/pytest-temp`.

## DECISION_REQUIRED

`DR-C1-001`: GitHub visibility/public-safety before remote creation. Recommended private-first.

## Do not do

- No task broker tables/logic in WO-P1-009.
- No process/tunnel/Serena lifecycle mutation.
- No network/UI/provider behavior.
- No credentials/secrets.
- No A-Wiki/Phase6 mutation.
- No remote/push.

## Next safe action

Commit WO-P1-009 coordination checkpoint, then write failing SQLite registry persistence tests before implementation.

## Resume instructions

Read `AGENTS.md` -> `PROJECT-PLAN.md` -> `COLLAB.md` -> `CURRENT-WORK.md` -> this file -> active WO. Reconcile Git/work-order/claim state before mutation.
