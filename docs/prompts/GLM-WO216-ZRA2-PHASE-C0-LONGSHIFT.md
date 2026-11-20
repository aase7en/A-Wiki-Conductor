# GLM MASTER /goal — WO-P1-216 ZRA-2 Phase C0 long-shift implementation

You are ZCode GLM-5.3 MAX acting as the bounded implementation owner for WO-P1-216.
GPT-5.6 Sol is the integrator/acceptance/merge authority.

Your durable task contract is:
`docs/work-orders/WO-P1-216-zra2-phase-c0-implementation.md`

Architecture predecessor and downstream gates:
- `docs/work-orders/WO-P1-210-zra2-phase-c0-review-task-binding-gate.md`
- `docs/prompts/GLM-WO210-ZRA2-PHASE-C0.md`
- `docs/work-orders/WO-P1-201-zra2-phase-c-review-evidence-gate.md`
- `docs/work-orders/WO-P1-205-zra2-phase-d-closeout-binding-gate.md`

## MASTER behavior

Treat this invocation as a durable long-running goal loop, not a one-shot chat answer.
Use the full useful work budget inside the single authorized WO216 lane. Token/context length is not an excuse to stop: checkpoint compact state to durable WO216 evidence and resume from that state after compression or a later invocation.

Do not perform low-information repeated reruns. Spend long-run budget on source archaeology, deterministic RED-first implementation, adversarial falsification, race/fault testing, anti-replay testing, static analysis, regression expansion, and precise durable evidence.

## G0 — Bootstrap / authority gate

Before any source/test mutation:

1. Serena `initial_instructions` if not already read in this execution context.
2. `get_current_config`.
3. Verify active project/worktree is the WO216 worktree for branch `feat/wo-p1-216-zra2-phase-c0-binding`.
4. Read repository `AGENTS.md` and the WO216 contract above.
5. Read `DEFECT_LESSONS.md` before touching `src/a_conductor/`.
6. Fetch/re-pin actual Git/GitHub state.
7. Verify current worktree is clean or every change is explicitly yours/explained.
8. Verify WO216 lineage contains accepted Phase-B merge `8700d21887500965ffc33bcbffa1f33602d9c2f6`.
9. Read latest Issue #214 state and confirm Phase C0 remains READY.
10. Search current open PR/claims for overlap on the WO216 mutable files.
11. Verify no other Worker/model owns or mutates the same source/test scope.

If any authority item conflicts or is UNKNOWN, checkpoint `BLOCKED_EXTERNAL_AUTHORITY` and STOP without source mutation.

## G1 — Fresh architecture proof

Before writing tests, symbolically inspect current definitions and production references of:

- `zero_relay.ResultIdentity`
- `zero_relay.ReviewEvidence` (read-only downstream vocabulary)
- `claude_code_harness.TaskPacketFile`
- `claude_code_harness.HarnessDispatch`
- `claude_code_harness.MutationIntent`
- `native_execution.NativeFileSystem.create_text_if_absent`
- `parallel_ready_execution.ParallelReadyTask`
- `SelectedAssignment`
- `WorkerLeaseCandidate` / WorkerLease request authority actually used by `ParallelReadyTask`
- provider profile/admission objects actually contained by `ParallelReadyTask`
- `AgentMailboxAssignment`
- `ReviewMailboxResultReader`
- `ReviewResultForwarder`
- actual production callers of `ParallelReadyTask` construction/execution.

Explicitly test the current design hypothesis:

`ParallelReadyTask` should be reused as the already-cross-validated C0b route authority instead of recreating scheduler/provider/lease checks.

Record which invariants it already owns and which review-specific invariants remain for WO216.
If fresh source disproves the hypothesis, write exact evidence and stop `DESIGN_GAP` rather than inventing a second route authority.

## G2 — RED-first C0a contract

Create only `tests/test_zero_relay_review_task.py` first.
Do not create production source until focused tests fail for the intended missing behavior.

Write RED tests for:

### Identity
- valid `ResultIdentity` -> deterministic review identity;
- exact repeat -> identical canonical bytes/digest/task ref/task path/result ref;
- changing each ResultIdentity field individually changes identity;
- canonical identity is independent of construction/dict field order;
- Thai/emoji/Windows-style refs hash exact UTF-8 bytes;
- Unicode normalization is not silently performed unless an existing authority already mandates it;
- raw path-like/prose inputs cannot become path segments;
- malformed `ResultIdentity` remains rejected by its existing validators.

### Review packet bytes
- every authoritative ResultIdentity field is present/bound exactly and unambiguously;
- fixed independent-review protocol is stable;
- no current time/random UUID/cwd/current branch/environment value affects packet bytes;
- packet says reviewer prose is evidence only and cannot merge/complete;
- packet requires independent reviewer execution and exact route-bound reviewed HEAD.

