# WO-P1-433 — RUNTIME-ACT-1 Production Durable Runtime Producer Activation

Status: R3_SHAPING / SOURCE_BLOCKED_ON_ZERO_RELAY_OWNERSHIP_AND_FRONT_DOOR_PROOF
Issue: #433
Parent roadmap: #397 / LOCAL-USABLE-1
Depends on: #431 RUNTIME-AUTH-1 RELEASED + active #215 / WO227 ownership reconciliation
Blocks: #429 COCKPIT-1B / LOCAL-USABLE-1
Topology: CONTROL_PLANE_ONLY
Risk: R3 — durable job/execution/lease activation, process ownership, replay/recovery, schema initialization
Owner: GPT-5.6 Sol integrator
Claim: WO-P1-433-RUNTIME-ACTIVATION-SHAPING-001

## Exact binding

- authority/execution repo: `A:\GitHub\A-Wiki-Conductor`
- authoritative remote branch: `docs/wo-p1-433-runtime-activation-shaping`
- original shaping base: `ccdbe99d87af0e33d316513457790da576e11bab`
- current accepted main after #431: `de8b037cfd78e4513656b726981caee05d5bb39b`
- current tracked mutable scope: this Work Order only
- source mutation: FORBIDDEN until Zero-Relay ownership is consumed/transferred explicitly, the runtime owner/product front door/input authority is proven, the migration/failure model remains valid, and exact source/test scope is frozen
- live installed DB/runtime mutation: FORBIDDEN in shaping
- local collision commit `c2bed66046f99a190164ddb7e3446a7442fda695` is non-authoritative evidence only and is not a merge source

## Product gap

#431 is now accepted/released and establishes one canonical control-database identity locator plus fail-closed identity comparison. That is necessary but not sufficient for LOCAL-USABLE-1.

Current ordinary desktop startup composes Control Center/settings/provider/connector-lifecycle/read-only operator surfaces but does not invoke an accepted durable task-execution producer. The Graph Monitor is read-only. Connector Start/Stop owns connector lifecycle, not work-order/job execution truth.

Repo-wide non-test tracing finds production-capable durable execution assemblies but no shipped caller for the complete producer chain. Library callability alone is not LOCAL-USABLE-1.

## Cross-roadmap ownership fence

The accepted WO397 roadmap explicitly states that it **does not cancel any active Zero-Relay claim**.

Issue #215 remains OPEN under claim `GPT1-ZRA3-PREFLIGHT-001` and owns automatic NEXT READY continuation. Its prepared WO227 already names the same two gaps rediscovered here:
- real production reachability into the existing scheduler/provider/lease/GraphDispatch execution fabric; and
- authoritative construction of `ParallelReadyNodeContract` inputs.

Historical PR #263 / #269 / #274 and WO191/WO195 source candidates are Draft/unaccepted and hundreds of commits behind current main. They are research evidence only, not source authority. However, the durable #215 ownership has not been released.

Therefore #433 MUST NOT implement a second production-reachability or contract-producer path while #215 remains active.

Default disposition:
1. **CONSUME / VERIFY** an accepted #215/WO227 producer when it lands, proving that it uses #431's canonical runtime-authority identity and produces the durable execution/lease truth required by LOCAL-USABLE-1; or
2. if Product Fast Lane needs a narrower non-continuation activation first, record an explicit ownership split/transfer in both #215 and #433 before any overlapping source claim.

Until one of those is durably true:
`SOURCE_MUTATION_433 = NO`.

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

These lower-level seams are shared capability, not permission for #433 to duplicate #215's continuation/product-reachability ownership.

### REUSE — recovery/replay precedent

`zero_relay_review_execution.execute_review_dispatch(...)` is an existing top-level composition precedent for durable job + execution + lease + provider-admission truth. It demonstrates exact-identity recovery, equivalent-execution reconciliation, lease/admission cleanup, and no blind replay.

It is review-specialized and is not automatically the generic product owner, but its recovery/failure semantics MUST be reused or preserved rather than re-invented.

### DO NOT BUILD

Do not add:
- another `ParallelReadyRunner`;
- another scheduler, task/job store, claim/lease store, retry/recovery engine, provider-admission store, review/completion plane, or execution journal;
- another ZRA-3/WO227 production-reachability or `ParallelReadyNodeContract` producer under #433;
- a writable Graph Monitor/operator projection;
- synthetic task semantics around connector Start/Stop;
- A-Faster `runs/**/execution-pointer.json` scanning as product authority.

## Remaining composition gap

The remaining gap is narrower than the first shaping draft:

