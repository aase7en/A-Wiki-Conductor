# WO-P1-145 — Exact-PID terminator ambiguous outcome after hosted timeout

Date: 2026-09-03
Owner: GPT-5.6 Sol MAX
Status: CLAIMED / DIAGNOSIS
Priority: P1 reliability
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-wo145-terminator-outcome`
Branch: `fix/wo-p1-145-terminator-outcome`
Base: `origin/main@272953a366f93a7f7dbd8e1e8060fc0f1bacdb88`

## Trigger — deterministic hosted evidence

PR #195 / WO144 CI run `33682227146`, attempt 1, Windows job `100421244222` failed the real lifecycle test after WO140 diagnostics were already on main.

Observed exact stop diagnostic:
- state = `RECOVERY_REQUIRED`
- reason_code = `PROCESS_STOP_FAILED`
- pid = `4428`
- elapsed_ms = `5266.0`
- pre_termination_ownership = `OWNED`
- terminate_called = `True`
- terminate_returned = `False`
- post_termination_observation_count = `0`
- post_termination_ownership_sequence = `[]`

This closes WO140's prior causal ambiguity: this recurrence is at the exact-PID terminator boundary, not post-termination CIM UNKNOWN/teardown.
## Problem statement

`WindowsExactPidTerminator.terminate()` collapses PowerShell timeout, launch error, and nonzero exit into boolean `False`. `WindowsOwnedProcessController.stop()` treats every `False` as definitive `PROCESS_STOP_FAILED` and returns before any side-effect-free exact-PID re-observation.

A `subprocess.TimeoutExpired` is an ambiguous mutation outcome: `Stop-Process` may have terminated the exact authorized PID before the PowerShell wrapper exceeded its 5-second wall timeout. Retrying termination is forbidden; blindly declaring failure may also be false.

## Goal

Establish the smallest fail-closed behavior that truthfully resolves an ambiguous terminator outcome without repeating the termination side effect and without weakening exact-PID ownership proof.

No production repair is authorized until deterministic RED evidence proves the selected boundary.

## Claimed mutable scope

- `src/a_conductor/owned_process.py`
- `tests/test_owned_process.py`
- `docs/work-orders/WO-P1-145-terminator-ambiguous-outcome.md`
- `DEFECT_LESSONS.md` only after accepted root cause/repair evidence

No shared `CURRENT-WORK.md` / `handoff.md` / `COLLAB.md` mutation while WO144 owns those hotspots.

## Forbidden

- no second termination attempt;
- no broad process kill;
- no blind timeout increase;
- no live Worker/tunnel/process maintenance;
- no weakening pre-termination OWNED proof, MISMATCH/UNKNOWN fail-closed semantics, or exact PID metadata cleanup;
- no observer/runtime/UI/provider/scheduler changes without new evidence and explicit scope expansion.
## Investigation / RED gate

Before production edit:
1. Attempt GitNexus impact; if unavailable/unindexed, record tool failure without fabricating verification.
2. Reproduce current behavior when the terminator reports an ambiguous/failed outcome but exact-PID observation proves the target is already STALE.
3. Prove no second termination call is needed or permitted.
4. Cover the same failed-terminator boundary with subsequent OWNED, UNKNOWN, and MISMATCH observations.
5. Preserve unchanged exact PID metadata before cleanup; changed/invalid/unknown metadata remains recovery.
6. Compare a bounded re-observation repair against a native exact-PID terminator replacement; choose the smaller trust-preserving change from evidence, not preference.

## Acceptance

- hosted root-cause evidence is preserved exactly;
- RED precedes production repair;
- exact termination side effect count remains <= 1;
- ambiguous terminator outcome + proven STALE exact PID may complete only after unchanged VALID PID metadata;
- ambiguous outcome + OWNED remains `PROCESS_STOP_FAILED`;
- UNKNOWN/MISMATCH never manufacture STOPPED;
- no new broad kill or generic retry utility;
- focused owned-process suite passes;
- observer/runtime/supervisor related matrices pass;
- native Windows real lifecycle stress exceeds the recurrence window;
- compileall, `git diff --check`, strict UTF-8, scope and secret audits pass;
- exact-SHA independent review, hosted CI, expected-SHA merge, post-main CI and defect-memory/SSoT closeout complete before release.

## Initial safety gate

`SAFE_TO_MUTATE = YES` only for this isolated worktree and the declared WO145 scope after this claim checkpoint is committed. Primary checkout remains protected.

Next safe action: commit/push this WO claim, then create deterministic RED tests before touching production code.

## Pre-edit tool gate — 2026-09-03

GitNexus CLI is available through `npx gitnexus`, but this A-Conductor worktree/repository is not indexed: `gitnexus status` returned `Repository not indexed. Run: gitnexus analyze`. A direct impact attempt could not bind this unindexed repository and listed only other indexed repos. Per policy this is `UNVERIFIED — tool/index unavailable`; no system DLL or unrelated index mutation was attempted. Deterministic caller/reference analysis remains required before edit.

## RED → GREEN repair checkpoint — 2026-09-03

Hosted evidence from PR #195 attempt 1 removed the prior WO140 ambiguity: `PROCESS_STOP_FAILED`, `terminate_returned=False`, `elapsed_ms=5266.0`, and zero post-termination observations prove the recurrence reached the PowerShell exact-PID terminator boundary.

RED-first tests reproduced four missing semantics: failed terminator outcome followed by STALE, OWNED, UNKNOWN, and MISMATCH. Baseline: **4 failed / 35 deselected** because current code returned immediately on boolean `False` without re-observation.

Repair is intentionally bounded: after the already-authorized exact-PID terminator returns `False`, perform exactly one side-effect-free exact-PID ownership observation. Never invoke termination again and never extend the mutation timeout. `OWNED` remains `PROCESS_STOP_FAILED`; `UNKNOWN`/`MISMATCH` become `PROCESS_EXIT_OWNERSHIP_UNCERTAIN`; only proven `STALE` may continue to the existing unchanged-exact-PID metadata guard and cleanup.

A fifth regression proves STALE is insufficient when PID metadata changed: `1234 -> 9999` remains `PID_METADATA_CHANGED` and metadata is retained.
Verification on the repaired working tree:
- `tests/test_owned_process.py` = **40 passed**.
- owned-process + Windows observer + runtime safety = **86 passed**.
- supervised execution/command/Serena/Claude lifecycle = **74 passed**.
- realistic native-Windows ambiguity probe: real dummy PID terminated once by the real `WindowsExactPidTerminator`, wrapper deliberately reports `False`, controller observes STALE and completes safely = **15/15 PASS**.
- normal real Windows lifecycle = **30/30 PASS**.
- `python -m compileall -q src/a_conductor`, `git diff --check`, strict UTF-8/U+FFFD, scope and added-line secret scans = PASS.
- GitNexus impact remains `UNVERIFIED — A-Conductor repository not indexed`; no unrelated index/system mutation was performed.

Next safe action: record Defect Lesson #50, commit/push exact candidate, then require independent exact-SHA adversarial review before PR/CI/merge.
