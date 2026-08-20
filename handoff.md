# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current objective

Implement AC-RES-006 output backpressure so large supervised logs remain durable locally while transport responses stay bounded.

## Current task

`WO-AC-RES-006 — Output Backpressure + Durable Reports`

Status: `IN_PROGRESS`

## Baseline

- branch `main`
- AC-RES-005 completion `a0a2e52`
- focused regression through AC-RES-005: 70 passed
- active Conductor listener remains PID `25396`

## Design boundary

- read only durable stdout/stderr/report refs already created by AC-RES-002
- enum artifact selection only; no arbitrary caller path
- repo/run-dir confinement and symlink escape checks
- max 64 KiB returned bytes per call
- tail/chunk/full-digest metadata + bounded pytest summary
- no process/log mutation/network transport

## Context rollover rule

If chat context becomes crowded, checkpoint repository continuity first and only then recommend a new session. New sessions resume from repository artifacts without copied chat history.

## Next safe action

Write RED artifact-reader tests, then implement the smallest read-only bounded artifact service.
