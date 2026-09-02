# WO-P2-137 — Supervised child PID transient read recovery

Date: 2026-09-02
Owner: GPT-5.6 Sol integrator
Status: CLAIMED / RED_FIRST_PENDING
Priority: P2 reliability; blocks WO136 post-main closeout
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-wo137-supervised-unknown-observation`
Branch: `fix/wo-p2-137-supervised-unknown-observation`
Base: `origin/main@9a88b1d38d90bf8ce98dcef9a5108e270e8d2b48`

## Trigger evidence

- WO136 PR #187 exact-head CI `33611169181` passed.
- PR #187 merged as `9a88b1d38d90bf8ce98dcef9a5108e270e8d2b48`; merge tree equals reviewed tree.
- Post-main CI `33612208575` attempt 1 failed only `tests/test_supervised_command_runner.py`.
- Failure result hash decodes exactly to `SUPERVISED_LAUNCH_FAILED:CHILD_PID_READ_FAILED`.
- Local exact-tree target stress passed 20/20, then full supervised-suite stress reproduced the same failure class on run 5.

## Goal

Treat a transient `OSError` while reading startup `child.pid` as bounded not-ready evidence inside the existing startup poll budget, without retrying launch/start/termination or weakening malformed-PID/ownership failures.

## Mutable scope

- `src/a_conductor/supervised_execution.py`
- `tests/test_supervised_command_runner.py`
- optional focused `tests/test_supervised_execution.py` only if needed
- this work order

## Forbidden

- supervisor/child relaunch or termination retry authority
- `owned_process.py`, Windows observer/runtime-safety policy, scheduler/job/provider/UI code
- WO134 UI/control/test scope
- PR #183 / WO132 roadmap scope
- shared SSoT until the repair is accepted
- live Workers/tunnels/credentials/WO096/release publication

## Acceptance

1. RED deterministically injects `child.pid` read `OSError` followed by a valid PID and proves current launch fails too early.
2. Repair retries only `CHILD_PID_READ_FAILED` within existing `startup_poll_attempts` / delay; no second `controller.start()`.
3. Persistent read failure exhausts the same bounded startup budget and returns typed `CHILD_PID_READ_FAILED` recovery, not an infinite wait.
4. `CHILD_PID_INVALID` remains immediate typed recovery; malformed PID is never treated as not-ready.
5. Existing fast/nonzero/timeout/attach lifecycle tests remain green.
6. Repeated real-Windows supervised suite and the formerly failing cases are stable.
7. Focused + related + compileall + diff/UTF-8/scope audit pass before exact-SHA review/CI.

## Implementation checkpoint — 2026-09-02

Root cause was proven from post-main CI stderr SHA-256: the failed result maps exactly to `SUPERVISED_LAUNCH_FAILED:CHILD_PID_READ_FAILED`. A single transient Windows `OSError` while reading `child.pid` was converted to permanent recovery immediately despite an existing startup poll budget.

RED: two deterministic tests proved transient and persistent read failures were each attempted only once. Repair retries only typed `CHILD_PID_READ_FAILED` inside the existing startup poll budget; `controller.start()` remains exactly-once, malformed PID remains immediate typed recovery, and persistent read failure remains fail-closed after budget exhaustion. A guard also proves read-error then absent file returns the existing STARTING truth instead of stale recovery.

Evidence on the repaired working tree: focused supervised execution/runner 29 passed; related supervisor/recovery/owned-process matrix 94 passed; real Windows supervised-command suite stress 20 iterations x 11 tests = 220/220 passed. Before repair the same suite reproduced locally at iteration 5. One-process full-suite runs still hit documented environment/topology issues: optional GPU/Tk dependency failures in one interpreter and the known Windows 0x80000003 breakpoint when Tk/subprocess-heavy suites share a process. Hosted split-process CI remains the full-suite authority.

Next gate: static/scope audit -> commit/push exact SHA -> independent GLM-5.3 MAX long adversarial review -> repair if needed -> PR/exact-head CI/merge/post-main proof. GPT remains integration and merge authority.
