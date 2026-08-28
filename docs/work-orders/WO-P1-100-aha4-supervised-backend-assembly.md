# WO-P1-100 — AHA-4 supervised durable backend assembly

Date: 2026-08-28
Owner: GPT-5.6 Sol integrator
Status: ACTIVE — TDD
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-aha4-assembly`
Branch: `feat/wo-p1-100-aha4-supervised-backend-assembly`
Base/reconciled main: `origin/main@7db34048a0dd002b9bfbe41408c83c7ec18df2ad`
Parent: AHA-4 / PR #124 supervised Claude runner

## Goal

Join the accepted durable `ClaudeCodeJobBackend` to the accepted `SupervisedClaudeCodeRunner` at the real per-job execution boundary. A durable job attempt must create one identity-bound supervised Claude runner using the exact job/work-order/project/worker plus dispatch branch/HEAD and opaque provider refs, while reusing existing lifecycle, duplicate execution, stores, and recovery authority.

## Reuse gate

Classification: **REUSE + WRAP + EXTEND**.
Reuse `ClaudeCodeJobBackend`, `ClaudeCodeHarnessAdapter`, `build_supervised_claude_code_runner`, `DurableJobExecutionCoordinator`, `DuplicateExecutionGuard`, execution store and supervised service. No new process runner, lifecycle, retry loop, scheduler, provider registry, job store, or memory system.

## Allowed scope

- `src/a_conductor/claude_code_job_backend.py` — narrow adapter-factory seam only if needed
- new `src/a_conductor/claude_code_job_assembly.py`
- new `tests/test_claude_code_job_assembly.py`
- focused `tests/test_claude_code_job_backend.py`
- this work order, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`

## Forbidden scope

- graph scheduler/dispatch semantics
- worker lease/fallback/heartbeat (AHA-4A/4B)
- provider DB/gateway/live credentials
- connector CR-2/CR-4 / PR #125
- installer PR #108
- North Star branch
- A-Wiki mutation
- live connector/model invocation

## Acceptance

1. Provider-unavailable/denied paths remain typed and do not resolve credential values or launch a process.
2. An accepted durable job attempt builds its Claude adapter lazily from the exact `JobExecutionContext`.
3. Supervised identity binds job/work-order/project/worker + dispatch worktree/branch/HEAD + non-secret runtime-profile ref.
4. Missing/invalid branch identity fails closed before reference resolution or external launch.
5. Opaque endpoint/credential refs resolve only inside `SupervisedClaudeCodeRunner.run()`.
6. Canonical `DuplicateExecutionGuard` remains the only duplicate-launch authority; timeout/unknown cannot blind relaunch.
7. Harness/model output remains bounded/redacted and only digest evidence reaches durable job state.
8. Existing fixed-adapter `ClaudeCodeJobBackend` callers remain backward compatible.
9. Deterministic RED→GREEN tests, focused/broad regression, compileall, diff/secret audit, remote diff audit and exact-head 3-OS CI pass before merge.

## Safety gate

Verified before mutation:
- repo/worktree/remote/branch/HEAD clean and exact;
- branch reconciled to `origin/main@7db34048a0dd002b9bfbe41408c83c7ec18df2ad`;
- PR #125 connector recovery and PR #108 installer scopes do not overlap this slice;
- North Star and shared dirty root remain protected;
- A-Wiki reuse check confirms Conductor owns dispatch/process control and must not duplicate A-Wiki brain logic;
- no live provider, connector, credential store, or A-Wiki mutation is required.

`SAFE_TO_MUTATE = YES` only inside this worktree and the allowed scope above.

## First TDD sequence

1. RED: prove a durable job cannot currently construct a per-job supervised Claude runner from its `JobExecutionContext`.
2. GREEN: add the smallest lazy adapter-factory seam and production assembly wrapper.
3. RED/GREEN: provider unavailable and missing branch fail before resolver/launcher.
4. Prove supervised fingerprint identity differs across durable job identity while raw secret values never enter fingerprint material.
5. Run regression/audit and PR loop.

## Implementation checkpoint — 2026-08-28

Implemented:
- `ClaudeCodeJobBackend` now accepts exactly one fixed adapter or lazy adapter factory; existing fixed-adapter callers remain compatible.
- new `SupervisedClaudeCodeAdapterFactory` builds `build_supervised_claude_code_runner` only after durable `JobExecutionContext` and provider state are known.
- supervised identity binds exact job/work-order/project/worker plus dispatch worktree/branch/HEAD and opaque provider reference digest.
- missing dispatch branch fails closed as `POLICY_DENIED` before reference resolution/launch.
- provider unavailable/rate-limited paths remain typed and do not resolve credentials or launch.
- repeated unknown/recovery fingerprint attaches/blocks through canonical `DuplicateExecutionGuard`; no blind relaunch.
- deterministic successful chain reaches durable `VERIFYING` through the existing coordinator.

Verification at `origin/main@7db34048a0dd002b9bfbe41408c83c7ec18df2ad`:
- first RED: missing `a_conductor.claude_code_job_assembly` module at collection.
- focused runner/backend/assembly: **25 passed in 1.49s**.
- broader Claude/provider/native/supervisor/dedup/job/graph regression: **237 passed in 13.43s**.
- `python -m compileall -q src/a_conductor`: PASS.
- `git diff --check`: PASS (line-ending warning only).
- changed-file scope: exactly 7 allowed files.
- bounded real-secret-prefix scan: PASS; no credential/private-key prefixes found.

Draft PR #130 opened from exact feature head. Next gate: push this truthfulness/formatting follow-up, re-audit exact remote diff, require exact-head Windows/Ubuntu/macOS CI, then merge only if green.
