# WO-AC-RES-003: Transport-Loss State & Lease Preservation

Status: completed
Lane/files: `src/a_conductor/transport_recovery.py`, `src/a_conductor/__init__.py`, `tests/test_transport_recovery.py`, `docs/contracts/transport-loss-lease.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-AC-RES-003-transport-loss-lease.md`
Branch: main
Model tier: high

## Goal

Make transport loss an explicit durable execution condition that never implies execution failure or ownership release. Preserve the A-Conductor durable job claim/worker ownership while the transport is lost.

## Reuse classification

`WRAP + EXTEND`: reuse AC-RES-001 `TransportState` + execution events and the existing durable job claim (`JobRuntimeState.worker_id`). Do not create a second claim/lease system.

## Acceptance

- `mark_lost/degraded/connected/unavailable` mutate transport state only.
- Job state and job worker claim remain unchanged across transport loss/recovery signals.
- Execution process/result state remains unchanged across transport mutations.
- Mutations validate that execution worker and current durable-job worker still match before writing.
- Repeating the same transport state is idempotent: no version/event churn.
- Transport-loss evidence is an opaque bounded ref; no raw HTTP/body/error text persistence.
- Service exposes no release/retry/relaunch/reconnect-loop behavior.
- Targeted tests + compileall/diff pass.

## Forbidden

- No transition to execution FAILED on transport loss.
- No job state transition or claim release.
- No automatic subprocess retry.
- No reconnect loop/backoff implementation yet.
- No Serena-specific transport code.
- No A-Wiki/Phase6 mutation.

## Verify

- `python -m pytest tests/test_transport_recovery.py tests/test_execution_store.py tests/test_job_store.py -q`
- compileall
- diff check
- PID 25396 unchanged

## Checkpoint log

- [2026-08-20] Opened from clean AC-RES-002 completion `03a623d`.

- [2026-08-20] RED gate confirmed missing transport recovery module before implementation.
- [2026-08-20] Targeted transport recovery tests: 10 passed, including idempotent duplicate loss, ownership mismatch blocking, and shared SQLite job/execution claim preservation.
- [2026-08-20] Full-suite rerun intentionally deferred pending separate Python/Tcl-Tk environment remediation; AC-RES-003 acceptance relies on targeted store regression + compile/diff gates.
