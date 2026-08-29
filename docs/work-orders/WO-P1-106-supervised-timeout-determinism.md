# WO-P1-106 — Supervised timeout determinism

Date: 2026-08-29
Owner: GPT-5.6 Sol integrator
Status: REVIEW_READY - LOCAL GREEN / PR PENDING
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-ci-timeout`
Branch: `fix/wo-p1-106-supervised-timeout-determinism`
Base: `origin/main@599e0dcd68173aca857a14d77b5628cd2333e673`

## Defect

Windows hosted CI intermittently fails `test_timeout_leaves_durable_running_execution_then_retry_attaches` because a one-second caller timeout returns `timed_out=False` with a supervisor recovery error. The same test failed on PR #132 attempt 1 and post-merge main run `33215329678`; reruns/local stress can pass.

Current suspect: `_poll_until_resolved()` checks `inspection.recovery_required` before checking whether the caller timeout elapsed during a slow `inspect()` call. Windows inspection uses bounded CIM/PowerShell and can consume most/all of the caller budget.

## Reuse / scope

Classification: **EXTEND** existing `SupervisedCommandRunner` timeout semantics; no scheduler, supervisor, retry loop, process launcher, or execution store replacement.

Allowed mutable scope:
- `src/a_conductor/supervised_command_runner.py`
- `tests/test_supervised_command_runner.py`
- this work order
- `DEFECT_LESSONS.md` only after verified prevention evidence
## Acceptance

1. Caller timeout is measured across inspection latency, not only between polls.
2. A result that becomes available remains authoritative even if the deadline also elapsed.
3. If the deadline elapses while inspection returns a non-result transient/recovery classification, caller result is `timed_out=True`; durable execution truth remains available for later attach/recovery.
4. Pre-deadline confirmed recovery remains a recovery result, not a timeout.
5. Existing duplicate attach, collection, ownership, and result semantics remain green.
6. Real Windows supervised integration is stress-tested repeatedly.
7. Exact-head 3-OS CI including Windows packaging/frozen smoke passes.

## TDD sequence

- RED deterministic fake-clock test: `inspect()` advances clock beyond caller budget and returns recovery-required; current code returns recovery instead of timeout.
- GREEN: smallest ordering/deadline repair in `_poll_until_resolved()`.
- Negative regression: recovery returned before deadline remains recovery.
- Positive regression: result available after inspection still wins and is collected.
- Run focused supervised suite repeatedly, broader execution/dedup/native suites, compile/diff/secret review, PR/CI, post-CI re-audit, merge.

## Boundaries

Forbidden: PR #131 worker lease/SSoT hotspots; connector/live tunnel-client; installer; North Star; provider secrets; shared stale root mutation.

## Verification checkpoint - 2026-08-29

- Hosted Windows evidence: PR #132 attempt 1 and post-merge main run `33215329678` failed the same timeout test with `timed_out=False`; reruns passed.
- Deterministic RED: late recovery after caller deadline = `1 failed, 2 passed`.
- GREEN after ordering repair: new timeout-order tests `3 passed`; complete supervised-command runner `11 passed`.
- Real Windows attach/timeout integration stress: `20/20` passed.
- Broader supervised/execution/dedup/native/job/Claude suite rerun: `75 passed`.
- `python -m compileall -q src`: PASS.
- `git diff --check`: PASS.
- Separate observed native temp-cleanup PermissionError did not reproduce in 12 isolated retries; tracked for independent fault-injection rather than speculative repair.

Next: final scope/secret audit -> commit/push -> exact remote diff -> 3-OS CI -> post-CI re-audit -> merge -> verify main.
