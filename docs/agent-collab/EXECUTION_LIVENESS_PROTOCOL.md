# Execution Liveness / Operator Status Protocol

Status: PROPOSED BINDING GOVERNANCE CONTRACT / RUNTIME IMPLEMENTATION PENDING / R2_REREVIEW_REQUIRED
Owner: A-Sunday Conductor coordination layer
Parent architecture: `GE-0008` / `WO-P1-231`

## 1. Purpose

Long-running agent, provider, tool, CI, review, repair, or executor work must never become an opaque "wait" state. The operator and the next session must be able to determine whether work is progressing, waiting on a known dependency, stalled, terminal, or unknown without reconstructing chat history.

This protocol EXTENDS existing durable job events/checkpoints, ContinuityGuard, recovery reconciliation, provider/execution authority, and `operator.v1`. It does **not** create a second scheduler, task store, claim/lease system, retry engine, review system, or SSoT.

## 2. Authority

Authoritative execution/task state remains the existing durable job/task state plus actual runtime/process/Git/GitHub evidence. Liveness is a derived operator projection.

Priority for factual liveness truth:

`ACTUAL PROCESS/SESSION/RUNTIME -> DURABLE JOB EVENTS/CHECKPOINTS -> PROVIDER/CI EVIDENCE -> OPERATOR PROJECTION -> CHAT CLAIM`

Unknown or contradictory evidence fails closed for mutation/retry.

## 3. Required liveness projection

Every long-running execution must expose or allow derivation of:

- `task_ref` / work-order identity;
- `execution_id` or equivalent attempt identity;
- executor/provider/model/runtime identity where applicable;
- authoritative job/task state;
- derived `liveness_class`;
- `last_activity_at`;
- `last_progress_at`;
- `last_heartbeat_at` when the executor supports heartbeats;
- typed waiting/blocker/failure reason;
- exact candidate SHA / worktree identity when repository work is involved;
- evidence/log/result reference;
- exact next safe action.

For every material delegated dispatch that can outlive one immediate turn, the existing work-order/job/evidence path must also retain a recoverable dispatch pointer: task/work-order, lane, executor/provider/model, repo/worktree/branch/base/current SHA, claim/scope, process/session identity when known, start time, log/result/evidence destinations, retry-safety classification, and expected completion evidence. This is a pointer into existing authorities, not a new task or execution store.

Do not store secrets, unrestricted environment dumps, hidden reasoning, raw credentials, or credential-bearing command lines in liveness evidence.

## 4. Derived liveness classes

Use this small projection vocabulary; do not replace the underlying job state machine with it:

- `STARTING` — accepted/launching but execution identity is not yet fully observed;
- `RUNNING` — runtime/session is alive and recent activity evidence exists;
- `WAITING` — execution is intentionally blocked on a typed dependency while ownership remains known;
- `STALLED` — expected runtime remains non-terminal but silence/progress age exceeded its declared bound or evidence stopped advancing;
- `TERMINAL_UNHARVESTED` — the executor/process is terminal and a result/log/evidence artifact exists or is expected, but the integrator has not yet reconciled and consumed it; conflicting mutation/replay is blocked until harvest/reconciliation;
- `INTERRUPTED` — the prior executor/session is no longer live and required completion evidence is absent or incomplete; retry authority depends on explicit replay-safety and side-effect reconciliation;
- `TERMINAL` — a durable terminal result/outcome exists and harvest, runtime cleanup, and reconciliation are complete or explicitly classified;
- `UNKNOWN` — evidence is insufficient or contradictory; fail closed.

Typed `WAITING` reasons should reuse existing failure/blocker vocabulary where possible, including permission/authorization, rate limit/quota, provider unavailable, external dependency, CI, human action, or device offline.

Terminal result detail may include `COMPLETED_ACCEPT`, `COMPLETED_CHANGES_REQUIRED`, `FAILED`, `CANCELLED`, or `ABNORMAL_EXIT` as an operator/result classification. These are not a replacement durable state machine.

## 5. Activity, progress, and heartbeat are different

`last_activity_at` advances on trustworthy executor/tool/runtime activity such as a bounded tool call, output event, process observation, or provider response.

`last_progress_at` advances only on meaningful task progress: a completed phase, new verified artifact, changed candidate identity, completed test/review step, or other task-contract milestone. Repeated polling or identical logs do not count as progress.

`last_heartbeat_at` proves only that an expected actor/runtime is still observable. A heartbeat must never be presented as proof of task progress.

## 6. Stall contract

Each long-running task/executor adapter must declare a bounded expected activity/heartbeat policy appropriate to the task class. Do not hard-code one global timeout for every model/provider/tool.

