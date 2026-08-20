# A-Conductor Durable Job Execution Contract

Status: Phase 1 binding contract
Work order: `WO-P1-035`
A-Wiki classification: `EXTEND`

## Purpose

Coordinate one explicitly invoked bounded execution operation against an already-gated durable job. A-Wiki remains authoritative for planning, orchestration policy, work-order content, and model/provider routing decisions. This coordinator owns only the runtime transaction boundary around one execution attempt.

## Preconditions

A bounded execution may begin only when:

- durable job exists
- caller supplies exact `expected_version`
- job state is `GATING`
- job has a non-blank claimed `worker_id`
- caller worker ID exactly matches the durable claim
- attempt budget allows entering `EXECUTING`

If any precondition fails, the backend must not be invoked.

## Backend boundary

The coordinator receives an injected `JobExecutionBackend` exposing one bounded method:

```text
execute(operation_ref, worker_id) -> JobBackendResult
```

`operation_ref` is ephemeral/opaque to the coordinator. It is not stored in the job record. Only bounded checkpoint metadata and evidence references may be persisted.

A backend result contains:

- `success`
- optional opaque `evidence_ref`
- on failure, required `RecoveryClassification`

Successful results require evidence. Failed results require an explicit recovery classification.

## Success transaction

```text
GATING
  -> EXECUTING        durable transition; attempt_count increments
  -> backend execute  external bounded operation
  -> CHECKPOINT       opaque completion checkpoint + evidence ref
  -> VERIFYING        durable transition
```

The coordinator does not mark a job COMPLETE. Verification/review remains a separate phase.

## Failure transaction

Expected backend failure:

```text
GATING -> EXECUTING -> backend failure -> RECOVERY_NEEDED(classification)
```

Unexpected backend exception:

```text
GATING -> EXECUTING -> exception -> RECOVERY_NEEDED(UNKNOWN)
```

Raw exception text is never persisted or surfaced through the durable result. Only code-level failure semantics may escape the coordinator.

## Persistence uncertainty

If the backend has already been invoked and a later durable checkpoint/transition fails, the coordinator must report `recovery_required=True` and must not claim completion. The latest durable state remains evidence for later reconciliation.

## Explicitly deferred

- automatic retry loops
- scheduler/background workers
- worker selection
- model/provider routing
- operation-ref resolution to concrete native adapters
- verification/review coordinator
- Discord transport
