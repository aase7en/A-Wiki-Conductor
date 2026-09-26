# WO-P1-218 — independent review of ZRA-2 Phase C0 candidate

Status: COMPLETE / CHANGES_REQUIRED
Owner: GPT-5.6 Sol integrator
Review target: PR #296 exact `ade1628247a4512fa879c10bfd093d14f51d487f`
Parent: WO-P1-216 / Issue #214
Risk: R3 provenance and anti-replay
Merge authority: none in this review lane

## Mission

Independently falsify the GLM-authored Phase C0 implementation before C1 release. Review only; no candidate mutation and no self-merge.

## Result

Verdict: `CHANGES_REQUIRED`

P0=0, P1=0, P2=4.

Durable evidence: `docs/reviews/WO-P1-218-zra2-phase-c0-independent-review.md`.

The four blockers are:

1. foreign-worktree packet accepted by C0b because packet path is suffix-checked rather than bound to route worktree;
2. caller-forged MaterializedReviewTask/hash can mint DirectReviewRoute without proving C0a persistence;
3. exact reviewed HEAD is not in deterministic review identity, allowing old packet -> new HEAD replay;
4. C0a success path trusts create_text_if_absent result without exact persisted-byte read-back.

## Next safe action

Create one bounded child repair from exact candidate `ade1628...`, RED-first against all four deterministic repros, with no C1/Phase-D expansion. Reuse existing NativeFileSystem, scheduler/provider/lease/harness authority. Independent rereview required after repaired candidate freeze.

C1 remains HOLD.
