# WO-P1-218 — ZRA-2 Phase C0 independent review gate

Status: COMPLETE / CHANGES_REQUIRED
Parent: WO-P1-216 / PR #296 / Issue #214
Review target: `ade1628247a4512fa879c10bfd093d14f51d487f`
Owner: GPT-5.6 Sol independent reviewer
Mutable scope: this WO + `docs/reviews/WO-P1-218-zra2-c0-independent-review.md`
Forbidden: candidate source/tests, C1, Phase D, merge, live runtime/provider/credential state

## Objective

Independently falsify the Phase-C0 provenance chain before it can authorize Phase C1.

## Result

Verdict: `CHANGES_REQUIRED`

Blockers: 4 x P2, documented with deterministic reproducers in the review artifact:

1. success write-result is trusted without persisted-byte verification;
2. caller-forged `MaterializedReviewTask` can mint `DirectReviewRoute`;
3. foreign-worktree packet path passes suffix-only binding;
4. candidate HEAD is absent from deterministic review identity, allowing old-packet/new-HEAD replay.

PR #296 exact candidate CI is green, so these are source-contract blockers rather than CI/infrastructure failures.

## Next safe action

Create one bounded repair child from exact `ade1628...` that repairs the entire provenance chain, then require hosted CI + independent exact-SHA rereview. C1 remains HOLD.

`merge_performed=false`
