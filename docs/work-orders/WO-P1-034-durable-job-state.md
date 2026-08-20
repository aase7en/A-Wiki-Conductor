# WO-P1-034: Durable Job State + Checkpoint Store

Status: in_progress
Lane/files: `src/a_conductor/job_state.py`, `src/a_conductor/job_store.py`, `src/a_conductor/__init__.py`, `tests/test_job_state.py`, `tests/test_job_store.py`, `docs/contracts/durable-job-state.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-034-durable-job-state.md`
Branch: main
Model tier: high

## Goal

Persist A-Conductor runtime job state around A-Wiki work-order references without implementing a competing planner. Provide validated state transitions, worker claims, bounded execution attempts, recovery classification, optimistic concurrency, and append-only checkpoint/evidence events.

## A-Wiki classification

`WRAP + EXTEND`: A-Wiki remains source of work-order/handoff/orchestration knowledge. A-Conductor stores operational runtime state needed to execute/resume those work orders across sessions/workers.

## Acceptance

- Pure transition policy over existing `TaskState`.
- SQLite job rows store identifiers/refs/state only; no raw prompt/task payload column.
- Append-only job events store transition/checkpoint metadata and evidence refs only.
- Every mutation uses expected job version; stale writers receive `JOB_VERSION_CONFLICT`.
- Claim transition requires worker ID.
- Entering EXECUTING increments attempt count and enforces max-attempt budget.
- RECOVERY_NEEDED requires explicit `RecoveryClassification` and can resume only through conservative allowed transitions.
- Terminal states cannot be mutated/checkpointed.
- Persistence survives store reopen.
- Full suite + compileall + diff/schema safety gates pass.

## Forbidden

- No LLM planning/decomposition/router implementation.
- No prompt/transcript/raw command/stdout/stderr payload persistence.
- No worker/process/Git mutation from the job store.
- No background scheduler yet.
- No A-Wiki repo mutation.

## Verify

- `python -m pytest tests/test_job_state.py tests/test_job_store.py -q`
- `python -m pytest -q`
- `python -m compileall -q src`
- `git diff --check`

## Checkpoint log

- [2026-08-20] Opened from clean Native Execution/Git foundation at `23443fe`.
- [2026-08-20] Reuse gate complete: `WRAP + EXTEND`; durable contract defined and local claim opened from baseline `23443fe`.
