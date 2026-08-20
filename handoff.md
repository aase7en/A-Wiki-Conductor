# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current objective

Design the safe staged integration-test path for the first concrete lifecycle mutation backend without provisioning or touching active runtime workers.

## Current task

`WO-P1-014 — Lifecycle Integration Test Strategy`

Status: `IN_PROGRESS`

## Completed

- C1 contracts/schemas complete.
- Local Git safety baseline complete.
- Typed/provider-neutral runtime foundation complete.
- Reusable Project/A-Worker registry + SQLite persistence complete.
- Pure lifecycle planner, transaction executor, durable journal, and resume planner complete.
- P1-013 recovery planner commit: `fcd3d61`; full suite 233 passed.
- `DR-P1-002` durable safety gate is recorded in `PROJECT-PLAN.md`.
- Initial read-only P1-014 preflight: candidate A-Worker 3 runtime root absent; candidate port 18013 had no listener; `A:/GitHub/serena-test` exists but is not yet approved as a mutation target.

## Current repository state

- branch: `main`
- HEAD before P1-014 coordination commit: `fcd3d61`
- no Git remote
- exact per-command safe-directory override required; global Git config unchanged.

## DECISION_REQUIRED

### DR-C1-001 — GitHub publication

Recommended private-first; no remote/push until resolved.

### DR-P1-002 — First live lifecycle integration target

No target is approved yet. WO-P1-014 will define a staged test strategy. Recommended architecture is Stage A self-owned dummy process first, then Stage B dedicated isolated `A-Worker 3` Serena/transport runtime. Active `Sunday-Conducter` and Phase6 are forbidden as first mutation targets.

## Do not do

- No process/tunnel/Serena lifecycle mutation in P1-014.
- No provisioning of A-Worker 3 or port/tunnel resources.
- No writes to `serena-test`, A-Wiki, Phase6, or external runtime roots.
- No remote/push.

## Next safe action

Commit P1-014 coordination state, then inspect `A:/GitHub/serena-test` repository identity/status read-only and write the integration-test strategy contract.

## Resume instructions

Read `AGENTS.md` -> `PROJECT-PLAN.md` -> `COLLAB.md` -> `CURRENT-WORK.md` -> this file -> active WO. Verify Git HEAD/status before mutation.
