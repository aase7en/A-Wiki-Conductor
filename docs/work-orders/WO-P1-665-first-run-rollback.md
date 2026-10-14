# WO-P1-665 — first-run readiness planner + bounded install rollback

Status: OPEN — implementation lane (SRM source; AWC docs only)
Issue: #665
Parent: #495 (operator steer 2026-10-15 — P4 first-run integration); predecessors: installer slice E, WO-653/656/659/662 components.
Risk: R3 — rollback touches (test-root) filesystem semantics; pure planner adjacent to the install trust surface.
Topology: EXECUTION_SUBSTRATE_ONLY. Compatibility: SRM `5d337d5` + AWC `2b5b366` (re-pin on drift).

## Scope

1. `src/sunday/first-run.ts`: `planFirstRun(signals)` (PURE, injected signals — install marker + config/allowlist grants + agent-state health + pairing) → typed FIRST_RUN_READY / NOT_READY(reason); `rollbackSundayInstall(configRoot)` — removes ONLY `config.json`/`install.json`, preserves runtime/user data, typed refusals (absent/corrupt marker, version mismatch), idempotent; library export only, NOT wired to any CLI.
2. Doctor `First run` row via the planner (read-only).
3. RED-first suite (temp roots only).

## Review assignment

Independent reviewer: GPT-6 Sol (gpt-6-sol codex exec read-only, exact-SHA, harness outside the worktree). JEV: SPENDING_GATED (recorded; no paid calls).

## Forbidden

Standard set; no rollback CLI wiring; no real machine paths; shipped components reused as-is (no weakening).

## Checkpoint log (append-only)

- [2026-10-15] WO created. Lane issue #665 verified real BEFORE naming; one clean `Issue: #665` line. No source mutation yet.
