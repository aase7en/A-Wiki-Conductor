# A-Conductor Durable Job Control Service Contract

Status: Phase 1 binding contract
Work order: `WO-P1-038`

## Purpose

Provide one bounded application-service facade over the completed durable job and native execution runtime so future operator surfaces do not need to understand SQLite tables, job transition internals, operation registries, or worker adapter assembly.

The service does not own a second state machine. Every durable mutation delegates to `SQLiteJobStore`; every bounded execution delegates to `DurableJobExecutionCoordinator`.

## Composition

`open(database_path, control_center, operations, ...)` composes:

```text
SQLiteJobStore
NativeOperationRegistry
ControlCenterNativeAdapterResolver (or injected resolver)
AllowlistedNativeJobBackend
DurableJobExecutionCoordinator
DurableJobControlService
```

Construction performs no native command, worker lifecycle, Git mutation, scheduling, or model call.

## Bounded API

Initial service operations:

- `create_job(...)`
- `get_job(job_id)`
- `list_events(job_id)`
- `mark_ready(job_id, expected_version)`
- `claim(job_id, expected_version, worker_id)`
- `gate(job_id, expected_version, worker_id)`
- `checkpoint(job_id, expected_version, checkpoint_ref, evidence_ref=None)`
- `execute_operation(job_id, expected_version, worker_id, operation_ref)`

There is intentionally no generic `transition(target_state)` surface in this application facade.

## Concurrency and authority

All mutations carry the caller's current `expected_version`; optimistic concurrency remains enforced by `SQLiteJobStore`.

Claim/gate/execute worker identity is explicit. Native execution authority comes from the current Control Center assignment through the native-adapter resolver at execution time.

## Persistence

The service adds no tables and writes no SQL directly. Job/work-order/evidence metadata persistence remains owned by `SQLiteJobStore`; raw native output remains ephemeral.

## Explicitly out of scope

- background scheduler
- automatic retries
- worker/model routing
- planning/decomposition
- Discord/Tk UI adapters
- generic command execution
- arbitrary state transition API
