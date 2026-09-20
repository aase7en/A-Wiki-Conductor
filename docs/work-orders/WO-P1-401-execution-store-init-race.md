# WO-P1-401 — SQLite Execution-Store Concurrent Initialization Race

Status: READY_FOR_REVIEW / R3 / CLAIMED
Claim: `WO-P1-401-EXECUTION-STORE-INIT-RACE-001`
Owner: GPT-5.6 Sol integrator; GLM-5.3 MAX bounded implementation author.
Issue: #401
Date: 2026-09-20

## Authority and exact state

Repo: `aase7en/A-Wiki-Conductor`.
Base (dispatch head): `61315b71d510ce8ba88498018bb6c1d76dab144d`.
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo401-execution-store-init-race`.
Branch: `fix/wo-p1-401-execution-store-init-race`.
Trigger: PR #388 CI run `35478809895` failed `tests/test_zero_relay_review_execution.py::test_concurrent_same_fingerprint_lanes_one_model_effect_winner` with `sqlite3.IntegrityError: UNIQUE constraint failed: execution_store_meta.key` inside `SQLiteExecutionStore.initialize`, rethrown as `EXECUTION_STORE_INIT_FAILED`.

## Problem

`SQLiteExecutionStore.initialize()` performed a SELECT-then-plain-INSERT sequence for `execution_store_meta.schema_version`. Concurrent callers sharing one control database can both observe no row and then race on the unique key; the loser raises `sqlite3.IntegrityError`, surfaced as `EXECUTION_STORE_INIT_FAILED`.

WO-P1-242 / Issue #322 fixed the analogous `job_store` race only. This WO reuses that accepted race-safe pattern in the existing execution-store authority; it creates no new store/schema authority.

## Scope and forbidden scope

Allowed mutable scope exactly:
1. `src/a_conductor/execution_store.py`
2. `tests/test_execution_store.py`
3. `docs/work-orders/WO-P1-401-execution-store-init-race.md`

Forbidden: job_store/provider/lease/review semantics, schema version bump, second database, broad retries, any other tracked path, runtime/live control DB, credentials, reset/clean/stash/rebase/merge/force-push, merge/self-accept.

## Repair semantics

`initialize()` now creates the single `schema_version` row with an atomic idempotent upsert:

```sql
INSERT INTO execution_store_meta(key, value) VALUES('schema_version', ?)
ON CONFLICT(key) DO NOTHING
```

followed by a durable re-read in the same connection/transaction. Fail-closed behavior preserved exactly: missing row after upsert raises `EXECUTION_STORE_INIT_FAILED`; a persisted unsupported value still raises `EXECUTION_SCHEMA_VERSION_UNSUPPORTED` (the upsert never overwrites an existing row). No schema bump (`EXECUTION_STORE_SCHEMA_VERSION` stays `"1"`), no DB identity change, no public API/error-code surface change, single store authority retained.

## RED evidence (pre-fix, dispatch head `61315b7`)

Command: `python -m pytest tests/test_execution_store.py -q` (venv Python 3.11.15 / pytest 9.1.1, matching CI 3.11).

Added `test_initialize_is_safe_for_two_callers_that_both_observe_missing_schema_version` deterministically forces the historical SELECT-then-INSERT interleave via connection proxies (both callers observe no row; the winner's INSERT commits before the loser's INSERT executes — no timing luck, no sleep-based correctness).

Result:

```
1 failed, 13 passed in 1.87s
FAILED tests/test_execution_store.py::test_initialize_is_safe_for_two_callers_that_both_observe_missing_schema_version
AssertionError: assert ['EXECUTION_STORE_INIT_FAILED', 'OK'] == ['OK', 'OK']
```

This reproduces the exact PR #388 CI failure signature on old code.

## GREEN evidence (post-fix)

- `tests/test_execution_store.py -q` → 14 passed (includes deterministic race, 8-thread × 10-round fresh-database stress with barrier-coordinated starts, unsupported-version fail-closed guard).
- `tests/test_zero_relay_review_execution.py::test_concurrent_same_fingerprint_lanes_one_model_effect_winner` → 1 passed (exact CI-failing test).
- `tests/test_zero_relay_review_execution.py -q` → 80 passed.
- Adjacent suites `tests/test_job_store.py tests/test_execution_record.py tests/test_graph_store.py -q` → 35 passed.
- Repeated concurrency stress: `-k initialize` × 5 repeats → `3 passed` each (15 concurrent executions green).
- `py_compile` on both changed code files → OK.
- `git diff --check` → clean.
- Scope: exactly the three allowed paths.
- Strict UTF-8 read with no U+FFFD on both changed code files → OK.
- Added-line secret scan → no matches.

## Continuity

Fresh sessions recover from actual Git/GitHub/Issue #401, then this WO. Agent/model output is evidence only; deterministic tests/CI and exact Git state are completion authority. Do not merge or self-accept.

Next: independent exact-SHA R3 review + exact-head CI, then expected-head acceptance per the standing delivery-gate sequence.
