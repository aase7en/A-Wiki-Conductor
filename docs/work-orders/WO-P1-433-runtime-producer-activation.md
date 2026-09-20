# WO-P1-433 — RUNTIME-ACT-1 Production Durable Runtime Producer Activation

Status: SHAPING / R3_ACTIVATION_MODEL / SOURCE_BLOCKED_ON_431
Issue: #433
Parent roadmap: #397 / LOCAL-USABLE-1
Depends on: #431 RUNTIME-AUTH-1 accepted identity/composition
Blocks: #429 COCKPIT-1B / LOCAL-USABLE-1
Topology: CONTROL_PLANE_ONLY
Risk: R3 — production execution, leases, provider admission, migration boundary
Claim: WO-P1-433-RUNTIME-ACTIVATION-SHAPING-001

## Exact binding

- repo: `A:\GitHub\A-Wiki-Conductor`
- shaping worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo433-runtime-activation-shaping`
- branch: `docs/wo-p1-433-runtime-activation-shaping`
- shaping base: `ccdbe99d87af0e33d316513457790da576e11bab`
- current mutable scope: this Work Order only
- source mutation: FORBIDDEN until #431 is accepted and this R3 owner/failure model passes independent review
- live installed DB/runtime mutation: FORBIDDEN in shaping

## Product gap

Current desktop startup builds Control Center/settings/provider/lifecycle surfaces but does not invoke an accepted durable task execution producer.
The existing Graph Monitor is read-only. Connector Start/Stop controls Serena connector lifecycle, not durable job/execution truth.
Library callability is insufficient: no ordinary desktop caller currently drives GraphDispatchCoordinator, ParallelReadyExecutor, or DurableJobControlService execution.

## Reuse-before-build findings

Accepted authorities already exist and MUST be reused:
- GE-0007: GraphDispatchCoordinator -> DurableJobControlService is the canonical graph-to-durable-execution transaction.
- SQLiteJobStore owns durable job lifecycle/version/events.
- SQLiteExecutionStore + supervised execution own durable process execution and recovery truth.
- ParallelReadyExecutor already gates provider authority, acquires WorkerLease, then invokes a runner and understands GraphDispatchResult.
- WorkerLeaseBroker / SQLiteWorkerLeaseStore own worker execution lease truth.
- SQLiteProviderConfigStore owns provider admission/generation/capacity truth.
- GE-6 scheduler owns deterministic ready/capability/conflict selection; no second scheduler is permitted.
- #431 owns one canonical control-DB identity locator shared by those authorities.

Missing composition:
- no production ParallelReadyRunner adapter was found that wraps GraphDispatchCoordinator for ordinary product use;
- no ordinary desktop product action invokes the lease + provider + graph-dispatch chain;
- no default NativeOperationDefinition product assembly exists for that desktop path.

Therefore RUNTIME-ACT-1 is an activation/composition problem, not permission to invent new stores or lifecycle semantics.

## R3 activation direction candidate

Preferred composition is:
`GE-6 ready assignment -> ParallelReadyExecutor -> existing WorkerLease + provider admission -> GraphDispatchCoordinator -> DurableJobControlService -> supervised execution`.

This reuses the only accepted owners for scheduling, lease, provider admission, job lifecycle and execution records.
The runner adapter may translate one ParallelReadyTask + exact acquired WorkerLease into the already-defined GraphDispatchRequest/GateDecision; it must add no lifecycle state.

Smallest product trigger candidate for LOCAL-USABLE-1 is an explicit bounded operator action from the existing Graph Monitor/control facade, not a new background timer:
- select an existing graph/run context;
- compute/consume the current accepted ready plan;
- execute at most one bounded batch through the composition above;
- show typed blocked/reconcile outcomes;
- only PROGRAMMATIC_PUSH lanes may launch; INTERACTIVE_PULL remains offered/pull-mode and must never be fake-pushed.

This trigger is a candidate, not source authorization. Exact UI/control/assembly scope must be frozen only after #431 lands and a full call-path audit proves the minimum set.

## Initialization / migration boundary

Runtime tables may be created only because the explicit runtime owner is activated:
- Cockpit/Graph Monitor reads never initialize or migrate;
- app startup alone must not fabricate empty runtime truth;
- first explicit runtime activation may initialize existing owning stores only after exact #431 DB identity is proven;
- SQLiteWorkerLeaseStore constructor auto-initializes, so construction itself is a consequential activation effect;
- mismatch must fail before any store construction/write;
- legacy installed DB activation requires sacrificial-copy proof before live use.

A failed or ambiguous activation never means safe retry. Reconcile job/execution/lease/provider durable state first.

## Failure model

Fail closed on:
1. #431 canonical authority identity unavailable/mismatch;
2. graph/run/assignment identity unavailable or stale;
3. worker dispatch mode unknown;
4. INTERACTIVE_PULL passed to a push-only execution path;
5. provider configuration/admission drift;
6. worker lease conflict/expiry/ambiguous recovery;
7. durable job/execution equivalent live or outcome-unknown state;
8. legacy migration/init failure;
9. product command repeats after ambiguous response;
10. any cross-authority identity mismatch.

## RED-first acceptance matrix before source mutation

Tests must prove:
1. no runtime tables are created by startup/read-only Graph/Cockpit observation;
2. mismatched DB identity fails before job/execution/lease/provider initialization;
3. explicit activation on a sacrificial legacy DB initializes only existing owning-store schemas;
4. one PROGRAMMATIC_PUSH graph assignment creates/reuses the canonical durable job, acquires the exact WorkerLease/provider admission, and creates durable execution truth;
5. RUNNING execution is observable from the same canonical DB while the process is live;
6. terminal/unknown execution outcomes remain durable and reconcilable without blind replay;
7. duplicate activation attaches/reconciles rather than launching twice;
8. provider/lease cleanup follows existing authorities and ambiguous cleanup remains recovery-required;
9. INTERACTIVE_PULL produces OFFERED/no process launch;
10. unrelated connector Start/Stop does not masquerade as task execution evidence.

## Scope gate

Do not assume source paths yet.
Likely touched seams may include existing graph/parallel-ready composition plus a bounded desktop control/action surface, but any exact list requires a fresh post-#431 call-graph/ownership proof.
No new DB/store/schema/state machine/scheduler/retry engine/review authority is allowed.

## Current checkpoint

Shaping conclusion: reuse the accepted ParallelReadyExecutor + GraphDispatchCoordinator chain as the production runtime owner path.
The missing work is top-level composition/product activation, not durable semantics.
#431 remains the prerequisite identity/comparison slice; #429 remains downstream until this node is accepted.
