# GLM / WO-P1-205 — ZRA-2 Phase D durable execution/result → GoalCloseout composition

STATUS: HOLD — DO NOT IMPLEMENT UNTIL EXPLICITLY RELEASED

This packet is a future implementation pointer. It does not authorize source mutation now.

## External release gate

Before any source/test mutation, independently verify ALL from durable Git/GitHub authority:

1. ZRA-2 Phase B is ACCEPTED, MERGED, and required post-main verification is green.
2. ZRA-2 Phase C is ACCEPTED, MERGED, and required post-main verification is green.
3. WO-P1-208 closeout crash-boundary GLM lab is complete and the parent/integrator has accepted one explicit external-effect/recovery contract for Phase D.
4. Issue #214 explicitly marks Phase D `NEXT_READY`.
5. A fresh Phase-D implementation claim names exact owner, base SHA, branch, worktree, mutable paths, forbidden paths, and dependencies.
6. The claimed worktree is isolated and clean except for explained owned changes.
7. No overlapping mutable lane exists.

If any item is false or unknown, write/checkpoint `BLOCKED_EXTERNAL_AUTHORIZATION` and STOP. Do not create a source implementation branch merely because this file exists.

## Read first after release

Read the released versions of:

- `docs/work-orders/WO-P1-205-zra2-phase-d-closeout-binding-gate.md`
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
  - `GoalCloseoutExecutor`
- related accepted tests for execution records/store, zero-relay, Phase C, job state, and GoalCloseout.

Re-run source archaeology at the released base. Do not assume the pre-shaped module/file names remain correct after Phase C lands.

## Objective

Build the smallest production composition seam that binds:

`exact accepted author execution/result` + `exact accepted independent Phase-C review` + `current durable job/candidate identity`

into the EXISTING `GoalCloseoutExecutor` authority.

Phase D is NOT a second completion state machine.

It must never call `JobStore.transition(... COMPLETE ...)` directly and must never fabricate GoalCloseout checkpoints.

## Mandatory authority chain

The final composition must preserve this chain:

```text
TaskPacketFile / exact task bytes
  -> durable supervised author execution record
  -> exact durable result artifact + recomputed SHA-256
  -> zero_relay.ResultIdentity
  -> accepted trusted Phase-C ReviewEvidence
  -> classify_relay_decision == ACCEPTED
  -> re-read current durable job + current candidate SHA
  -> compose GoalCloseoutFacts using trusted evidence
  -> existing GoalCloseoutExecutor
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
- attempt/generation come from trusted durable ZRA/job authority, never free-form input;
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
- candidate/reviewed SHA where applicable.

Also prove reviewer execution is durable/terminal, follows the accepted independent-review route, and differs from `author_execution_id`.

`CHANGES_REQUIRED`, unknown, malformed, stale, or ambiguous review must not flow to closeout.

## Current durable job / GoalCloseout binding

Immediately before calling GoalCloseout:

- re-read current job;
- bind expected job_id/task_id/attempt/version;
- re-read current candidate SHA from accepted authority;
- reject version/head/candidate drift;
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
- stale attempt/generation.

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
- version conflict;
- state not accepted for closeout;
- current candidate SHA unknown;
- candidate SHA changes after accepted review;
- stale reviewed SHA;
- missing verify/fold/release obligations remain blocked by GoalCloseout;
- duplicate/restart invocation remains idempotent through existing store/GoalCloseout semantics;
- prove no direct COMPLETE transition exists in the Phase-D module.

Use positive controls beside negative cases.

## Implementation constraints

- Prefer one narrow new composition module after released archaeology.
- Reuse execution store, artifact reader, job store, Phase-C evidence, and GoalCloseout ports.
- No second DB/store/journal/review bus/scheduler/retry policy.
- No network/provider/credential/live Worker mutation.
- No direct A-Wiki mutation.
- No fabricated lease/provider/review/closeout authority.
- No blind retries on UNKNOWN.
- No weakening existing tests.
- Stable typed failure codes; do not leak arbitrary exception text as authority.

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
- RED/GREEN matrix;
- verification results;
- P0/P1/P2/P3 self-audit;
- any DESIGN_GAP_*;
- Draft PR URL;
- `merge_performed=false`;
- next safe action.

Then STOP at the first external gate. A later invocation resumes from durable state rather than starting over.
