# WO-P1-218 — ZRA-2 Phase C0 independent exact-SHA review

Status: CHANGES_REQUIRED
Parent: WO-P1-216 / PR #296 / Issue #214
Reviewed candidate: `ade1628247a4512fa879c10bfd093d14f51d487f`
Candidate base at review: `cfcb369fe5ab3a50569defa822289f10f2f38aac`
Current main during review: `3e10b0464017f30b250314ba3ece9ebf9edf202f`
Reviewer: GPT-5.6 Sol integrator (independent of GLM author)
Risk: R3 identity / provenance / anti-replay boundary
Verdict: `CHANGES_REQUIRED`
P0: 0
P1: 0
P2: 4
Merge performed: false
C1 released: false

## 1. Candidate baseline

PR #296 hosted CI is terminal green on the exact reviewed head:

- Windows/full `test`: SUCCESS
- Ubuntu smoke: SUCCESS
- macOS smoke: SUCCESS
- merge state: CLEAN

The implementation is bounded to one new source module, one focused test module, and WO216 evidence. GLM stopped before C1 and did not self-accept.

Main advanced during review from `cfcb369...` to `3e10b04...`; an exact-path drift check proved there were no changes between those commits to the C0 dependency surfaces (`native_execution.py`, `zero_relay.py`, `parallel_ready_execution.py`, `claude_code_harness.py`, worker candidate assembly, ZCode production assembly, or their relevant route tests). The findings below therefore remain valid for the exact candidate.

## 2. Accepted strengths

The candidate correctly:

- derives deterministic versioned refs from `ResultIdentity`;
- renders a bounded fixed review task;
- uses the accepted `NativeFileSystem.create_text_if_absent()` publication primitive;
- reuses `ParallelReadyTask` instead of creating scheduler/provider/lease authority;
- requires `MutationIntent.READ_ONLY`;
- checks author/reviewer execution-id distinction;
- keeps external mailbox identity out of this direct route;
- introduces no C1 `ReviewEvidence`, retry loop, scheduler, provider store, lease store, or A-Wiki internal import.

These are retained in the repair.

## 3. P2-1 — C0a success path trusts the write-result object without persisted-byte verification

`materialize_review_task()` computes expected task bytes, calls `create_text_if_absent()`, then immediately returns `MaterializedReviewTask(... persisted_sha256=result.sha256, created=True)`.

Unlike the accepted Phase-B materializer, the success path does not verify:

- returned `relative_path`;
- returned `size_bytes`;
- returned `sha256` against the independently computed content hash;
- persisted bytes by rereading the target.

Independent deterministic probe supplied a filesystem object whose `create_text_if_absent()` returned a fabricated success result with a wrong path/size and SHA `000...000`, while no trusted persisted state was proven. Candidate result:

```text
ACCEPTED runs/zra2-review-<digest>.md 0000000000000000000000000000000000000000000000000000000000000000 True
```

This violates the C0 contract that persisted packet identity is evidence-backed rather than caller/result-object asserted.

Required repair: mirror the accepted Phase-B post-write verification discipline. Any wrong path/size/hash or failed reread must fail typed; exact persisted UTF-8 bytes/hash must be verified before returning a materialized object.

## 4. P2-2 — caller can forge `MaterializedReviewTask` and mint a trusted `DirectReviewRoute`

`MaterializedReviewTask` is a normal public frozen dataclass. `bind_direct_review_route()` accepts it as provenance and checks only that `deterministic_review_refs(author) == review.refs`; the `persisted_sha256` value is then trusted if the caller also supplies a matching `TaskPacketFile.sha256`.

Independent probe manually constructed a `MaterializedReviewTask` with correct refs but forged persisted SHA `000...000`, built a matching route packet, and obtained:

```text
ACCEPTED 0000000000000000000000000000000000000000000000000000000000000000 zra2-review-v1:<digest>
```

No C0a materialization was required.

