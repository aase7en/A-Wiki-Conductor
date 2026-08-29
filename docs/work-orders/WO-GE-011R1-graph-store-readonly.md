# WO-GE-011R1 — GraphStore read-only hardening

Created: 2026-08-29
Owner: GPT-5.6 Sol Graph hardening lane
Status: ACTIVE / TDD
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-ge11r1-readonly`
Branch: `fix/wo-ge-011r1-graph-store-readonly`
Base: `origin/main@1fea5cfffbe9bb8a9093e67dfa1065559e324ab2`

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
