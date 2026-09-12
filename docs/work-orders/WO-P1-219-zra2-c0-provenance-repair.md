# WO-P1-219 — ZRA-2 Phase C0 provenance-chain repair

Status: ACTIVE / RED-FIRST
Parent candidate: WO216 / PR #296 / `ade1628247a4512fa879c10bfd093d14f51d487f`
Independent review: WO218 / `c5b04305154e229e3fd42d2092844ded6234a2ff`
Owner: GPT-5.6 Sol bounded repair lane
Branch: `fix/wo-p1-219-zra2-c0-provenance`
Base: `ade1628247a4512fa879c10bfd093d14f51d487f`
Risk: R3 identity / persisted provenance / anti-replay

## Scope

Mutable:

- `src/a_conductor/zero_relay_review_task.py`
- `tests/test_zero_relay_review_task.py`
- this WO evidence

Read-only:

- Phase C1 / `zero_relay.ReviewEvidence`
- scheduler/provider/lease/harness semantics
- external mailbox adapter
- live runtime/provider/credential state
- `DEFECT_LESSONS.md` while PR #293 owns that file

No merge or self-acceptance is authorized.

## Root cause

WO216 correctly reused existing filesystem and route aggregates but stopped one trust boundary too early in four places:

1. C0a trusted `NativeWriteResult` instead of proving persisted bytes after successful create;
2. C0b trusted a caller-constructible `MaterializedReviewTask` as provenance;
3. C0b checked packet path by suffix instead of exact selected worktree identity;
4. deterministic review identity omitted the exact candidate HEAD, allowing old-packet/new-HEAD replay.

All four are one provenance-chain defect: a downstream object could claim more authority than had been independently re-derived from durable bytes and route facts.

## Repair contract

The repaired chain is:

```text
(ResultIdentity + reviewed_head)
  -> canonical review identity
  -> deterministic refs + exact markdown bytes/hash
  -> NativeFileSystem.create_text_if_absent
  -> verify write result + reread exact persisted bytes
  -> route packet exact path under selected worktree
  -> reread exact persisted bytes again at C0b
  -> DirectReviewRoute
```

Rules:

- `reviewed_head` must be a validated 7..64 hex Git identity and part of canonical bytes/digest;
- changing HEAD changes review contract ref, task path and result destination;
- C0b re-derives expected refs/content/hash from `(author, route HEAD)` and never trusts `persisted_sha256` alone;
- exact packet path must equal `<dispatch.worktree_path>/<deterministic task relative path>` after normalization;
- C0b must receive accepted `NativeFileSystem` rooted at the same selected worktree and reread deterministic relative task path;
- persisted read path/content/size/hash must all match independently computed values;
- forged `MaterializedReviewTask` cannot authorize anything without those bytes;
- no second filesystem/scheduler/provider/lease/review lifecycle is introduced.

## RED matrix

Before source mutation add deterministic failing tests for:

1. C0a successful write result with wrong path/size/hash -> typed verify failure;
2. C0a success followed by missing/divergent reread -> typed verify failure;
3. forged `MaterializedReviewTask.persisted_sha256` with matching caller packet -> C0b refusal;
4. foreign-worktree packet path with correct suffix/hash/contract -> refusal;
5. changing reviewed HEAD changes deterministic refs;
6. old packet cannot bind route with new HEAD;
7. exact selected worktree + persisted bytes positive control remains accepted.

## Verification floor

After GREEN:

- focused `tests/test_zero_relay_review_task.py`;
- WO216 related regression floor;
- `tests/test_native_execution.py` + Phase-B no-clobber/materializer tests;
- compile/import diagnostics;
- `git diff --check`;
- strict UTF-8/no U+FFFD;
- changed/untracked scope audit;
- secret-like added-line scan;
- hosted CI;
- independent exact-SHA review by a non-author.

## Defect-memory follow-up

The provenance lesson must be appended to `DEFECT_LESSONS.md` after PR #293 releases that file. WO219 must not overlap that active owner merely to satisfy documentation timing.

## Stop gates

STOP on any required change outside released module/tests, source/authority drift, new scheduler/provider/lease semantics, non-terminal hosted CI after freeze, independent review gate, merge/post-main gate, or UNKNOWN authority.

`PHASE_C1=HOLD` until repaired exact SHA is independently accepted and post-main verified.

## RED evidence

Before source mutation, the WO219 contract was applied to the existing WO216 tests plus the four independent reproducers. Result:

- `38 failed, 2 passed`
- failures were expected signature/provenance failures because candidate source did not yet bind `reviewed_head` or filesystem authority;
- dedicated REDs reproduced wrong success write-result acceptance, missing post-write reread, forged materialized provenance, foreign-worktree packet acceptance, and old-packet/new-HEAD replay.

No source change preceded this RED run.

## GREEN evidence

After the bounded repair:

- focused `tests/test_zero_relay_review_task.py`: `44 passed`;
- full WO216/Phase-B related floor: `346 passed, 1 skipped`;
- skip: existing POSIX FIFO-only harness case unavailable on Windows;
- `python -m compileall -q src/a_conductor/zero_relay_review_task.py`: PASS;
- `git diff --check`: PASS;
- strict UTF-8 decode/no replacement-character check: PASS;
- changed scope: only WO219 doc + `zero_relay_review_task.py` + focused tests;
- added-line secret-like scan: 0 hits;
- source LSP diagnostics: 0 errors/warnings.

Additional non-vacuity controls prove:

- successful create followed by divergent reread fails closed;
- a valid materialized object without persisted bytes cannot mint a route;
- filesystem root must equal selected review worktree;
- invalid HEAD is rejected and uppercase/lowercase hex HEAD canonicalizes to one identity.

## Repair result

The repaired implementation now:

1. binds exact normalized `reviewed_head` into canonical review bytes/digest/refs/markdown;
2. verifies create result path/size/hash/created flag and rereads persisted bytes before returning C0a provenance;
3. stores normalized reviewed HEAD in `MaterializedReviewTask` but does not treat that caller-constructible object as final authority;
4. C0b re-derives expected refs/content/hash from `(author ResultIdentity, route HEAD)`;
5. requires filesystem root identity to match `HarnessDispatch.worktree_path`;
6. requires packet path to equal the deterministic task path under that selected worktree after existing Windows worktree normalization;
7. rereads exact persisted relative task bytes again before returning `DirectReviewRoute`;
8. leaves scheduler/provider/lease/C1/mailbox semantics unchanged.

## Remaining gate

Candidate must be committed/pushed, hosted CI must be terminal, then a non-author must independently review the exact SHA. Implementation author GPT must not self-accept or self-merge.
