# GE-0007 — Graph dispatch reuses durable job control, execution dedup, and recovery

Status: ACCEPTED — GPT-5.6 Sol MAX integrator decision, 2026-08-26
Date: 2026-08-26
Parent: `docs/work-orders/WO-GE-001-graph-engineering-kickoff.md`
Design evidence: `docs/work-orders/WO-GE-006-scheduler-dispatch-design.md`

## Context

GE-6 produces a bounded deterministic schedule plan but intentionally performs no durable job transition or external execution. GE-7 must connect a selected graph node/worker pair to the existing Conductor execution machinery.

The repository already has the required durable authority:

- `DurableJobControlService` — bounded application service for create/ready/claim/gate/checkpoint/execute;
- `SQLiteJobStore` — versioned durable state + event log with optimistic concurrency;
- `DurableJobExecutionCoordinator` — one caller-selected operation, attempt accounting, checkpoint, VERIFYING transition, and recovery classification;
- supervised command runner + execution record/store;
- canonical execution fingerprint / duplicate-execution guard;
- transport-recovery semantics where transport loss is not execution failure.

Creating a graph-specific job lifecycle, retry store, process runner, or dedup system would duplicate proven invariants and violate GE-0001 and the A-Wiki/A-Conductor reuse rules.

## Decision

### 1. Existing durable job control remains the execution authority

GE-7 is **REUSE + WRAP + EXTEND** of the existing job-control path.

A thin graph-dispatch adapter may translate a GE-6 assignment into durable job-control calls. `DurableJobControlService` may receive narrowly-scoped API extensions if atomicity or idempotent recovery requires them, but it remains the single owner of durable job lifecycle transitions.

GE-7 must not introduce:

- a second job state machine;
- a second attempt/retry counter;
- a graph-only execution store that competes with `SQLiteJobStore`;
- a new generic shell/process runner;
- a parallel duplicate-execution implementation;
- a direct A-Wiki execution/claim store dependency.

### 2. Dispatch identity is graph-run scoped

A bare TaskNode ID is not a durable execution identity because the same graph/node may run more than once.

The semantic dispatch key is:

`{graph_id, graph_run_id, node_id}`

The implementation maps this key deterministically to the durable `job_id` / execution identity. Encoding details are implementation-local but must be validated, bounded, stable across reconnect/retry, and collision-safe.

Re-running the same graph creates a new `graph_run_id`; reconnecting/recovering the same run preserves it.

### 3. Chat/tunnel workers are pull-mode; programmatic workers may be push-mode

A Secure MCP Tunnel transports MCP traffic between ChatGPT and a private/local MCP server. It does **not** by itself turn an existing ChatGPT conversation into a server-addressable background worker that Conductor may push an arbitrary new model turn into.

Current OpenAI documentation describes custom MCP apps as tools that ChatGPT uses from a chat/prompt, with Secure MCP Tunnel providing connectivity to a private MCP server. It does not document an MCP-server primitive that starts an arbitrary new ChatGPT turn. GE-7 must therefore model execution-surface capability explicitly rather than assuming push semantics from the word `tunnel`.

Scheduler/dispatch vocabulary:

- `INTERACTIVE_PULL` — a ChatGPT/Serena-tunnel worker. Conductor durably queues/offers an assignment for that worker. During an active model turn, the AI client claims/pulls the next assignment through an approved Conductor task-inbox/application seam, executes bounded tools, heartbeats/checkpoints, and reports evidence. No scheduler code pretends it can wake the chat by writing to the tunnel.
- `PROGRAMMATIC_PUSH` — a local/headless/API/durable agent surface for which Conductor owns an explicit invocation API/process. GE-7 may call the adapter after durable reservation/gating and supervise the returned execution identity.

A worker snapshot therefore needs a declared dispatch mode/capability. Unknown mode is non-dispatchable; do not probe or guess.

For the current Sunday-Worker ChatGPT plugins, the model in the chat is the **actor**, Serena is the semantic/tool runtime, and the tunnel is only the **transport**. Conductor is the manager/queue/lease authority. The practical flow is:

`GE-6 selects node -> GE-7 durably offers/reserves -> active ChatGPT worker pulls/claims -> AI performs task through Serena/tools -> checkpoint/evidence -> lifecycle verify/review`

This means full hands-off autonomy for chat-backed workers additionally requires a documented way to trigger/continue model turns. Until such a surface is explicitly integrated (for example a supported agent/API execution surface), the ChatGPT-tunnel lane remains resumable pull-mode rather than fake push-mode.

A future Conductor MCP/task-inbox transport may expose bounded methods such as `next_assignment`, `claim_assignment`, `heartbeat`, `checkpoint`, and `report_result`; that transport must wrap this application contract and must not become a second scheduler/lifecycle store. Reopening/implementing a general MCP gateway remains a separate architecture gate.

External platform evidence checked 2026-08-26:
- OpenAI Help: `Developer mode and MCP apps in ChatGPT` — custom MCP tools are used in ChatGPT conversations; Secure MCP Tunnel connects private/local MCP servers to supported OpenAI products.
- OpenAI Help: `Apps in ChatGPT` — MCP apps let ChatGPT call approved tools and retrieve/use service data.

### 4. Bounded dispatch transaction

For one GE-6 selected assignment, GE-7 performs this logical transaction through existing seams:

