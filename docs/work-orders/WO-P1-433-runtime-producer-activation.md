# WO-P1-433 — RUNTIME-ACT-1 Production Durable Runtime Producer Activation

Status: R3_SHAPING / SOURCE_BLOCKED_ON_FRONT_DOOR_PROOF
Issue: #433
Parent roadmap: #397 / LOCAL-USABLE-1
Depends on: #431 RUNTIME-AUTH-1 source implementation acceptance
Blocks: #429 COCKPIT-1B / LOCAL-USABLE-1
Topology: CONTROL_PLANE_ONLY
Risk: R3 — durable job/execution/lease activation, process ownership, replay/recovery, schema initialization
Owner: GPT-5.6 Sol integrator
Claim: WO-P1-433-RUNTIME-ACTIVATION-SHAPING-001

## Exact binding

- authority/execution repo: `A:\GitHub\A-Wiki-Conductor`
- authoritative remote branch: `docs/wo-p1-433-runtime-activation-shaping`
- shaping base: `ccdbe99d87af0e33d316513457790da576e11bab`
- current tracked mutable scope: this Work Order only
- source mutation: FORBIDDEN until #431 implementation is accepted and the runtime owner, product front door, migration/failure model, and exact source/test scope are frozen
- live installed DB/runtime mutation: FORBIDDEN in shaping
- local collision commit `c2bed66046f99a190164ddb7e3446a7442fda695` is non-authoritative evidence only and is not a merge source

## Product gap

#431 establishes one canonical control-database identity locator and fail-closed identity comparison. That is necessary but not sufficient for LOCAL-USABLE-1.

Current ordinary desktop startup composes Control Center/settings/provider/connector-lifecycle/read-only operator surfaces but does not invoke an accepted durable task-execution producer. The Graph Monitor is read-only. Connector Start/Stop owns connector lifecycle, not work-order/job execution truth.

Current source contains production-capable durable execution assemblies, but no inspected ordinary product caller activates the complete chain from a shipped front door. Library callability alone is not LOCAL-USABLE-1.

## Reuse-before-build audit

### REUSE — existing scheduler / lease / dispatch chain

Existing accepted seams already cover the lower-level composition and MUST be reused:

- GE-6 `schedule_once(...)` owns deterministic ready/capability/conflict selection.
- `ProductionElasticWorkerExecutor.execute_once(...)` is the highest-level inspected production orchestration seam: it observes fresh worker supply, applies provider eligibility, invokes `schedule_once`, assembles selected `ParallelReadyTask` values, drives `ParallelReadyExecutor`, handles fixed-pool versus elastic-capacity recovery, and re-observes provisioned capacity.
- `ParallelReadyExecutor` owns provider authority/admission, canonical `WorkerLeaseBroker` acquisition, batch execution, typed wait/recovery outcomes, and admission-retention rules under uncertainty.
- `GraphDispatchParallelRunner` already exists and is the accepted adapter from one leased `ParallelReadyTask` to `GraphDispatchCoordinator.dispatch(...)`; no replacement runner is needed.
- `GraphDispatchCoordinator` reuses `DurableJobControlService` and GE-7 durable graph/job identity and reconcile semantics.
- `DurableJobControlService` / `DurableJobExecutionCoordinator` own job lifecycle, single-winner execution entry, checkpoints, VERIFYING/recovery transitions.
- `SQLiteExecutionStore` + supervised execution own durable process execution and recovery truth.
- `SQLiteWorkerLeaseStore` / `WorkerLeaseBroker` own worker execution-lease truth.
- `SQLiteProviderConfigStore` owns provider configuration/admission/generation/capacity truth.
- `build_sqlite_parallel_ready_executor(...)` already composes `ParallelReadyExecutor` with the SQLite provider-admission authority; it is a reusable assembly seam, not the missing product front door.
- #431 owns the canonical product control-DB identity locator/comparator shared by these owning stores.

### REUSE — recovery/replay precedent

`zero_relay_review_execution.execute_review_dispatch(...)` is an existing top-level composition precedent for durable job + execution + lease + provider-admission truth. It demonstrates exact-identity recovery, equivalent-execution reconciliation, lease/admission cleanup, and no blind replay.

It is review-specialized and is not automatically the generic product owner, but its recovery/failure semantics MUST be reused or preserved rather than re-invented.

### DO NOT BUILD

Do not add:
- another `ParallelReadyRunner`;
- another scheduler, task/job store, claim/lease store, retry/recovery engine, provider-admission store, review/completion plane, or execution journal;
- a writable Graph Monitor/operator projection;
- synthetic task semantics around connector Start/Stop;
- A-Faster `runs/**/execution-pointer.json` scanning as product authority.

## Remaining composition gap

The remaining gap is narrower than the first shaping draft:

1. no ordinary shipped product front door has been proven to instantiate and invoke the accepted production chain;
2. durable product input authority for `TaskGraph`, `ReadySetResult`, per-node `ParallelReadyNodeContract`, eligibility/provider-inflight evidence, batch identity, and runtime policy must be traced to existing accepted owners;
3. the canonical #431 DB identity must be bound before any write-capable runtime store is constructed;
4. the default product operation/backend used by the selected PROGRAMMATIC_PUSH task must already exist or be explicitly shaped without inventing a second execution universe.

## R3 activation direction

Preferred reuse stack:

`explicit product trigger -> accepted graph/ready/contracts/eligibility inputs -> ProductionElasticWorkerExecutor -> ParallelReadyExecutor -> provider admission + WorkerLease -> GraphDispatchParallelRunner -> GraphDispatchCoordinator -> DurableJobControlService -> supervised execution`.

Do not bypass `ProductionElasticWorkerExecutor` by manually rebuilding scheduler + worker-supply + task assembly unless a post-#431 exact call-path proof shows that higher-level seam is incompatible with the chosen product input authority.

