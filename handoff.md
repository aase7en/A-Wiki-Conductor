# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-28 — WO-P1-098 / AHA-4 supervised Claude runner

## Current Objective

Finish the real process boundary for the Sunday Family multi-model harness by adapting accepted AHA-3 `ClaudeCodeInvocation` into the existing supervised execution + duplicate-protection authority. No second process runner, lifecycle, store, retry loop, or dedup system.

## Repository State

- Repository: `aase7en/A-Wiki-Conductor`
- Worktree: `A:\GitHub\A-Wiki-Conductor-aha4-supervised`
- Branch: `feat/wo-p1-098-aha4-supervised-claude-runner`
- Base/current main at claim: `0e9b93a7c08cb7b284f2234af61ec6a96b16a2ea`
- Work order: `docs/work-orders/WO-P1-098-aha4-supervised-claude-runner.md`
- Shared root remains protected/read-only.

## Accepted Baseline

- AHA-3 bounded read-only Claude Code adapter merged `ab28dc7`.
- GE-6 scheduler merged `023c7b6`.
- durable graph dispatch PR #119 merged `5cc417c9`.
- connector-resilience roadmap PR #120 merged `7505bd3` and is an independent P0 v0.7.0 gate.
- durable Claude job backend PR #121 exact head `69fffe7` passed 3-OS CI run `33164201872` and merged as `0e9b93a`.

## Architecture Boundary

Classification: **REUSE + WRAP + EXTEND**.

Current authoritative execution chain:
`ClaudeCodeInvocation -> SupervisedClaudeCodeRunner -> NativeCommandSpec -> SupervisedCommandRunner -> DuplicateExecutionGuard -> SupervisedExecutionService -> OwnedProcessSpec`.

Implemented seams at this checkpoint:
- bounded environment overrides now flow through `SupervisedCommandRunner -> SupervisedLaunchPlan -> OwnedProcessSpec` after scope validation;
- exact-owned policy allows only the existing `SERENA_HOME` plus Claude's `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` keys;
- launch/spec repr masks environment values;
- `SupervisedClaudeCodeRunner` resolves opaque refs only at execution boundary, redacts resolved secret values from returned streams, and never creates a bare subprocess path;
- production builder binds durable execution identity plus `runtime:claude-code:<digest>` derived only from opaque endpoint/credential refs; source-ref drift fails before resolver/launch;
- canonical execution fingerprint excludes resolved environment values; duplicate attach/reuse remains owned by `DuplicateExecutionGuard`.

Local evidence: runner/builder **11 passed**; focused Claude/provider/native/supervisor/dedup/job regression **150 passed**; compileall, diff-check, and bounded secret-pattern scan PASS.

## Protected Parallel Work

- WO-P1-097 connector CR-1/CR-3: independently dirty `A-Wiki-Conductor-tunnel-stability`; do not touch.
- PR #108 installer target ownership: do not touch.
- North Star branch: do not touch.
- live connector fleet / tunnel-client binary: do not mutate.
- A-Wiki repository: read-only.

## Next Safe Action

1. commit the locally green WO-P1-098 implementation and SSoT checkpoint;
2. fetch/reconcile current `origin/main`; if it moved, merge safely and rerun focused gates;
3. push Draft PR and audit exact remote diff/scope;
4. require exact-head Windows/Ubuntu/macOS CI including Windows packaging/frozen/Portable smoke;
5. merge only after green CI + exact-head review;
6. then open the smallest per-job production assembly slice joining the accepted durable Claude backend to `build_supervised_claude_code_runner` without provider/gateway/live-secret mutation.

## Safety

`SAFE_TO_MUTATE = YES` only in `A:\GitHub\A-Wiki-Conductor-aha4-supervised` and WO-P1-098 allowed scope.
