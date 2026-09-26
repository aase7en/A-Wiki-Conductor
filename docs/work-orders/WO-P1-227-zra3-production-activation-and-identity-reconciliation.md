# WO-P1-227 — ZRA-3 production activation + durable work-order identity reconciliation

Status: PREPARED / HOLD UNTIL FULL ZRA-2 ACCEPTED + ISSUE #215 EXPLICIT RELEASE
Parent: WO-P1-191 / historical PR #263 / historical PR #269 / WO-P1-199 / Issue #215
Integrator/architecture owner: GPT-5.6 Sol
Preferred implementation executor after release: ZCode GLM-5.3 MAX
Repository: A-Wiki-Conductor
Prepared base: `60aba770fd457d04f1e31040b9dfd7af3927f669`
Risk: R3 — autonomous continuation / durable authority identity / live production wiring

## 1. Why this WO exists

The repaired ZRA-3 stack is a strong deterministic library seam but is not yet an accepted live automatic NEXT READY path.

Pinned historical stack under review:

- repaired parent PR #263 exact source head: `e13155b9947c7b42f00853cc5583480741119531`;
- stacked production-composition PR #269 exact source head: `0bf8f1ed088d234ec51e855cf4e067add5552da0`;
- independent-review packet PR #274; current review packet is separately maintained by WO199.

GPT-5.6 Sol read-only pre-review found two independent blockers that must be reconciled together rather than hidden behind green tests.

### P1-A — production reachability gap

At exact child `0bf8f1e...`, production-source tracing finds definitions but no concrete non-test caller/construction for:

- `NextReadyProductionAssembly`;
- the ZRA-3 path's `ParallelReadyNodeContract` construction/use;
- `ProductionElasticWorkerExecutor`.

Existing lower-level factories such as:

- `provider_runtime_assembly.build_sqlite_parallel_ready_executor()`;
- `elastic_worker_capacity.build_sqlite_elastic_worker_capacity_coordinator()`;
- `GraphStore.load_graph()`;
- `SQLiteJobStore` / durable job/event authority;
- `WorkerCandidateAssembler`;

are reusable building blocks, but the exact child has no accepted production composition that constructs and calls the whole chain automatically.

Definitions, exports and tests are not live production wiring.

### P1-B — duplicate durable work-order identity

Current `origin/main` already owns canonical:

`docs/work-orders/WO-P1-195-zra2-phase-b-materializer.md`

PR #269 independently introduces:

`docs/work-orders/WO-P1-195-zra3-production-composition.md`

and its source/tests/result namespace refer to `WO-P1-195` / `WO195` / `runs/WO-P1-195/**` for a different task.

This is a duplicate durable authority identity. Branch/PR titles do not disambiguate canonical WO identity.

WO227 becomes the unique successor authority for reconciling the ZRA-3 composition. It does not rewrite historical Git history; it prevents the conflicting ZRA-3 WO195 identity from entering main as a second canonical authority.

## 2. Hard release gate

Do not mutate candidate/product source merely because this packet exists.

`SAFE_TO_MUTATE_WO227=YES` only when all are durably true:

1. full ZRA-2 is GPT-accepted, merged and post-main verified, including its current exact predecessor chain;
2. Issue #214 records ZRA-2 COMPLETE/accepted and no open recovery/authority blocker remains that changes continuation semantics;
3. Issue #215 explicitly publishes WO227 / ZRA-3 production reconciliation as `NEXT_READY`;
4. PR #263 and PR #269 exact current heads are re-pinned; do not assume creation-time SHAs remain current;
5. WO199 independent-review evidence is read and its findings reconciled;
6. current `origin/main` is re-pinned and all relevant ZRA-3 dependencies are compared against the historical stack;
7. a fresh implementation worktree/branch is created from then-current main or an explicitly approved integration base;
8. exact mutable scope/owner/claim/non-overlap is published before source mutation;
9. no active owner controls the same source/test/application-entry paths;
10. dirty state is CLEAN or fully explained/protected.

If any item is UNKNOWN:

`SAFE_TO_MUTATE_WO227=NO`

Do not preempt ZRA-2 to start this implementation.

## 3. Reuse-before-build architecture

Classify each seam using `REUSE -> WRAP -> EXTEND`; NEW authority is forbidden unless GPT explicitly expands scope.

### Existing authorities to reuse

- `next_ready_continuation.py` repaired decision/fact/continuation semantics;
- `next_ready_production_assembly.py` child composition seam where still valid after rebase/reconciliation;
- `graph.store.GraphStore` as durable graph reader;
- `SQLiteJobStore` / existing durable job events and COMPLETE evidence;
- existing GraphDispatch identity and coordinator;
- `ParallelReadyNodeContract` and `assemble_parallel_ready_tasks()`;
- `WorkerCandidateAssembler` and canonical worker/lease evidence;
- `WorkerLeaseBroker` / `SQLiteWorkerLeaseStore`;
- provider configuration/observation/admission authority;
- `build_sqlite_parallel_ready_executor()` where applicable;
- `build_sqlite_elastic_worker_capacity_coordinator()` where applicable;
- `ProductionElasticWorkerExecutor` where applicable;
- existing scheduler `schedule_once()` and ReadySet authority;
- existing supervised/ZCode execution route;
- existing recovery/duplicate/result authority;
- accepted GoalCloseout completion provenance from the completed ZRA-2/main lineage.

