# WO-P1-173 — R5 Windows parent-path settings fail-closed repair

Date: 2026-09-10 (Asia/Bangkok)
Status: CLAIMED / R3 BOUNDED SUCCESSOR REPAIR
Owner: GPT-5.6 Sol integrator implementation lane
Parent: WO-P1-168 R4 / PR #242 @ `7d0fd83bb5608a4ab025d5000203cbad2a31831f`
Trigger: independent GLM R3 review on PR #242, verdict `CHANGES_REQUIRED`, P0=0 / P1=0 / P2=1

## Goal

Close the Windows-only fail-open where `.claude` exists as a regular file and
`os.stat(<worktree>/.claude/settings*.json)` raises `FileNotFoundError` / winerror 3,
which R4 currently interprets as an absent settings file. The harness must distinguish
"settings path absent because parent is absent" from "settings path cannot exist because
its parent exists but is not a directory" and fail closed before runner invocation.

## Risk / authority

R3 because this is a settings-confinement fail-open repair. GPT defines the failure model,
owns implementation and integration; a genuinely independent external reviewer must review
the frozen R5 SHA before acceptance. No self-merge.

## Worktree / branch / base

- Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo173-r5`
- Branch: `gpt/wo-p1-173-r5-claude-parent-boundary`
- Base/frozen predecessor: `7d0fd83bb5608a4ab025d5000203cbad2a31831f`

## Mutable scope

- `src/a_conductor/claude_code_harness.py`
- `tests/test_claude_code_harness.py`
- this WO only

Everything else is read-only. No provider config, secret, runtime DB, installed app,
process, `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`, PR #242 branch, or other lane mutation.

## Failure model

1. Missing `.claude` directory -> both settings files are legitimately absent -> continue.
2. Existing `.claude` directory + missing one settings file -> that file is legitimately absent -> continue.
3. `.claude` exists but is not a directory -> `CLAUDE_SETTINGS_INVALID` before runner.
4. Parent lookup error/loop/ambiguous filesystem state -> `CLAUDE_SETTINGS_INVALID` before runner.
5. Existing settings non-regular/outside-root/replaced/oversized/ambiguous JSON retains R4 behavior.
6. No weakened fallback and no platform-specific semantic divergence.

## RED first

Add a regression that creates `.claude` as a regular file and executes the harness. It must
raise `CLAUDE_SETTINGS_INVALID` and runner calls must remain empty. The test must run on Windows
and POSIX; it is specifically required to reproduce the R4 Windows failure before the repair.

## Smallest intended repair

On initial settings-path `FileNotFoundError`, inspect the immediate parent without following
symlinks. Return `None` only when the parent itself is absent. If the parent exists and is not
a directory, or parent inspection is otherwise ambiguous, raise `CLAUDE_SETTINGS_INVALID`.
Do not add a new filesystem authority or change later identity/bounded-read checks.

## Verification

- prove RED against exact predecessor behavior on Windows;
- focused harness/backend/host suites;
- related Claude/supervised/provider suites appropriate to the changed boundary;
- `compileall` and `git diff --check`;
- exact changed scope and credential-pattern scan;
- freeze exact SHA, push, CI, independent exact-SHA R3 review.

## Stop conditions

Stop on ownership conflict, unexpected scope drift, repeated same failure without new evidence,
secret/provider/runtime requirement, or any need to weaken fail-closed behavior.

## R5 implementation checkpoint

Durable claim: Issue #233 comment `5619928273`.

RED on exact predecessor behavior (Windows 11):
- `test_settings_parent_regular_file_fails_closed_before_runner`
- result before source repair: **1 failed**, `Failed: DID NOT RAISE ClaudeCodeHarnessError`.

Minimum repair:
- on initial settings-path `FileNotFoundError`, inspect the immediate parent with `follow_symlinks=False`;
- parent missing -> settings legitimately absent;
- parent exists but is not a directory, cannot be inspected, cannot be resolved, or resolves outside the trusted worktree -> `CLAUDE_SETTINGS_INVALID`;
- all later R4 regular-file/identity/size/bounded-read checks remain unchanged.

GREEN evidence before freeze:
- focused Claude harness/backend/host matrix: **65 passed / 7 expected skips**;
- related Claude/provider/supervised matrix: **199 passed / 7 expected skips**.

A disposable junction command was attempted as an additional probe but its transport returned no typed stdout evidence; it is intentionally **not** counted as verification.

## Next safe action

Run compile/diff/scope/credential-pattern gates, freeze/push the R5 SHA, open a Draft successor PR, then request a genuinely independent exact-SHA R3 rereview.
