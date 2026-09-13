# WO-P1-191 — ZRA-3 automatic NEXT READY continuation

Status: READY_FOR_GLM_IMPLEMENTATION / GPT-INTEGRATOR CLAIM
Date: 2026-09-11 (Asia/Bangkok)
Risk: R3
Parent: WO-P1-155 Zero-Relay Accelerator
Canonical preflight: GitHub Issue #215 / `GPT1-ZRA3-PREFLIGHT-001`
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo191-zra3`
Branch: `feat/wo-p1-191-zra3-next-ready`
Bootstrap base: `origin/main@46f90b329d4991211f5c8a26406f3aca2162e9a7`
Implementation owner: ZCode / GLM-5.3 MAX under this exact packet
Architecture, trust-boundary, exact-SHA acceptance, merge and release: GPT-5.6 Sol integrator
Execution packet: `docs/prompts/GLM-WAVE11-20H-ZRA3-CRITICAL-PATH.md`
Result destination: `runs/WO-P1-191/result.md`
Checkpoint destination: `runs/WO-P1-191/checkpoint.md`
Scope-selection evidence: `runs/WO-P1-191/scope-selection.json`

## User outcome

Remove the next remaining human-relay step after accepted ZRA-2:

`accepted + durably completed task -> reconcile authoritative state -> expose newly READY successor -> dispatch that successor automatically`

The user must not need to copy a new prompt, copy a result back, or type `continue` merely because one accepted external-agent task finished.

Primary metric: **human relay actions per accepted external-agent task = 0**.

## Current factual gate

At activation:

- `origin/main = 46f90b329d4991211f5c8a26406f3aca2162e9a7`;
- PR #258 / WO-P1-165 ZRA-2 is merged to `origin/main`;
- Issue #215 already owns the ZRA-3 preflight identity and forbids duplicate continuation engines;
- the older Issue #215 body still says implementation was blocked on ZRA-2; actual Git now proves that dependency is cleared;
- A-Conductor is the OWNER of `next_ready_continuation`; A-Wiki is CONSUMER under `docs/contracts/a-wiki-a-conductor-integration.md`;
- open source PRs inspected at activation do not overlap the initial ZRA-3 source/test scope below;
- the protected root checkout is dirty/stale and MUST NOT be used for implementation.

All embedded state is a bootstrap observation only. ZCode must re-pin actual Git/GitHub/runtime/claim state before mutation.

## Reuse-before-build

REUSE existing authorities; do not create substitutes:

- `TaskGraph`, graph READY/frontier analysis and scheduler semantics;
- `GraphDispatchCoordinator` and `GraphDispatchKey` durable dispatch identity;
- `ParallelReadyExecutor` / worker candidate assembly where composition requires them;
- existing WorkerLease and provider admission authorities;
- existing durable job state/recovery semantics;
- `GoalCloseout` as completion/continuity authority;
- WO165 ZRA-2 exact task/result/review identity;
- WO123 Loop Engineer stable task/status/result protocol;
- existing ContinuityGuard / GoalCloseout / single-writer projection rules.

Classification: **REUSE + THIN COMPOSITION EXTENSION**.

No second scheduler, task graph, job store, lease store, retry engine, review lifecycle, provider store, or continuity store is allowed.

## Core invariants

1. Reviewer prose, provider exit 0, or a truthy result is not sufficient to advance the graph.
2. The parent must be durably accepted/verified/closed under existing completion authority before continuation.
3. One completion transition may dispatch at most one selected successor in ZRA-3.
4. Duplicate ticks/observations are idempotent no-ops or reconcile to the same durable identity.
5. A successor already completed, running, offered, reconciled, or otherwise durably represented must never be respawned blindly.
6. UNKNOWN, timeout, ambiguous side effect, dirty worktree, HEAD drift, claim/lease conflict, stale provider admission, or missing identity fails closed.
7. A foreign task/result/completion identity cannot advance another graph run.
8. Restart/recovery must reconstruct behavior from durable authority, not process memory.
9. Continuation must preserve existing dependency/barrier semantics; it does not mark blocked nodes READY itself.
10. Human prompt/result relay is not part of the successful execution path.
11. No broad process kill, secret access, live provider mutation, live DB mutation, or Worker fleet mutation belongs to this WO.
12. Implementation author may self-test and self-audit but may not count that as independent acceptance review.
13. GLM may commit/push only this branch; GLM must not merge or release.
14. GPT-5.6 Sol reviews the frozen exact SHA before any merge.

## Mutation gate and allowed scope

Before source mutation ZCode MUST read `DEFECT_LESSONS.md`, re-pin the branch/worktree/HEAD/dirty state, inspect open PR file overlap, and record `SAFE_TO_MUTATE=YES` in `runs/WO-P1-191/checkpoint.md`.

### Always allowed tracked files

- `docs/work-orders/WO-P1-191-zra3-next-ready.md`
- `docs/prompts/GLM-WAVE11-20H-ZRA3-CRITICAL-PATH.md`

### Phase A — new-file-only core

Preferred initial mutable scope:

- NEW `src/a_conductor/next_ready_continuation.py`
- NEW `tests/test_next_ready_continuation.py`

Phase A should implement the smallest deterministic continuation decision/coordinator seam while keeping existing scheduler/lease/dispatch authority external and injected.

### Phase B — one production composition seam

After Phase A is green, ZCode may select **at most one** existing production composition file from this whitelist, only if needed to make the accepted continuation callable by production code:

- `src/a_conductor/graph/lifecycle_bridge.py`
- `src/a_conductor/lifecycle_coordinator.py`
- `src/a_conductor/lifecycle_assembly.py`
- `src/a_conductor/parallel_ready_execution.py`

It may select the matching existing test file for that one seam:

- `tests/test_graph_lifecycle_bridge.py`
- `tests/test_lifecycle_coordinator.py`
- `tests/test_lifecycle_assembly.py`
- `tests/test_parallel_ready_execution.py`

Before the first edit to an existing file, write `runs/WO-P1-191/scope-selection.json` with:

- chosen file and test;
- why new-file-only composition is insufficient;
- current exact HEAD;
- open-PR overlap recheck;
- proof no other active claim owns that file;
- expected call path;
- rollback/minimality note.

Do not edit more than one existing production file and its matching test under this WO. If more is genuinely required, stop that expansion, preserve the Phase-A candidate, and write a bounded successor packet instead of silently widening scope.

### Explicit forbidden scope

- `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`, `PROJECT-PLAN.md`;
- A-Wiki repository mutation;
- provider DB/schema or provider credential/secret handling;
- Worker lease semantics;
- scheduler/TaskGraph semantics;
- review authority semantics;
- tunnel/Worker/process runtime mutation;
- unrelated open PR/worktree files;
- broad refactors or cleanup;
- force push, rebase, reset, clean, stash-and-forget, branch deletion;
- merge/release.

## Required RED-first matrix

At minimum prove failures before implementation for:

1. parent not durably complete -> no successor dispatch;
2. review accepted but GoalCloseout incomplete -> no dispatch;
3. parent task/result/graph-run identity mismatch -> typed fail closed;
4. no newly READY successor -> deterministic no-op;
5. exactly one newly READY successor -> exactly one dispatch attempt;
6. multiple READY successors -> deterministic ZRA-3 selection or typed policy block; never accidental fan-out (fan-out belongs to ZRA-4);
7. duplicate continuation tick -> no duplicate execution;
8. process restart with same durable identity -> no duplicate execution;
9. prior dispatch UNKNOWN/timeout/ambiguous -> RECOVERY/RECONCILE, never blind retry;
10. successor already RUNNING/COMPLETE/durably represented -> no respawn;
11. foreign completion cannot unlock/dispatch successor;
12. graph dependency/barrier still blocked -> no dispatch;
13. dirty worktree -> no mutation dispatch path;
14. HEAD drift -> fail closed;
15. lease/claim conflict -> fail closed;
16. provider/admission not fresh/authorized -> fail closed;
17. malformed/stale task/result digest identity -> fail closed;
18. crash after durable dispatch record but before caller sees response -> restart reconciles, no duplicate;
19. crash before durable dispatch record -> safe retry decision is explicit and evidence-backed;
20. successful continuation needs no human prompt/result copy-paste.

Every adversarial test needs a positive control that proves the intended valid path still works.

## Implementation phases

### Phase 0 — recover and bind

- read universal entry + project graph + AGENTS + this WO + WO155/WO165 + Issue #215;
- inspect actual main/branch/HEAD/dirty/worktrees/open PR overlap;
- inspect authority contract for `next_ready_continuation`;
- read `DEFECT_LESSONS.md` before source edits;
- checkpoint mutation verdict.

### Phase 1 — architecture trace

Produce a concise call/authority map in the checkpoint:

`durable accepted completion -> GoalCloseout/continuity truth -> graph state -> READY selection -> lease/admission gate -> GraphDispatch identity -> execution result/reconcile`

Identify exactly which existing authority owns each transition. New code may compose, not duplicate.

### Phase 2 — RED Phase A

Add the adversarial/positive-control tests to the new focused test file and prove the expected RED state before implementation.

### Phase 3 — GREEN Phase A

Implement the smallest pure/injected coordinator/state decision seam in the new source file. Avoid filesystem/network/subprocess/GitHub I/O in the pure core.

### Phase 4 — composition selection

Determine whether production already has a clean caller seam. If a single existing composition file is necessary, record scope-selection evidence and edit only that file + its matching test.

### Phase 5 — progressive verification

Run focused tests, then relevant graph/lifecycle/GoalCloseout/parallel-ready suites, then adversarial/restart tests. Do not run broad suites repeatedly without a changed hypothesis.

### Phase 6 — freeze

- self-review exact diff;
- strict UTF-8/no U+FFFD;
- `git diff --check`;
- no secrets/credential-like additions;
- verify changed scope exactly allowed files;
- commit and push the frozen candidate;
- record exact SHA and test evidence to `runs/WO-P1-191/result.md`;
- do not merge.

### Phase 7 — useful remaining capacity

If the ZRA-3 candidate is frozen before the GLM session limit:

- do read-only adversarial review of the candidate and add tests/fixes only within the same allowed scope when deterministic evidence finds a defect;
- prepare a concise independent-review checklist for GPT;
- shape ZRA-4 Issue #216 read-only failure matrix and smallest future packet;
- inspect Worker/PowerShell WO156 only read-only for reusable resilience evidence if time remains;
- do not start unrelated roadmap features.

## Verification floor

Required before GLM declares `CANDIDATE_FROZEN`:

- focused `tests/test_next_ready_continuation.py` all green;
- matching production composition test green if Phase B used;
- `tests/test_goal_closeout.py` relevant/full file green;
- relevant `tests/test_graph_ready.py`, `test_graph_scheduler.py`, `test_graph_dispatch.py`, `test_graph_lifecycle_bridge.py`, `test_parallel_ready_execution.py` based on touched call path;
- adversarial duplicate/restart/UNKNOWN/identity tests green;
- compile/import check for touched source;
- `git diff --check` pass;
- strict UTF-8/no U+FFFD pass;
- changed-scope audit pass;
- credential-pattern added-line scan pass;
- clean worktree after final commit/push.

Hosted CI and independent exact-SHA review are GPT/integrator acceptance gates; GLM does not self-accept them.

## Long-run checkpoint discipline

The companion `/goal` packet may run for a very long session. Time/token capacity is a ceiling for useful work, never a target for filler.

Checkpoint at least:

- after recovery/claim re-pin;
- after RED matrix;
- after Phase-A green;
- before/after any Phase-B existing-file edit;
- after any material defect/repair;
- before context compaction/model session rollover;
- before provider/session limit;
- at frozen candidate.

A blocked sub-step is not a reason to end the session if another read-only task inside this WO is safe and useful.

## Result contract

`runs/WO-P1-191/result.md` must include:

- exact repo/worktree/branch/base/final SHA;
- actual changed files;
- selected composition seam or `NEW_FILE_ONLY`;
- RED evidence;
- GREEN/final verification commands and results;
- identity/replay/restart findings;
- defects found and fixes made;
- unresolved P0/P1/P2/P3 risks;
- open-PR/claim overlap recheck;
- secret/scope/encoding/diff checks;
- exact independent-review checklist;
- ZRA-4 readiness delta;
- exact next safe action.

Final machine-readable status must be one of:

- `CANDIDATE_FROZEN_FOR_GPT_REVIEW`
- `BLOCKED_AUTHORITY`
- `BLOCKED_DEPENDENCY`
- `RECOVERY_REQUIRED`
- `NO_SAFE_NEXT_ACTION`

Do not report `DONE` merely because time elapsed.

## Acceptance gate

GPT-5.6 Sol may accept/merge only after:

1. frozen exact SHA exists;
2. deterministic verification is reproducible;
3. exact diff/scope is reviewed;
4. independent R3 review has no unresolved P0/P1 findings;
5. hosted CI required for the risk tier passes on the reviewed SHA;
6. no ownership/claim drift exists;
7. post-merge reality and continuity are reconciled.

Until then this WO is not COMPLETE.
