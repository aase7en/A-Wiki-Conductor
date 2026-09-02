# WO-P2-140 ? Residual owned-process stop intermittency after WO129

Date: 2026-09-02
Owner / integrator: GPT-5.6 Sol MAX
Status: CLAIMED / DIAGNOSIS
Priority: P2 reliability residual
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-wo140-owned-process-stop-residual`
Branch: `fix/wo-p2-140-owned-process-stop-residual`
Base: `origin/main@edac38d913a04d3ab2c7a95e726f77608abe49d0`

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