Required repair: C0b must independently re-derive expected bytes/hash from the authoritative review identity and verify persisted bytes through accepted filesystem authority. A caller-constructible dataclass must not be the final trust root.

## 5. P2-3 — packet path is suffix-checked, not bound to the selected review worktree

C0b currently accepts packet path when `packet.path.endswith(review.refs.task_path)`.

Independent probe used:

```text
route worktree = A:/wt/review
packet path    = A:/wt/OTHER/runs/zra2-review-<digest>.md
```

with matching contract/hash. `bind_direct_review_route()` returned:

```text
ACCEPTED A:/wt/OTHER/runs/zra2-review-<digest>.md A:/wt/review
```

The downstream harness does perform confinement before execution, but C0b already minted a `DirectReviewRoute` that claims trusted provenance for a packet outside the scheduler/lease-selected worktree. C1 must not receive such an object.

Required repair: resolve/normalize the packet path and require exact equality to `<dispatch.worktree_path>/<deterministic relative review task path>` (using existing path semantics, not string suffix matching), then reread/rehash that exact file before returning the binding.

## 6. P2-4 — review identity does not bind candidate HEAD; old packet can authorize a new HEAD

The deterministic review digest currently contains only `ResultIdentity` fields. Candidate HEAD is introduced later from `HarnessDispatch.expected_head` and is not part of the review packet identity.

Independent probe reused the same author identity/materialized packet and rebuilt an internally consistent `ParallelReadyTask` whose lease/candidate/dispatch HEAD was changed to `cccc...`. C0b accepted it:

```text
ACCEPTED_HEAD cccccccccccccccccccccccccccccccccccccccc AUTHOR_DIGEST <unchanged digest>
```

This violates the WO210/WO216 anti-replay requirement: an old review packet must not authorize a new candidate HEAD.

Required repair: exact reviewed HEAD must be part of the canonical review identity before C0a materialization and therefore change the contract ref/task path/result path/hash when HEAD changes. C0b must require route HEAD equality with that bound identity.

## 7. Required repair shape

One bounded repair child may fix all four P2 findings together because they are one provenance chain:

```text
(ResultIdentity + exact reviewed_head)
  -> canonical deterministic review identity
  -> exact rendered bytes/hash
  -> collision-safe persisted file
  -> post-write reread verification
  -> exact route-worktree packet path
  -> second persisted-byte/hash verification at C0b
  -> DirectReviewRoute
```

Constraints:

- reuse `NativeFileSystem`; no second filesystem implementation;
- reuse `ParallelReadyTask`; no scheduler/provider/lease changes;
- no C1/ReviewEvidence/GoalCloseout changes;
- external mailbox remains out of scope;
- no hidden retries;
- stable typed error codes;
- RED-first tests for each independent reproducer;
- retain all current positive controls and regression floor.

## 8. Independent rereview requirements after repair

The repaired exact SHA must prove at minimum:

1. wrong success write-result path/size/hash is rejected;
2. post-write disappeared/divergent bytes fail closed;
3. manually forged `MaterializedReviewTask` cannot mint a binding without matching persisted bytes;
4. packet in a foreign worktree is rejected even with matching suffix/hash/contract;
5. exact selected worktree packet is accepted;
6. changing reviewed HEAD changes deterministic contract/path/result refs;
7. old packet cannot bind a new route HEAD;
8. same `(ResultIdentity, HEAD)` remains deterministic/idempotent;
9. same-input publication races converge and divergent races preserve conflict;
10. all existing route/provider/worker/read-only/author-distinct checks remain green.

## 9. Gate

`WO216=CHANGES_REQUIRED`

`PHASE_C1=HOLD`

Next safe action: bounded WO219 repair child from exact candidate `ade1628247a4512fa879c10bfd093d14f51d487f`, followed by hosted CI and independent exact-SHA review. Do not merge PR #296 as-is.
