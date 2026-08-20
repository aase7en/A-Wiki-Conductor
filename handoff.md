# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current objective

Add transactional Git stage/commit support without weakening the deterministic Native Execution boundary.

## Current task

`WO-P1-033 — Transactional Git Stage + Commit`

Status: `IN_PROGRESS`

## Baseline

- Base HEAD: `88a863f feat: add native git and verification adapters`.
- Native execution core + read-only Git/verification adapters are complete.
- P1-032 evidence: 10 targeted + 448 full-suite passed, 1 environment-specific Tk/Tcl skip; real read-only Git adapter smoke exit 0.
- Transaction contract: `docs/contracts/native-git-transactions.md`.

## Current safety design

- Snapshot exact HEAD + status hash + cached-diff hash before mutation.
- Stage requires explicit file paths and exact snapshot preconditions.
- Commit requires exact snapshot preconditions and a non-empty cached diff.
- Commit is deterministic/noninteractive in this first slice: hooks skipped, GPG signing disabled.
- Integration tests must use temporary Git repos only.

## Forbidden

No blanket stage `.`, reset/clean/checkout/switch/stash/rebase/merge/cherry-pick/revert/push/fetch/pull/remote mutation, force options, or generic Git argv passthrough.

## External / deferred gate

`DR-P1-003 / BLOCKED_EXTERNAL` unchanged. A-Wiki companion registration payload remains prepared but unapplied.

## Next safe action

Commit docs/claim checkpoint, write RED unit and temp-repo transaction tests, implement `native_git_transactions.py`, then run targeted/full/compile/diff/static gates.

## Resume instructions

Read `AGENTS.md` -> `PROJECT-PLAN.md` -> native execution contracts -> `COLLAB.md` -> `CURRENT-WORK.md` -> this file -> active WO; verify branch/HEAD/status before mutation.