1. active #215/WO227 production-reachability ownership must be consumed, formally split, or transferred before #433 source work;
2. no ordinary shipped product front door has been proven to instantiate and invoke the accepted production chain;
3. durable product input authority for `TaskGraph`, `ReadySetResult`, per-node `ParallelReadyNodeContract`, eligibility/provider-inflight evidence, batch identity, and runtime policy must be traced to existing accepted owners;
4. the canonical #431 DB identity must be bound before any write-capable runtime store is constructed;
5. the default product operation/backend used by the selected PROGRAMMATIC_PUSH task must already exist or be explicitly shaped without inventing a second execution universe.

## R3 activation direction

Target reuse stack, to be **consumed from the accepted owner rather than reimplemented by #433**:

`accepted product/continuation trigger -> authoritative graph/ready/contracts/eligibility inputs -> ProductionElasticWorkerExecutor -> ParallelReadyExecutor -> provider admission + WorkerLease -> GraphDispatchParallelRunner -> GraphDispatchCoordinator -> DurableJobControlService -> supervised execution`.

If #215/WO227 lands this chain, #433's job is compatibility/integration proof against #431 canonical DB identity and LOCAL-USABLE-1 observation needs.

Do not bypass `ProductionElasticWorkerExecutor` by manually rebuilding scheduler + worker-supply + task assembly. Do not port unaccepted WO191/WO195/WO227 code merely because it demonstrates a plausible shape.

Only PROGRAMMATIC_PUSH lanes may launch. INTERACTIVE_PULL remains OFFERED/pull-mode and must never be fake-pushed.

## Product front-door gate

Before any #433 source mutation, prove one of these ownership-safe cases:

A. **Preferred:** an accepted #215/WO227 production path already owns the front door and authoritative contract production. #433 only consumes/verifies it against #431 identity.

B. #215 and #433 both durably record a non-overlapping ownership split or transfer for a narrower activation path; then re-derive the smallest existing control/CLI/application entry from current main.

C. Neither A nor B is true: STOP with `OWNERSHIP_RECONCILIATION_REQUIRED`. Do not create a new durable request file/store or parallel contract producer merely to bridge the gap.

The activation command, wherever owned, MUST live at a runtime-owner control seam. The read-only Graph Monitor/operator projection may display context and outcome but may not become scheduling/execution authority or initialize runtime stores.

A library-only helper or test-only call path is insufficient.

## Initialization / migration boundary

Runtime tables may be created only because an accepted runtime owner is activating a real product action:

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
2. #215/#433 ownership unresolved for the proposed product-reachability or contract-producer seam;
3. graph/run/node/contract identity unavailable or stale;
4. required ready/eligibility/provider-inflight/batch evidence missing;
5. worker dispatch mode unknown;
6. INTERACTIVE_PULL presented to a push-only execution path;
7. provider configuration/admission generation drift;
8. worker lease conflict/expiry/ambiguous recovery;
9. durable equivalent execution live, terminal-unharvested, or outcome-unknown;
10. migration/init/concurrency/post-migration verification failure;
11. repeated product command after ambiguous response;
12. any cross-authority identity mismatch;
13. product front door cannot prove the durable input owner.

## RED-first acceptance matrix before source mutation

Any future #433 source entry must first prove:
1. #215/WO227 ownership is accepted/consumed or a non-overlapping transfer/split is durably recorded;
2. ordinary product invocation reaches the selected existing runtime owner, not a test-only helper;
3. startup/read-only Graph/Cockpit observation creates no runtime tables;
4. canonical DB mismatch fails before job/execution/lease/provider construction or mutation;
5. legacy canonical DB remains unchanged until explicit activation;
6. sacrificial activation initializes only existing owning-store schemas and passes rollback/concurrency/post-migration verification;
7. one bounded PROGRAMMATIC_PUSH assignment creates/reuses the canonical durable job, exact WorkerLease/provider admission, and durable execution truth;
8. RUNNING execution is observable from the same canonical DB while the process is live;
9. successful terminal execution reaches existing verification/terminal semantics;
10. timeout/disconnect/ambiguous child state remains terminal-unharvested/outcome-unknown/reconcile-required and never authorizes blind replay;
11. exact replay of a live/equivalent dispatch does not launch a second child;
12. lease/provider cleanup occurs only when exact terminality/ownership is proven;
13. INTERACTIVE_PULL is OFFERED with no process launch;
14. Cockpit/read-only refresh constructs none of the owning runtime stores;
15. concurrent activation is idempotent or fails typed without split authority;
16. provider, job-CAS, execution-fingerprint/dedup, scheduler/conflict and lease invariants remain green;
17. connector Start/Stop never masquerades as durable task execution evidence;
18. no new scheduler/store/claim/retry/review/completion authority exists;
19. no duplicate #215/WO227 continuation/contract-producer authority exists;
20. installed default startup remains usable when runtime activation is never invoked.

