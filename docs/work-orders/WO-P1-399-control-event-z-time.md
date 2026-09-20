# WO-P1-399 — HOOK-1b.1 persisted UTC Z timestamp

Status: CLAIMED / READY_FOR_IMPLEMENTATION
Issue: #399
Identity schema: GITHUB_ISSUE_V1
Risk: R3 — time/interface compatibility
Topology: CONTROL_PLANE_ONLY

## Binding

- repo: `A:\GitHub\A-Wiki-Conductor`
- worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo399-control-event-z-time`
- branch: `feat/wo-p1-399-control-event-z-time`
- base: `61315b71d510ce8ba88498018bb6c1d76dab144d`
- claim: `WO-P1-399-CONTROL-EVENT-Z-TIME-001`
- integrator: GPT-5.6 Sol
- preferred author: GLM-5.3 MAX
- dependency: accepted WO-P1-391; blocks WO-P1-394 production fan-in

## Problem

`SQLiteControlEventLog.append()` currently persists
`datetime.now(timezone.utc).isoformat()`, which ends in `+00:00`.
Hook Contract v1 requires `occurred_at` to end in UTC `Z`.
WO-P1-394 correctly reuses the exact persisted timestamp byte-for-byte,
so current production Hook delivery degrades instead of emitting.## Settled design

Change only the timestamp serialization used for newly appended control events.

New rows MUST persist one canonical UTC representation:
`YYYY-MM-DDTHH:MM:SS[.fraction]Z`.

Use the existing UTC clock and existing `recorded_at TEXT NOT NULL` column.
Do not add a second clock, projection timestamp, column, table, migration,
trigger, or metadata store.

The exact persisted string returned by `append()`, `get()`, and
`list_recent()` must remain identical.

Legacy rows already containing `+00:00` remain readable exactly as stored.
No migration or rewrite of historical rows is authorized.

## Mutable scope ONLY

- `src/a_conductor/control_events.py`
- `tests/test_control_events.py`
- this Work Order

Everything else read-only.

## Forbidden

- `src/a_conductor/lifecycle_assembly.py` / WO-P1-394 mutation
- `src/a_conductor/control_hook_adapter.py`
- Hook Contract docs/schema
- SQLite DDL/schema migration
- legacy-row rewrite
- planner/coordinator/executor semantics
- CURRENT-WORK / handoff / COLLAB
- new scheduler/task/claim/review/time authority
- reset/clean/stash/rebase/force-push/history rewrite## RED-first acceptance

Before production mutation add deterministic failures proving:
1. a newly appended event does not yet end in `Z`;
2. append/get/list must expose the same exact persisted Z string;
3. the new string satisfies the existing Hook `occurred_at` format;
4. a pre-existing legacy `+00:00` row remains readable byte-for-byte;
5. SQLite schema columns are unchanged.

Use a deterministic/test-scoped clock where useful. Do not weaken the
existing Hook normalizer or schema to accept the current production defect.

## GREEN

- newly appended rows end in canonical `Z`;
- persisted/returned value equality is exact;
- legacy `+00:00` rows round-trip unchanged;
- existing control-event behavior remains green;
- existing control-hook adapter tests remain green without source changes;
- no schema migration or new authority;
- exact three-file scope, strict UTF-8, no U+FFFD, diff/secret checks clean.

## Verification

Run at minimum:
- `python -m pytest -q tests/test_control_events.py`
- `python -m pytest -q tests/test_control_events.py tests/test_control_hook_adapter.py`
- `python -m pytest -q tests/test_work_order_identity.py`
- `git diff --check`

If a direct existing normalizer assertion can prove the new timestamp is
accepted without widening source scope, add that assertion only in the
already-owned `tests/test_control_events.py`; otherwise report the boundary
and let the integrator perform cross-candidate integration verification.## R3 / fan-in gates

1. freeze exact candidate SHA;
2. independent exact-SHA review;
3. exact-head hosted CI;
4. GPT-5.6 Sol acceptance and expected-head merge;
5. fresh post-main focused verification;
6. only then validate WO-P1-394 candidate against the new main using a
   detached integration/merge-tree proof;
7. WO-P1-394 may be accepted only when the real, unpatched production path
   emits a valid Hook envelope using the persisted timestamp.

## Replay safety

Recover durable delegated-run pointers before redispatch.
RUNNING is never duplicated; TERMINAL_UNHARVESTED is harvested first.
Unknown dirty state or overlapping ownership fails closed.

## Continuity

This Work Order owns only the timestamp serialization hotspot above.
WO-P1-394 continues to own lifecycle Hook composition and must not mutate
these files while this lane is active.