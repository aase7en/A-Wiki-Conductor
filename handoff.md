# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current objective

Model reusable Serena worker resources separately from dynamic Project/worktree assignment before any real process supervision.

## Current task

`WO-P1-004 — Serena Worker Runtime Profile Model`

Status: `IN_PROGRESS`

## Completed

- C1 contracts/schemas complete.
- Local Git safety baseline complete.
- Typed core domain complete, test-first, commit `dbf5b34`.
- Serena runtime-manager contract complete, commit `2b2ecbd`.
- Pure runtime safety classifiers complete; full suite `41 passed`, commit `676a881`.
- WO-P1-004 opened/claimed.

## Current repository state

- branch: `main`
- HEAD before WO-P1-004 coordination commit: `676a881`
- no Git remote
- exact per-command safe-directory override required; global Git config unchanged.

## DECISION_REQUIRED

`DR-C1-001`: GitHub visibility/public-safety before remote creation. Recommended private-first.

## Do not do

- No process/tunnel/Serena start/stop.
- No filesystem/network/subprocess logic in WO-P1-004.
- No real secret/tunnel credential values.
- No A-Wiki/Phase6 mutation.
- No remote/push.

## Next safe action

Commit WO-P1-004 coordination checkpoint, then write failing tests for stable worker config vs dynamic project binding.

## Resume instructions

Read `AGENTS.md` -> `PROJECT-PLAN.md` -> `COLLAB.md` -> `CURRENT-WORK.md` -> this file -> active WO. Reconcile Git/work-order/claim state before mutation.
