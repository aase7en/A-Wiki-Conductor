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

Missing seams at this checkpoint:
- `NativeCommandSpec.environment_overrides` is not forwarded by `SupervisedCommandRunner`;
- `SupervisedLaunchPlan` has no environment field;
- `OwnedProcessSpec` permits only `SERENA_HOME` overrides;
- no Claude-specific adapter yet resolves opaque environment references into that supervised path.

Raw endpoint/credential values must resolve only at execution boundary and never enter argv, SQLite identity metadata, result JSON, or command summaries.

## Protected Parallel Work

- WO-P1-097 connector CR-1/CR-3: independently dirty `A-Wiki-Conductor-tunnel-stability`; do not touch.
- PR #108 installer target ownership: do not touch.
- North Star branch: do not touch.
- live connector fleet / tunnel-client binary: do not mutate.
- A-Wiki repository: read-only.

## Next Safe Action

1. RED tests proving supervised environment overrides are dropped today;
2. propagate bounded overrides through launch plan into exact-owned process spec;
3. add `SupervisedClaudeCodeRunner` with injected opaque-reference resolver and secret redaction;
4. prove canonical duplicate attach/reuse + timeout/recovery behavior is unchanged;
5. run focused/regression/compile/diff/scope/secret gates;
6. open exact-head PR + require Windows/Ubuntu/macOS CI;
7. follow with a separate bounded production-assembly slice if per-job runner construction is still required.

## Safety

`SAFE_TO_MUTATE = YES` only in `A:\GitHub\A-Wiki-Conductor-aha4-supervised` and WO-P1-098 allowed scope.
