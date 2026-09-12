# WO-P1-224 — GoalCloseout lease-release outcome truth gate

Status: PREPARED / READY_WHEN_NONOVERLAPPING_EXECUTOR_AVAILABLE / PHASE-D PREREQUISITE
Parent: WO-P1-205 / WO-P1-208 / Issue #214
Owner: GPT-5.6 Sol integrator
Preferred executor: ZCode GLM-5.3
Base: `origin/main@60aba770fd457d04f1e31040b9dfd7af3927f669`
Risk: R3 — closeout durable-state / external-effect authority

## 1. Objective

Repair one bounded latent authority defect in `GoalCloseoutExecutor` before Phase D is allowed to depend on lease-release closeout.

Current exact source behavior at the base:

- `CloseoutFoldPort.fold()` is fail-closed: only `FoldOutcome.completed is True` may be checkpointed.
- `LeaseReleasePort.release()` returns `LeaseReleaseOutcome(released, already_released)`.
- `GoalCloseoutExecutor.execute_next()` currently ignores `released` and unconditionally writes the lease-release checkpoint after any non-throwing return.
- Therefore `LeaseReleaseOutcome(released=False, already_released=False)` can create durable evidence that the exact lease was released even though the port did not confirm release.
- The current `tests/test_goal_closeout.py` fake always returns `released=True`; there is no RED case for the unconfirmed outcome.
- Repository search at this base finds no production construction/caller of `GoalCloseoutExecutor`; classify this as a **latent R3 authority defect / Phase-D blocker**, not a claimed live production incident.

This WO is intentionally narrow. It does not redesign GoalCloseout, leases, stores, outboxes, recovery, or Phase D.

## 2. Authority and dependency

This defect is independently source-proven and does not depend on WO208, WO225, WO226 or WO223/C1 source completion. It may run whenever a separate executor lane is genuinely free and a fresh non-overlap claim proves the exact `goal_closeout.py` / focused-test scope is unowned.

Current Phase-D fan-in is:

`(WO225 -> WO226 -> WO223/C1) + (WO208 + WO224) -> WO205 Phase D`

WO224 must not preempt an active critical lane on the same executor merely to reduce queue time. If only one ZCode lane is available, preserve the integrator's current critical-path ordering; if separate independent GLM capacity is proven, WO224 may execute in parallel because its mutable source scope is disjoint from WO225/WO226/WO223 and WO208 lab evidence scope.

GPT-5.6 Sol remains final R3 acceptance/merge authority.

## 3. Existing authorities to preserve

Reuse unchanged:

- `GoalCloseoutFacts`
- `plan_goal_closeout()`
- deterministic closeout checkpoint identities
- `GoalCloseoutExecutor`
- `CloseoutJobStorePort`
- `LeaseReleasePort`
- `LeaseReleaseOutcome`
- `CloseoutFoldPort` / `FoldOutcome`
- existing JobStore CAS/version-conflict behavior
- existing `RECOVERY_REQUIRED` and `RELOAD_REPLAN` semantics

Do not add a second store, journal, outbox, retry loop, lease state machine, or effect ledger.

## 4. Binding outcome semantics

The release port result is evidence, not decorative metadata.

For the existing two-boolean contract, current canonical `SQLiteWorkerLeaseStore.release()` is stronger than the loose dataclass shape: it emits exactly one of the two booleans as true.

1. `released=True, already_released=False` — confirmed successful release; checkpoint may proceed.
2. `released=False, already_released=True` — confirmed idempotent pre-existing release; checkpoint may proceed and detail should remain `ALREADY_RELEASED`.
3. `released=True, already_released=True` — **contract contradiction / unsupported authority shape**; fail closed as `RECOVERY_REQUIRED`, write no checkpoint, and do not infer release truth from it.
4. `released=False, already_released=False` — **not confirmed**; return typed `RECOVERY_REQUIRED` at `RELEASE_LEASE`, write no closeout checkpoint, perform no COMPLETE transition, and do not blind-retry inside the executor.

Recommended typed details: `LEASE_RELEASE_OUTCOME_CONTRADICTORY` for case 3 and `LEASE_RELEASE_NOT_CONFIRMED` for case 4, unless existing repository naming conventions require equivalent code-only names.

