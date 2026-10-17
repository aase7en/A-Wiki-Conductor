/goal

Execute WO-P1-227 only after full ZRA-2 is accepted/post-main and Issue #215 explicitly releases WO227.

PRIMARY REPO:
A:\GitHub\A-Wiki-Conductor

PRIMARY WORK ORDER:
docs/work-orders/WO-P1-227-zra3-production-activation-and-identity-reconciliation.md

ROLE:
You are ZCode GLM-5.3 MAX acting as the bounded long-shift implementation/research executor. GPT-5.6 Sol owns architecture, trust-boundary adjudication, final acceptance, merge and release.

MASTER OUTCOME:
Reconcile the repaired ZRA-3 stack into one unique durable WO227 authority and make automatic NEXT READY reachable from a real production control-plane/application path without adding a second scheduler/store/lease/provider/review authority.

Do NOT start source mutation before the release gate.

## G0 — cold-start / release / ownership gate

1. Read `00-AGENT-ENTRY.md` -> `PROJECT-GRAPH.yaml` -> `AGENTS.md`.
2. Read `DEFECT_LESSONS.md` before touching `src/a_conductor/`.
3. Read WO227 in full.
4. Re-pin `origin/main`, PR #263, PR #269, PR #274, Issue #215 and full ZRA-2 acceptance state.
5. Verify full ZRA-2 is accepted/merged/post-main and Issue #215 explicitly names WO227/ZRA-3 as NEXT_READY.
6. Recover every active claim/worktree/open PR touching proposed source/application-entry scope.
7. Use a fresh isolated implementation worktree/branch; never mutate protected root checkout.
8. Publish exact owner/base/head/worktree/mutable-scope/forbidden-scope/non-overlap claim before source mutation.
9. If any authority/dirty/ownership fact is UNKNOWN, checkpoint `SAFE_TO_MUTATE_WO227=NO` and STOP.

Do not assume historical exact SHAs are still current if Git/GitHub disproves them.

## G1 — exact stack + reuse archaeology

Trace current/reconciled equivalents of:

- repaired `next_ready_continuation.py` Phase-A seam;
- `NextReadyProductionAssembly`;
- `GraphStore` / graph reader;
- `SQLiteJobStore` / job events / completion evidence;
- `ParallelReadyNodeContract` and its real producer (if any);
- `WorkerCandidateAssembler`;
- `WorkerLeaseBroker` / lease store;
- provider snapshot/observation/admission authority;
- `build_sqlite_parallel_ready_executor()`;
- `build_sqlite_elastic_worker_capacity_coordinator()`;
- `ProductionElasticWorkerExecutor`;
- `GraphDispatchCoordinator`;
- actual top-level application/control-plane/service entrypoints that run bounded work.

Produce compact table:

`seam | exact symbol/path | production caller? | authority | REUSE/WRAP/EXTEND | gap | mutable?`

Fresh GPT evidence to reproduce, not blindly trust:

- exact historical child `0bf8f1e...` had no non-test callers of `NextReadyProductionAssembly`, ZRA-3 `ParallelReadyNodeContract` construction or `ProductionElasticWorkerExecutor`;
- lower-level ParallelReady/Elastic factories existed but also had no production callers;
- current main already owns canonical `WO-P1-195-zra2-phase-b-materializer.md` while PR #269 introduced another canonical ZRA-3 WO195.

If current source already has accepted equivalent production wiring, classify REUSE and checkpoint before duplicating it.

## G2 — reconcile durable WO identity first

The final candidate must have one unambiguous canonical work-order authority.

Required:

- preserve accepted ZRA-2 `WO-P1-195-zra2-phase-b-materializer.md` unchanged;
- ZRA-3 production reconciliation authority is `WO-P1-227`;
- no second canonical ZRA-3 `# WO-P1-195` work-order document may enter main;
- update active ZRA-3 source/test authority annotations from WO195 to WO227 only where they identify the current WO;
- all new ZRA-3 result/checkpoint evidence goes under `runs/WO-P1-227/**`;
- preserve historical commit/PR provenance without treating historical WO195 strings as current mutation authority.

Write deterministic checks that detect duplicate canonical WO IDs in the candidate.

## G3 — RED first: production reachability

Before GREEN wiring, write tests/probes proving the actual gap.

Minimum:

- candidate has no accepted production path when the activation hook is disconnected;
- a real non-test application/control-plane entry constructs/reaches the ZRA-3 activation after repair;
- definition/export/test-only construction is rejected as insufficient evidence;
- production activation invokes `NextReadyProductionAssembly.execute_once()` at most once per bounded invocation;
- downstream `ProductionElasticWorkerExecutor.execute_once()` at most once;
- no same-tick retry/watchdog loop.

The production-reachability test must fail if the real production construction/call is removed. Avoid source-string-only tests that can pass while the product never calls the seam.

## G4 — contract producer truth

Trace who constructs `ParallelReadyNodeContract` for real READY nodes.

If an accepted producer exists, REUSE it.

