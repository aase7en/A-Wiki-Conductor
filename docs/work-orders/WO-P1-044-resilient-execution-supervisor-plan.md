# WO-P1-044: Resilient Execution Supervisor Architecture Capture

Status: planning_complete
Lane/files: `PROJECT-PLAN.md`, `docs/contracts/resilient-execution-supervisor.md`, `docs/work-orders/WO-P1-044-resilient-execution-supervisor-plan.md`, `COLLAB.md`
Branch: main
Model tier: high

## Goal

Capture the real Phase 6 Serena/MCP failure evidence as a binding A-Conductor resilience requirement without modifying A-Wiki or Phase 6 and without creating a second execution/task engine.

Core invariant:

> TRANSPORT FAILURE != EXECUTION FAILURE.

A-Conductor must preserve execution identity and evidence independently from any Serena/MCP/chat transport session. It must never blind-retry an interrupted substantial operation until the original execution has been classified.

## FIT ANALYSIS

### Existing components to reuse/extend

- `src/a_conductor/job_state.py` + `job_store.py`: durable runtime job state, optimistic versions, checkpoints/evidence, recovery classification.
- `src/a_conductor/job_execution.py`: durable execution coordinator and backend result/recovery boundary.
- `src/a_conductor/native_execution.py`: bounded subprocess execution, durable digest metadata, output limits.
- `src/a_conductor/owned_process.py`: exact owned PID/process lifecycle primitives.
- `src/a_conductor/lifecycle_journal.py` + `lifecycle_recovery.py`: checkpoint/reconciliation pattern.
- `src/a_conductor/worker_status.py`: explicit worker/runtime health classification.
- `src/a_conductor/native_operations.py` + operator protocol stack: allowlisted operation identity and transport-neutral command boundary.
- Existing A-Wiki work-order/claim/handoff conventions: semantic/micro-step continuity; do not duplicate them.

### Architecture gaps

1. No durable per-execution record distinct from job/task state.
2. No explicit transport-health state distinct from execution-process state.
3. Long native operations are still primarily synchronous; no supervised detach/inspect/collect lifecycle.
4. No command fingerprint/deduplication registry for substantial executions.
5. No reconciliation engine that combines PID/report/repo identity after transport loss.
6. No durable run-directory/report convention with bounded response/backpressure.
7. No execution ownership lease that survives transport loss.
8. No fake backend/fault-injection harness for disconnect timing cases.
9. No executor health/degradation record for repeated 502/reconnect patterns.
10. No Serena-specific recovery adapter built on a provider-neutral execution backend contract.

### Duplicate-work risk

High if implemented as a new scheduler/task engine. The correct classification is `EXTEND + WRAP` of the existing durable job/native execution/lifecycle recovery foundation.

Do NOT create:
- a second job state machine,
- another work-order/TODO system,
- a competing planner/router,
- Serena-only recovery semantics,
- automatic retry hidden inside the transport adapter.

## PROPOSED MICRO-STEPS

### AC-RES-001 — Durable execution record

Add stable `execution_id` and durable metadata/state separate from the higher-level job. Persist identifiers, repo identity snapshot, executor kind, operation fingerprint, PID/run paths, bounded result metadata and timestamps. Do not persist raw prompt/transcript.

### AC-RES-002 — Supervised subprocess

Add launch/inspect/collect for suitable medium/long native operations. Persist PID and logs, return execution ID quickly, and keep small operations synchronous.

### AC-RES-003 — Transport-loss state model

Represent transport health separately from execution state. `TRANSPORT_LOST` never means `FAILED` by itself.

### AC-RES-004 — Recovery reconciliation

On reconnect/recovery, re-check project/repo/branch/HEAD/dirty state/claim ownership, inspect original PID and durable result/report, then classify before any retry or next mutation.

### AC-RES-005 — Duplicate-execution protection

Compute a stable operation fingerprint from repo identity + work/task/execution scope + normalized allowlisted operation + relevant runtime profile. Attach/monitor equivalent live execution; reuse completed evidence only when identity/evidence remains valid.

### AC-RES-006 — Output backpressure and durable reports

Use per-execution run directories and bounded summaries/tails. Store full raw output locally; transport only compact summaries/failure slices unless explicitly requested.

### AC-RES-007 — Fake executor + fault injection

Deterministically test disconnect before launch, immediately after launch, mid-command, after completion-before-delivery, large output, nonzero exit, malformed response, duplicate request, and wrong-repo reconnect.

### AC-RES-008 — Serena adapter integration

Only after provider-neutral supervisor/reconciliation passes deterministic tests. Map Serena/MCP transport loss/reconnect into the generic model; never make real Serena outages the test harness.

## Required MVP acceptance

A deterministic test must demonstrate:
1. supervised long command starts;
2. Serena-like transport disappears;
3. underlying process continues;
4. transport loss is recorded without marking execution failed;
5. reconnect/recovery checks identity and original process/report;
6. original result is collected;
7. no duplicate execution starts;
8. durable logs/evidence remain available;
9. workflow resumes at the exact next safe micro-step;
10. no human context reconstruction is required.

## Safety invariants

- Evidence beats inference.
- Never blind-retry substantial/durable-state operations.
- Never automatically release live ownership on temporary transport loss.
- Unknown process/result state becomes `RECOVERY_REQUIRED`, not guessed success/failure.
- Reconnect must repeat repo/project/branch/HEAD/dirty/claim identity gates before mutation.
- Retry transport only with bounded configurable policy; underlying command retry requires prior classification.
- Repeated executor instability may lead to `EXECUTOR_DEGRADED` and later controlled handoff, but only after confirming no old mutation process is alive.
- A-Wiki remains brain/policy/memory; A-Conductor owns operational execution supervision/recovery; workers remain execution hands.

## Decision required

None for architecture capture. Implementation ordering should begin only after the current P1-038 runtime-control work is reconciled/closed or a non-overlapping implementation claim is explicitly opened.

## Checkpoint log

- [2026-08-20] Requirement derived from repeated real Serena 502/session-terminated incidents during A-Wiki Phase 6, including cases where pytest continued and completed after transport failure.
- [2026-08-20] Fit classified `EXTEND + WRAP`; existing durable job/native execution/lifecycle recovery components are reusable and must remain authoritative.
