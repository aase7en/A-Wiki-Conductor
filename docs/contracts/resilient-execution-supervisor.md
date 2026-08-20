# Resilient Execution Supervisor Contract

Status: binding architecture requirement
Source: real Serena/MCP session-loss evidence from A-Wiki Phase 6

## Purpose

A-Conductor must supervise substantial executions independently from the transport session used to request or observe them.

The core invariant is:

> **TRANSPORT FAILURE != EXECUTION FAILURE**

A Serena/MCP/agent connection can disappear while the underlying process is still running or has already completed. Therefore transport state and execution state are separate dimensions and must never be collapsed into one boolean/status.

## Responsibility boundary

- **A-Wiki** owns durable knowledge, policy, architecture decisions, work-order/claim conventions, cross-project memory and orchestration intelligence.
- **A-Conductor** owns operational execution identity, scheduling/routing enforcement, process supervision, durable runtime state, checkpoints, evidence, recovery and operator surfaces.
- **Serena/Codex/local shell/future workers** are execution backends/hands. Their transport/session is not the source of truth for execution completion.

This contract extends the existing durable-job/native-execution foundation. It does not authorize a second task engine, planner, work-order system or model router.

## Required model separation

### Transport health

At minimum:
- `CONNECTED`
- `DEGRADED`
- `LOST`
- `UNAVAILABLE`

### Execution process/result

At minimum:
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

`LOST` transport must never automatically transition execution to `FAILED`.

## Durable execution identity

Every substantial supervised execution receives a stable `execution_id` independent of chat/MCP session IDs.

Durable metadata should include, where applicable:
- execution/job/task/work-order identifiers;
- executor/backend kind;
- project/repo root;
- branch and HEAD-before identity;
- allowlisted operation/command fingerprint and bounded summary;
- start/finish timestamps;
- process PID/ownership evidence;
- run/report/stdout/stderr paths or opaque refs;
- exit code/result classification;
- evidence refs/checkpoint refs;
- transport-loss/reconnect evidence.

Do not persist raw prompts, transcripts, credentials or arbitrary secret-bearing environment values as execution metadata.

## Supervised command policy

Do not detach every operation. Classify suitable work as bounded synchronous vs supervised based on command category, known/historical duration, expected output volume, durability impact and transport-timeout risk.

For supervised executions:
1. allocate durable execution ID/run directory;
2. persist intent/fingerprint/identity preconditions;
3. launch exact owned process;
4. persist PID and durable log/report paths;
5. return control without depending on one long MCP call;
6. inspect/poll through separate operations;
7. collect and verify result when complete.

## Never blind retry

Before rerunning an interrupted substantial operation, classify the previous execution as one of:
- never started;
- still running;
- completed with valid evidence;
- partially completed;
- unknown provenance/state.

Default when uncertain: **do not retry**.

Particularly sensitive operations include tests/full suites, generators, formatters, migrations, Git mutations, deployments and other durable-state mutations.

## Fingerprint and duplicate protection

A stable fingerprint should cover relevant execution identity such as:
- repo/project identity;
- branch/HEAD or required precondition snapshot;
- job/task/work-order scope;
- normalized allowlisted operation/command shape;
- relevant runtime/profile identity.

If an equivalent execution is already alive, attach/monitor rather than spawn another. Completed evidence may be reused only when its identity/preconditions remain valid.

## Durable reports and output backpressure

Medium/long executions should write full raw output to a per-execution local run directory, conceptually:

```text
.a-conductor/runs/<execution-id>/
  metadata.json
  stdout.log
  stderr.log
  result.json
  reports/...
```

Transport responses should be bounded summaries/tails/failure slices, not unbounded raw logs. Machine-readable reports are preferred where available.

## Recovery after executor/transport loss

Recovery sequence:
1. mark transport lost/degraded without releasing ownership;
2. preserve execution/job ownership lease;
3. reconnect/reinitialize backend when safe and supported;
4. re-verify worker/project/repo root/branch/HEAD/dirty state/claim authority;
5. inspect original PID/process ownership;
6. inspect durable result/report/log evidence;
7. classify execution state;
8. only then choose collect/resume/retry/block/handoff;
9. continue from the exact next safe micro-step.

If automatic backend recovery is impossible, surface one precise `ACTION_REQUIRED` to the human and continue reconciliation after the backend returns.

## Ownership lease

Transport loss does not release the execution/job/file claim. Ownership may be released only after explicit cancellation, verified completion, controlled handoff, or a verified expiry/reconciliation policy proving no old mutation process is alive.

## Backend-neutral recovery port

The architecture should support a narrow backend lifecycle equivalent to:
- launch;
- inspect;
- collect;
- reconnect/reinitialize;
- cancel when explicitly authorized.

Reuse existing A-Conductor ports/components where possible; do not force a broad abstraction rewrite solely to match these method names.

## Retry and health policy

Transport reconnect may use a small bounded configurable retry/backoff policy. Underlying command retries are forbidden until execution state is classified.

Repeated transport failures should contribute to a simple durable backend health classification such as `CONNECTED`, `DEGRADED`, `UNAVAILABLE`, with minimal evidence: last success, recent failure/reconnect count and operation-duration/output correlation where useful.

No infinite retry loop.

## Fault-injection acceptance

A local fake backend must deterministically cover:
- disconnect before launch;
- disconnect after launch;
- disconnect mid-command;
- disconnect after process completion but before result delivery;
- delayed execution;
- large stdout/stderr;
- nonzero exit;
- malformed backend response;
- duplicate execution request while original remains alive;
- reconnect to wrong project/repo identity.

The feature is not complete if reliability exists only as documentation or if testing requires intentionally breaking real Serena.

## MVP implementation order

1. `AC-RES-001` Durable execution record
2. `AC-RES-002` Supervised subprocess launch/inspect/collect
3. `AC-RES-003` Transport-loss state separation
4. `AC-RES-004` Recovery reconciliation and identity gate
5. `AC-RES-005` Duplicate-execution protection
6. `AC-RES-006` Output backpressure/durable reports
7. `AC-RES-007` Fake backend + fault injection
8. `AC-RES-008` Serena adapter integration

Advanced automatic backend failover/routing comes only after these primitives are stable.
