# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Resilient Execution Supervisor MVP**

## Active work order

`WO-AC-RES-003 — Transport-Loss State & Lease Preservation`

Status: `IN_PROGRESS`

## Goal

Persist transport loss/degradation/recovery independently from process/result state while preserving the existing durable job worker claim.

## Baseline

- AC-RES-001 durable execution records: `0a3040d`
- AC-RES-002 supervised subprocess: `03a623d`
- active Conductor listener PID `25396` must not be touched

## Boundary

- reuse durable job worker claim; no second lease table
- transport changes only `TransportState`
- duplicate same-state signal is idempotent
- ownership mismatch blocks mutation; no automatic reassignment/release
- no actual reconnect/retry loop in this slice

## Next safe action

Write RED tests integrating real SQLite job + execution stores for `LOST` while execution remains RUNNING and job remains CLAIMED by the same worker.