Do not weaken canonical WorkerLease semantics merely because `LeaseReleaseOutcome` is currently a permissive dataclass. If source archaeology later proves a distinct accepted producer legitimately emits another shape, stop for GPT adjudication before broadening acceptance.

## 5. RED-first requirements

Before source repair, add deterministic tests that fail on base behavior.

Required RED matrix:

1. `released=False, already_released=False` => `RECOVERY_REQUIRED`, stage `RELEASE_LEASE`, no release checkpoint.
2. the same unconfirmed outcome must never transition to COMPLETE.
3. `released=True, already_released=False` positive control still checkpoints.
4. `released=False, already_released=True` idempotent positive control checkpoints and reports `ALREADY_RELEASED`.
5. `released=True, already_released=True` => typed recovery/contradiction, no release checkpoint, no COMPLETE; canonical WorkerLease store never emits this pair.
6. confirmed release followed by JobStore checkpoint failure => `RECOVERY_REQUIRED / CHECKPOINT_AFTER_EFFECT_FAILED`; no second release call inside one executor invocation.
7. ACTIVE lease + exact release checkpoint already present remains `LEASE_RELEASE_CONTRADICTION` before calling the release port.
8. RELEASED lease without current exact release checkpoint remains recovery-required.
9. old-lease checkpoint does not satisfy a new lease.
10. version conflict semantics remain `RELOAD_REPLAN`, not retry.

At least test 1 must discriminate pre-repair from repaired behavior.

## 6. Implementation boundary

Expected mutable scope only:

- `src/a_conductor/goal_closeout.py`
- `tests/test_goal_closeout.py`
- this WO checkpoint/result evidence

Prefer the smallest repair in `GoalCloseoutExecutor.execute_next()`.

A small `LeaseReleaseOutcome` validation hardening is allowed only if RED evidence proves malformed non-boolean values are otherwise authority-bearing and the change remains backward compatible with accepted bool callers. Do not widen scope merely for style.

## 7. Forbidden scope

Without a separate GPT release, do not modify:

- job store implementation/schema
- WorkerLease store/authority
- scheduler/provider/admission code
- fold adapters
- Zero-Relay C0/C1 modules
- WO221/WO223 source
- GoalCloseout lifecycle/state machine beyond the exact result gate
- external runtime/processes/providers
- A-Wiki
- live DBs
- credentials/secrets

No merge, self-acceptance, or downstream Phase-D release by the executor.

## 8. Verification floor

After GREEN:

1. focused `tests/test_goal_closeout.py`;
2. related GoalCloseout/job-store/lease/recovery tests selected from actual imports/call paths;
3. at least one adversarial replay proving unconfirmed release never becomes a durable release checkpoint;
4. compile/import check for changed source;
5. `git diff --check`;
6. strict UTF-8 / no U+FFFD for changed text files;
7. added-line secret-shape scan;
8. scope audit: only allowed files;
9. full relevant regression justified by dependency graph;
10. freeze exact SHA and open/update a dedicated PR;
11. independent exact-SHA R3 review;
12. exact-head hosted CI;
13. GPT acceptance, merge, and post-main verification.

Do not rerun broad suites without a concrete reason.

## 9. Acceptance criteria

WO224 is acceptable only when:

- an unconfirmed lease-release outcome cannot create a durable release checkpoint;
- confirmed release and already-released positive paths remain correct;
- checkpoint failure after a confirmed effect remains recovery-required;
- no internal blind retry is introduced;
- no second lifecycle/store/journal is introduced;
- exact candidate tests and relevant regression pass;
- independent reviewer reports no P0/P1/P2 blocker;
- exact-head CI is green;
- GPT independently accepts the exact reviewed SHA.

## 10. Handoff

Executor result must durably record:

- exact base/head/branch/worktree;
- changed paths;
- RED command + failing test names;
- GREEN/regression/adversarial evidence;
- source-level root cause;
- whether any additional malformed-outcome hardening was necessary;
- independent-review state;
- hosted-CI state;
- exact next safe action.

Stop/checkpoint at the first external gate. Do not poll, wait, merge, or switch to another backlog item.
