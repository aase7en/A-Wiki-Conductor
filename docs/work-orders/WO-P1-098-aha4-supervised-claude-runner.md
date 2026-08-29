# WO-P1-098 — AHA-4 supervised Claude Code runner

Date: 2026-08-28
Owner: GPT-5.6 Sol integrator
Status: COMPLETE / MERGED
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-aha4-supervised`
Branch: `feat/wo-p1-098-aha4-supervised-claude-runner`
Base: `origin/main@0e9b93a7c08cb7b284f2234af61ec6a96b16a2ea`

## Goal

Replace the injected fake/process runner boundary behind the accepted Claude Code harness with a bounded adapter over the existing supervised execution + duplicate-protection authority. Keep external launch recoverable and secret-safe without creating a second process runner, execution store, lifecycle, retry loop, or dedup system.

## Reuse gate

Classification: **REUSE + WRAP + EXTEND**.

Reuse:
- AHA-3 `ClaudeCodeInvocation` / `ClaudeCodeRunner` contract;
- `SupervisedCommandRunner` + `DuplicateExecutionGuard`;
- `SupervisedExecutionService` + `OwnedProcessSpec`;
- existing opaque provider endpoint/credential references;
- existing durable execution identity/fingerprint semantics.

## Allowed scope

- new `src/a_conductor/claude_code_supervised_runner.py`
- new `tests/test_claude_code_supervised_runner.py`
- `src/a_conductor/supervised_command_runner.py` + focused tests
- `src/a_conductor/supervised_execution.py` + focused tests
- `src/a_conductor/owned_process.py` + focused tests only for narrow environment policy
- this WO, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`

## Forbidden scope

- connector stability WO-P1-097 files / live tunnel-client binary
- PR #108 installer target ownership
- North Star files
- graph scheduler/dispatch semantics
- provider DB/gateway/live credential values
- worker lease/fallback/heartbeat
- A-Wiki mutation

## Acceptance

1. Claude invocation executes only through the canonical supervised runner; no bare subprocess path is added.
2. Environment reference values resolve only at execution boundary through an injected resolver.
3. Only `ANTHROPIC_BASE_URL` and `ANTHROPIC_AUTH_TOKEN` may be supplied by this adapter; raw values never enter argv, SQLite identity metadata, result JSON, or command summaries.
4. Supervised launch forwards bounded environment overrides to the exact-owned helper/target process.
5. Duplicate attach/reuse remains owned by `DuplicateExecutionGuard`; timeout/unknown state never blind-relaunches.
6. Runner output is mapped to `ClaudeCodeRunnerResult` with resolved secret values redacted in returned stdout/stderr.
7. Existing native/supervised execution remains backward compatible.
8. Focused TDD, regression, compileall, diff-check, scope/secret audit, and exact-head 3-OS CI pass before merge.

## Identity rule

The canonical execution fingerprint must continue to use durable job/work-order/project/backend/repo/branch/HEAD/operation/runtime-profile/argv identity. Raw environment values are not fingerprint material. The supervised Claude runner must use a non-secret runtime-profile reference derived from opaque endpoint/credential reference identity, never from the resolved credential value.

## Safety gate

Verified before mutation:
- clean isolated worktree from accepted `origin/main@0e9b93a` (PR #121 merged);
- candidate scope has zero overlap with PR #108, North Star, and WO-P1-097 known files;
- historical WO-P1-022 ownership of `owned_process.py` is completed/released;
- shared root remains protected/read-only;
- live connector fleet and local credential stores remain untouched.

`SAFE_TO_MUTATE = YES` only inside this worktree and the allowed scope above.

## First TDD sequence

1. RED: supervised launch drops `NativeCommandSpec.environment_overrides` today.
2. GREEN: propagate only bounded allowed overrides into `OwnedProcessSpec`.
3. RED/GREEN: implement `SupervisedClaudeCodeRunner` reference resolution, mapping, redaction, and no-secret-persistence assertions.
4. Reconcile whether production backend assembly needs a separate bounded follow-up after this runner contract is proven.

## Implementation checkpoint — 2026-08-28

Implemented:
- `NativeCommandSpec.environment_overrides` now survives the supervised launch seam into `OwnedProcessSpec` under the existing scope allowlist;
- low-level owned-process policy explicitly permits only `SERENA_HOME`, `ANTHROPIC_BASE_URL`, and `ANTHROPIC_AUTH_TOKEN`;
- `SupervisedLaunchPlan` / `OwnedProcessSpec` mask environment override values from dataclass repr;
- new `SupervisedClaudeCodeRunner` resolves endpoint/token refs only at execution time, validates the exact two Claude environment keys, maps to `NativeCommandSpec`, and redacts resolved secrets from returned streams;
- production builder derives `runtime:claude-code:<digest>` only from opaque endpoint/credential refs and pins invocation refs to that identity before resolution;
- raw environment values are excluded from execution fingerprints; duplicate attach/reuse remains canonical `DuplicateExecutionGuard` behavior.

TDD evidence:
- environment propagation RED: **3 failed** -> GREEN;
- repr secret-safety RED: **2 failed** -> GREEN;
- new runner import RED: module absent -> GREEN;
- reference-drift RED proved an unpinned binding could reach launch -> GREEN after builder pinning;
- runner/builder suite: **11 passed**;
- post-reconcile Claude/provider/native/supervisor/dedup/job/graph regression: **241 passed**;
- compileall PASS; diff-check PASS; bounded secret-pattern scan PASS.

Reconciled `origin/main@ceee9bb7aa361aef6d0ecfc210c25b564578d552` (PR #122 / WO-P1-097) with zero scope overlap. Next: push Draft PR, audit exact remote diff, require exact-head Windows/Ubuntu/macOS CI including Windows packaging/frozen/Portable smoke before merge.

## Repo-health reconciliation - 2026-08-29

- Historical execution text above is preserved as evidence; the stale status is superseded by accepted GitHub state.
- PR #124 merged into main as `e933a53c3c32bf0f8126f1602c913c08765d9a8a`.