If no producer exists, add the smallest thin assembler allowed by WO227, taking every fact from existing authoritative stores/observations. It may not own policy, scheduling or durable state.

RED cases must include:

- foreign graph/run/node;
- stale project/work-order/operation identity;
- stale provider generation/endpoint/security/requirement;
- stale TaskPacketFile/hash;
- stale lease worktree/branch/HEAD;
- stale HarnessDispatch;
- caller-prose override attempts.

If truthful production contract construction requires a new store/policy engine, checkpoint `DESIGN_GAP` and STOP.

## G5 — minimal production activation

Implement the thinnest real production construction/caller over existing authorities.

Conceptual flow:

```text
accepted bounded production entry/tick
 -> current GraphStore + JobStore observations
 -> current node/provider/task/worker contract assembly
 -> NextReadyProductionAssembly.execute_once
 -> one focused successor
 -> existing ProductionElasticWorkerExecutor
 -> existing ParallelReadyExecutor / GraphDispatch / lease / provider
 -> typed EXECUTED | WAIT | RECOVERY_REQUIRED | NOOP
```

Rules:

- no new scheduler;
- no new durable store;
- no independent retry loop;
- at most one focused successor for ZRA-3;
- WAIT/RECOVERY propagate without same-tick retry;
- duplicates/restarts use existing durable identities;
- no ZRA-4 multi-lane fan-out;
- production caller must be actually reachable outside tests.

If the only candidate hook is a broad UI/desktop/event-loop redesign, checkpoint exact evidence and STOP for GPT scope expansion rather than smuggling it into this WO.

## G6 — completion provenance attacks

Re-run prior repaired P1 attacks and extend them to the real production caller:

- incomplete direct-successor observations -> fail closed;
- COMPLETE without exact completion evidence -> fail closed;
- stale/foreign completion event/ref -> fail closed;
- parent graph/run/job/version drift -> fail closed;
- caller cannot fabricate `ContinuationGuards(True,...)` to bypass authority;
- direct JobStore COMPLETE without accepted closeout provenance never authorizes continuation.

The activation hook must not weaken repaired Phase-A semantics.

## G7 — downstream authority/adversarial campaign

Attack the composed production path:

- no workers / capacity WAIT;
- provider unavailable/quota/generation drift;
- provider admission conflict/recovery;
- lease busy/existing/recovery;
- dirty/head/worktree drift;
- malformed/unsupported downstream result;
- duplicate invocation before/after durable successor representation;
- restart after uncertain dispatch;
- exception between observation and downstream execution;
- stale `contracts_by_node` vs current graph;
- source/test mutation probe proving the production-wiring test is non-vacuous.

No sleeps for correctness when deterministic barriers/store fixtures can be used.

## G8 — regression + authority fence

Run the WO227 verification ladder plus current task-relevant suites.

Explicitly prove:

- only one canonical ZRA-2 WO195 remains;
- ZRA-3 current authority is WO227;
- no second scheduler/store/lease/provider/review/retry authority;
- no direct COMPLETE authority added;
- ZRA-4 fan-out remains absent;
- human relay count on the composed continuation path is zero.

Run compile/diff/UTF-8/secret/scope audits.

## G9 — freeze / hosted CI

Freeze coherent candidate:

- commit exact source/tests/docs/evidence;
- push branch;
- Draft PR only;
- record exact base/head/diff paths;
- trigger/observe hosted CI once.

If CI nonterminal, checkpoint `BLOCKED_EXTERNAL_CI` and STOP; do not poll.
If CI fails, inspect once and repair only if clearly inside released scope.

## G10 — independent R3 review handoff

Because ZRA-3 history includes GPT-authored repair/composition and this implementation may be GLM-authored, final acceptance requires a non-author independent exact-SHA reviewer.

Review must independently prove:

- durable WO identity uniqueness;
- real non-test production reachability;
- completion provenance;
- bounded one-successor/no-retry semantics;
- existing downstream scheduler/provider/lease/dispatch authority reuse;
- duplicate/restart safety;
- no hidden ZRA-4 fan-out;
- exact hosted CI.

GLM must not merge or self-accept.

## Stop gates

Checkpoint and STOP on:

- ZRA-2 gate not satisfied;
- Issue #215 release absent;
- PR #263/#269 material source drift requiring architecture re-adjudication;
- current main already contains equivalent accepted production wiring;
- overlap/claim conflict;
- unexplained dirty state;
- need for broad application/UI/runtime redesign;
- need for new scheduler/store/lease/provider authority;
- need to modify accepted ZRA-2 semantics;
- need to begin ZRA-4;
- live credential/runtime/provider operation;
- external CI/review/GPT acceptance/merge gate;
- UNKNOWN authority.

Use durable checkpoints across context rollover. Do not ask the human to relay intermediate state.

Final handoff must record exact current/base/head/worktree/branch, reconciled ancestry, unique WO227 authority proof, production call graph, contract-producer path, RED/GREEN/adversarial/regression counts, changed paths, findings, CI/review state and exact next safe action. Do not merge.
