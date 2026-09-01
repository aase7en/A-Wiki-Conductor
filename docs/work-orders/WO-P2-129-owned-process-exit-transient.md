# WO-P2-129 - Bounded Post-Termination UNKNOWN Observation

Date: 2026-09-01
Owner: GPT-5.6 Sol
Status: ACTIVE / RED-FIRST
Priority: P2 reliability; independent from AHA-7
Base: `origin/main@a9578681076442f54f62a2da9308cdd7505d5e4b`
Branch: `fix/wo-p2-129-owned-process-exit-transient`

## Trigger
Hosted Windows CI twice returned `RECOVERY_REQUIRED` from `test_real_dummy_process_start_idempotent_stop` on unrelated PRs. Both failed-job reruns passed without product changes, and the exact real-process test passed 5/5 locally for each incident.

## Source finding
Before termination, UNKNOWN/MISMATCH correctly blocks mutation. After `WindowsExactPidTerminator.terminate()` has already returned success, `WindowsOwnedProcessController.stop()` polls for exit but currently treats a single UNKNOWN observation as immediate recovery. `WindowsRuntimeObserver` can produce UNKNOWN when the bounded CIM inspection itself errors or returns incomplete facts.

## Goal
Permit bounded re-observation of UNKNOWN only after successful exact-PID termination. Do not issue another termination side effect. MISMATCH remains immediate recovery; persistent UNKNOWN remains recovery at the existing timeout.

## Mutable scope
- `src/a_conductor/owned_process.py`
- `tests/test_owned_process.py`
- this work order

## Acceptance
1. Pre-termination UNKNOWN remains `PROCESS_OWNERSHIP_UNKNOWN`; no terminator call.
2. Post-termination `UNKNOWN -> STALE` may reach STOPPED and cleanup exact unchanged PID metadata.
3. Post-termination MISMATCH remains immediate `PROCESS_EXIT_OWNERSHIP_UNCERTAIN` and does not cleanup metadata.
4. Persistent post-termination UNKNOWN remains `RECOVERY_REQUIRED`, preserving `PROCESS_EXIT_OWNERSHIP_UNCERTAIN`.
5. Existing STOP failure, PID metadata-change, stale/mismatch, and real Windows lifecycle tests remain green.
6. No generic retry utility, process registry, or second lifecycle authority is introduced.

## RED / repair checkpoint - 2026-09-01

RED reproduced the post-termination observation race deterministically: `UNKNOWN -> STALE` returned `RECOVERY_REQUIRED / PROCESS_EXIT_OWNERSHIP_UNCERTAIN` before the second observation. Existing safety controls remained green.

Repair is deliberately narrower than generic retry: only after exact-PID termination has returned success, UNKNOWN is remembered and re-observed inside the already-existing stop deadline. MISMATCH still returns recovery immediately. If UNKNOWN persists through the deadline, the result remains `RECOVERY_REQUIRED / PROCESS_EXIT_OWNERSHIP_UNCERTAIN`; an ordinary still-owned timeout with no UNKNOWN remains `PROCESS_EXIT_UNCONFIRMED`.

Evidence after repair:
- focused `tests/test_owned_process.py`: 28 passed;
- related observer/runtime/instance matrix: 117 passed;
- real Windows `test_real_dummy_process_start_idempotent_stop`: 10/10 consecutive passes;
- compileall + `git diff --check`: PASS.

Hosted evidence that motivated the slice remains separate: unrelated run `33497112619` attempt1 and PR #174 run `33497483113` attempt1 both failed this same real lifecycle assertion, while their failed-job reruns passed without product-code changes.

Status: IMPLEMENTED / SELF_REVIEW_PENDING. Defect Memory must be folded after the active WO122 closeout releases `DEFECT_LESSONS.md`; do not steal that shared scope.
