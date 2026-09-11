# WO-P1-213 — ZRA-2 Phase-B fresh-main fold

Status: CANDIDATE_FROZEN_PENDING_HOSTED_CI
Parent: WO-P1-165 / Issue #214 / WO209 fold gate
Owner: GPT-5.6 Sol integrator
Risk: R3

## Objective

Fold the independently accepted Phase-B repaired tree onto the latest accepted `main` without merging the known-defective stacked parent PR #280 or temporarily advancing main to parent SHA `865ef3c18ebc5f4fb0f34f40dcee6851295baee4`.

## Authority

- accepted repaired source: `1c8c159bba74346dce60e6abb7d01ecbd1c17b4e` / PR #281;
- independent review: WO204 commit `4a63d912bb269f44e2c685d296cd5823218907c5`, verdict PASS, P0/P1/P2=0;
- candidate CI for `1c8c159...`: terminal SUCCESS;
- review-branch #282 CI failure is unrelated `test_owned_process.py::test_real_dummy_process_start_idempotent_stop` on docs-only review evidence and does not modify candidate source;
- fresh fold base: `a23149640750579c94369eb5a6730bba757ff772`.

## Fold method

A fresh branch/worktree was created from exact current `origin/main`.

The accepted activation + parent + repair changes were materialized with `git cherry-pick -n` and intentionally committed as one future fold commit. This prevents the known-defective intermediate source commit from becoming a new branch commit in the fold history.

## Exact reviewed-byte proof

Before metadata was added, all six accepted paths matched exact Git blob IDs from `1c8c159...`:

- `docs/work-orders/WO-P1-195-zra2-phase-b-materializer.md` → `d993c7c434b968ee62934c421a07a4e59e7391c4`
- `docs/work-orders/WO-P1-203-zra2-phase-b-no-clobber-publication.md` → `a1734d7718b725a5562c3d421ba193c59ad2f6bb`
- `src/a_conductor/native_execution.py` → `00ba4b07566fa64a44b9e21a23e0ac42891cc5e8`
- `src/a_conductor/zero_relay_repair_materializer.py` → `393ac0c7a180f8ed6115847233e30839ad494654`
- `tests/test_native_execution.py` → `a794f54fece1379daa318b5364ab4cdb9dd4047e`
- `tests/test_zero_relay_repair_materializer.py` → `d4dbab3e204029b6b52ebe7cbf42a1fbabfce198`

Any future drift of one of these accepted paths invalidates the fold and requires re-review.

## Verification on latest-main fold tree

- `tests/test_native_execution.py tests/test_zero_relay_repair_materializer.py` → 65 passed;
- `tests/test_agent_change_packets.py tests/test_claude_code_harness.py` → 107 passed, 1 POSIX-only FIFO skip;
- `tests/test_zero_relay.py tests/test_review_mailbox_adapter.py tests/test_goal_closeout.py` → 149 passed;
- total explicit regression floor: 321 passed, 1 expected platform skip;
- compileall for modified production modules → PASS;
- `git diff --cached --check` → clean.

## Mutable scope

Only:

- the six accepted reviewed paths above;
- this WO213 metadata document.

No scheduler/provider/review/job/lease/worker/runtime/credential authority is changed.

## External gate

After committing/pushing this exact fold candidate, hosted CI must run on the fresh-main candidate.

If CI is non-terminal: `BLOCKED_EXTERNAL_CI` and STOP.

If CI fails because of an owned deterministic defect: do not mutate reviewed bytes silently; classify the failure and require explicit adjudication.

If CI succeeds: GPT/integrator may perform final exact-SHA fold acceptance and merge, followed by post-main verification and Issue #214 Phase-C0 release.

`merge_performed=false` until that gate is satisfied.
