# WO-P1-107 — Native timeout temp cleanup

Date: 2026-08-29
Owner: GPT-5.6 Sol integrator
Status: MERGE_READY - EXACT-HEAD CI GREEN / POST-CI RE-AUDIT PASS
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-native-timeout-cleanup`
Branch: `fix/wo-p1-107-native-timeout-cleanup`
Base: `origin/main@df6819213e0489f3b02a86c3d63f9045139e2da5` (reconciled after PR #134)

## Defect evidence

A broader local execution suite produced `PermissionError [WinError 32]` while `TemporaryDirectory` removed `stderr.bin` immediately after a subprocess timeout. `NativeSubprocessRunner.run()` then raised `COMMAND_EXECUTION_FAILED` instead of returning its already-known timeout result. Twelve isolated retries passed, so production mutation requires deterministic fault injection first.

## Classification / scope

**EXTEND** the existing synchronous native-runner cleanup boundary. No helper process, detached cleaner, scheduler, retry lifecycle, or execution store.

Allowed:
- `src/a_conductor/native_execution.py`
- `tests/test_native_execution.py`
- this WO
- `DEFECT_LESSONS.md` after verified prevention

Forbidden: PR #131/SSoT hotspots; WO106/PR #134; connectors/tunnel-client; installer; North Star; provider secrets.
## Acceptance

1. A transient `PermissionError` during temp-tree removal cannot convert an already-known timeout/result into `COMMAND_EXECUTION_FAILED`.
2. Cleanup retry is finite and catches only `PermissionError`.
3. Unrelated `OSError` fails without cleanup retry.
4. Persistent cleanup lock terminates after a finite budget with an explicit cleanup failure.
5. Output handles are closed before cleanup begins.
6. Tests inject cleanup failures; no wall-clock sleep is required for unit behavior.
7. Existing native execution security/scope/environment/output limits remain unchanged.
8. Exact-head 3-OS CI passes before merge.

## First RED

Fault-inject `shutil.rmtree` for only `a-conductor-exec-*`: fail twice with `PermissionError`, then delegate to real removal. A real timeout command must still return `timed_out=True`. Current one-shot `TemporaryDirectory` cleanup is expected to fail this test.

## Verification checkpoint - 2026-08-29

- Real broader-suite observation: one WinError 32 on `stderr.bin` after timeout.
- Isolated baseline retries before mutation: 12/12 passed, so no speculative fix was made.
- Deterministic fault injection RED: transient cleanup lock converted timeout into `COMMAND_EXECUTION_FAILED`.
- GREEN public fault test: transient lock twice then success preserves `timed_out=True`.
- Staff-review RED: `mkdtemp()` failure initially escaped raw `OSError`; repaired to preserve `COMMAND_EXECUTION_FAILED` contract.
- Native execution suite: 21 passed.
- Broader native/supervisor/dedup/job/Claude regression: 67 passed.
- compileall PASS; `git diff --check` PASS.
- No new process, detached cleaner, scheduler, store, or background lifecycle.

PR #135 checkpoint: head 0431c32f794c99f8fa1145a42a39e22d9ec5c44b; exact-head CI run 33219590720 passed Windows test plus Ubuntu/macOS cross-platform smoke. Remote diff = exactly four claimed files, one commit, no review/comment findings, base/head unchanged, CLEAN/MERGEABLE.

Next: commit this final checkpoint -> require CI green on the new documentation head -> post-CI re-audit -> merge -> verify accepted main.

## Reconcile checkpoint

- Fast-forwarded from `599e0dc` to accepted main `df681921` after PR #134 merged; no source/test conflict.
- Defect lesson #16 was appended only after #134 released `DEFECT_LESSONS.md`, preserving lesson #15.
- Post-reconcile native + supervised: `32 passed`; broader execution/supervisor/job: `59 passed`.
- compileall/diff PASS.
