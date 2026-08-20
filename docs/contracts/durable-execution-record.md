# Durable Execution Record Contract

Status: AC-RES-001 binding contract
Parent: `docs/contracts/resilient-execution-supervisor.md`

## Purpose

Persist one substantial execution independently from its requesting/observing transport. This record is operational runtime state and does not replace A-Wiki work orders or A-Conductor durable job state.

## Two independent state dimensions

### TransportState
- `CONNECTED`
- `DEGRADED`
- `LOST`
- `UNAVAILABLE`

### ExecutionProcessState
- `QUEUED`
- `STARTING`
- `RUNNING`
- `PROCESS_STILL_RUNNING`
- `PROCESS_EXITED_UNKNOWN_RESULT`
- `SUCCEEDED`
- `FAILED`
- `PARTIAL`
- `CANCELLED`
- `RECOVERY_REQUIRED`
- `VERIFICATION_REQUIRED`

Changing transport state never changes execution process/result state implicitly.

## Immutable identity

After creation these fields do not change:
- execution_id
- job_id / work_order_ref / project_id / worker_id
- backend_id
- repo_root / branch / head_before
- operation_ref
- command_fingerprint
- bounded command_summary
- runtime_profile_ref
- run_dir_ref / stdout_ref / stderr_ref / result_ref / report_ref

These are identifiers/references and bounded summaries only. Raw prompt, transcript, credentials, arbitrary environment values, stdout and stderr are forbidden.

## Mutable runtime/result metadata

May change only through versioned mutations:
- transport_state
- execution_state
- pid
- exit_code
- started_at
- finished_at
- version

## Optimistic concurrency

All mutations require `expected_version`. Stale writers fail with `EXECUTION_VERSION_CONFLICT`. State/result update and append-only event insertion occur in the same SQLite transaction.

## Events

Append-only events record bounded metadata such as:
- created
- transport state changed
- execution state changed
- process metadata updated
- result metadata updated

Events may contain opaque evidence/checkpoint refs but never raw process output or secret-bearing content.

## Explicitly deferred

AC-RES-001 does not launch, inspect, collect, reconnect, retry, cancel or deduplicate processes. Those belong to AC-RES-002+.