1. resolve the graph-run dispatch key;
2. idempotently find or create/recover the corresponding durable job;
3. move the job to READY only when lifecycle policy permits;
4. claim the exact scheduled worker using the store's expected-version/CAS protection;
5. execute required brain/safety/human/provider gates;
6. enter GATING through the existing lifecycle API;
7. invoke exactly one allowlisted operation using `execute_operation()`;
8. let `DurableJobExecutionCoordinator` own the GATING → EXECUTING → checkpoint → VERIFYING path or RECOVERY_NEEDED classification;
9. reconcile/release the GE-6 reservation from the durable outcome.

The adapter must tolerate observing a job already part-way through this sequence after reconnect. It reconciles actual durable state rather than replaying non-idempotent steps blindly.

### 5. Gates occur before attempt consumption

A gate refusal, missing human approval, lost mutation authority, provider unavailability, or identity mismatch must prevent entry into EXECUTING.

Existing job execution increments attempt count when the durable transition to EXECUTING succeeds. GE-7 preserves this invariant so a NO-GO that prevents execution does not consume an attempt.

### 6. Scheduler reservation lease is Conductor execution state

A GE-6 reservation and its heartbeat/expiry are control-plane execution coordination, not A-Wiki cross-agent claims.

A-Wiki `.tmp/agent-claims.json` TTL leases remain brain-side coordination and are not imported/read as the execution lease store.

Reservation policy must be:

- bounded;
- heartbeat/reconciliation aware;
- injectable for deterministic expiry tests;
- fail-closed on ambiguous ownership;
- released/reconciled after durable job outcome.

Lease expiry or missed heartbeat means `RECONCILE DURABLE STATE`. It does **not** mean `RELAUNCH`.

This ADR deliberately does not freeze a wall-clock lease duration. The implementation must choose one bounded policy at a single seam and prove expiry/recovery behavior; tuning the number does not require a new architecture ADR unless semantics change.

### 7. Existing duplicate-execution guard is mandatory

Before an external execution can be launched, the existing canonical execution fingerprint/dedup path remains authoritative.

Expected outcomes stay:

- no equivalent execution → safe to launch;
- equivalent live execution → attach/observe, do not duplicate;
- equivalent verified completion → reuse completion/evidence where identity matches;
- unknown/unsafe identity or state → block and reconcile.

Transport/session/tunnel failure never authorizes blind replay.

### 8. Dispatch failures are node-local and evidence-backed

A failure dispatching one selected node does not automatically invalidate unrelated assignments from the same GE-6 schedule plan.

Each node records/reconciles its own durable outcome. The scheduler is then triggered again by the resulting state change, allowing remaining safe capacity to be reconsidered.

### 9. `operator_dispatch.py` is not the internal graph-dispatch bus

`operator_dispatch.py` translates bounded external operator requests to job-control calls. GE-7 may reuse the same service contract, but internal graph scheduling must call the application/job-control seam directly rather than synthesize operator protocol requests.

This avoids unnecessary protocol coupling and keeps transport concerns outside Graph Runtime.

### 10. A-Wiki access remains bridge-only

If GE-7 needs brain gate/claim/policy information, it uses the GE-0005 approved bridge seam. No direct `.tmp` store reads and no `scripts.lib.*` imports are allowed.

A-Wiki claims may document cross-agent work ownership; they do not substitute for Conductor job claims/reservations/execution records.

## Required implementation tests

GE-7 implementation must prove at least:

- same `{graph_id, run_id, node_id}` retry does not create duplicate durable jobs;
- different graph runs of the same node remain distinct;
- stale expected-version/worker claim fails without external execution;
- gate NO-GO does not increment attempt count;
- successful dispatch reaches VERIFYING through the existing coordinator;
- backend uncertainty reaches RECOVERY_NEEDED and does not blind-relaunch;
- equivalent live execution attaches/reconciles rather than launching twice;
- equivalent verified completion is reused only when fingerprint + identity match;
- reservation expiry triggers reconciliation before reassignment;
- transport loss between durable transition and observer response can resume safely;
- one node's dispatch failure does not corrupt another independently safe reservation.

## Rejected alternatives

### New `GraphExecutionStore` owning lifecycle

Rejected. Graph persistence records graph structure/runs/events; job lifecycle is already durably modeled and verified elsewhere.

### Dispatch through A-Wiki agent-claim TTLs

Rejected. Those leases coordinate agents working on repository scope; they do not own local Conductor process execution and are intentionally brain-side implementation state.

### Internal graph dispatch through operator protocol

Rejected. It couples scheduler internals to an external transport contract without adding durability.

### Blind retry on lease/transport expiry

Rejected by the resilient-execution invariant: transport/observation failure is not execution failure, and duplicate execution must be assessed from durable state first.

## Consequences

- Graph Runtime composes with the proven job lifecycle instead of replacing it.
- Retry budgets, worker claims, evidence checkpoints, recovery classification, supervised execution, and dedup remain single-source-of-truth behaviors.
- GE-7 work should be mostly adapter/orchestration logic with focused extensions to `job_control.py` only when existing public seams are insufficient.
- Scheduler remains free to recompute after each durable state event without owning execution attempts.
- Future worker/runtime/provider adapters can change without redesigning graph dispatch identity or lifecycle semantics.