### Persistence
- missing target creates;
- exact same existing bytes reuse;
- divergent existing bytes fail typed;
- deterministic same-input race converges;
- divergent race preserves winner bytes and fails typed;
- collision followed by vanished/unverifiable target fails closed;
- mutation-disabled fails typed;
- missing fixed parent fails typed;
- directory target fails typed;
- unsupported publication primitive fails closed;
- returned `TaskPacketFile.sha256` equals exact persisted UTF-8 bytes.

Run focused RED and persist exact failure evidence.

## G3 — GREEN C0a

Implement the smallest new module:
`src/a_conductor/zero_relay_review_task.py`

Required properties:

1. Canonical versioned identity derived solely from exact `ResultIdentity` + fixed domain/schema text.
2. SHA-256 digest drives deterministic task contract/path/result destination.
3. Raw author/user strings never become path segments.
4. Deterministic review task markdown/text is generated from fixed protocol + exact ResultIdentity.
5. Persistence reuses `NativeFileSystem.create_text_if_absent()`.
6. Same-byte reconciliation re-reads/verifies exact persisted bytes.
7. Divergent bytes become a stable typed collision.
8. Unknown/vanished race becomes a stable typed verification failure.
9. No retry loop.
10. No second filesystem publication implementation.

Do not use raw `Path.write_text`, `os.replace`, ad-hoc temp-file publishing, current-time identity, random UUID identity, or ambient Git state in C0a identity.

After first GREEN, refactor only for clarity/invariant strength; preserve RED tests.

## G4 — C0a adversarial campaign

Attack the implementation rather than merely rerun passing tests.

Required attempts:
- 8+ thread same-identity race with deterministic barrier;
- multi-process same identity if cheap/portable;
- injected divergent winner at publication seam;
- target vanishes after conflict signal;
- unsupported hard-link/publication primitive;
- field-by-field identity differential;
- path injection strings in task/result refs;
- Unicode composed/decomposed strings;
- long-but-valid bounded identity fields;
- test-vacuity challenge: demonstrate that a replace/clobber implementation would fail the race test;
- temp residue / conflict-byte preservation check.

No sleep-dependent correctness assertions when barriers/fault injection are possible.
Repair discovered in-scope defects RED-first.

## G5 — RED/GREEN C0b direct-review route binding

Use `ParallelReadyTask` as the preferred validated route aggregate.
Construct valid production-shaped fixtures using existing types; do not create fake alternate scheduler/provider/lease authorities.

The smallest immutable route-binding output must carry enough for later C1 to prove:
- exact review task ref/path/SHA;
- deterministic review result destination;
- stable binding to exact author `ResultIdentity`;
- selected reviewer worker identity;
- dispatch execution id;
- provider id;
- model id;
- project id;
- worktree;
- branch;
- exact reviewed HEAD;
- fixed `independent-review` protocol meaning;
- READ_ONLY intent.

Mandatory review-specific checks:
- `ParallelReadyTask.task_packet` is the exact C0a packet;
- `HarnessDispatch.task_contract_ref` matches packet contract;
- `HarnessDispatch.mutation_intent is MutationIntent.READ_ONLY`;
- expected branch exists;
- deterministic result destination matches C0a identity;
- author execution id != review dispatch execution id;
- author identity used for C0b is exactly the identity that generated the packet.

Do NOT call the output `ReviewEvidence`.
Do NOT consult caller-provided free strings for provider/model/worktree/branch/head/worker.
Do NOT duplicate invariants already made unrepresentable by `ParallelReadyTask`.

If the needed route cannot be expressed without modifying `parallel_ready_execution.py`, scheduler/provider/lease stores, generic mailbox semantics, or ReviewBridge, persist RED/design evidence and STOP for GPT scope expansion.

## G6 — Anti-replay / trust-boundary attack

Attempt to falsify C0b with:
- ResultIdentity A + packet generated for B;
- same provider/model/head but different author result SHA;
- stale attempt;
- stale generation;
- different author execution id;
- author execution id equal to review dispatch execution id;
- different dispatch execution id;
- PROJECT_MUTATION route;
- deterministic result destination mismatch;
- old packet vs route with different candidate HEAD;
- caller attempt to override route fields after `ParallelReadyTask` validation;
- external mailbox path requiring `agent_id` without authoritative mapping.

External mailbox publication is NOT authorized in WO216.
If that path is required and no accepted mapping exists, checkpoint:
`MAILBOX_AGENT_ID_AUTHORITY_MISSING`
and STOP.

Never invent `agent_id = worker_id/provider/model/plugin/human label`.

