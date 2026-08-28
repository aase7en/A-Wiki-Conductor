# WO-P1-095 — AHA-4 Claude Code durable backend bridge

Status: REVIEW_READY — LOCAL GREEN / PR PENDING
Owner: GPT-5.6 Sol integrator
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-aha4-bridge`
Branch: `feat/wo-p1-095-aha4-harness-durable-bridge`
Base: `origin/main@5cc417c92450eba796fa9af1cf3da037663b1eea`

## Goal

Place the accepted AHA-3 `ClaudeCodeHarnessAdapter` behind the existing `DurableJobExecutionCoordinator` authority so a durable graph job can execute one bounded Claude Code operation with the same attempt, recovery, checkpoint, and VERIFYING semantics as existing backends.

## Reuse gate

Classification: **REUSE + WRAP + EXTEND**.

Reuse:
- `DurableJobExecutionCoordinator` + `SQLiteJobStore`
- `JobExecutionBackend` application seam
- AHA-3 `ClaudeCodeHarnessAdapter`
- AHA-2 provider/readiness contracts
- canonical supervised execution/dedup for any later real external launch

Do not create a second job lifecycle, execution store, retry counter, process runner, duplicate guard, provider store, scheduler, or router.
## Allowed scope

- new `src/a_conductor/claude_code_job_backend.py`
- new `tests/test_claude_code_job_backend.py`
- `src/a_conductor/job_execution.py` + `tests/test_job_execution.py` only for the smallest execution-context seam if required
- `src/a_conductor/job_control.py` + `tests/test_job_control.py` only for the smallest injected-backend assembly seam if required
- `src/a_conductor/native_operations.py` + `tests/test_native_operations.py` only to consume the bounded execution-context protocol change
- this WO, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`

## Forbidden scope

- GE-6 scheduler or PR #119 graph-dispatch semantics
- `supervised_command_runner.py` / live process launch in this slice
- provider DB/live gateway/user secrets
- worker lease/fallback/heartbeat (AHA-4A/4B)
- PR #108 installer files
- North Star files
- A-Wiki mutation

## Acceptance

1. One opaque Claude operation maps to the existing `JobExecutionBackend` authority; no direct lifecycle mutation from the harness backend.
2. Durable job identity/work-order/project/worker context reaches the backend without hidden chat state.
3. Harness SUCCESS returns bounded evidence and the existing coordinator alone advances to VERIFYING.
4. Harness/provider/timeout/output failures map to typed durable recovery without declaring task completion.
5. Raw credential values and raw unbounded model output are never persisted as job evidence.
6. Provider readiness remains observed/fresh and fail-closed; no configured=>READY shortcut.
7. External launch is still delegated to an injected runner; production launch must later wrap canonical supervised dedup rather than bypass it.
8. Focused deterministic tests, regression tests, compileall, diff-check, scope/secret audit, and exact-head 3-OS CI pass before merge.

## Architecture decision for this slice

`DurableJobExecutionCoordinator` currently calls `backend.execute(operation_ref, worker_id)`. That is insufficient for a durable harness backend because resilient execution identity requires job/work-order/project context. Add only a bounded immutable execution context if RED tests prove it necessary; existing native backend may ignore fields it does not need.

A Claude backend may bind opaque operation definitions in memory, but must verify the durable context matches the pre-bound harness dispatch identity before calling AHA-3. It returns only `JobBackendResult`; the coordinator remains lifecycle authority.

The real Claude CLI process/supervision adapter is deliberately a separate non-overlapping micro-slice after this backend contract is green. It must reuse `SupervisedCommandRunner` / `DuplicateExecutionGuard`, not recreate them.

## Safety gate

Verified before mutation:
- base/current main `5cc417c92450eba796fa9af1cf3da037663b1eea` contains PR #119 final head;
- isolated branch/worktree were absent before creation;
- PR #108 + North Star candidate scope overlap = none;
- A-Wiki main inspected read-only at `290626ba16272f54742b6ebac8981629b04b3131`; its phase 8+ work remains HOLD, and A-Conductor bridge additions are allowed;
- shared dirty root remains untouched.

`SAFE_TO_MUTATE = YES` only inside this worktree and the allowed scope above.

## Checkpoint — GPT replaced blocked GLM archaeology lane

Read-only archaeology completed against current source:
- `SupervisedCommandRunner` already owns canonical `DuplicateExecutionGuard`, durable execution records, attach/reuse decisions, launch/inspect/collect, bounded result mapping;
- `NativeCommandSpec` already carries `environment_overrides` and `NativeExecutionScope` already carries an explicit override-key policy;
- current supervised runner validates argv but does not propagate `NativeCommandSpec.environment_overrides` into `SupervisedLaunchPlan`;
- `SupervisedLaunchPlan` currently has no environment field;
- `OwnedProcessSpec` already supports in-memory environment overrides, but its safety allowlist currently permits only `SERENA_HOME`;
- `supervised_child.py` inherits the sanitized supervisor environment and explicitly does not persist environment/argv in result JSON.

Recommended future seam: adapt `ClaudeCodeInvocation -> NativeCommandSpec -> SupervisedCommandRunner`; resolve credential references only immediately before building the NativeCommandSpec. Extend supervised environment propagation narrowly; do not create a Claude-specific process supervisor or duplicate guard.

## Checkpoint — durable Claude backend local implementation

Implemented:
- immutable `JobExecutionContext` carrying durable job/work-order/project/worker/attempt identity into the existing backend seam;
- existing native backend migrated to consume the context without changing native operation authority;
- optional typed `JobBackendResult.error_code`; existing coordinator remains sole state-transition/recovery authority;
- new `ClaudeCodeJobBackend` with opaque operation registry, exact identity checks, injected provider state, accepted AHA-3 adapter reuse, evidence digest only, and typed provider/harness/unknown-execution failures;
- no scheduler/store/lifecycle/process runner/duplicate guard added.

Verification so far:
- Claude backend + job execution + native operations: **33 passed**;
- provider/harness/job-control/graph/dedup/supervised regression set: **106 passed**;
- full local run: **1398 passed, 4 skipped**; 31 failures + 8 errors were confined to pre-existing machine-specific PermissionError instance-file tests and local GPU framebuffer tests, outside changed scope.

Final local gate: compileall PASS; diff-check PASS; exact changed scope = allowed files only; bounded secret scan PASS; latest main overlap = NONE. Next: commit/push Draft PR, remote diff audit, exact-head 3-OS CI.