### Forbidden duplicate authorities

Do not add a second:

- scheduler;
- graph store;
- job store;
- continuation state machine;
- retry/watchdog loop;
- WorkerLease store/broker;
- provider admission store/semaphore;
- GraphDispatch journal;
- review authority;
- execution store;
- completion/closeout authority.

A new **composition/application service** is allowed only as a thin constructor/caller over existing authorities, with no independent durable state.

## 4. Work-order identity reconciliation

Before product source changes, repair the candidate authority identity in the integration lane.

Required canonical state:

- ZRA-2 retains canonical `WO-P1-195-zra2-phase-b-materializer.md` and any accepted `runs/WO-P1-195/**` meaning;
- ZRA-3 production activation uses canonical **WO-P1-227**;
- no second `# WO-P1-195` document for ZRA-3 may enter main;
- any ZRA-3 source docstrings/comments/tests that state the work-order authority must be updated to `WO-P1-227` when they materially identify the active WO;
- ZRA-3 durable result/checkpoint namespace becomes `runs/WO-P1-227/**` for new execution evidence;
- historical PR #269 / old commits may still mention WO195 as historical provenance, but current merge candidate must contain one unambiguous canonical authority.

Do not rename the existing accepted ZRA-2 WO195.

## 5. Production reachability acceptance rule

ZRA-3 is not accepted merely because `NextReadyProductionAssembly.execute_once()` passes tests.

The final candidate must prove a real non-test production call graph such as:

```text
accepted application/control-plane entry or bounded runtime tick
  -> existing durable graph/job observations
  -> existing contract/task/provider/worker observations
  -> NextReadyProductionAssembly.execute_once(...)
  -> ProductionElasticWorkerExecutor.execute_once(...)
  -> existing ParallelReadyExecutor / GraphDispatch / lease / provider authority
  -> one bounded successor attempt
```

Exact entrypoint is implementation-owned after archaeology.

The production caller must be bounded and externally triggerable by an accepted control-plane/runtime path. A helper that is itself never constructed/called outside tests does not close the gap.

If current source has no suitable existing application entrypoint, implement the smallest thin activation service and one narrow construction hook. If this requires a broad desktop/UI/runtime-loop redesign, persist exact evidence and STOP for GPT scope adjudication.

## 6. Contract production / ParallelReadyNodeContract truth

Fresh archaeology must identify who owns construction of every selected node's `ParallelReadyNodeContract`.

No caller may fabricate a contract from caller prose or stale cached state merely to satisfy `NextReadyProductionAssembly`.

At minimum prove the contract binds current authoritative:

- graph_id / graph_run_id / node_id through `GraphDispatchKey`;
- project/work-order/operation refs;
- dispatch gate;
- WorkerLeaseRequest;
- provider profile + observation + endpoint + security + generation;
- provider execution requirement;
- exact HarnessDispatch;
- exact TaskPacketFile;
- attempt budget;
- candidate branch/HEAD/worktree identity.

If there is no accepted producer for these contracts, WO227 may add a thin **assembler** only if every input comes from existing authorities and no second store/policy engine is introduced. Otherwise checkpoint `DESIGN_GAP`.

## 7. One-tick / no-loop semantics

WO227 production activation must remain bounded:

- one invocation observes current durable state;
- at most one focused successor is selected for ZRA-3;
- downstream executor is called at most once per invocation;
- WAIT stays WAIT;
- RECOVERY_REQUIRED stays recovery;
- no same-tick retry;
- no hidden polling/watchdog loop;
- duplicate/restart relies on existing durable GraphDispatch/execution identities;
- ambiguous prior execution never causes a second physical dispatch.

ZRA-4 owns bounded multi-lane fan-out. WO227 must not smuggle ZRA-4 into ZRA-3.

## 8. Completion provenance

The repaired stack's COMPLETE evidence requirements remain mandatory.

Continuation may begin only from the current durable parent job whose COMPLETE transition/evidence is bound to the exact parent graph/run/job and accepted closeout path.

Do not accept:

- raw caller `TaskState.COMPLETE`;
- direct test-style JobStore transition without canonical closeout evidence;
- stale completion_ref/evidence_ref;
- a completion event for another job/graph run/candidate;
- missing current completion evidence.

The production activation caller must not weaken these repaired checks.

## 9. Initial mutable scope after release

Do not assume this exact scope survives future main drift. Re-pin before claim.

Expected bounded scope may include:

