# WO-P1-200 — GLM master continuation controller

Status: ACTIVATED / COORDINATION-ONLY / NO PRODUCT SOURCE OWNERSHIP
Owner: GPT-5.6 Sol integrator
Executor target: ZCode GLM-5.3
Base: `02d39cbd9bca1ab3bb19b6e0cfbb0766c991f971`
Branch: `docs/wo-p1-200-glm-master-continuation`
Parent roadmap: `docs/plans/2026-09-04-zero-relay-accelerator-roadmap.md`

## Purpose

Give ZCode/GLM one durable MASTER goal that can resume useful work without repeated human relay.
The master is a router/checkpoint contract, not a second scheduler or task authority.

GLM must continue only work that is durably READY under the existing work-order/claim/branch authority.
It must stop immediately at an external gate and resume from durable state on the next invocation.

External gates include, at minimum:
- GPT/integrator acceptance or independent review;
- merge or post-merge verification;
- hosted CI whose result is not yet terminal;
- authorization/claim/scope not yet granted;
- another active owner or overlapping mutable lane;
- provider/credential/entitlement/quota gate;
- unknown execution/recovery state.

`BLOCKED_EXTERNAL_*` is a successful safe stop, not a failure.

## Authority order

Actual Git/GitHub/runtime/task state
> current work-order / issue claim / branch / result checkpoint
> planning projections
> model recollection.

Never use chat memory as authority.
Never reset/clean/stash/rebase/force-push another lane to make state convenient.
Never steal or reinterpret another lane's scope.

## MASTER state

Master checkpoint (ignored/local evidence):
`A:\GitHub\_worktrees\A-Wiki-Conductor-wo200-glm-master\runs\WO-P1-200\checkpoint.json`

Each checkpoint must record:
- timestamp;
- master packet SHA/commit;
- current queue item;
- repo/worktree/branch/HEAD;
- dirty files and whether they are expected/owned;
- claim/owner/scope;
- completed verification;
- candidate SHA if any;
- PR/CI state if any;
- exact blocker code;
- next safe action;
- files/results created.

On every invocation:
1. Read this work order and `docs/prompts/GLM-WO200-MASTER-CONTINUATION.md` from the WO200 worktree.
2. Read the previous master checkpoint if present.
3. Re-pin actual state. Do not assume the prior checkpoint is still true.
4. Resume the same queue item unless durable authority says it is accepted/closed/superseded.
5. Never restart completed phases just because context was lost.

## Critical-path queue

### Q1 — ZRA-2 Phase B / WO-P1-195 — CURRENT READY WORK

Authoritative execution worktree:
`A:\GitHub\_worktrees\A-Wiki-Conductor-wo195-zra2-phase-b`

Expected branch:
`feat/wo-p1-195-zra2-phase-b-materializer`

Activation HEAD before the current WIP:
`a1ec5eafba30640dd583b345756e931e41305661`

Parent authority:
- Issue #214
- `docs/work-orders/WO-P1-165-zra2-review-repair-loop.md`
- `docs/work-orders/WO-P1-195-zra2-phase-b-materializer.md`

Expected owned dirty WIP at MASTER creation:
- `M docs/work-orders/WO-P1-195-zra2-phase-b-materializer.md`
- `?? src/a_conductor/zero_relay_repair_materializer.py`
- `?? tests/test_zero_relay_repair_materializer.py`

Do NOT delete or recreate these files merely because they are untracked.
They are existing GLM/Worker-2 work to inspect and finish.

Independent GPT read-only precheck at MASTER creation observed:
- key materializer contract structurally matches Phase B;
- related verification: `212 passed, 1 skipped`;
- no PR exists yet for the Phase-B branch.

This is evidence only; GLM must re-run its own bounded pre-freeze checks.

Q1 completion target:
- inspect existing WIP first;
- repair only P0/P1/P2 defects inside the declared WO195 scope;
- do not broaden authority;
- finish work-order checkpoint;
- write `runs/WO-P1-195/result.md` with exact candidate evidence;
- run focused + justified related verification;
- run compile/diff/UTF-8/U+FFFD/secret-like added-line/scope checks;
- commit only the declared tracked scope;
- push exact candidate branch;
- open/update a DRAFT PR against the authorized base;
- record exact candidate SHA and PR URL.

As soon as hosted CI is triggered and is not already terminal, write:
`BLOCKED_EXTERNAL_CI`
and STOP. Do not poll CI in a loop.

If CI is already terminal on a later invocation:
- if failed: diagnose only within the owned scope; repair if the failure is owned and authorized, otherwise `BLOCKED_EXTERNAL_OWNER`;
- if successful: record `BLOCKED_EXTERNAL_GPT_ACCEPTANCE` and STOP.

GLM does not accept or merge its own Phase-B candidate.

### Q2 — ZRA-2 Phase C — NOT YET AUTHORIZED