## Scope gate

Do not assume source paths yet.

#431 implementation is accepted. The remaining source-entry gate is now:
- current-main #215/WO227 ownership disposition;
- narrow product front door;
- durable graph/ready/contracts/eligibility input owners;
- minimal accepted assembly under #431 canonical DB identity;
- exact source/test paths with no overlap against the active Zero-Relay owner.

Any need to add a new serialized task/route authority, scheduler, store, schema, retry/completion lifecycle, or duplicate Zero-Relay producer is `SCOPE_EXPANSION_REQUIRED` and requires a new R3 architecture decision.

## Current checkpoint

- #431 is ACCEPTED / MERGED / POST_MAIN_VERIFIED at `main@de8b037cfd78e4513656b726981caee05d5bb39b`.
- PR #434 first candidate `2ef328aff0c2df9fe4ffaa7a5308dde079107812` received independent R3 `CHANGES_REQUIRED` (P0/P1/P2/P3 = 0/0/1/4) for missed reuse seams and weaker trigger/migration wording.
- Repaired candidate `bdfc6857629d433fcbb2bb2cb05862c8999281dd` received independent R3 `PASS 0/0/0/0` for its internal reuse/failure model.
- After that rereview was dispatched, integrator recovery found a material cross-roadmap fact: WO397 preserves active Zero-Relay claims, Issue #215 is still OPEN, and prepared WO227 owns the same production-reachability + contract-producer gap.
- Current non-test repo census still finds no shipped caller for `ProductionElasticWorkerExecutor.execute_once`, no production `ParallelReadyNodeContract` constructor, and no production `GraphStore` writer.
- WO191/WO195/WO227 worktrees are clean but stale by roughly 223-265 current-main commits; no live ZRA-3 process exists. Their branches are evidence, not a safe current mutation base.
- This repair therefore adds the missing ownership fence. Source mutation remains blocked pending fresh exact-SHA rereview and #215/#433 ownership reconciliation.
- #429 remains dependency-required until #433 is accepted.


## 2026-09-21 session-rollover checkpoint — source gate re-pin required

This checkpoint supersedes only the stale *runtime/source-entry status* above; accepted architecture, ownership split, failure model, and acceptance requirements remain binding.

- Observed remote main at rollover: `75d9e96e46e15cc8ef647d12194d677657689bde`.
- The earlier R3 source claim in Issue #433 comment `5751797434` was bound to `d2ad5bdcac521d4803a84edabe56fb57eda9a2e8`; its mutation verdict does not survive head drift automatically.
- Fresh relevance diff from that base to the rollover main changes none of the frozen #433 implementation/test paths. The only related inspected drift is WO246 author-provenance wiring in `zcode_production_assembly.py`.
- Current main still has `ClaudeCodeJobBackend`, while `ClaudeCodeHarnessAdapter` rejects `PROJECT_MUTATION` as `HARNESS_MUTATION_NOT_READY`.
- Current main still has `SupervisedZCodeRunner` but no accepted `ZCodeJobBackend` that GraphDispatch can use as the generic job backend.
- Therefore the smallest truthful first LOCAL-USABLE slice is **explicit/manual READ_ONLY activation** through the accepted supervised Claude durable backend. Mutation-capable harness activation is a successor architecture/scope decision.
- The manual command consumes one caller-named existing graph/run/node and cross-checks all authority-bearing identities. It never chooses a successor and never implements automatic NEXT_READY.
- Fixed-pool only: no elastic worker provisioning in this slice.
- Required capability evidence fails closed; non-empty canonical TaskNode capability demand must not be inferred from runtime-type markers.
- No live installed database activation is authorized during implementation or review; migration/initialization behavior is proven on sacrificial databases first.
- Prior GLM-5.3-Flash source-scope assist was recovered as TERMINAL exit 0 and supported REUSE+WRAP/thin composition. It is advisory evidence, not review or acceptance authority.
- No #433 source writer or material GLM implementation dispatch was started before this deliberate chat rollover.
- Durable rollover claim/checkpoint: Issue #433 comment `5753493574`.

### Exact next safe action after session rotation

Fresh session must run canonical ENTRY/A-Faster recovery, fetch/re-pin actual `origin/main`, reconcile global delegated runs/WIP, and rerun collision/relevance checks. Only then may it create a new clean isolated R3 source worktree/claim for the frozen manual READ_ONLY activation scope and begin RED-first implementation. Automatic NEXT_READY remains #215-exclusive.
