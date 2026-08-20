# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current objective

Build deterministic fault injection for the Resilient Execution Supervisor without touching real Serena/tunnels.

## Current task

`WO-AC-RES-007 — Fake Executor + Fault Injection`

Status: `IN_PROGRESS`

## Baseline

- branch `main`
- AC-RES-006 completion `9cc3c46`
- focused regression through AC-RES-006: 80 passed
- active Conductor listener remains PID `25396`

## Boundary

The fake is test support only. It simulates lifecycle/output/result timing and implements supervised inspect/collect shape, while production transport/recovery/dedup/artifact logic remains authoritative.

## Context rollover rule

If context becomes crowded, checkpoint repository continuity before recommending a new session; new sessions resume from repository artifacts.

## Next safe action

Write RED deterministic scenario tests, implement the fake without threads/timers/network, then integrate it with AC-RES-003/004/005/006 in temp repositories.
