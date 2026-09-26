# GLM task packet — WO-P1-198 ZRA-4 deterministic batch identity

STATUS: HOLD. Do not mutate product source without explicit Issue #216 release after ZRA-3 and C1/C1b acceptance.

Read `docs/work-orders/WO-P1-198-zra4-deterministic-batch-identity-gate.md` and current durable parent state before doing anything.

## Goal

Derive provider batch identity from the actual selected GraphDispatch set; eliminate arbitrary caller-chosen batch identity on the ZRA-4 path while preserving existing provider admission and ParallelReady authorities.

## Pre-mutation gate

Record repo/worktree/branch/HEAD/origin-main, dirty state, accepted ZRA-3 SHA, accepted C1/C1b SHA, Issue #216 release evidence, open-PR overlap, owner/claim/lease/scope. If any material item is unknown or conflicting: `SAFE_TO_MUTATE=NO`, write checkpoint only, stop.

## Contract

Use deterministic `GraphDispatchKey.job_id` values. Sort the selected IDs canonically before hashing. Use a versioned domain separator such as `zra4-batch-v1`. Reject empty, foreign, malformed or ambiguous selections. A reordered input representing the same set must yield the same identity; a different run or set must not.

Do not add a second scheduler, provider store, admission semaphore, retry loop, dispatch identity, or review authority.

## RED-first minimum

Prove all cases from WO198, especially reordered 2/3-lane sets, restart stability, foreign run rejection, duplicate handling, empty-set rejection, different-set separation, and inability for arbitrary caller input to override the derived ID.

## Verification

Run focused tests plus ParallelReady/provider/elastic/graph regressions required by touched seams. Then compile/import, `git diff --check`, UTF-8/no-U+FFFD, secret scan, scope audit, hosted CI.

## Handback

Do not merge or self-accept. Freeze exact SHA, write `runs/WO-P1-198/result.md`, and provide durable branch/PR/result pointers. GPT-5.6 Sol retains integration acceptance. Live ZRA-4 fan-out remains separately gated.
