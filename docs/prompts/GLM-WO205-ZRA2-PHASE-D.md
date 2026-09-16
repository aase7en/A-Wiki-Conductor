# GLM / WO-P1-205 — ZRA-2 Phase D durable execution/result → GoalCloseout composition

STATUS: DOCS/SOURCE-PREFLIGHT FRONTIER RELEASED (`PHASE_D_NEXT_READY=YES`) — SOURCE IMPLEMENTATION STILL HOLD UNTIL THE SOURCE RELEASE CHECKLIST BELOW PASSES

This packet is the future implementation pointer for the Phase-D source lane. `PHASE_D_NEXT_READY=YES` on Issue #214 means the docs/source-preflight frontier is released — it is NOT automatic source mutation authority. This packet does not authorize source mutation now.

## Post-main truth snapshot (2026-09-16, exact)

At current main `5267ef94b0b23a631bdbb740bfd67d629aae85f4`:

- WO223 / Phase-C C1 accepted candidate `99e1f307a2a7e2ecb6131b201a37087e0a228245`; exact-head CI `35036900483` SUCCESS;
- PR #319 merged that expected head exactly as `5267ef94b0b23a631bdbb740bfd67d629aae85f4`; post-main CI `35038290207` SUCCESS;
- Issue #214 publishes `PHASE_D_NEXT_READY=YES`;
- fresh WO205 read-only archaeology: `READY_AFTER_WO223_POSTMAIN P0=0 P1=0 P2=0 SOURCE_SCOPE=TBD`;
- execution-routing context only (no Phase-D authority change): WO242 SQLite init-race repair is accepted reliability infrastructure; WO228 fast-path routing and WO244 Kilo/Claude harness decision are routing context only.

Older HOLD statements in prior snapshots of this packet are history. Actual Git/GitHub/Issue truth on the then-current lineage always wins over this prose.

## External release gate — verify before any source/test mutation

Already durably satisfied (verify, do not re-litigate):

