# WO-P1-042: Transport-Neutral Operator Dispatcher

Status: completed
Lane/files: `src/a_conductor/operator_dispatch.py`, `tests/test_operator_dispatch.py`, `COLLAB.md`, `docs/work-orders/WO-P1-042-operator-dispatcher.md`
Branch: main
Model tier: high

## Goal

Dispatch validated `operator.v1` requests onto a structural durable-job-control interface and return bounded `OperatorResponse` metadata without importing or editing the dirty P1-038 implementation.

## Parallel-safety boundary

Additive-only. `WO-P1-038` remains the owner of `job_control.py`, `__init__.py`, `test_job_control.py`, `CURRENT-WORK.md`, and `handoff.md`.

## Acceptance

- Structural `Protocol` matches bounded job-control methods; no direct import of `job_control.py`.
- Every operator action maps to one explicit service method.
- No generic transition/run/command method exists.
- Service exceptions surface code-only; raw exception text is never returned.
- Execution outcome exposes bounded state/version/attempt/evidence metadata only.
- Job events are represented by capped opaque event/checkpoint/evidence refs, not payloads.
- Status is injected separately and may return `OPERATOR_STATUS_UNAVAILABLE` when no provider exists.
- Targeted tests + compileall + diff/static scan pass.
- Full suite deferred while independent Windows Python `0x80000003` investigation is active.

## Forbidden

- No SQL/network/Telegram/Discord/subprocess/planner/router.
- No direct P1-038 file edit/import.
- No generic action passthrough.

## Verify

- `python -m pytest tests/test_operator_protocol.py tests/test_operator_dispatch.py -q`
- `python -m compileall -q src`
- `git diff --check`

## Verification evidence

- RED: missing `a_conductor.operator_dispatch` module.
- Targeted dispatcher tests: 46 passed.
- Combined operator/Telegram protocol+mapper+renderer+dispatcher tests: 83 passed.
- `compileall`: PASS.
- `git diff --check`: PASS.
- Import scan: structural job state/event/outcome + operator protocol only; no concrete `job_control.py`, network, Telegram/Discord SDK, or subprocess import.
- Exception sanitizer returns code-only responses and drops raw exception text.
- Full-suite verification intentionally deferred while the independent Windows Python `0x80000003` investigation remains active.
- P1-038-owned files were not edited or staged by this work order.

## Checkpoint log

- [2026-08-20] Opened after Telegram mapper/renderer parallel commits while P1-038 remains targeted-green but full-suite blocked by Windows runtime crash investigation.
- [2026-08-20] Completed structural operator dispatcher with bounded response mapping and event-ref cap.
