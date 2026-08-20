# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current objective

Implement AC-RES-005 duplicate execution protection so repeated transport/session requests cannot silently spawn an equivalent long-running operation twice.

## Current task

`WO-AC-RES-005 — Duplicate Execution Protection`

Status: `IN_PROGRESS`

## Baseline

- branch `main`
- HEAD before coordination checkpoint: `bb5dab0`
- AC-RES-004: 59 focused/regression tests passed
- active Conductor listener remains PID `25396`

## Design boundary

- canonical in-memory SHA-256 fingerprint builder
- read-only newest-first SQLite fingerprint lookup
- exact durable identity recheck after hash match
- decisions only: `SAFE_TO_LAUNCH`, `ATTACH_RUNNING`, `REUSE_COMPLETED`, `BLOCKED_UNKNOWN`
- no launch/retry/failover/Git/filesystem/network mutation

## Context rollover rule

If chat context becomes crowded, checkpoint active WO/HEAD/worktree/evidence/next-safe-action/ownership constraints before recommending a new session. The new session resumes from repository continuity artifacts, not copied chat history.

## Next safe action

Write RED AC-RES-005 tests, then implement the smallest fingerprint/query/decision layer without touching AC-RES-002 process launch behavior.