- the ZRA-3 production-composition files from PR #269 as reconciled onto the approved integration base;
- NEW/renamed canonical `docs/work-orders/WO-P1-227-zra3-production-activation-and-identity-reconciliation.md` authority;
- focused ZRA-3 production tests;
- at most one thin new production composition/activation module;
- at most one existing application/control-plane construction hook if archaeology proves it is the correct owner;
- minimal source comments/docstrings/result-path updates necessary to remove the duplicate WO195 authority.

Read-only archaeology may span graph/job/provider/lease/worker/scheduler/desktop/control-plane modules.

Forbidden without new GPT scope release:

- ZRA-2 accepted source changes;
- scheduler algorithm redesign;
- WorkerLease semantics/schema;
- provider schema/admission semantics;
- GraphDispatch lifecycle semantics;
- GoalCloseout semantics;
- execution-store schema;
- ZRA-4 fan-out;
- A-Wiki source;
- live credentials/runtime mutation.

## 10. RED-first campaign

Write failing or discriminating tests before production wiring changes.

### Identity / governance

1. repository candidate cannot contain two canonical `WO-P1-195` work-order documents for different tasks;
2. ZRA-3 current authority/result namespace is WO227;
3. historical provenance does not become current mutation authority;
4. ZRA-2 WO195 remains unchanged.

### Production reachability

5. test/proof that the accepted production entry actually constructs/reaches the continuation activation path;
6. mutation probe deleting/disconnecting the production call must fail that test;
7. an assembly class used only by tests is insufficient;
8. production tick calls `NextReadyProductionAssembly` at most once;
9. production tick calls downstream elastic/parallel executor at most once.

### Durable input authority

10. wrong graph/run/node contract rejected;
11. missing/foreign `ParallelReadyNodeContract` rejected;
12. stale parent job version/state rejected;
13. parent COMPLETE missing exact completion evidence rejected;
14. stale/foreign completion evidence rejected;
15. stale branch/HEAD/worktree candidate evidence rejected downstream;
16. provider generation/security/requirement drift fails closed downstream;
17. lease/project/worktree/branch/HEAD drift fails closed downstream.

### Replay/recovery

18. duplicate invocation after durable successor representation does not dispatch twice;
19. running/ambiguous successor remains WAIT/RECOVERY, not new dispatch;
20. downstream WAIT does not retry in same tick;
21. downstream RECOVERY_REQUIRED does not retry in same tick;
22. exception/malformed downstream result fails recovery, not success;
23. restart/re-observe uses durable identity, not volatile boolean guards.

### Boundaries

24. no second scheduler/store/lease/provider/review authority;
25. at most one successor per ZRA-3 tick;
26. no ZRA-4 parallel fan-out;
27. zero human relay on the composed automatic path.

## 11. Verification ladder

After GREEN:

1. focused repaired parent tests;
2. focused production-assembly tests;
3. new production-reachability/activation tests;
4. graph/store/lifecycle bridge tests justified by imports;
5. worker candidate + WorkerLease tests;
6. provider/ParallelReady/elastic worker tests;
7. GoalCloseout provenance regression;
8. duplicate/restart/fault campaign;
9. `python -m compileall -q` on changed source;
10. diagnostics / `git diff --check`;
11. strict UTF-8 / no U+FFFD;
12. changed-scope audit;
13. added-line secret-shape scan;
14. hosted exact-head CI;
15. independent exact-SHA R3 review by a non-author.

A green unit suite without production reachability evidence is not acceptance.

## 12. Independent review / authorship

GPT authored material portions of the repaired parent/production child history and therefore must not be the sole final independent reviewer of those exact source semantics.

WO227 implementation may be GLM-authored after release, but final R3 acceptance still requires an independent reviewer that did not author the candidate, followed by GPT/integrator acceptance/merge authority.

No executor may self-merge/self-accept.

## 13. Stop gates

Checkpoint and STOP after the current atomic safe step on any:

- ZRA-2 not fully accepted/post-main;
- Issue #215 has not explicitly released WO227;
- PR #263/#269 source drift changes the repair strategy materially;
- current main already contains an accepted equivalent live production wiring (then classify REUSE and reconcile rather than duplicate);
- overlapping owner/claim;
- unexplained dirty state;
- required source scope expansion beyond one bounded activation/composition hook;
- need for a new scheduler/store/lease/provider authority;
- need to alter ZRA-2 or ZRA-4 semantics;
- live credential/runtime action;
- hosted CI external gate;
- independent review / GPT acceptance / merge / post-main gate;
- UNKNOWN authority.

Do not poll external gates. Do not jump to ZRA-4 while ZRA-3 is blocked.

## 14. Durable handoff

At freeze, persist:

- current main/base/head/branch/worktree;
- exact reconciled ancestry from repaired parent/child;
- canonical WO227 identity and proof duplicate WO195 is absent from the merge candidate;
- exact production call graph / construction path;
- exact contract producer path;
- RED/GREEN/fault/regression evidence;
- changed files;
- P0/P1/P2/P3 findings;
- hosted CI state;
- independent-review task pointer;
- exact next safe action.

GLM implementation claim is evidence only, never acceptance.
