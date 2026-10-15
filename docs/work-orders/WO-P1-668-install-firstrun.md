# WO-P1-668 — install CLI first-run posture wiring

Status: DONE — SRM PR #34 merged 2026-10-15 at `998a028` (pinned-head `4d05443`); six-round Sol review arc (all findings real, all repaired; r6 PASS); claim released #668 comment 6183938348
Issue: #668
Parent: #495 (operator steer 2026-10-15); predecessor WO-P1-665 (planner + rollback + doctor row).
Risk: R2 — read-only report composition in the install CLI; no trust-surface change.
Topology: EXECUTION_SUBSTRATE_ONLY. Compatibility: SRM `2f02170` + AWC `73acb69` (re-pin on drift).

## Scope

`sunday-install.ts`: post-result `first-run:` line via `planFirstRun` (signals read back from the effective install root + Sunday-root agent state + installer-result pairing). Read-only; exit-code contract unchanged; fail-closed UNKNOWN on composition errors. RED-first subprocess suite (fresh → NOT READY with expected reasons; seeded → READY).

## Review assignment

Independent reviewer: GPT-6 Sol (gpt-6-sol codex exec, exact-SHA, harness outside the worktree). JEV: SPENDING_GATED (recorded; no paid calls).

## Forbidden

Standard set; no new CLI surface; no exit-code change; shipped components reused as-is.

## Checkpoint log (append-only)

- [2026-10-15] WO created. Lane issue #668 verified real BEFORE naming; one clean `Issue: #668` line. No source mutation yet.
