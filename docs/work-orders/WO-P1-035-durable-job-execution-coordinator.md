# WO-P1-035: Durable Job Execution Coordinator

Status: in_progress
Lane/files: `src/a_conductor/job_execution.py`, `src/a_conductor/__init__.py`, `tests/test_job_execution.py`, `docs/contracts/durable-job-execution.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-035-durable-job-execution-coordinator.md`
Branch: main
Model tier: high

## Goal

Bind an explicitly invoked, already-gated durable job to an injected bounded execution backend. Persist only job transitions/checkpoint/evidence refs; never persist operation payloads or raw backend errors.

## A-Wiki classification

`EXTEND`: A-Wiki remains planner/orchestrator/policy source. A-Conductor coordinates the durable runtime transaction around one explicitly requested bounded execution operation.

## Acceptance

- Coordinator requires job state `GATING` and exact claimed worker ID before backend execution.
- Caller supplies `expected_version`; stale calls do not invoke backend.
- Before backend invocation: durable transition `GATING -> EXECUTING` succeeds and increments attempt budget.
- Successful backend result requires an opaque evidence ref; coordinator checkpoints completion metadata then transitions `EXECUTING -> VERIFYING`.
- Failed backend result requires explicit `RecoveryClassification`; coordinator transitions `EXECUTING -> RECOVERY_NEEDED` with evidence ref when present.
- Unexpected backend exception is reduced to code-only `UNKNOWN` recovery; raw exception text is never persisted.
- If persistence fails after backend invocation, coordinator returns/raises `recovery_required=True`; it does not pretend completion.
- Retry-budget failure happens before backend invocation.
- No scheduler/thread/background loop.
- No planner/router/model selection.
- No process/Git/filesystem implementation in coordinator; backend is injected.
- Full suite + compileall + diff/static safety gates pass.

## Forbidden

- No raw command/stdout/stderr/prompt/transcript/model response persistence.
- No automatic retry loop.
- No automatic worker routing.
- No A-Wiki mutation.
- No GitHub remote/network operation.

## Verify

- `python -m pytest tests/test_job_execution.py -q`
- `python -m pytest -q`
- `python -m compileall -q src`
- `git diff --check`

## Checkpoint log

- [2026-08-20] Opened from clean durable-job-store baseline `9382442`.
- [2026-08-20] Contract defined; local claim opened from baseline `9382442`.
