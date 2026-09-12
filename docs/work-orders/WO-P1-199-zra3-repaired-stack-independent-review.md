# WO-P1-199 — Independent review of repaired ZRA-3 stack

Status: READY_FOR_INDEPENDENT_REVIEW / READ_ONLY_REVIEW_LANE
Date: 2026-09-11 (Asia/Bangkok)
Risk: R3 review gate; this lane itself is docs-only and must not mutate candidate source.
Owner: GPT-5.6 Sol integrator for packet/coordination only
Independent reviewer: GLM/ZCode or another non-author of the repaired exact SHAs
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo199-zra3-review`
Branch: `review/wo-p1-199-zra3-repaired-stack`
Base: `origin/main@46f90b329d4991211f5c8a26406f3aca2162e9a7`

## Exact review targets

Review exactly, not branch tips by recollection:

1. Parent Phase-A PR #263 candidate:
   - SHA: `e13155b9947c7b42f00853cc5583480741119531`
   - Original Phase A at `738ae0da8702080926e83a92dda2aef5a7830dba` was GLM-authored.
   - GPT independent review found two P1 defects, then GPT authored bounded repair commit `e13155b...`.
2. Stacked production-composition PR #269 candidate:
   - SHA: `0bf8f1ed088d234ec51e855cf4e067add5552da0`
   - Contains GPT-authored WO195 production composition plus a merge of the repaired parent.

Because GPT authored the repaired parent delta and WO195 production composition, GPT must not be the final independent acceptor of these exact SHAs.

## Review outcome

Return exactly one of:

- `ACCEPT_EXACT_SHAS`
- `CHANGES_REQUIRED`
- `BLOCKED_EVIDENCE`

Do not merge and do not modify either candidate branch.

## Parent review — required checks

Verify PR #263 exact SHA `e13155b...` against WO191:

1. diff from its predecessor `738ae0d...` is bounded to the two declared files;
2. direct successor observation set must be complete; partial `{B2}` for graph `A -> {B1,B2}` fails closed with `SUCCESSOR_OBSERVATION_INCOMPLETE`;
3. parent `TaskState.COMPLETE` with `completion_ref=None` fails closed with `PARENT_COMPLETION_EVIDENCE_MISSING`;
4. foreign graph-run/job identity still fails closed;
5. represented/RECOVERY_NEEDED successor semantics remain idempotent/no blind replay;
6. duplicate/restart/concurrent execution behavior remains bounded by durable GraphDispatch identity;
7. guard semantics remain unchanged in Phase A; no scheduler/lease/provider/retry/review authority is added;
8. observer accepts a completion-evidence projection but does not claim to authenticate its provenance itself;
9. verify the Phase-A integration tests no longer falsely state that direct JobStore transition is equivalent to GoalCloseout provenance;
10. run deterministic parent/related suite and hosted CI on the exact SHA.

Expected local integrator evidence before review: 290 tests passed for parent + related graph/lifecycle/ParallelReady suites; compile/diff/UTF-8 clean. Treat this as a claim to verify, not authority.

## Child review — required checks

Verify PR #269 exact SHA `0bf8f1e...` against WO195:

1. parent ancestry includes exact repaired parent `e13155b...`;
2. child conflict resolution did not drop the two parent P1 fixes;
3. `NextReadyProductionAssembly` loads durable graph/job truth rather than trusting caller-supplied graph state;
4. COMPLETE continuation requires the current durable COMPLETE transition event and non-empty canonical closeout evidence for the exact parent job;
5. evidence validation is structural authority binding, not represented as cryptographic proof against a malicious in-process writer;
6. production path never invents `ContinuationGuards(True, True, True, True)` to bypass mutation safety;
7. selection-only logic cannot be used through the mutating Phase-A executor without explicit guards;
8. selected node must have exact `ParallelReadyNodeContract` graph/run/node identity;
9. selected scheduler eligibility/readiness evidence is present before downstream call;
10. focused ready set contains at most one node; no ZRA-4 fan-out occurs here;
11. downstream production executor is called at most once per tick; no retry loop/watchdog is introduced;
12. downstream WAIT/RECOVERY_REQUIRED remain typed and do not retry in the same tick;
13. duplicate tick after durable successor representation becomes no-op/reconcile, not second physical dispatch;
14. provider/lease/dirty/head gates remain owned by existing production authorities and are revalidated downstream;
15. ZRA-3 batch ID is deterministic/versioned and derived from graph/run/selected GraphDispatch identity, not caller supplied;
16. no second scheduler/store/lease/provider/review/dispatch-journal authority is introduced;
17. human relay count on the composed accepted path remains zero;
18. run focused production suite + parent suite + relevant GoalCloseout/graph/ParallelReady/elastic/worker-candidate regressions and hosted CI on exact SHA.
19. prove a **real production construction/caller path** exists outside tests for the composed automatic NEXT READY seam. At minimum trace concrete source construction/use of `NextReadyProductionAssembly`, production creation of the required `ParallelReadyNodeContract`, and the downstream `ProductionElasticWorkerExecutor` (or the exact accepted equivalent after source drift).
20. tests, exported classes, or assembly objects with zero production caller do **not** satisfy automatic continuation. If repository-wide production-source tracing finds these only in definitions/tests, classify `P1 PRODUCTION_WIRING_GAP / CHANGES_REQUIRED`; do not return `ACCEPT_EXACT_SHAS` merely because deterministic tests pass.
21. any production caller must reuse existing graph/job/lease/provider/dispatch authorities; a new second scheduler/loop introduced only to make the call graph non-empty is itself a blocker.
22. verify durable work-order identity uniqueness against current `origin/main` and open stacked authority. PR #269 currently carries `docs/work-orders/WO-P1-195-zra3-production-composition.md` while `origin/main` already owns `WO-P1-195-zra2-phase-b-materializer.md`; unless this collision is reconciled to one unique canonical WO identity, report `P1 DUPLICATE_WORK_ORDER_ID / CHANGES_REQUIRED`.
23. a branch name or PR title may remain historical metadata, but no merge candidate may introduce a second canonical `WO-P1-195` document or ambiguous result/checkpoint namespace such as `runs/WO-P1-195/**` for a different task.

Expected local integrator claim: focused/related regressions were green in prior review, but GPT pre-review later reproduced both a production-wiring gap and a duplicate durable WO identity. Treat all as claims to verify; production reachability and authority-ID uniqueness are independent acceptance gates.

## Adversarial review prompts

Try to disprove the candidate with at least these attacks:

- partial direct-successor observations;
- COMPLETE with missing evidence;
- foreign graph run/job ID;
- malformed/foreign closeout evidence;
- missing or wrong-type node contract;
- contract GraphDispatchKey drift;
- missing eligibility for selected node;
- two READY siblings (must select/focus one only);
- represented sibling / RECOVERY_NEEDED sibling;
- duplicate tick after durable dispatch;
- downstream WAIT and RECOVERY_REQUIRED;
- reordered/repeated observation across restart;
- stale parent version/state between initial read and fact assembly;
- attempt to pass production selection into mutating executor without guards.

## Merge-order rule

If both exact SHAs are accepted:

1. PR #263 may merge first.
2. Re-pin main and PR #269 base/ancestry after parent merge.
3. Re-run or confirm hosted CI against the rebased/merge-resolved exact child candidate if its SHA changes.
4. Only then may PR #269 be accepted/merged.

Never merge child ahead of parent.

## Review result file

Write only review evidence under this review lane, preferably:

`runs/WO-P1-199/result.md`

Record:

- reviewed exact SHAs;
- commands/tests and outcomes;
- hosted CI states;
- P0/P1/P2 findings with exact file/symbol/reproducer;
- authority-duplication verdict;
- final `ACCEPT_EXACT_SHAS`, `CHANGES_REQUIRED`, or `BLOCKED_EVIDENCE`.

Do not edit PR #263/#269 source from this lane.
