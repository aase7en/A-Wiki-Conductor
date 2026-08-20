# A-Conductor Durable Job State Contract

Status: Phase 1 binding contract
Work order: `WO-P1-034`
A-Wiki classification: `WRAP + EXTEND`

## Purpose

A-Wiki remains the owner of work-order content, planning knowledge, handoff conventions, and orchestration policy. A-Conductor stores only the durable operational state required to execute and resume an A-Wiki work order across workers, sessions, and execution surfaces.

The durable job store is not a planner and does not persist prompts, transcripts, raw commands, stdout, stderr, or task-decomposition payloads.

## Job record

A durable job contains only:

- `job_id`
- opaque `work_order_ref`
- `project_id`
- `TaskState`
- optional current/last `worker_id`
- `attempt_count`
- `max_attempts`
- optional `RecoveryClassification`
- optimistic `version`
- timestamps

Creation starts at `NEW`, `attempt_count=0`, `version=1`.

## Transition policy

Allowed normal transitions:

```text
NEW -> PLANNING | READY | BLOCKED | CANCELLED
PLANNING -> READY | BLOCKED | FAILED | CANCELLED
READY -> CLAIMED | BLOCKED | CANCELLED
CLAIMED -> GATING | READY | BLOCKED | CANCELLED
GATING -> EXECUTING | BLOCKED | RECOVERY_NEEDED | FAILED | CANCELLED
EXECUTING -> VERIFYING | RECOVERY_NEEDED | FAILED | CANCELLED
VERIFYING -> REVIEW_PENDING | CHANGES_REQUIRED | COMPLETE | RECOVERY_NEEDED | FAILED
REVIEW_PENDING -> COMPLETE | CHANGES_REQUIRED | BLOCKED | FAILED
CHANGES_REQUIRED -> REPAIRING | CANCELLED
REPAIRING -> VERIFYING | RECOVERY_NEEDED | FAILED | CANCELLED
BLOCKED -> READY | FAILED | CANCELLED
```

`COMPLETE`, `FAILED`, and `CANCELLED` are terminal.

### Claim semantics

Entering `CLAIMED` requires a non-blank `worker_id`. Operational states preserve the worker claim unless the policy explicitly releases it. Returning to `READY` or entering `BLOCKED`/terminal states clears the active worker claim.

### Attempt budget

Entering `EXECUTING` increments `attempt_count`. The transition is refused with `ATTEMPT_BUDGET_EXHAUSTED` when the increment would exceed `max_attempts`.

### Recovery semantics

Entering `RECOVERY_NEEDED` requires an explicit `RecoveryClassification`.

Resume is classification-specific and intentionally conservative:

```text
NO_MUTATION                    -> READY
PARTIAL_MUTATION               -> GATING
MUTATION_COMPLETE_UNVERIFIED   -> VERIFYING
COMPLETE_VERIFIED              -> REVIEW_PENDING
UNEXPECTED_DRIFT               -> BLOCKED
UNKNOWN                        -> BLOCKED
```

A recovery transition to any other state is refused. Leaving `RECOVERY_NEEDED` clears the recovery classification.

## Optimistic concurrency

Every mutation of an existing job requires the caller's `expected_version`.

- exact match: mutation may proceed and increments version by one
- mismatch: refuse with `JOB_VERSION_CONFLICT`

The version check and mutation/event append occur in one SQLite `BEGIN IMMEDIATE` transaction.

## Events and checkpoints

Job events are append-only and sequence-numbered per job. Events contain metadata only:

- event ID
- job ID
- sequence number
- event type (`CREATED`, `TRANSITION`, `CHECKPOINT`)
- optional from/to state
- optional worker ID
- optional recovery classification
- optional opaque checkpoint reference
- optional evidence reference
- recorded timestamp

No payload/text/blob column is permitted for prompt, transcript, command, stdout, stderr, or model response content.

`checkpoint()` is refused for terminal jobs and requires the current `expected_version`; successful checkpointing increments the job version.

## Persistence boundaries

The SQLite job tables use an isolated `job_*` namespace so they can coexist with registry, lifecycle journal, Serena config, and event-log tables in the same database.

The store performs no process, filesystem-project, Git, network, worker lifecycle, LLM, or scheduling action.

## Explicitly deferred

- background scheduler
- automatic worker routing
- model/provider routing
- A-Wiki planning/decomposition
- prompt/message persistence
- Discord transport
- remote coordination backend
