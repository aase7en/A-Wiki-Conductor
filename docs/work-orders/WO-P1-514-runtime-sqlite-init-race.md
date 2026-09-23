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

## Phase A root-cause checkpoint — 2026-09-23

Diagnosis completed without tracked source/test mutation.

Evidence:
- existing concurrent RuntimeActivation test under natural local timing: `12/12 PASS`;
- sacrificial external probe reduced the existing store busy-timeout to 1 ms
  without changing tracked code and ran four concurrent initializers over one
  fresh authority database for 20 iterations;
- result: `41` failure events, of which `37` were the exact hosted chain
  `RuntimeActivationError -> JOB_STORE_INITIALIZE_FAILED ->
  sqlite3.OperationalError(database is locked)` at JobStore DDL;
- remaining failures included ExecutionStore initialization/read and another
  SQLite read-lock path, proving this is a multi-store initialization window,
  not a JobStore schema-version UNIQUE race;
- SQL traces showed multiple threads interleaving JobStore `CREATE TABLE`
  statements while peers advanced into ExecutionStore/provider/lease phases;
- control probe serializing only the RuntimeActivation multi-store
  initialization assembly under the same 1 ms lock pressure: `30/30 PASS`,
  `0` failures.

Root cause: same-process callers stampede the same idempotent multi-store
schema-initialization assembly. Individual stores remain the schema owners;
simultaneous DDL/read phases create avoidable SQLite schema/write-lock
contention. Increasing `busy_timeout` would mask the stampede rather than
remove it.

Phase B/C scope is now explicitly widened to:
- `tests/test_runtime_activation.py`
- `src/a_conductor/runtime_activation.py`
- this Work Order

Everything else remains read-only.

Repair boundary:
- add deterministic RED coverage that forces the contention condition;
- serialize only RuntimeActivation authority-store initialization in-process;
- add no durable lock/store/schema/task authority;
- add no retry loop and do not increase timeout;
- operational store reads/writes remain concurrent;
- existing SQLite busy-timeout remains the cross-process contention fallback;
- preserve #322/#401 store semantics and public error codes.

## Phase B RED checkpoint — 2026-09-23

Deterministic regression is now RED before production repair:

`test_runtime_authority_initialization_serializes_same_process_schema_pressure`

The test leaves the provider schema pre-initialized, shortens only JobStore's
test connection busy timeout to 1 ms, and makes the first JobStore initializer
hold an external SQLite `BEGIN EXCLUSIVE` lock for 50 ms while peer
RuntimeActivation initializers enter. Current code deterministically raises
`RUNTIME_AUTHORITY_INITIALIZATION_RECOVERY_REQUIRED`.

This reproducer isolates the same-process initialization stampede without
changing production timeouts or depending on hosted timing.

Implementation handoff contract:
- only `src/a_conductor/runtime_activation.py`,
  `tests/test_runtime_activation.py`, and this WO may mutate;
- serialize only the RuntimeActivation multi-store initialization assembly;
- no JobStore/ExecutionStore/WorkerLeaseStore/provider-store mutation;
- no timeout increase, retry loop, new schema, durable lock service, or task
  authority;
- preserve public error codes and existing store ownership;
- run the RED test first, then the existing concurrency test and directly
  related runtime/store initialization regressions.

## Phase C repair / verification checkpoint — 2026-09-23

The deterministic RED regression was repaired at the RuntimeActivation assembly
boundary only.

Implementation:
- added one process-local startup initialization lock in
  `runtime_activation.py`;
- `_initialize_runtime_authority_stores()` acquires that transient lock and
  delegates to an unlocked helper containing the previously-existing store
  initialization/read-verification sequence;
- no JobStore, ExecutionStore, WorkerLeaseStore or provider-store code changed;
- no timeout changed;
- no retry loop, durable lock record, schema, scheduler, task/claim authority or
  provider authority was added;
- operational store reads/writes remain outside this synchronization boundary;
- this only removes the proven same-process schema-initialization stampede.
  Existing SQLite locking/busy-timeout semantics remain responsible for
  cross-process contention.

Verification:
- deterministic pressure regression + existing four-way concurrent init:
  `2 passed`;
- full `tests/test_runtime_activation.py`: `33 passed`;
- store regressions
  `test_job_store.py + test_execution_store.py + test_worker_lease.py +
  test_provider_config_store.py`: `177 passed`;
- deterministic pressure regression repeated 12 times: `0` failures;
- `py_compile`: PASS;
- `git diff --check`: PASS;
- exact changed scope: this WO + `runtime_activation.py` +
  `test_runtime_activation.py`;
- added-line credential/session/share-URL scan: PASS.

A GLM-5.3 MAX implementation attempt was admitted after the RED checkpoint but
never entered model execution (0 input/0 output, no production mutation). It is
classified as interrupted/no-model-progress rather than a code/model failure;
the integrator continued the already-owned lane without replaying that attempt.

Next gate: freeze exact SHA -> independent R3 exact-SHA review -> exact-head
hosted CI -> expected-head merge -> post-main verification. #498 remains frozen
and must not receive another blind CI rerun from this checkpoint.

## Replay / stop rules

- RUNNING/UNKNOWN external execution is never redispatched.
- Repeated material failure twice without new evidence enters root-cause mode.
- SQLite lock ambiguity is not solved by blind retry.
- Stop only for real authority/ownership/safety/authorization gates.
