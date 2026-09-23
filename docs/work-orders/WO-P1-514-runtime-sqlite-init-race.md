# WO-P1-514 — RuntimeActivation concurrent SQLite initialization race

Status: ACTIVE / R3 / CONTROL_PLANE_ONLY
Issue: #514
Parent blocker: #498 / PR #512 hosted acceptance
Reuse class: EXTEND existing SQLite authority stores; no new store/lock service

## Lane binding

- Authority repo: `A:\GitHub\A-Wiki-Conductor`
- Execution repo: same repo
- Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo514-sqlite-init-race-r1`
- Branch: `fix/wo-p1-514-sqlite-init-race-r1`
- Base/head at claim: `19ee92ca3888ce563ac743cfcca7707334cc8189`
- Mutable slot: one A-Faster implementation lane
- Independent review slot remains separate
- Existing ambiguous clean worktree `A:\GitHub\_worktrees\A-Wiki-Conductor-wo514-sqlite-init-race` is forbidden and left untouched.

## Problem statement

Hosted Windows CI for PR #512 failed twice on unrelated non-PR tests. The second
failure was:

`tests/test_runtime_activation.py::test_runtime_authority_concurrent_initialization_converges_on_one_database`

with `sqlite3.OperationalError: database is locked` originating from
`SQLiteJobStore.initialize()` around its schema DDL / metadata initialization,
wrapped as `JOB_STORE_INITIALIZE_FAILED` and then
`RUNTIME_AUTHORITY_INITIALIZATION_RECOVERY_REQUIRED`.

The first rerun failure was a different process-lifecycle test, so #498 itself
does not own this defect. No further blind hosted reruns are allowed.

## Risk / failure model

R3 because this changes concurrency behavior of durable project authority state.

Potential failure classes to distinguish before repair:

1. JobStore DDL-vs-DDL lock contention.
2. JobStore metadata INSERT/COMMIT contention after DDL.
3. Cross-store ordering contention between JobStore / ExecutionStore / lease /
   provider-store initialization.
4. Hosted filesystem/SQLite timing amplification rather than a logical race.
5. Busy-timeout exhaustion that would merely be masked by increasing timeout.

A repair must preserve #322 job-store schema-row idempotency and #401 execution-
store initialization semantics. Do not add a second store, global retry loop,
process-global mutex, or hidden scheduler/authority.

## Phase A — diagnosis only

Mutable scope:
- this Work Order only.

All production/test source is READ-ONLY.

Required evidence:

1. Re-run the existing concurrent RuntimeActivation test locally in bounded
   repetition to measure natural reproducibility.
2. Build temporary external/sacrificial SQLite probes outside tracked repo files
   that can deterministically hold/release SQLite locks and identify which
   JobStore initialization statement fails.
3. Compare JobStore and ExecutionStore initialization transaction shape and
   busy-timeout behavior.
4. Determine the smallest truthful repair boundary.

Phase A exit requires a durable root-cause checkpoint on Issue #514 and this WO.
Only then may the integrator explicitly widen mutation scope.

## Phase B — regression

Allowed only after Phase A exit.

Expected initial test scope:
- `tests/test_runtime_activation.py`
- optionally one focused JobStore test file only if root cause is JobStore-local.

RED must fail deterministically without depending on hosted timing.

## Phase C — repair

Allowed only after RED root cause is proven.

Expected production scope must be the minimum owner:
- `src/a_conductor/job_store.py` if JobStore-local, or
- another existing store/activation module only if Phase A proves it owns the
  failure.

No timeout-only fix. No broad retry. No process-global lock. Preserve durable
schema/version validation and fail-closed errors.

## Verification

R3 minimum:

- deterministic RED reproducer;
- targeted repair tests;
- existing `test_runtime_activation.py`;
- accepted #322/#401 initialization regressions;
- adversarial concurrent multi-initializer stress;
- py_compile + diff-check + exact-scope/secret scan;
- frozen exact SHA;
- independent read-only review;
- exact-head hosted CI;
- post-main verification.

## Replay / stop rules

- RUNNING/UNKNOWN external execution is never redispatched.
- Repeated material failure twice without new evidence enters root-cause mode.
- SQLite lock ambiguity is not solved by blind retry.
- Stop only for real authority/ownership/safety/authorization gates.