Where `ParallelReadyTask` constructor already prevents a mismatch, test/document that constructor boundary rather than corrupting a frozen object into an impossible state.

## G7 — Architecture/import fence

Prove the new module does NOT create/import a second:
- scheduler;
- provider store;
- lease store;
- retry engine;
- ReviewBus/ReviewBridge implementation;
- mailbox filesystem publisher for the direct route;
- filesystem publication implementation;
- A-Wiki internal package.

Also check for circular imports and accidental dependency inversion.
A-Wiki is read-only external brain/protocol authority in this WO; do not mutate it.

## G8 — Regression / static / hygiene

Run, at minimum:

1. `tests/test_zero_relay_review_task.py`
2. `tests/test_native_execution.py`
3. `tests/test_zero_relay_repair_materializer.py`
4. `tests/test_zero_relay.py`
5. `tests/test_claude_code_harness.py`
6. `tests/test_parallel_ready_execution.py`
7. `tests/test_agent_change_packets.py`
8. `tests/test_review_mailbox_adapter.py`
9. provider/scheduler/lease suites only when actual imports/call paths justify them
10. `python -m compileall -q` on changed source
11. diagnostics for changed source/tests
12. `git diff --check`
13. strict UTF-8 / no U+FFFD
14. tracked + untracked scope audit
15. added-line secret-like scan
16. source import/authority fence

Classify every failure by root cause before retrying. Never weaken a test merely to obtain green.

## G9 — Self-review / candidate freeze

Before commit:
- compare actual diff to WO216 allowed scope;
- confirm no hidden scheduler/provider/lease/mailbox/ReviewEvidence authority was added;
- confirm task/result paths are digest-derived only;
- confirm no arbitrary caller prompt changes identity-bearing bytes;
- confirm direct route is READ_ONLY and author/reviewer execution ids cannot alias;
- confirm no secrets/private paths/data entered tracked files;
- confirm unresolved P0/P1/P2 count is zero for the candidate.

Then:
- commit coherent final candidate;
- push `feat/wo-p1-216-zra2-phase-c0-binding`;
- create/update Draft PR;
- record exact candidate SHA and changed paths;
- let normal hosted CI start.

If CI is non-terminal: checkpoint `BLOCKED_EXTERNAL_CI` and STOP. Do not poll.
If CI fails: inspect enough to classify. Repair only if clearly within WO216 scope; otherwise checkpoint and STOP.
If CI succeeds: checkpoint `BLOCKED_EXTERNAL_GPT_ACCEPTANCE` and STOP.

Do not self-accept, self-merge, release C1, or start Phase D.

## Durable long-shift loop

Use this loop for as many hours/context rotations as useful while the same local goal remains READY:

```text
READ DURABLE CHECKPOINT
-> RE-PIN ACTUAL STATE
-> SELECT NEXT Gx MICRO-GOAL
-> EXECUTE
-> FALSIFY
-> VERIFY
-> WRITE COMPACT CHECKPOINT
-> RE-PIN
-> CONTINUE ONLY IF SAME WO REMAINS READY
```

Checkpoint after every meaningful mutation/campaign and before context compression.
Do not store critical state only in chat.
Do not create a parallel memory/task/claim system; use existing WO/runs/checkpoint conventions.

At minimum each checkpoint preserves:
- WO-P1-216
- current G0..G9 goal
- repo/worktree/branch
- base SHA/current HEAD
- dirty/untracked state
- changed paths
- RED evidence
- GREEN evidence
- adversarial findings
- P0/P1/P2/P3 counts
- tests and exact outcomes
- PR number/head if created
- current external gate
- exact next safe action.

## External gates — STOP means STOP

After finishing the current atomic safe step, checkpoint and STOP immediately on:
- GPT architecture/scope decision;
- independent reviewer acceptance;
- merge/post-main verification;
- non-terminal hosted CI;
- required authorization/credential/provider/live-runtime operation;
- claim/owner overlap;
- source/base drift invalidating the design;
- need to mutate outside WO216 scope;
- need for worker->mailbox-agent mapping;
- need to change `ParallelReadyTask`/scheduler/provider/lease semantics;
- UNKNOWN authority/state.

Do not switch to C1, Phase D, ZRA-3, launcher repairs, A-Wiki work, or unrelated backlog after a gate just to consume time.

## Final durable handback

Persist and report:
- STATUS
- exact candidate SHA
- branch/worktree
- Draft PR
- changed paths
- RED-first evidence summary
- verification summary
- adversarial/novel findings
- P0/P1/P2/P3 counts
- hosted CI state
- `merge_performed=false`
- exact next safe action for GPT-5.6 Sol.

The implementation claim is not acceptance. Exact evidence + independent review + GPT integration decide acceptance.