1. ZRA-2 Phase B ACCEPTED, MERGED, post-main verified.
2. WO-P1-225 repaired C0 READ_ONLY lease/task binding ACCEPTED, MERGED, post-main verified.
3. WO-P1-226 reviewer-execution bridge ACCEPTED, MERGED, post-main verified.
4. WO-P1-223 / Phase-C C1 review-evidence composition ACCEPTED, MERGED (PR #319 as above), post-main verified.
5. WO-P1-208 crash-boundary evidence completed with the accepted external-effect/recovery contract (consume-proven-effects-first).
6. WO-P1-224 GoalCloseout lease-release truth repair ACCEPTED, MERGED, post-main verified.
7. Issue #214 explicitly marks Phase D `PHASE_D_NEXT_READY=YES`.

Still required before any source/test mutation (the source release checklist, in order):

8. The WO205 docs activation (the two-file refresh containing this packet) is itself accepted, merged and post-main verified through its own R2 gates (bounded diff/scope/UTF-8 -> freeze SHA -> independent exact-SHA R2 review -> exact-head CI -> expected-head merge -> post-main).
9. Re-pin current main, Issue #214, and WO205 against actual Git/GitHub on the then-current lineage.
10. A fresh isolated source worktree plus an exact claim/non-overlap gate naming owner, base SHA, branch, worktree, mutable paths, forbidden paths, and dependencies; no overlapping mutable lane.
11. Read `DEFECT_LESSONS.md` before any `src/a_conductor/` mutation.
12. Run fresh source archaeology at the released base; do not assume pre-shaped module/file names.
13. Prove exact author `attempt_id`/`generation` provenance from existing durable authority — never fabricate from caller hints or `attempt_count`. If unprovable, report `DESIGN_GAP` and STOP for integrator adjudication.
14. Freeze the exact mutable source/test scope (replacing `SOURCE_SCOPE=TBD`), then implement RED first against the frozen minimum matrix in the WO205 packet.

If any item is false or unknown, write/checkpoint `BLOCKED_EXTERNAL_AUTHORIZATION` and STOP. Do not create a source implementation branch merely because this file exists.

## Read first after release

Read the released versions of:

- `docs/work-orders/WO-P1-205-zra2-phase-d-closeout-binding-gate.md` (authoritative; includes the frozen minimum RED matrix and forbidden scope)
- `DEFECT_LESSONS.md`
- `src/a_conductor/zero_relay.py`
  - `ResultIdentity`
  - `ReviewEvidence`
  - `classify_relay_decision`
- the accepted Phase-C review-evidence composition module and tests
- `src/a_conductor/execution_record.py`
  - `DurableExecutionRecord`
  - execution/transport terminal-state semantics
- `src/a_conductor/execution_store.py` or the actual accepted execution-store reader API
- `src/a_conductor/zcode_runner.py`
  - `SupervisedZCodeRunner`
- `src/a_conductor/supervised_run_coordinator.py`
- `src/a_conductor/job_state.py`
- `src/a_conductor/goal_closeout.py`
  - `GoalCloseoutFacts`
  - `ReviewEvidence`
  - `plan_goal_closeout`
  - `GoalCloseoutExecutor` / `execute_next`
- related accepted tests for execution records/store, zero-relay, Phase C, job state, and GoalCloseout.

Re-run source archaeology at the released base. Do not assume the pre-shaped module/file names remain correct.

## Objective

Build the smallest production composition seam that binds:

`exact accepted author execution/result` + `exact accepted independent Phase-C review` + `current durable job/candidate identity`

into the EXISTING `GoalCloseoutExecutor` authority.

Phase D is NOT a second completion state machine.

It must never call `JobStore.transition(... COMPLETE ...)` directly and must never fabricate GoalCloseout checkpoints. The sole mutation seam is the existing `GoalCloseoutExecutor.execute_next()` — one stage at a time; `GoalCloseoutExecutor` remains the sole VERIFY/REVIEW/MERGE/FOLD/RELEASE/COMPLETE authority.

## Mandatory authority chain

The final composition must preserve this chain:

```text
TaskPacketFile / exact task bytes
  -> durable supervised author execution record
  -> exact durable result artifact + recomputed SHA-256
  -> zero_relay.ResultIdentity
  -> accepted trusted Phase-C ReviewEvidence
  -> classify_relay_decision == ACCEPTED (only)
  -> re-read current durable job + current candidate SHA after review
  -> compose GoalCloseoutFacts using trusted evidence
  -> existing GoalCloseoutExecutor.execute_next()
  -> existing staged verify/review/merge/fold/release/COMPLETE authority
```

Any unknown/mismatch/drift must fail closed before closeout mutation.

## Author execution/result binding

Do not accept caller prose as authority. Prove at least:

- durable execution record exists;
- expected execution/job/work-order/project/worker/backend identity matches;
- execution is terminal success under accepted execution semantics;
- timeout/partial/recovery/unknown states cannot pass;
- result_ref comes from durable execution authority;
- result artifact is read through accepted confined artifact authority;
- `result_sha256` is recomputed from exact durable bytes;
- task_contract_ref and task SHA match the execution/task packet authority;
- `author_execution_id` is the durable record execution_id;
- attempt/generation come from trusted durable ZRA/job authority, never free-form input, never derived from `attempt_count` or caller hints — this is a binding design gate: if archaeology cannot prove exact provenance, report `DESIGN_GAP` and STOP;
- branch/head/candidate identity has not drifted.

Do not substitute stdout merely because a stdout hash exists. Choose and document the canonical review/result artifact.

## Review binding

Consume the accepted Phase-C typed evidence. Never reconstruct authority from raw reviewer JSON.

Require exact equality for:

- task_contract_ref;
- task SHA;
- result_ref;
- result SHA;
- attempt;
- generation;
- three-way SHA equality: review target SHA == current candidate SHA == future merge/closeout candidate SHA.

Also prove reviewer execution is durable/terminal, follows the accepted independent-review route, and differs from `author_execution_id`.

`CHANGES_REQUIRED`, unknown, malformed, stale, or ambiguous review must not flow to closeout. Relay gate is ACCEPTED-only; rejection/ambiguity never closeout.

## Current durable job / GoalCloseout binding

Immediately before calling GoalCloseout:

- re-read current job;
- bind expected job_id/task_id/attempt/version;
- re-read current candidate SHA from accepted authority;
- reject version/head/candidate drift; on version conflict, reload and replan — never overwrite or force a stale view;
- do not coerce VERIFYING/CHANGES_REQUIRED/RECOVERY_NEEDED into REVIEW_PENDING;
- do not fabricate `completed_closeout_refs`;
- derive GoalCloseout `reviewed_sha` from the exact accepted review/candidate authority;
- delegate final mutation to `GoalCloseoutExecutor` only.

A low-level store API being technically callable does not make it the Phase-D completion authority.

## Accepted WO208 crash/effect contract is mandatory input

Do not implement external fold/release initiation merely because `GoalCloseoutExecutor` and JobStore CAS exist.

Before source work, read the accepted parent decision derived from WO-P1-208 and its GLM crash-boundary lab. Preserve the following invariant:

```text
external effect may happen before JobStore checkpoint
=> checkpoint CAS alone is not an effect fence
=> missing checkpoint is not proof of no effect
=> UNKNOWN/lost acknowledgment is not retry permission
```

Phase-D v1 is consume-proven-effects-first: consume already-proven durable fold/release facts; keep missing/in-progress/stale/UNKNOWN effect truth as `RECOVERY_REQUIRED`/blocked; do not initiate unsupported external effects merely to close out. External effect initiation is allowed only in a later bounded slice whose exact adapter contract has passed WO208-style proof and whose release truth passes WO224 semantics.

The released Phase-D scope must name which supported contract applies to each external effect:

- already-proven/pre-existing effect only; or
- existing effect owner is idempotent + queryable/reconcilable by exact operation identity; or
- an accepted existing-authority intent/recovery extension explicitly approved by the parent.

If none applies, that external effect remains unsupported and ambiguous state must return `RECOVERY_REQUIRED` without replay.

Do not invent a new outbox, second journal, SQLite transaction around arbitrary external work, or caller-local retry memory.

RED-first crash/concurrency cases must include:

- two same-version callers at the effect boundary;
- stale version/ownership before effect;
- effect success + acknowledgment loss;
- UNKNOWN effect followed by process restart;
- completed checkpoint + response loss positive control;
- same-key/same-payload idempotency if claimed;
- same-key/divergent-payload refusal;
- query/reconcile failure remains recovery, never inferred success or absence.

## Frozen minimum RED-first acceptance matrix

The WO205 packet freezes this minimum matrix; a source candidate lacking a deterministic RED/GREEN case for any row is unacceptable:

1. exact author task/result/execution/attempt/generation cross-binding;
2. trusted ReviewEvidence exact match and reviewer distinctness;
3. relay ACCEPTED-only; rejection/ambiguity never closeout;
4. durable job state/version and current candidate re-observed after review;
5. review target SHA == current candidate == future merge/closeout candidate;
6. replay/idempotency and version-conflict reload/replan;
7. missing/UNKNOWN ownership/effects fail closed;
8. `GoalCloseoutExecutor` alone emits closeout stages / COMPLETE;
9. no duplicate model/review/external effect.

Expand each row with the detailed adversarial cases below. Use positive controls beside negative cases.

## RED-first adversarial campaign

Before GREEN implementation, force deterministic failures for at least:

### Author/result
- missing execution record;
- wrong execution/job/work-order/project/worker/backend;
- wrong task contract ref or task SHA;
- non-terminal/failed/timeout/recovery execution;
- missing result artifact;
- result hash mismatch;
- artifact changed between observation and binding;
- wrong branch/head;
- wrong author execution ID;
- stale or fabricated attempt/generation (including any derivation from `attempt_count`).

### Review
- no review;
- stale task/result SHA;
- stale result ref;
- stale attempt/generation;
- same author/reviewer execution ID;
- reviewer execution missing/non-terminal;
- CHANGES_REQUIRED/UNKNOWN;
- accepted review for previous candidate SHA;
- raw reviewer convenience fields trying to bypass typed authority.

### Job/closeout
- missing job;
- version conflict (must reload/replan, never overwrite);
- state not accepted for closeout;
- current candidate SHA unknown;
- candidate SHA changes after accepted review;
- stale reviewed SHA;
- missing verify/fold/release obligations remain blocked by GoalCloseout;
- missing/UNKNOWN ownership or effect truth remains blocked/recovery;
- duplicate/restart invocation remains idempotent through existing store/GoalCloseout semantics;
- prove no direct COMPLETE transition exists in the Phase-D module.

## Implementation constraints

- Proposed source layout is TBD and non-binding. Working hypothesis only (not an authorized scope): one thin NEW composition module plus focused tests after release-time archaeology.
- Reuse execution store, artifact reader, job store, Phase-C evidence, and GoalCloseout ports.
- No second DB/store/journal/review bus/scheduler/retry policy.
- No network/provider/credential/live Worker mutation.
- No direct A-Wiki mutation.
- No fabricated lease/provider/review/closeout authority.
- No blind retries on UNKNOWN.
- No weakening existing tests.
- Stable typed failure codes; do not leak arbitrary exception text as authority.
- FORBIDDEN scope unless a separately accepted RED/design finding proves it necessary: modifying `goal_closeout` / Phase-C composition / store / schema / lease / provider / job lifecycle.

If the released source cannot bind one required identity without inventing authority, report `DESIGN_GAP_<NAME>` with exact source evidence and STOP for integrator adjudication.

## Verification ladder

After GREEN, run at least:

1. focused Phase-D tests;
2. accepted Phase-C tests;
3. `tests/test_zero_relay.py`;
4. relevant execution record/store/supervised execution tests;
5. job-state tests;
6. `tests/test_goal_closeout.py`;
7. restart/version-conflict/recovery fault injection;
8. compile/import diagnostics;
9. `git diff --check`;
10. strict UTF-8/no U+FFFD;
11. changed-path scope audit including untracked files;
12. added-line secret-like scan;
13. freeze exact candidate SHA + durable result/checkpoint;
14. push Draft PR;
15. STOP at hosted CI / independent review / GPT acceptance gate.

Do not self-accept or self-merge.

## Required handback

Write the released child work-order result with exact:

- base SHA;
- candidate SHA;
- changed paths;
- architecture/reuse decisions;
- RED/GREEN matrix (mapping every frozen minimum row);
- verification results;
- P0/P1/P2/P3 self-audit;
- any DESIGN_GAP_*;
- Draft PR URL;
- `merge_performed=false`;
- next safe action.

Then STOP at the first external gate. A later invocation resumes from durable state rather than starting over.
