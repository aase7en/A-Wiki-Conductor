# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Resilient Execution Supervisor MVP**

## Active work order

`WO-AC-RES-002 — Supervised Subprocess Launch / Inspect / Collect`

Status: `IN_PROGRESS`

## Goal

Reuse exact-owned-process primitives to run suitable commands independently from one transport request, with durable child PID/log/result evidence and no blind retry.

## Baseline

- P1-038 complete: `4f300ca`
- AC-RES-001 complete: `0a3040d`
- transport and execution states already persist independently
- active Conductor listener PID `25396` must not be touched

## Architecture choice

Reuse `WindowsOwnedProcessController` to own an internal A-Conductor supervisor helper. The helper carries `execution_id` as the ownership marker, launches the real target with `shell=False`, writes child PID/result JSON atomically, and inherits sanitized environment + durable log handles.

## Next safe action

Write RED tests for the helper's result contract and for launch/inspect/collect using injected fake process/controller components before any real subprocess smoke.