Only PROGRAMMATIC_PUSH lanes may launch. INTERACTIVE_PULL remains OFFERED/pull-mode and must never be fake-pushed.

## Product front-door gate

Before source mutation, prove a thin existing product/control entry can invoke the runtime owner from durable accepted inputs.

The activation command MUST live at a runtime-owner control seam. The read-only Graph Monitor/operator projection may display context and outcome but may not become scheduling/execution authority or initialize runtime stores.

Preferred proof order:

A. Reuse an already-shipped control/CLI/application entry that can reconstruct the required graph/ready/contracts/eligibility/runtime inputs from accepted durable state and call the existing production executor.

B. If A is unavailable, reuse an already-accepted durable operator/graph request contract that can reach the same owner without adding a parallel serialized task/route authority.

C. If neither is true, STOP with `SCOPE_EXPANSION_REQUIRED`. Do not invent a new durable request file/store merely to bridge process boundaries.

A library-only helper or test-only call path is insufficient.

## Initialization / migration boundary

Runtime tables may be created only because an explicit runtime-owner activation is executing a real product action:

- Cockpit/Graph Monitor/operator reads never initialize or migrate runtime stores.
- App startup alone must not fabricate empty runtime truth.
- #431 canonical control-DB identity must be proven before job/execution/lease/provider runtime store construction.
- `SQLiteWorkerLeaseStore` constructor is write-capable; constructing it is an activation effect, never a read.
- identity mismatch fails before any runtime store constructor/initialize/write.
- legacy installed DB activation is first exercised on a sacrificial copy.
- rollback/recovery is defined and verified for each partial initialization/migration failure.
- concurrent activation/initialization is tested for idempotence or typed fail-closed behavior.
- schema/table inventory and durable identity are verified after migration before execution is authorized.
- post-migration reopen/read/write verification is required before any live installed-DB activation is accepted.
- the live source DB must remain recoverable if activation fails.

A failed or ambiguous activation never means safe retry. Reconcile job/execution/lease/provider durable state first.

## Failure model

Fail closed on:
1. #431 canonical authority identity unavailable/mismatch;
2. graph/run/node/contract identity unavailable or stale;
3. required ready/eligibility/provider-inflight/batch evidence missing;
4. worker dispatch mode unknown;
5. INTERACTIVE_PULL presented to a push-only execution path;
6. provider configuration/admission generation drift;
7. worker lease conflict/expiry/ambiguous recovery;
8. durable equivalent execution live, terminal-unharvested, or outcome-unknown;
9. migration/init/concurrency/post-migration verification failure;
10. repeated product command after ambiguous response;
11. any cross-authority identity mismatch;
12. product front door cannot prove the durable input owner.

## RED-first acceptance matrix before source mutation

Tests must prove:
1. ordinary product invocation reaches the selected existing runtime owner, not a test-only helper;
2. startup/read-only Graph/Cockpit observation creates no runtime tables;
3. canonical DB mismatch fails before job/execution/lease/provider construction or mutation;
4. legacy canonical DB remains unchanged until explicit activation;
5. sacrificial activation initializes only existing owning-store schemas and passes rollback/concurrency/post-migration verification;
6. one bounded PROGRAMMATIC_PUSH assignment creates/reuses the canonical durable job, exact WorkerLease/provider admission, and durable execution truth;
7. RUNNING execution is observable from the same canonical DB while the process is live;
8. successful terminal execution reaches existing verification/terminal semantics;
9. timeout/disconnect/ambiguous child state remains terminal-unharvested/outcome-unknown/reconcile-required and never authorizes blind replay;
10. exact replay of a live/equivalent dispatch does not launch a second child;
11. lease/provider cleanup occurs only when exact terminality/ownership is proven;
12. INTERACTIVE_PULL is OFFERED with no process launch;
13. Cockpit/read-only refresh constructs none of the owning runtime stores;
14. concurrent activation is idempotent or fails typed without split authority;
15. provider, job-CAS, execution-fingerprint/dedup, scheduler/conflict and lease invariants remain green;
16. connector Start/Stop never masquerades as durable task execution evidence;
17. no new scheduler/store/claim/retry/review/completion authority exists;
18. installed default startup remains usable when runtime activation is never invoked.

## Scope gate

Do not assume source paths yet.

After #431 implementation acceptance, run a fresh exact-main call-graph/ownership audit to prove:
- the narrow product front door;
- the durable graph/ready/contracts/eligibility input owners;
- the minimal production assembly needed to instantiate `ProductionElasticWorkerExecutor` and its existing dependencies under the #431 canonical DB identity;
- the exact source/test paths.

Any need to add a new serialized task/route authority, scheduler, store, schema, or retry/completion lifecycle is `SCOPE_EXPANSION_REQUIRED` and requires a new R3 architecture decision.

## Current checkpoint

- #431 authority-model docs are merged, but #431 source implementation acceptance is still the dependency gate.
- PR #434 first candidate `2ef328aff0c2df9fe4ffaa7a5308dde079107812` received independent R3 `CHANGES_REQUIRED` (P0/P1/P2/P3 = 0/0/1/4) because it missed existing `GraphDispatchParallelRunner` / `build_sqlite_parallel_ready_executor` and needed stronger trigger/migration wording.
- Additional read-only archaeology identified `ProductionElasticWorkerExecutor.execute_once(...)` as the higher-level existing production orchestration seam and found no ordinary product caller.
- The repaired shaping contract therefore reuses that stack and narrows the remaining problem to durable input/front-door composition.
- Source mutation remains blocked until this repaired docs candidate passes fresh independent exact-SHA review and #431 implementation is accepted.
- #429 remains dependency-required until #431 and #433 are accepted.
