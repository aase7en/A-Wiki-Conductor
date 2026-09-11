# MASTER /goal — WO-P1-212 independent launcher-stack review

You are ZCode GLM-5.3 acting strictly as an independent reviewer.

Read and execute:

`docs/work-orders/WO-P1-212-launcher-stack-independent-review.md`

## Immutable target

Parent:

`8339e4c9e15c8eefd94693245ef9ef4b627c00de` / PR #266

Combined repaired child:

`f7d23c96690f7cdb94d2ebe62cac6d4669ad6f00` / PR #285

Do not review a different SHA.

## Startup gate

Before substantive review:

1. read repo governance/routing and `DEFECT_LESSONS.md`;
2. re-pin repo/remote/review worktree/branch/HEAD/dirty state;
3. fetch exact parent/child without mutating candidate branches;
4. verify PR #285 base is PR #266 branch and exact head above;
5. verify hosted CI for exact parent and child is terminal SUCCESS;
6. verify no unexplained source drift.

If any identity is wrong/unknown, write durable `SOURCE_DRIFT`/`BLOCKED` review result and STOP.

## Reviewer-only rule

Candidate source/tests are READ-ONLY.

Do not:

- fix findings yourself;
- edit PR #266/#285 branch;
- deploy/rematerialize Worker launchers;
- restart any Worker/process;
- inspect or print secrets;
- merge/rebase/reset/cherry-pick/amend/force-push candidate branches.

You may write only WO212 review evidence in the review lane.

## Review mission

Try to falsify the combined launcher hardening.

Do not merely rerun authored tests.

Review all A–H sections of WO212, especially:

- actual live-shaped `$RuntimeProcess.WaitForExit()` + stale direct ExitCode branch;
- older `Wait-Process -Id` variant;
- preservation of `try/finally`, credentials, doctor/preflight and environment cleanup;
- archive-before-new-run ordering;
- WaitForExit -> Refresh -> stable captured exit code;
- numeric lifecycle logs;
- stale terminal branch removal;
- byte idempotency;
- structural marker guard;
- partial migration fail-unchanged behavior;
- comment/free-text marker false positives;
- ambiguous launcher fail-unchanged behavior.

## Mandatory marker adversarial matrix

At minimum independently probe:

1. harmless comment containing `runtime-archive`;
2. quoted free string containing `runtime-archive`;
3. exact archive assignment only;
4. exact `$RuntimeExitCode = $RuntimeProcess.ExitCode` only;
5. Refresh only;
6. `exit $RuntimeExitCode` only;
7. archive + Refresh only;
8. capture + exit only;
9. complete generated hardening;
10. complete markers plus unrelated comments;
11. archive assignment using double quotes;
12. whitespace variants;
13. marker-looking text inside PowerShell comment;
14. duplicated structural marker;
15. complete-looking marker set surrounding a stale or ambiguous terminal seam.

For each, classify expected behavior and compare actual behavior.

A complete-marker guard that can classify an unsafe stale launcher as already hardened is a blocking source finding.

## Mandatory novel counterexample

Attempt at least one case absent from candidate tests.

Prefer deterministic pure-string experiments. No live mutation.

## Verification floor

Run:

```text
python -m pytest -q tests/test_instance_create.py
python -m pytest -q tests/test_setup_wizard.py tests/test_ps1_encoding_and_quoting.py tests/test_doctor_fixes.py
python -m compileall -q src/a_conductor/instance_create.py
git diff --check 8339e4c9e15c8eefd94693245ef9ef4b627c00de..f7d23c96690f7cdb94d2ebe62cac6d4669ad6f00
```

Then execute justified adversarial string-only probes.

If read-only live Worker launcher files are available safely, test the transformation in memory only and report summarized booleans. Do not print launcher contents or secrets. If unavailable, record the gap honestly.

## Verdict

Write only one final verdict:

- `PASS`
- `CHANGES_REQUIRED`
- `BLOCKED`
- `SOURCE_DRIFT`

P0/P1/P2 means CHANGES_REQUIRED.

P3 may PASS with advisory.

## Durable handback

Write:

`docs/reviews/WO-P1-212-launcher-stack-review.md`

Include exact SHAs, PR/CI state, tests, adversarial probes, A–H answers, findings, live-read status, verdict, `merge_performed=false`, next safe action.

Commit/push only the review evidence on the WO212 review branch.

Then STOP at GPT/integrator acceptance gate.

Do not continue into deployment or unrelated backlog work.