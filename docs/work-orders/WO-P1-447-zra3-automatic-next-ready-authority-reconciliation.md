# WO-P1-447 — ZRA-3 automatic NEXT_READY authority reconciliation

Identity schema: GITHUB_ISSUE_V1
Issue: #447

Status: PREPARED / DESIGN_GAP / SOURCE HOLD
Parent authority: Issue #215 / claim `GPT1-ZRA3-PREFLIGHT-001`
Predecessor completed: Issue #214 / WO-P1-205
Accepted activation dependency: Issue #433 / RUNTIME-ACT-1
Integrator / architecture owner: GPT-5.6 Sol
Repository: A-Wiki-Conductor
Topology: CONTROL_PLANE_ONLY
Risk: R3 — autonomous continuation / durable authority / replay safety
Prepared base: `0ce82be15355bf3af782cd488b54d77c475d285b`
Governance worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo447-zra3-authority`
Governance branch: `docs/wo-p1-447-zra3-authority`

## 1. Objective

Close the ZRA-3 roadmap node with the thinnest safe production behavior:

`accepted + fully closed parent -> re-observe durable graph/run truth -> expose newly READY successor(s) -> select at most one successor through accepted policy -> invoke the accepted production activation path once`

Human relay on the automatic path must be zero.

ZRA-3 changes continuation transport/composition only. It must not create a second scheduler, graph lifecycle, job lifecycle, review authority, execution store, provider authority, lease authority, retry engine, completion authority, or generic activation front door.

## 2. Dependency release status

ZRA-2 is no longer a blocker.

Accepted predecessor evidence:

- WO-P1-205 exact reviewed candidate: `cf4760a00dc212eca4a6b2d15be728c66b5ea332`;
- merge/current-main SHA at this WO preparation: `0ce82be15355bf3af782cd488b54d77c475d285b`;
- exact-head CI `35549943412`: SUCCESS;
- independent R3 review: PASS, P0/P1/P2/P3 = 0/0/0/3;
- post-main CI `35550896410`: SUCCESS on Windows/macOS/Ubuntu, including packaging and frozen Setup E2E;
- Issue #214: CLOSED / COMPLETE / RELEASED / POST_MAIN_VERIFIED.

Therefore:

`ZRA2_PREREQUISITE = SATISFIED`

This does **not** itself grant ZRA-3 source mutation authority.

## 3. Canonical ownership split

The latest Issue #215 <-> Issue #433 bilateral split is binding.

### Issue #433 / RUNTIME-ACT-1 owns

- the generic/manual explicitly invoked runtime activation primitive;
- authoritative `ParallelReadyNodeContract` production composition;
- production reachability through existing worker/lease/provider/admission/ParallelReady/GraphDispatch authorities;
- explicit activation request validation and exact task/worktree/provider/model authority checks.

### Issue #215 / WO447 owns

- automatic accepted-completion -> NEXT_READY trigger/policy;
- successor selection semantics;
- exact parent-completion/provenance validation required before continuation;
- one-tick automatic continuation/reconcile behavior;
- no-blind-replay behavior for duplicate/running/ambiguous successor state;
- the thinnest composition that **consumes** the accepted #433 activation primitive.

WO447 must not build a second generic activation primitive or a second `ParallelReadyNodeContract` producer.

## 4. Historical ZRA-3 material — research only

Historical work is evidence, not current mutation authority:

- PR #263 / `feat/wo-p1-191-zra3-next-ready` / historical head `e13155b9947c7b42f00853cc5583480741119531`;
- PR #269 / `feat/wo-p1-195-zra3-production-composition` / historical head `0bf8f1ed088d234ec51e855cf4e067add5552da0`;
- PR #274 / `review/wo-p1-199-zra3-repaired-stack` / historical head `d44f55711a48d29223024949efd8852e9be505d8`;
- PR #310 / old WO227 docs / historical head `a7ffb47c7b38d55d5687dce0675001f5aeef0bcb`.

A-Faster recovery on 2026-09-21 found all four historical worktrees clean and no matching live executor. Old WO191/WO195 run artifacts are terminal historical results.

Do not cherry-pick or port those branches merely because they once passed tests. Their assumptions predate accepted WO205, WO433 and current work-order identity policy.

Useful historical concepts may be re-derived against current main only.

## 5. Work-order identity reconciliation

New canonical work-order files with numeric IDs below 381 are forbidden unless already present in the frozen legacy exception set.

Neither old proposed `WO-P1-215-...` nor `WO-P1-227-...` ZRA-3 files are in that frozen set.

Therefore:

- Issue #215 remains the parent roadmap/claim authority;
- this current GitHub-backed child Issue #447 owns the canonical active work order;
- the only current work-order identity is **WO-P1-447 / Issue #447**;
- old WO191/WO195/WO199/WO227 names remain historical evidence aliases only;
- do not alter the frozen legacy identity fixture to make old names mergeable.

## 6. Current-main completion -> READY truth

Current main already contains the durable state transition chain needed before successor activation:

1. accepted WO205 Phase-D requires store-backed ACCEPTED review/relay before closeout;
2. existing `ProductionGoalCloseoutFacade.next_stage()` delegates bounded closeout to existing `GoalCloseoutExecutor`;
3. existing `GoalCloseoutExecutor.execute_next()` is the sole final authority that transitions a durable job to `TaskState.COMPLETE`;
4. `graph.lifecycle_bridge.project_job_state()` maps `TaskState.COMPLETE -> TaskNodeStatus.DONE`;
5. `project_graph_node_states()` re-observes every graph/run node through exact `GraphDispatchKey` job identity;
6. `compute_ready_set()` marks a TODO node READY only when predecessors are DONE/SKIPPED and no running write-set conflict blocks it.

ZRA-3 must consume this re-observed truth. It must never accept caller-supplied `COMPLETE` or a stale in-memory “success” boolean as continuation authority.

## 7. Accepted activation truth to reuse

Current main contains accepted WO433 `runtime_activation.py`.

`activate_production_runtime(...)` already owns the production composition needed to run one explicit task through:

- canonical database identity;
- graph loading;
- exact READY re-check;
- task-contract authority;
- provider snapshot/generation/endpoint/model authority;
- authorized worker candidates;
- existing job/execution/lease stores;
- existing `GraphDispatchCoordinator`;
- existing `ParallelReadyExecutor`;
- existing `ProductionElasticWorkerExecutor`.

`RuntimeActivationService.activate()` deliberately narrows the already-computed ready set to the **operator-named node** and states that READY siblings are excluded because that path is not ZRA-3.

That explicit/manual primitive is the integration dependency. ZRA-3 may wrap/consume it; ZRA-3 may not fork its authority.

## 8. Confirmed current design gap

Automatic successor *readiness* is provable, but automatic successor *activation identity* is not yet provable.

Accepted `RuntimeActivationRequest` requires:

- `graph_id`;
- `graph_run_id`;
- `node_id`;
- `runtime_kind`;
- `project_root`;
- `task_contract_ref`;
- `task_packet_path`;
- `provider_id`;
- `model_id`;
- `effort_level`.

Current canonical `TaskNode` persists:

- id/objective;
- expected outputs;
- read/write sets;
- worker requirement;
- model requirement;
- priority/timeout/retry-policy ref;
- planning status;
- artifacts.

Current `GraphStore` stores only that TaskNode JSON plus graph edges/runs/events. No graph-level task-contract/provider activation registry was found.

Current-main searches also found:

- no graph-layer `task_contract_ref`;
- no graph-layer `work_order_ref`;
- no canonical task-contract registry/class that maps a READY node to an activation request;
- `task_packet_path` enters production activation from the explicit operator request;
- `model_requirement` currently carries legacy workspace/worker binding semantics in graph analysis and is not an activation provider/model authority;
- `artifacts` has no accepted activation-identity schema.

Therefore:

`SUCCESSOR_SELECTION_AUTHORITY = AVAILABLE`

`SUCCESSOR_ACTIVATION_IDENTITY_AUTHORITY = NOT_PROVEN`

`SAFE_TO_MUTATE_ZRA3_SOURCE = NO`

No source implementation may infer missing identity from objective text, filenames, artifact ordering, branch conventions, “latest” files, or caller prose.

## 9. Reuse-before-build decision tree

Before source release, classify the missing successor activation identity seam in this order:

### REUSE

Prove an already-accepted durable authority exists on then-current main that binds each schedulable node to all required activation inputs.

If proven, name the exact source/store/schema/API and use it directly.

### WRAP

If an accepted authority already stores the complete identity but exposes no suitable reader, add only a thin read-only adapter with no new durable state.

### EXTEND

If current accepted graph/task authority is missing a bounded subset of fields, propose the smallest extension to an existing authority.

An EXTEND proposal must specify:

- definition home;
- exact persisted identity;
- producer and consumer;
- version/migration behavior;
- immutable/currentness semantics;
- how task-contract SHA and task-packet SHA/path are bound;
- provider/model/effort authority;
- graph/run/node identity;
- branch/worktree/HEAD identity interaction;
- replay and stale-binding rejection;
- no duplicate store or lifecycle.

EXTEND remains design-only until independently reviewed and explicitly released.

### NEW

A new registry/store is forbidden by default. If archaeology proves no safe REUSE/WRAP/EXTEND path, checkpoint `DESIGN_DECISION_REQUIRED` rather than creating a shadow activation registry.

## 10. Successor selection semantics

ZRA-3 owns “which successor is attempted now”, but it must reuse existing readiness/scheduling policy rather than fork a second scheduler.

Required invariants:

- re-read current graph and durable graph-run job states immediately before selection;
- derive READY from existing `compute_ready_set()`;
- preserve existing priority/topological/lexical and worker/identity/conflict policy wherever selection is delegated to the existing scheduler/executor;
- at most one successor physical attempt per ZRA-3 invocation;
- no same-tick fan-out — ZRA-4 owns bounded parallel fan-out;
- no hand-written “first list item” policy when existing scheduler policy is applicable;
- if zero READY nodes exist, return WAIT/NO_READY without mutation;
- if multiple READY nodes cannot be reduced using accepted policy without creating a second contract producer/scheduler, fail closed and resolve the composition design first.

## 11. Parent completion / provenance gate

Automatic continuation may start only after current durable parent state proves the accepted closeout boundary.

At source design time, the continuation seam must show how it binds at minimum:

- exact graph_id / graph_run_id / parent node_id;
- exact parent GraphDispatch job identity;
- durable parent job state == COMPLETE;
- accepted current candidate/closeout provenance where required by the existing completion authority;
- no unresolved recovery/version conflict;
- no stale parent observation between completion proof and successor re-observation.

Do not create a second completion certificate or boolean latch. Consume existing durable job/closeout truth.

## 12. One-tick and replay semantics

One invocation must be bounded:

1. observe exact parent/graph/run durable state;
2. if parent is not durably COMPLETE, refuse/wait;
3. re-project graph-run states;
4. compute READY;
5. derive one authorized successor only when current activation identity authority is complete;
6. call the accepted activation primitive at most once;
7. return the downstream typed outcome;
8. stop.

Forbidden:

- internal polling loop;
- same-tick retry;
- blind retry after timeout/UNKNOWN;
- volatile “already continued” flags;
- second physical dispatch when existing GraphDispatch/job/execution identity represents the successor;
- automatic retry after RECOVERY_REQUIRED;
- ZRA-4 multi-successor fan-out.

Restart/replay must rely on existing durable GraphDispatch/job/execution dedup/recovery authority.

## 13. Initial design verification matrix

Before any source-release verdict, prove with current-main references/tests or new design tests:

### Authority

1. parent completion comes from durable existing closeout/job truth;
2. successor READY comes from current graph/run projection + existing ReadySet;
3. every required RuntimeActivationRequest field has a named durable authority;
4. no field is inferred from prose/convention/latest-file lookup;
5. provider/model/effort binding cannot drift between selection and activation;
6. task contract/packet identity cannot cross-wire between graph nodes.

### Replay / boundedness

7. one invocation reaches accepted activation at most once;
8. zero READY -> no activation;
9. ambiguous/unknown durable state -> no activation;
10. running/already represented successor -> no duplicate physical dispatch;
11. WAIT -> no same-tick retry;
12. RECOVERY_REQUIRED -> no same-tick retry;
13. crash/restart uses durable identity.

### Ownership boundaries

14. no second scheduler;
15. no second generic activation primitive;
16. no second ParallelReadyNodeContract producer;
17. no second graph/job/lease/provider/execution/review/closeout store;
18. no ZRA-4 fan-out;
19. no mutation of accepted WO205 semantics;
20. no mutation of accepted WO433 semantics unless a separately accepted dependency repair is required.

## 14. Source-release gate

Source mutation remains blocked until all are true:

1. this WO is merged/accepted as current governance authority;
2. current main is re-pinned after the governance merge;
3. Issue #215 confirms the current child WO447 source release;
4. historical PR #263/#269/#274/#310 are rechecked only for reusable ideas, never used as integration bases;
5. exact successor activation identity authority is proven as REUSE/WRAP or an EXTEND design is separately accepted;
6. exact implementation files are frozen;
7. owner/claim/non-overlap are published;
8. fresh isolated source worktree is created from then-current main;
9. `DEFECT_LESSONS.md` is read at that source gate;
10. RED-first matrix is frozen;
11. no concurrent owner controls the selected source/test hotspot.

Until then:

`SAFE_TO_MUTATE_ZRA3_SOURCE = NO`

## 15. Expected source shape after future release

This section is non-authoritative until the source-release gate passes.

Preferred shape is a thin automatic-continuation composition that:

- consumes existing closeout/job/graph/run truth;
- uses existing READY/scheduler policy;
- obtains an authoritative activation request for the chosen successor;
- invokes accepted WO433 activation exactly once;
- contains no durable state of its own.

Do not assume historical `next_ready_continuation.py` or `next_ready_production_assembly.py` survives current-main design unchanged.

A future source claim should normally be smaller than the historical repaired stack because WO433 already owns generic activation composition.

## 16. Independent R3 design review

Because this is an R3 trust-boundary change, freeze the governance candidate and obtain an independent exact-SHA review before source release.

Reviewer must challenge:

- whether the activation identity gap is real;
- whether an existing authority was missed;
- whether REUSE/WRAP/EXTEND classification is correct;
- whether the Issue #215 <-> #433 split is preserved;
- whether successor selection accidentally creates a second scheduler;
- whether one-tick/replay semantics prevent blind duplicate dispatch;
- whether the proposed source-release gate is sufficient;
- whether stale historical PR assumptions leaked into current authority.

PASS requires P0/P1/P2 = 0.

## 17. Governance mutation scope

Current governance lane may mutate only:

`docs/work-orders/WO-P1-447-zra3-automatic-next-ready-authority-reconciliation.md`

Forbidden in this lane:

- all `src/a_conductor/**`;
- all tests/fixtures;
- `CURRENT-WORK.md`;
- `handoff.md`;
- `COLLAB.md`;
- historical PR branches/files;
- SunDayRemoteMCP;
- live databases/providers/workers/credentials.

## 18. Closeout / handoff contract

At every material boundary preserve:

- Issue #447 + parent #215;
- current main/base/candidate SHA;
- exact worktree/branch;
- source-mutation verdict;
- confirmed activation-identity authority or exact design gap;
- historical evidence disposition;
- independent-review run pointer;
- CI state when a PR exists;
- exact next safe action.

Governance acceptance does not equal source release unless Section 14 is explicitly satisfied.

## 19. Current verdict

At prepared base `0ce82be15355bf3af782cd488b54d77c475d285b`:

- ZRA-2 prerequisite: **SATISFIED**
- #215 <-> #433 ownership split: **BOUND**
- historical ZRA-3 lanes: **TERMINAL / RESEARCH ONLY**
- successor readiness authority: **PROVEN**
- accepted explicit activation primitive: **PROVEN**
- successor activation identity authority: **NOT PROVEN**
- source mutation: **HOLD**
- governance/design review: **READY**

Exact next safe action:

freeze this one-file governance candidate, run deterministic identity/hygiene checks, obtain independent R3 design review, and reconcile any finding before deciding whether a source lane can be released.
