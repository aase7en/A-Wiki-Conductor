# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Project

A-Wiki Conductor / product name **A-Conductor**.

## Current objective

Begin Phase 1 implementation with the smallest provider-neutral typed domain layer, test-first, before process/runtime/UI work.

## Current phase

`Phase 1 — Multi-Serena Control Center / typed domain foundation`

## Current task

`WO-P1-001 — Typed Core Domain Models`

Status: `IN_PROGRESS`

## Completed

- A-Wiki reuse-before-build/duplicate-work gate checked.
- A-Wiki work-order scaffolding reused and bootstrapped.
- C1 core domain contract and three JSON Schemas completed and validated.
- Local Git initialized on `main`.
- `.serena/` is ignored.
- Initial local architecture baseline committed.
- `WO-P1-000` local repository safety baseline completed.
- Python 3.11.15 and pytest 9.1.1 confirmed available.
- `WO-P1-001` opened and claimed for typed domain models.

## Evidence

C1:
- Draft 2020-12 schema check: PASS (3)
- example validation: PASS (3/3)
- baseline contract SHA256 recorded in `CURRENT-WORK.md`/WO-C1-001.

Repository baseline:
- branch: `main`
- baseline content commit: `3ed22df0d884cf15729167d923ec4a0e32593662`
- no remote configured
- worktree was clean immediately after baseline commit
- `.serena/project.local.yml` confirmed ignored

## Current repository state

Git is initialized locally. Current checkpoint is based on `main` from baseline commit `3ed22df0d884cf15729167d923ec4a0e32593662`; WO-P1-001 coordination docs are being prepared as the next coherent commit.

Git ownership warning: this filesystem reports the directory owner as `Administrators`, so ordinary Git commands trigger dubious-ownership protection. This session uses exact per-command `git -c safe.directory=A:/GitHub/A-Wiki-Conductor ...`. Global Git config was intentionally not modified.

## Decisions made

- Product: `A-Conductor`.
- Initial slots: `A-Worker 1..3` / `a-worker-01..03`.
- Worker is runtime-neutral; Serena is the first runtime implementation only.
- Reuse A-Wiki work-order/claim/handoff primitives.
- Core implementation starts with Python 3.11 stdlib dataclasses/enums; no third-party runtime framework is introduced by WO-P1-001.
- Tests precede behavior/source implementation.

## DECISION_REQUIRED

### DR-C1-001 — GitHub repository publication

Need explicit visibility/public-safety decision before creating/configuring a GitHub remote. Recommended default remains private-first.

## Known problems / warnings

- No cross-machine GitHub visibility for A-Conductor yet because no remote exists.
- Prior GitHub connector path returned `FORBIDDEN`; public A-Wiki GitHub was still checked read-only via web.
- Local A-Wiki contains unrelated dirty work and must remain read-only for this project.
- Git dubious-ownership warning must be handled per-command until a separate machine-level decision changes protected Git config.

## Do not do

- Do not modify A-Wiki/Phase6.
- Do not configure/push a Git remote yet.
- Do not start Serena/tunnel/process manager, broker, UI, network, or provider integration during WO-P1-001.
- Do not write source implementation before the failing domain tests exist.

## TODO

See `CURRENT-WORK.md` and `docs/work-orders/WO-P1-001-domain-models.md`.

## Next safe action

Commit the WO-P1-001 coordination checkpoint, then create minimal pytest configuration and failing domain contract tests.

## Resume instructions

Read `AGENTS.md` -> `PROJECT-PLAN.md` -> `COLLAB.md` -> `CURRENT-WORK.md` -> this file -> `docs/work-orders/WO-P1-001-domain-models.md`. Reconcile actual Git state using the exact safe-directory override before mutation.
