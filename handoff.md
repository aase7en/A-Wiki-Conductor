# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current objective

Continue building the Work-class execution plane over the completed Native Execution Core without widening it into a generic model-facing shell.

## Current task

`WO-P1-032 — Native Git + Verification Adapters`

Status: `IN_PROGRESS`

## Baseline

- Base HEAD: `24f4e33 feat: add native execution core`.
- P1-031 evidence: 16 targeted + 439 full-suite tests; compileall/diff/static safety PASS.
- Native core contract: `docs/contracts/native-execution-core.md`.
- Adapter contract: `docs/contracts/native-execution-adapters.md`.

## Current scope

- Fixed read-only Git: status, working diff, cached diff.
- Fixed verification: pytest, compileall.
- Root-confined path validation and command option-injection defense.
- Verification commands declare mutation intent; read-only scopes must refuse them.

## Forbidden

No Git add/commit/reset/clean/checkout/stash/rebase/merge/push, no arbitrary command strings, no shell=True, no A-Wiki/tunnel/provider mutation.

## External / deferred gate

`DR-P1-003 / BLOCKED_EXTERNAL` remains unchanged. A-Wiki companion registration payload remains prepared but not applied.

## Next safe action

Commit P1-032 docs/claim checkpoint, write RED adapter tests, implement `native_adapters.py`, then run targeted/full/compile/diff/static gates.

## Resume instructions

Read `AGENTS.md` -> `PROJECT-PLAN.md` -> native execution contracts -> `COLLAB.md` -> `CURRENT-WORK.md` -> this file -> active WO; verify branch/HEAD/status before mutation.
