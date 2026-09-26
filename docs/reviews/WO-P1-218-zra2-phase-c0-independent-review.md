# WO-P1-218 — ZRA-2 Phase C0 independent exact-SHA review

Verdict: CHANGES_REQUIRED
Risk: R3 provenance / anti-replay boundary
Reviewer: GPT-5.6 Sol integrator (independent of GLM author)
Candidate PR: #296
Candidate exact SHA: `ade1628247a4512fa879c10bfd093d14f51d487f`
Candidate base observed at review: `cfcb369fe5ab3a50569defa822289f10f2f38aac`
Current main during review later advanced to `3e10b0464017f30b250314ba3ece9ebf9edf202f` via an unrelated docs/architecture merge; no C0 dependency paths changed in that drift.
Candidate hosted CI: Windows/full SUCCESS, Ubuntu smoke SUCCESS, macOS smoke SUCCESS.
Merge performed: false.

## Scope reviewed

Exact source/test additions in the candidate:

- `src/a_conductor/zero_relay_review_task.py`
- `tests/test_zero_relay_review_task.py`
- WO216 evidence

The review specifically challenged the intended chain:

`ResultIdentity -> deterministic persisted review task -> trusted ParallelReadyTask route -> DirectReviewRoute`

and the WO210/WO216 requirements that:

- persisted bytes, not caller claims, are provenance authority;
- a review packet is bound to the selected review worktree;
- an old review packet cannot authorize a different candidate HEAD;
- caller-created value objects cannot mint review authority without the accepted persistence seam.

## Positive evidence

The candidate is otherwise well-bounded and disciplined:

- new source is isolated to one C0 module plus focused tests;
- deterministic JSON identity over the author ResultIdentity is stable;
- task/result paths are digest-derived and do not use raw user path text;
- NativeFileSystem no-clobber publication is reused rather than reimplemented;
- direct review route requires READ_ONLY mutation intent;
- author and reviewer execution ids are checked for distinctness;
- no scheduler/provider/lease store or ReviewBus is introduced;
- GLM stopped before C1/merge as required.

These positives do not close the provenance blockers below.

## P2-1 — C0b accepts packet from a different worktree

`bind_direct_review_route()` validates packet path with:

`packet.path.endswith(review.refs.task_path)`

but does not prove that the packet is located under the exact `dispatch.worktree_path` selected by the validated route.

Deterministic review probe on exact candidate:

- route worktree: `A:/wt/review`
- packet path changed to: `A:/wt/OTHER/runs/zra2-review-<digest>.md`
- task contract/hash/suffix kept internally consistent
- result: `bind_direct_review_route()` returned ACCEPTED

Observed output:

`ACCEPTED A:/wt/OTHER/runs/zra2-review-...md A:/wt/review`

The later ClaudeCode harness has its own root-confinement check, but C0 itself is supposed to return a trusted route-provenance object for C1. A `DirectReviewRoute` that can already be minted for a packet outside the selected worktree violates that contract and can become evidence for a route that was never executable.

Required repair: bind the exact packet path to the exact selected worktree/root, using existing path authority semantics; suffix matching alone is insufficient.

## P2-2 — caller can forge MaterializedReviewTask without C0a persistence

`MaterializedReviewTask` is a public dataclass. C0b checks that `review.refs == deterministic_review_refs(author)` but trusts caller-supplied `review.persisted_sha256`.

Deterministic probe constructed a MaterializedReviewTask directly with correct refs but:

`persisted_sha256 = 0000000000000000000000000000000000000000000000000000000000000000`

and a matching caller-created TaskPacketFile.

Result: C0b returned ACCEPTED.

Observed output:

`ACCEPTED 0000000000000000000000000000000000000000000000000000000000000000 zra2-review-v1:<digest>`

Therefore the current C0b chain proves only that caller objects agree with one another; it does not prove that the review task ever passed C0a and exists with exact persisted bytes.

Required repair: re-derive expected rendered bytes/hash from authoritative inputs and re-read/verify the persisted task through NativeFileSystem (or an equally existing accepted filesystem authority) before DirectReviewRoute can be produced. Do not rely on a caller's MaterializedReviewTask hash as authority.

## P2-3 — candidate HEAD is not part of review identity; old packet can bind a new HEAD

The deterministic review digest contains the author ResultIdentity fields but no reviewed candidate HEAD. `bind_direct_review_route()` later copies `dispatch.expected_head` into DirectReviewRoute without binding that HEAD into the review task identity.

Deterministic probe reused the exact same author identity and materialized review packet, changed all route facts consistently to a different valid HEAD (`cccc...`), and constructed a valid ParallelReadyTask.

Result: C0b returned ACCEPTED and `author_digest` was unchanged.

Observed output:

`ACCEPTED_HEAD cccccccccccccccccccccccccccccccccccccccc AUTHOR_DIGEST <same prior digest>`

This directly violates the WO210 anti-replay acceptance condition that an old review packet cannot authorize a new candidate HEAD.

Required repair: bind exact reviewed HEAD into the deterministic C0a identity/task bytes/refs before persistence. A later route may assert that same HEAD but may not redefine it.

## P2-4 — C0a success path trusts create_text_if_absent result without exact persisted-byte verification

On the normal create path, `materialize_review_task()` returns `result.sha256` immediately after `filesystem.create_text_if_absent(...)` and does not verify returned path/size/hash or re-read the exact persisted bytes.

Deterministic fault probe used a filesystem double whose create operation returned:

- wrong relative path;
- wrong size;
- SHA `000...000`;
- no persisted file proving the expected content.

Result: `materialize_review_task()` returned ACCEPTED with that forged SHA.

Observed output:

`ACCEPTED <deterministic task path> 0000000000000000000000000000000000000000000000000000000000000000 True`

The concrete NativeFileSystem implementation normally returns correct values, but the accepted Phase-B materializer already established the stronger boundary: verify create result metadata and re-read exact persisted bytes before returning provenance. C0 should reuse that discipline instead of weakening it.

Required repair: after create, verify relative path, byte size and expected SHA, then re-read and compare exact content/path/size/hash. Collision/reuse paths must receive the same exact-byte proof.

## Severity / decision

P0: 0
P1: 0
P2: 4
P3: 0 newly required for this decision

Verdict: `CHANGES_REQUIRED`

The four findings share one root cause: C0 currently lets caller-assembled metadata stand in for persisted and route-bound provenance. Repair should be one bounded child, not four independent rewrites.

## Required bounded repair shape

A single repair should:

1. include exact reviewed HEAD in canonical review identity and rendered task bytes;
2. verify C0a success and collision paths by exact persisted byte/path/size/hash read-back;
3. require the exact route worktree/task path relationship, not suffix matching;
4. re-derive expected review bytes/hash from `(ResultIdentity, reviewed_head)` in C0b and re-read persisted bytes before returning DirectReviewRoute;
5. prevent a caller-created MaterializedReviewTask from minting route authority merely by supplying self-consistent fields;
6. preserve READ_ONLY, author/reviewer distinctness, deterministic result destination, scheduler/provider/lease reuse, and no new authority/store/retry system;
7. add RED-first tests for all four repros plus same-input idempotency/concurrent no-clobber regression.

C1 remains HOLD until the repaired exact SHA receives independent review and integrator acceptance.
