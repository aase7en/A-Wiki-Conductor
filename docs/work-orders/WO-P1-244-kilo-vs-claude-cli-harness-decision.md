# WO-P1-244 — Kilo vs Claude CLI harness decision reference

Status: ACTIVE / DOCS-ONLY / R1
Issue: #325
Owner: GPT-5.6 Sol integrator
Base: `origin/main@82d3aabe352d071a676db5bb6b9cbfeb5dcda05b`
Branch: `docs/wo244-kilo-claude-cli-harness-decision`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo244-cli-harness-decision`

## Purpose

Capture the Kilo CLI vs Claude Code CLI decision as durable project guidance before session rollover. This work order does not authorize source implementation.

## Claimed scope

- `docs/decisions/2026-09-15-kilo-vs-claude-cli-harness.md`
- `docs/work-orders/WO-P1-244-kilo-vs-claude-cli-harness-decision.md`
- `docs/checkpoints/2026-09-15-session-rollover-a-conductor.md`

Forbidden scope: `src/**`, tests, runtime DB, credentials, provider config values, WO223/WO242 source worktrees, `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`, scheduler/job/provider/lease/review authority.

## Mutation gate

- Repo: `aase7en/A-Wiki-Conductor`
- Runtime: Windows `DESKTOP-7IB57R4`
- Base: current `origin/main@82d3aabe352d071a676db5bb6b9cbfeb5dcda05b`
- Root checkout remains stale/dirty/protected; this WO uses a fresh isolated worktree.
- `SAFE_TO_MUTATE_DOCS=YES`
- `SAFE_TO_MUTATE_SOURCE=NO`

## Decision summary

Kilo CLI is the current proven GLM execution transport on this Windows runtime. Claude Code CLI has better documented structured headless primitives and gateway support, but its local GLM route is still unverified. A-Conductor should not choose a vendor/harness as authority; it should route across accepted backends using durable health/quota/cost/readiness evidence.

## Acceptance

- Decision matrix exists and separates repo authority, local runtime observations, public docs, and inference.
- Recommendation is executor-neutral: reuse existing Claude path, add thin Kilo backend, route by capability/health/cost.
- Completion classifier forbids trusting agent `DONE`, exit code, or prose alone.
- Session rollover checkpoint exists for the next chat.

## Next safe action

Commit/push docs-only candidate, checkpoint Issue #325, then return to active critical path: WO223 final R3, WO242 CI/review, Phase-D/WO205, WO227/ZRA-3, Browser Wake MVP.
