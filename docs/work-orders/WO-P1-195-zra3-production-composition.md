# WO-P1-195 — ZRA-3 production continuation composition

Status: ACTIVE / STACKED_ON_WO191_PHASE_A / GPT-INTEGRATOR OWNED
Date: 2026-09-11 (Asia/Bangkok)
Risk: R3 — autonomous mutation composition boundary
Parent: WO-P1-191 / PR #263 Phase-A candidate `738ae0da8702080926e83a92dda2aef5a7830dba`
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo195-zra3-production`
Branch: `feat/wo-p1-195-zra3-production-composition`
Base: WO191 exact candidate `738ae0da8702080926e83a92dda2aef5a7830dba`
Merge dependency: WO191 Phase-A must be accepted first; this lane is a stacked successor and must not be merged ahead of its parent.
Architecture / implementation / exact-SHA review: GPT-5.6 Sol integrator, with independent GLM review required before final merge when provider access is healthy.

## Outcome

Turn the accepted ZRA-3 Phase-A deterministic NEXT READY selector into a truthful production composition boundary:

`durable GoalCloseout COMPLETE -> durable completion evidence -> graph readiness/representation -> select at most one successor -> existing scheduler/worker-supply/provider/lease/GraphDispatch execution -> durable result/reconcile`

No user prompt/result relay is allowed between those transitions.

This WO does **not** implement ZRA-4 fan-out. At most one successor may enter the production execution authority per tick.

## Why this successor exists

GPT exact-SHA review of WO191 `738ae0d...` found Phase A sound but not production-callable. The parent WO allowed only one pre-existing composition file; fresh tracing proved no single whitelisted file owned all required authorities without duplication. The parent therefore required a bounded successor rather than silent scope expansion.

Review evidence:

- Phase-A focused: 61 passed;
- graph/dispatch/ready/scheduler/lifecycle/parallel-ready/worker-candidate regressions: 179 passed;
- GoalCloseout: 81 passed;
- total reviewed local tests before this WO: 321 passed;
- no conflicting open PR owns the Phase-A source/test files.

## Independent-review repair closure (added 2026-09-11)

After WO195 activation, GPT-5.6 Sol independently re-ran WO191 and proved two P1 authority defects on exact parent SHA `738ae0da8702080926e83a92dda2aef5a7830dba`:

1. **Incomplete successor evidence fail-open** — for `A -> {B1, B2}`, supplying only the `B2` observation can still yield `DISPATCH_ONE/B2`. The planner must require an exact observation set for all direct successors before selection.
2. **Unproven parent completion fail-open** — a parent with `TaskState.COMPLETE` and `completion_ref=None` can still yield `DISPATCH_ONE`. Production continuation must require durable closeout completion evidence, and the pure Phase-A contract must not represent missing completion evidence as dispatch-authorized.

This stacked WO is explicitly authorized to repair these two findings in the smallest bounded parent files:

- `src/a_conductor/next_ready_continuation.py`
- `tests/test_next_ready_continuation.py`

plus the preferred new production-composition files below. The repair must be RED-first, preserve all previously-green semantics, and must not broaden scheduler/lease/provider/review authority.

## Existing authorities that MUST be reused

- `GoalCloseoutExecutor` is the accepted closeout authority for `TaskState.COMPLETE` after verification/review/fold/release conditions; because `SQLiteJobStore.transition` is a generic persistence seam, production continuation treats COMPLETE without canonical GoalCloseout completion evidence as unauthorized;
- `SQLiteJobStore.get_job/list_events` owns durable job state and completion `evidence_ref` history;
- `observe_next_ready_facts` + `plan_next_ready_continuation` own ZRA-3 parent/successor representation and one-successor selection semantics;
- `compute_ready_set` / `schedule_once` own graph readiness and scheduler policy;
- `ProductionElasticWorkerExecutor.execute_once` owns production worker supply observation, scheduler selection, provider authority/admission, Worker lease acquisition, optional elastic capacity, task materialization and execution through existing `ParallelReadyExecutor` / `GraphDispatch` authorities;
- `ParallelReadyNodeContract` owns per-node dispatch/lease/provider/task-packet binding;
- existing durable GraphDispatch job identity remains the replay/dedup boundary.

Do not create a second scheduler, lease store, provider semaphore, retry loop, review bus, completion store, or dispatch journal.

## Completion evidence closure — fixes WO191 review P2

Phase A carried `ParentCompletion.completion_ref` but did not consume it, and its observer set the field to `None`.

Production composition MUST recover the parent COMPLETE transition from `JobStore.list_events(parent_job_id)` and fail closed unless all are true:

1. current parent job is `TaskState.COMPLETE`;
2. event sequence is valid under the existing JobStore reader;
3. the terminal/latest state transition corresponding to the current COMPLETE state has `to_state == TaskState.COMPLETE`;
4. its `evidence_ref` is a non-empty bounded durable reference;
5. the event belongs to the exact `GraphDispatchKey(graph_id, graph_run_id, parent_node_id).job_id`;
6. completion evidence cannot come from a foreign graph run or foreign job;
7. no caller-supplied prose/digest may substitute for the durable event.

The composition may bind that real evidence reference into a replaced immutable `ParentCompletion`; it must not invent a digest.

## Production guard rule

Phase-A `ContinuationGuards` are safety assertions, not permission to bypass production checks.

WO195 MUST NOT pass unconditional truthy guard values merely to make the planner dispatch.

The production path must prove that every mutation-sensitive condition is either:

- directly derived from an existing authoritative observation, or
- delegated to an existing production authority that re-observes/revalidates it immediately before mutation.

In particular:

- dirty/head truth remains owned by production worker/worktree observations and lease/task binding;
- actual lease availability is decided atomically by the existing Worker lease broker;
- provider freshness/admission is decided by the existing provider authority/admission store;
- scheduler eligibility/worker supply is re-observed by `ProductionElasticWorkerExecutor`;
- a stale preflight can only degrade to WAIT/RECOVERY, never cause mutation.

If the Phase-A boolean guard shape cannot be composed truthfully without inventing state, stop and make the smallest explicit Phase-A contract adjustment in this stacked WO, with RED-first tests and no semantic weakening.

## Preferred new source scope

Prefer new-file composition:

- NEW `src/a_conductor/next_ready_production_assembly.py`
- NEW `tests/test_next_ready_production_assembly.py`

A narrowly justified change to `src/a_conductor/next_ready_continuation.py` + its existing test is allowed **only** if required to make delegated production guards truthful. Record the reason before editing.

Do not modify existing scheduler/lease/provider/GraphDispatch semantics.

## Suggested composition contract

The new assembly should accept trusted injected existing authorities and immutable execution inputs rather than creating stores internally. The minimum useful inputs are expected to include:

- durable job/event reader;
- `TaskGraph`, graph ID, graph-run ID, parent node ID;
- `ParallelReadyNodeContract` mapping;
- `ProductionElasticWorkerExecutor` (or a narrow protocol matching its one-shot production call);
- existing `SchedulePolicy`;
- provider inflight snapshot/authority inputs required by the executor;
- runtime kind and existing elastic policy;
- existing scheduler eligibility evidence;
- running write sets if applicable.

The composition should derive any batch identity deterministically from canonical graph-run + selected dispatch identity rather than accepting an arbitrary caller-chosen string when provider admission requires a batch ID.

A recommended ZRA-3 batch identity is versioned and deterministic, e.g. a SHA-256 over canonical `graph_id`, `graph_run_id`, and selected `GraphDispatchKey.job_id`. Do not create a new provider admission authority.

## One-tick algorithm

1. Re-read exact parent durable job by canonical GraphDispatchKey.
2. Re-read durable parent events and bind the exact COMPLETE transition evidence.
3. Reconstruct graph representation/readiness from durable jobs.
4. Decide at most one direct successor with the accepted Phase-A planner.
5. If no dispatch is authorized, return typed NOOP/WAIT/RECONCILE; do not call production execution.
6. Require an exact production contract for the selected node and reject graph-run/job/task identity drift.
7. Create a focused ready set containing exactly that selected node while preserving the original ready check evidence.
8. Derive deterministic ZRA-3 batch identity.
9. Call the existing `ProductionElasticWorkerExecutor.execute_once` once for the focused node.
10. Map its EXECUTED/WAIT/RECOVERY result to a typed continuation result without retry loops.
11. On the next tick, durable GraphDispatch representation prevents duplicate dispatch.

## Required RED-first matrix

Before GREEN prove failures/controls for at least:

1. parent not COMPLETE -> no production executor call;
2. COMPLETE job with missing completion event/evidence -> typed fail closed;
3. foreign/incorrect COMPLETE event -> typed fail closed;
4. stale/malformed completion evidence reference -> typed fail closed;
5. no successor ready -> no executor call;
6. represented successor -> no executor call;
7. recovery successor -> reconciliation outcome, no executor call;
8. multiple ready successors -> exactly one focused node, never fan-out;
9. selected node missing production contract -> typed recovery/fail closed;
10. contract GraphDispatchKey differs from selected graph/run/node -> typed fail closed;
11. deterministic batch identity stable across restart/repeated observation;
12. focused executor is called at most once per tick;
13. downstream WAIT -> no retry in same tick;
14. downstream RECOVERY_REQUIRED -> no retry in same tick;
15. downstream fixed-pool/elastic success -> typed EXECUTED;
16. duplicate tick after durable dispatch representation -> no second executor call;
17. worker dirty/head drift in downstream authority -> WAIT/RECOVERY and zero mutation success;
18. lease conflict -> downstream WAIT/RECOVERY, no second lease authority;
19. provider admission/generation drift -> WAIT/RECOVERY, no blind retry;
20. human relay count on the composed accepted path = 0.

## Verification floor

At minimum:

- new focused production-assembly tests;
- parent `tests/test_next_ready_continuation.py`;
- `tests/test_goal_closeout.py`;
- `tests/test_graph_ready.py`;
- `tests/test_graph_scheduler.py`;
- `tests/test_graph_dispatch.py`;
- `tests/test_parallel_ready_execution.py`;
- relevant production elastic-capacity tests;
- relevant worker-candidate assembly tests;
- compile/import;
- `git diff --check`;
- strict UTF-8 / no U+FFFD;
- added-line secret scan;
- exact changed-scope audit;
- hosted CI on the frozen SHA.

## Forbidden

- live Worker/process/tunnel mutation;
- provider credential/key mutation;
- direct ZCode config/DB mutation;
- manual task replay;
- parallel fan-out >1 node;
- second retry/watchdog/scheduler/lease/provider/review authority;
- destructive Git operations;
- `CURRENT-WORK.md`, handoff/COLLAB/PROJECT-PLAN mutation;
- merge/release before parent and this exact SHA pass independent review.

## Result contract

`runs/WO-P1-195/result.md` must record:

- parent/base exact SHA;
- candidate exact SHA;
- changed files;
- completion-event evidence design;
- production guard delegation/revalidation map;
- deterministic batch identity rule;
- RED and GREEN evidence;
- duplicate/restart/WAIT/RECOVERY proofs;
- test totals;
- scope/encoding/secret/diff checks;
- parent PR status;
- independent review verdict;
- exact next safe action.

Final state must be one of:

- `CANDIDATE_FROZEN_FOR_REVIEW`
- `BLOCKED_PARENT`
- `BLOCKED_AUTHORITY`
- `RECOVERY_REQUIRED`
- `NO_SAFE_NEXT_ACTION`
