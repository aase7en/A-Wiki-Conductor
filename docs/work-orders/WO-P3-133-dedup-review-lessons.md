# WO-P3-133 — Dedup chronology and review-gate defect lessons

Date: 2026-09-02
Owner: GPT-5.6 Sol integrator
Status: CLAIMED / DOCS_ONLY
Priority: P3 continuity
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-wo133-defect-lessons`
Branch: `docs/wo-p3-133-dedup-review-lessons`
Base: `origin/main@9118a289b9fcd87e0bae4e4eb601cc585062856d`

## Goal

Persist two reusable lessons from WO131/PR #180 without reopening product code: deterministic newest-row chronology when timestamps tie, and truthful reconciliation when an external merge bypasses a planned independent-review gate.

## Mutable scope

- `DEFECT_LESSONS.md`
- this work order only

## Forbidden scope

- all `src/**` and `tests/**`
- shared frontier files (`CURRENT-WORK.md`, `handoff.md`, `README.md`, `AGENT_TASKS.md`)
- WO127/WO128/AiPASS work orders or PR branches
- live Workers, tunnels, credentials, release/version files
## Acceptance

1. Record that millisecond timestamps can tie and opaque lexical IDs are not chronology authority.
2. Record the bounded current repair: same-table SQLite insertion chronology via `rowid DESC` after `created_at DESC` when no durable monotonic sequence exists.
3. Record the deterministic regression shape: force the same timestamp and reverse lexical ID order.
4. Preserve the caveat that a future durable sequence column is preferable if row identity can be rebuilt/copied in ways that invalidate insertion chronology.
5. Record that a merge occurring before planned review evidence exists remains a process deviation even if CI/post-main verification is green.
6. Never manufacture a retrospective PASS or pretend missing review evidence existed.

## Verification

- docs-only exact scope
- `git diff --check`
- strict UTF-8 read
- check lesson numbering remains unique
- confirm no `src/**`, `tests/**`, or shared frontier files changed
- commit/PR only after scope audit
