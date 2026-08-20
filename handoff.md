# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current objective

Implement the reusable A-Worker/Project registry that will back the Control Center before introducing process lifecycle mutation or persistence.

## Current task

`WO-P1-008 — Reusable Worker Pool + Project Registry`

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
- Strict concrete read-only Windows I/O complete, full suite `134 passed`, commit `e0682cc`.
- Live read-only Conductor smoke observed PID VALID, process OWNED, port OWNED, ready HTTP 200 without mutation.
- WO-P1-008 opened/claimed; reuse classification is `NEW` only at A-Conductor runtime-control layer and does not replace A-Wiki claims.

## Current repository state

- branch: `main`
- HEAD before WO-P1-008 coordination commit: `e0682cc`
- no Git remote
- exact per-command safe-directory override required; global Git config unchanged.

## Environment note

Use ignored local pytest basetemp: ensure `runtime/` exists, then `python -m pytest tests -q --basetemp=runtime/pytest-temp`.

## DECISION_REQUIRED

`DR-C1-001`: GitHub visibility/public-safety before remote creation. Recommended private-first.

## Do not do

- No runtime/process/tunnel lifecycle mutation.
- No filesystem/Git/network/SQLite behavior in WO-P1-008.
- Do not duplicate A-Wiki claim/work-order implementation.
- No A-Wiki/Phase6 mutation.
- No remote/push.

## Next safe action

Commit WO-P1-008 coordination checkpoint, then write failing worker/project registry tests before implementation.

## Resume instructions

Read `AGENTS.md` -> `PROJECT-PLAN.md` -> `COLLAB.md` -> `CURRENT-WORK.md` -> this file -> active WO. Reconcile Git/work-order/claim state before mutation.