A `STALLED` classification is a warning that triggers reconciliation, not automatic replay. Before retry/restart/failover:

1. inspect actual process/session identity;
2. inspect the latest bounded logs/output;
3. inspect durable job events/checkpoints/result destination;
4. inspect provider/CI state when applicable;
5. classify whether the prior attempt is still running, completed, failed, or ambiguous;
6. only then choose attach/recover/retry/failover under existing authority.

A timeout by itself is never proof that work did not complete. Likewise, a vanished chat turn, closed browser, context rollover, transport disconnect, or missing terminal session is not replay authority. Classify the prior attempt as `NOT_STARTED`, `PARTIAL`, `COMPLETE_UNVERIFIED`, `COMPLETE_VERIFIED`, or `UNKNOWN` using existing execution evidence before any non-idempotent retry.

## 7. Operator reporting rule

Do not report only "waiting for GLM/CI/reviewer". For active long-running work, report a compact truthful status block containing at least:

`STATE | TASK | EXECUTOR | EXACT_ID/SHA | LAST_ACTIVITY | LAST_PROGRESS | BLOCKER/REASON | EVIDENCE | NEXT_SAFE_ACTION`

When direct timestamps are not available, say `UNKNOWN` rather than inventing them.

When terminal evidence exists, report the terminal classification and stop describing the task as running.

## 8. New-session recovery rule

Every new session must recover active long-running status from actual runtime/Git/GitHub/durable records using the universal repository entry sequence. Do not ask the user to paste prior prompts/results when the state is recoverable.

Before selecting new READY work, reconcile every known outstanding delegated execution pointer for the current task/lane against: exact process/session identity when still observable; bounded logs/result destination; Git/worktree/branch/HEAD/dirty state; existing job/events/checkpoints; and provider/CI state when applicable. Derive at least `RUNNING`, `TERMINAL_UNHARVESTED`, `STALLED`, `INTERRUPTED`, or `UNKNOWN`.

`TERMINAL_UNHARVESTED` is a harvest-first state: consume and verify the declared result/evidence before redispatch or conflicting mutation. `STALLED`, transport timeout, session loss, and `INTERRUPTED` require replay-safety reconciliation; none grants automatic retry.

The previous chat may be used only as convenience context after factual state is re-pinned.

If an active execution cannot be recovered, classify `UNKNOWN` or the appropriate typed failure and checkpoint the blocker. Never silently launch a duplicate mutable attempt.

### 8.1 Context/session rollover checkpoint

Before intentionally rotating a chat/session/context while delegated work is outstanding, checkpoint the existing task/claim reference, every outstanding execution/process/session identity known, evidence/log/result destinations, current liveness classification, replay-safety state, and the exact next harvest/reconcile action. The checkpoint is continuity evidence only; it does not create a second execution authority.

## 9. `operator.v1` / mobile projection

`operator.v1` remains the canonical control vocabulary. Mobile/ChatGPT/operator surfaces should WRAP/EXTEND it with bounded liveness/status fields rather than creating a broad second Mobile API.

The mobile/operator projection should support read-only status/result retrieval first. Any cancel/retry/recover action remains subject to existing authorization, lease/worktree, provider, replay-safety, and exact-identity gates.

ChatGPT itself is not assumed to push a new turn into an arbitrary closed conversation. Push notification, if desired, must use an accepted external channel/adaptor while durable status remains readable through A-Conductor.

## 10. Acceptance requirements

Execution-liveness implementation is not accepted until deterministic tests prove at minimum:

- activity can advance without falsely advancing progress;
- heartbeat can stay alive while progress is stale;
- a silent non-terminal execution becomes `STALLED` only after its declared bound;
- `STALLED` never causes blind duplicate replay;
- a process that completed during a timeout is reconciled to terminal truth before retry;
- `WAITING` exposes a typed reason;
- terminal result stops heartbeat/stall monitoring for that attempt;
- a fresh session can recover the same execution identity/status without chat history;
- a terminal-but-unharvested result is collected before any duplicate dispatch or conflicting mutation;
- context rollover preserves the outstanding dispatch pointer and exact next harvest/reconcile action;
- `operator.v1` status projection leaks no secret/credential data;
- ambiguous evidence yields `UNKNOWN` and blocks unsafe mutation/retry.

## 11. Roadmap placement

This is a P0 prerequisite for trustworthy mobile Zero-Relay observability. Implement it after the required ZRA predecessor authority is accepted and before claiming the hybrid mobile E2E loop complete.

Reuse existing execution records/events/checkpoints first; implementation must remain `REUSE -> WRAP -> EXTEND` unless concrete evidence proves a new primitive is unavoidable.
