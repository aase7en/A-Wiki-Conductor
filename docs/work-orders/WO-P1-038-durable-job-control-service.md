# WO-P1-038: Durable Job Control Service

Status: in_progress
Lane/files: `src/a_conductor/job_control.py`, `src/a_conductor/__init__.py`, `tests/test_job_control.py`, `docs/contracts/durable-job-control-service.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-038-durable-job-control-service.md`
Branch: main
Model tier: high

## Goal

Expose the durable job store + execution coordinator + allowlisted native backend through one small application-service API suitable for later Discord/Desktop adapters, without duplicating state policy or adding scheduling/routing.

## Acceptance

- `open()` composes SQLiteJobStore + NativeOperationRegistry + worker native-adapter resolver + AllowlistedNativeJobBackend + DurableJobExecutionCoordinator.
- Existing resolver can be injected for deterministic tests; default uses ControlCenterNativeAdapterResolver.
- Service exposes bounded create/get/events/ready/claim/gate/checkpoint/execute operations only.
- Every state mutation requires caller `expected_version` and delegates to SQLiteJobStore policy.
- `execute_operation` delegates to DurableJobExecutionCoordinator and does not inspect native output.
- Reopening service on the same database sees durable job state/events.
- No generic transition API, arbitrary command API, planner/router/scheduler/background loop.
- Full suite + compileall + diff/static safety gates pass.

## Forbidden

- No duplicate transition graph.
- No direct SQL outside SQLiteJobStore.
- No raw command/prompt/stdout/stderr persistence.
- No automatic retries or worker/model selection.
- No Discord/UI code yet.
- No A-Wiki/GitHub mutation.

## Verify

- `python -m pytest tests/test_job_control.py -q`
- `python -m pytest -q`
- `python -m compileall -q src`
- `git diff --check`

## Checkpoint log

- [2026-08-20] Opened from clean worker-native-adapter-assembly baseline `543b1ab`.
- [2026-08-20] Contract defined; local claim opened from baseline `543b1ab`.
