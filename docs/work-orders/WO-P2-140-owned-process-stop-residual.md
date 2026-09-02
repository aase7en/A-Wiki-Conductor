# WO-P2-140 ? Residual owned-process stop intermittency after WO129

Date: 2026-09-02
Owner: GLM-5.3 MAX / ZCode Goal + $a-loop
Integrator / merge authority: GPT-5.6 Sol MAX
Status: GLM_OWNED / DIAGNOSIS
Priority: P2 reliability residual
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-wo140-owned-process-stop-residual`
Branch: `fix/wo-p2-140-owned-process-stop-residual`
Base: origin/main@a28638c0e5d865803b985f08eb1d1db9c9d7dfc1 (PR #191 merged)

## Trigger evidence

- WO129 previously repaired the same hosted-Windows symptom in `test_real_dummy_process_start_idempotent_stop`; accepted repair head `661c86f9a30433006a01e996ed1ea46fde4a7e52`, merge `fae5c0d8a36a41eb172e2acb8dc88ca04658c4e9`, post-main CI `33509029840` green.
- PR #190 / WO138 exact head `8f60f045ba29c231f76ef28d589629b808e48012` changed only supervisor polling and its focused tests. CI run `33653167768` attempt 1 failed the unrelated real-Windows owned-process lifecycle assertion: expected `STOPPED`, observed `RECOVERY_REQUIRED`.
- Failed-job rerun of the same exact PR head passed; attempt 2 completed successfully on Windows/Ubuntu/macOS including packaging/Frozen Setup.
- Local exact test stress on the PR head: 10/10 PASS.
- Additional off-repo real lifecycle diagnostic loop after merge: 25/25 PASS, with no residual reason reproduced locally.

## Problem statement

The exact failure class that WO129 was intended to narrow has recurred once in hosted Windows CI after the accepted repair. The recurrence is not in the WO138 diff and is not yet deterministically reproducible. Treat it as a separate residual reliability defect, not as WO138 code failure and not as harmless noise.

## Goal

Obtain a deterministic or evidence-rich reproducer that identifies the exact `RECOVERY_REQUIRED` reason and observation sequence, establish root cause, then apply the smallest fail-closed repair only if evidence justifies one. Preserve exactly-once termination and ownership safety.

## Claimed scope

- `src/a_conductor/owned_process.py`
- `tests/test_owned_process.py`
- `docs/work-orders/WO-P2-140-owned-process-stop-residual.md`
- `COLLAB.md` for claim/release only
- off-repo diagnostic scripts/artifacts that contain no secrets

## Forbidden

- `src/a_conductor/supervised_execution.py` / WO137
- `src/a_conductor/supervised_command_runner.py` / WO138
- provider/UI/scheduler/job/graph authority
- WO134 evidence-dialog scope
- WO096 live Workers/tunnels/binaries/credentials
- production/live process mutation beyond bounded dummy-runtime tests
- weakening ownership mismatch/unknown fail-closed behavior merely to make CI green

## Investigation gate

No production edit until all applicable items are satisfied:

1. Reproduce or capture the exact `RECOVERY_REQUIRED` reason/sequence from the real lifecycle.
2. Distinguish observer UNKNOWN, MISMATCH, PID metadata drift/cleanup, termination result, and ordinary exit timeout.
3. Verify the accepted WO129 behavior is present in current main.
4. Add a deterministic RED at the highest stable seam for the proven causal path.
5. Run impact analysis before editing the production symbol.

## Acceptance

1. Root cause is evidenced, not guessed.
2. Regression test is RED before repair and GREEN after repair when a repair is required.
3. No second termination side effect is introduced.
4. Pre-termination UNKNOWN/MISMATCH remains fail-closed; post-termination uncertainty cannot manufacture STOPPED truth.
5. PID metadata cleanup remains exact-PID guarded.
6. Focused owned-process + observer/runtime matrices pass.
7. Repeated real-Windows lifecycle stress exceeds the historical failure window.
8. Exact-head independent review, CI, post-main verification, defect-memory/SSoT closeout complete before release.

## Initial checkpoint

`SAFE_TO_MUTATE = YES` for this isolated worktree and claimed scope. No source/test mutation has occurred. Current evidence is insufficient to choose a repair; next action is diagnosis/reproducer only.

## Diagnosis checkpoint 1 - hosted timing correlation

Additional deterministic evidence narrows the failure class without claiming root cause:

- PR #190 CI `33653167768` attempt 1: `test_owned_process.py` = `1 failed, 27 passed in 9.64s`; the real lifecycle returned `RECOVERY_REQUIRED`.
- Same exact head, attempt 2: the file completed `28 passed in 2.01s`.
- Historical pre-WO129 incident `33497112619` attempt 1: `1 failed, 24 passed in 9.02s`; rerun = `25 passed in 2.25s`.
- Historical pre-WO129 incident `33497483113` attempt 1: `1 failed, 24 passed in 9.21s`; rerun = `25 passed in 2.41s`.
- Current-main off-repo stress after PR #190 merge: sequential real lifecycle 25/25 PASS; 4-way concurrent real lifecycle 40/40 PASS.

The repeated ~9s failure-file runtime versus ~2s successful runtime is consistent with at least one bounded PowerShell/process-observation timeout plus recovery/cleanup overhead. This is an **inference**, not yet a proven reason code. Current competing causal paths remain:

1. terminator subprocess timeout -> `PROCESS_STOP_FAILED`;
2. post-termination CIM inspection timeout/UNKNOWN consuming the stop deadline -> `PROCESS_EXIT_OWNERSHIP_UNCERTAIN`;
3. less likely PID metadata change/cleanup failure.

WO129 changed only post-termination UNKNOWN re-observation; it did not make the real integration assertion print `reason_code`. Therefore the old and new hosted failures cannot yet prove which path occurred. No production fix is authorized by this checkpoint. Next diagnostic must surface the exact reason without weakening fail-closed behavior.

## GLM ownership transfer checkpoint — 2026-09-03

- Branch reconciled with origin/main@a28638c0e5d865803b985f08eb1d1db9c9d7dfc1; integration HEAD before GLM mutation: 260ce722de25fe5a2af95c7c57211857dbcaaaa7.
- GLM-5.3 MAX / ZCode Goal + $a-loop now owns the declared mutable WO140 scope. GPT-5.6 Sol MAX remains architecture, exact-SHA acceptance, PR/CI, merge, post-main, and final authority.
- No production/test mutation has occurred in WO140 yet. Diagnosis/root-cause + deterministic RED remain mandatory before any repair.
- GPT must not overlap owned_process.py / test_owned_process.py while GLM ownership is active.

## GLM diagnosis + diagnostic-surface checkpoint — 2026-09-03

**Identity at mutation start:** branch `fix/wo-p2-140-owned-process-stop-residual`, HEAD `01789c55889d668d94827a7f6179b1d74b2541fe` (= remote branch HEAD, clean tree). Declared integrated main `a28638c0` is an ancestor. Current `origin/main` advanced to `0c437d7a` with **docs-only** commits (WO142 reconciliation) — zero drift on `owned_process.py` / `test_owned_process.py`; noted for integrator reconciliation, not a blocker.

**Diagnosis (matrix executed, off-repo fault injection against the real controller):**
- `stop()` has 9 RECOVERY_REQUIRED/REFUSED return paths. Empirically timed ~5s signatures: terminator timeout/nonzero → `PROCESS_STOP_FAILED`; persistent post-termination CIM UNKNOWN → `PROCESS_EXIT_OWNERSHIP_UNCERTAIN` (wall 5.00s); slow teardown still-OWNED → `PROCESS_EXIT_UNCONFIRMED` (wall 5.00s). All three produce exactly the hosted evidence shape (RECOVERY_REQUIRED + ~5s bounded wait + ~9s file runtime).
- Pre-termination CIM timeout is EXCLUDED by hosted evidence: it yields `REFUSED/PROCESS_OWNERSHIP_UNKNOWN`, not RECOVERY_REQUIRED.
- WO129 behavior verified present in this tree (UNKNOWN→STALE post-termination → STOPPED; matrix PASS).
- Invariants held under every injected fault: terminate ≤ 1 call, never before OWNED proof, UNKNOWN/MISMATCH never STOPPED, exact-PID cleanup only after STALE + unchanged VALID metadata.
- Documented behavior (not a defect): the post-termination poll deadline is created AFTER `terminate()` returns, so a slow-but-successful terminator still receives a full fresh observation budget (worst-case stop wall ≈ 2× stop_timeout_seconds by design).
- **Verdict: exact hosted root cause is NOT locally provable** — three production paths match all available hosted evidence; local stress cannot reproduce (see below). Per the task rule, no invented fix.

**Impact analysis (pre-edit, deterministic callers/references):** `WindowsOwnedProcessController` constructed at `lifecycle_assembly.py:354`, `serena_operations.py`, `supervised_command_runner.py:435` + test suites; no caller overrides `stop()`. The change is purely additive (new `last_stop_diagnostics` attribute + recording inside `stop()`); zero behavioral change to any return path.

**RED → GREEN (diagnostic surface):**
- RED: 7 new tests in `tests/test_owned_process.py` (`test_stop_diagnostics_*`) failed with `AttributeError: last_stop_diagnostics` before implementation.
- Implementation: `stop()` now records `last_stop_diagnostics` on every return — `{state, reason_code, pid, elapsed_ms, initial/final_metadata_status, pre_termination_ownership, terminate_called, terminate_returned, post_termination_ownership_sequence (capped 64), post_termination_observation_count}` — secret-free (codes/pids/timings only), identical control flow.
- GREEN: `tests/test_owned_process.py` = **35 passed** (28 pre-existing + 7 new; two pre-existing monkeypatched-tick tests recalibrated for the two added `monotonic()` calls — same behavioral assertions).
- Real integration test upgraded: the STOPPED assertion now prints `controller.last_stop_diagnostics` on failure, so the next hosted occurrence self-identifies (state, reason_code, pid, elapsed, ownership sequence).

**Verification on the candidate tree:** owned_process + windows_observer + runtime_safety = **81 passed**; related supervisor suites (`test_supervised_execution`, `test_supervised_command_runner`, `test_claude_code_supervised_runner`, `test_serena_lifecycle_backend`) = **74 passed**; off-repo fault-injection matrix = 17/17 scenarios PASS (terminator timeout/nonzero/OSError-mapped-to-False, first-CIM-timeout-then-STALE, persistent UNKNOWN, UNKNOWN→MISMATCH, STALE-after-termination, metadata INVALID/UNKNOWN/ABSENT/changed, slow terminator, unlink failure implicit via cleanup guard); real-Windows lifecycle sequential stress = **30/30 PASS** (historical window was 25) and concurrent 4-way stress = **40/40 PASS** (70 total real lifecycles, zero failures); compileall + `git diff --check` + strict UTF-8 + diff secret scan all PASS.

Next safe action: GPT-5.6 Sol Max independent exact-SHA adversarial review → PR/CI/merge.
