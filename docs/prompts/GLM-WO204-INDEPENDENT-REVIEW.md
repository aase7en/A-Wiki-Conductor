# MASTER /goal — WO-P1-204 independent exact-SHA review of repaired ZRA-2 Phase B

## Pointer

Read and execute this work order exactly:

`docs/work-orders/WO-P1-204-zra2-phaseb-no-clobber-independent-review.md`

Review target:

- parent GLM Phase-B candidate: `865ef3c18ebc5f4fb0f34f40dcee6851295baee4` / PR #280;
- GPT repair candidate: `1c8c159bba74346dce60e6abb7d01ecbd1c17b4e` / PR #281.

You are an INDEPENDENT REVIEWER. You are not the source author and must not become a co-author.

## Startup gate

Before substantive review:

1. read repository entry/routing rules and `DEFECT_LESSONS.md`;
2. re-pin repo, remote, review worktree, branch, HEAD, dirty state;
3. fetch exact target SHAs without mutating target branches;
4. verify PR #281 base/head identities exactly;
5. verify every hosted CI job for exact `1c8c159bba74346dce60e6abb7d01ecbd1c17b4e` is terminal SUCCESS.

If CI is still running/failing, SHA/base drifted, or ownership is ambiguous: write a durable checkpoint with the blocker and STOP. Do not poll/wait in a loop.

## Review mode

Review source/tests READ-ONLY.

Do NOT:

- edit candidate source/tests;
- fix findings yourself;
- commit on PR #280/#281 branches;
- rebase/reset/cherry-pick/amend candidate branches;
- merge any PR;
- mutate live Worker/provider/credential/runtime state.

Writable evidence is limited to the WO204 review lane as defined in the work order.

## Core question

Does exact repair SHA `1c8c159...` truthfully close the Phase-B P1 no-clobber race while preserving existing authority boundaries and cross-platform fail-closed behavior?

You must attempt to falsify the repair, not merely rerun its tests.

## Mandatory adversarial program

Execute the A–F matrix in WO204, including at minimum:

- compare parent `865ef3c...` vs repair `1c8c159...` exactly;
- prove legacy `NativeFileSystem.write_text()` semantics were not changed;
- reproduce different-byte target creation after initial absence observation and before final publication; repaired path must preserve conflicting bytes and surface `REPAIR_TASK_COLLISION`;
- independently exercise `NativeFileSystem.create_text_if_absent()` with existing target and concurrent same-path creators;
- repeat same-input concurrent materializer calls;
- test mutation-disabled, missing parent, directory target, size bound, UTF-8 bytes/hash;
- inspect root/symlink confinement interaction;
- inspect unsupported hard-link failure behavior — no fallback to clobber;
- challenge whether `os.link` assumptions are portable across Windows/Linux/macOS and clearly scope unsupported network/reparse/shared-filesystem cases;
- attempt at least one novel counterexample that is not already in PR #281 tests;
- inspect monkeypatch/barrier tests for vacuity or production-path bypass;
- confirm no scheduler/provider/review/lease/retry/filesystem authority duplication.

Use deterministic barriers/fault injection instead of sleeps when possible.

## Verification

Run the minimum verification floor from WO204 and add only justified adversarial commands.

Do not weaken tests. A test failure is evidence to investigate, not permission to edit the candidate.

## Result

Write the durable review result with:

- exact candidate/parent SHA;
- PR base/head + CI status;
- commands/results;
- adversarial attempts;
- findings P0/P1/P2/P3;
- explicit answers to A–F;
- one verdict only: `PASS`, `CHANGES_REQUIRED`, `BLOCKED`, or `SOURCE_DRIFT`;
- `merge_performed=false`;
- next safe action.

Commit/push ONLY the allowed review evidence on the WO204 review branch, then STOP at GPT acceptance gate.

## Resume semantics

If invoked again, read WO204 durable checkpoint/result first and resume unfinished READY review steps only. Do not restart completed experiments without source/CI drift.

## External gates

STOP immediately on:

- non-terminal CI;
- source/base drift;
- mutation required to continue;
- missing authority;
- unknown runtime/filesystem semantics that cannot be proven safely;
- GPT acceptance/merge/post-main gate.

At a gate, finish only the current atomic safe step, checkpoint exact state, report next safe action, then STOP.