# WO-GE-011R1 — GraphStore read-only hardening

Created: 2026-08-29
Owner: GPT-5.6 Sol Graph hardening lane
Status: COMPLETE / MERGED PR #142 / POST-MERGE MAIN CI GREEN
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-ge11r1-readonly`
Branch: `fix/wo-ge-011r1-graph-store-readonly`
Base reconciled: `origin/main@392047a0395f30cc1d6ed7d8c2c3f7c0457a5e37` (PR #140 merged)

## Trigger

Independent GLM audit found a conditional safety risk: constructing `GraphStore` always creates/migrates schema, so a future diagnostic/UI caller could accidentally mutate the database merely to read it.

## Goal

Add an explicit read-only GraphStore open path while preserving current writable constructor behavior.

## Scope

- `src/a_conductor/graph/store.py`
- `tests/test_graph_store.py`
- this work order

No GE-11 UI, lifecycle, scheduler, dispatch, job store, or SSoT hotspot mutation.

## Acceptance

- `GraphStore.open_read_only(path)` never creates a missing database or parent directory;
- read-only load/list/event methods work on an existing initialized graph database;
- read-only mutation methods fail explicitly before SQL writes;
- normal `GraphStore(path)` behavior remains unchanged;
- read-only connection uses SQLite URI `mode=ro` and `PRAGMA query_only=ON`;
- focused + full graph regression, compile/diff/secret gates pass;
- reconcile accepted main after GE-11 before PR creation.

## TDD

1. RED: missing path is not created.
2. RED: existing database can be read without mtime change.
3. RED: save/delete/event writes are rejected explicitly.
4. GREEN: minimal read-only constructor/classmethod and write guard.
5. Review, full graph regression, PR/CI/re-audit/merge.

## Local verification checkpoint

- RED: import failed because read-only API/error did not exist;
- GREEN focused `tests/test_graph_store.py`: **9 passed**;
- full pre-GE11 graph suite: **170 passed**;
- compileall: PASS;
- `git diff --check`: PASS;
- no subprocess/network/timer path added.

Implementation preserves `GraphStore(path)` writable behavior. `open_read_only(path)` requires an existing file, skips mkdir/schema initialization, uses SQLite URI `mode=ro` + `query_only`, and rejects save/delete/event mutation before SQL.

Next: commit local checkpoint; after PR #140 merges, fetch/reconcile accepted main, rerun graph suite, then open PR.

## Accepted-main reconciliation — 2026-08-29

- PR #140 merged as `392047a0395f30cc1d6ed7d8c2c3f7c0457a5e37`; merge into this lane was conflict-free.
- focused GraphStore + GE-11 composition: **24 passed**.
- full `tests/test_graph_*.py` after reconciliation: **185 passed**.
- read-only event retrieval is covered in addition to load/list; database mtime remains unchanged.
- compileall and `git diff --check`: PASS.

Next: exact-scope commit/push, PR, exact-head 3-OS CI, remote re-audit, merge and accepted-main verification.

Accepted-main prerequisite verified: CI run `33239717637` for PR #140 merge `392047a0` is SUCCESS.

## Merge closeout - 2026-08-29

PR #142 merged as `7acb10225e0fff15c6ca0e43b6227599852d3e84`. Post-merge main CI run `33241026175` passed Windows, Ubuntu, and macOS. `GraphStore.open_read_only()` is accepted with SQLite `mode=ro`, `query_only=ON`, no missing-database creation, supported read paths, and fail-closed mutations.
