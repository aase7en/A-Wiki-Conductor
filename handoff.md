# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current objective

Implement AC-RES-004 recovery reconciliation so transport reconnection never causes blind retry and repository mutation cannot resume under mismatched identity.

## Current task

`WO-AC-RES-004 — Recovery Reconciliation + Repo Identity Gate`

Status: `IN_PROGRESS`

## Baseline

- branch: `main`
- AC-RES-003 completion: `f9838a5`
- AC-RES-002 real Windows supervised smoke passed
- active Conductor listener remains PID `25396`

## Reuse

- `SupervisedExecutionService.inspect/collect`
- `TransportRecoveryService`
- `StrictReadOnlyGitRunner`
- `NativeGitReadAdapter.status_short()`
- durable execution/job stores

## Project rule

Before recommending a new chat/session because context is crowded, checkpoint active WO, HEAD/worktree, evidence, blocker/decision, exact next safe action, and forbidden/ownership constraints in repo continuity files. A new session must resume from repo state without requiring copied chat history.

## Next safe action

Write RED AC-RES-004 tests. Reconciliation may monitor/collect/block but must never relaunch, retry, reset, clean, checkout, release the claim, or perform Serena-specific reconnect logic.
