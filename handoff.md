# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current objective

Connect the completed durable job transaction layer to fixed native execution primitives through opaque allowlisted operation IDs, while keeping A-Wiki authoritative for planning/orchestration.

## Current task

`WO-P1-036 — Allowlisted Native Operation Registry + Backend`

Status: `IN_PROGRESS`

## Baseline

- durable execution coordinator commit: `0de7365`
- P1-035 full suite: 502 passed, 1 Tk environment skip
- active Conductor listener: PID `25396`

## Boundary

- five enum-backed initial operations only: Git status/working diff/cached diff, pytest, compileall
- no arbitrary argv/executable/shell string
- output remains ephemeral; durable evidence uses digest refs only
- no Git mutation/filesystem mutation/scheduler/router/model selection

## Next safe action

Commit P1-036 coordination/contract checkpoint, then write RED registry/backend and end-to-end durable evidence tests.
