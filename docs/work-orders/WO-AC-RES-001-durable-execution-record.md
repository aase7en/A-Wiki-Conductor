# WO-AC-RES-001: Durable Execution Record

Status: in_progress
Lane/files: `src/a_conductor/execution_record.py`, `src/a_conductor/execution_store.py`, `src/a_conductor/__init__.py`, `tests/test_execution_record.py`, `tests/test_execution_store.py`, `docs/contracts/durable-execution-record.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-AC-RES-001-durable-execution-record.md`
Branch: main
Model tier: high

## Goal

Implement the first Resilient Execution Supervisor slice: durable execution identity and independent transport/execution state persistence. This is a per-execution runtime record underneath/alongside durable jobs, not a replacement task state machine.

## Reuse classification

`EXTEND + WRAP`: reuse existing durable-job persistence patterns, optimistic versioning, execution coordinator concepts, owned-process identity fields, lifecycle reconciliation conventions, and operator evidence discipline.

## Acceptance

- Stable execution ID is independent from chat/MCP/session IDs.
- Separate `TransportState` and `ExecutionProcessState` dimensions.
- Transport `LOST` never implies execution `FAILED`.
- Durable immutable launch identity stores opaque job/work-order/project/worker/backend/operation refs plus repo root, branch, HEAD-before, command fingerprint, bounded command summary, runtime profile ref, and run/log/result/report refs.
- No raw prompt/transcript/credential/environment/stdout/stderr persistence.
- Mutable result fields include PID, exit code, started/finished timestamps, execution state and transport state.
- Every mutation requires expected version and uses one SQLite transaction.
- Append-only execution events record state transitions/metadata refs without raw output.
- Store survives reopen.
- No process launch/inspect/collect/retry/reconnect/deduplication yet.
- Targeted tests + compileall + diff/schema safety gates pass.

## Forbidden

- No second job/work-order/task state machine.
- No subprocess launch.
- No blind retry.
- No transport reconnect loop.
- No Serena-specific logic.
- No raw command/env/output persistence.
- No A-Wiki or Phase6 repo mutation.

## Verify

- `python -m pytest tests/test_execution_record.py tests/test_execution_store.py -q`
- `python -m compileall -q src`
- `git diff --check`
- SQLite schema forbidden-column scan

## Checkpoint log

- [2026-08-20] Opened after P1-038 completed at `4f300ca`; resilient supervisor architecture baseline `c57bd2a`.
