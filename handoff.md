# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current task

`WO-AC-RES-003 — Transport-Loss State & Lease Preservation`

Status: `IN_PROGRESS`

## Baseline

- branch: main
- baseline HEAD: `03a623d`
- active Conductor listener: PID `25396`

## Core invariant

`TRANSPORT LOST != EXECUTION FAILED` and temporary transport loss does not release the durable job worker claim.

## Next safe action

RED integration tests first. No network/Serena/reconnect implementation in this work order.
