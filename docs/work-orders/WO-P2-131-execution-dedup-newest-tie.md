# WO-P2-131 — Deterministic newest execution tie-break

Date: 2026-09-01
Owner: GPT-5.6 Sol integrator
Status: CLAIMED / RED_FIRST
Priority: P2 reliability
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-wo131-execution-dedup-tie`
Branch: `fix/wo-p2-131-execution-dedup-tie`
Base: `origin/main@23b988764a3529f0721375f5d0a0c885b715ad46`

## Trigger / evidence

WO126 exact-head full regression exposed intermittent failure in `test_newest_equivalent_record_is_authoritative_for_duplicate_decision`. WO126 changes no execution/dedup files.

Reproduction:
- WO126 exact head: 2 failures / 10 isolated runs.
- Pre-WO126 base tree: 4 failures / 10 isolated runs.
- Query orders equivalent records by `created_at DESC, execution_id DESC`.
- SQLite `created_at` uses millisecond-resolution `strftime('%Y-%m-%dT%H:%M:%fZ','now')`; equal timestamps let lexical execution IDs override actual insertion chronology.

## Goal

Make `find_by_fingerprint()` deterministically return the most recently created record even when two records share the same persisted timestamp. Preserve all duplicate-execution identity/state semantics.

## Mutable scope

- `src/a_conductor/execution_store.py`
- `tests/test_execution_deduplication.py`
- this work order

Shared SSoT / `DEFECT_LESSONS.md` are intentionally excluded while WO126 PR #179 owns those files.

## Forbidden scope

- execution state-machine semantics outside query ordering
- provider/UI/runtime/worker/tunnel code
- schema migration or timestamp-format change unless rowid tie-break proves insufficient
- sleeps/retries added merely to stabilize the test

## Acceptance

1. Deterministic RED forces equal `created_at` values and proves lexical execution ID cannot choose the older record.
2. The smallest repair uses durable insertion chronology as the secondary ordering authority.
3. Existing duplicate-guard focused/related tests remain green.
4. Query remains deterministic for non-tied timestamps and does not mutate records.
5. Independent review/CI required before merge; no coupling to WO126 merge authority.

## RED / repair checkpoint

Deterministic RED forced equal `created_at` timestamps with `zz-old` inserted before `aa-new`; the existing query selected the FAILED old record because lexical `execution_id DESC` won the tie.

Smallest repair: `ORDER BY created_at DESC, rowid DESC`. SQLite rowid preserves creation insertion chronology for this ordinary rowid table; no schema/state/timestamp mutation was introduced.

Evidence:
- deterministic tie RED: 1/1 failed before repair;
- focused dedup: 12/12 PASS after repair;
- execution store: 11/11 PASS;
- execution-focused matrix: 44/44 PASS;
- deterministic tie stress: 20/20 PASS;
- original formerly-flaky test stress: 20/20 PASS;
- compileall + diff-check PASS.

Status: IMPLEMENTED / REVIEW_CI_PENDING. Shared SSoT/Defect Memory remain untouched until WO126 releases those files.
