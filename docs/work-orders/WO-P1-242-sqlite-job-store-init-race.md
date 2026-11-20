# WO-P1-242 — SQLite Job-Store Concurrent Initialization Race

Status: ACTIVE / R2 / CLAIMED
Claim: `WO-P1-242-SQLITE-JOB-STORE-INIT-RACE-001`
Owner: GPT-5.6 Sol integrator; GLM-5.3 MAX may take bounded implementation/review after provider quota resets.
Issue: #322
Date: 2026-09-15

## Authority and exact state

Repo: `aase7en/A-Wiki-Conductor`.
Base: `82d3aabe352d071a676db5bb6b9cbfeb5dcda05b`.
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo242-sqlite-init-race`.
Branch: `fix/wo-p1-242-sqlite-job-store-init-race`.
Trigger: main CI run `34950485251` failed with `JOB_STORE_INITIALIZE_FAILED` caused by concurrent schema-version insertion.

## Problem

`SQLiteJobStore.initialize()` performs a read-then-insert sequence for `job_store_meta.schema_version`. Concurrent callers can both observe no row and then race on the unique key; one raises `sqlite3.IntegrityError` and the public API surfaces `JOB_STORE_INITIALIZE_FAILED`.

This defect is separate from WO223 RE2-A. WO223 candidate `779fcf5975e21d6891f63b94ad79893745776675` remains frozen/read-only.
## Scope and forbidden scope

Allowed tracked source/test scope after bootstrap re-gate:
1. `src/a_conductor/job_store.py`
2. `tests/test_job_store.py`
3. only if needed, the smallest existing concurrency regression file that exercises the same public store API.

Forbidden: WO223's four files, provider/lease/review semantics, Browser Wake/Sunday-Family source, runtime/live control DB, credentials, root checkout, unrelated scheduler/router changes, reset/clean/stash/rebase/merge/force-push.

## RED-first acceptance

- deterministic concurrent initialization must reproduce the pre-fix race without timing luck;
- all concurrent initializers must complete without duplicate schema-version failure;
- exactly one supported `schema_version` truth remains persisted;
- an existing unsupported schema version must still fail typed `JOB_STORE_SCHEMA_UNSUPPORTED`;
- repeated initialize/get operations remain idempotent;
- the previously failing zero-relay concurrency test must pass;
- focused job-store tests plus broader job/graph/zero-relay regression must pass.

## Delivery gates

Bootstrap docs commit -> fresh mutation gate -> RED -> minimal repair -> focused+related regression -> diff/scope/UTF-8/secret checks -> freeze exact SHA -> independent review -> hosted CI -> expected-head acceptance/merge -> post-main verification.

Agent/model output is evidence only. Deterministic tests/CI and exact Git state are completion authority.
## Continuity

Fresh sessions recover from actual Git/GitHub/Issue #322, then this WO. Do not use chat as authority.

Meaningful checkpoints record branch/HEAD/dirty state, exact scope, tests/evidence, blocker classification, candidate/review/CI status, and next safe action.

### 2026-09-15 bootstrap checkpoint

Issue #322 is the durable claim. Branch/worktree were created clean from exact `origin/main@82d3aabe352d071a676db5bb6b9cbfeb5dcda05b` after a branch-diff scan found no other branch changing `src/a_conductor/job_store.py` or `tests/test_job_store.py` versus current main.

GLM CoinTH route is temporarily `RATE_LIMITED` by its 5-hour quota until 2026-09-15 19:26:26 local provider time. This does not block deterministic bootstrap, RED construction, or GPT integration work; no blind provider retries are allowed before reset.

`SAFE_TO_MUTATE_WO242_DOCS=YES`
`SAFE_TO_MUTATE_WO242_SOURCE=NO`

Next safe action: verify/commit/push this docs bootstrap, re-prove exact HEAD/clean/scope/ownership, then open the bounded source/test mutation gate and build the deterministic RED concurrency test before repair.
### 2026-09-15 source mutation gate

Bootstrap `7d93ad67338bac49902a2929370a2835a6c28b8f` is pushed and the worktree is clean. Repo/worktree/branch/HEAD/Issue #322 ownership and the bounded source/test scope are proven; branch-diff scan found no competing `job_store.py` / `test_job_store.py` mutation.

`SAFE_TO_MUTATE_WO242_SOURCE=YES`

One mutable owner only. Next: add deterministic RED for concurrent initialization, prove the pre-fix failure, then apply the smallest idempotent schema-version initialization repair while preserving typed unsupported-version rejection.