Canonical Phase-C contract from WO165:
compose the existing review adapter / trusted ReviewBridge evidence without importing A-Wiki internals and without creating a second review lifecycle.

Do not invent a Phase-C implementation packet, branch, or mutable scope.
Proceed only after all are true:
- Q1 exact candidate is independently accepted;
- Phase B is merged/post-main verified where required;
- Issue #214 explicitly says Phase C is `NEXT_READY`;
- a fresh child WO/claim/worktree/mutable-scope pointer exists.

If any item is missing: `BLOCKED_EXTERNAL_AUTHORIZATION` and STOP.

### Q3 — ZRA-2 Phase D — NOT YET AUTHORIZED

Canonical Phase-D contract from WO165:
bind accepted ZRA-1 execution/result path and durable job state, including `REVIEW_PENDING -> COMPLETE` only after exact-head review evidence.

Same rule as Q2: no scope invention. Require explicit NEXT_READY child packet.

### Q4 — ZRA-3 acceptance/continuation — DEPENDENCY BLOCKED

Current preserved candidates:
- PR #263 parent repaired head: `e13155b9947c7b42f00853cc5583480741119531`
- PR #269 production composition head at MASTER creation: `0bf8f1ed088d234ec51e855cf4e067add5552da0`
- WO199 independent-review packet: PR #274

GLM authored the original WO191 Phase-A candidate. Therefore this MASTER must NOT let the same GLM execution self-accept the full ZRA-3 stack.
Only inspect these lanes read-only when needed to understand dependency state.
Wait for an independent reviewer/integrator decision.

### Q5 — ZRA-4 — HOLD

Current planning/gates:
- WO196 physical workspace identity design is merged in main;
- PR #272 / WO197 physical identity implementation gate;
- PR #273 / WO198 deterministic batch identity gate.

No ZRA-4 product-source mutation until ZRA-3 is durably accepted and Issue #216 releases the relevant child scope.

## Non-critical READY backlog

These items are useful but MUST NOT be used to escape an external gate on the active critical-path item.
The MASTER stops at the gate and waits for the next invocation.

### B1 — WO193 GLM validation child repair

Parent byte-integrity source PR #268 is merged in main at merge commit
`02d39cbd9bca1ab3bb19b6e0cfbb0766c991f971`.

GLM validation child PR #275 head at MASTER creation:
`26a841922629b5f3d269a14e5ac5c5339d000738`.

GPT independent rerun found one timing-dependent B07 failure followed by 10/10 focused passes.
Cause evidence: post-spawn identity-write failure paths can return directly before the `_HelperExit` cleanup/wait path; this behavior predates WO193 source repair.

PR #275 is `CHANGES_REQUIRED` for validation quality only.
Do not fix product source on the #275 validation child.
A later explicit invocation may repair B07 determinism/evidence and characterize the lifecycle gap.

### B2 — WO194 launcher-forensics independent review

PR #266 candidate:
`8339e4c9e15c8eefd94693245ef9ef4b627c00de`

This source repair was authored by GPT and is suitable for independent GLM exact-SHA review when the integrator explicitly routes it.
Do not mix it into Q1-Q5 source work.

## Work conservation rules

- Prefer finishing existing owned WIP over opening a new lane.
- Reuse accepted authorities; never create second scheduler/job/provider/lease/review/retry stores.
- Tests are evidence, not permission to expand scope.
- No live Worker restart, provider credential change, installed runtime change, live DB mutation, or process kill from this MASTER unless a future work order explicitly grants it.
- No A-Wiki mutation.
- No shared root-main mutation.
- No hidden background/subagent fan-out unless a work order explicitly grants parallel child claims.

## Safe stop protocol

When an external gate is reached:
1. finish any atomic local write already in progress;
2. do not begin the next mutation;
3. write/update master checkpoint and lane result/checkpoint;
4. ensure tracked work is committed/pushed if the current work order requires candidate freeze and it is safe to do so;
5. report one concise terminal state:
   - `BLOCKED_EXTERNAL_CI`
   - `BLOCKED_EXTERNAL_GPT_ACCEPTANCE`
   - `BLOCKED_EXTERNAL_MERGE`
   - `BLOCKED_EXTERNAL_AUTHORIZATION`
   - `BLOCKED_EXTERNAL_PROVIDER`
   - `BLOCKED_EXTERNAL_OWNER`
   - `RECOVERY_REQUIRED`
6. include exact next safe action and pointer;
7. STOP. Do not poll and do not switch to an unrelated backlog item.

## Definition of useful autonomy

"Continue on your own" means:
- inspect durable truth;
- execute all currently authorized micro-steps in the active queue item;
- checkpoint frequently;
- recover after context rollover from checkpoint;
- stop at authority boundaries.

It never means guessing authority, silently taking another lane, merging one's own implementation, or converting UNKNOWN into permission.
